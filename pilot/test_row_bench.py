"""Pilot tests for the M20-S92 row diagnosis harness."""

from __future__ import annotations

from pathlib import Path

from tax_graph.extract.cells import CellRecord

from row_bench import replay_payload, _attempt_prompt


def _row() -> CellRecord:
    return CellRecord(
        form="form_1040_2025",
        line="5a",
        label="Example",
        form_face_text="Example",
        instruction_text="Subtract line 6 from line 2.",
        instruction_locator="instructions_form_1040_2025_5a",
        metadata={
            "printed_lines": ["2", "5a", "6"],
            "evidence_spans": [
                {"span_id": "form_span_5a", "text": "Example"},
                {
                    "span_id": "instructions_form_1040_2025_5a",
                    "text": "Subtract line 6 from line 2.",
                },
            ],
        },
    )


def _inventory() -> dict:
    return {
        "document_inventory": [{"document_id": "form_1040_2025", "title": "Form 1040"}],
        "graph_nodes": [],
    }


def test_replay_payload_uses_production_validator() -> None:
    verdict = replay_payload(
        _row(),
        {
            "expression": {
                "op": "SUBTRACT",
                "args": [{"line": "6"}, {"line": "2"}],
            },
            "quote": "Subtract line 6 from line 2.",
        },
        reference_inventory=_inventory(),
    )

    assert not verdict["accepted"]
    assert [issue.kind for issue in verdict["issues"]] == ["subtract_direction"]


def test_replay_payload_reports_source_side_no_call_separately() -> None:
    verdict = replay_payload(
        _row(),
        None,
        reference_inventory=_inventory(),
    )

    assert not verdict["accepted"]
    assert verdict["issues"][0].kind == "payload"


def test_repair_prompt_is_the_production_repair_shape() -> None:
    row = _row()
    first = replay_payload(
        row,
        {
            "expression": {
                "op": "SUBTRACT",
                "args": [{"line": "6"}, {"line": "2"}],
            },
            "quote": "Subtract line 6 from line 2.",
        },
        reference_inventory=_inventory(),
    )

    prompt = _attempt_prompt("base", row, first)

    assert prompt.startswith("base\n\nREPAIR REQUEST for form_1040_2025 line 5a:")
    assert "subtract_direction:" in prompt

