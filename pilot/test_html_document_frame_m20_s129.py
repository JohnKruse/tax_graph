"""M20-S129 guards for the full-document HTML frame."""

from __future__ import annotations

from pathlib import Path

import pytest

from pilot.html_document_frame_m20_s129 import BOOKLET_IDS
from pilot.html_document_frame_m20_s129 import measure_corpus
from pilot.html_document_frame_m20_s129 import parse_html_document_frame


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / ".cache" / "raw" / "2025"


def test_all_eight_booklets_tile_their_div_book_content_region() -> None:
    """Each full frame conserves every byte in the semantic content region."""
    for source_document_id in BOOKLET_IDS:
        html = (RAW_ROOT / f"{source_document_id}.html").read_text(encoding="utf-8")
        frame = parse_html_document_frame(
            html,
            source_document_id=source_document_id,
            root=ROOT,
        )

        assert frame.content_region_source == "div.book"
        assert frame.offset_coordinate_space == "utf8_bytes_of_acquired_html"
        assert frame.content_start_offset < frame.content_end_offset
        assert frame.sections
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


def test_toc_is_outside_the_content_region_and_cannot_start_a_section() -> None:
    """A TOC link before ``div.book`` is excluded from the full frame."""
    html = """
    <div class="col-md-4"><a class="text-overflow" href="#en_US_2025_publink_missing">Line 99.</a></div>
    <div class="col-md-8"><div class="book" lang="en">
      <div class="section" id="en_US_2025_publink_real">
        <h4 class="title role-hd1"><a name="en_US_2025_publink_heading"></a>Instructions for Form 1040</h4>
        <p class="inlinehd"><strong>Line 1.</strong></p><p>Real text.</p>
      </div>
    </div></div>
    """
    frame = parse_html_document_frame(
        html,
        source_document_id="instructions_form_1040_2025",
        root=ROOT,
        owner_document_ids={"form_1040_2025"},
        worksheet_document_ids=set(),
        all_manifest_document_ids={"form_1040_2025"},
    )

    toc_offset = html.index("en_US_2025_publink_missing")
    assert toc_offset < frame.content_start_offset
    assert all("publink_missing" not in item.source_text for item in frame.sections)
    assert all(item.start_offset >= frame.content_start_offset for item in frame.sections)
    assert frame.structural_invariants["sections_tile_content"] is True


def test_foreign_owner_rejection_keeps_the_rejected_interval_in_the_tile() -> None:
    """Containment rejection remains section-local without making a byte gap."""
    html = """
    <div class="book"><div class="section">
      <h4 class="title role-hd1"><a name="en_US_2025_publink_root"></a>Instructions for Form 1040</h4>
      <h4 class="title role-hd2"><a name="en_US_2025_publink_foreign"></a>Instructions for Form 9999</h4>
      <p class="inlinehd"><strong>Line 1.</strong></p><p>Foreign text.</p>
    </div></div>
    """
    frame = parse_html_document_frame(
        html,
        source_document_id="instructions_form_1040_2025",
        root=ROOT,
        owner_document_ids={"form_1040_2025"},
        worksheet_document_ids=set(),
        all_manifest_document_ids={"form_1040_2025"},
    )

    assert len(frame.rejected_sections) == 1
    rejected = [item for item in frame.sections if item.rejected]
    assert len(rejected) == 1
    assert rejected[0].owner_document_id is None
    assert rejected[0].heading == "Line 1."
    assert any("Instructions for Form 9999" in title for title in rejected[0].ancestor_chain)
    assert frame.structural_invariants["sections_tile_content"] is True


def test_s128_ownership_survives_full_document_tiling() -> None:
    """Worksheet rows remain owned or rejected exactly as S128 established."""
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
    assert len(rejected_line_sections) == 13
    assert all(section.owner_document_id is None for section in rejected_line_sections)
    assert all(
        any("Qualified Dividends" in title for title in section.ancestor_chain)
        or any("Schedule D" in title for title in section.ancestor_chain)
        for section in rejected_line_sections
    )


def test_corpus_report_compares_full_html_frames_to_the_three_model_frames() -> None:
    """The report states model counts and text-match direction separately."""
    report = measure_corpus(ROOT)

    assert report["round"] == "M20-S129"
    assert report["summary"]["booklet_count"] == 8
    assert report["summary"]["structural_invariants_hold"] is True
    assert "normalized heading text" in report["coordinate_note"]
    comparison = report["model_comparison"]
    assert comparison["instructions_form_1040_2025"]["model_section_count"] == 586
    assert comparison["instructions_schedule_b_2025"]["model_section_count"] == 29
    assert comparison["instructions_schedule_d_2025"]["model_section_count"] == 93
    for source_document_id in (
        "instructions_form_1040_2025",
        "instructions_schedule_b_2025",
        "instructions_schedule_d_2025",
    ):
        item = comparison[source_document_id]
        assert item["available"] is True
        assert item["model_sections_with_html_text_match"] > 0
        assert item["model_sections_missed_by_html"] >= 0
        assert item["html_sections_missed_by_model"] >= 0
        assert "not a byte match" in item["match_basis"]
    assert all(
        not item["available"]
        for key, item in comparison.items()
        if key not in {
            "instructions_form_1040_2025",
            "instructions_schedule_b_2025",
            "instructions_schedule_d_2025",
        }
    )
