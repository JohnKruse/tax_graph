"""M20-S123 guards for source-only model segmentation and its verifier."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

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
    load_recorded_fixture,
    load_reconciliation_cells,
    manifest_owner_document_ids,
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


def test_governs_conflict_prefers_the_observation_with_more_following_context() -> None:
    """A longer trailing window wins without unioning competing claims."""
    source = _source()
    two_start = source.index(b"# Two")
    three_start = source.index(b"# Three")
    first_window_end = three_start + 5
    records = [
        {
            "window_index": 0,
            "window_start_byte": 0,
            "window_end_byte": first_window_end,
            "response": {
                "sections": [
                    {
                        "heading": "# One",
                        "level": 1,
                        "start_byte": 0,
                        "end_byte": two_start,
                        "document_id": "demo_2025",
                        "governs": ["1"],
                    },
                    {
                        "heading": "# Two",
                        "level": 1,
                        "start_byte": two_start,
                        "end_byte": three_start,
                        "document_id": "demo_2025",
                        "governs": ["old_claim"],
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
                        "document_id": "demo_2025",
                        "governs": ["better_claim"],
                    },
                    {
                        "heading": "# Three",
                        "level": 1,
                        "start_byte": three_start,
                        "end_byte": len(source),
                        "document_id": "demo_2025",
                        "governs": ["3"],
                    },
                ]
            },
        },
    ]

    frame = build_model_frame(
        source.decode("utf-8"),
        source_document_id="instructions_demo_2025",
        responses=records,
    )

    two = next(section for section in frame.sections if section.heading == "# Two")
    assert two.governs == ("better_claim",)
    assert frame.coverage["governs_conflict_count"] == 1
    assert frame.coverage["rejected_sections"] == []


def test_governs_conflict_tie_is_rejected_but_other_sections_tile_source() -> None:
    """Equal context rejects only the ambiguous section and keeps its neighbors."""
    source = _source()
    two_start = source.index(b"# Two")
    three_start = source.index(b"# Three")
    tie_end = three_start + 5
    records = [
        {
            "window_index": 0,
            "window_start_byte": 0,
            "window_end_byte": tie_end,
            "response": {
                "sections": [
                    {
                        "heading": "# One",
                        "level": 1,
                        "start_byte": 0,
                        "end_byte": two_start,
                        "document_id": "demo_2025",
                        "governs": ["1"],
                    },
                    {
                        "heading": "# Two",
                        "level": 1,
                        "start_byte": two_start,
                        "end_byte": three_start,
                        "document_id": "demo_2025",
                        "governs": ["left_claim"],
                    },
                ]
            },
        },
        {
            "window_index": 1,
            "window_start_byte": two_start - 5,
            "window_end_byte": tie_end,
            "response": {
                "sections": [
                    {
                        "heading": "# Two",
                        "level": 1,
                        "start_byte": two_start,
                        "end_byte": three_start,
                        "document_id": "demo_2025",
                        "governs": ["right_claim"],
                    }
                ]
            },
        },
        {
            "window_index": 2,
            "window_start_byte": three_start,
            "window_end_byte": len(source),
            "response": {
                "sections": [
                    {
                        "heading": "# Three",
                        "level": 1,
                        "start_byte": three_start,
                        "end_byte": len(source),
                        "document_id": "demo_2025",
                        "governs": ["3"],
                    }
                ]
            },
        },
    ]

    frame = build_model_frame(
        source.decode("utf-8"),
        source_document_id="instructions_demo_2025",
        responses=records,
    )

    assert [section.heading for section in frame.sections] == ["# One", "# Three"]
    assert frame.coverage["governs_conflict_count"] == 1
    rejected = frame.coverage["rejected_sections"]
    assert len(rejected) == 1
    assert rejected[0]["reason"] == "ambiguous_governs_conflict"
    assert rejected[0]["ambiguity"] == "equal_following_context"
    assert [claim["governs"] for claim in rejected[0]["competing_claims"]] == [
        ["left_claim"],
        ["right_claim"],
    ]
    assert frame.coverage["reconciles_to_file_size"] is True


def test_governs_conflict_with_every_observation_at_an_edge_is_rejected() -> None:
    """Edge-only observations stay rejected even when one has more context."""
    source = _source()
    two_start = source.index(b"# Two")
    three_start = source.index(b"# Three")
    records = [
        {
            "window_index": 0,
            "window_start_byte": 0,
            "window_end_byte": three_start,
            "response": {
                "sections": [
                    {
                        "heading": "# One",
                        "level": 1,
                        "start_byte": 0,
                        "end_byte": two_start,
                        "document_id": "demo_2025",
                        "governs": ["1"],
                    },
                    {
                        "heading": "# Two",
                        "level": 1,
                        "start_byte": two_start,
                        "end_byte": three_start,
                        "document_id": "demo_2025",
                        "governs": ["edge_left"],
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
                        "end_byte": len(source),
                        "document_id": "demo_2025",
                        "governs": ["edge_right"],
                    },
                    {
                        "heading": "# Three",
                        "level": 1,
                        "start_byte": three_start,
                        "end_byte": len(source),
                        "document_id": "demo_2025",
                        "governs": ["3"],
                    },
                ]
            },
        },
    ]

    frame = build_model_frame(
        source.decode("utf-8"),
        source_document_id="instructions_demo_2025",
        responses=records,
    )

    assert frame.coverage["governs_conflict_count"] == 1
    assert frame.coverage["rejected_sections"][0]["ambiguity"] == (
        "all_observations_abut_window_edge"
    )


def test_verifier_rejects_a_range_whose_claimed_text_is_fabricated() -> None:
    """A fabricated section is rejected while the surrounding booklet remains valid."""
    source = _source()
    records = _section_records(source, "demo_2025")
    bad = deepcopy(records)
    for record in bad:
        record["response"] = dict(record["response"])
        record["response"]["sections"] = [
            dict(section) for section in record["response"]["sections"]
        ]
        for section in record["response"]["sections"]:
            if section["heading"] == "# Two":
                section["text"] = "invented text"
    frame = build_model_frame(
        source.decode("utf-8"),
        source_document_id="instructions_demo_2025",
        responses=bad,
    )
    assert [section.heading for section in frame.sections] == ["# One", "# Three"]
    assert frame.coverage["rejected_sections"][0]["reason"] == "text_mismatch"


def test_verifier_rejects_a_heading_not_at_the_claimed_source_offset() -> None:
    """A fabricated heading is rejected without hiding the remaining booklet."""
    source = _source()
    records = _section_records(source, "demo_2025")
    fabricated_records = deepcopy(records)
    for record in fabricated_records:
        for section in record["response"]["sections"]:
            if section["heading"] == "# Two":
                section["heading"] = "# Invented"

    frame = build_model_frame(
        source.decode("utf-8"),
        source_document_id="instructions_demo_2025",
        responses=fabricated_records,
    )

    assert [section.heading for section in frame.sections] == ["# One", "# Three"]
    rejected = frame.coverage["rejected_sections"]
    assert rejected
    assert all(
        item == {
            "start_byte": source.index(b"# Two"),
            "heading": "# Invented",
            "reason": "heading_not_at_source_offset",
        }
        for item in rejected
    )


def test_verifier_accepts_markdown_and_run_in_heading_prefixes() -> None:
    """The heading witness may be marked up or followed by paragraph text."""
    source = b"# Page 1\n**Line 1.** Report the amount.\n"
    sections = (
        ModelSection(
            section_id="page",
            source_document_id="instructions_demo_2025",
            document_id="demo_2025",
            heading="Page 1",
            level=1,
            governs=(),
            start_byte=0,
            end_byte=source.index(b"**Line"),
        ),
        ModelSection(
            section_id="line",
            source_document_id="instructions_demo_2025",
            document_id="demo_2025",
            heading="Line 1.",
            level=1,
            governs=("1",),
            start_byte=source.index(b"**Line"),
            end_byte=len(source),
        ),
    )
    verify_model_sections(
        source,
        sections,
        source_document_id="instructions_demo_2025",
    )


def test_verifier_rejects_a_document_id_outside_the_manifest_owner_set() -> None:
    """A source booklet id cannot become an owner for a governed section."""
    source = _source()
    records = _section_records(source, "demo_2025")
    bad = deepcopy(records)
    for record in bad:
        record["response"] = dict(record["response"])
        record["response"]["sections"] = [
            dict(section) for section in record["response"]["sections"]
        ]
        for section in record["response"]["sections"]:
            if section["heading"] == "# Two":
                section["document_id"] = "instructions_demo_2025"
    frame = build_model_frame(
        source.decode("utf-8"),
        source_document_id="instructions_demo_2025",
        responses=bad,
        allowed_document_ids={"demo_2025"},
    )
    assert [section.heading for section in frame.sections] == ["# One", "# Three"]
    assert frame.coverage["rejected_sections"][0]["reason"] == "disallowed_document_id"


def test_malformed_section_is_rejected_without_failing_the_booklet() -> None:
    """A bad level drops one section while neighboring sections still tile."""
    source = _source()
    records = _section_records(source, "demo_2025")
    bad = deepcopy(records)
    for section in bad[0]["response"]["sections"]:
        if section["heading"] == "# Two":
            section["level"] = 0

    frame = build_model_frame(
        source.decode("utf-8"),
        source_document_id="instructions_demo_2025",
        responses=bad,
    )

    assert [section.heading for section in frame.sections] == ["# One", "# Three"]
    rejected = frame.coverage["rejected_sections"]
    assert rejected
    assert all(item["reason"] == "invalid_level" for item in rejected)
    assert all(item["start_byte"] == source.index(b"# Two") for item in rejected)


def test_prompt_contains_source_but_no_cell_conditioning() -> None:
    """The model prompt names only source coordinates and segmentation rules."""
    source = _source()
    window = build_source_windows(source, max_window_bytes=100, overlap_bytes=10)[0]
    prompt = build_window_prompt(
        source,
        window,
        source_document_id="instructions_demo_2025",
        allowed_document_ids=("demo_2025",),
        prompt_text="Segment source text into sections.",
    )
    assert "# One" in prompt
    assert "[[source_byte=0]]" in prompt
    assert "BEGIN ACQUIRED SOURCE" in prompt
    assert "cell_id" not in prompt
    assert "unmatched list" not in prompt
    assert "Allowed document_id values for every section" in prompt
    assert "demo_2025" in prompt
    assert "The source booklet id is a source marker, never an owner" in prompt


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


def test_schema_enumerates_manifest_owners_without_the_source_id() -> None:
    """The provider contract carries only the booklet's manifest owners."""
    schema = segmenter_schema(allowed_document_ids=("schedule_b_2025",))
    item = schema["properties"]["sections"]["items"]
    assert item["properties"]["document_id"] == {
        "type": "string",
        "enum": ["schedule_b_2025"],
    }


