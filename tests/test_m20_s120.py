"""M20-S120 guards for heading-granular instruction reachability measurement."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pytest
import yaml

from pilot.instruction_extent_split import build_instruction_extent_split


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def _report() -> dict:
    """Build the real deterministic S120 witness once for this focused file."""
    return build_instruction_extent_split(root=ROOT, year="2025")


def test_every_unclaimed_span_is_split_without_losing_bytes() -> None:
    """Every S119 parent is covered contiguously by its heading-local rows."""
    report = _report()
    assert report["counts"]["unclaimed_parent_spans"] == 56
    assert report["counts"]["instruction_booklets"] == 8
    for booklet in report["booklets"].values():
        for parent in booklet["parent_spans"]:
            rows = parent["split_rows"]
            assert rows
            assert rows[0]["start"] == parent["start"]
            assert rows[-1]["end"] == parent["end"]
            for previous, current in zip(rows, rows[1:]):
                assert previous["end"] == current["start"]
            assert sum(row["bytes"] for row in rows) == parent["bytes"]
            assert all(row["byte_end"] - row["byte_start"] == row["bytes"] for row in rows)


def test_all_no_truncation_cells_have_one_causal_reason() -> None:
    """The 81-cell join is total and retains an honest unresolved bucket."""
    report = _report()
    rows = report["cell_classifications"]
    assert len(rows) == 81
    assert len({row["cell_id"] for row in rows}) == 81
    assert all(row["truncated_body_found"] is False for row in rows)
    assert set(report["counts"]["reason_counts"]) == {
        "HEADING_NEVER_SECTIONED",
        "MENTIONED_IN_PROSE_ONLY",
        "NON_LINE_CONTENT",
        "UNRESOLVED",
    }
    assert report["counts"]["reason_counts"]["UNRESOLVED"] > 0
    assert sum(report["counts"]["reason_counts"].values()) == 81


def test_third_party_designee_is_heading_granular_and_links_cells() -> None:
    """The 34-heading span names the actual heading for its governed cells."""
    report = _report()
    parent = next(
        parent
        for parent in report["booklets"]["instructions_form_1040_2025"]["parent_spans"]
        if parent["start"] == 341299
    )
    rows = [row for row in parent["split_rows"] if row["heading"] is not None]
    assert len(rows) == 34
    governed_lines = {
        cell["line"]
        for row in rows
        for cell in row["governed_cells"]
    }
    assert {"11", "15", "16", "26", "37", "38"}.issubset(governed_lines)
    assert rows[0]["heading"]["title"] == "Third Party Designee"
    assert any(row["heading"]["title"] == "Additional Income" for row in rows)
    assert all(row["governed_cells"] is not None for row in rows)
    electronic_return = next(
        row
        for row in rows
        if row["heading"]["title"] == "Requirements for an Electronic Return"
    )
    assert any(
        cell["line"] == "11" and cell["reason"] == "HEADING_NEVER_SECTIONED"
        for cell in electronic_return["governed_cells"]
    )


def test_schedule_1a_chapter_is_one_recoverable_group() -> None:
    """The unsectioned Schedule 1-A chapter ranks its full 48-cell surface."""
    report = _report()
    groups = [
        group
        for group in report["recovery_ranking"]
        if group.get("scope") == "all_form_cells"
        and group["heading_title"] == "Instructions for Schedule 1-A"
    ]
    assert len(groups) == 1
    assert groups[0]["booklet_id"] == "instructions_form_1040_2025"
    assert groups[0]["heading_level"] == 1
    assert groups[0]["cells_recovered"] == 48
    assert len(groups[0]["cell_ids"]) == 48


def test_eic_table_and_front_matter_are_negative_controls() -> None:
    """Lookup tables and front matter never enter the actionable ranking."""
    report = _report()
    controls = report["negative_controls"]
    assert controls["earned_income_credit_table"]["actionable"] is False
    assert controls["earned_income_credit_table"]["row_count"] > 0
    assert controls["front_matter"]["actionable"] is False
    assert controls["front_matter"]["row_count"] > 0
    assert all(
        group["scope"] != "negative_control"
        for group in report["recovery_ranking"]
    )


def test_checked_in_artifact_is_reproducible_from_the_live_measurement() -> None:
    """The committed witness is generated output, not a hand-authored summary."""
    artifact = yaml.safe_load(
        (ROOT / "plans" / "m20_s120_instruction_extent_split.yaml").read_text(
            encoding="ascii"
        )
    )
    assert artifact == _report()
