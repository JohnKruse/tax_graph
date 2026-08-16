"""M20-S114 guards for resilient generated review projection."""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench import generated_review
from workbench.cell_inventory import DocumentCells


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.m20


def _cell(document_id: str, official_ref: str, control_role: str = "amount") -> dict[str, object]:
    return {
        "cell_id": f"{document_id}_{official_ref}_{control_role}",
        "document_id": document_id,
        "official_ref": official_ref,
        "display_name": f"Line {official_ref}",
        "control_role": control_role,
        "address_id": f"2025/document={document_id}/line={official_ref}/control={control_role}",
        "page": 1,
        "order": 1,
        "field_name": f"field_{official_ref}_{control_role}",
        "node_id": None,
        "population_policy": "review_gap",
        "citations": [],
        "instruction_citations": [],
    }


def test_unplaceable_generated_rows_are_reported_without_changing_cell_denominator(monkeypatch) -> None:
    document_id = "form_1040_2025"
    base = DocumentCells(document_id, [_cell(document_id, "1")], pages=[1])
    draft = {
        "micro_extraction": {
            "formula_cells": [
                {
                    "target_cell_id": f"{document_id}_root_line_99",
                    "line_anchor": "99",
                    "label": "Generated line 99",
                    "status": "review_gap",
                    "review_gap": "fixture gap",
                }
            ]
        },
        "outline": {},
        "rules": [],
        "edges": [],
        "decisions": [],
        "citations": [],
        "candidate_spans": [],
        "metrics": {"llm_calls": []},
    }
    monkeypatch.setattr(generated_review, "build_document_cells", lambda *args, **kwargs: base)
    monkeypatch.setattr(generated_review, "_load_draft", lambda *args, **kwargs: draft)

    result = generated_review.build_generated_document_cells(ROOT, 2025, document_id)

    assert len(result.cells) == 1
    assert len(result.unplaceable) == 1
    assert result.unplaceable[0]["line_anchor"] == "99"
    assert result.unplaceable[0]["label"] == "Generated line 99"
    assert result.unplaceable[0]["kind"] == "generated"
    assert result.unplaceable[0]["reason"]


def test_elections_redirect_to_checkbox_and_deduplicate_equivalent_questions(monkeypatch) -> None:
    document_id = "schedule_a_2025"
    amount = _cell(document_id, "5a", "amount")
    checkbox = _cell(document_id, "5a", "checkbox")
    base = DocumentCells(document_id, [amount, checkbox], pages=[1])
    first = {
        "decision_id": "decision_schedule_a_2025_5_filer_election",
        "sets_node": f"{document_id}_section_line_5",
        "question": "Which type of tax will you include on Schedule A, line 5a?",
        "citation_refs": ["cite_face"],
        "options": [
            {"option_id": "income", "label": "State and local income taxes", "option_type": "choice"},
            {"option_id": "sales", "label": "General sales taxes", "option_type": "choice"},
        ],
    }
    second = {
        "decision_id": "decision_schedule_a_2025_5a_filer_election",
        "sets_node": f"{document_id}_section_line_5a",
        "question": "Do you elect to deduct state and local general sales taxes instead of state and local income taxes?",
        "citation_refs": ["cite_face"],
        "options": [
            {"option_id": "income", "label": "Do not elect general sales taxes; use state and local income taxes on line 5a", "option_type": "choice"},
            {"option_id": "sales", "label": "Elect state and local general sales taxes", "option_type": "choice"},
        ],
    }
    draft = {
        "micro_extraction": {
            "formula_cells": [
                {
                    "target_cell_id": f"{document_id}_section_line_5a",
                    "line_anchor": "5a",
                    "status": "decision",
                    "decision_id": second["decision_id"],
                }
            ],
            "non_formula_cells": [
                {
                    "target_cell_id": f"{document_id}_section_line_5",
                    "line_anchor": "5",
                    "status": "decision",
                    "response_kind": "election",
                    "decision_id": first["decision_id"],
                }
            ],
            "decision_cells": [
                {"target_cell_id": f"{document_id}_section_line_5", "line_anchor": "5", "decision_id": first["decision_id"]},
                {"target_cell_id": f"{document_id}_section_line_5a", "line_anchor": "5a", "decision_id": second["decision_id"]},
            ],
        },
        "outline": {},
        "rules": [],
        "edges": [],
        "decisions": [first, second],
        "citations": [],
        "candidate_spans": [],
        "metrics": {"llm_calls": []},
    }
    monkeypatch.setattr(generated_review, "build_document_cells", lambda *args, **kwargs: base)
    monkeypatch.setattr(generated_review, "_load_draft", lambda *args, **kwargs: draft)

    result = generated_review.build_generated_document_cells(ROOT, 2025, document_id)

    checkbox_result = next(cell for cell in result.cells if cell["cell_id"] == checkbox["cell_id"])
    assert [item["decision_id"] for item in checkbox_result["decisions"]] == [second["decision_id"]]
    assert checkbox_result["decisions"][0]["anchor"] == "5a"
    assert checkbox_result["decisions"][0]["anchor_source"] == "line"
    assert result.unplaceable == []
