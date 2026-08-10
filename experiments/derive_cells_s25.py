"""Run the M20-S26 cell frame and property-validator bench.

The pure derivation function remains in ``tax_graph.extract.cells``.  This
caller is the reproducible boundary that loads acquired inputs, persists the
typed instruction frame and coverage report, and optionally calls the
configured provider for the real 1040.  It never writes drafts or graph state.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tax_graph.config import get_config_value, load_config, resolve_llm_model, resolve_llm_seed
from tax_graph.acquire.manifest import load_manifest
from tax_graph.extract.cells import (
    CellFrame,
    build_reference_inventory,
    build_cell_frame_from_document,
    derive_cells,
    get_structural_skip_reason,
    load_cell_prompt,
    _scoped_graph_nodes,
)
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.instruction_sections import write_instruction_sections_artifact
from tax_graph.extract.llm_client import build_llm_client
from tax_graph.io.loader import load_graph
from tax_graph.extract.outline import (
    _flatten_outline_nodes,
    build_instruction_sections_frame,
    build_outline_tree,
)
from tax_graph.extract.outline_pipeline import build_derivation_denominator


PROCESS_MODES = frozenset({"all", "broken"})
SUCCESS_STATUSES = frozenset({"derived", "repaired"})
REPORT_SUFFIX = "_derive_cells_report.yaml"
REPORT_PREFIX = "m20_s26_"


def persist_instruction_frame(
    *,
    root: str | Path,
    year: str,
    document_id: str = "form_1040_2025",
    output_dir: str | Path | None = None,
) -> tuple[Path, Path]:
    """Persist the deterministic instruction frame and its coverage report."""
    root_path = Path(root).resolve()
    destination = _output_destination(root_path, output_dir)
    document = load_document_input(document_id, year=year, root=root_path)
    frame = build_instruction_sections_frame(document, outline=build_outline_tree(document))
    frame = _portable_frame(frame, root_path)
    frame_path = write_instruction_sections_artifact(
        frame,
        destination / f"m20_s26_{document_id}_instruction_sections.yaml",
    )
    coverage_path = destination / f"m20_s26_{document_id}_instruction_sections_coverage.yaml"
    coverage_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": frame.schema_version,
                "year": frame.year,
                "source_document_id": frame.source_document_id,
                "section_count": len(frame.sections),
                "coverage": frame.coverage,
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="utf-8",
        newline="\n",
    )
    return frame_path, coverage_path


def _portable_frame(frame: Any, root: Path) -> Any:
    """Replace machine-specific source paths with repository-relative paths."""
    def relative(value: str | None) -> str | None:
        if value is None:
            return None
        path = Path(value)
        try:
            return path.resolve().relative_to(root).as_posix()
        except ValueError:
            return str(value).replace("\\", "/")

    sections = tuple(
        replace(section, locator=replace(section.locator, source_path=relative(section.locator.source_path)))
        for section in frame.sections
    )
    return replace(frame, source_path=relative(frame.source_path), sections=sections)


def _config_temperature(config: Any) -> float | None:
    """Return the configured sampling temperature, preserving an explicit zero.

    ``0`` is falsy, so a truthiness test here would silently discard the pinned
    value and hand the provider its own default.  Only ``None`` and ``""`` mean
    "unset".
    """
    value = get_config_value(config, "llm.temperature")
    if value is None or value == "":
        return None
    return float(value)


def _normalize_process(process: str) -> str:
    """Validate and normalize the corpus processing mode."""
    value = str(process or "all").strip().lower()
    if value not in PROCESS_MODES:
        choices = ", ".join(sorted(PROCESS_MODES))
        raise ValueError(f"process must be one of {choices}, got {process!r}")
    return value


def _report_path(run_dir: str | Path, document_id: str) -> Path:
    """Return the persisted derivation report for one document."""
    return Path(run_dir).resolve() / f"{REPORT_PREFIX}{document_id}{REPORT_SUFFIX}"


def _load_prior_report(run_dir: str | Path, document_id: str) -> dict[str, Any]:
    """Load one prior report used to select and merge a broken-only pass."""
    path = _report_path(run_dir, document_id)
    if not path.is_file():
        raise FileNotFoundError(f"prior derivation report not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"prior derivation report must be an object: {path}")
    recorded_document = str(payload.get("document_id") or "")
    if recorded_document != document_id:
        raise ValueError(
            f"prior derivation report document {recorded_document} does not match {document_id}"
        )
    rows = payload.get("rows_detail")
    if not isinstance(rows, list):
        raise ValueError(f"prior derivation report has no rows_detail list: {path}")
    return payload


def _row_key(row: Mapping[str, Any] | Any) -> str:
    """Return the stable per-document key used by reports and run floors."""
    if isinstance(row, Mapping):
        value = row.get("line")
    else:
        value = getattr(row, "line", "")
    return str(value or "").strip().lower()


def _prior_rows_by_line(report: Mapping[str, Any]) -> dict[str, list[Mapping[str, Any]]]:
    """Index prior rows by printed line while preserving repeated flow positions."""
    result: dict[str, list[Mapping[str, Any]]] = {}
    for row in report.get("rows_detail", []) or []:
        if not isinstance(row, Mapping):
            raise ValueError("prior derivation report has a non-object row")
        key = _row_key(row)
        if not key:
            raise ValueError("prior derivation report has a row without a line")
        result.setdefault(key, []).append(row)
    return result


def _prior_group(
    prior_rows: Mapping[str, Mapping[str, Any] | list[Mapping[str, Any]]],
    key: str,
) -> list[Mapping[str, Any]]:
    """Normalize one prior-line entry, including legacy test mappings."""
    value = prior_rows.get(key)
    if value is None:
        return []
    if isinstance(value, Mapping):
        return [value]
    if isinstance(value, list) and all(isinstance(item, Mapping) for item in value):
        return value
    raise ValueError(f"prior derivation report has malformed rows for line {key}")


def _source_fields(row: Mapping[str, Any] | Any) -> dict[str, str]:
    """Return the source packet fields that determine whether a row is reusable."""
    if isinstance(row, Mapping):
        label = row.get("label_before", row.get("label", ""))
        form_face = row.get("form_face_before", row.get("form_face_text", ""))
        instruction_text = row.get("instruction_text", "")
        instruction_locator = row.get("instruction_locator", "")
    else:
        metadata = getattr(row, "metadata", {}) or {}
        label = metadata.get("label_before", getattr(row, "label", ""))
        form_face = metadata.get("form_face_before", getattr(row, "form_face_text", ""))
        instruction_text = getattr(row, "instruction_text", "")
        instruction_locator = getattr(row, "instruction_locator", "")
    return {
        "label_before": str(label or ""),
        "form_face_before": str(form_face or ""),
        "instruction_text": str(instruction_text or ""),
        "instruction_locator": str(instruction_locator or ""),
    }


def _source_fingerprint(row: Mapping[str, Any] | Any) -> str:
    """Return a stable digest of the source evidence supplied to one row."""
    encoded = json.dumps(
        _source_fields(row),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _prior_row_is_reusable(
    source_row: Mapping[str, Any] | Any,
    prior_row: Mapping[str, Any] | None,
) -> bool:
    """Return whether a prior success belongs to the current source packet."""
    if prior_row is None:
        return False
    if str(prior_row.get("status") or "").lower() not in SUCCESS_STATUSES:
        return False
    recorded = str(prior_row.get("source_fingerprint") or "")
    if recorded:
        return recorded == _source_fingerprint(source_row)
    required = set(_source_fields(source_row))
    if not required.issubset(prior_row):
        return False
    return _source_fields(source_row) == _source_fields(prior_row)


def _frame_for_process(
    frame: CellFrame,
    *,
    process: str,
    prior_report: Mapping[str, Any] | None,
) -> tuple[CellFrame, dict[str, list[Mapping[str, Any]]]]:
    """Select provider work and return the prior rows needed for a merge.

    A broken-only pass never asks the provider about a uniquely identified row
    that already has a shippable answer. Repeated printed lines are rederived
    as a group because their occurrence in the form flow is the only stable
    local disambiguator available to this report format.
    """
    mode = _normalize_process(process)
    if mode == "all":
        return frame, {}
    if prior_report is None:
        raise ValueError("broken process requires a prior derivation report")
    prior_rows = _prior_rows_by_line(prior_report)
    frame_counts = Counter(_row_key(row) for row in frame.rows)
    selected = []
    for row in frame.rows:
        key = _row_key(row)
        group = _prior_group(prior_rows, key)
        reusable = (
            frame_counts[key] == 1
            and len(group) == 1
            and _prior_row_is_reusable(row, group[0])
        )
        if not reusable:
            selected.append(row)
    return CellFrame(selected), prior_rows


def _row_detail(row: Any) -> dict[str, Any]:
    """Serialize one derived row in the report schema."""
    return {
        "line": row.line,
        "source_fingerprint": _source_fingerprint(row),
        "label_before": row.metadata.get("label_before", row.label),
        "label_after": row.label,
        "form_face_before": row.metadata.get("form_face_before", row.form_face_text),
        "form_face_after": row.form_face_text,
        "status": row.status,
        "error": row.error,
        "expression": row.expression,
        "rendered": row.rendered,
        "validation_failures": row.metadata.get("validation_failures", []),
        "validation_warnings": row.metadata.get("validation_warnings", []),
        "repaired_after": row.metadata.get("repaired_after", []),
        "dropped_instruction_sections": row.metadata.get("dropped_instruction_sections", []),
        "source_findings": row.metadata.get("evidence_findings", []),
        "structural_skip_reason": get_structural_skip_reason(row.metadata),
        "model_outcome": row.metadata.get("model_outcome", ""),
        # What the model actually answered, kept even when it was rejected.
        # Without this a failing row can only be counted, not diagnosed.
        "attempted_payloads": row.metadata.get("attempted_payloads", []),
        "unresolved_external_nodes": row.metadata.get("unresolved_external_nodes", []),
        # The candidate writer consumes the exact evidence selected by the
        # provider-side derivation.  Keep it beside the expression so a
        # candidate can never be promoted without its citation.
        "instruction_text": row.instruction_text,
        "instruction_locator": row.instruction_locator,
        "quote": row.quote,
        "quote_span_id": row.quote_span_id,
        "evidence_spans": row.metadata.get("evidence_spans", []),
        "instruction_span_ids": row.metadata.get("instruction_span_ids", []),
        "model": row.model,
        "provider": row.provider,
        "prompt_tokens": row.prompt_tokens,
        "completion_tokens": row.completion_tokens,
        "cost": row.cost,
    }


def _merge_row_details(
    frame: CellFrame,
    current_rows: list[Mapping[str, Any]],
    prior_rows: Mapping[str, Mapping[str, Any] | list[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    """Merge current results with reusable prior successes without dropping rows."""
    current_by_line: dict[str, list[dict[str, Any]]] = {}
    for row in current_rows:
        key = _row_key(row)
        if not key:
            raise ValueError("current derivation result has a row without a line")
        current_by_line.setdefault(key, []).append(dict(row))
    frame_keys = [_row_key(row.as_dict()) for row in frame.rows]
    if any(not key for key in frame_keys):
        raise ValueError("current cell frame has a row without a line")
    frame_counts = Counter(frame_keys)
    unexpected = sorted(set(current_by_line) - set(frame_counts))
    if unexpected:
        raise ValueError(
            "current derivation result has rows outside the current frame: "
            + ", ".join(unexpected)
        )
    for key, rows in current_by_line.items():
        if len(rows) != frame_counts[key]:
            raise ValueError(
                f"current derivation result has {len(rows)} rows for line {key}; "
                f"expected {frame_counts[key]}"
            )
    merged: list[dict[str, Any]] = []
    positions: Counter[str] = Counter()
    for source_row in frame.rows:
        key = _row_key(source_row.as_dict())
        position = positions[key]
        positions[key] += 1
        prior_group = _prior_group(prior_rows, key)
        prior = prior_group[0] if len(prior_group) == 1 else None
        if frame_counts[key] == 1 and _prior_row_is_reusable(source_row, prior):
            carried = dict(prior)
            carried["source_fingerprint"] = _source_fingerprint(source_row)
            merged.append(carried)
        elif position < len(current_by_line.get(key, [])):
            merged.append(current_by_line[key][position])
        else:
            raise ValueError(f"current derivation result is missing row for line {key}")
    return merged


def _report_status_counts(rows: list[Mapping[str, Any]]) -> tuple[dict[str, int], dict[str, int]]:
    """Return normalized and raw row status counts for a merged report."""
    raw = Counter(str(row.get("status") or "pending") for row in rows)
    normalized = {
        "derived": raw.get("derived", 0),
        "repaired": raw.get("repaired", 0),
        "gapped": raw.get("gapped", 0),
        "errored": raw.get("error", 0) + raw.get("errored", 0),
        "skipped": raw.get("skipped", 0),
    }
    return normalized, dict(sorted(raw.items()))


def _merged_validation(
    result: Any,
    *,
    process: str,
    frame: CellFrame,
    prior_rows: Mapping[str, Mapping[str, Any] | list[Mapping[str, Any]]],
    merged_rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build validation totals whose scope matches the merged row report."""
    validation = dict(result.validation_report)
    if _normalize_process(process) == "all":
        return validation

    frame_counts = Counter(_row_key(row) for row in frame.rows)
    untouched = []
    for source_row in frame.rows:
        key = _row_key(source_row)
        group = _prior_group(prior_rows, key)
        if (
            frame_counts[key] == 1
            and len(group) == 1
            and _prior_row_is_reusable(source_row, group[0])
        ):
            untouched.append(group[0])
    status_counts, _ = _report_status_counts(merged_rows)
    validation["attempted"] = len(untouched) + int(result.validation.get("attempted", 0))
    validation["repaired"] = status_counts["repaired"]
    validation["gapped"] = status_counts["gapped"]
    validation["errored"] = status_counts["errored"]

    failures = Counter(validation.get("validator_failures_by_kind") or {})
    warnings = Counter(validation.get("validator_warnings_by_kind") or {})
    dropped = 0
    dropped_by_kind: Counter[str] = Counter()
    for row in untouched:
        for item in row.get("validation_failures", []) or []:
            if isinstance(item, Mapping) and item.get("kind"):
                failures[str(item["kind"])] += 1
        for kind in row.get("repaired_after", []) or []:
            failures[str(kind)] += 1
        for item in row.get("validation_warnings", []) or []:
            if isinstance(item, Mapping) and item.get("kind"):
                warnings[str(item["kind"])] += 1
        dropped_items = row.get("dropped_instruction_sections", []) or []
        dropped += len(dropped_items)
        for item in dropped_items:
            if isinstance(item, Mapping) and item.get("kind"):
                dropped_by_kind[str(item["kind"])] += 1
    validation["validator_failures_by_kind"] = dict(sorted(failures.items()))
    validation["validator_warnings_by_kind"] = dict(sorted(warnings.items()))
    validation["instruction_sections_dropped"] = int(
        validation.get("instruction_sections_dropped", 0)
    ) + dropped
    prior_drop_counts = Counter(validation.get("instruction_drops_by_kind") or {})
    prior_drop_counts.update(dropped_by_kind)
    validation["instruction_drops_by_kind"] = dict(sorted(prior_drop_counts.items()))
    return validation