def test_scorer_reports_form_and_worksheet_owner_metrics_after_segmentation() -> None:
    """Ownership metrics distinguish wrong forms from correct worksheet sections."""
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
    assert report["documents"]["schedule_b_2025"]["wrong_form_owner_count"] == 0
    assert report["documents"]["schedule_d_2025"]["wrong_form_owner_count"] == 1


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
    ("source_document_id", "fixture_name", "expected_sections", "expected_raw_sections"),
    (
        (
            "instructions_schedule_b_2025",
            "instruction_segmenter_live_recordings.json",
            29,
            29,
        ),
        (
            "instructions_schedule_d_2025",
            "instruction_segmenter_live_recordings.json",
            93,
            104,
        ),
    ),
)
def test_recorded_booklet_fixture_is_source_backed(
    source_document_id: str,
    fixture_name: str,
    expected_sections: int,
    expected_raw_sections: int,
) -> None:
    """The named booklets run from checked-in responses without a provider."""
    frame = build_frame_from_fixture(
        ROOT / ".cache" / "raw" / "2025" / f"{source_document_id}.txt",
        source_document_id=source_document_id,
        fixture_path=ROOT / "pilot" / "fixtures" / fixture_name,
        allowed_document_ids=manifest_owner_document_ids(
            ROOT,
            source_document_id=source_document_id,
        ),
    )
    assert len(frame.sections) == expected_sections
    assert frame.coverage["reconciles_to_file_size"] is True
    assert frame.coverage["response_section_count"] == expected_raw_sections
    assert frame.coverage["rejected_sections"] == []
    assert frame.coverage["heading_offset_repaired_count"] == (
        0 if source_document_id == "instructions_schedule_b_2025" else 2
    )


