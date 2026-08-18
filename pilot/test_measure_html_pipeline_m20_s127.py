"""M20-S127 guards for the offline IRS HTML measurement."""

from __future__ import annotations

from pathlib import Path

import pytest

from pilot.measure_html_pipeline_m20_s127 import BOOKLET_IDS, measure_corpus


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]


def test_all_eight_html_booklets_hold_structural_invariants() -> None:
    """Every acquired booklet yields non-empty, source-offset HTML structure."""
    report = measure_corpus(ROOT)

    assert report["summary"]["booklet_count"] == 8
    assert set(report["booklets"]) == set(BOOKLET_IDS)
    assert report["summary"]["structural_invariants_hold"] is True
    for booklet in report["booklets"].values():
        invariants = booklet["structural_invariants"]
        assert invariants["anchor_ids_unique"] is True
        assert invariants["toc_targets_exist"] is True
        assert invariants["section_offsets_valid"] is True
        assert invariants["sections_nonempty"] is True
        assert booklet["inline_headings"]
        assert booklet["role_headings"]
        assert booklet["toc_entries"]


def test_three_arm_report_covers_all_cells_and_marks_model_availability() -> None:
    """The report keeps unavailable paid recordings distinct from zero scores."""
    report = measure_corpus(ROOT)

    assert report["summary"]["document_count"] == 12
    assert report["summary"]["cell_count"] == 449
    assert set(report["documents"]) == {
        "form_1040_2025",
        "form_1116_2025",
        "form_2441_2025",
        "form_6251_2025",
        "form_8949_2025",
        "schedule_1_2025",
        "schedule_1a_2025",
        "schedule_2_2025",
        "schedule_3_2025",
        "schedule_a_2025",
        "schedule_b_2025",
        "schedule_d_2025",
    }

    assert report["documents"]["schedule_b_2025"]["arms"]["pdf_model"]["available"] is True
    assert report["documents"]["schedule_b_2025"]["arms"]["html_deterministic"]["available"] is True
    assert report["documents"]["form_1116_2025"]["arms"]["pdf_model"]["available"] is False


def test_first_eight_disagreements_include_each_answer_and_source_quotes() -> None:
    """Disagreements compare arm answers, and available matches carry source text."""
    report = measure_corpus(ROOT)
    disagreements = report["disagreements"]

    assert len(disagreements) >= 8
    for item in disagreements[:8]:
        states = item["answer_states"]
        comparable_states = {
            value for value in states.values() if value != "unavailable"
        }
        assert len(comparable_states) > 1
        assert item["line"]
        for matches in item["arms"].values():
            if matches:
                assert all(match["quote"].strip() for match in matches)
