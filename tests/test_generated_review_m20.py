"""M20-S15 tests for draft-only generated review projection."""

from __future__ import annotations

from pathlib import Path

import json
import jsonschema
import pytest

from workbench.generated_review import build_generated_document_cells


ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    not (ROOT / "graph" / "2025" / "_drafts").exists(),
    reason="live review drafts are required: fresh checkouts carry no _drafts",
)


@pytest.mark.m20
def test_generated_review_projects_formula_and_source_cells_with_provenance() -> None:
    expected = {
        "form_1040_2025": 57,
        "schedule_1_2025": 4,
        "schedule_a_2025": 7,
    }
    for document_id, count in expected.items():
        result = build_generated_document_cells(ROOT, 2025, document_id)
        assert len(result.cells) == count
        assert all(cell["generated"] is True for cell in result.cells)
        assert all(cell["review_source"] == "draft_only" for cell in result.cells)
        assert all(cell["generated_model"] == "google/gemini-3.6-flash" for cell in result.cells)
        assert all(cell["generated_provider"] == "Google AI Studio" for cell in result.cells)
    assert sum(cell["generated_status"] == "review_gap" for cell in build_generated_document_cells(ROOT, 2025, "form_1040_2025").cells) == 40


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
    assert sum(cell["population_policy"] == "review_gap" for cell in result.cells) == 40


@pytest.mark.m20
def test_generated_review_renders_structured_math_for_humans() -> None:
    result = build_generated_document_cells(ROOT, 2025, "form_1040_2025")
    line_22 = next(item for item in result.cells if item["official_ref"] == "22")
    assert line_22["expression"]["text"] == "line 22 = line 18 - line 21"
    assert "node_id" not in line_22["expression"]["text"]
    assert "addend" not in line_22["expression"]["text"]
    schema = json.loads((ROOT / "schemas" / "review_expression.schema.json").read_text(encoding="utf-8"))
    for cell in result.cells:
        jsonschema.validate(cell["expression"], schema)