def test_ab_report_is_per_booklet_and_names_both_directions() -> None:
    """The real A/B report exposes Schedule B recovery and Schedule D control."""
    reports = {}
    for source_document_id, fixture_name in (
        ("instructions_schedule_b_2025", "instruction_segmenter_live_recordings.json"),
        ("instructions_schedule_d_2025", "instruction_segmenter_live_recordings.json"),
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
        "gained_correctly_owned": 8,
        "wrong_form_owner": 0,
        "sibling_worksheet_owner": 0,
    }
    assert schedule_b["documents"]["schedule_b_2025"]["baseline_correct"] == 0
    assert schedule_b["documents"]["schedule_b_2025"]["model_reachable"] == 8
    assert schedule_b["documents"]["schedule_b_2025"]["wrong_form_owner_count"] == 0

    schedule_d = reports["instructions_schedule_d_2025"]
    assert schedule_d["totals"] == {
        "cells": 24,
        "gained_correctly_owned": 1,
        "wrong_form_owner": 0,
        "sibling_worksheet_owner": 58,
    }
    assert schedule_d["documents"]["schedule_d_2025"]["baseline_correct"] == 11
    assert schedule_d["documents"]["schedule_d_2025"]["model_correct"] == 12
    assert schedule_d["documents"]["schedule_d_2025"]["model_reachable"] == 24
    assert schedule_d["documents"]["schedule_d_2025"]["wrong_form_owner_count"] == 0
    assert schedule_d["documents"]["schedule_d_2025"]["sibling_worksheet_owner_count"] == 58


