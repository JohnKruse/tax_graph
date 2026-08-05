"""Build a readable, band-aware diff of derivation run reports.

The derivation harness writes one ``*_derive_cells_report.yaml`` file per
document.  This module treats those files as immutable pipeline evidence and
builds a comparison projection without contacting a provider or writing graph
state.  The latest run is compared with the immediately previous run, while
the preceding three runs provide a noise band for nondeterministic counts.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

import yaml


DERIVATION_REPORT_SUFFIX = "_derive_cells_report.yaml"
DEFAULT_BASELINE_WINDOW = 3
_BAND_METRICS = ("derived", "attempted", "resolved", "gapped", "errored", "derived_rate")


@dataclass(frozen=True)
class _DocumentSnapshot:
    """Normalized metrics and rows for one document in one run."""

    document_id: str
    run_id: str
    source_path: str | None
    present: bool
    metrics: Mapping[str, int | float | None]
    rows: Mapping[str, Mapping[str, Any]]
    findings: tuple[dict[str, Any], ...]
    empty_reason: str | None = None


@dataclass(frozen=True)
class _Run:
    """One ordered input run and the reports found in it."""

    run_id: str
    source_path: Path
    reports: Mapping[str, _DocumentSnapshot]


def _ascii(value: Any, *, limit: int = 500) -> str:
    """Return bounded ASCII text for a human-facing report."""
    text = str(value).encode("ascii", errors="replace").decode("ascii")
    return text[:limit]


def _number(value: Any, default: int = 0) -> int:
    """Coerce a report count without accepting booleans or fractional values."""
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _mapping(value: Any) -> Mapping[str, Any]:
    """Return a mapping or an empty mapping for optional report sections."""
    return value if isinstance(value, Mapping) else {}


def _json_key(value: Any) -> str:
    """Serialize an expression deterministically for comparison."""
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _rendered_expression(row: Mapping[str, Any]) -> str | None:
    """Use the harness rendering, with a deterministic fallback for old reports."""
    rendered = row.get("rendered")
    if rendered not in (None, ""):
        return _ascii(rendered, limit=1000)
    expression = row.get("expression")
    if expression is None:
        return None
    return _ascii(json.dumps(expression, sort_keys=True, ensure_ascii=True), limit=1000)


def _finding_detail(value: Any) -> tuple[str, str]:
    """Extract a stable finding kind and a bounded display detail."""
    if isinstance(value, Mapping):
        kind = value.get("kind") or value.get("reason") or value.get("node_id") or "unknown"
        message = value.get("message") or value.get("reason") or value.get("node_id") or kind
        return _ascii(kind, limit=160), _ascii(message)
    return "value", _ascii(value)


def _finding_id(category: str, line: str, kind: str, detail: str = "") -> str:
    """Build a stable finding identity that ignores changing prose."""
    subject = detail if category == "unresolved_external_node" else ""
    return ":".join(part for part in (category, line, kind, subject) if part)


def _row_findings(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Collect row-level findings without turning prose changes into new findings."""
    line = _ascii(row.get("line", "<unknown>"), limit=80)
    findings: list[dict[str, Any]] = []

    for field, category in (
        ("validation_failures", "validator_failure"),
        ("validation_warnings", "validator_warning"),
        ("dropped_instruction_sections", "instruction_section_dropped"),
    ):
        values = row.get(field) or []
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
            values = [values]
        for value in values:
            kind, detail = _finding_detail(value)
            findings.append(
                {
                    "id": _finding_id(category, line, kind),
                    "category": category,
                    "line": line,
                    "kind": kind,
                    "message": detail,
                }
            )

    external = row.get("unresolved_external_nodes") or []
    if not isinstance(external, Sequence) or isinstance(external, (str, bytes)):
        external = [external]
    for value in external:
        kind, detail = _finding_detail(value)
        findings.append(
            {
                "id": _finding_id("unresolved_external_node", line, kind, detail),
                "category": "unresolved_external_node",
                "line": line,
                "kind": kind,
                "message": detail,
            }
        )

    error = row.get("error")
    if error:
        error_text = _ascii(error)
        match = re.match(r"([A-Za-z_][A-Za-z0-9_.]*)", error_text)
        kind = match.group(1) if match else "row_error"
        findings.append(
            {
                "id": _finding_id("row_error", line, kind),
                "category": "row_error",
                "line": line,
                "kind": kind,
                "message": error_text,
            }
        )

    status = _ascii(row.get("status", ""), limit=80)
    if status in {"gapped", "errored"} and not error:
        findings.append(
            {
                "id": _finding_id("row_status", line, status),
                "category": "row_status",
                "line": line,
                "kind": status,
                "message": f"row status is {status}",
            }
        )
    return findings


