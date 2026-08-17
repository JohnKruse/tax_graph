"""M20-S118 guards for typed instruction packet attachments."""

from __future__ import annotations

from pathlib import Path

import pytest

from pilot.reconcile_instructions import build_live_report
from tax_graph.extract.cells import build_cell_frame_from_document
from tax_graph.extract.instruction_ownership import (
    instruction_line_owners,
    instruction_span_resolution_for_line,
    instruction_span_ids_for_line,
)
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.outline import CandidateSpan, build_candidate_spans


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]


def _span(
    span_id: str,
    text: str,
    owner_lines: tuple[str, ...],
) -> CandidateSpan:
    """Build a small owned instruction span for packet-policy tests."""
    return CandidateSpan(
        span_id=span_id,
        document_id="instructions_form_1040_2025",
        relationship="instructions",
        locator=span_id,
        text=text,
        owner_document_id="form_1040_2025",
        owner_lines=owner_lines,
        section_id=f"section_{span_id}",
    )


def test_nested_containment_keeps_the_child_and_records_the_parent() -> None:
    parent = _span(
        "parent",
        "## Lines 4a and 4b\n\n### IRA distributions\n\nEnter the amount.",
        ("4a", "4b"),
    )
    child = _span(
        "child",
        "### IRA distributions\n\nEnter the amount.",
        ("4a", "4b"),
    )
    spans = [parent, child]
    owners = instruction_line_owners(spans)

    resolution = instruction_span_resolution_for_line(
        spans,
        "4a",
        owners=owners,
        owner_document_id="form_1040_2025",
    )

    assert instruction_span_ids_for_line(
        spans,
        "4a",
        owners=owners,
        owner_document_id="form_1040_2025",
    ) == ["child"]
    assert resolution["dropped"] == [
        {
            "span_id": "parent",
            "section_id": "section_parent",
            "kept_span_id": "child",
            "reason": "nested_text_containment",
        }
    ]


def test_general_and_specific_sections_are_kept_specific_first() -> None:
    general = _span(
        "general",
        "## Lines 8a Through 8z\n\nDo not report this income here.",
        tuple(f"8{letter}" for letter in "abcdefghijklmnopqrstuvwxyz"),
    )
    specific = _span(
        "specific",
        "#### Line 8a\n\nEnter the NOL deduction.",
        ("8a",),
    )
    resolution = instruction_span_resolution_for_line(
        [general, specific],
        "8a",
        owner_document_id="form_1040_2025",
    )

    assert resolution["selected_ids"] == ["specific", "general"]
    assert resolution["ambiguous"] is False
    assert [item["specificity"] for item in resolution["attachments"]] == [
        "specific",
        "general",
    ]


def test_stub_is_excluded_and_worksheet_is_packet_provenance() -> None:
    stub = _span("stub", "#### Line 1\n\n", ("1",))
    worksheet = _span(
        "worksheet",
        "# State and Local Income Tax Refund WorksheetSchedule 1, Line 1\n\nBefore you begin.",
        ("1",),
    )
    resolution = instruction_span_resolution_for_line(
        [stub, worksheet],
        "1",
        owner_document_id="form_1040_2025",
    )

    assert resolution["selected_ids"] == ["worksheet"]
    assert resolution["stubs"] == ["stub"]
    assert resolution["worksheets"] == ["worksheet"]
    assert resolution["attachments"][0]["provenance"] == "WORKSHEET"
    assert resolution["dropped"][0]["reason"] == "stub_section"


@pytest.fixture(scope="module")
def live_report() -> dict:
    """Build the same deterministic report that is checked in."""
    return build_live_report(ROOT)


def test_real_round_examples_and_bucket_sums(live_report: dict) -> None:
    """The live packet examples and both populations remain reconciled."""
    form_1040 = live_report["documents"]["form_1040_2025"]
    row_4a = next(row for row in form_1040["cells"] if row["line"] == "4a")
    assert row_4a["bucket"] == "MATCHED"
    assert row_4a["section_ids"] == [
        "instruction_section_instructions_form_1040_2025_0019"
    ]
    assert row_4a["instruction_dropped_sections"][0]["section_id"].endswith("_0018")

    schedule_1 = live_report["documents"]["schedule_1_2025"]
    row_8a = next(row for row in schedule_1["cells"] if row["line"] == "8a")
    assert row_8a["bucket"] == "MATCHED"
    assert row_8a["section_ids"] == [
        "instruction_section_instructions_form_1040_2025_0069",
        "instruction_section_instructions_form_1040_2025_0067",
    ]
    row_8b = next(row for row in schedule_1["cells"] if row["line"] == "8b")
    assert [
        item["specificity"]
        for item in row_8b["instruction_attachments"][:2]
    ] == ["specific", "general"]
    row_1 = next(row for row in schedule_1["cells"] if row["line"] == "1")
    assert row_1["bucket"] == "MATCHED"
    assert row_1["instruction_attachments"][0]["provenance"] == "WORKSHEET"
    assert row_1["instruction_dropped_sections"][0]["reason"] == "stub_section"

    for document_report in live_report["documents"].values():
        assert sum(document_report["cell_buckets"].values()) == document_report[
            "cell_count"
        ]
        assert sum(document_report["instruction_buckets"].values()) == document_report[
            "instruction_section_count"
        ]


def test_real_selected_packets_have_no_nested_text_duplicates(live_report: dict) -> None:
    """No selected packet sends a literal section twice under different ids."""
    for document_id, document_report in live_report["documents"].items():
        document = load_document_input(document_id, year="2025", root=ROOT)
        spans = build_candidate_spans(document)
        text_by_section = {
            span.section_id: span.text
            for span in spans
            if span.relationship == "instructions" and span.section_id
        }
        for cell in document_report["cells"]:
            texts = [
                text_by_section[section_id]
                for section_id in cell["section_ids"]
                if section_id in text_by_section
            ]
            for index, text in enumerate(texts):
                assert all(
                    text != other
                    and text.casefold() not in other.casefold()
                    and other.casefold() not in text.casefold()
                    for other in texts[index + 1 :]
                ), (document_id, cell["line"], texts)


def test_cell_frame_keeps_general_direct_owner_for_each_line() -> None:
    """The cell packet carries the range heading on every directly owned line."""
    document = load_document_input("schedule_1_2025", year="2025", root=ROOT)
    row = next(
        row
        for row in build_cell_frame_from_document(document).rows
        if row.line == "8b"
    )
    assert [
        item["specificity"]
        for item in row.metadata["instruction_attachments"][:2]
    ] == ["specific", "general"]
    assert row.metadata["instruction_match"] == "direct"
