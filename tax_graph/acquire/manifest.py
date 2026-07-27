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
    """One source document to acquire."""

    document_id: str
    kind: str
    url: str
    instructions_document_id: str | None = None
    instruction_url: str | None = None
    expected_sha256: str | None = None


@dataclass(frozen=True)
class AcquisitionManifest:
    """Authoritative document acquisition manifest for a tax year."""

    tax_year: int
    documents: tuple[ManifestEntry, ...]

    def by_document_id(self) -> dict[str, ManifestEntry]:
        """Index entries by document id."""
        return {entry.document_id: entry for entry in self.documents}


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
                url=entry["url"],
                instructions_document_id=entry.get("instructions_document_id"),
                instruction_url=entry.get("instruction_url"),
                expected_sha256=entry.get("expected_sha256"),
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
    bad_urls = [entry["url"] for entry in data["documents"] if not IRS_PDF_URL_RE.match(entry["url"])]
    if bad_urls:
        joined = ", ".join(sorted(bad_urls))
        raise ValueError(f"manifest URLs must use stable IRS PDF paths: {joined}")


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
