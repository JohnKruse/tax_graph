"""M20-S23 tests for the deterministic instruction_sections frame."""

from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.extract.instruction_sections import (
    build_instruction_sections,
    build_instruction_sections_file,
    load_instruction_sections_artifact,
    write_instruction_sections_artifact,
)
from tax_graph.extract.instruction_ownership import instruction_span_ids_for_line
from tax_graph.extract.outline import CandidateSpan


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]


def test_line_sections_keep_form_context_and_stop_at_equal_heading() -> None:
    text = "\n".join(
        [
            "# Line Instructions for Forms 1040 and 1040-SR",
            "## Line 9",
            "Form 1040 line 9 text.",
            "### More detail",
            "The page marker is layout, not a section boundary.",
            "# Page 2",
            "Continued verbatim text.",
            "## Instructions for Schedule 1",
            "## Line 9",
            "Schedule 1 line 9 text.",
            "## Line 10",
            "Schedule 1 line 10 text.",
            "",
        ]
    )

    frame = build_instruction_sections(
        text,
        source_document_id="instructions_form_1040_2025",
        year="2025",
    )

    form_line = frame.for_line("form_1040_2025", "9")
    schedule_line = frame.for_line("schedule_1_2025", "9")
    assert len(form_line) == 1
    assert len(schedule_line) == 1
    assert "Continued verbatim text." in form_line[0].text
    assert "Schedule 1 line 9 text." not in form_line[0].text
    assert "Schedule 1 line 10 text." not in schedule_line[0].text
    assert frame.coverage["collision_count"] == 1
    assert frame.coverage["collisions_resolved_by_form_context"] == 1


def test_line_ranges_expand_only_when_the_heading_says_through() -> None:
    frame = build_instruction_sections(
        "\n".join(
            [
                "# Instructions for Schedule 2",
                "## Lines 1a Through 1z",
                "The additions section applies to each printed child line.",
                "## Line 2",
                "The AMT section.",
            ]
        ),
        source_document_id="instructions_form_1040_2025",
        year="2025",
    )

    lines = [section.line for section in frame.sections]
    assert lines[:26] == [f"1{letter}" for letter in "abcdefghijklmnopqrstuvwxyz"]
    assert lines[-1] == "2"
    assert all(section.document_id == "schedule_2_2025" for section in frame.sections)


def test_real_1040_booklet_does_not_cross_schedule_owners() -> None:
    path = ROOT / ".cache" / "raw" / "2025" / "instructions_form_1040_2025.txt"
    if not path.exists():
        pytest.skip("acquired 2025 Form 1040 instructions are not present")

    frame = build_instruction_sections_file(
        path,
        source_document_id="instructions_form_1040_2025",
        year="2025",
    )

    form_1040_line_9 = frame.for_line("form_1040_2025", "9")
    form_1040_line_21 = frame.for_line("form_1040_2025", "21")
    schedule_2_line_9 = frame.for_line("schedule_2_2025", "9")
    schedule_1a_line_38 = frame.for_line("schedule_1a_2025", "38")
    assert not any("Household Employment Taxes" in section.text for section in form_1040_line_9)
    assert not any("Student Loan Interest Deduction" in section.text for section in form_1040_line_21)
    assert any("Household Employment Taxes" in section.text for section in schedule_2_line_9)
    assert not schedule_1a_line_38
    assert frame.coverage["forms"]["schedule_1a_2025"]["has_sections"] is False
    assert "schedule_1a_2025" in frame.coverage["documents_without_sections"]
    assert frame.coverage["wrong_owner_spans_after"] == 0
    assert frame.coverage["collision_count"] > 0


def test_instruction_sections_artifact_round_trips_verbatim(tmp_path: Path) -> None:
    source = "# Instructions for Schedule A\n## Line 3\nMultiply line 2 by 7.5%.\n"
    frame = build_instruction_sections(
        source,
        source_document_id="instructions_schedule_a_2025",
        year="2025",
        source_path=tmp_path / "instructions.txt",
    )
    artifact = write_instruction_sections_artifact(frame, tmp_path / "instruction_sections.yaml")

    loaded = load_instruction_sections_artifact(artifact)
    section = loaded.for_line("schedule_a_2025", "3")[0]
    assert section.text == "## Line 3\nMultiply line 2 by 7.5%.\n"
    assert section.locator.start_line == 2
    assert section.locator.end_line == 3
    assert section.locator.start_offset < section.locator.end_offset


def test_shared_booklet_line_join_respects_owner_form() -> None:
    spans = [
        CandidateSpan(
            span_id="form-9",
            document_id="instructions_form_1040_2025",
            relationship="instructions",
            locator="lines 1-2",
            text="## Line 9\nForm 1040 line 9.",
            owner_document_id="form_1040_2025",
            owner_lines=("9",),
        ),
        CandidateSpan(
            span_id="schedule-9",
            document_id="instructions_form_1040_2025",
            relationship="instructions",
            locator="lines 3-4",
            text="## Line 9\nSchedule 2 line 9.",
            owner_document_id="schedule_2_2025",
            owner_lines=("9",),
        ),
    ]

    assert instruction_span_ids_for_line(
        spans,
        "9",
        owner_document_id="form_1040_2025",
    ) == ["form-9"]
    assert instruction_span_ids_for_line(
        spans,
        "9",
        owner_document_id="schedule_2_2025",
    ) == ["schedule-9"]