def _rows_from_report(report: Mapping[str, Any], *, document_id: str) -> dict[str, Mapping[str, Any]]:
    """Index rows by printed line and fail closed on duplicate identities."""
    raw_rows = report.get("rows_detail") or []
    if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes)):
        raise ValueError(f"{document_id}: rows_detail must be a list")
    rows: dict[str, Mapping[str, Any]] = {}
    for raw_row in raw_rows:
        if not isinstance(raw_row, Mapping):
            raise ValueError(f"{document_id}: rows_detail contains a non-object row")
        line = _ascii(raw_row.get("line", ""), limit=80)
        if not line:
            raise ValueError(f"{document_id}: derived row has no printed line")
        if line in rows:
            raise ValueError(f"{document_id}: duplicate derived row for printed line {line}")
        rows[line] = raw_row
    return rows


def _snapshot_from_report(report: Mapping[str, Any], *, run_id: str, source_path: Path) -> _DocumentSnapshot:
    """Normalize one harness report into the fields needed by the diff."""
    document_id = _ascii(report.get("document_id", ""), limit=160)
    if not document_id:
        raise ValueError(f"{source_path}: derivation report has no document_id")
    validation = _mapping(report.get("validation"))
    status_counts = dict(_mapping(report.get("row_status_counts")))
    if not status_counts:
        status_counts = dict(validation.get("row_status_counts") or {})

    rows = _rows_from_report(report, document_id=document_id)
    attempted = _number(report.get("rows_attempted"), _number(validation.get("attempted")))
    selected = _number(report.get("rows"), len(rows))
    derived = _number(status_counts.get("derived"), _number(validation.get("derived")))
    repaired = _number(status_counts.get("repaired"), _number(validation.get("repaired")))
    gapped = _number(status_counts.get("gapped"), _number(validation.get("gapped")))
    errored = _number(status_counts.get("errored"), _number(validation.get("errored")))
    skipped = _number(status_counts.get("skipped"), _number(report.get("skipped")))
    resolved = derived + repaired
    derived_rate = (derived / attempted) if attempted else None
    empty = not rows and attempted == 0
    empty_reason = None
    if empty:
        empty_reason = _ascii(
            report.get("reason") or report.get("empty_reason") or "no derivation rows were produced",
            limit=240,
        )

    findings: list[dict[str, Any]] = []
    for row in rows.values():
        findings.extend(_row_findings(row))
    return _DocumentSnapshot(
        document_id=document_id,
        run_id=run_id,
        source_path=str(source_path.resolve()),
        present=True,
        metrics={
            "selected": selected,
            "attempted": attempted,
            "derived": derived,
            "repaired": repaired,
            "resolved": resolved,
            "gapped": gapped,
            "errored": errored,
            "skipped": skipped,
            "outline_nodes": _number(report.get("outline_node_count")),
            "line_anchors": _number(report.get("line_anchor_count")),
            "derived_rate": derived_rate,
        },
        rows=rows,
        findings=tuple(sorted(findings, key=lambda item: str(item["id"]))),
        empty_reason=empty_reason,
    )


def _missing_snapshot(document_id: str, run_id: str, reason: str) -> _DocumentSnapshot:
    """Represent a missing expected report explicitly instead of dropping it."""
    return _DocumentSnapshot(
        document_id=document_id,
        run_id=run_id,
        source_path=None,
        present=False,
        metrics={
            "selected": 0,
            "attempted": 0,
            "derived": 0,
            "repaired": 0,
            "resolved": 0,
            "gapped": 0,
            "errored": 0,
            "skipped": 0,
            "outline_nodes": 0,
            "line_anchors": 0,
            "derived_rate": None,
        },
        rows={},
        findings=(),
        empty_reason=reason,
    )


