"""Focused tests for the M20-S103 source-extents pilot."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from source_extents import measure_source_extents


ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def _report() -> dict:
    """Build the real corpus report for the focused pilot assertions."""
    return measure_source_extents(root=ROOT, year="2025")


def _rows(report: dict, document_id: str) -> dict[str, dict]:
    """Index report rows for one corpus document."""
    return {
        str(row["line"]): row
        for row in report["rows"]
        if row["document_id"] == document_id
    }


def _source_slice(row: dict) -> str:
    """Read and concatenate the acquired source ranges for one row."""
    source_id = row["source_document_id"]
    source = (ROOT / ".cache" / "raw" / "2025" / f"{source_id}.txt").read_text(
        encoding="utf-8"
    )
    return "".join(source[item["start"] : item["end"]] for item in row["ranges"])


def test_full_manifest_rule_has_no_silent_rows() -> None:
    """Every manifest-defined row lands in exactly one measured bucket."""
    report = _report()
    assert report["excluded_documents"] == []
    assert report["counts"]["documents"] == 35
    assert report["counts"]["rows"] == 731
    assert report["counts"]["overlaps"] == 0
    assert report["counts"]["unclaimed_runs"] > 0
    assert sum(report["counts"]["classification"].values()) == 731
    assert all(
        row["status"] in {"single_range", "multi_range", "unreconstructable"}
        for row in report["rows"]
    )


def test_known_simplified_method_boundary_is_before_note() -> None:
    """Line 2 must stop before the note that names line 4."""
    report = _report()
    row = _rows(report, "simplified_method_worksheet_2025")["2"]
    assert row["status"] == "single_range"
    assert row["ranges"][-1]["end"] <= 118265
    note_runs = [
        item
        for item in report["unclaimed_runs"]
        if item["source_document_id"] == "instructions_form_1040_2025"
        and item["start"] <= 118266
        and item["end"] >= 118490
    ]
    assert note_runs
    assert any("line 4" in item["preview"].casefold() for item in note_runs)


def test_capital_loss_routing_sentences_are_not_claimed_by_rows() -> None:
    """Rows 4 and 8 exclude the routing tails that follow them in source."""
    report = _report()
    rows = _rows(report, "capital_loss_carryover_worksheet_2025")
    assert "go to line 5" not in _source_slice(rows["4"]).casefold()
    assert "go to line 9" not in _source_slice(rows["8"]).casefold()


def test_known_layout_rows_are_multi_range_not_defects() -> None:
    """The named layout cases remain a distinct multi-range class."""
    report = _report()
    expected = {
        ("form_6251_2025", "5"),
        ("schedule_d_2025", "21"),
        ("form_1116_2025", "1a"),
        ("form_1116_2025", "3b"),
        ("form_1116_2025", "10"),
        ("form_1116_2025", "18"),
    }
    actual = {
        (row["document_id"], str(row["line"])): row
        for row in report["rows"]
        if (row["document_id"], str(row["line"])) in expected
    }
    assert all(row["status"] == "multi_range" for row in actual.values())
    assert len(actual) == len(expected)
    assert report["counts"]["classification"]["multi_range"] >= len(expected)
