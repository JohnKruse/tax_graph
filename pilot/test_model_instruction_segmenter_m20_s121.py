"""M20-S121 guards for source-only model segmentation and its verifier."""

from __future__ import annotations

from pathlib import Path

import pytest

from pilot.model_instruction_segmenter import (
    ModelFrameVerificationError,
    ModelInstructionFrame,
    ModelSection,
    build_model_frame,
    build_ab_report,
    build_frame_from_fixture,
    build_source_windows,
    build_window_prompt,
    score_ab,
    segmenter_schema,
    verify_model_sections,
)


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]


def _source() -> bytes:
    """Return a small source with a seam-crossing duplicate opportunity."""
    return b"# One\nfirst body\n# Two\nsecond body\n# Three\nthird body\n"


def _section_records(source: bytes, owner: str) -> list[dict[str, object]]:
    """Build recorded response records from fixed source headings only."""
    starts = [0, source.index(b"# Two"), source.index(b"# Three")]
    ends = starts[1:] + [len(source)]
    headings = ["# One", "# Two", "# Three"]
    sections = [
        {
            "heading": heading,
            "level": 1,
            "start_byte": start,
            "end_byte": end,
            "document_id": owner,
            "governs": [str(index + 1)],
        }
        for index, (heading, start, end) in enumerate(zip(headings, starts, ends))
    ]
    windows = build_source_windows(source, max_window_bytes=38, overlap_bytes=34)
    records: list[dict[str, object]] = []
    for window in windows:
        records.append(
            {
                "window_index": window.index,
                "window_start_byte": window.start_byte,
                "window_end_byte": window.end_byte,
                "response": {
                    "sections": [
                        section
                        for section in sections
                        if window.start_byte <= int(section["start_byte"])
                        and int(section["end_byte"]) <= window.end_byte
                    ]
                },
            }
        )
    return records


def test_window_reconciliation_deduplicates_and_tiles_source() -> None:
    """Overlapping recorded calls dedupe sections and conserve every byte."""
    source = _source()
    frame = build_model_frame(
        source.decode("utf-8"),
        source_document_id="instructions_demo_2025",
        responses=_section_records(source, "demo_2025"),
    )

    assert len(frame.sections) == 3
    assert frame.coverage["response_window_count"] > 1
    assert frame.coverage["duplicate_response_sections"] > 0
    assert frame.coverage["reconciles_to_file_size"] is True
    assert frame.sections[0].start_byte == 0
    assert frame.sections[-1].end_byte == len(source)


def test_verifier_rejects_a_range_whose_claimed_text_is_fabricated() -> None:
    """A response cannot smuggle invented section text through a valid range."""
    source = _source()
    records = _section_records(source, "demo_2025")
    bad = dict(records[0])
    bad_response = dict(bad["response"])
    bad_sections = [dict(section) for section in bad_response["sections"]]
    bad_sections[0]["text"] = "invented text"
    bad_response["sections"] = bad_sections
    bad["response"] = bad_response
    with pytest.raises(ModelFrameVerificationError, match="text does not match"):
        build_model_frame(
            source.decode("utf-8"),
            source_document_id="instructions_demo_2025",
            responses=[bad, *records[1:]],
        )


def test_verifier_rejects_a_heading_not_at_the_claimed_source_offset() -> None:
    """A real source range is not enough when the heading witness is wrong."""
    source = _source()
    records = _section_records(source, "demo_2025")
    bad = dict(records[0])
    bad_response = dict(bad["response"])
    bad_sections = [dict(section) for section in bad_response["sections"]]
    bad_sections[0]["heading"] = "# Invented"
    bad_response["sections"] = bad_sections
    bad["response"] = bad_response
    with pytest.raises(ModelFrameVerificationError, match="heading mismatch"):
        build_model_frame(
            source.decode("utf-8"),
            source_document_id="instructions_demo_2025",
            responses=[bad, *records[1:]],
        )


def test_prompt_contains_source_but_no_cell_conditioning() -> None:
    """The model prompt names only source coordinates and segmentation rules."""
    source = _source()
    window = build_source_windows(source, max_window_bytes=100, overlap_bytes=10)[0]
    prompt = build_window_prompt(
        source,
        window,
        source_document_id="instructions_demo_2025",
        prompt_text="Segment source text into sections.",
    )
    assert "# One" in prompt
    assert "[[source_byte=0]]" in prompt
    assert "BEGIN ACQUIRED SOURCE" in prompt
    assert "cell_id" not in prompt
    assert "unmatched list" not in prompt


def test_schema_has_closed_required_output_contract() -> None:
    """The pilot response schema requires every section field."""
    schema = segmenter_schema()
    item = schema["properties"]["sections"]["items"]
    assert item["additionalProperties"] is False
    assert set(item["required"]) == {
        "heading",
        "level",
        "start_byte",
        "end_byte",
        "document_id",
        "governs",
    }


