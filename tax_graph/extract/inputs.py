"""Load rendered acquisition artifacts for extraction."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from tax_graph.acquire.manifest import AcquisitionManifest, load_manifest
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
    manifest: AcquisitionManifest | None = None,
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

    active_manifest = manifest or load_manifest(root=root_path)
    if str(active_manifest.tax_year) != str(year):
        raise ValueError(f"manifest tax_year {active_manifest.tax_year} does not match requested {year}")
    entries = active_manifest.by_document_id()
    if document_id not in entries:
        raise ValueError(f"unknown manifest document_id: {document_id}")

    entry = entries[document_id]
    if entry.is_region:
        return _load_region_document_input(
            document_id,
            entry=entry,
            entries=entries,
            year=str(year),
            root=root_path,
            graph=load_graph(year, root_path),
        )

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


def _load_region_document_input(
    document_id: str,
    *,
    entry: Any,
    entries: dict[str, Any],
    year: str,
    root: Path,
    graph: Any,
) -> SourceDocumentInput:
    """Serve a manifest region from its promoted graph objects.

    A worksheet region is not an acquired artifact and must never acquire a
    synthetic raw-store text file.  Its harvested citations and line nodes
    are the extraction face; this function assembles those objects into the
    in-memory text shape consumed by the existing outline/cell pipeline.
    """
    parent_id = str(entry.region_of or "").strip()
    if not parent_id or parent_id not in entries:
        raise ValueError(f"region {document_id} has no valid parent document")

    document = next(
        (item for item in graph.items("documents") if item.get("document_id") == document_id),
        None,
    )
    nodes = [
        item
        for item in graph.items("nodes")
        if item.get("document_id") == document_id
        and item.get("node_type") == "worksheet_field"
    ]
    citations = {str(item.get("citation_id")): item for item in graph.items("citations")}
    if document is None:
        raise FileNotFoundError(
            f"promoted region document is missing from graph: {document_id}"
        )
    if not nodes:
        raise FileNotFoundError(
            f"promoted region line nodes are missing from graph: {document_id}"
        )

    def line_key(item: dict[str, Any]) -> tuple[int, str]:
        match = re.search(r"_line_([0-9]+[a-z]?|[a-z])(?:$|_)", str(item.get("node_id") or ""), re.IGNORECASE)
        value = match.group(1).lower() if match else ""
        number = re.match(r"[0-9]+", value)
        return (int(number.group(0)) if number else 10**9, value)

    rows: list[tuple[str, str, str]] = []
    for node in sorted(nodes, key=line_key):
        node_id = str(node.get("node_id") or "")
        match = re.search(r"_line_([0-9]+[a-z]?|[a-z])(?:$|_)", node_id, re.IGNORECASE)
        if match is None:
            continue
        line = match.group(1).lower()
        quote = ""
        for citation_id in node.get("citation_refs") or []:
            citation = citations.get(str(citation_id))
            if citation is not None:
                quote = str(citation.get("quoted_text") or "").strip()
                if quote:
                    break
        if not quote:
            quote = str(node.get("label") or "").strip()
        quote = re.sub(
            rf"^\s*{re.escape(line)}\s*[.)]?\s*",
            "",
            quote,
            count=1,
            flags=re.IGNORECASE,
        )
        rows.append((line, quote, node_id))
    if not rows:
        raise FileNotFoundError(
            f"promoted region has no addressable printed line nodes: {document_id}"
        )

    title = str(entry.region_title or document.get("title") or document_id)
    text_lines = [f"Header: {title}"]
    line_anchors: list[dict[str, Any]] = []
    fields: list[dict[str, Any]] = []
    for line, quote, node_id in rows:
        text_offset = sum(len(item) + 1 for item in text_lines)
        text_lines.append(f"- {line}: {quote}")
        line_anchors.append({"anchor": line, "text_offset": text_offset, "text_length": len(quote)})
        fields.append({
            "line_anchor": line,
            "field_type": str(next(
                (item.get("value_type") for item in nodes if item.get("node_id") == node_id),
                "currency",
            )),
            "promoted_node_id": node_id,
        })

    graph_dir = root / "graph" / year
    document_path = graph_dir / "documents" / f"{_document_file_stem(document_id)}.yaml"
    return SourceDocumentInput(
        document_id=document_id,
        kind=entry.kind,
        year=year,
        url=None,
        text="\n".join(text_lines) + "\n",
        text_path=document_path,
        fields={"fields": fields, "line_anchors": line_anchors},
        fields_path=None,
        pages_dir=None,
        links=[],
        links_path=None,
        related_sources=[],
        not_modeled_fields=list(document.get("not_modeled_fields", []) or []),
        source_document_id=parent_id,
    )


def _document_file_stem(document_id: str) -> str:
    """Match the promotion filename convention for an in-memory provenance path."""
    stem = re.sub(r"_20[0-9]{2}$", "", document_id)
    return stem.replace("_", "-")


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
