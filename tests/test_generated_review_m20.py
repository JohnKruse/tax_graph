"""M20-S20 tests for draft-only generated review projection."""

from __future__ import annotations

from pathlib import Path

import json
import jsonschema
import pytest

from workbench import generated_review
from workbench.generated_review import build_generated_document_cells


ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    not (ROOT / "graph" / "2025" / "_drafts").exists(),
    reason="live review drafts are required: fresh checkouts carry no _drafts",
)


@pytest.mark.m20
def test_generated_review_projects_formula_and_source_cells_with_provenance() -> None:
    expected = {
        "form_1040_2025": 199,
        "schedule_1_2025": 73,
        "schedule_a_2025": 33,
    }
    for document_id, count in expected.items():
        result = build_generated_document_cells(ROOT, 2025, document_id)
        assert len(result.cells) == count
        assert all(cell["generated"] is True for cell in result.cells)
        assert all(cell["review_source"] == "draft_only" for cell in result.cells)
        assert all(cell["generated_model"] for cell in result.cells)
        assert all(cell["generated_provider"] for cell in result.cells)
    generated = build_generated_document_cells(ROOT, 2025, "form_1040_2025").cells
    assert sum(cell["generated_status"] == "review_gap" for cell in generated) < len(generated)
    assert any(cell["generated_model"] == "deterministic-authored-policy" for cell in generated)


@pytest.mark.m20
def test_generated_review_keeps_form_and_instruction_slots_separate() -> None:
    result = build_generated_document_cells(ROOT, 2025, "form_1040_2025")
    cell = next(item for item in result.cells if item["official_ref"] == "1z")
    assert isinstance(cell["expression"], dict)
    assert "operation" in cell["expression"]
    assert isinstance(cell["form_citations"], list)
    assert isinstance(cell["instruction_citations"], list)
    assert cell["citations"] is cell["form_citations"]
    line_1i = next(item for item in result.cells if item["official_ref"] == "1i")
    assert any("nontaxable combat pay" in item["quoted_text"].lower() for item in line_1i["instruction_citations"])


@pytest.mark.m20
def test_generated_review_uses_generated_risk_policy_for_gap_cells() -> None:
    result = build_generated_document_cells(ROOT, 2025, "form_1040_2025")
    assert all(cell["population_policy"] for cell in result.cells)
    assert sum(cell["population_policy"] == "review_gap" for cell in result.cells) < len(result.cells)


@pytest.mark.m20
def test_generated_review_renders_resolved_external_sources_and_hides_sentinels() -> None:
    result = build_generated_document_cells(ROOT, 2025, "form_1040_2025")
    line_1a = next(item for item in result.cells if item["official_ref"] == "1a")
    line_1e = next(item for item in result.cells if item["official_ref"] == "1e")
    line_28 = next(item for item in result.cells if item["official_ref"] == "28")
    assert line_1a["expression"]["text"] == "line 1a = W-2 box 1"
    assert line_1e["expression"]["text"] == "line 1e = Form 2441, line 26"
    assert line_28["expression"]["text"] == "line 28 = unresolved source"
    assert "line none" not in str(line_28["expression"])


@pytest.mark.m20
def test_generated_review_renders_structured_math_for_humans() -> None:
    result = build_generated_document_cells(ROOT, 2025, "form_1040_2025")
    line_22 = next(item for item in result.cells if item["official_ref"] == "22")
    assert line_22["expression"]["text"] == "line 22 = line 18 - line 21"
    assert "node_id" not in line_22["expression"]["text"]
    assert "addend" not in line_22["expression"]["text"]
    line_32 = next(item for item in result.cells if item["official_ref"] == "32")
    assert line_32["population_policy"] == "computed"
    assert line_32["expression"]["kind"] == "sum"
    schema = json.loads((ROOT / "schemas" / "review_expression.schema.json").read_text(encoding="utf-8"))
    for cell in result.cells:
        jsonschema.validate(cell["expression"], schema)


@pytest.mark.m20
def test_generated_review_projects_background_policy_and_form_face_citation(monkeypatch) -> None:
    draft = {
        "micro_extraction": {
            "formula_cells": [
                {
                    "target_cell_id": "form_1040_2025_root_line_1z",
                    "line_anchor": "1z",
                    "status": "review_gap",
                    "review_gap": "fixture gap",
                }
            ],
            "background_controls": [
                {
                    "field_name": "topmostSubform[0].Page1[0].f1_04[0]",
                    "population_policy": "user_entered",
                    "status": "complete",
                    "has_policy": True,
                    "reason": "The filer supplies the combat-zone name.",
                    "citation_span_ids": ["span_form_face"],
                }
            ],
        },
        "outline": {},
        "rules": [],
        "edges": [],
        "citations": [],
        "candidate_spans": [
            {
                "span_id": "span_form_face",
                "document_id": "form_1040_2025",
                "relationship": "source",
                "locator": "page 1, line 1",
                "text": "Combat zone",
            }
        ],
        "metrics": {"llm_calls": []},
    }
    monkeypatch.setattr(generated_review, "_load_draft", lambda *args, **kwargs: draft)

    result = build_generated_document_cells(ROOT, 2025, "form_1040_2025")
    cell = next(item for item in result.cells if item["field_name"].endswith("f1_04[0]"))
    assert cell["population_policy"] == "user_entered"
    assert cell["expression"]["text"] == "Header = entered by filer"
    assert cell["form_citations"][0]["quoted_text"] == "Combat zone"
    assert cell["citations"] is cell["form_citations"]
