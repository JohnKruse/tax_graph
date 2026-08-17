"""M20-S126 guards for start-byte section identity and local owner rejection."""

from __future__ import annotations

from pathlib import Path

import pytest

from pilot.model_instruction_segmenter import (
    build_frame_from_fixture,
    build_model_frame,
    manifest_owner_document_ids,
)


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]
RAW_1040 = ROOT / ".cache" / "raw" / "2025" / "instructions_form_1040_2025.txt"
LIVE_1040 = ROOT / "pilot" / "fixtures" / "instruction_segmenter_live_1040.json"


def test_live_1040_deduplicates_heading_variants_by_start_byte() -> None:
    """The paid 1040 recording tiles after duplicate heading markup collapses."""
    if not RAW_1040.exists():
        pytest.skip("acquired 2025 Form 1040 instructions are not present")

    frame = build_frame_from_fixture(
        RAW_1040,
        source_document_id="instructions_form_1040_2025",
        fixture_path=LIVE_1040,
        allowed_document_ids=manifest_owner_document_ids(
            ROOT,
            source_document_id="instructions_form_1040_2025",
        ),
        root=ROOT,
    )

    assert len(frame.sections) == 586
    assert frame.coverage["response_section_count"] == 670
    assert len(frame.coverage["rejected_sections"]) == 18
    assert frame.coverage["owner_conflict_count"] == 0
    assert frame.coverage["chapter_owner_disagreement_count"] == 0
    assert frame.coverage["reconciles_to_file_size"] is True
    assert frame.sections[0].start_byte == 0
    assert frame.sections[-1].end_byte == len(RAW_1040.read_bytes())
    assert len({section.start_byte for section in frame.sections}) == len(frame.sections)

    line_12d = [section for section in frame.sections if section.start_byte == 140474]
    assert len(line_12d) == 1
    assert line_12d[0].heading == "### Line 12d"
    assert line_12d[0].end_byte > line_12d[0].start_byte


def test_owner_disagreement_is_rejected_locally_and_neighbors_still_tile() -> None:
    """Conflicting owners at one start byte do not abort the surrounding frame."""
    source = b"# One\nfirst body\n# Two\nsecond body\n# Three\nthird body\n"
    two_start = source.index(b"# Two")
    three_start = source.index(b"# Three")
    responses = [
        {
            "window_index": 0,
            "window_start_byte": 0,
            "window_end_byte": len(source),
            "response": {
                "sections": [
                    {
                        "heading": "# One",
                        "level": 1,
                        "start_byte": 0,
                        "end_byte": two_start,
                        "document_id": "form_a_2025",
                        "governs": ["1"],
                    },
                    {
                        "heading": "# Two",
                        "level": 1,
                        "start_byte": two_start,
                        "end_byte": three_start,
                        "document_id": "form_a_2025",
                        "governs": ["2"],
                    },
                ]
            },
        },
        {
            "window_index": 1,
            "window_start_byte": two_start,
            "window_end_byte": len(source),
            "response": {
                "sections": [
                    {
                        "heading": "# Two",
                        "level": 1,
                        "start_byte": two_start,
                        "end_byte": three_start,
                        "document_id": "form_b_2025",
                        "governs": ["2"],
                    },
                    {
                        "heading": "# Three",
                        "level": 1,
                        "start_byte": three_start,
                        "end_byte": len(source),
                        "document_id": "form_b_2025",
                        "governs": ["3"],
                    },
                ]
            },
        },
    ]

    frame = build_model_frame(
        source.decode("utf-8"),
        source_document_id="instructions_booklet_2025",
        responses=responses,
        allowed_document_ids={"form_a_2025", "form_b_2025"},
    )

    assert [section.heading for section in frame.sections] == ["# One", "# Three"]
    assert frame.coverage["owner_conflict_count"] == 1
    assert frame.coverage["reconciles_to_file_size"] is True
    rejected = frame.coverage["rejected_sections"]
    assert len(rejected) == 1
    assert rejected[0]["start_byte"] == two_start
    assert rejected[0]["reason"] == "overlapping_document_id_conflict"
