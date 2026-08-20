"""Account for refusal candidates and their human-visible artifacts.

This module is provider-free and read-only.  It turns the five refusal
candidate shapes named by M20-S152 into records that can be checked by the
doctor without treating a log message or a missing record as evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from pilot.run_report import REPORT_PREFIX, REPORT_SUFFIX
from tax_graph.acquire.corpus import load_core_document_ids
from tax_graph.acquire.manifest import load_manifest
from tax_graph.config import get_config_value, load_config, project_root
from tax_graph.io.loader import load_yaml


@dataclass(frozen=True)
class CandidateRule:
    """Written definition of one refusal candidate and its surface."""

    kind: str
    refusal: str
    surface: str


CANDIDATE_RULES = (
    CandidateRule(
        "derive_cell_status",
        "A derivation row has status errored, error, gapped, or skipped.",
        "The row is present in its *_derive_cells_report.yaml with a non-empty reason field.",
    ),
    CandidateRule(
        "formula_review_gap",
        "A formula cell is recorded in review_gaps.yaml with status review_gap.",
        "The document draft's review_gaps.yaml contains the cell and its review_gap text.",
    ),
    CandidateRule(
        "not_derivable_outcome",
        "An extracted outcome has kind not_derivable.",
        "The document draft's micro_extraction.yaml contains the outcome and its reason.",
    ),
    CandidateRule(
        "worksheet_refusal",
        "Worksheet discovery records a worksheet whose status is not ready, or a non-advisory finding.",
        "The worksheet-discovery*.yaml artifact contains the status or finding reason.",
    ),
    CandidateRule(
        "frontier_refusal",
        "The frontier registry contains an entry with status unmodeled or declared.",
        "graph/<year>/frontier.yaml contains the entry and its status.",
    ),
)

RULES_BY_KIND = {rule.kind: rule for rule in CANDIDATE_RULES}
_ADVISORY_WORKSHEET_FINDINGS = frozenset({
    "html_markdown_extent_disagreement",
    "unresolved_footnote_marker",
    "worksheet_window_reached_edge",
    "window_claim_overlap",
})


@dataclass(frozen=True)
class RefusalCandidate:
    """One refusal candidate, including the artifact that surfaces it."""

    kind: str
    document_id: str
    owner_document_id: str
    line: str
    status: str
    reason: str
    artifact: str
    surfaced: bool
    is_core: bool

    def as_dict(self) -> dict[str, Any]:
        """Return a stable machine-readable candidate record."""
        return {
            "kind": self.kind,
            "document_id": self.document_id,
            "owner_document_id": self.owner_document_id,
            "line": self.line,
            "status": self.status,
            "reason": self.reason,
            "artifact": self.artifact,
            "surfaced": self.surfaced,
            "is_core": self.is_core,
        }


@dataclass(frozen=True)
class CoreRefusalReport:
    """Complete core-only refusal gate result."""

    tax_year: str
    candidates: tuple[RefusalCandidate, ...]
    configuration_error: str | None = None

    @property
    def core_candidates(self) -> tuple[RefusalCandidate, ...]:
        """Return all refusal candidates owned by a core document."""
        return tuple(item for item in self.candidates if item.is_core)

    @property
    def core_unsurfaced(self) -> tuple[RefusalCandidate, ...]:
        """Return core refusals a human cannot find in the named artifact."""
        return tuple(item for item in self.core_candidates if not item.surfaced)

    @property
    def non_core_unsurfaced(self) -> tuple[RefusalCandidate, ...]:
        """Return visible accounting for non-core refusals without blocking."""
        return tuple(item for item in self.candidates if not item.is_core and not item.surfaced)

    @property
    def ok(self) -> bool:
        """Return whether the core refusal gate is satisfied."""
        return self.configuration_error is None and not self.core_unsurfaced

    def as_dict(self) -> dict[str, Any]:
        """Return the gate result without collapsing individual refusals."""
        return {
            "tax_year": self.tax_year,
            "ok": self.ok,
            "configuration_error": self.configuration_error,
            "counts": {
                "candidates": len(self.candidates),
                "core_candidates": len(self.core_candidates),
                "core_unsurfaced": len(self.core_unsurfaced),
                "non_core_unsurfaced": len(self.non_core_unsurfaced),
            },
            "candidates": [item.as_dict() for item in self.candidates],
        }

    def format_report(self) -> str:
        """Render the gate in a form suitable for a doctor report."""
        lines = [
            "=== core refusal gate ===",
            f"  tax year: {self.tax_year}",
            f"  candidates: {len(self.candidates)}",
            f"  core candidates: {len(self.core_candidates)}",
            f"  core unsurfaced: {len(self.core_unsurfaced)}",
            f"  non-core unsurfaced: {len(self.non_core_unsurfaced)}",
        ]
        if self.configuration_error:
            lines.append(f"  configuration error: {self.configuration_error}")
        for item in self.candidates:
            scope = "core" if item.is_core else "non-core"
            state = "surfaced" if item.surfaced else "UNSURFACED"
            lines.append(
                f"  {item.kind}: {item.document_id} line {item.line or '-'}; "
                f"{scope}; {state}; artifact={item.artifact or '-'}; "
                f"{item.reason or '(no reason recorded)'}"
            )
        lines.append("  result: " + ("OK" if self.ok else "FAILED: core refusal is unsurfaced"))
        return "\n".join(lines) + "\n"


def evaluate_core_refusals(
    *,
    root: str | Path | None = None,
    year: str | int = "2025",
) -> CoreRefusalReport:
    """Evaluate all configured local refusal artifacts without provider calls."""
    root_path = Path(root).resolve() if root is not None else project_root()
    year_text = str(year)
    try:
        manifest = load_manifest(root=root_path)
        core_ids = set(load_core_document_ids(root=root_path, year=year_text))
    except Exception as exc:
        return CoreRefusalReport(
            tax_year=year_text,
            candidates=(),
            configuration_error=f"core inventory could not be loaded: {type(exc).__name__}: {exc}",
        )

    candidates: list[RefusalCandidate] = []
    output_dir = _configured_path(
        root_path,
        get_config_value(load_config(root=root_path), "project.paths.output_dir", "output"),
    )
    candidates.extend(_derive_candidates(output_dir, manifest, core_ids))

    draft_root = root_path / "graph" / year_text / "_drafts"
    candidates.extend(_review_gap_candidates(draft_root, manifest, core_ids))
    candidates.extend(_not_derivable_candidates(draft_root, manifest, core_ids))
    candidates.extend(_worksheet_candidates(draft_root, manifest, core_ids))
    candidates.extend(_frontier_candidates(root_path / "graph" / year_text / "frontier.yaml", manifest, core_ids))
    candidates.sort(key=lambda item: (item.kind, item.document_id, item.line, item.artifact, item.reason))
    return CoreRefusalReport(tax_year=year_text, candidates=tuple(candidates))


def _configured_path(root: Path, value: Any) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else root / path


def _ascii(value: Any) -> str:
    """Bound human-facing artifact text to ASCII."""
    return str(value or "").encode("ascii", errors="replace").decode("ascii").strip()


def _owner(manifest: Any, document_id: str, source_document_id: str | None = None) -> str:
    candidate = document_id or _ascii(source_document_id)
    if not candidate:
        return ""
    try:
        return manifest.owner_document_id(candidate)
    except KeyError:
        return candidate


def _candidate(
    kind: str,
    manifest: Any,
    core_ids: set[str],
    *,
    document_id: str,
    line: Any,
    status: Any,
    reason: Any,
    artifact: Path,
    owner_document_id: str | None = None,
) -> RefusalCandidate:
    owner = owner_document_id or _owner(manifest, document_id)
    reason_text = _ascii(reason)
    artifact_text = str(artifact)
    return RefusalCandidate(
        kind=kind,
        document_id=_ascii(document_id) or owner,
        owner_document_id=owner,
        line=_ascii(line),
        status=_ascii(status) or "refused",
        reason=reason_text,
        artifact=artifact_text,
        surfaced=bool(reason_text and artifact.is_file()),
        is_core=owner in core_ids,
    )


def _load_mapping(path: Path) -> Mapping[str, Any] | None:
    if not path.is_file():
        return None
    payload = load_yaml(path)
    return payload if isinstance(payload, Mapping) else None


def _derive_candidates(run_dir: Path, manifest: Any, core_ids: set[str]) -> list[RefusalCandidate]:
    records: list[RefusalCandidate] = []
    if not run_dir.is_dir():
        return records
    for artifact in sorted(run_dir.glob(f"{REPORT_PREFIX}*{REPORT_SUFFIX}")):
        payload = _load_mapping(artifact) or {}
        document_id = _ascii(payload.get("document_id"))
        for row in payload.get("rows_detail") or []:
            if not isinstance(row, Mapping):
                continue
            status = _ascii(row.get("status")).lower()
            if status not in {"errored", "error", "gapped", "skipped"}:
                continue
            records.append(_candidate(
                "derive_cell_status", manifest, core_ids,
                document_id=document_id,
                line=row.get("line"),
                status=status,
                reason=row.get("error") or row.get("review_gap") or row.get("structural_skip_reason"),
                artifact=artifact,
            ))
    return records


def _draft_documents(draft_root: Path) -> Iterable[Path]:
    if not draft_root.is_dir():
        return ()
    return (path for path in sorted(draft_root.iterdir()) if path.is_dir())


def _review_gap_candidates(draft_root: Path, manifest: Any, core_ids: set[str]) -> list[RefusalCandidate]:
    records: list[RefusalCandidate] = []
    for document_dir in _draft_documents(draft_root):
        artifact = document_dir / "review_gaps.yaml"
        payload = load_yaml(artifact) if artifact.is_file() else []
        if not isinstance(payload, list):
            continue
        document_id = document_dir.name
        for row in payload:
            if not isinstance(row, Mapping) or _ascii(row.get("status")).lower() != "review_gap":
                continue
            records.append(_candidate(
                "formula_review_gap", manifest, core_ids,
                document_id=document_id,
                line=row.get("line_anchor"),
                status=row.get("status"),
                reason=row.get("review_gap"),
                artifact=artifact,
            ))
    return records


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_mappings(child)


def _not_derivable_candidates(draft_root: Path, manifest: Any, core_ids: set[str]) -> list[RefusalCandidate]:
    records: list[RefusalCandidate] = []
    for document_dir in _draft_documents(draft_root):
        artifact = document_dir / "micro_extraction.yaml"
        payload = _load_mapping(artifact)
        if payload is None:
            continue
        for outcome in _walk_mappings(payload):
            if _ascii(outcome.get("kind")).lower() != "not_derivable":
                continue
            records.append(_candidate(
                "not_derivable_outcome", manifest, core_ids,
                document_id=document_dir.name,
                line=outcome.get("line_anchor") or outcome.get("line"),
                status=outcome.get("status") or "outcome",
                reason=outcome.get("reason"),
                artifact=artifact,
            ))
    return records


def _worksheet_candidates(draft_root: Path, manifest: Any, core_ids: set[str]) -> list[RefusalCandidate]:
    records: list[RefusalCandidate] = []
    seen: set[bytes] = set()
    for artifact in sorted(draft_root.glob("worksheet-discovery*.yaml")):
        content = artifact.read_bytes()
        if content in seen:
            continue
        seen.add(content)
        payload = _load_mapping(artifact) or {}
        source_document_id = _ascii(payload.get("source_document_id"))
        for item in payload.get("worksheets") or []:
            if not isinstance(item, Mapping) or _ascii(item.get("status") or "ready").lower() == "ready":
                continue
            findings = item.get("findings") or []
            reason = "; ".join(_ascii(value.get("message") or value.get("reason")) for value in findings if isinstance(value, Mapping))
            records.append(_candidate(
                "worksheet_refusal", manifest, core_ids,
                document_id=_ascii(item.get("document_id")),
                line="",
                status=item.get("status"),
                reason=reason,
                artifact=artifact,
                owner_document_id=_owner(manifest, _ascii(item.get("document_id")), source_document_id),
            ))
        for finding in payload.get("findings") or []:
            if not isinstance(finding, Mapping) or _ascii(finding.get("kind")) in _ADVISORY_WORKSHEET_FINDINGS:
                continue
            records.append(_candidate(
                "worksheet_refusal", manifest, core_ids,
                document_id="",
                line="",
                status="refused",
                reason=finding.get("message") or finding.get("reason"),
                artifact=artifact,
                owner_document_id=_owner(manifest, "", source_document_id),
            ))
    return records


def _frontier_candidates(artifact: Path, manifest: Any, core_ids: set[str]) -> list[RefusalCandidate]:
    payload = _load_mapping(artifact) or {}
    records: list[RefusalCandidate] = []
    for item in payload.get("frontiers") or []:
        if not isinstance(item, Mapping) or _ascii(item.get("status")).lower() not in {"unmodeled", "declared"}:
            continue
        source = item.get("source") if isinstance(item.get("source"), Mapping) else {}
        document_id = _ascii(source.get("document_id"))
        target = item.get("target") if isinstance(item.get("target"), Mapping) else {}
        line = target.get("line") or source.get("line")
        status = _ascii(item.get("status"))
        records.append(_candidate(
            "frontier_refusal", manifest, core_ids,
            document_id=document_id,
            line=line,
            status=status,
            reason=f"frontier status: {status}",
            artifact=artifact,
        ))
    return records


__all__ = ["CANDIDATE_RULES", "RULES_BY_KIND", "CandidateRule", "CoreRefusalReport", "RefusalCandidate", "evaluate_core_refusals"]
