"""Focused tests for the M20-S112 production replay harness."""

from __future__ import annotations

from pilot.replay_harness import run_replay


def test_s112_replays_at_least_twenty_recorded_cases_through_all_layers() -> None:
    """Keep the diagnostic fixture large enough to cover the named shape floor."""
    results = run_replay()
    assert len(results) >= 20
    mismatches = [result for result in results if not result.matches_expectation]
    assert not mismatches, "\n".join(
        f"{result.case_id}: actual={result.actual} expected={result.expected} errors={result.errors}"
        for result in mismatches
    )
    targets = {(result.document_id, result.line_anchor) for result in results}
    assert {
        ("form_1040_2025", "11a"),
        ("form_1040_2025", "35a"),
        ("form_1040_2025", "36"),
        ("schedule_1_2025", "10"),
        ("schedule_1a_2025", "9"),
        ("schedule_1a_2025", "12"),
        ("form_6251_2025", "13"),
        ("form_6251_2025", "18"),
        ("form_2441_2025", "8"),
        ("schedule_2_2025", "1z"),
    }.issubset(targets)
