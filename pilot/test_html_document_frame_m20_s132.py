"""M20-S132 guards for the three-way HTML ownership rule."""

from __future__ import annotations

from pathlib import Path

import pytest

from pilot.html_document_frame_m20_s129 import BOOKLET_IDS
from pilot.html_document_frame_m20_s132 import measure_corpus
from pilot.html_document_frame_m20_s132 import parse_html_document_frame


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / ".cache" / "raw" / "2025"


def test_all_eight_frames_keep_s130_tiling_and_toc_invariants() -> None:
    """Ownership-only reassignment cannot change the accepted byte frame."""
    for source_document_id in BOOKLET_IDS:
        frame = parse_html_document_frame(
            (RAW_ROOT / f"{source_document_id}.html").read_text(encoding="utf-8"),
            source_document_id=source_document_id,
            root=ROOT,
        )
        for key in (
            "content_region_valid",
            "sections_tile_content",
            "section_offsets_valid",
            "section_source_resolves",
            "sections_nonempty",
            "no_toc_sections",
            "anchor_ids_unique",
            "anchor_ranges_valid",
            "ancestor_chain_present",
        ):
            assert frame.structural_invariants[key] is True


def test_real_sections_prove_all_three_ownership_cases() -> None:
    """The worksheet row, foreign worksheet row, and worked example name each case."""
    schedule_d = parse_html_document_frame(
        (RAW_ROOT / "instructions_schedule_d_2025.html").read_text(encoding="utf-8"),
        source_document_id="instructions_schedule_d_2025",
        root=ROOT,
    )
    schedule_d_by_heading = {section.heading: section for section in schedule_d.sections}

    # Case 1: the nearest worksheet naming ancestor owns the line section.
    assert schedule_d_by_heading["Line 4."].owner_document_id == (
        "unrecaptured_section_1250_gain_worksheet_2025"
    )
    assert schedule_d_by_heading["Line 12."].owner_document_id == (
        "unrecaptured_section_1250_gain_worksheet_2025"
    )

    form_1116 = parse_html_document_frame(
        (RAW_ROOT / "instructions_form_1116_2025.html").read_text(encoding="utf-8"),
        source_document_id="instructions_form_1116_2025",
        root=ROOT,
    )
    # Case 2: the foreign worksheet naming ancestor still rejects its 13 rows.
    rejected_rows = [
        section
        for section in form_1116.sections
        if section.rejected and section.line_tokens
    ]
    assert len(rejected_rows) == 13
    assert all(section.owner_document_id is None for section in rejected_rows)
    assert all(
        any(
            "Qualified Dividends" in title or "Schedule D Tax Worksheet" in title
            for title in section.ancestor_chain
        )
        for section in rejected_rows
    )

    worked_examples = {
        "Example 1-Basis Reported to the IRS",
        "Example 2-Basis Not Reported to the IRS",
        "Example 3-Adjustment",
        "Example 1-gain.",
        "Example 2-loss.",
        "Example 3-adjustment.",
    }
    # Case 3: these line-heading children have no naming ancestor; the line
    # headings' incidental Form 8949 mentions do not create one.
    assert worked_examples <= set(schedule_d_by_heading)
    assert all(
        schedule_d_by_heading[heading].owner_document_id == "schedule_d_2025"
        and not schedule_d_by_heading[heading].rejected
        for heading in worked_examples
    )


def test_report_shows_rejections_fall_without_moving_line_scores() -> None:
    """S132 reports ownership movement and protects the S130 score baseline."""
    report = measure_corpus(ROOT)

    assert report["round"] == "M20-S132"
    assert report["summary"]["booklet_count"] == 8
    assert report["summary"]["structural_invariants_hold"] is True
    assert report["booklets"]["instructions_schedule_d_2025"]["rejected_before"] == 6
    assert report["booklets"]["instructions_schedule_d_2025"]["rejected_after"] == 0
    assert report["booklets"]["instructions_form_1116_2025"]["rejected_before"] == 21
    assert report["booklets"]["instructions_form_1116_2025"]["rejected_after"] == 21

    assert report["summary"]["total_rejected_after"] < report["summary"]["total_rejected_before"]
    assert report["documents"]
    for document in report["documents"].values():
        assert document["line_anchored_before"] == document["line_anchored"]
        assert document["cells"] >= document["line_anchored"] >= 0
