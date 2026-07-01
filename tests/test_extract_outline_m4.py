from __future__ import annotations

from pathlib import Path
import json
import re
import shutil

import jsonschema
import pytest

from tax_graph.extract.assembly import assemble_formula_plan, realize_outbound_flows
from tax_graph.extract.outline_pipeline import _formula_outline_nodes
from tax_graph.extract.pipeline import extract_document
from tax_graph.extract.micro import MicroExtractionError, extract_formula_plan, validate_formula_plan
from tax_graph.extract.models import RelatedSourceInput, SourceDocumentInput
from tax_graph.extract.outline_checks import OutlineArtifactError, run_outline_artifact_checks
from tax_graph.extract.outline import (
    CandidateSpan,
    OutboundFlow,
    OutlineNode,
    OutlineTree,
    build_candidate_spans,
    build_outline_tree,
    build_outbound_flows,
    write_outline_artifacts,
)
from tax_graph.extract.prompts import graph_object_schemas
from tax_graph.io.loader import load_yaml


ROOT = Path(__file__).resolve().parents[1]


class FakeMicroClient:
    def __init__(self, response: dict):
        self.response = response
        self.calls = []

    def structured_completion(self, *, prompt, schema, model, max_tokens, temperature, purpose):
        self.calls.append(
            {
                "prompt": prompt,
                "schema": schema,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "purpose": purpose,
            }
        )
        return self.response


class PromptAwareMicroClient:
    def __init__(self):
        self.calls = []

    def structured_completion(self, *, prompt, schema, model, max_tokens, temperature, purpose):
        self.calls.append(
            {
                "prompt": prompt,
                "schema": schema,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "purpose": purpose,
            }
        )
        if "kind: totals" in prompt:
            span_id = re.search(r"- (span_[a-z0-9_]+): .*- 2: Totals", prompt).group(1)
            return {
                "operation_plan": [
                    {
                        "output": f"line_2_column_{column}_total",
                        "operation": "SUM",
                        "inputs": [{"name": f"line_1_column_{column}", "role": "addend"}],
                        "citation_span_ids": [span_id],
                    }
                    for column in ["d", "e", "g", "h"]
                ]
            }
        span_id = re.search(r"- (span_[a-z0-9_]+): .*Subtract column", prompt).group(1)
        return {
            "operation_plan": [
                {
                    "output": "column_h_before_adjustment",
                    "operation": "SUBTRACT",
                    "inputs": [
                        {"name": "column_d", "role": "minuend"},
                        {"name": "column_e", "role": "subtrahend"},
                    ],
                    "citation_span_ids": [span_id],
                },
                {
                    "output": "column_h",
                    "operation": "SUM",
                    "inputs": [
                        {"name": "column_h_before_adjustment", "role": "addend"},
                        {"name": "column_g", "role": "addend"},
                    ],
                    "citation_span_ids": [span_id],
                },
            ]
        }


@pytest.mark.m4
def test_outline_builder_captures_8949_structure_and_flow_cue(tmp_path):
    document = _outline_document(tmp_path)

    outline = build_outline_tree(document)

    part_i = outline.children[0]
    assert part_i.outline_id == "part_i"
    assert part_i.kind == "section"
    assert part_i.boxes == ["A", "B", "C"]
    assert part_i.children[0].kind == "transaction_table"
    assert part_i.children[0].outline_id == "part_i_line_1"
    assert part_i.children[0].columns == ["a", "d", "e", "g", "h"]
    assert part_i.children[1].kind == "totals"
    assert part_i.children[1].outline_id == "part_i_line_2"
    assert part_i.children[1].columns == ["a", "d", "e", "g", "h"]
    assert part_i.children[2].kind == "outbound_flow_cue"
    part_ii = outline.children[1]
    assert part_ii.children[2].kind == "outbound_flow_cue"
    assert outline.children[-1].kind == "outbound_flow_cue"
    assert "1b, 2, 3, 8b, 9, 10" in outline.children[-1].label