def test_scorer_reports_gains_and_wrong_owner_after_segmentation() -> None:
    """Ownership is scored only after the source-backed frame is verified."""
    frame = ModelInstructionFrame(
        schema_version=1,
        year="2025",
        source_document_id="instructions_demo_2025",
        source_path=None,
        sections=(
            ModelSection(
                section_id="model_1",
                source_document_id="instructions_demo_2025",
                document_id="schedule_b_2025",
                heading="# One",
                level=1,
                governs=("1",),
                start_byte=0,
                end_byte=1,
            ),
        ),
        coverage={},
    )
    report = score_ab(
        source_document_id="instructions_demo_2025",
        model_frame=frame,
        deterministic_sections=(),
        cells_by_document={
            "schedule_b_2025": (
                {"cell_id": "b1", "line": "1"},
            ),
            "schedule_d_2025": (
                {"cell_id": "d1", "line": "1"},
            ),
        },
    )
    assert report["documents"]["schedule_b_2025"]["gained_correctly_owned"] == ["b1"]
    assert report["documents"]["schedule_b_2025"]["wrong_owner_count"] == 0
    assert report["documents"]["schedule_d_2025"]["wrong_owner_count"] == 1


def test_verifier_rejects_non_tiling_sections_directly() -> None:
    """The byte witness also rejects a gap even when headings are valid."""
    source = _source()
    sections = (
        ModelSection(
            section_id="one",
            source_document_id="instructions_demo_2025",
            document_id="demo_2025",
            heading="# One",
            level=1,
            governs=(),
            start_byte=0,
            end_byte=source.index(b"# Two"),
        ),
        ModelSection(
            section_id="three",
            source_document_id="instructions_demo_2025",
            document_id="demo_2025",
            heading="# Three",
            level=1,
            governs=(),
            start_byte=source.index(b"# Three"),
            end_byte=len(source),
        ),
    )
    with pytest.raises(ModelFrameVerificationError, match="byte conservation"):
        verify_model_sections(
            source,
            sections,
            source_document_id="instructions_demo_2025",
        )


@pytest.mark.parametrize(
    ("source_document_id", "fixture_name", "expected_sections"),
    (
        ("instructions_schedule_b_2025", "m20_s121_segmenter_responses.json", 10),
        ("instructions_schedule_d_2025", "m20_s121_schedule_d_responses.json", 70),
    ),
)
def test_recorded_booklet_fixture_is_source_backed(
    source_document_id: str,
    fixture_name: str,
    expected_sections: int,
) -> None:
    """The named booklets run from checked-in responses without a provider."""
    frame = build_frame_from_fixture(
        ROOT / ".cache" / "raw" / "2025" / f"{source_document_id}.txt",
        source_document_id=source_document_id,
        fixture_path=ROOT / "pilot" / "fixtures" / fixture_name,
    )
    assert len(frame.sections) == expected_sections
    assert frame.coverage["reconciles_to_file_size"] is True
    assert frame.coverage["duplicate_response_sections"] == 0


def test_ab_report_is_per_booklet_and_names_both_directions() -> None:
    """The real A/B report exposes Schedule B recovery and Schedule D control."""
    reports = {}
    for source_document_id, fixture_name in (
        ("instructions_schedule_b_2025", "m20_s121_segmenter_responses.json"),
        ("instructions_schedule_d_2025", "m20_s121_schedule_d_responses.json"),
    ):
        reports[source_document_id] = build_ab_report(
            ROOT / ".cache" / "raw" / "2025" / f"{source_document_id}.txt",
            source_document_id=source_document_id,
            fixture_path=ROOT / "pilot" / "fixtures" / fixture_name,
            root=ROOT,
        )

    schedule_b = reports["instructions_schedule_b_2025"]
    assert schedule_b["totals"] == {
        "cells": 8,
        "gained_correctly_owned": 7,
        "wrong_owner": 0,
    }
    assert schedule_b["documents"]["schedule_b_2025"]["baseline_correct"] == 0
    assert schedule_b["documents"]["schedule_b_2025"]["wrong_owner_count"] == 0

    schedule_d = reports["instructions_schedule_d_2025"]
    assert schedule_d["totals"]["cells"] == 24
    assert schedule_d["totals"]["gained_correctly_owned"] == 0
    assert schedule_d["totals"]["wrong_owner"] == 0
    assert schedule_d["documents"]["schedule_d_2025"]["baseline_correct"] == 11
    assert schedule_d["documents"]["schedule_d_2025"]["model_correct"] == 11


def test_scorer_keeps_the_schedule_1a_denominator_visible() -> None:
    """A parser miss is reported as 48 cells, not silently dropped."""
    frame = ModelInstructionFrame(
        schema_version=1,
        year="2025",
        source_document_id="instructions_form_1040_2025",
        source_path=None,
        sections=(),
        coverage={},
    )
    report = score_ab(
        source_document_id="instructions_form_1040_2025",
        model_frame=frame,
        deterministic_sections=(),
        cells_by_document={
            "schedule_1a_2025": tuple(
                {"cell_id": f"schedule_1a_2025:line={index}", "line": str(index)}
                for index in range(1, 49)
            )
        },
    )
    assert report["documents"]["schedule_1a_2025"]["cell_count"] == 48
    assert report["documents"]["schedule_1a_2025"]["model_reachable"] == 0
