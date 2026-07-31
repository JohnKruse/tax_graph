from __future__ import annotations

from pathlib import Path
import json
import re
import shutil

import jsonschema
import pytest

from tax_graph.extract.assembly import FormulaAssemblyFinding, assemble_formula_plan, realize_outbound_flows
from tax_graph.extract.outline_pipeline import _formula_outline_nodes, generate_outline_first_drafts
from tax_graph.extract.outline_pipeline import _resolve_declared_source, _spans_for_outline_node
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


@pytest.mark.m20
def test_formula_line_micro_path_is_bounded_and_isolates_failed_cells(tmp_path):
    text = "\n".join(
        [
            "# Page 1",
            "Header: Part I",
            "- 1z: Add lines 1a through 1h",
            "- 2: Add lines 1z and 2b",
            "- 2b: Ordinary input",
            "",
        ]
    )
    text_path = tmp_path / "form_1040_2025.txt"
    text_path.write_text(text, encoding="utf-8")
    line_anchors = [
        {
            "anchor": match.group(1).lower(),
            "page": 1,
            "text_offset": match.start(1),
            "text_length": len(match.group(1)),
        }
        for match in re.finditer(r"^[-]\s+([0-9]+[a-z]?|[a-z]):", text, re.IGNORECASE | re.MULTILINE)
    ]
    document = SourceDocumentInput(
        document_id="form_1040_2025",
        kind="tax_form",
        year="2025",
        url="https://example.test/form.pdf",
        text=text,
        text_path=text_path,
        fields={"fields": [], "line_anchors": line_anchors},
    )

    class FailingCellClient:
        def __init__(self):
            self.calls = []

        def structured_completion(self, *, prompt, schema, model, max_tokens, temperature, purpose):
            self.calls.append({"prompt": prompt, "max_tokens": max_tokens, "purpose": purpose})
            if len(self.calls) == 1:
                raise RuntimeError("cell failed")
            return {
                "operation": "SUM",
                "source_lines": ["1z", "2b"],
                "quote": "Add lines 1z and 2b",
            }

    client = FailingCellClient()
    batch = generate_outline_first_drafts(
        document,
        client=client,
        config={"extraction": {"micro_max_tokens": 4000}, "llm": {"model": "mock"}},
        root=ROOT,
    )

    assert batch.micro_stats["cells_attempted"] == 2
    assert batch.micro_stats["cells_succeeded"] == 1, batch.micro_stats
    assert batch.micro_stats["cells_failed"] == 1
    assert "RuntimeError" in batch.micro_stats["failure_reasons_by_kind"]
    assert all(call["max_tokens"] == 4000 for call in client.calls)
    assert "target line label:" in client.calls[1]["prompt"]
    assert "Add lines 1z and 2b" in client.calls[1]["prompt"]
    assert "addressable_operand_candidates:" not in client.calls[1]["prompt"]
    assert "outline_id:" not in client.calls[1]["prompt"]


@pytest.mark.m20
def test_human_formula_answer_resolves_printed_lines_and_fails_closed(tmp_path):
    document = SourceDocumentInput(
        document_id="form_1040_2025",
        kind="tax_form",
        year="2025",
        url="https://example.test/form.pdf",
        text="1a Wages\n9 Total income\n",
        text_path=tmp_path / "form.txt",
    )
    span = CandidateSpan(
        span_id="span_form_1040_2025_0001",
        document_id=document.document_id,
        relationship="source",
        locator="page 1, line 1",
        text="9 Total income: Add lines 1a and 2b",
    )
    node = OutlineNode("root_line_9", "line", "Add lines 1a and 2b", line_anchor="9")
    plan = {
        "operation": "SUM",
        "source_lines": [{"form": "Form 1040 or 1040-SR", "line": "1a"}, "2b"],
        "quote": "Add lines 1a and 2b",
    }
    line_index = {
        (document.document_id, "1a"): "form_1040_2025_root_line_1a",
        (document.document_id, "2b"): "form_1040_2025_root_line_2b",
    }

    batch = assemble_formula_plan(document, node, plan, [span], line_index=line_index)
    assert {edge.data["source"] for edge in batch.items("edges")} == {
        "form_1040_2025_root_line_1a",
        "form_1040_2025_root_line_2b",
    }
    assert {edge.data["target"] for edge in batch.items("edges")} == {"form_1040_2025_root_line_9"}
    assert not any("root_line_9_root_line" in node.data["node_id"] for node in batch.items("nodes"))

    with pytest.raises(FormulaAssemblyFinding, match="not present"):
        assemble_formula_plan(
            document,
            node,
            {**plan, "source_lines": ["missing"]},
            [span],
            line_index=line_index,
        )


