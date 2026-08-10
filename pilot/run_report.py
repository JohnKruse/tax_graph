"""Report a derivation run the way every M20 round needs it reported.

This module is deliberately outside ``tax_graph/``.  It reads the YAML that
``experiments/derive_cells_s25.py`` already writes and produces the numbers a
round is accepted or rejected on, so those numbers stop being retyped as
throwaway one-liners and start being reproducible by whoever ran the round.

Two rules are baked in because both were learned the expensive way:

* **Coverage is reported against every printed anchor**, never against
  attempted rows.  The derived-over-attempted denominator is what hid 32
  formulas until S89.
* **A regression is a row-level fact**, not a total.  Counts can stay flat
  while individual rows swap places, so the floor check compares each row that
  derived or repaired in the baseline against its status now.

Usage::

    python pilot/run_report.py <RUN_DIR> [--baseline DIR [--baseline DIR ...]]

A baseline may be given more than once because a corpus baseline is sometimes
split across run directories.  With no baseline the report is a snapshot, which
is the right shape for a document's first run.
"""

from __future__ import annotations

import argparse
import pathlib
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

import yaml


REPORT_SUFFIX = "_derive_cells_report.yaml"
REPORT_PREFIX = "m20_s26_"
SUCCESS_STATUSES = frozenset({"derived", "repaired"})


@dataclass
class DocumentReport:
    """One document's slice of a run."""

    document_id: str
    printed_anchors: int
    rows: int
    attempted: int
    status_counts: dict[str, int]
    outcome_counts: dict[str, int]
    cost: float
    failures: dict[str, int]
    warnings: dict[str, int]
    rows_by_line: dict[str, Mapping[str, Any]] = field(repr=False, default_factory=dict)
    process_mode: str = "all"

    @property
    def covered(self) -> int:
        """Rows that produced an answer we would ship."""
        return sum(self.status_counts.get(name, 0) for name in SUCCESS_STATUSES)

    @property
    def coverage(self) -> float:
        """Covered rows over every printed anchor, not over attempted."""
        if not self.printed_anchors:
            return 0.0
        return 100.0 * self.covered / self.printed_anchors


def discover_documents(run_dir: pathlib.Path) -> list[str]:
    """Return the document ids a run directory holds, in sorted order."""
    found = []
    for path in run_dir.glob(f"{REPORT_PREFIX}*{REPORT_SUFFIX}"):
        stem = path.name[len(REPORT_PREFIX):-len(REPORT_SUFFIX)]
        if stem:
            found.append(stem)
    return sorted(found)


def load_document(run_dir: pathlib.Path, document_id: str) -> DocumentReport | None:
    """Read one document report, or return None when the run lacks it."""
    path = run_dir / f"{REPORT_PREFIX}{document_id}{REPORT_SUFFIX}"
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    detail = data.get("rows_detail") or []
    outcomes: Counter[str] = Counter()
    cost = 0.0
    by_line: dict[str, Mapping[str, Any]] = {}
    for row in detail:
        if not isinstance(row, Mapping):
            continue
        outcomes[str(row.get("model_outcome") or "-")] += 1
        cost += float(row.get("cost") or 0.0)
        by_line[str(row.get("line") or "").lower()] = row
    validation = data.get("validation") or {}
    return DocumentReport(
        document_id=document_id,
        printed_anchors=int(data.get("line_anchor_count") or 0),
        rows=int(data.get("rows") or len(detail)),
        attempted=int(data.get("rows_attempted") or 0),
        status_counts=dict(data.get("row_status_counts") or {}),
        outcome_counts=dict(outcomes),
        cost=cost,
        failures=dict(validation.get("validator_failures_by_kind") or {}),
        warnings=dict(validation.get("validator_warnings_by_kind") or {}),
        rows_by_line=by_line,
        process_mode=str(data.get("process_mode") or "all"),
    )


def load_run(run_dir: pathlib.Path, documents: Iterable[str] | None = None) -> list[DocumentReport]:
    """Read every document report in a run directory."""
    wanted = list(documents) if documents else discover_documents(run_dir)
    reports = []
    for document_id in wanted:
        report = load_document(run_dir, document_id)
        if report is not None:
            reports.append(report)
    return reports


