"""M20-S128 guards for the containment-owned HTML section frame."""

from __future__ import annotations

from pathlib import Path

import pytest

from pilot.html_section_frame_m20_s128 import BOOKLET_IDS
from pilot.html_section_frame_m20_s128 import measure_corpus
from pilot.html_section_frame_m20_s128 import parse_html_section_frame


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / ".cache" / "raw" / "2025"


def test_all_eight_html_booklets_build_nonempty_byte_resolving_frames() -> None:
    """Every acquired booklet satisfies the frame's source and ancestry gates."""
    for source_document_id in BOOKLET_IDS:
        frame = parse_html_section_frame(
            (RAW_ROOT / f"{source_document_id}.html").read_text(encoding="utf-8"),
            source_document_id=source_document_id,
            root=ROOT,
        )

        assert frame.offset_coordinate_space == "utf8_bytes_of_acquired_html"
        assert frame.anchors
        assert frame.headings
        assert frame.sections
        for key in (
            "anchor_ids_unique",
            "anchor_ranges_valid",
            "section_offsets_valid",
            "section_source_resolves",
            "sections_nonempty",
            "ancestor_chain_present",
        ):
            assert frame.structural_invariants[key] is True
        assert all(section.ancestor_chain is not None for section in frame.sections)


def test_schedule_d_worksheet_lines_are_owned_by_the_containing_worksheet() -> None:
    """Containment prevents Schedule D rows from inheriting the booklet owner."""
    source_document_id = "instructions_schedule_d_2025"
    frame = parse_html_section_frame(
        (RAW_ROOT / f"{source_document_id}.html").read_text(encoding="utf-8"),
        source_document_id=source_document_id,
        root=ROOT,
    )

    by_line = {
        token: section
        for section in frame.sections
        for token in section.line_tokens
    }
    for token in ("4", "12"):
        section = by_line[token]
        assert section.owner_document_id == "unrecaptured_section_1250_gain_worksheet_2025"
        assert "Instructions for the Unrecaptured Section 1250 Gain Worksheet" in section.ancestor_chain
        assert section.anchor_id
        assert section.source_text.strip()


def test_body_anchors_are_the_index_not_dangling_toc_links() -> None:
    """A TOC href cannot create a section when its body anchor is absent."""
    html = """
    <div class="toc"><a class="text-overflow" href="#en_US_2025_publink_missing">Line 99.</a></div>
    <div class="section" id="en_US_2025_publink_real">
      <h4 class="title role-hd1"><a name="en_US_2025_publink_heading"></a>Instructions for Form 1040</h4>
      <p class="inlinehd"><strong>Line 1.</strong></p><p>Real text.</p>
    </div>
    """
    frame = parse_html_section_frame(
        html,
        source_document_id="instructions_form_1040_2025",
        root=ROOT,
        owner_document_ids={"form_1040_2025"},
        worksheet_document_ids=set(),
        all_manifest_document_ids={"form_1040_2025"},
    )

    assert "en_US_2025_publink_missing" not in {item.anchor_id for item in frame.anchors}
    assert len(frame.sections) == 1
    assert frame.sections[0].anchor_id == "en_US_2025_publink_real"


def test_outside_manifest_owner_is_rejected_locally() -> None:
    """A foreign form named by an ancestor does not abort neighboring sections."""
    html = """
    <div class="section">
      <h4 class="title role-hd1"><a name="en_US_2025_publink_root"></a>Instructions for Form 1040</h4>
      <h4 class="title role-hd2"><a name="en_US_2025_publink_foreign"></a>Instructions for Form 9999</h4>
      <div class="section" id="en_US_2025_publink_line">
        <p class="inlinehd"><strong>Line 1.</strong></p><p>Foreign text.</p>
      </div>
    </div>
    """
    frame = parse_html_section_frame(
        html,
        source_document_id="instructions_form_1040_2025",
        root=ROOT,
        owner_document_ids={"form_1040_2025"},
        worksheet_document_ids=set(),
        all_manifest_document_ids={"form_1040_2025"},
    )

    assert frame.sections == ()
    assert len(frame.rejected_sections) == 1
    assert frame.rejected_sections[0].reason == "foreign_owner_rejected"
    assert frame.rejected_sections[0].foreign_document_id == "form_9999"


def test_corpus_report_separates_the_three_score_components() -> None:
    """Corpus scoring exposes line, topic, and rejected-owner counts separately."""
    report = measure_corpus(ROOT)

    assert report["round"] == "M20-S128"
    assert report["summary"]["booklet_count"] == 8
    assert report["summary"]["structural_invariants_hold"] is True
    assert report["documents"]
    for document in report["documents"].values():
        assert set(document) >= {
            "line_anchored",
            "topic_attributed",
            "foreign_owner_rejected",
            "score",
        }
        assert set(document["score"]) >= {
            "line_anchored",
            "topic_attributed",
            "foreign_owner_rejected",
        }