@pytest.mark.m20
def test_instruction_join_requires_line_ownership_not_mentions(tmp_path):
    document = SourceDocumentInput(
        document_id="form_1040_2025",
        kind="tax_form",
        year="2025",
        url="https://example.test/form-1040.pdf",
        text="1z Add lines 1a through 1h\n",
        text_path=tmp_path / "form.txt",
        fields={"line_anchors": [{"anchor": "1z", "page": 1, "text_offset": 0}]},
    )
    source = CandidateSpan(
        "span_form_1040_2025_0001", document.document_id, "source", "page 1, line 1", "1z Add lines 1a through 1h"
    )
    wrong_heading = CandidateSpan(
        "span_instructions_form_1040_2025_0001",
        "instructions_form_1040_2025",
        "instructions",
        "page 35, line 1",
        "### Line 27b",
    )
    wrong_body = CandidateSpan(
        "span_instructions_form_1040_2025_0002",
        "instructions_form_1040_2025",
        "instructions",
        "page 35, line 2",
        "Check the box on line 27b if the amount was also reported on Form 1040, line 1z.",
    )
    owned = CandidateSpan(
        "span_instructions_form_1040_2025_0003",
        "instructions_form_1040_2025",
        "instructions",
        "page 3, line 3",
        "|  1z. Add lines 1a through 1h  |",
    )
    owned_body = CandidateSpan(
        "span_instructions_form_1040_2025_0004",
        "instructions_form_1040_2025",
        "instructions",
        "page 3, line 4",
        "The amount on line 1z is the total of these wages.",
    )
    node = OutlineNode("root_line_1z", "line", "Add lines 1a through 1h", line_anchor="1z")

    selected = _spans_for_outline_node(document, node, [source, wrong_heading, wrong_body, owned, owned_body])

    assert source in selected
    assert owned in selected
    assert wrong_body not in selected
    assert owned_body not in selected


@pytest.mark.m20
def test_instruction_section_body_survives_deeper_heading(tmp_path):
    document = SourceDocumentInput(
        document_id="form_1040_2025",
        kind="tax_form",
        year="2025",
        url="https://example.test/form-1040.pdf",
        text="1i Combat pay election\n",
        text_path=tmp_path / "form.txt",
    )
    spans = [
        CandidateSpan("instruction_heading", "instructions_form_1040_2025", "instructions", "page 1, line 1", "## Line 1i"),
        CandidateSpan("instruction_title", "instructions_form_1040_2025", "instructions", "page 1, line 2", "### Nontaxable Combat Pay Election"),
        CandidateSpan("instruction_body", "instructions_form_1040_2025", "instructions", "page 1, line 3", "If you elect to include the amount on line 1i, enter it here."),
        CandidateSpan("next_heading", "instructions_form_1040_2025", "instructions", "page 1, line 4", "## Line 27a"),
        CandidateSpan("next_body", "instructions_form_1040_2025", "instructions", "page 1, line 5", "Enter the amount for line 27a."),
    ]
    node = OutlineNode("root_line_1i", "line", "Combat pay election", line_anchor="1i")

    selected = _spans_for_outline_node(document, node, spans)

    assert [span.span_id for span in selected] == ["instruction_heading", "instruction_title", "instruction_body"]


