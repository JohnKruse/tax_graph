"""M20-S22 tests for evidence packets and the read-only prompt bench."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tax_graph.extract.models import RelatedSourceInput, SourceDocumentInput
from tax_graph.extract.background import background_evidence
from tax_graph.extract.assembly import assemble_formula_plan
from tax_graph.extract.micro import validate_formula_plan
from tax_graph.extract.prompt_bench import run_prompt_bench
from tax_graph.extract.outline import CandidateSpan, OutlineNode


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]


class BenchClient:
    def __init__(self, responses: list[dict]):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def structured_completion(self, *, prompt, schema, model, max_tokens, temperature, purpose, seed=None):
        self.calls.append({
            "prompt": prompt,
            "schema": schema,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "purpose": purpose,
        })
        return self.responses.pop(0)


def _control_document(tmp_path: Path) -> SourceDocumentInput:
    return SourceDocumentInput(
        document_id="form_1040_2025",
        kind="tax_form",
        year="2025",
        url="https://example.test/form.pdf",
        text="# Page 1\nCombat zone name\n",
        text_path=tmp_path / "form_1040_2025.txt",
        fields={"fields": [{"field_name": "control_a", "page": 1}]},
        related_sources=[
            RelatedSourceInput(
                document_id="instructions_form_1040_2025",
                kind="instructions",
                text="# Page 1\nIf you served in a combat zone, enter the name.\n",
                text_path=tmp_path / "instructions.txt",
                relationship="instructions",
            )
        ],
    )


def _write_field_map(tmp_path: Path) -> None:
    (tmp_path / "tax-graph.config.yaml").write_text(
        "llm:\n  model: mock\n  micro_model: mock\n",
        encoding="ascii",
    )
    path = tmp_path / "graph" / "2025" / "field_maps"
    path.mkdir(parents=True)
    (path / "form_1040_2025.yaml").write_text(
        yaml.safe_dump(
            {
                "field_dispositions": [
                    {
                        "field_name": "control_a",
                        "label": "Combat zone name",
                        "address_id": "2025/document=form_1040/section=header/control=combat_zone_name",
                        "population_policy": "unsupported",
                        "value_format": "text",
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="ascii",
    )


def test_background_evidence_reserves_form_face_slots() -> None:
    spans = [
        CandidateSpan("source", "form_1040_2025", "source", "page 1, line 1", "Combat zone"),
        CandidateSpan("instruction_a", "instructions", "instructions", "page 1, line 2", "Combat zone instructions"),
        CandidateSpan("instruction_b", "instructions", "instructions", "page 1, line 3", "Combat zone filer guidance"),
        CandidateSpan("instruction_c", "instructions", "instructions", "page 1, line 4", "Combat zone answer guidance"),
        CandidateSpan("instruction_d", "instructions", "instructions", "page 1, line 5", "Combat zone filing guidance"),
        CandidateSpan("instruction_e", "instructions", "instructions", "page 1, line 6", "Combat zone extra guidance"),
    ]

    selected = background_evidence(
        {"label": "Combat zone name", "address_id": "combat_zone_name", "page": 1},
        spans,
    )

    assert selected[0].span_id == "source"
    assert any(span.relationship == "source" for span in selected)
    assert len(selected) <= 8


def test_prompt_bench_print_data_is_in_memory_and_reports_matching_span(tmp_path: Path) -> None:
    _write_field_map(tmp_path)
    document = _control_document(tmp_path)
    client = BenchClient([
        {
            "population_policy": "user_entered",
            "quote": "Combat zone name",
            "reason": "The filer supplies the name.",
        }
    ])
    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))

    results = run_prompt_bench(
        document,
        ["control_a"],
        client=client,
        config={"llm": {"model": "mock", "micro_model": "mock"}},
        root=tmp_path,
    )

    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    result = results[0]
    assert before == after
    assert result["accepted"] is True
    assert result["validation_error"] is None
    assert result["response"]["quote"] == "Combat zone name"
    assert result["matched_spans"][0]["span_id"] == "span_form_1040_2025_0001"
    assert "exactly one population_policy" in result["prompt"]
    assert client.calls[0]["purpose"] == "tax_graph_background_policy"


def test_prompt_bench_reports_form_face_citation_rejection(tmp_path: Path) -> None:
    _write_field_map(tmp_path)
    document = _control_document(tmp_path)
    client = BenchClient([
        {
            "population_policy": "user_entered",
            "quote": "If you served in a combat zone, enter the name.",
            "reason": "The instructions describe a filer entry.",
        }
    ])

    result = run_prompt_bench(
        document,
        ["control_a"],
        client=client,
        config={"llm": {"model": "mock", "micro_model": "mock"}},
        root=tmp_path,
    )[0]

    assert result["accepted"] is False
    assert result["validation_error"] == (
        "MicroExtractionError: background policy quote has no form-face citation"
    )
    assert result["matched_spans"][0]["relationship"] == "instructions"


def test_prompt_bench_uses_formula_cell_prompt_path(tmp_path: Path) -> None:
    document = SourceDocumentInput(
        document_id="form_1040_2025",
        kind="tax_form",
        year="2025",
        url="https://example.test/form.pdf",
        text="# Page 1\n- 1: Wages\n- 2: Add lines 1 and 1\n",
        text_path=tmp_path / "form.txt",
        fields={"fields": []},
    )
    client = BenchClient([
        {"operation": "SUM", "source_lines": ["1", "1"], "quote": "Add lines 1 and 1"}
    ])

    result = run_prompt_bench(
        document,
        ["2"],
        client=client,
        config={"llm": {"model": "mock", "micro_model": "mock"}},
        root=ROOT,
    )[0]

    assert result["target_type"] == "cell"
    assert result["accepted"] is True
    assert "target line label: Add lines 1 and 1" in result["prompt"]
    assert client.calls[0]["purpose"] == "tax_graph_micro_formula"


def test_prompt_bench_command_prints_exact_prompt_response_and_decision(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    from tax_graph.cli import prompt_bench_command
    import tax_graph.extract.inputs as extract_inputs

    _write_field_map(tmp_path)
    document = _control_document(tmp_path)
    monkeypatch.setattr(extract_inputs, "load_document_input", lambda *args, **kwargs: document)
    client = BenchClient([
        {
            "population_policy": "user_entered",
            "quote": "Combat zone name",
            "reason": "The filer supplies the name.",
        }
    ])

    code = prompt_bench_command(
        doc="form_1040_2025",
        target_ids=["control_a"],
        root=tmp_path,
        client=client,
    )
    output = capsys.readouterr().out

    assert code == 0
    assert "=== prompt bench: control_a ===" in output
    assert "Classify one physical tax-form control" in output
    assert '"quote": "Combat zone name"' in output
    assert "decision: accepted" in output
    assert "span_form_1040_2025_0001" in output


def test_explicit_printed_constant_becomes_a_cited_parameter_node(tmp_path: Path) -> None:
    document = SourceDocumentInput(
        document_id="schedule_a_2025",
        kind="schedule",
        year="2025",
        url="https://example.test/schedule-a.pdf",
        text="2 Enter amount\n3 Multiply line 2 by 7.5% (0.075) 3\n",
        text_path=tmp_path / "schedule_a.txt",
    )
    node = OutlineNode(
        "section_1_line_3",
        "line",
        "Multiply line 2 by 7.5% (0.075) 3",
        line_anchor="3",
    )
    span = CandidateSpan(
        "span_form",
        document.document_id,
        "source",
        "page 1, line 2",
        "Multiply line 2 by 7.5% (0.075) 3",
    )
    plan = {
        "operation": "MULTIPLY",
        "source_lines": ["2", {"constant": 0.075}],
        "quote": "Multiply line 2 by 7.5% (0.075)",
    }

    validate_formula_plan(plan, spans=[span], root=ROOT, outline_node=node)
    batch = assemble_formula_plan(
        document,
        node,
        plan,
        [span],
        root=ROOT,
        line_index={("schedule_a_2025", "2"): "schedule_a_2025_root_line_2"},
    )

    literal = next(item for item in batch.items("nodes") if "constant_value" in item.data)
    edge = next(item for item in batch.items("edges") if item.data["role"] == "multiplier")
    assert literal.data["constant_value"] == 0.075
    assert literal.data["node_type"] == "parameter"
    assert literal.data["value_type"] == "percentage"
    assert literal.data["citation_refs"] == ["cite_span_form"]
    assert edge.data["source"] == literal.data["node_id"]


def test_printed_constant_pair_keeps_lookup_roles_and_shared_citation(tmp_path: Path) -> None:
    document = SourceDocumentInput(
        document_id="schedule_1a_2025",
        kind="schedule",
        year="2025",
        url="https://example.test/schedule-1a.pdf",
        text="9 Enter $150,000 ($300,000 if married filing jointly) 9\n",
        text_path=tmp_path / "schedule_1a.txt",
    )
    node = OutlineNode(
        "section_1_line_9",
        "line",
        "Enter $150,000 ($300,000 if married filing jointly)",
        line_anchor="9",
    )
    span = CandidateSpan(
        "span_form",
        document.document_id,
        "source",
        "page 1, line 9",
        "Enter $150,000 ($300,000 if married filing jointly)",
    )
    plan = {
        "operation": "LOOKUP_TABLE",
        "source_lines": [
            {"constant": 150000, "role": "default", "value_type": "currency"},
            {"constant": 300000, "role": "married_filing_jointly", "value_type": "currency"},
        ],
        "quote": "Enter $150,000 ($300,000 if married filing jointly)",
    }

    validate_formula_plan(plan, spans=[span], root=ROOT, outline_node=node)
    batch = assemble_formula_plan(document, node, plan, [span], root=ROOT)

    parameters = [item for item in batch.items("nodes") if "constant_value" in item.data]
    assert [item.data["constant_value"] for item in parameters] == [150000, 300000]
    assert all(item.data["value_type"] == "currency" for item in parameters)
    assert all(item.data["citation_refs"] == ["cite_span_form"] for item in parameters)
    assert [edge.data["role"] for edge in batch.items("edges")] == [
        "single",
        "married_filing_separately",
        "head_of_household",
        "qualifying_surviving_spouse",
        "married_filing_jointly",
    ]


def test_constant_multiplier_escape_hatch_is_removed(tmp_path: Path) -> None:
    node = OutlineNode("line_3", "line", "Multiply line 2 by 7.5% (0.075)", line_anchor="3")
    span = CandidateSpan("span_form", "schedule_a_2025", "source", "page 1", node.label)
    with pytest.raises(ValueError, match="MULTIPLY requires exactly 2"):
        validate_formula_plan(
            {
                "operation": "MULTIPLY",
                "source_lines": ["2"],
                "quote": node.label,
            },
            spans=[span],
            root=ROOT,
            outline_node=node,
        )


def test_explicit_form_range_skips_unprinted_optional_children(tmp_path: Path) -> None:
    document = SourceDocumentInput(
        document_id="schedule_1_2025",
        kind="schedule",
        year="2025",
        url="https://example.test/schedule-1.pdf",
        text="24a First\n24b Second\n24z Other\n25 Add lines 24a through 24z 25\n",
        text_path=tmp_path / "schedule_1.txt",
    )
    node = OutlineNode(
        "section_2_line_25",
        "line",
        "Add lines 24a through 24z 25",
        line_anchor="25",
    )
    span = CandidateSpan(
        "span_form",
        document.document_id,
        "source",
        "page 1, line 4",
        "Add lines 24a through 24z 25",
    )
    source_lines = [f"24{letter}" for letter in "abcdefghijklmnopqrstuvwxy"] + ["24z"]
    line_index = {
        (document.document_id, anchor): f"{document.document_id}_root_line_{anchor}"
        for anchor in ("24a", "24b", "24z")
    }
    events: list[dict] = []
    batch = assemble_formula_plan(
        document,
        node,
        {"operation": "SUM", "source_lines": source_lines, "quote": span.text},
        [span],
        root=ROOT,
        line_index=line_index,
        resolution_events=events,
    )

    assert len(batch.items("edges")) == 3
    assert {event["source_line"] for event in events} == set(source_lines[2:-1])
