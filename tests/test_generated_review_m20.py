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
        "schedule_2_2025": 63,
        "schedule_3_2025": 37,
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
def test_instruction_span_index_uses_persisted_owner_lines() -> None:
    """Multiline frame spans keep their explicit line owner in the projection."""
    spans = {
        "span_line_1i": {
            "span_id": "span_line_1i",
            "document_id": "instructions_form_1040_2025",
            "relationship": "instructions",
            "owner_lines": ["1i"],
            "text": "## Line 1i\n\n### Nontaxable Combat Pay Election\n\nEnter the amount.",
        },
        "span_legacy": {
            "span_id": "span_legacy",
            "document_id": "instructions_form_1040_2025",
            "relationship": "instructions",
            "text": "## Line 2a\n\n### Tax-Exempt Interest\n\nEnter the amount.",
        },
    }

    index = generated_review._instruction_span_index(spans)

    assert index["1i"] == ["span_line_1i"]
    assert index["2a"] == ["span_legacy"]


@pytest.mark.m20
def test_instruction_span_index_respects_shared_booklet_owner() -> None:
    """Shared-booklet line tokens stay attached to their owning form."""
    spans = {
        "span_schedule_2": {
            "span_id": "span_schedule_2",
            "document_id": "instructions_form_1040_2025",
            "owner_document_id": "schedule_2_2025",
            "relationship": "instructions",
            "owner_lines": ["17a", "17b"],
            "text": "## Lines 17a Through 17b\n\nEnter the amount.",
        },
        "span_schedule_3": {
            "span_id": "span_schedule_3",
            "document_id": "instructions_form_1040_2025",
            "owner_document_id": "schedule_3_2025",
            "relationship": "instructions",
            "owner_lines": ["17a", "17b"],
            "text": "## Lines 17a Through 17b\n\nEnter the amount.",
        },
    }

    schedule_2 = generated_review._instruction_span_index(
        spans,
        owner_document_id="schedule_2_2025",
    )
    schedule_3 = generated_review._instruction_span_index(
        spans,
        owner_document_id="schedule_3_2025",
    )

    assert schedule_2["17b"] == ["span_schedule_2"]
    assert schedule_3["17b"] == ["span_schedule_3"]


@pytest.mark.m20
def test_generated_review_projects_all_multiline_schedule_instruction_owners() -> None:
    """Shared line-family spans reach every owning Schedule 2 and 3 cell."""
    expected = {
        "schedule_2_2025": {f"17{letter}" for letter in "bcdefghijklmnopq"} | {"17z"},
        "schedule_3_2025": {f"6{letter}" for letter in "bcdefghijklm"},
    }
    for document_id, anchors in expected.items():
        cells = build_generated_document_cells(ROOT, 2025, document_id).cells
        by_anchor = {
            str(cell.get("official_ref") or "").lower(): cell
            for cell in cells
        }
        assert all(by_anchor[anchor]["instruction_citations"] for anchor in anchors)


@pytest.mark.m20
def test_generated_review_s142_splits_run_labels_and_s143_prioritizes_narrow_owners() -> None:
    """Run-in labels narrow packets before family spans are used as context."""
    schedule_1 = build_generated_document_cells(ROOT, 2025, "schedule_1_2025").cells
    line_24a = next(item for item in schedule_1 if item["official_ref"] == "24a")
    line_24f = next(item for item in schedule_1 if item["official_ref"] == "24f")
    line_8a = next(item for item in schedule_1 if item["official_ref"] == "8a")
    line_8b = next(item for item in schedule_1 if item["official_ref"] == "8b")

    citation_24a = line_24a["instruction_citations"][0]
    citation_24f = line_24f["instruction_citations"][0]
    citation_8a = line_8a["instruction_citations"][0]
    citation_8b = line_8b["instruction_citations"][0]
    assert citation_24a["citation_id"].endswith("__line_24a")
    assert citation_24a["quoted_text"].startswith("##### Line 24a")
    assert "##### Line 24b" not in citation_24a["quoted_text"]
    assert citation_24f["citation_id"].endswith("__line_24f")
    assert citation_24f["quoted_text"].startswith("# **Line 24f**")
    assert citation_8a["citation_id"].endswith("__line_8a")
    assert citation_8b["citation_id"].endswith("__line_8b")
    assert any(
        item["citation_id"] == "span_instructions_form_1040_2025_section_0067"
        for item in line_8a["instruction_citations"]
    )
    assert any(
        item["citation_id"] == "span_instructions_form_1040_2025_section_0067"
        for item in line_8b["instruction_citations"]
    )

    schedule_2 = build_generated_document_cells(ROOT, 2025, "schedule_2_2025").cells
    for anchor in ("17b", "17q", "17z"):
        citation = next(
            item for item in schedule_2 if item["official_ref"] == anchor
        )["instruction_citations"][0]
        assert citation["citation_id"].endswith(f"__line_{anchor}")
        assert f"**Line {anchor}." in citation["quoted_text"]

    schedule_3 = build_generated_document_cells(ROOT, 2025, "schedule_3_2025").cells
    for anchor in ("6b", "6m"):
        citation = next(
            item for item in schedule_3 if item["official_ref"] == anchor
        )["instruction_citations"][0]
        assert citation["citation_id"].endswith(f"__line_{anchor}")
        assert f"**Line {anchor}." in citation["quoted_text"]


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