def test_manifest_owner_sets_exclude_the_instruction_source() -> None:
    """Booklet owner vocabularies come from manifest relationships, not prose."""
    assert manifest_owner_document_ids(
        ROOT,
        source_document_id="instructions_schedule_b_2025",
    ) == frozenset({"schedule_b_2025"})
    assert manifest_owner_document_ids(
        ROOT,
        source_document_id="instructions_schedule_d_2025",
    ) == frozenset(
        {
            "schedule_d_2025",
            "capital_loss_carryover_worksheet_2025",
            "28_rate_gain_worksheet_2025",
            "unrecaptured_section_1250_gain_worksheet_2025",
            "schedule_d_tax_worksheet_2025",
        }
    )


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


def test_three_measured_heading_pointer_repairs_are_source_anchored() -> None:
    """The three measured pointer errors repair only to their real line bytes."""
    source_document_id = "instructions_schedule_d_2025"
    source_path = ROOT / ".cache" / "raw" / "2025" / f"{source_document_id}.txt"
    source_bytes = source_path.read_bytes()
    fixture_path = ROOT / "pilot" / "fixtures" / "instruction_segmenter_live_recordings.json"
    records = [
        dict(record)
        for record in load_recorded_fixture(
            fixture_path,
            source_document_id=source_document_id,
            source_bytes=source_bytes,
        )
    ]
    claimed_offsets = {
        "What's New": 378,
        "Mark-to-Market Election for Traders": 33026,
        "Gain from an Installment Sale of QSB Stock": 51283,
    }
    for record in records:
        record["response"] = dict(record["response"])
        record["response"]["sections"] = [
            dict(section)
            for section in record["response"]["sections"]
        ]
        for section in record["response"]["sections"]:
            if section["heading"] in claimed_offsets:
                section["start_byte"] = claimed_offsets[section["heading"]]

    frame = build_model_frame(
        source_bytes.decode("utf-8"),
        source_document_id=source_document_id,
        responses=records,
        allowed_document_ids=manifest_owner_document_ids(
            ROOT,
            source_document_id=source_document_id,
        ),
    )

    assert frame.coverage["heading_offset_repaired_count"] == 4
    assert frame.coverage["rejected_sections"] == []
    repaired = {
        section.heading: section.start_byte
        for section in frame.sections
        if section.heading in claimed_offsets
    }
    assert repaired == {
        "What's New": 380,
        "Mark-to-Market Election for Traders": 32984,
        "Gain from an Installment Sale of QSB Stock": 51234,
    }


