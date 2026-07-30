"""M20-S15 tests for draft-only generated review projection."""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench.generated_review import build_generated_document_cells


ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    not (ROOT / "graph" / "2025" / "_drafts").exists(),
    reason="live review drafts are required: fresh checkouts carry no _drafts",
)


@pytest.mark.m20
def test_generated_review_projects_only_formula_cells_with_provenance() -> None:
    expected = {
        "form_1040_2025": 17,
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


@pytest.mark.m20
def test_generated_review_keeps_form_and_instruction_slots_separate() -> None:
    result = build_generated_document_cells(ROOT, 2025, "form_1040_2025")
    cell = next(item for item in result.cells if item["official_ref"] == "1z")
    assert isinstance(cell["expression"], dict)
    assert "operation" in cell["expression"]
    assert isinstance(cell["form_citations"], list)
    assert isinstance(cell["instruction_citations"], list)
    assert cell["citations"] is cell["form_citations"]
