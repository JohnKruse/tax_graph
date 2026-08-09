"""Tests for the pilot run report.

Fixtures are synthetic on purpose.  The report must be checkable without the
untracked `.cache` artifacts or a live run, which is the drift that made the
2441 denominator counts fail as a code regression.
"""

from __future__ import annotations

import pathlib

import yaml

from pilot.run_report import (
    discover_documents,
    find_regressions,
    format_report,
    load_run,
)


def _write_report(
    run_dir: pathlib.Path,
    document_id: str,
    rows: list[dict[str, object]],
    printed_anchors: int,
) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        key = {"error": "errored"}.get(str(row["status"]), str(row["status"]))
        counts[key] = counts.get(key, 0) + 1
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "document_id": document_id,
        "line_anchor_count": printed_anchors,
        "rows": len(rows),
        "rows_attempted": sum(1 for row in rows if row["status"] != "skipped"),
        "row_status_counts": counts,
        "rows_detail": rows,
        "validation": {"validator_failures_by_kind": {}, "validator_warnings_by_kind": {}},
    }
    path = run_dir / f"m20_s26_{document_id}_derive_cells_report.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")


def test_coverage_is_reported_against_every_printed_anchor(tmp_path: pathlib.Path) -> None:
    # Two of five printed anchors produce an answer.  Reporting against the
    # three attempted rows would claim 67%; the honest number is 40%.
    _write_report(
        tmp_path,
        "form_test_2025",
        [
            {"line": "1", "status": "derived", "model_outcome": "model_stated_expression", "cost": 0.01},
            {"line": "2", "status": "repaired", "model_outcome": "model_stated_input", "cost": 0.01},
            {"line": "3", "status": "error", "model_outcome": "-", "cost": 0.01},
        ],
        printed_anchors=5,
    )

    report = load_run(tmp_path)[0]

    assert report.printed_anchors == 5
    assert report.covered == 2
    assert round(report.coverage, 1) == 40.0
    assert "COVERAGE 2 of 5 printed anchors (40.0%)" in format_report([report])


def test_a_row_that_loses_its_answer_is_a_regression(tmp_path: pathlib.Path) -> None:
    baseline = tmp_path / "base"
    current = tmp_path / "now"
    _write_report(
        baseline,
        "form_test_2025",
        [
            {"line": "1", "status": "derived"},
            {"line": "2", "status": "derived"},
        ],
        printed_anchors=2,
    )
    # Same totals, different rows: line 2 broke and an unattempted row landed.
    _write_report(
        current,
        "form_test_2025",
        [
            {"line": "1", "status": "derived"},
            {"line": "2", "status": "error", "error": "payload"},
        ],
        printed_anchors=2,
    )

    regressions, protected = find_regressions(load_run(current), load_run(baseline))

    assert protected == 2
    assert [(item["line"], item["was"], item["now"]) for item in regressions] == [("2", "derived", "error")]


def test_a_row_that_vanishes_counts_as_a_regression(tmp_path: pathlib.Path) -> None:
    baseline = tmp_path / "base"
    current = tmp_path / "now"
    _write_report(baseline, "form_test_2025", [{"line": "9", "status": "repaired"}], printed_anchors=1)
    _write_report(current, "form_test_2025", [{"line": "1", "status": "derived"}], printed_anchors=1)

    regressions, protected = find_regressions(load_run(current), load_run(baseline))

    assert protected == 1
    assert regressions[0]["now"] == "ABSENT"


def test_a_baseline_split_across_directories_is_one_floor(tmp_path: pathlib.Path) -> None:
    # The real temperature-0 baseline lives in two run directories.
    first = tmp_path / "b1"
    second = tmp_path / "b2"
    current = tmp_path / "now"
    _write_report(first, "form_a_2025", [{"line": "1", "status": "derived"}], printed_anchors=1)
    _write_report(second, "form_b_2025", [{"line": "1", "status": "derived"}], printed_anchors=1)
    _write_report(current, "form_a_2025", [{"line": "1", "status": "derived"}], printed_anchors=1)
    _write_report(current, "form_b_2025", [{"line": "1", "status": "error"}], printed_anchors=1)

    baselines = load_run(first) + load_run(second)
    regressions, protected = find_regressions(load_run(current), baselines)

    assert protected == 2
    assert [item["document_id"] for item in regressions] == ["form_b_2025"]


def test_documents_are_discovered_and_a_first_run_needs_no_baseline(tmp_path: pathlib.Path) -> None:
    _write_report(tmp_path, "schedule_a_2025", [{"line": "1", "status": "derived"}], printed_anchors=1)
    _write_report(tmp_path, "schedule_b_2025", [{"line": "1", "status": "derived"}], printed_anchors=1)

    assert discover_documents(tmp_path) == ["schedule_a_2025", "schedule_b_2025"]
    rendered = format_report(load_run(tmp_path))
    assert "across 2 documents" in rendered
    assert "FLOOR" not in rendered
