"""Focused tests for the M20-S104 unclaimed-source partition pilot."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from source_extents import measure_source_extents, partition_unclaimed_text


ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def _report() -> dict:
    """Build the real corpus report for the focused S104 assertions."""
    return measure_source_extents(root=ROOT, year="2025")


def test_every_unclaimed_run_has_one_explicit_partition() -> None:
    """Every measured run is reported exactly once, including undecided runs."""
    report = _report()
    allowed = {"scaffolding", "rule_bearing", "undecided"}
    runs = report["unclaimed_runs"]
    counts = report["counts"]["unclaimed_partitions"]

    assert runs
    assert all(run["partition"] in allowed for run in runs)
    assert sum(counts.values()) == len(runs)
    assert all(run["preview"] for run in runs if run["partition"] == "undecided")


def test_rule_bearing_character_report_covers_all_corpus_documents() -> None:
    """The per-document report includes documents with zero rule-bearing gaps."""
    report = _report()
    document_ids = {str(row["document_id"]) for row in report["rows"]}
    by_document = report["unclaimed_rule_bearing_characters_by_document"]

    assert set(by_document) == document_ids
    assert all(isinstance(value, int) and value >= 0 for value in by_document.values())
    assert sum(by_document.values()) == report["counts"]["unclaimed_rule_bearing_characters"]


def test_known_rule_bearing_and_scaffolding_cases_are_not_undecided() -> None:
    """The S104 known answers stay visible in the partition report."""
    report = _report()
    simplified_note = next(
        run
        for run in report["unclaimed_runs"]
        if run["source_document_id"] == "instructions_form_1040_2025"
        and run["start"] == 118241
    )
    capital_loss_routes = [
        run
        for run in report["unclaimed_runs"]
        if run["source_document_id"] == "schedule_d_2025"
        and run["kind"] == "routing_sentence"
    ]
    dot_leader = next(
        run
        for run in report["unclaimed_runs"]
        if run["source_document_id"] == "schedule_d_2025"
        and run["start"] == 1386
    )
    footer = next(
        run
        for run in report["unclaimed_runs"]
        if "Cat. No." in run["preview"]
    )

    assert simplified_note["partition"] == "rule_bearing"
    assert capital_loss_routes
    assert all(run["partition"] == "rule_bearing" for run in capital_loss_routes)
    assert dot_leader["partition"] == "scaffolding"
    assert footer["partition"] == "scaffolding"


def test_partition_helper_defaults_to_honest_undecided() -> None:
    """Prose without structural rule evidence is not promoted by a cue guess."""
    assert partition_unclaimed_text("Short-term capital loss carryover.") == (
        "undecided",
        "no_structural_rule_evidence",
    )
    assert partition_unclaimed_text(". . . . . . 8b") == (
        "scaffolding",
        "field_marker_layout",
    )
    assert partition_unclaimed_text("If line 4 is over $10, enter the amount on line 5.") == (
        "rule_bearing",
        "condition_or_filer_instruction",
    )