@pytest.mark.m4
def test_outline_builder_uses_post_line_headers_for_8949_part_ii_formula(tmp_path):
    text_path = tmp_path / "form_8949_2025.txt"
    text = "\n".join(
        [
            "# Page 2",
            "Header: Part II Long-Term. Transactions involving capital assets you held more than 1 year are generally long-term",
            "Header: (J) Long-term transactions reported on Form(s) 1099-DA showing basis was reported to the IRS",
            "Header: (K) Long-term transactions reported on Form(s) 1099-DA showing basis was not reported to the IRS",
            "Header: (L) Long-term digital asset transactions not reported to you on Form 1099-DA or Form 1099-B",
            "- 1: If you enter an amount in column (g),",
            "Header: (e) (h)",
            "Header: (c) (d) Cost or other basis enter a code in column (f). Gain or (loss)",
            "Header: instructions. Code(s) from Amount of with column (g).",
            "- 2: Totals. Add the amounts in columns (d), (e), (g), and (h)",
            "",
        ]
    )
    document = SourceDocumentInput(
        document_id="form_8949_2025",
        kind="tax_form",
        year="2025",
        url="https://www.irs.gov/pub/irs-pdf/f8949.pdf",
        text=text,
        text_path=text_path,
        fields={"fields": []},
        related_sources=[],
    )

    outline = build_outline_tree(document)

    part_ii_line_1 = outline.children[0].children[0]
    assert part_ii_line_1.outline_id == "part_ii_line_1"
    assert part_ii_line_1.kind == "transaction_table"
    assert "h" in part_ii_line_1.columns
    assert [node.outline_id for node in _formula_outline_nodes(outline.children)] == [
        "part_ii_line_1",
        "part_ii_line_2",
    ]


@pytest.mark.m4
def test_candidate_spans_are_code_generated_and_artifacts_are_local(tmp_path):
    document = _outline_document(tmp_path)

    spans = build_candidate_spans(document)
    draft_dir = write_outline_artifacts(document, root=tmp_path)

    subtract_span = next(span for span in spans if "Subtract column" in span.text)
    assert subtract_span.span_id.startswith("span_instructions_form_8949_2025_")
    assert subtract_span.document_id == "instructions_form_8949_2025"
    assert (draft_dir / "outline.yaml").exists()
    assert (draft_dir / "candidate_spans.yaml").exists()
    assert (draft_dir / "outbound_flows.yaml").exists()
    written = load_yaml(draft_dir / "candidate_spans.yaml")
    assert any(item["span_id"] == subtract_span.span_id for item in written)


@pytest.mark.m4
def test_outbound_flows_are_intermediate_until_target_exists(tmp_path):
    document = _outline_document(tmp_path)
    outline = build_outline_tree(document)
    spans = build_candidate_spans(document)

    flows = build_outbound_flows(document, outline=outline, spans=spans)

    assert {flow.target_line for flow in flows} == {"1b", "2", "3", "8b", "9", "10"}
    by_target = {flow.target_line: flow for flow in flows}
    assert by_target["1b"].source_node_id == "form_8949_2025_part_i_line_2_column_h"
    assert by_target["8b"].source_node_id == "form_8949_2025_part_ii_line_2_column_h"
    assert by_target["10"].source_outline_id == "part_ii_line_2"
    assert all(flow.target_document_id == "schedule_d_2025" for flow in flows)
    spans_by_id = {span.span_id: span for span in spans}
    assert "Schedule D" in spans_by_id[by_target["1b"].citation_span_ids[0]].text

    assert realize_outbound_flows(flows, target_node_ids={}) == []
    objects = realize_outbound_flows(
        flows,
        target_node_ids={("schedule_d_2025", "1b"): "schedule_d_2025_line_1b_gain"},
        spans=spans,
    )
    schemas = graph_object_schemas(root=ROOT)
    edges = [obj for obj in objects if obj.kind == "edges"]
    citations = [obj for obj in objects if obj.kind == "citations"]
    assert len(edges) == 1
    assert len(citations) == 1
    jsonschema.validate(edges[0].data, schemas["edges"])
    jsonschema.validate(citations[0].data, schemas["citations"])
    assert edges[0].data["relationship"] == "FEEDS"
    assert edges[0].data["target"] == "schedule_d_2025_line_1b_gain"
    assert citations[0].data["quoted_text"] == spans_by_id[by_target["1b"].citation_span_ids[0]].text


