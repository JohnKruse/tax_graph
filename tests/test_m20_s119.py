"""M20-S119 guards for instruction-booklet extent census and causal join."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pytest

from pilot.instruction_extent_census import build_instruction_extent_census


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def _report() -> dict:
    """Build the real deterministic census once for this focused file."""
    return build_instruction_extent_census(root=ROOT, year="2025")


def test_every_instruction_booklet_reconciles_every_source_byte() -> None:
    """The census covers all manifest instruction booklets without silent gaps."""
    report = _report()
    expected = {
        "instructions_form_1040_2025",
        "instructions_form_1116_2025",
        "instructions_form_2441_2025",
        "instructions_form_6251_2025",
        "instructions_form_8949_2025",
        "instructions_schedule_a_2025",
        "instructions_schedule_b_2025",
        "instructions_schedule_d_2025",
    }
    assert set(report["booklets"]) == expected
    assert report["counts"]["instruction_booklets"] == len(expected)
    for booklet in report["booklets"].values():
        claims = booklet["claims"]
        assert claims["reconciles_to_file_size"] is True
        assert (
            claims["claimed_exactly_once_plus_unclaimed_plus_overlap_bytes"]
            == booklet["file_size_bytes"]
        )
        assert sum(booklet["classification_counts"].values()) == len(
            booklet["unclaimed_spans"]
        )


def test_known_stub_negative_and_overlap_cases_are_visible() -> None:
    """S119 names the schedule 1 stub, the 1040 negative, and the overlap."""
    report = _report()
    form_1040 = report["booklets"]["instructions_form_1040_2025"]

    schedule_1_stub_body = next(
        span
        for span in form_1040["unclaimed_spans"]
        if span["start"] == 512137
    )
    assert schedule_1_stub_body["classification"] == "TRUNCATED_BODY"
    assert schedule_1_stub_body["byte_end"] - schedule_1_stub_body["byte_start"] == (
        schedule_1_stub_body["bytes"]
    )
    assert schedule_1_stub_body["heading"]["title"].startswith(
        "Taxable Refunds, Credits, or Offsets"
    )

    line_27c = "instruction_section_instructions_form_1040_2025_0048"
    negative_spans = [
        span
        for span in form_1040["unclaimed_spans"]
        if span["preceding_section_id"] == line_27c
    ]
    assert not any(
        span["classification"] == "TRUNCATED_BODY" for span in negative_spans
    )
    # The parent Lines 27a-27c section owns the long body through the chapter
    # boundary, so the naive 138,288-byte gap is not an unclaimed span at all.
    assert not negative_spans

    overlap = next(
        span
        for span in form_1040["overlaps"]
        if "instruction_section_instructions_form_1040_2025_0010"
        in span["section_ids"]
    )
    assert overlap["end"] > overlap["start"]
    assert overlap["bytes"] == overlap["byte_end"] - overlap["byte_start"]


def test_item_three_has_one_row_per_missing_cell_and_stub() -> None:
    """The S116 causal join keeps both positive and negative answers visible."""
    join = _report()["s116_join"]
    assert join["counts"]["cells"] == 91
    assert join["counts"]["stub_sections"] == 3
    assert join["counts"]["rows"] == len(join["rows"]) == 94
    assert join["counts"]["cells_with_truncated_body"] == sum(
        row["target_type"] == "cell" and row["truncated_body_found"]
        for row in join["rows"]
    )
    assert join["counts"]["stub_sections_with_immediately_following_truncated_body"] == sum(
        row["target_type"] == "stub_section"
        and row["immediately_following_truncated_body"]
        for row in join["rows"]
    )
    assert all("truncated_body_found" in row for row in join["rows"])
    schedule_1_stub = next(
        row
        for row in join["rows"]
        if row.get("section_id")
        == "instruction_section_instructions_form_1040_2025_0060"
    )
    assert schedule_1_stub["immediately_following_truncated_body"] is True
    assert schedule_1_stub["immediately_following_truncated_body_bytes"] > 0
    assert schedule_1_stub["truncated_body_bytes"] == schedule_1_stub[
        "immediately_following_truncated_body_bytes"
    ]