def find_regressions(
    current: Iterable[DocumentReport],
    baselines: Iterable[DocumentReport],
) -> tuple[list[dict[str, Any]], int]:
    """Return rows that lost a shippable answer, and the baseline row count.

    A row counts as protected when the baseline had it at ``derived`` or
    ``repaired``.  Absent-from-current counts as a regression: a row that
    stopped being produced at all is not an improvement.
    """
    now = {report.document_id: report for report in current}
    regressions: list[dict[str, Any]] = []
    protected = 0
    for base in baselines:
        after = now.get(base.document_id)
        for line, row in base.rows_by_line.items():
            if str(row.get("status")) not in SUCCESS_STATUSES:
                continue
            protected += 1
            current_row = after.rows_by_line.get(line) if after else None
            status = str(current_row.get("status")) if current_row else "ABSENT"
            if status in SUCCESS_STATUSES:
                continue
            regressions.append({
                "document_id": base.document_id,
                "line": line,
                "was": str(row.get("status")),
                "now": status,
                "error": str((current_row or {}).get("error") or "")[:70],
            })
    return regressions, protected


def _merge(counters: Iterable[Mapping[str, int]]) -> dict[str, int]:
    total: Counter[str] = Counter()
    for counter in counters:
        total.update(counter)
    return dict(total)


def format_report(
    reports: list[DocumentReport],
    regressions: list[dict[str, Any]] | None = None,
    protected: int = 0,
) -> str:
    """Render the report a round is judged on."""
    lines = [
        "%-24s %7s %7s %7s %7s %7s  %s" % (
            "document", "anchors", "derived", "repair", "error", "skip", "coverage",
        ),
    ]
    modes = sorted({report.process_mode for report in reports})
    lines.append("PROCESS " + ", ".join(modes))
    for report in sorted(reports, key=lambda item: item.document_id):
        lines.append("%-24s %7d %7d %7d %7d %7d  %5.1f%%" % (
            report.document_id,
            report.printed_anchors,
            report.status_counts.get("derived", 0),
            report.status_counts.get("repaired", 0),
            report.status_counts.get("errored", 0),
            report.status_counts.get("skipped", 0),
            report.coverage,
        ))
    anchors = sum(report.printed_anchors for report in reports)
    covered = sum(report.covered for report in reports)
    cost = sum(report.cost for report in reports)
    coverage = 100.0 * covered / anchors if anchors else 0.0
    lines.append("")
    lines.append("COVERAGE %d of %d printed anchors (%.1f%%) across %d documents, cost $%.4f" % (
        covered, anchors, coverage, len(reports), cost,
    ))
    outcomes = _merge(report.outcome_counts for report in reports)
    lines.append("OUTCOMES expression %d, model-stated input %d, no answer %d" % (
        outcomes.get("model_stated_expression", 0),
        outcomes.get("model_stated_input", 0),
        outcomes.get("-", 0),
    ))
    failures = _merge(report.failures for report in reports)
    if failures:
        ranked = sorted(failures.items(), key=lambda item: (-item[1], item[0]))
        lines.append("FAILURES " + ", ".join("%s %d" % pair for pair in ranked))
    warnings = _merge(report.warnings for report in reports)
    if warnings:
        ranked = sorted(warnings.items(), key=lambda item: (-item[1], item[0]))
        lines.append("WARNINGS " + ", ".join("%s %d" % pair for pair in ranked))
    if regressions is not None:
        lines.append("")
        lines.append("FLOOR %d protected baseline rows, %d regressed" % (protected, len(regressions)))
        for item in regressions:
            lines.append("  %s line %s: %s -> %s  %s" % (
                item["document_id"], item["line"], item["was"], item["now"], item["error"],
            ))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir", type=pathlib.Path)
    parser.add_argument("--baseline", type=pathlib.Path, action="append", default=[])
    parser.add_argument("--document", action="append", default=[])
    args = parser.parse_args(argv)

    reports = load_run(args.run_dir, args.document or None)
    if not reports:
        parser.error("no derive_cells reports found in %s" % args.run_dir)
    regressions = None
    protected = 0
    if args.baseline:
        baselines: list[DocumentReport] = []
        for path in args.baseline:
            baselines.extend(load_run(path))
        regressions, protected = find_regressions(reports, baselines)
    print(format_report(reports, regressions, protected))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
