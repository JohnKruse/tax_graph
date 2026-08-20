"""Load rendered acquisition artifacts for extraction."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from tax_graph.acquire.manifest import AcquisitionManifest, load_manifest
from tax_graph.acquire.source_ranges import resolve_source_range
from tax_graph.acquire.html_source import HtmlSourceIndex, html_source_path
from tax_graph.config import get_config_value, load_config, project_root
from tax_graph.extract.models import RelatedSourceInput, SourceDocumentInput
from tax_graph.io.loader import load_graph


FORM_KINDS = {"tax_form", "schedule", "source_document"}
INSTRUCTION_KINDS = {"instructions", "publication"}
_FACE_TOKEN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|[0-9]+(?:[A-Za-z]+)?")
_WORKSHEET_FACE_CACHE: dict[tuple[str, str, str], dict[str, str]] = {}


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
    if entry.kind in INSTRUCTION_KINDS:
        html_path = text_dir / f"{document_id}.html"
        if html_path.exists():
            text_path = html_path
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
    governed_notes: dict[str, list[dict[str, Any]]] = {}
    for citation in citations.values():
        if (
            citation.get("document_id") != document_id
            or citation.get("kind") != "note"
        ):
            continue
        for governed_line in citation.get("governs") or []:
            governed_notes.setdefault(str(governed_line).lower(), []).append(citation)
    if document is None:
        raise FileNotFoundError(
            f"promoted region document is missing from graph: {document_id}"
        )
    if not nodes:
        raise FileNotFoundError(
            f"promoted region line nodes are missing from graph: {document_id}"
        )
    source_path = root / ".cache" / "raw" / year / f"{parent_id}.txt"
    html_path = source_path.with_suffix(".html")
    if html_path.exists():
        source_path = html_path
    source_text = source_path.read_text(encoding="utf-8") if source_path.exists() else ""
    html_faces = _worksheet_html_faces(
        document_id,
        entry=entry,
        year=year,
        root=root,
    )

    def line_key(item: dict[str, Any]) -> tuple[int, str]:
        match = re.search(r"_line_([0-9]+[a-z]?|[a-z])(?:$|_)", str(item.get("node_id") or ""), re.IGNORECASE)
        value = match.group(1).lower() if match else ""
        number = re.match(r"[0-9]+", value)
        return (int(number.group(0)) if number else 10**9, value)

    rows: list[tuple[str, str, str]] = []
    governed_note_provenance: dict[str, list[dict[str, str]]] = {}
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
                if citation.get("kind", "row") == "row":
                    html_face = html_faces.get(node_id, "")
                    if html_face and citation.get("ranges"):
                        # The node id is the deterministic HTML row selected
                        # for these ranges.  The range projection trims only
                        # source chunks that bleed into a neighboring row;
                        # retain the row's form controls for the existing
                        # cell-face cleaner.
                        quote = _worksheet_face_from_ranges(
                            html_face,
                            citation,
                            source_text,
                        )
                    else:
                        quote = re.sub(
                            rf'^\s*{re.escape(line)}\s*[.):]?\s*',
                            "",
                            quote,
                            count=1,
                            flags=re.IGNORECASE,
                        )
                if quote:
                    break
        if not quote:
            quote = str(node.get("label") or "").strip()
        quote = re.sub(
            rf"^\s*{re.escape(line)}\s*[.):]?\s*",
            "",
            quote,
            count=1,
            flags=re.IGNORECASE,
        )
        note_provenance: list[dict[str, str]] = []
        for note in governed_notes.get(line, []):
            governed_lines = [str(value).lower() for value in note.get("governs") or []]
            if not governed_lines or line == governed_lines[0]:
                continue
            note_text = str(note.get("quoted_text") or "").strip()
            if not note_text:
                continue
            note_provenance.append(
                {
                    "source_line": str(note.get("locator") or "").split("after=", 1)[-1],
                    "target_line": line,
                    "citation_id": str(note.get("citation_id") or ""),
                    "text": note_text,
                }
            )
        if note_provenance:
            governed_note_provenance[line] = note_provenance
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
        fields={
            "fields": fields,
            "line_anchors": line_anchors,
            "governed_note_provenance": governed_note_provenance,
        },
        fields_path=None,
        pages_dir=None,
        links=[],
        links_path=None,
        related_sources=[],
        not_modeled_fields=list(document.get("not_modeled_fields", []) or []),
        source_document_id=parent_id,
    )


def _worksheet_html_faces(
    document_id: str,
    *,
    entry: Any,
    year: str,
    root: Path,
) -> dict[str, str]:
    """Render a transient HTML face bounded by the promoted source ranges."""
    key = (str(root), str(year), document_id)
    if key in _WORKSHEET_FACE_CACHE:
        return _WORKSHEET_FACE_CACHE[key]
    html_path = root / ".cache" / "raw" / year / f"{entry.region_of}.html"
    if not html_path.exists():
        _WORKSHEET_FACE_CACHE[key] = {}
        return {}
    try:
        from tax_graph.ingest.worksheet_harvest import WorksheetTarget, harvest_worksheet_file

        result = harvest_worksheet_file(
            html_path,
            WorksheetTarget(
                document_id=document_id,
                title=str(entry.region_title or document_id),
                start_anchor="",
                source_document_id=str(entry.region_of or ""),
            ),
            source_document_id=str(entry.region_of or ""),
            year=year,
            advisories_enabled=True,
        )
    except (OSError, RuntimeError, ValueError):
        _WORKSHEET_FACE_CACHE[key] = {}
        return {}
    faces = {
        str(node["node_id"]): str(node.source_quote or "")
        for node in result.nodes
        if node.get("node_type") == "worksheet_field"
    }
    _WORKSHEET_FACE_CACHE[key] = faces
    return faces


def _worksheet_face_from_ranges(
    html_face: str,
    citation: dict[str, Any],
    source_text: str,
) -> str:
    """Project a transient HTML face onto a citation's source ranges."""
    if not html_face or not source_text or not citation.get("ranges"):
        return html_face
    source_document_id = str(
        citation.get("source_document_id") or citation.get("document_id") or ""
    )
    if source_document_id.startswith("instructions_") and "<" in source_text[:1000]:
        source_value = HtmlSourceIndex(source_text).visible_text_for_ranges(citation["ranges"])
    else:
        source_value = " ".join(
            resolve_source_range(
                source_document_id,
                int(item["start"]),
                int(item["end"]),
                source_text=source_text,
            )
            for item in citation["ranges"]
        )
    expected = tuple(_FACE_TOKEN_RE.finditer(source_value))
    actual = tuple(_FACE_TOKEN_RE.finditer(html_face))
    if not expected or not actual:
        return html_face
    cursor = 0
    first_start: int | None = None
    last_end = 0
    for token in expected:
        wanted = token.group(0).casefold().replace("'", "")
        while cursor < len(actual):
            candidate = actual[cursor]
            cursor += 1
            if candidate.group(0).casefold().replace("'", "") == wanted:
                if first_start is None:
                    first_start = candidate.start()
                last_end = candidate.end()
                break
        else:
            return html_face
    if first_start is None:
        return html_face
    line = str(citation.get("locator") or "").rsplit("lines=", 1)[-1]
    if (
        re.fullmatch(r"[0-9]+[a-z]", line, flags=re.IGNORECASE)
        and first_start > 0
        and html_face[:first_start].strip()
    ):
        # Lettered output columns may be represented by marker-only source
        # ranges while the preceding HTML cell carries the column's prose.
        # Preserve the full deterministic cell so the existing face cleaner
        # can remove the repeated marker and continuation furniture.
        return html_face
    trimmed = html_face[first_start:last_end]
    tail = html_face[last_end:]
    tail_tokens = tuple(_FACE_TOKEN_RE.finditer(tail))
    if not tail_tokens:
        return html_face
    first = tail_tokens[0].group(0).casefold()
    if first in {"field", "checkbox"}:
        return html_face
    if re.fullmatch(r"[0-9]+[a-z]?", first) and first == line.casefold():
        return html_face
    if re.fullmatch(rf"{re.escape(line)}[a-z]", first) or first in {"no", "yes"}:
        return html_face
    if not re.search(r"\bnote\b", tail, flags=re.IGNORECASE):
        # Preserve deterministic output controls and routing continuations;
        # the existing cell-face cleaner removes their repeated markers.
        return html_face
    note_match = re.search(r"\bnote\b", tail, flags=re.IGNORECASE)
    if note_match is not None:
        # Keep the row's printed output marker when it precedes a separate
        # note. The marker gives the extent cleaner the same bounded cell it
        # had before the note became its own citation.
        bounded = html_face[: last_end + note_match.start()].rstrip()
        if bounded.startswith('"'):
            content = bounded[1:].rstrip(" .\"")
            punctuation = "" if content.endswith((".", "?", "!")) else "."
            return f'"{content}{punctuation}" field'
        return bounded
    repeated_marker = re.search(
        rf"\s+{re.escape(line)}\s*$",
        trimmed,
        flags=re.IGNORECASE,
    )
    if repeated_marker:
        trimmed = trimmed[: repeated_marker.start()].rstrip()
    if html_face.startswith('"'):
        punctuation = "" if trimmed.rstrip().endswith((".", "?", "!")) else "."
        return '"' + trimmed.rstrip(" .") + punctuation + '" field'
    return trimmed


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
    if entry.kind in INSTRUCTION_KINDS:
        html_path = text_dir / f"{document_id}.html"
        if html_path.exists():
            text_path = html_path
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
