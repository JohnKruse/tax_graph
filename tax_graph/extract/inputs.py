"""Load rendered acquisition artifacts for extraction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tax_graph.acquire.manifest import load_manifest
from tax_graph.config import get_config_value, load_config, project_root
from tax_graph.extract.models import RelatedSourceInput, SourceDocumentInput
from tax_graph.io.loader import load_graph


FORM_KINDS = {"tax_form", "schedule", "source_document"}
INSTRUCTION_KINDS = {"instructions", "publication"}


def load_document_input(
    document_id: str,
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    raw_store: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> SourceDocumentInput:
    """Load rendered text and companion artifacts for one manifest document."""
    root_path = Path(root).resolve() if root is not None else project_root()
    settings = config if config is not None else load_config(root=root_path)
    store = Path(raw_store) if raw_store is not None else root_path / get_config_value(
        settings,
        "project.paths.raw_store",
        ".cache/raw",
    )
    if not store.is_absolute():
        store = root_path / store

    manifest = load_manifest(root=root_path)
    if str(manifest.tax_year) != str(year):
        raise ValueError(f"manifest tax_year {manifest.tax_year} does not match requested {year}")
    entries = manifest.by_document_id()
    if document_id not in entries:
        raise ValueError(f"unknown manifest document_id: {document_id}")

    entry = entries[document_id]
    text_dir = store / str(year)
    text_path = text_dir / f"{document_id}.txt"
    if not text_path.exists():
        raise FileNotFoundError(f"missing rendered text: {text_path}")

    fields = None
    fields_path = None
    if entry.kind in FORM_KINDS:
        fields_path = text_dir / f"{document_id}.fields.json"
        if not fields_path.exists():
            raise FileNotFoundError(f"missing rendered field grid: {fields_path}")
        fields = json.loads(fields_path.read_text(encoding="utf-8"))

    pages_dir = None
    links: list[dict[str, Any]] = []
    links_path = None
    if entry.kind in INSTRUCTION_KINDS:
        pages_dir = text_dir / f"{document_id}.pages"
        links_path = text_dir / f"{document_id}.links.json"
        if not pages_dir.is_dir():
            raise FileNotFoundError(f"missing rendered pages dir: {pages_dir}")
        if not links_path.exists():
            raise FileNotFoundError(f"missing rendered links: {links_path}")
        links = json.loads(links_path.read_text(encoding="utf-8"))
    related_sources = []
    if entry.instructions_document_id:
        related_sources.append(
            _load_related_source(
                entry.instructions_document_id,
                entries=entries,
                text_dir=text_dir,
                relationship="instructions",
            )
        )

    return SourceDocumentInput(
        document_id=document_id,
        kind=entry.kind,
        year=str(year),
        url=entry.url,
        text=text_path.read_text(encoding="utf-8"),
        text_path=text_path,
        fields=fields,
        fields_path=fields_path,
        pages_dir=pages_dir,
        links=links,
        links_path=links_path,
        related_sources=related_sources,
        not_modeled_fields=_load_not_modeled_fields(document_id, year=year, root=root_path),
    )


def _load_not_modeled_fields(document_id: str, *, year: str | int, root: Path) -> list[dict[str, Any]]:
    try:
        graph = load_graph(year, root)
    except FileNotFoundError:
        return []
    for document in graph.items("documents"):
        if document.get("document_id") == document_id:
            return list(document.get("not_modeled_fields", []) or [])
    return []


def _load_related_source(document_id: str, *, entries, text_dir: Path, relationship: str) -> RelatedSourceInput:
    entry = entries[document_id]
    text_path = text_dir / f"{document_id}.txt"
    if not text_path.exists():
        raise FileNotFoundError(f"missing related rendered text: {text_path}")

    links_path = text_dir / f"{document_id}.links.json"
    links: list[dict[str, Any]] = []
    if links_path.exists():
        links = json.loads(links_path.read_text(encoding="utf-8"))

    return RelatedSourceInput(
        document_id=document_id,
        kind=entry.kind,
        text=text_path.read_text(encoding="utf-8"),
        text_path=text_path,
        links=links,
        links_path=links_path if links_path.exists() else None,
        relationship=relationship,
    )
