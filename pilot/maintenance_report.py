"""Partition derivation refusals by maintenance ownership.

This is a read-only projection of a derivation run.  It does not promote a
draft, change a verdict, or claim human review.  A refusal is reported when
the run leaves a reason in its row or discovery finding.  Core documents are
allowed to have reported refusals while the pipeline is under construction;
only a core refusal with no reason is a failing condition.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from pilot.run_report import REPORT_PREFIX, REPORT_SUFFIX, SUCCESS_STATUSES, discover_documents
from tax_graph.acquire.corpus import load_core_document_ids
from tax_graph.acquire.manifest import AcquisitionManifest, load_manifest


@dataclass(frozen=True)
class RefusalRecord:
    """One pipeline item that did not produce a shippable answer."""

    document_id: str
    owner_document_id: str
    ownership: str
    is_core: bool
    line: str
    status: str
    reason: str
    reported: bool
    source: str

    def as_dict(self) -> dict[str, Any]:
        """Return the record in stable review-queue shape."""
        return {
            "document_id": self.document_id,
            "owner_document_id": self.owner_document_id,
            "ownership": self.ownership,
            "is_core": self.is_core,
            "line": self.line,
            "status": self.status,
            "reason": self.reason,
            "reported": self.reported,
            "source": self.source,
        }


@dataclass(frozen=True)
class MaintenanceRefusalReport:
    """Complete refusal accounting for a derivation run."""

    tax_year: str
    records: tuple[RefusalRecord, ...]

    @property
    def reported(self) -> tuple[RefusalRecord, ...]:
        """Return refusals that carry an explicit reason."""
        return tuple(item for item in self.records if item.reported)

    @property
    def unreported(self) -> tuple[RefusalRecord, ...]:
        """Return refusals whose pipeline artifact contains no reason."""
        return tuple(item for item in self.records if not item.reported)

    @property
    def core_unreported(self) -> tuple[RefusalRecord, ...]:
        """Return the only class that fails the M20-S101 reporting gate."""
        return tuple(item for item in self.unreported if item.is_core)

    @property
    def ok(self) -> bool:
        """Return whether every core refusal is explicitly reported."""
        return not self.core_unreported

    def as_dict(self) -> dict[str, Any]:
        """Return a machine-readable report without collapsing refusals to counts."""
        by_ownership: dict[str, list[dict[str, Any]]] = {}
        for item in self.records:
            by_ownership.setdefault(item.ownership, []).append(item.as_dict())
        return {
            "tax_year": self.tax_year,
            "ok": self.ok,
            "counts": {
                "refusals": len(self.records),
                "reported": len(self.reported),
                "unreported": len(self.unreported),
                "core_unreported": len(self.core_unreported),
            },
            "by_ownership": by_ownership,
            "records": [item.as_dict() for item in self.records],
        }

    def format_report(self) -> str:
        """Render ownership, core membership, and every refusal reason."""
        lines = [
            "=== maintenance refusal report ===",
            f"  tax year: {self.tax_year}",
            f"  refusals: {len(self.records)}",
            f"  reported: {len(self.reported)}",
            f"  unreported: {len(self.unreported)}",
            f"  core unreported: {len(self.core_unreported)}",
        ]
        for item in self.records:
            core = "core" if item.is_core else "non-core"
            state = "reported" if item.reported else "UNREPORTED"
            line = f" line {item.line}" if item.line else ""
            reason = item.reason or "(no reason recorded)"
            lines.append(
                f"  {item.document_id}{line}: {item.status}; {core}; "
                f"owner={item.owner_document_id}; ownership={item.ownership}; {state}; {reason}"
            )
        lines.append("  result: " + ("OK" if self.ok else "FAILED: core refusal is unreported"))
        return "\n".join(lines) + "\n"


def _load(path: Path, default: Any = None) -> Any:
    """Load one YAML artifact without treating an empty file as a record."""
    if not path.is_file():
        return default
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return default if value is None else value


def _reason(value: Any) -> str:
    """Render stored failure fields without inventing a cause."""
    if isinstance(value, Mapping):
        kind = str(value.get("kind") or "").strip()
        message = str(value.get("message") or value.get("error") or "").strip()
        return f"{kind}: {message}" if kind and message else kind or message
    return "" if value is None else str(value).strip()


def _reasons(row: Mapping[str, Any]) -> str:
    """Combine all row-level evidence that explains a refusal."""
    values: list[str] = []
    for key in ("error", "review_gap", "structural_skip_reason"):
        text = _reason(row.get(key))
        if text:
            values.append(text)
    for key in ("validation_failures", "validation_warnings", "findings"):
        items = row.get(key) or []
        if isinstance(items, list):
            values.extend(text for item in items if (text := _reason(item)))
    return "; ".join(dict.fromkeys(values))


def _ownership(
    manifest: AcquisitionManifest,
    document_id: str,
    *,
    source_document_id: str | None = None,
) -> tuple[str, str]:
    """Resolve owner and maintenance marking, including region inheritance."""
    candidate = document_id or str(source_document_id or "")
    if not candidate:
        return "", "unknown"
    try:
        return manifest.owner_document_id(candidate), manifest.ownership_for(candidate)
    except KeyError:
        return candidate, "unknown"


def _record(
    manifest: AcquisitionManifest,
    core_ids: set[str],
    *,
    document_id: str,
    line: Any,
    status: Any,
    reason: str,
    source: str,
    source_document_id: str | None = None,
) -> RefusalRecord:
    owner_document_id, ownership = _ownership(
        manifest,
        document_id,
        source_document_id=source_document_id,
    )
    return RefusalRecord(
        document_id=document_id or owner_document_id,
        owner_document_id=owner_document_id,
        ownership=ownership,
        is_core=owner_document_id in core_ids,
        line="" if line is None else str(line),
        status=str(status or "refused"),
        reason=reason,
        reported=bool(reason),
        source=source,
    )


def _run_records(
    run_dir: Path,
    manifest: AcquisitionManifest,
    core_ids: set[str],
) -> list[RefusalRecord]:
    """Read every non-success row and every explicit skipped denominator anchor."""
    records: list[RefusalRecord] = []
    for document_id in discover_documents(run_dir):
        path = run_dir / f"{REPORT_PREFIX}{document_id}{REPORT_SUFFIX}"
        payload = _load(path, default={})
        if not isinstance(payload, Mapping):
            continue
        detail = payload.get("rows_detail") or []
        detail_lines: set[str] = set()
        for row in detail:
            if not isinstance(row, Mapping):
                continue
            line = "" if row.get("line") is None else str(row.get("line"))
            detail_lines.add(line.lower())
            status = str(row.get("status") or "error").strip().lower()
            if status in SUCCESS_STATUSES:
                continue
            records.append(_record(
                manifest,
                core_ids,
                document_id=document_id,
                line=row.get("line"),
                status=status,
                reason=_reasons(row),
                source=path.name,
            ))
        denominator = payload.get("denominator") or {}
        for anchor in denominator.get("anchors", []) if isinstance(denominator, Mapping) else []:
            if not isinstance(anchor, Mapping) or not anchor.get("skip_reason"):
                continue
            line = "" if anchor.get("anchor") is None else str(anchor.get("anchor"))
            if line.lower() in detail_lines:
                continue
            records.append(_record(
                manifest,
                core_ids,
                document_id=document_id,
                line=line,
                status="skipped",
                reason=_reason(anchor.get("skip_reason")),
                source=path.name,
            ))
    return records


def _worksheet_records(
    run_dir: Path,
    manifest: AcquisitionManifest,
    core_ids: set[str],
) -> list[RefusalRecord]:
    """Read worksheet refusals and discovery findings from a candidate run."""
    records: list[RefusalRecord] = []
    advisory = {
        "html_markdown_extent_disagreement",
        "unresolved_footnote_marker",
        "worksheet_window_reached_edge",
        "window_claim_overlap",
    }
    for path in sorted(run_dir.glob("worksheet-discovery*.yaml")):
        payload = _load(path, default={})
        if not isinstance(payload, Mapping):
            continue
        source_document_id = str(payload.get("source_document_id") or "")
        for item in payload.get("worksheets", []) or []:
            if not isinstance(item, Mapping) or str(item.get("status") or "ready") == "ready":
                continue
            findings = item.get("findings") or []
            reason = "; ".join(text for value in findings if (text := _reason(value)))
            records.append(_record(
                manifest,
                core_ids,
                document_id=str(item.get("document_id") or ""),
                line="",
                status=str(item.get("status") or "refused"),
                reason=reason,
                source=path.name,
                source_document_id=source_document_id,
            ))
        for finding in payload.get("findings", []) or []:
            if not isinstance(finding, Mapping) or str(finding.get("kind") or "") in advisory:
                continue
            records.append(_record(
                manifest,
                core_ids,
                document_id="",
                line="",
                status="refused",
                reason=_reason(finding),
                source=path.name,
                source_document_id=source_document_id,
            ))
    return records


def build_refusal_report(
    run_dir: str | Path,
    *,
    root: str | Path | None = None,
    year: str | int = "2025",
) -> MaintenanceRefusalReport:
    """Build ownership-aware refusal accounting from one run directory."""
    run_path = Path(run_dir).resolve()
    root_path = Path(root).resolve() if root is not None else Path.cwd().resolve()
    manifest = load_manifest(root=root_path)
    core_ids = set(load_core_document_ids(root=root_path, year=year))
    records = _run_records(run_path, manifest, core_ids)
    records.extend(_worksheet_records(run_path, manifest, core_ids))
    records.sort(key=lambda item: (item.document_id, item.line, item.source, item.reason))
    return MaintenanceRefusalReport(tax_year=str(year), records=tuple(records))


def main(argv: list[str] | None = None) -> int:
    """Print a refusal report and fail only on an unreported core refusal."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--year", default="2025")
    args = parser.parse_args(argv)
    report = build_refusal_report(args.run_dir, root=args.root, year=args.year)
    print(report.format_report(), end="")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
