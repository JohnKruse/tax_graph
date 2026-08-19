"""M20-S144 tests for run-in-aware instruction ownership."""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench import generated_review
from workbench.generated_review import build_generated_document_cells


ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    not (ROOT / "graph" / "2025" / "_drafts").exists(),
    reason="live review drafts are required: fresh checkouts carry no _drafts",
)


@pytest.mark.m20
def test_instruction_span_index_uses_run_in_width_for_the_current_line() -> None:
    spans = {
        "span_family": {
            "span_id": "span_family",
            "document_id": "instructions_form_1040_2025",
            "relationship": "instructions",
            "owner_lines": ["17a", "17b", "17z"],
            "text": (
                "## Lines 17a Through 17z\n\n"
                "**Line 17z.** List the type and amount of tax.\n"
            ),
        },
        "span_heading": {
            "span_id": "span_heading",
            "document_id": "instructions_form_1040_2025",
            "relationship": "instructions",
            "owner_lines": ["17z"],
            "text": "#### Lines 17z",
        },
    }

    index = generated_review._instruction_span_index(spans)

    assert index["17z"] == ["span_family", "span_heading"]
    assert index["17a"] == ["span_family"]


@pytest.mark.m20
def test_instruction_span_index_keeps_unmatched_foreign_coverage() -> None:
    spans = {
        "span_local": {
            "span_id": "span_local",
            "document_id": "instructions_form_1040_2025",
            "owner_document_id": "form_1040_2025",
            "relationship": "instructions",
            "owner_lines": ["1"],
            "text": "## Line 1\n\nEnter the amount.",
        },
        "span_foreign_competing": {
            "span_id": "span_foreign_competing",
            "document_id": "instructions_form_1040_2025",
            "owner_document_id": "schedule_3_2025",
            "relationship": "instructions",
            "owner_lines": ["1"],
            "text": "**Line 1.** Foreign form context.",
        },
        "span_foreign_only": {
            "span_id": "span_foreign_only",
            "document_id": "instructions_form_1040_2025",
            "owner_document_id": "schedule_3_2025",
            "relationship": "instructions",
            "owner_lines": ["2"],
            "text": "**Line 2.** Foreign-only context.",
        },
    }

    index = generated_review._instruction_span_index(
        spans,
        owner_document_id="form_1040_2025",
        retain_foreign_owner_spans=True,
    )

    assert index["1"] == ["span_local"]
    assert index["2"] == ["span_foreign_only"]


@pytest.mark.m20
def test_real_corpus_run_in_candidates_project_line_own_text() -> None:
    """Every live run-in candidate has line-owned primary text."""
    for document_id in sorted(generated_review.GENERATED_REVIEW_DOCUMENTS):
        draft = generated_review._load_draft(ROOT, 2025, document_id)
        spans = generated_review._span_index(draft["candidate_spans"])
        owner_document_id = (
            document_id
            if document_id == "form_1040_2025"
            or document_id in {"schedule_2_2025", "schedule_3_2025"}
            else None
        )
        index = generated_review._instruction_span_index(
            spans,
            owner_document_id=owner_document_id,
            retain_foreign_owner_spans=document_id == "form_1040_2025",
        )
        cells = build_generated_document_cells(ROOT, 2025, document_id).cells
        by_anchor: dict[str, list[dict[str, object]]] = {}
        for cell in cells:
            anchor = str(cell.get("official_ref") or "").lower()
            if anchor:
                by_anchor.setdefault(anchor, []).append(cell)
        for line, candidate_ids in index.items():
            run_in_ids = [
                span_id
                for span_id in candidate_ids
                if line in generated_review._instruction_run_in_segments(
                    str(spans[span_id].get("text") or "")
                )
            ]
            if not run_in_ids:
                continue
            generated_cells = [
                cell
                for cell in by_anchor.get(line, [])
                if str(cell.get("generated_target_cell_id") or "").endswith(
                    f"_line_{line}"
                )
            ]
            if not generated_cells:
                # A parent instruction heading such as Form 1040 line 6 can
                # have a run-in span without being a physical review cell.
                continue
            for cell in generated_cells:
                citations = cell["instruction_citations"]
                assert citations, (
                    f"run-in candidate has no projected citation: {document_id} {line}"
                )
                primary = citations[0]
                primary_source = str(
                    primary.get("source_span_id") or primary.get("citation_id") or ""
                )
                owner_only = {
                    span_id
                    for span_id in candidate_ids
                    if {
                        str(value).strip().lower()
                        for value in spans[span_id].get("owner_lines", []) or []
                    }
                    == {line}
                }
                assert (
                    primary_source in run_in_ids
                    and primary.get("projection") == "run_in_line"
                ) or primary_source in owner_only, (
                    f"{document_id} {line}: candidates={candidate_ids}, "
                    f"run_in={run_in_ids}, owner_only={owner_only}, "
                    f"primary={primary_source}"
                )

    form_1040 = build_generated_document_cells(ROOT, 2025, "form_1040_2025").cells
    line_6a = next(
        cell
        for cell in form_1040
        if str(cell.get("official_ref") or "").lower() == "6a"
        and str(cell.get("generated_target_cell_id") or "").endswith("_line_6a")
    )
    assert line_6a["instruction_citations"][0]["citation_id"] == (
        "span_instructions_form_1040_2025_section_0025"
    )
    assert "Social Security Benefits" in line_6a["instruction_citations"][0]["quoted_text"]
