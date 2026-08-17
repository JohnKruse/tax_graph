"""M20-S124 guards for chapter-scoped instruction segmentation windows."""

from __future__ import annotations

from pathlib import Path

import pytest

from pilot.model_instruction_segmenter import (
    SourceChapter,
    build_frame_from_fixture,
    build_model_frame,
    build_source_chapters,
    build_source_windows,
    manifest_owner_document_ids,
)


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]
RAW_1040 = ROOT / ".cache" / "raw" / "2025" / "instructions_form_1040_2025.txt"
LIVE_FIXTURE = ROOT / "pilot" / "fixtures" / "instruction_segmenter_live_recordings.json"


def test_real_1040_chapters_pin_raw_byte_conversion() -> None:
    """The five deterministic context chapters are measured in raw bytes."""
    if not RAW_1040.exists():
        pytest.skip("acquired 2025 Form 1040 instructions are not present")

    source_bytes = RAW_1040.read_bytes()
    normalized_text = source_bytes.decode("utf-8").replace("\r\n", "\n")
    chapters = build_source_chapters(
        source_bytes,
        source_document_id="instructions_form_1040_2025",
        year="2025",
    )

    assert len(source_bytes) == 683265
    assert len(normalized_text) == 675580
    assert [chapter.document_id for chapter in chapters] == [
        "form_1040_2025",
        "schedule_1_2025",
        "schedule_1a_2025",
        "schedule_2_2025",
        "schedule_3_2025",
    ]
    assert [chapter.start_byte for chapter in chapters] == [
        0,
        513738,
        566452,
        619843,
        639893,
    ]
    assert chapters[-1].end_byte == len(source_bytes)


def test_1040_windows_never_cross_chapters_and_tile_boundaries() -> None:
    """Chapter-local overlap remains, but adjacent chapters meet exactly."""
    if not RAW_1040.exists():
        pytest.skip("acquired 2025 Form 1040 instructions are not present")

    source_bytes = RAW_1040.read_bytes()
    chapters = build_source_chapters(
        source_bytes,
        source_document_id="instructions_form_1040_2025",
        year="2025",
    )
    windows = build_source_windows(
        source_bytes,
        max_window_bytes=100000,
        overlap_bytes=10000,
        chapters=chapters,
    )

    assert windows
    for window in windows:
        matches = [
            chapter
            for chapter in chapters
            if chapter.start_byte <= window.start_byte
            and window.end_byte <= chapter.end_byte
        ]
        assert len(matches) == 1
        assert window.chapter_index == matches[0].index
        assert window.chapter_document_id == matches[0].document_id
    for previous, current in zip(windows, windows[1:]):
        if previous.chapter_index != current.chapter_index:
            assert previous.end_byte == current.start_byte
    for chapter in chapters:
        chapter_windows = [
            window for window in windows if window.chapter_index == chapter.index
        ]
        assert chapter_windows[0].start_byte == chapter.start_byte
        assert chapter_windows[-1].end_byte == chapter.end_byte


@pytest.mark.parametrize(
    ("source_document_id", "expected_sections"),
    (
        ("instructions_schedule_b_2025", 29),
        ("instructions_schedule_d_2025", 93),
    ),
)
def test_single_chapter_booklets_keep_the_s123_window_coordinates(
    source_document_id: str,
    expected_sections: int,
) -> None:
    """Schedule B and D remain one chapter and replay unchanged."""
    source_path = ROOT / ".cache" / "raw" / "2025" / f"{source_document_id}.txt"
    if not source_path.exists():
        pytest.skip(f"acquired source is not present: {source_document_id}")

    source_bytes = source_path.read_bytes()
    chapters = build_source_chapters(
        source_bytes,
        source_document_id=source_document_id,
        year="2025",
    )
    chapter_windows = build_source_windows(source_bytes, chapters=chapters)
    legacy_windows = build_source_windows(source_bytes)
    assert len(chapters) == 1
    assert [(item.start_byte, item.end_byte) for item in chapter_windows] == [
        (item.start_byte, item.end_byte) for item in legacy_windows
    ]

    frame = build_frame_from_fixture(
        source_path,
        source_document_id=source_document_id,
        fixture_path=LIVE_FIXTURE,
        allowed_document_ids=manifest_owner_document_ids(
            ROOT,
            source_document_id=source_document_id,
        ),
    )
    assert len(frame.sections) == expected_sections
    assert frame.coverage["chapter_count"] == 1
    assert frame.coverage["chapter_owner_disagreement_count"] == 0
    assert frame.coverage["rejected_sections"] == []
    assert frame.coverage["reconciles_to_file_size"] is True


def test_foreign_chapter_form_claim_is_rejected_locally_and_source_still_tiles() -> None:
    """A wrong form owner is disclosed without losing neighboring coverage."""
    source = b"# One\nform A body\n# Worksheet\nworksheet body\n# Two\nform B body\n"
    two_start = source.index(b"# Two")
    worksheet_start = source.index(b"# Worksheet")
    chapters = (
        SourceChapter(1, "form_a_2025", 0, two_start),
        SourceChapter(2, "form_b_2025", two_start, len(source)),
    )
    responses = [
        {
            "window_index": 0,
            "window_start_byte": 0,
            "window_end_byte": two_start,
            "chapter_index": 1,
            "chapter_document_id": "form_a_2025",
            "response": {
                "sections": [
                    {
                        "heading": "# One",
                        "level": 1,
                        "start_byte": 0,
                        "end_byte": two_start,
                        "document_id": "form_b_2025",
                        "governs": [],
                    },
                    {
                        "heading": "# One",
                        "level": 1,
                        "start_byte": 0,
                        "end_byte": two_start,
                        "document_id": "form_a_2025",
                        "governs": [],
                    },
                    {
                        "heading": "# Worksheet",
                        "level": 1,
                        "start_byte": worksheet_start,
                        "end_byte": two_start,
                        "document_id": "worksheet_2025",
                        "governs": [],
                    },
                ]
            },
        },
        {
            "window_index": 1,
            "window_start_byte": two_start,
            "window_end_byte": len(source),
            "chapter_index": 2,
            "chapter_document_id": "form_b_2025",
            "response": {
                "sections": [
                    {
                        "heading": "# Two",
                        "level": 1,
                        "start_byte": two_start,
                        "end_byte": len(source),
                        "document_id": "form_b_2025",
                        "governs": [],
                    }
                ]
            },
        },
    ]

    frame = build_model_frame(
        source.decode("utf-8"),
        source_document_id="instructions_booklet_2025",
        responses=responses,
        allowed_document_ids={"form_a_2025", "form_b_2025", "worksheet_2025"},
        chapters=chapters,
        worksheet_document_ids={"worksheet_2025"},
    )

    assert [section.heading for section in frame.sections] == [
        "# One",
        "# Worksheet",
        "# Two",
    ]
    assert [section.document_id for section in frame.sections] == [
        "form_a_2025",
        "worksheet_2025",
        "form_b_2025",
    ]
    assert frame.coverage["chapter_owner_disagreement_count"] == 1
    assert [
        item["reason"] for item in frame.coverage["rejected_sections"]
    ] == ["chapter_owner_disagreement"]
    assert frame.coverage["reconciles_to_file_size"] is True
