"""Reconcile the declared, modelled, and acquired document inventories.

The acquisition manifest is the pipeline's declared corpus. The graph is a
downstream projection and the raw text store is local build state, so each
inventory is reported separately instead of allowing the graph to define the
corpus denominator. Missing raw state is a named, non-fatal condition because
the raw store is gitignored and is not available in every checkout.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tax_graph.acquire.manifest import load_manifest
from tax_graph.config import get_config_value, load_config, project_root
from tax_graph.io.loader import load_graph


@dataclass(frozen=True)
class ReconcileDifference:
    """One named directional difference between two document inventories."""

    name: str
    document_ids: tuple[str, ...]
    status: str = "reported"
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON/YAML-friendly representation."""
        return {
            "name": self.name,
            "document_ids": list(self.document_ids),
            "status": self.status,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class DocumentReconcileReport:
    """Named reconciliation results for one tax year."""

    tax_year: str
    graph_documents: tuple[str, ...]
    manifest_documents: tuple[str, ...]
    raw_documents: tuple[str, ...] | None
    raw_status: str
    raw_store: str
    raw_reason: str | None
    differences: tuple[ReconcileDifference, ...]

    def difference(self, name: str) -> ReconcileDifference:
        """Return one named difference, raising for an unknown name."""
        for difference in self.differences:
            if difference.name == name:
                return difference
        raise KeyError(name)

    def as_dict(self) -> dict[str, Any]:
        """Return the complete report without collapsing ids into counts."""
        return {
            "tax_year": self.tax_year,
            "graph_documents": list(self.graph_documents),
            "manifest_documents": list(self.manifest_documents),
            "raw_documents": None if self.raw_documents is None else list(self.raw_documents),
            "raw_status": self.raw_status,
            "raw_store": self.raw_store,
            "raw_reason": self.raw_reason,
            "differences": [difference.as_dict() for difference in self.differences],
        }

    def format_report(self) -> str:
        """Render a stable CLI report with every difference named."""
        lines = [
            "=== document reconcile ===",
            f"  tax year: {self.tax_year}",
            f"  graph documents: {len(self.graph_documents)}",
            f"  manifest documents: {len(self.manifest_documents)}",
            f"  raw text: {self.raw_status} ({self.raw_store})",
        ]
        if self.raw_reason:
            lines.append(f"  raw reason: {self.raw_reason}")
        for difference in self.differences:
            if difference.status == "skipped":
                detail = f"SKIPPED ({difference.reason or 'no reason recorded'})"
            else:
                detail = ", ".join(difference.document_ids) if difference.document_ids else "-"
            lines.append(f"  {difference.name}: {detail}")
        return "\n".join(lines) + "\n"


def reconcile_document_lists(
    year: str | int = "2025",
    *,
    root: str | Path | None = None,
    raw_store: str | Path | None = None,
) -> DocumentReconcileReport:
    """Compare graph, manifest, and acquired text ids without writing state.

    The graph and manifest comparisons always run. The raw comparison is
    ``skipped`` when the year-specific raw text directory is absent, which is
    expected in CI and in a fresh clone. Only direct ``*.txt`` files count as
    acquired text artifacts; PDFs, HTML, and state files do not enter the raw
    inventory.
    """
    root_path = Path(root).resolve() if root is not None else project_root()
    year_text = str(year)
    graph = load_graph(year_text, root=root_path)
    manifest = load_manifest(root=root_path)
    if str(manifest.tax_year) != year_text:
        raise ValueError(
            f"manifest tax_year {manifest.tax_year} does not match requested year {year_text}"
        )

    graph_documents = tuple(sorted(
        str(document["document_id"])
        for document in graph.items("documents")
        if document.get("document_id")
    ))
    manifest_documents = tuple(entry.document_id for entry in manifest.documents)
    raw_root = _raw_year_directory(root_path, year_text, raw_store)
    if raw_root.is_dir():
        raw_documents: tuple[str, ...] | None = tuple(sorted(path.stem for path in raw_root.glob("*.txt")))
        raw_status = "available"
        raw_reason = None
    else:
        raw_documents = None
        raw_status = "skipped"
        raw_reason = "raw text directory is absent"

    graph_set = set(graph_documents)
    manifest_set = set(manifest_documents)
    differences = [
        ReconcileDifference(
            name="graph_not_in_manifest",
            document_ids=tuple(sorted(graph_set - manifest_set)),
        ),
        ReconcileDifference(
            name="manifest_not_in_graph",
            document_ids=tuple(sorted(manifest_set - graph_set)),
        ),
    ]
    if raw_documents is None:
        skipped_reason = raw_reason or "raw text inventory is unavailable"
        differences.extend([
            ReconcileDifference(
                name="raw_not_in_manifest",
                document_ids=(),
                status="skipped",
                reason=skipped_reason,
            ),
            ReconcileDifference(
                name="manifest_not_in_raw",
                document_ids=(),
                status="skipped",
                reason=skipped_reason,
            ),
        ])
    else:
        raw_set = set(raw_documents)
        differences.extend([
            ReconcileDifference(
                name="raw_not_in_manifest",
                document_ids=tuple(sorted(raw_set - manifest_set)),
            ),
            ReconcileDifference(
                name="manifest_not_in_raw",
                document_ids=tuple(sorted(manifest_set - raw_set)),
            ),
        ])
    return DocumentReconcileReport(
        tax_year=year_text,
        graph_documents=graph_documents,
        manifest_documents=manifest_documents,
        raw_documents=raw_documents,
        raw_status=raw_status,
        raw_store=raw_root.as_posix(),
        raw_reason=raw_reason,
        differences=tuple(differences),
    )


def _raw_year_directory(root: Path, year: str, raw_store: str | Path | None) -> Path:
    """Resolve the year-specific raw text directory without creating it."""
    if raw_store is None:
        config = load_config(root=root)
        raw_store = get_config_value(config, "project.paths.raw_store", ".cache/raw")
    candidate = Path(raw_store)
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate / year