@pytest.mark.m20
def test_line_reference_resolves_schedule_alias_and_reports_bare_parent(tmp_path):
    document = SourceDocumentInput(
        document_id="schedule_a_2025",
        kind="schedule",
        year="2025",
        url="https://example.test/schedule-a.pdf",
        text="11a A\n11b B\n14 Total\n",
        text_path=tmp_path / "schedule-a.txt",
    )
    span = CandidateSpan(
        "span_schedule_a_2025_0001", document.document_id, "source", "page 1, line 3", "14 Total: Add lines 11 through 13"
    )
    node = OutlineNode("section_1_line_15", "line", "Add lines 11 through 13", line_anchor="15")
    line_index = {
        (document.document_id, "11a"): "schedule_a_2025_section_1_line_11a",
        (document.document_id, "11b"): "schedule_a_2025_section_1_line_11b",
        (document.document_id, "14"): "schedule_a_2025_section_1_line_14",
    }
    plan = {
        "operation": "SUM",
        "source_lines": [
            {"form": "Schedule A", "line": "11"},
            {"form": "Schedule A", "line": "14"},
        ],
        "quote": "Add lines 11 through 13",
    }

    alias_batch = assemble_formula_plan(
        document,
        node,
        {**plan, "source_lines": [{"form": "Schedule A", "line": "14"}]},
        [span],
        line_index=line_index,
    )
    assert alias_batch.items("edges")[0].data["source"] == "schedule_a_2025_section_1_line_14"

    with pytest.raises(FormulaAssemblyFinding, match="bare source line is ambiguous") as exc_info:
        assemble_formula_plan(document, node, plan, [span], line_index=line_index)

    assert exc_info.value.finding["code"] == "ambiguous_parent_source_line"
    assert exc_info.value.finding["candidates"] == [
        "schedule_a_2025_section_1_line_11a",
        "schedule_a_2025_section_1_line_11b",
    ]


@pytest.mark.m20
def test_line_reference_resolves_a_missing_parent_to_its_only_lettered_child(tmp_path):
    document = SourceDocumentInput(
        document_id="schedule_1_2025",
        kind="schedule",
        year="2025",
        url="https://example.test/schedule-1.pdf",
        text="2a Alimony received\n10 Combine lines 1 through 7 and 9\n",
        text_path=tmp_path / "schedule-1.txt",
    )
    span = CandidateSpan(
        "span_schedule_1_2025_0001",
        document.document_id,
        "source",
        "page 1, line 2",
        "10 Combine lines 1 through 7 and 9",
    )
    node = OutlineNode("line_10", "line", "Combine lines 1 through 7 and 9", line_anchor="10")
    events: list[dict] = []

    batch = assemble_formula_plan(
        document,
        node,
        {
            "operation": "SUM",
            "source_lines": ["2"],
            "quote": "Combine lines 1 through 7 and 9",
        },
        [span],
        line_index={(document.document_id, "2a"): "schedule_1_2025_line_2a"},
        resolution_events=events,
    )

    assert batch.items("edges")[0].data["source"] == "schedule_1_2025_line_2a"
    assert events == [
        {
            "source_line": "2",
            "resolved_to": ["schedule_1_2025_line_2a"],
            "reason": "resolved through deterministic lettered child lines",
        }
    ]


@pytest.mark.m20
def test_line_reference_expands_a_heading_only_when_operation_supports_children(tmp_path):
    document = SourceDocumentInput(
        document_id="schedule_1_2025",
        kind="schedule",
        year="2025",
        url="https://example.test/schedule-1.pdf",
        text="8 Other income\n8a First\n8b Second\n9 Total\n",
        text_path=tmp_path / "schedule-1.txt",
    )
    span = CandidateSpan(
        "span_schedule_1_2025_0002",
        document.document_id,
        "source",
        "page 1, line 4",
        "9 Total",
    )
    node = OutlineNode("line_9", "line", "Total", line_anchor="9")
    line_index = {
        (document.document_id, "8"): "schedule_1_2025_line_8",
        (document.document_id, "8a"): "schedule_1_2025_line_8a",
        (document.document_id, "8b"): "schedule_1_2025_line_8b",
    }

    batch = assemble_formula_plan(
        document,
        node,
        {"operation": "SUM", "source_lines": ["8"], "quote": "9 Total"},
        [span],
        line_index=line_index,
        line_kinds={(document.document_id, "8"): "heading"},
        line_children={(document.document_id, "8"): [
            "schedule_1_2025_line_8a",
            "schedule_1_2025_line_8b",
        ]},
    )

    assert [edge.data["source"] for edge in batch.items("edges")] == [
        "schedule_1_2025_line_8a",
        "schedule_1_2025_line_8b",
    ]


@pytest.mark.m20
def test_source_declaration_identity_is_explicit_and_fail_closed(tmp_path):
    document = SourceDocumentInput(
        document_id="form_1040_2025",
        kind="tax_form",
        year="2025",
        url="https://example.test/form-1040.pdf",
        text="",
        text_path=tmp_path / "form.txt",
    )
    line_index = {(document.document_id, "1a"): "form_1040_2025_root_line_1a"}

    assert _resolve_declared_source(
        document,
        {"source_kind": "information_return", "form": "W-2", "box": "1", "line": ""},
        line_index=line_index,
    ) == "form_w2_2025_box_1"
    assert _resolve_declared_source(
        document,
        {"source_kind": "form_line", "form": "Form 2441", "line": "26", "box": ""},
        line_index=line_index,
    ) == "form_2441_2025_root_line_26"
    assert _resolve_declared_source(
        document,
        {"source_kind": "form_line", "form": "Form 1040", "line": "99", "box": ""},
        line_index=line_index,
    ) is None