@pytest.mark.m4
def test_outline_artifact_checks_catch_missing_lines_and_bad_flow_spans(tmp_path):
    document = _outline_document(tmp_path)
    spans = build_candidate_spans(document)
    outline = OutlineTree(
        document_id=document.document_id,
        kind=document.kind,
        children=[
            OutlineNode("part_i", "section", "Part I"),
        ],
    )
    flows = [
        OutboundFlow(
            flow_id="flow_bad",
            source_document_id=document.document_id,
            source_outline_id="missing_outline",
            source_node_id="form_8949_2025_missing_column_h",
            target_document_id="schedule_d_2025",
            target_line="1b",
            citation_span_ids=["missing_span"],
        )
    ]

    report = run_outline_artifact_checks(document, outline, spans, flows)

    reasons = [issue.reason for issue in report.issues]
    assert "line 1 count 0 below rendered count 2" in reasons
    assert "missing section part_ii" in reasons
    assert "flow_bad source outline missing" in reasons
    assert "flow_bad unknown span missing_span" in reasons
    with pytest.raises(OutlineArtifactError, match="missing section part_ii"):
        report.raise_for_issues()


@pytest.mark.m4
def test_micro_formula_uses_micro_model_and_validates_span_ids(tmp_path):
    document = _outline_document(tmp_path)
    spans = build_candidate_spans(document)
    span_id = next(span.span_id for span in spans if "Subtract column" in span.text)
    client = FakeMicroClient(
        {
            "operation_plan": [
                {
                    "output": "column_h_before_adjustment",
                    "operation": "SUBTRACT",
                    "inputs": [
                        {"name": "column_d", "role": "minuend"},
                        {"name": "column_e", "role": "subtrahend"},
                    ],
                    "citation_span_ids": [span_id],
                }
            ]
        }
    )

    plan = extract_formula_plan(
        outline_node=OutlineNode("part_i_line_1", "transaction_table", "Line 1", columns=["d", "e", "h"]),
        spans=spans,
        client=client,
        config={"llm": {"model": "big-model", "micro_model": "cheap-model", "temperature": 0}},
        root=ROOT,
    )

    assert plan["operation_plan"][0]["operation"] == "SUBTRACT"
    assert client.calls[0]["model"] == "cheap-model"
    assert client.calls[0]["purpose"] == "tax_graph_micro_formula"

    with pytest.raises(MicroExtractionError, match="unknown citation span id"):
        validate_formula_plan(
            {"operation_plan": [{**plan["operation_plan"][0], "citation_span_ids": ["missing_span"]}]},
            spans=spans,
            root=ROOT,
        )


@pytest.mark.m4
def test_assembly_turns_operation_plan_into_schema_objects(tmp_path):
    document = _outline_document(tmp_path)
    span = CandidateSpan(
        span_id="span_instructions_form_8949_2025_0001",
        document_id="instructions_form_8949_2025",
        relationship="instructions",
        locator="page 1, line 1",
        text="Column (h). Subtract column (e) from column (d), and include column (g).",
    )
    outline_node = OutlineNode("part_i_line_1", "transaction_table", "Form 8949 line 1", columns=["d", "e", "g", "h"])
    plan = {
        "operation_plan": [
            {
                "output": "column_h_before_adjustment",
                "operation": "SUBTRACT",
                "inputs": [
                    {"name": "column_d", "role": "minuend"},
                    {"name": "column_e", "role": "subtrahend"},
                ],
                "citation_span_ids": [span.span_id],
            },
            {
                "output": "column_h",
                "operation": "SUM",
                "inputs": [
                    {"name": "column_h_before_adjustment", "role": "addend"},
                    {"name": "column_g", "role": "addend"},
                ],
                "citation_span_ids": [span.span_id],
            },
        ]
    }

    batch = assemble_formula_plan(document, outline_node, plan, [span], model="mock-micro", root=ROOT)

    schemas = graph_object_schemas(root=ROOT)
    for obj in batch.objects:
        jsonschema.validate(obj.data, schemas[obj.kind])
    assert [rule.data["operation"] for rule in batch.items("rules")] == ["SUBTRACT", "SUM"]
    assert any(node.data["node_type"] == "computed" for node in batch.items("nodes"))
    assert any(node.data["node_id"] == "form_8949_2025_part_i_line_1_column_d_minus_e" for node in batch.items("nodes"))
    assert any(edge.data["role"] == "subtrahend" for edge in batch.items("edges"))
    assert batch.items("citations")[0].data["quoted_text"] == span.text


