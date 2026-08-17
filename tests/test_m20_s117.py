"""M20-S117 guards for accessor-backed instruction reconciliation."""

from __future__ import annotations

from pathlib import Path

import pytest

from pilot.reconcile_instructions import build_live_report
from tax_graph.extract.cells import build_cell_frame_from_document
from tax_graph.extract.instruction_ownership import (
    instruction_line_owners,
    instruction_span_ids_for_line,
)
from tax_graph.extract.instruction_sections import build_instruction_sections
from tax_graph.extract.instruction_reconciliation import reconcile_instruction_document
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.outline import (
    _spans_for_instruction_frame,
    build_instruction_sections_frame,
)


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]


def test_multiline_heading_uses_the_packet_ownership_accessor() -> None:
    booklet = "\n".join(
        [
            "# Instructions for Schedule 2",
            "## Lines 1a Through 1z",
            "The additions section applies to each printed child line.",
            "## Line 6",
            "Schedule 2 line 6 guidance.",
            "## Line 13",
            "Schedule 2 line 13 guidance.",
        ]
    )
    frame = build_instruction_sections(
        booklet,
        source_document_id="instructions_form_1040_2025",
        year="2025",
    )
    report = reconcile_instruction_document(
        "schedule_2_2025",
        booklet,
        frame,
        [
            {"form": "schedule_2_2025", "line": "1b"},
            {"form": "schedule_2_2025", "line": "1d"},
            {"form": "schedule_2_2025", "line": "6"},
            {"form": "schedule_2_2025", "line": "13"},
        ],
    )

    rows = {row["line"]: row for row in report["cells"]}
    assert rows["1b"]["bucket"] == "MATCHED"
    assert rows["1d"]["bucket"] == "MATCHED"
    assert rows["1b"]["match"] == "direct"
    assert rows["1d"]["match"] == "direct"
    assert "other_form_document_ids" not in rows["1b"]
    assert "other_form_document_ids" not in rows["1d"]
    assert rows["1b"]["section_ids"] == rows["1d"]["section_ids"]
    assert report["cell_buckets"]["MATCHED"] == 4
    assert sum(report["cell_buckets"].values()) == report["cell_count"]
    assert sum(report["instruction_buckets"].values()) == report["instruction_section_count"]


def test_report_cell_state_matches_accessor_for_every_real_line_cell() -> None:
    report = build_live_report(ROOT)

    for document_id, document_report in report["documents"].items():
        document = load_document_input(document_id, year="2025", root=ROOT)
        frame = build_instruction_sections_frame(document)
        spans = _spans_for_instruction_frame(frame, source_text="")
        owners = instruction_line_owners(spans)
        rows = build_cell_frame_from_document(document).rows
        assert len(document_report["cells"]) == len(rows)
        for report_row, cell in zip(document_report["cells"], rows):
            expected = bool(
                instruction_span_ids_for_line(
                    spans,
                    cell.line,
                    owners=owners,
                    owner_document_id=document_id,
                )
            )
            report_has_instruction = report_row["bucket"] in {"MATCHED", "AMBIGUOUS"}
            assert report_has_instruction == expected, (
                document_id,
                cell.line,
                report_row,
            )
        assert sum(document_report["cell_buckets"].values()) == document_report["cell_count"]
        assert sum(document_report["instruction_buckets"].values()) == document_report[
            "instruction_section_count"
        ]


def test_report_has_three_family_rows_and_no_mixed_bucket_counter() -> None:
    report = build_live_report(ROOT)

    assert report["round"] == "M20-S117"
    assert set(report["families"]) == {
        "line_anchored",
        "topic_organized",
        "table_addressed",
    }
    assert all(
        "bucket_counts" not in document_report
        for document_report in report["documents"].values()
    )