@pytest.mark.m20
def test_non_formula_micro_path_records_resolved_source_identity(tmp_path):
    text = "\n".join(
        [
            "- 1a: Total amount from Form(s) W-2, box 1 (see instructions)",
            "- 1e: Taxable dependent care benefits from Form 2441, line 26",
            "",
        ]
    )
    text_path = tmp_path / "form_1040_2025.txt"
    text_path.write_text(text, encoding="utf-8")
    line_anchors = [
        {
            "anchor": match.group(1).lower(),
            "page": 1,
            "text_offset": match.start(1),
            "text_length": len(match.group(1)),
        }
        for match in re.finditer(r"^[-]\s+([0-9]+[a-z]?):", text, re.IGNORECASE | re.MULTILINE)
    ]
    document = SourceDocumentInput(
        document_id="form_1040_2025",
        kind="tax_form",
        year="2025",
        url="https://example.test/form-1040.pdf",
        text=text,
        text_path=text_path,
        fields={"fields": [], "line_anchors": line_anchors},
    )

    class SourceClient:
        def structured_completion(self, *, prompt, schema, model, max_tokens, temperature, purpose):
            target_label = prompt.split("target line label:", 1)[1].splitlines()[0]
            if "W-2" in target_label:
                return {
                    "source_kind": "information_return",
                    "form": "W-2",
                    "line": "",
                    "box": "1",
                    "quote": "Total amount from Form(s) W-2, box 1 (see instructions)",
                }
            return {
                "source_kind": "form_line",
                "form": "Form 2441",
                "line": "26",
                "box": "",
                "quote": "Taxable dependent care benefits from Form 2441, line 26",
            }

    batch = generate_outline_first_drafts(
        document,
        client=SourceClient(),
        config={"extraction": {"micro_max_tokens": 4000}, "llm": {"model": "mock"}},
        root=ROOT,
    )

    records = {item["line_anchor"]: item for item in batch.micro_stats["non_formula_cells"]}
    assert records["1a"]["status"] == "complete", records["1a"].get("review_gap")
    assert records["1a"]["resolved_source_id"] == "form_w2_2025_box_1"
    assert records["1e"]["status"] == "complete"
    assert records["1e"]["resolved_source_id"] == "form_2441_2025_root_line_26"
    assert batch.micro_stats["source_cells_resolved"] == 2


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
                "extraction": {"mode": "outline_first", "expression_mode": "none"},
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
    shutil.copyfile(
        root / "config" / "tax-graph.config.example.yaml",
        root / "config" / "tax-graph.config.yaml",
    )  # hermetic: never inherit the developer's gitignored local config
    shutil.copytree(ROOT / "schemas", root / "schemas")
    graph_documents = root / "graph" / "2025" / "documents"
    graph_documents.mkdir(parents=True)
    (graph_documents / "form-8949.yaml").write_text(
        "\n".join(
            [
                "document_id: form_8949_2025",
                "title: Form 8949",
                "tax_year: 2025",
                "document_type: tax_form",
                "document_class: return",
                "status: partial",
                "not_modeled_fields:",
                "  - field_id: form_8949_unmodeled_table_columns",
                "    table_columns:",
                "      - a",
                "      - b",
                "      - c",
                "      - f",
                "    reason: Non-arithmetic table columns are outside the draft slice.",
                "",
            ]
        ),
        encoding="utf-8",
    )
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
        json.dumps({"fields": _form_8949_row_fields(), "line_anchors": _line_anchor_index(form_text)}),
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


def _line_anchor_index(text: str) -> list[dict[str, int | str]]:
    return [
        {
            "anchor": match.group(1).lower(),
            "page": 1,
            "text_offset": match.start(1),
            "text_length": len(match.group(1)),
        }
        for match in re.finditer(r"^[-]\s+([0-9]+[a-z]?|[a-z]):", text, re.IGNORECASE | re.MULTILINE)
    ]
