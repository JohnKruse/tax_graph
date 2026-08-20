"""Acquisition manifest loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import jsonschema

from tax_graph.config import get_config_value, load_config, project_root
from tax_graph.io.loader import load_yaml


IRS_PDF_URL_RE = re.compile(r"^https://www\.irs\.gov/pub/irs-(?:pdf|prior)/[fip][a-z0-9-]+\.pdf$")


@dataclass(frozen=True)
class ManifestEntry:
    """One source document to acquire, optionally marked as part of core."""

    document_id: str
    kind: str
    url: str | None = None
    instructions_document_id: str | None = None
    instruction_url: str | None = None
    expected_sha256: str | None = None
    ownership: str | None = None
    core: bool = False
    region_of: str | None = None
    region_title: str | None = None
    region_parent_sha256: str | None = None

    @property
    def is_region(self) -> bool:
        """Return whether this entry names a region of another acquired document."""
        return self.region_of is not None


@dataclass(frozen=True)
class AcquisitionManifest:
    """Authoritative document acquisition manifest for a tax year."""

    tax_year: int
    documents: tuple[ManifestEntry, ...]

    def by_document_id(self) -> dict[str, ManifestEntry]:
        """Index entries by document id."""
        return {entry.document_id: entry for entry in self.documents}

    def owner_document_id(self, document_id: str) -> str:
        """Return the acquired document that owns a document's maintenance commitment."""
        entries = self.by_document_id()
        entry = entries.get(document_id)
        if entry is None:
            raise KeyError(document_id)
        if entry.is_region:
            if entry.region_of is None:  # pragma: no cover - schema prevents this.
                raise ValueError(f"region {document_id} has no parent document")
            return self.owner_document_id(entry.region_of)
        return entry.document_id

    def ownership_for(self, document_id: str) -> str:
        """Return effective ownership, inheriting it through a region parent."""
        owner_id = self.owner_document_id(document_id)
        ownership = self.by_document_id()[owner_id].ownership
        if ownership is None:  # pragma: no cover - schema prevents this for live data.
            raise ValueError(f"manifest document {owner_id} has no ownership")
        return ownership


def default_manifest_path(root: str | Path | None = None) -> Path:
    """Return the configured manifest path or the default project manifest."""
    root_path = Path(root).resolve() if root is not None else project_root()
    config = load_config(root=root_path)
    configured = get_config_value(config, "project.paths.manifest", "config/manifest.yaml")
    return root_path / configured


def load_manifest(path: str | Path | None = None, root: str | Path | None = None) -> AcquisitionManifest:
    """Load and validate an acquisition manifest."""
    root_path = Path(root).resolve() if root is not None else project_root()
    manifest_path = Path(path) if path is not None else default_manifest_path(root_path)
    if not manifest_path.is_absolute():
        manifest_path = root_path / manifest_path

    data = load_yaml(manifest_path)
    validate_manifest_data(data, root=root_path)
    return AcquisitionManifest(
        tax_year=data["tax_year"],
        documents=tuple(
            ManifestEntry(
                document_id=entry["document_id"],
                kind=entry["kind"],
                ownership=entry.get("ownership"),
                url=entry.get("url"),
                instructions_document_id=entry.get("instructions_document_id"),
                instruction_url=entry.get("instruction_url"),
                expected_sha256=entry.get("expected_sha256"),
                region_of=(entry.get("region") or {}).get("source_document_id"),
                region_title=(entry.get("region") or {}).get("title"),
                region_parent_sha256=(entry.get("region") or {}).get("parent_sha256"),
                core=bool(entry.get("core", False)),
            )
            for entry in data["documents"]
        ),
    )


def validate_manifest_data(data: dict[str, Any], root: str | Path | None = None) -> None:
    """Validate raw manifest data against schema and manifest invariants."""
    root_path = Path(root).resolve() if root is not None else project_root()
    schema = load_yaml(root_path / "schemas" / "manifest.schema.json")
    jsonschema.validate(data, schema)
    _validate_unique_document_ids(data)
    _validate_irs_pdf_urls(data)
    _validate_instruction_relationships(data)


def _validate_unique_document_ids(data: dict[str, Any]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for entry in data["documents"]:
        document_id = entry["document_id"]
        if document_id in seen:
            duplicates.add(document_id)
        seen.add(document_id)
    if duplicates:
        joined = ", ".join(sorted(duplicates))
        raise ValueError(f"duplicate manifest document_id: {joined}")


def _validate_irs_pdf_urls(data: dict[str, Any]) -> None:
    bad_urls = [
        entry.get("url")
        for entry in data["documents"]
        if entry.get("url") is not None and not IRS_PDF_URL_RE.match(entry["url"])
    ]
    if bad_urls:
        joined = ", ".join(sorted(bad_urls))
        raise ValueError(f"manifest URLs must use stable IRS PDF paths: {joined}")
    _validate_region_entries(data)


def _validate_region_entries(data: dict[str, Any]) -> None:
    """Validate region parents and keep region identity source-backed."""
    entries = {entry["document_id"]: entry for entry in data["documents"]}
    for entry in data["documents"]:
        region = entry.get("region")
        if not region:
            continue
        if entry.get("expected_sha256"):
            raise ValueError(
                f"manifest region {entry['document_id']} cannot carry its own expected_sha256"
            )
        parent_id = region["source_document_id"]
        if parent_id == entry["document_id"]:
            raise ValueError(f"manifest region {entry['document_id']} cannot name itself as parent")
        parent = entries.get(parent_id)
        if parent is None:
            raise ValueError(
                f"manifest region {entry['document_id']} references missing parent {parent_id}"
            )
        if parent.get("region"):
            raise ValueError(
                f"manifest region {entry['document_id']} parent {parent_id} cannot itself be a region"
            )
        if not parent.get("url"):
            raise ValueError(
                f"manifest region {entry['document_id']} parent {parent_id} has no acquired URL"
            )


def _validate_instruction_relationships(data: dict[str, Any]) -> None:
    entries = {entry["document_id"]: entry for entry in data["documents"]}
    for entry in data["documents"]:
        instructions_document_id = entry.get("instructions_document_id")
        if not instructions_document_id:
            continue
        target = entries.get(instructions_document_id)
        if target is None:
            raise ValueError(
                f"manifest document {entry['document_id']} references missing instructions "
                f"{instructions_document_id}"
            )
        if target.get("kind") not in {"instructions", "publication"}:
            raise ValueError(
                f"manifest document {entry['document_id']} instructions_document_id "
                f"{instructions_document_id} is kind {target.get('kind')}"
            )