@pytest.mark.m4
def test_assembly_normalizes_generic_subtract_intermediate_names(tmp_path):
    document = _outline_document(tmp_path)
    span = CandidateSpan(
        span_id="span_instructions_form_8949_2025_0001",
        document_id="instructions_form_8949_2025",
        relationship="instructions",
        locator="page 1, line 1",
        text="Column (h). Subtract column (e) from column (d), and include column (g).",
    )
    outline_node = OutlineNode("part_ii_line_1", "transaction_table", "Form 8949 line 1", columns=["d", "e", "g", "h"])
    plan = {
        "operation_plan": [
            {
                "output": "intermediate_1",
                "operation": "SUBTRACT",
                "inputs": [
                    {"name": "column_d"},
                    {"name": "column_e"},
                ],
                "citation_span_ids": [span.span_id],
            },
            {
                "output": "column_h",
                "operation": "SUM",
                "inputs": [
                    {"name": "intermediate_1", "role": "addend"},
                    {"name": "column_g", "role": "addend"},
                ],
                "citation_span_ids": [span.span_id],
            },
        ]
    }

    batch = assemble_formula_plan(document, outline_node, plan, [span], model="mock-micro", root=ROOT)

    assert any(
        node.data["node_id"] == "form_8949_2025_part_ii_line_1_column_d_minus_e"
        for node in batch.items("nodes")
    )
    assert any(
        edge.data["source"] == "form_8949_2025_part_ii_line_1_column_d_minus_e"
        and edge.data["target"] == "form_8949_2025_part_ii_line_1_column_h"
        for edge in batch.items("edges")
    )


@pytest.mark.m4
def test_outline_first_mode_routes_and_writes_assembled_drafts(tmp_path):
    root = _make_outline_project(tmp_path)
    client = PromptAwareMicroClient()

    routed = extract_document(
        "form_8949_2025",
        year="2025",
        root=root,
        client=client,
        config={
            "project": {"paths": {"graph_dir": "graph", "raw_store": ".cache/raw"}},
            "extraction": {"mode": "outline_first"},
            "llm": {"model": "large-model", "micro_model": None, "temperature": 0},
        },
    )

    draft_dir = root / "graph" / "2025" / "_drafts" / "form_8949_2025"
    assert routed.output_dir == draft_dir
    assert not routed.review
    assert not routed.issues
    assert client.calls[0]["model"] == "large-model"
    assert client.calls[0]["purpose"] == "tax_graph_micro_formula"
    assert [call["purpose"] for call in client.calls] == ["tax_graph_micro_formula"] * 4
    assert (draft_dir / "outline.yaml").exists()
    assert (draft_dir / "candidate_spans.yaml").exists()
    assert (draft_dir / "outbound_flows.yaml").exists()
    rules = load_yaml(draft_dir / "rules.yaml")
    assert [rule["operation"] for rule in rules] == [
        "SUBTRACT",
        "SUM",
        "SUM",
        "SUM",
        "SUM",
        "SUM",
        "SUBTRACT",
        "SUM",
        "SUM",
        "SUM",
        "SUM",
        "SUM",
    ]
    assert any(rule["rule_id"].endswith("line_2_column_h_total_sum") for rule in rules)
    edges = load_yaml(draft_dir / "edges.yaml")
    assert any(edge["target"].endswith("line_2_column_h_total") for edge in edges)
    assert any(edge["target"].endswith("part_ii_line_2_line_2_column_h_total") for edge in edges)
    nodes = load_yaml(draft_dir / "nodes.yaml")
    assert any(node["node_id"] == "form_8949_2025_part_i_line_3" for node in nodes)
    assert any(node["node_id"] == "form_8949_2025_part_ii_line_10" for node in nodes)
    citations = load_yaml(draft_dir / "citations.yaml")
    assert citations[0]["document_id"] == "instructions_form_8949_2025"
    assert "Subtract column" in citations[0]["quoted_text"]
    assert any("Totals. Add the amounts" in citation["quoted_text"] for citation in citations)
    review_html = (draft_dir / "review.html").read_text(encoding="utf-8")
    assert "Form Structure" in review_html
    assert "line 1.01 through line 1.11" in review_html
    assert "Review-only slot label" in review_html
    assert "part_i.line_1.row_01.column_h" in review_html
    assert "column_node#row_key" in review_html
    assert "Outbound Flows" in review_html
    assert "form_8949_2025_part_i_line_1_column_h" in review_html
    assert "Report long-term totals on Schedule D lines 8b, 9, and 10." in review_html
    assert not (root / "graph" / "2025" / "nodes").exists()


