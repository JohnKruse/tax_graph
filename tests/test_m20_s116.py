"""M20-S116 regression coverage for bidirectional instruction reconciliation."""

from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.extract.cells import build_cell_frame_from_document
from tax_graph.extract.instruction_ownership import (
    instruction_line_owners,
    instruction_span_ids_for_line,
)
from tax_graph.extract.instruction_reconciliation import (
    build_instruction_reconciliation_report,
    reconcile_instruction_document,
)
from tax_graph.extract.instruction_sections import build_instruction_sections
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.outline import CandidateSpan, build_candidate_spans


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]


def test_sub_line_inherits_only_when_no_specific_owner_exists() -> None:
    spans = [
        CandidateSpan(
            span_id="line-11",
            document_id="instructions_form_1040_2025",
            relationship="instructions",
            locator="lines 1-2",
            text="## Line 11\nLine 11 guidance.",
            owner_document_id="form_1040_2025",
            owner_lines=("11",),
        ),
        CandidateSpan(
            span_id="line-11a",
            document_id="instructions_form_1040_2025",
            relationship="instructions",
            locator="lines 3-4",
            text="## Line 11a\nSpecific 11a guidance.",
            owner_document_id="form_1040_2025",
            owner_lines=("11a",),
        ),
    ]
    owners = instruction_line_owners(spans)

    assert instruction_span_ids_for_line(
        spans, "11b", owners=owners, owner_document_id="form_1040_2025"
    ) == ["line-11"]
    assert instruction_span_ids_for_line(
        spans, "11a", owners=owners, owner_document_id="form_1040_2025"
    ) == ["line-11a"]


def test_reconciliation_reports_parser_gap_and_genuine_absence() -> None:
    frame = build_instruction_sections(
        "\n".join(
            [
                "# Instructions for Form 1040",
                "## Line 11",
                "Line 11 guidance.",
                "## Line 14",
                "Line 14 guidance.",
            ]
        ),
        source_document_id="instructions_form_1040_2025",
        year="2025",
    )
    report = reconcile_instruction_document(
        "form_1040_2025",
        "Line 11 guidance.\nLine 14 guidance.\nLine 15 is not listed here.",
        frame,
        [
            {"form": "form_1040_2025", "line": "11"},
            {"form": "form_1040_2025", "line": "11a"},
            {"form": "form_1040_2025", "line": "15"},
        ],
    )

    assert report["cell_buckets"]["MATCHED"] == 2
    assert report["cell_buckets"]["CELL WITH NO INSTRUCTION + BOOKLET MENTIONS IT"] == 1
    assert report["instruction_buckets"]["MATCHED"] == 1
    assert report["instruction_buckets"]["INSTRUCTION WITH NO CELL"] == 1
    assert next(item for item in report["cells"] if item["line"] == "11a")["match"] == "inherited"


def test_reconciliation_distinguishes_another_form_owner() -> None:
    frame = build_instruction_sections(
        "\n".join(
            [
                "# Instructions for Schedule 2",
                "## Line 9",
                "Schedule 2 line 9 guidance.",
            ]
        ),
        source_document_id="instructions_form_1040_2025",
        year="2025",
    )
    report = reconcile_instruction_document(
        "form_1040_2025",
        "Line 9 guidance appears in this shared booklet.",
        frame,
        [{"form": "form_1040_2025", "line": "9"}],
    )
    cell = report["cells"][0]
    assert cell["bucket"] == "CELL WITH NO INSTRUCTION + OTHER FORM OWNS LINE"
    assert cell["other_form_document_ids"] == ["schedule_2_2025"]


def test_real_1040_packet_consumes_every_owned_line() -> None:
    document = load_document_input("form_1040_2025", year="2025", root=ROOT)
    frame = build_cell_frame_from_document(document)
    rows = {row.line: row for row in frame.rows}

    spans = build_candidate_spans(document)
    owners = instruction_line_owners(spans)

    owned_lines = {
        line
        for line in rows
        if instruction_span_ids_for_line(
            spans,
            line,
            owners=owners,
            owner_document_id=document.document_id,
        )
    }
    assert owned_lines
    assert all(rows[line].instruction_text for line in owned_lines)
    assert all(
        rows[line].metadata["instruction_match"] in {"direct", "inherited"}
        for line in owned_lines
    )


def test_report_covers_topic_and_table_families() -> None:
    frame = build_instruction_sections(
        "# Instructions for Schedule B\n## Part I. Interest\nTopic guidance.\n",
        source_document_id="instructions_schedule_b_2025",
        year="2025",
    )
    report = build_instruction_reconciliation_report(
        [
            {
                "document_id": "schedule_b_2025",
                "raw_booklet_text": "# Instructions for Schedule B\n## Part I. Interest\nTopic guidance.\n",
                "frame": frame,
                "cells": [{"form": "schedule_b_2025", "line": "8"}],
            }
        ],
        table_addressed_cells=46,
    )

    assert report["families"]["topic_organized"]["cell_count"] == 1
    assert report["families"]["table_addressed"]["cell_count"] == 46
    assert report["documents"]["schedule_b_2025"]["cell_buckets"][
        "CELL WITH NO INSTRUCTION + BOOKLET DOES NOT MENTION IT"
    ] == 1