def test_live_degenerate_line_four_is_recovered_from_its_start_byte() -> None:
    """An advisory end byte cannot discard the real Line 4 section."""
    source_document_id = "instructions_schedule_d_2025"
    source_path = ROOT / ".cache" / "raw" / "2025" / f"{source_document_id}.txt"
    frame = build_frame_from_fixture(
        source_path,
        source_document_id=source_document_id,
        fixture_path=ROOT / "pilot" / "fixtures" / "instruction_segmenter_live_recordings.json",
        allowed_document_ids=manifest_owner_document_ids(
            ROOT,
            source_document_id=source_document_id,
        ),
    )

    line_four = next(section for section in frame.sections if section.heading == "Line 4.")
    assert line_four.start_byte == 71963
    assert line_four.end_byte > line_four.start_byte
    assert line_four.document_id == "unrecaptured_section_1250_gain_worksheet_2025"
    assert line_four.governs == ("4",)


def test_reconciliation_cells_use_the_manifest_owner_set() -> None:
    """Cell scoring receives the same five-document owner vocabulary as the model."""
    source_document_id = "instructions_schedule_d_2025"
    cells = load_reconciliation_cells(
        ROOT,
        source_document_id=source_document_id,
    )

    assert set(cells) == manifest_owner_document_ids(
        ROOT,
        source_document_id=source_document_id,
    )


def test_live_cli_writes_each_window_before_frame_verification(tmp_path, monkeypatch) -> None:
    """A verification failure leaves the paid response recording on disk."""
    import pilot.model_instruction_segmenter as segmenter

    source_path = tmp_path / "source.txt"
    source_path.write_bytes(b"# One\nbody\n")
    output_path = tmp_path / "recording.json"
    monkeypatch.setattr(segmenter, "ROOT", tmp_path)
    monkeypatch.setattr(
        segmenter,
        "manifest_owner_document_ids",
        lambda root, *, source_document_id: frozenset({"demo_2025"}),
    )
    monkeypatch.setattr(segmenter, "load_config", lambda root: {})
    monkeypatch.setattr(
        segmenter,
        "call_model_window",
        lambda prompt, config, *, allowed_document_ids: {"sections": []},
    )

    def fail_verification(*args, **kwargs):
        payload = json.loads(output_path.read_text(encoding="ascii"))
        assert len(payload["booklets"]["demo_2025"]["responses"]) == 1
        raise ModelFrameVerificationError("verification failed")

    monkeypatch.setattr(segmenter, "build_model_frame", fail_verification)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "model_instruction_segmenter.py",
            "demo_2025",
            "--source",
            str(source_path),
            "--output",
            str(output_path),
        ],
    )

    with pytest.raises(ModelFrameVerificationError, match="verification failed"):
        segmenter.main()