def _outline_document(tmp_path: Path) -> SourceDocumentInput:
    text_path = tmp_path / "form_8949_2025.txt"
    text = "\n".join(
        [
            "# Page 1",
            "Header: Part I Short-Term. Box A Box B Box C",
            "Header: (a) Description (d) Proceeds (e) Cost (g) Adjustment (h) Gain or loss",
            "- 1: Transaction table",
            "- 2: Totals. Add the amounts in columns (d), (e), (g), and (h)",
            "Header: include on your Schedule D, line 1b",
            "- 3: (if Box C or Box I above is checked)",
            "# Page 2",
            "Header: Part II Long-Term. Box D Box E Box F",
            "Header: (a) Description (d) Proceeds (e) Cost (g) Adjustment (h) Gain or loss",
            "- 1: Transaction table",
            "- 2: Totals. Add the amounts in columns (d), (e), (g), and (h)",
            "Header: include on your Schedule D, line 8b",
            "- 10: (if Box F or Box L above is checked)",
            "",
        ]
    )
    text_path.write_text(text, encoding="utf-8")
    return SourceDocumentInput(
        document_id="form_8949_2025",
        kind="tax_form",
        year="2025",
        url="https://www.irs.gov/pub/irs-pdf/f8949.pdf",
        text=text,
        text_path=text_path,
        fields={"fields": []},
        related_sources=[
            RelatedSourceInput(
                document_id="instructions_form_8949_2025",
                kind="instructions",
                text="\n".join(
                    [
                        "# Page 1",
                        "Column (h). Subtract column (e) from column (d), and include column (g).",
                        "Report the totals on Schedule D lines 1b, 2, and 3.",
                        "Report long-term totals on Schedule D lines 8b, 9, and 10.",
                        "Report some transactions directly on Schedule D, line 1a.",
                        "Report some transactions directly on Schedule D, line 8a.",
                        "",
                    ]
                ),
                text_path=tmp_path / "instructions_form_8949_2025.txt",
                relationship="instructions",
            )
        ],
    )


def _make_outline_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "config", root / "config")
    shutil.copytree(ROOT / "schemas", root / "schemas")
    raw_dir = root / ".cache" / "raw" / "2025"
    raw_dir.mkdir(parents=True)
    form_text = "\n".join(
        [
            "# Page 1",
            "Header: Part I Short-Term. Box A Box B Box C",
            "Header: (a) Description (d) Proceeds (e) Cost (g) Adjustment (h) Gain or loss",
            "- 1: Transaction table",
            "- 2: Totals. Add the amounts in columns (d), (e), (g), and (h)",
            "Header: include on your Schedule D, line 1b",
            "- 3: (if Box C or Box I above is checked)",
            "# Page 2",
            "Header: Part II Long-Term. Box D Box E Box F",
            "Header: (a) Description (d) Proceeds (e) Cost (g) Adjustment (h) Gain or loss",
            "- 1: Transaction table",
            "- 2: Totals. Add the amounts in columns (d), (e), (g), and (h)",
            "Header: include on your Schedule D, line 8b",
            "- 10: (if Box F or Box L above is checked)",
            "",
        ]
    )
    instructions_text = "\n".join(
        [
            "# Page 1",
            "Column (h). Subtract column (e) from column (d), and include column (g).",
            "Report the totals on Schedule D lines 1b, 2, and 3.",
            "Report long-term totals on Schedule D lines 8b, 9, and 10.",
            "Report some transactions directly on Schedule D, line 1a.",
            "Report some transactions directly on Schedule D, line 8a.",
            "",
        ]
    )
    (raw_dir / "form_8949_2025.txt").write_text(form_text, encoding="utf-8")
    (raw_dir / "form_8949_2025.fields.json").write_text(
        json.dumps({"fields": _form_8949_row_fields()}),
        encoding="utf-8",
    )
    (raw_dir / "instructions_form_8949_2025.txt").write_text(instructions_text, encoding="utf-8")
    return root


def _form_8949_row_fields() -> list[dict]:
    fields = []
    x_clusters = [25, 175, 225, 275, 350, 400, 450, 500]
    for part in [1, 2]:
        for row in range(1, 12):
            for index, x_cluster in enumerate(x_clusters, 1):
                fields.append(
                    {
                        "field_name": f"topmostSubform[0].Page{part}[0].Table_Line1_Part{part}[0].Row{row}[0].f{part}_{row:02d}_{index:02d}[0]",
                        "page": part,
                        "x_cluster": x_cluster,
                        "y_cluster": 400 + row * 25,
                    }
                )
    return fields
