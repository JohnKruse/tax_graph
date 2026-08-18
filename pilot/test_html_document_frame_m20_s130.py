"""M20-S130 guards for the observed semantic HTML heading expansion."""

from __future__ import annotations

from pathlib import Path

import pytest

from pilot.html_document_frame_m20_s129 import BOOKLET_IDS
from pilot.html_document_frame_m20_s130 import measure_corpus
from pilot.html_document_frame_m20_s130 import parse_html_document_frame


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / ".cache" / "raw" / "2025"


def test_all_eight_widened_frames_still_tile_and_resolve() -> None:
    """Observed title markup cannot weaken the S129 byte-frame invariants."""
    for source_document_id in BOOKLET_IDS:
        html = (RAW_ROOT / f"{source_document_id}.html").read_text(encoding="utf-8")
        frame = parse_html_document_frame(
            html,
            source_document_id=source_document_id,
            root=ROOT,
        )

        assert frame.sections
        assert frame.content_region_source == "div.book"
        assert frame.offset_coordinate_space == "utf8_bytes_of_acquired_html"
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
        assert frame.sections[0].start_offset == frame.content_start_offset
        assert frame.sections[-1].end_offset == frame.content_end_offset


def test_observed_title_markup_creates_bounded_sections() -> None:
    """The real 1040 uses title roles and p.title for non-line sections."""
    frame = parse_html_document_frame(
        (RAW_ROOT / "instructions_form_1040_2025.html").read_text(encoding="utf-8"),
        source_document_id="instructions_form_1040_2025",
        root=ROOT,
    )
    headings = {section.heading for section in frame.sections}

    assert "Chart A-For Most People" in headings
    assert "Step 1. Do You Have a Qualifying Child?" in headings
    assert "2025 Tax Computation Worksheet-Line 16" in headings
    assert "List of Tax Topics" in headings


def test_lines_6a_and_6b_is_owned_by_form_1040() -> None:
    """The line heading is a role-hd2 section despite OCR punctuation drift."""
    frame = parse_html_document_frame(
        (RAW_ROOT / "instructions_form_1040_2025.html").read_text(encoding="utf-8"),
        source_document_id="instructions_form_1040_2025",
        root=ROOT,
    )
    matches = [
        section
        for section in frame.sections
        if {"6a", "6b"}.issubset(section.line_tokens)
        and "Social Security Benefits" in section.heading
    ]

    assert len(matches) == 1
    assert matches[0].owner_document_id == "form_1040_2025"
    assert matches[0].source_text


def test_s128_ownership_and_rejection_survive_widening() -> None:
    """Extra headings do not reassign worksheet content to the booklet form."""
    schedule_d = parse_html_document_frame(
        (RAW_ROOT / "instructions_schedule_d_2025.html").read_text(encoding="utf-8"),
        source_document_id="instructions_schedule_d_2025",
        root=ROOT,
    )
    schedule_d_lines = {
        token: section
        for section in schedule_d.sections
        if not section.rejected
        for token in section.line_tokens
    }
    for token in ("4", "12"):
        assert schedule_d_lines[token].owner_document_id == (
            "unrecaptured_section_1250_gain_worksheet_2025"
        )

    form_1116 = parse_html_document_frame(
        (RAW_ROOT / "instructions_form_1116_2025.html").read_text(encoding="utf-8"),
        source_document_id="instructions_form_1116_2025",
        root=ROOT,
    )
    rejected_line_sections = [
        section
        for section in form_1116.sections
        if section.rejected and section.line_tokens
    ]
    assert len(rejected_line_sections) >= 13
    assert all(section.owner_document_id is None for section in rejected_line_sections)


def test_generic_bold_prose_is_not_promoted_to_a_heading() -> None:
    """The observed bold class is not a license to section every bold run."""
    html = """
    <div class="book">
      <p><span class="bold"><strong>Bold prose.</strong></span> More prose.</p>
      <p class="title">A real title.</p>
      <p>Body text.</p>
    </div>
    """
    frame = parse_html_document_frame(
        html,
        source_document_id="instructions_form_1040_2025",
        root=ROOT,
        owner_document_ids={"form_1040_2025"},
        worksheet_document_ids=set(),
        all_manifest_document_ids={"form_1040_2025"},
    )

    assert "A real title." in {section.heading for section in frame.sections}
    assert "Bold prose." not in {section.heading for section in frame.sections}
    assert frame.structural_invariants["sections_tile_content"] is True


def test_s130_report_contains_gap_and_per_document_line_scores() -> None:
    """The report exposes the remaining gap without turning a score into a guard."""
    report = measure_corpus(ROOT)

    assert report["round"] == "M20-S130"
    assert report["summary"]["booklet_count"] == len(BOOKLET_IDS)
    assert report["summary"]["structural_invariants_hold"] is True
    assert report["gap"]["baseline_model_only_non_page"] > 0
    assert report["gap"]["remaining_unsectioned"] >= 0
    assert report["gap"]["remaining_unsectioned"] <= report["gap"]["baseline_model_only_non_page"]
    assert report["documents"]
    for item in report["documents"].values():
        assert item["cells"] >= item["line_anchored"] >= 0
