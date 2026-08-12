"""Reconcile the maintained document tiers with the acquisition manifest.

The manifest is the source-backed inventory and ``document_tiers.yaml`` is the
machine-readable projection of the requirements document's tier tables.  They
are checked in both directions so adding a document to either side cannot
silently change the corpus denominator.  Worksheet regions are deliberately
excluded: they inherit maintenance ownership from their parent booklet and
are not independent tier entries.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from tax_graph.acquire.manifest import AcquisitionManifest, load_manifest
from tax_graph.config import project_root
from tax_graph.io.loader import load_yaml


DEFAULT_TIER_PATH = "config/document_tiers.yaml"


@dataclass(frozen=True)
class TierManifestReport:
    """Directional differences between the tier list and one manifest."""

    tax_year: str
    tiers: Mapping[str, tuple[str, ...]]
    tier_document_ids: tuple[str, ...]
    manifest_document_ids: tuple[str, ...]
    tier_not_in_manifest: tuple[str, ...]
    manifest_not_in_tier: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """Return whether both inventories name exactly the same documents."""
        return not self.tier_not_in_manifest and not self.manifest_not_in_tier

    def as_dict(self) -> dict[str, Any]:
        """Return a stable serialized report without hiding document ids."""
        return {
            "tax_year": self.tax_year,
            "tiers": {name: list(ids) for name, ids in self.tiers.items()},
            "tier_document_ids": list(self.tier_document_ids),
            "manifest_document_ids": list(self.manifest_document_ids),
            "tier_not_in_manifest": list(self.tier_not_in_manifest),
            "manifest_not_in_tier": list(self.manifest_not_in_tier),
            "ok": self.ok,
        }

    def format_report(self) -> str:
        """Render the directional guard in plain language."""
        lines = [
            "=== tier and manifest reconcile ===",
            f"  tax year: {self.tax_year}",
            f"  tier documents: {len(self.tier_document_ids)}",
            f"  manifest documents: {len(self.manifest_document_ids)}",
            "  tier not in manifest: " + ", ".join(self.tier_not_in_manifest or ("-",)),
            "  manifest not in tier: " + ", ".join(self.manifest_not_in_tier or ("-",)),
        ]
        return "\n".join(lines) + "\n"


def load_document_tiers(
    *,
    root: str | Path | None = None,
    path: str | Path | None = None,
    year: str | int = "2025",
) -> dict[str, tuple[str, ...]]:
    """Load and validate the machine-readable tier inventory."""
    root_path = Path(root).resolve() if root is not None else project_root()
    tier_path = Path(path) if path is not None else root_path / DEFAULT_TIER_PATH
    if not tier_path.is_absolute():
        tier_path = root_path / tier_path
    payload = load_yaml(tier_path) or {}
    if not isinstance(payload, Mapping):
        raise ValueError(f"document tier inventory must be a mapping: {tier_path}")
    if str(payload.get("tax_year")) != str(year):
        raise ValueError(
            f"document tier tax_year {payload.get('tax_year')} does not match requested year {year}"
        )
    raw_tiers = payload.get("tiers")
    if not isinstance(raw_tiers, Mapping) or not raw_tiers:
        raise ValueError(f"document tier inventory has no tiers: {tier_path}")
    result: dict[str, tuple[str, ...]] = {}
    seen: dict[str, str] = {}
    for raw_name, raw_ids in raw_tiers.items():
        name = str(raw_name).strip()
        if not name:
            raise ValueError(f"document tier inventory has an empty tier name: {tier_path}")
        if not isinstance(raw_ids, list) or not raw_ids:
            raise ValueError(f"document tier {name} must contain at least one document")
        ids = tuple(str(item).strip() for item in raw_ids)
        if any(not item for item in ids):
            raise ValueError(f"document tier {name} contains an empty document id")
        for document_id in ids:
            previous = seen.get(document_id)
            if previous is not None:
                raise ValueError(
                    f"document {document_id} appears in tiers {previous} and {name}"
                )
            seen[document_id] = name
        result[name] = ids
    return result


def load_core_document_ids(
    *,
    root: str | Path | None = None,
    path: str | Path | None = None,
    year: str | int = "2025",
) -> tuple[str, ...]:
    """Load the explicit core set used by refusal accounting.

    Core membership is intentionally separate from ownership.  The former is
    the reporting gate for this tax year; the latter is the forward maintenance
    commitment stored on each acquired manifest entry.
    """
    root_path = Path(root).resolve() if root is not None else project_root()
    tier_path = Path(path) if path is not None else root_path / DEFAULT_TIER_PATH
    if not tier_path.is_absolute():
        tier_path = root_path / tier_path
    payload = load_yaml(tier_path) or {}
    if str(payload.get("tax_year")) != str(year):
        raise ValueError(
            f"document tier tax_year {payload.get('tax_year')} does not match requested year {year}"
        )
    raw_ids = payload.get("core_documents")
    if not isinstance(raw_ids, list) or not raw_ids:
        raise ValueError(f"document tier inventory has no core_documents: {tier_path}")
    ids = tuple(str(item).strip() for item in raw_ids)
    if any(not item for item in ids) or len(set(ids)) != len(ids):
        raise ValueError(f"document tier inventory core_documents must be unique and non-empty")
    tier_ids = {
        item
        for values in load_document_tiers(root=root_path, path=tier_path, year=year).values()
        for item in values
    }
    missing = sorted(set(ids) - tier_ids)
    if missing:
        raise ValueError(
            "core documents must also be named by a tier: " + ", ".join(missing)
        )
    return ids


def reconcile_tier_manifest(
    manifest: AcquisitionManifest | None = None,
    *,
    root: str | Path | None = None,
    year: str | int = "2025",
    tier_path: str | Path | None = None,
) -> TierManifestReport:
    """Compare every non-region manifest document against the tier inventory."""
    root_path = Path(root).resolve() if root is not None else project_root()
    active_manifest = manifest or load_manifest(root=root_path)
    if str(active_manifest.tax_year) != str(year):
        raise ValueError(
            f"manifest tax_year {active_manifest.tax_year} does not match requested year {year}"
        )
    tiers = load_document_tiers(root=root_path, path=tier_path, year=year)
    tier_ids = tuple(document_id for ids in tiers.values() for document_id in ids)
    manifest_ids = tuple(
        entry.document_id for entry in active_manifest.documents if not entry.is_region
    )
    tier_set = set(tier_ids)
    manifest_set = set(manifest_ids)
    return TierManifestReport(
        tax_year=str(year),
        tiers=tiers,
        tier_document_ids=tier_ids,
        manifest_document_ids=manifest_ids,
        tier_not_in_manifest=tuple(sorted(tier_set - manifest_set)),
        manifest_not_in_tier=tuple(sorted(manifest_set - tier_set)),
    )