def _run_id_for_path(path: Path, index: int) -> str:
    """Derive a readable run id while keeping explicit input order authoritative."""
    if path.is_dir():
        candidate = path.name
    else:
        candidate = path.stem
    return _ascii(candidate or f"run_{index + 1}", limit=120)


def _report_paths(run_path: Path) -> list[Path]:
    """Find top-level derivation reports in a run directory."""
    if run_path.is_file():
        return [run_path] if run_path.name.endswith(DERIVATION_REPORT_SUFFIX) else []
    return sorted(run_path.glob(f"*{DERIVATION_REPORT_SUFFIX}"))


def _load_run(path: str | Path, *, index: int) -> _Run:
    """Load and validate one ordered run directory."""
    source_path = Path(path).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"run path does not exist: {source_path}")
    report_paths = _report_paths(source_path)
    if not report_paths:
        raise ValueError(f"run path has no {DERIVATION_REPORT_SUFFIX} files: {source_path}")
    run_id = _run_id_for_path(source_path, index)
    reports: dict[str, _DocumentSnapshot] = {}
    for report_path in report_paths:
        payload = yaml.safe_load(report_path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError(f"{report_path}: derivation report must be an object")
        snapshot = _snapshot_from_report(payload, run_id=run_id, source_path=report_path)
        if snapshot.document_id in reports:
            raise ValueError(f"{source_path}: duplicate report for {snapshot.document_id}")
        reports[snapshot.document_id] = snapshot
    return _Run(run_id=run_id, source_path=source_path, reports=reports)


def _public_snapshot(snapshot: _DocumentSnapshot) -> dict[str, Any]:
    """Serialize a snapshot without exposing its internal row index."""
    result: dict[str, Any] = {
        "run_id": snapshot.run_id,
        "present": snapshot.present,
        "source": snapshot.source_path,
        "status": "reported" if snapshot.present and snapshot.empty_reason is None else "empty" if snapshot.present else "missing",
        "absolute": dict(snapshot.metrics),
    }
    if snapshot.empty_reason:
        result["reason"] = snapshot.empty_reason
    return result


def _band(snapshots: Iterable[_DocumentSnapshot]) -> dict[str, dict[str, Any]]:
    """Return observed min/max values for the preceding runs."""
    result: dict[str, dict[str, Any]] = {}
    for metric in _BAND_METRICS:
        values = [
            (snapshot.run_id, snapshot.metrics.get(metric))
            for snapshot in snapshots
            if snapshot.present and snapshot.metrics.get(metric) is not None
        ]
        if not values:
            continue
        numbers = [float(value) for _, value in values]
        minimum = min(numbers)
        maximum = max(numbers)
        result[metric] = {
            "min": int(minimum) if minimum.is_integer() else minimum,
            "max": int(maximum) if maximum.is_integer() else maximum,
            "values": [
                {"run_id": run_id, "value": value}
                for run_id, value in values
            ],
        }
    return result


def _metric_delta(current: _DocumentSnapshot, previous: _DocumentSnapshot | None) -> dict[str, Any]:
    """Compare current metrics with the immediately preceding report."""
    if not current.present or previous is None or not previous.present:
        return {}
    delta: dict[str, Any] = {}
    for metric in ("derived", "attempted", "resolved", "repaired", "gapped", "errored", "skipped", "derived_rate"):
        current_value = current.metrics.get(metric)
        previous_value = previous.metrics.get(metric)
        if current_value is None or previous_value is None:
            difference = None
        else:
            difference = current_value - previous_value
        delta[metric] = {
            "previous": previous_value,
            "current": current_value,
            "delta": difference,
        }
    return delta


def _expression_changes(
    current: _DocumentSnapshot,
    previous: _DocumentSnapshot | None,
    *,
    attention: bool,
) -> list[dict[str, Any]]:
    """Show every changed expression with both deterministic renderings."""
    if previous is None or not previous.present:
        return []
    changes: list[dict[str, Any]] = []
    for line in sorted(set(current.rows) | set(previous.rows)):
        current_row = current.rows.get(line)
        previous_row = previous.rows.get(line)
        current_expression = current_row.get("expression") if current_row else None
        previous_expression = previous_row.get("expression") if previous_row else None
        if _json_key(current_expression) == _json_key(previous_expression):
            continue
        changes.append(
            {
                "line": line,
                "attention": attention,
                "previous": _rendered_expression(previous_row) if previous_row else None,
                "current": _rendered_expression(current_row) if current_row else None,
                "previous_status": previous_row.get("status") if previous_row else "missing",
                "current_status": current_row.get("status") if current_row else "missing",
            }
        )
    return changes


def _finding_diff(current: _DocumentSnapshot, previous: _DocumentSnapshot | None) -> dict[str, list[dict[str, Any]]]:
    """Return findings that appeared or cleared in the immediate comparison."""
    if previous is None or not previous.present:
        return {"appeared": [], "cleared": []}
    current_by_id = {item["id"]: item for item in current.findings}
    previous_by_id = {item["id"]: item for item in previous.findings}
    appeared = [current_by_id[key] for key in sorted(set(current_by_id) - set(previous_by_id))]
    cleared = [previous_by_id[key] for key in sorted(set(previous_by_id) - set(current_by_id))]
    return {"appeared": appeared, "cleared": cleared}


def build_run_summary(
    run_paths: Sequence[str | Path],
    *,
    expected_documents: Sequence[str] = (),
    baseline_window: int = DEFAULT_BASELINE_WINDOW,
) -> dict[str, Any]:
    """Build the S63 summary from ordered, provider-free run artifacts.

    ``run_paths`` is ordered oldest to newest.  Only the preceding
    ``baseline_window`` runs contribute to a document's observed band.  A
    missing expected document remains visible as a named ``missing`` state.
    """
    if len(run_paths) < 1:
        raise ValueError("at least one run path is required")
    if baseline_window < 1:
        raise ValueError("baseline_window must be at least 1")
    runs = tuple(_load_run(path, index=index) for index, path in enumerate(run_paths))
    expected = {_ascii(document, limit=160) for document in expected_documents if str(document).strip()}
    document_ids = set(expected)
    for run in runs:
        document_ids.update(run.reports)

    current_run = runs[-1]
    previous_run = runs[-2] if len(runs) > 1 else None
    documents: dict[str, Any] = {}
    attention_documents: list[str] = []
    for document_id in sorted(document_ids):
        current = current_run.reports.get(document_id)
        if current is None:
            current = _missing_snapshot(document_id, current_run.run_id, "expected report was not produced in the current run")
        previous = previous_run.reports.get(document_id) if previous_run else None
        baseline = [
            run.reports[document_id]
            for run in runs[max(0, len(runs) - 1 - baseline_window) : -1]
            if document_id in run.reports
        ]
        observed_band = _band(baseline)
        outside_band_metrics: list[str] = []
        if current.present and observed_band:
            for metric in _BAND_METRICS:
                value = current.metrics.get(metric)
                limits = observed_band.get(metric)
                if value is not None and limits and not (limits["min"] <= value <= limits["max"]):
                    outside_band_metrics.append(metric)
        if not current.present:
            movement = "missing_report"
        elif not baseline:
            movement = "no_baseline"
        elif outside_band_metrics:
            movement = "outside_band"
        else:
            movement = "in_band_noise"
        if movement in {"outside_band", "missing_report"}:
            attention_documents.append(document_id)
        finding_diff = _finding_diff(current, previous)
        changes = _expression_changes(
            current,
            previous,
            attention=movement == "outside_band",
        )
        documents[document_id] = {
            "current": _public_snapshot(current),
            "previous": _public_snapshot(previous) if previous else None,
            "delta": _metric_delta(current, previous),
            "derived_over_attempted": {
                "previous": previous.metrics.get("derived_rate") if previous and previous.present else None,
                "current": current.metrics.get("derived_rate") if current.present else None,
                "delta": (
                    current.metrics.get("derived_rate") - previous.metrics.get("derived_rate")
                    if previous and previous.present and current.metrics.get("derived_rate") is not None and previous.metrics.get("derived_rate") is not None
                    else None
                ),
            },
            "band": observed_band,
            "movement": movement,
            "outside_band_metrics": outside_band_metrics,
            "expression_changes": changes,
            "findings": finding_diff,
        }

    years = {
        str(_mapping(yaml.safe_load(Path(report.source_path).read_text(encoding="utf-8"))).get("year"))
        for run in runs
        for report in run.reports.values()
        if report.source_path
    }
    years.discard("None")
    if len(years) > 1:
        raise ValueError(f"run reports contain multiple tax years: {sorted(years)}")
    year = next(iter(years), None)
    return {
        "schema_version": 1,
        "year": year,
        "run_order": [
            {
                "run_id": run.run_id,
                "source": str(run.source_path),
                "documents": sorted(run.reports),
            }
            for run in runs
        ],
        "current_run": current_run.run_id,
        "previous_run": previous_run.run_id if previous_run else None,
        "baseline_window": baseline_window,
        "attention_documents": attention_documents,
        "documents": documents,
        "full_run_contract": {
            "cadence": (
                "Run before publish after any shared-layer change (evidence, schema, vocabulary, "
                "or operation registry); otherwise run every fourth or fifth localized round."
            ),
            "must_include": [
                "corpus derivation reports",
                "candidate graph",
                "three-column review table",
                "full test suite",
            ],
            "current_round_scope": "summary only; no provider call and no candidate graph promotion",
        },
    }


def _markdown_cell(value: Any) -> str:
    """Escape one value for a pipe-delimited Markdown table."""
    if value is None:
        return "-"
    return _ascii(value, limit=1000).replace("|", "\\|").replace("\n", " ")


def _format_metric(value: Any) -> str:
    """Format counts and rates compactly without presenting a verdict."""
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def render_run_summary_markdown(summary: Mapping[str, Any]) -> str:
    """Render the summary with the delta first and absolute numbers below it."""
    documents = _mapping(summary.get("documents"))
    lines = [
        "# Derivation run summary",
        "",
        "This is an evidence diff, not a tax-correctness verdict.",
        "",
        f"- Year: {_markdown_cell(summary.get('year'))}",
        f"- Current run: {_markdown_cell(summary.get('current_run'))}",
        f"- Previous run: {_markdown_cell(summary.get('previous_run'))}",
        f"- Rolling baseline: previous {_markdown_cell(summary.get('baseline_window'))} runs",
        "",
        "## Attention",
        "",
    ]
    attention = summary.get("attention_documents") or []
    if attention:
        lines.extend(f"- `{_markdown_cell(document)}` requires attention: movement outside its observed band or a missing report." for document in attention)
    else:
        lines.append("- None: no document moved outside its observed band and no current report was missing.")

    lines.extend(
        [
            "",
            "## Delta by document",
            "",
            "| document | derived / attempted | delta | observed derived band | movement |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for document_id, item in documents.items():
        current = _mapping(item.get("current"))
        absolute = _mapping(current.get("absolute"))
        delta = _mapping(item.get("delta"))
        derived = _mapping(delta.get("derived"))
        band = _mapping(item.get("band")).get("derived")
        band_text = "-"
        if band:
            band_text = f"{_format_metric(band.get('min'))}..{_format_metric(band.get('max'))}"
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{_markdown_cell(document_id)}`",
                    f"{_format_metric(absolute.get('derived'))} / {_format_metric(absolute.get('attempted'))}",
                    _format_metric(derived.get("delta")),
                    band_text,
                    _markdown_cell(item.get("movement")),
                )
            )
            + " |"
        )

    lines.extend(["", "## Document details", ""])
    for document_id, item in documents.items():
        current = _mapping(item.get("current"))
        absolute = _mapping(current.get("absolute"))
        delta = _mapping(item.get("delta"))
        band = _mapping(item.get("band"))
        lines.extend([f"### {document_id}", "", f"Movement: `{_markdown_cell(item.get('movement'))}`", ""])
        if current.get("reason"):
            lines.extend([f"Explicit empty/missing reason: {_markdown_cell(current.get('reason'))}", ""])
        lines.extend(
            [
                "Absolute current counts:",
                "",
                "| selected | attempted | derived | repaired | resolved | gapped | errored | skipped | derived rate |",
                "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
                "| "
                + " | ".join(
                    _format_metric(absolute.get(metric))
                    for metric in ("selected", "attempted", "derived", "repaired", "resolved", "gapped", "errored", "skipped", "derived_rate")
                )
                + " |",
                "",
            ]
        )
        if delta:
            lines.extend(["Immediate delta from the previous run:", "", "| metric | previous | current | delta |", "| --- | ---: | ---: | ---: |"])
            for metric, values in delta.items():
                values = _mapping(values)
                lines.append(
                    f"| {metric} | {_format_metric(values.get('previous'))} | {_format_metric(values.get('current'))} | {_format_metric(values.get('delta'))} |"
                )
            lines.append("")
        if band:
            lines.extend(["Observed band from the preceding runs:", "", "| metric | min | max | samples |", "| --- | ---: | ---: | --- |"])
            for metric, values in band.items():
                values = _mapping(values)
                samples = ", ".join(f"{sample.get('run_id')}={sample.get('value')}" for sample in values.get("values", []))
                lines.append(f"| {metric} | {_format_metric(values.get('min'))} | {_format_metric(values.get('max'))} | {_markdown_cell(samples)} |")
            lines.append("")

        changes = item.get("expression_changes") or []
        lines.extend(["Expression changes (all are shown; in-band changes are noise):", "", "| line | attention | previous rendering | current rendering |", "| --- | --- | --- | --- |"])
        if changes:
            for change in changes:
                lines.append(
                    f"| `{_markdown_cell(change.get('line'))}` | {_markdown_cell(change.get('attention'))} | {_markdown_cell(change.get('previous'))} | {_markdown_cell(change.get('current'))} |"
                )
        else:
            lines.append("| - | - | none | none |")
        lines.append("")

        finding_diff = _mapping(item.get("findings"))
        for heading, key in (("Findings appeared", "appeared"), ("Findings cleared", "cleared")):
            findings = finding_diff.get(key) or []
            lines.extend([f"{heading}:", "", "| line | kind | message |", "| --- | --- | --- |"])
            if findings:
                for finding in findings:
                    lines.append(f"| `{_markdown_cell(finding.get('line'))}` | {_markdown_cell(finding.get('kind'))} | {_markdown_cell(finding.get('message'))} |")
            else:
                lines.append("| - | - | none |")
            lines.append("")

    contract = _mapping(summary.get("full_run_contract"))
    lines.extend(["## Full-run contract", "", _markdown_cell(contract.get("cadence")), "", "A full run should include:", ""])
    for item in contract.get("must_include") or []:
        lines.append(f"- {_markdown_cell(item)}")
    lines.extend(["", f"Current round scope: {_markdown_cell(contract.get('current_round_scope'))}", ""])
    return "\n".join(lines)


def write_run_summary(summary: Mapping[str, Any], output: str | Path, *, root: str | Path) -> Path:
    """Write one Markdown artifact outside the repository root."""
    root_path = Path(root).resolve()
    output_path = Path(output).resolve()
    if output_path == root_path or root_path in output_path.parents:
        raise ValueError("run summary output must be outside repository root")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_run_summary_markdown(summary), encoding="ascii", newline="\n")
    return output_path


def summarize_runs_command(
    run_paths: Sequence[str | Path],
    *,
    output: str | Path,
    expected_documents: Sequence[str] = (),
    baseline_window: int = DEFAULT_BASELINE_WINDOW,
    root: str | Path,
) -> int:
    """Build and write the provider-free S63 summary command."""
    summary = build_run_summary(
        run_paths,
        expected_documents=expected_documents,
        baseline_window=baseline_window,
    )
    output_path = write_run_summary(summary, output, root=root)
    print("=== derivation run summary ===")
    print(f"  current: {summary['current_run']}")
    print(f"  previous: {summary['previous_run'] or '-'}")
    print(f"  documents: {len(summary['documents'])}")
    print(f"  attention: {len(summary['attention_documents'])}")
    print(f"  summary: {output_path}")
    return 0