def run_real_document(
    *,
    root: str | Path,
    year: str,
    document_id: str,
    output_dir: str | Path | None = None,
    process: str = "all",
    prior_run_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Derive one document and persist a full or merged aggregate report."""
    mode = _normalize_process(process)
    if mode == "broken" and prior_run_dir is None:
        raise ValueError("broken process requires prior_run_dir")
    root_path = Path(root).resolve()
    destination = _output_destination(root_path, output_dir)
    prior_report = (
        _load_prior_report(prior_run_dir, document_id)
        if mode == "broken" and prior_run_dir is not None
        else None
    )
    config = load_config(root=root_path)
    document = load_document_input(document_id, year=year, root=root_path, config=config)
    outline = build_outline_tree(document)
    outline_nodes = _flatten_outline_nodes(outline.children)
    denominator = build_derivation_denominator(document, outline=outline)
    frame = build_cell_frame_from_document(document)
    work_frame, prior_rows = _frame_for_process(
        frame,
        process=mode,
        prior_report=prior_report,
    )
    client = build_llm_client(config)
    prompt = load_cell_prompt(config, root=root_path)
    reference_inventory = build_reference_inventory(
        load_graph(year, root_path),
        manifest=load_manifest(root=root_path),
    )
    result = derive_cells(
        work_frame,
        prompt,
        None,
        client=client,
        model=resolve_llm_model(config, "micro"),
        provider=str(get_config_value(config, "llm.provider", "configured-provider")),
        # Read from config like generator.py, critic.py, micro.py and background.py
        # already do.  Without this the derivation path silently used the parameter
        # default of None, so llm.temperature never reached the provider.
        temperature=_config_temperature(config),
        seed=resolve_llm_seed(config),
        reference_inventory=reference_inventory,
    )
    current_row_details = [_row_detail(row) for row in result.rows]
    row_details = (
        _merge_row_details(frame, current_row_details, prior_rows)
        if mode == "broken"
        else current_row_details
    )
    status_counts, raw_status_counts = _report_status_counts(row_details)
    selected_rows = [
        row
        for row in row_details
        if not row.get("structural_skip_reason")
    ]
    validation = _merged_validation(
        result,
        process=mode,
        frame=frame,
        prior_rows=prior_rows,
        merged_rows=row_details,
    )
    unresolved_external_nodes = [
        {
            "form": document.document_id,
            "line": row["line"],
            **node,
        }
        for row in row_details
        for node in row.get("unresolved_external_nodes", [])
    ]
    # What THIS pass actually spent, kept apart from the merged totals.  The
    # merged `rows_attempted` and per-row `cost` carry the prior run's figures
    # forward, so without these a broken pass and a full pass are
    # indistinguishable except by the mode flag - and the saving that
    # justifies the mode cannot be checked at all.
    pass_rows = [_row_detail(row) for row in result.rows]
    pass_cost = sum(float(row.get("cost") or 0.0) for row in pass_rows)
    pass_status_counts, _ = _report_status_counts(pass_rows)
    report = {
        "document_id": document.document_id,
        "year": str(year),
        "process_mode": mode,
        "pass_rows_sent": len(pass_rows),
        "pass_rows_attempted": int(result.validation_report.get("attempted", 0)),
        "pass_cost": round(pass_cost, 6),
        "pass_row_status_counts": pass_status_counts,
        "rows": len(selected_rows),
        "rows_attempted": validation.get("attempted", 0),
        "outline_node_count": len(outline_nodes),
        "line_anchor_count": sum(1 for node in outline_nodes if node.line_anchor),
        "row_status_counts": status_counts,
        "raw_row_status_counts": dict(sorted(raw_status_counts.items())),
        "rows_detail": row_details,
        "denominator": denominator,
        "validation": validation,
        "reference_inventory": {
            "total_graph_nodes": len(reference_inventory.get("graph_nodes", [])),
            "scoped_graph_nodes": len(
                _scoped_graph_nodes(reference_inventory, document.document_id)
            ),
        },
        "unresolved_external_node_count": len(unresolved_external_nodes),
        "unresolved_external_nodes": unresolved_external_nodes,
    }
    report_path = destination / f"m20_s26_{document_id}_derive_cells_report.yaml"
    report_path.write_text(
        yaml.safe_dump(report, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
        newline="\n",
    )
    return report


def _output_destination(root: Path, output_dir: str | Path | None) -> Path:
    """Return a writable output directory outside the source repository."""
    if output_dir is None:
        return Path(tempfile.mkdtemp(prefix="tax_graph_m20_s30_"))
    destination = Path(output_dir).resolve()
    try:
        destination.relative_to(root)
    except ValueError:
        destination.mkdir(parents=True, exist_ok=True)
        return destination
    raise ValueError(f"output directory must be outside repository root: {destination}")


def _top_three_counts(values: dict[str, int]) -> dict[str, int]:
    """Return the three most frequent validator findings in stable order."""
    return dict(sorted(values.items(), key=lambda item: (-item[1], item[0]))[:3])


def run_documents(
    *,
    root: str | Path,
    year: str,
    document_ids: list[str] | None = None,
    output_dir: str | Path | None = None,
    no_provider: bool = False,
    process: str = "all",
    prior_run_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Run the harness once per document, optionally reusing healthy rows.

    The default is ``all``.  ``broken`` requires a prior run directory and
    merges its successful rows into each newly written report.
    """
    mode = _normalize_process(process)
    if mode == "broken" and prior_run_dir is None:
        raise ValueError("broken process requires prior_run_dir")
    root_path = Path(root).resolve()
    if document_ids is None:
        document_ids = manifest_document_ids(root=root_path, year=year)
    destination = _output_destination(root_path, output_dir)
    reports: list[dict[str, Any]] = []
    for document_id in document_ids:
        try:
            frame_path, coverage_path = persist_instruction_frame(
                root=root_path,
                year=year,
                document_id=document_id,
                output_dir=destination,
            )
        except Exception as exc:  # noqa: BLE001 - one document must not hide another
            reports.append(
                {
                    "document_id": document_id,
                    "status": "reported",
                    "reason": f"{type(exc).__name__}: {exc}",
                    "rows_attempted": 0,
                    "derived": 0,
                    "repaired": 0,
                    "gapped": 0,
                    "errored": 0,
                }
            )
            continue

        if no_provider:
            denominator = _measure_denominator(
                root=root_path,
                year=year,
                document_id=document_id,
            )
            destination.mkdir(parents=True, exist_ok=True)
            denominator_path = destination / f"m20_s51_{document_id}_denominator.yaml"
            denominator_path.write_text(
                yaml.safe_dump(denominator, sort_keys=False, allow_unicode=False),
                encoding="utf-8",
                newline="\n",
            )
            reports.append(
                {
                    "document_id": document_id,
                    "status": "prepared",
                    "instruction_frame": str(frame_path),
                    "instruction_coverage": str(coverage_path),
                    "denominator_report": str(denominator_path),
                    "denominator": denominator,
                    "reason": "provider disabled",
                }
            )
            continue

        try:
            report = run_real_document(
                root=root_path,
                year=year,
                document_id=document_id,
                output_dir=destination,
                process=mode,
                prior_run_dir=prior_run_dir,
            )
        except Exception as exc:  # noqa: BLE001 - report provider failures per document
            reports.append(
                {
                    "document_id": document_id,
                    "status": "reported",
                    "reason": f"{type(exc).__name__}: {exc}",
                    "rows_attempted": 0,
                    "derived": 0,
                    "repaired": 0,
                    "gapped": 0,
                    "errored": 0,
                }
            )
            continue
        rows_attempted = report["rows_attempted"]
        denominator = report.get("denominator") or {}
        if denominator:
            status = str(denominator.get("status") or "complete")
        else:
            # Preserve the old shape for test doubles and older reports. Real
            # runs always carry the explicit denominator above.
            status = "empty" if rows_attempted == 0 else "complete"
        summary = {
            "document_id": document_id,
            "status": status,
            "rows_attempted": rows_attempted,
            **report["row_status_counts"],
            "outline_node_count": report["outline_node_count"],
            "line_anchor_count": report["line_anchor_count"],
            "reference_inventory": report.get("reference_inventory", {}),
            "unresolved_external_node_count": report.get("unresolved_external_node_count", 0),
            "unresolved_external_nodes": report.get("unresolved_external_nodes", []),
            "validator_failures_by_kind": _top_three_counts(
                report["validation"].get("validator_failures_by_kind", {})
            ),
        }
        if denominator:
            summary["denominator"] = denominator
        if denominator and denominator.get("reason"):
            summary["reason"] = denominator["reason"]
        elif rows_attempted == 0:
            summary["reason"] = (
                denominator.get("reason")
                if denominator
                else "document outline produced no derivation rows"
            )
        reports.append(summary)
    return reports


def _measure_denominator(
    *,
    root: str | Path,
    year: str,
    document_id: str,
) -> dict[str, Any]:
    """Measure one manifest document without constructing a provider client."""
    root_path = Path(root).resolve()
    document = load_document_input(document_id, year=year, root=root_path)
    outline = build_outline_tree(document)
    return build_derivation_denominator(document, outline=outline)


def manifest_document_ids(*, root: str | Path, year: str) -> list[str]:
    """Return fetch-backed document ids in manifest order for a form-row corpus run.

    Region documents have their own title-based harvest path and do not contribute
    printed form rows to this denominator.
    """
    manifest = load_manifest(root=Path(root).resolve())
    if str(manifest.tax_year) != str(year):
        raise ValueError(
            f"manifest tax_year {manifest.tax_year} does not match requested year {year}"
        )
    return [entry.document_id for entry in manifest.documents if not entry.is_region]


def main() -> int:
    """Run persistence and, unless disabled, the real provider bench."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--year", default="2025")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--document", action="append", dest="documents")
    parser.add_argument("--no-provider", action="store_true")
    parser.add_argument(
        "--process",
        choices=sorted(PROCESS_MODES),
        default="all",
        help="derive every row or only rows not successful in the prior run",
    )
    parser.add_argument(
        "--prior-run-dir",
        "--prior-run",
        dest="prior_run_dir",
        default=None,
        help="prior run directory used by --process broken",
    )
    args = parser.parse_args()
    if args.process == "broken" and args.prior_run_dir is None:
        parser.error("--prior-run-dir is required with --process broken")
    reports = run_documents(
        root=args.root,
        year=args.year,
        document_ids=args.documents,
        output_dir=args.output_dir,
        no_provider=args.no_provider,
        process=args.process,
        prior_run_dir=args.prior_run_dir,
    )
    print(yaml.safe_dump({"documents": reports}, sort_keys=False, allow_unicode=False).rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
