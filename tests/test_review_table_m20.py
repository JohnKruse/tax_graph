"""M20-S62 tests for the deterministic three-column review command."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tax_graph.extract.cells import CellFrame
from tax_graph.review_table import (
    build_review_table,
    render_pseudocode,
    render_review_table_html,
    review_table_command,
    score_instruction,
)


pytestmark = pytest.mark.m20


def _frame() -> CellFrame:
    return CellFrame.from_rows(
        [
            {
                "form": "toy_2025",
                "line": "1",
                "label": "Simple amount",
                "form_face_text": "Enter the amount from line 2.",
                "instruction_text": "Enter the amount from line 2.",
                "instruction_locator": "face_1",
            },
            {
                "form": "toy_2025",
                "line": "2",
                "label": "Conditional amount",
                "form_face_text": (
                    "If line 1 is less than $10,000, enter the smaller of line 1 or $500 "
                    "in column (a); otherwise enter zero."
                ),
                "instruction_text": "Use the worksheet when filing Schedule A.",
                "instruction_locator": "face_2",
            },
        ]
    )


def test_score_instruction_exposes_all_deterministic_signals() -> None:
    score = score_instruction(
        "If the amount is capped at $10,000, use the smaller of the two values in column (a) on Schedule A."
    )

    assert score.conditionals == 1
    assert score.caps == 2
    assert score.dollar_constants == 1
    assert score.table_columns == 2
    assert score.cross_document_refs == 1
    assert score.sentences == 1
    assert score.score > 0


def test_pseudocode_is_code_rendered_and_keeps_lookup_roles() -> None:
    expression = {
        "op": "LOOKUP_TABLE",
        "args": [
            {"node": "filing_status", "role": "key"},
            {"const": 100, "role": "single"},
            {"const": 200, "role": "joint"},
        ],
    }

    rendered = render_pseudocode(expression)

    assert rendered.splitlines() == [
        "LOOKUP TABLE",
        "  key: node filing_status",
        "  single: 100",
        "  joint: 200",
    ]
    assert "model" not in rendered.lower()


def test_pseudocode_does_not_guess_unresolvable_operands() -> None:
    rendered = render_pseudocode(
        {
            "operation": "SUBTRACT",
            "operands": [
                {"role": "minuend", "text": "line 1"},
                {"role": "subtrahend", "ref": {"object_id": "missing_node"}},
            ],
        }
    )

    assert "minuend: line 1" in rendered
    assert "[unresolvable operand: missing_node]" in rendered


def test_pseudocode_renders_graph_conditional_as_if_then_else() -> None:
    rendered = render_pseudocode(
        {
            "operation": "IF_ELSE",
            "operands": [
                {"role": "condition", "text": "line 1"},
                {"role": "threshold", "text": "100"},
                {"role": "when_true", "text": "line 2"},
                {"role": "when_false", "text": "line 3"},
            ],
        }
    )

    assert rendered.splitlines() == [
        "IF",
        "  condition: line 1",
        "  threshold: 100",
        "  THEN: line 2",
        "  ELSE: line 3",
    ]


def test_build_review_table_uses_cleaned_source_and_hardest_selection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tax_graph.review_table.load_document_input",
        lambda *args, **kwargs: SimpleNamespace(document_id="toy_2025", text=""),
    )
    monkeypatch.setattr("tax_graph.review_table.build_cell_frame_from_document", lambda document: _frame())
    monkeypatch.setattr(
        "tax_graph.review_table._graph_projection_rows",
        lambda *args, **kwargs: {
            "1": {"expression": {"op": "COPY", "args": [{"line": "2"}]}, "status": "derived"},
            "2": {
                "expression": {"op": "MAX", "args": [{"line": "1"}, {"const": 0}]},
                "status": "review_gap",
                "failures": ({"kind": "lookup_table_missing_bands"},),
                "warnings": ("unmapped operation",),
            },
        },
    )

    payload = build_review_table(tmp_path, 2025, "toy_2025", hardest=1)

    assert payload["selection_mode"] == "hardest 1"
    assert len(payload["rows"]) == 1
    row = payload["rows"][0]
    assert row.line == "2"
    assert row.printed_instruction.startswith("If line 1")
    assert row.status == "review_gap"
    assert row.selection.score > 0


def test_review_table_html_has_three_columns_and_no_correctness_verdict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tax_graph.review_table.load_document_input",
        lambda *args, **kwargs: SimpleNamespace(document_id="toy_2025", text=""),
    )
    monkeypatch.setattr("tax_graph.review_table.build_cell_frame_from_document", lambda document: _frame())
    monkeypatch.setattr(
        "tax_graph.review_table._graph_projection_rows",
        lambda *args, **kwargs: {"1": {"expression": {"op": "COPY", "args": [{"line": "2"}]}, "status": "derived"}},
    )

    payload = build_review_table(tmp_path, 2025, "toy_2025", all_rows=True)
    html = render_review_table_html(payload)

    assert html.count("<th>") == 3
    assert "Cleaned printed instruction" in html
    assert "Graph expression and status" in html
    assert "Pseudocode" in html
    assert "Selection signals" in html
    assert "right or wrong" not in html.lower()
    assert "Enter the amount from line 2." in html
    assert "Exact expression" in html


def test_review_table_command_writes_only_outside_repository(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "tax_graph.review_table.build_review_table",
        lambda *args, **kwargs: {
            "document_id": "toy_2025",
            "year": "2025",
            "selection_mode": "all rows",
            "rows": [],
        },
    )
    output = tmp_path.parent / "toy_review.html"

    assert review_table_command(
        root=tmp_path,
        document_id="toy_2025",
        output=output,
        all_rows=True,
    ) == 0
    assert output.is_file()
    assert not (tmp_path / "toy_review.html").exists()
    assert "review table:" in capsys.readouterr().out

    with pytest.raises(ValueError, match="outside repository root"):
        review_table_command(
            root=tmp_path,
            document_id="toy_2025",
            output=tmp_path / "inside.html",
            all_rows=True,
        )
