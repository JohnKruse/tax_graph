"""Verify authored citation quotes against acquired source text."""

from __future__ import annotations

from dataclasses import dataclass
import json
from html.parser import HTMLParser
from pathlib import Path
import re
from typing import Any

from tax_graph.acquire.text_normalize import normalize_punctuation

from tax_graph.acquire.manifest import load_manifest
from tax_graph.io.loader import load_graph


@dataclass(frozen=True)
class CitationMismatch:
    """A citation whose quoted text could not be found in acquired text."""

    citation_id: str
    document_id: str
    source_document_id: str
    reason: str


@dataclass(frozen=True)
class CitationIntegrityReport:
    """Citation integrity result."""

    checked: int
    mismatches: list[CitationMismatch]

    @property
    def ok(self) -> bool:
        """Whether every checked citation matched."""
        return not self.mismatches


def check_graph_citations(
    *,
    year: str | int,
    raw_store: str | Path,
    root: str | Path | None = None,
    source_map: dict[str, str] | None = None,
) -> CitationIntegrityReport:
    """Check graph citation quotes against rendered text in the raw store."""
    graph = load_graph(year, root)
    text_dir = Path(raw_store) / str(year)
    manifest = load_manifest(root=root)
    source_pins = {
        entry.document_id: entry.expected_sha256
        for entry in manifest.documents
        if entry.expected_sha256
    }
    return check_citation_integrity(
        graph.items("citations"),
        text_dir=text_dir,
        source_map=source_map,
        source_pins=source_pins,
    )


def check_citation_integrity(
    citations: list[dict[str, Any]],
    *,
    text_dir: str | Path,
    source_map: dict[str, str] | None = None,
    source_pins: dict[str, str] | None = None,
) -> CitationIntegrityReport:
    """Check citation quoted_text against acquired text files."""
    text_root = Path(text_dir)
    document_map = source_map or {}
    pin_map = source_pins or {}
    mismatches: list[CitationMismatch] = []
    checked_sources: set[str] = set()

    for citation in citations:
        document_id = citation["document_id"]
        source_document_id = _resolve_source_document_id(citation, document_map)
        if source_document_id not in checked_sources:
            checked_sources.add(source_document_id)
            drift_reason = _detect_source_drift(text_root, source_document_id, pin_map)
            if drift_reason is not None:
                mismatches.append(
                    CitationMismatch(
                        citation_id=f"source_drift_{source_document_id}",
                        document_id=document_id,
                        source_document_id=source_document_id,
                        reason=drift_reason,
                    )
                )
                continue
        text_path = text_root / f"{source_document_id}.txt"
        if not text_path.exists():
            mismatches.append(
                CitationMismatch(
                    citation_id=citation["citation_id"],
                    document_id=document_id,
                    source_document_id=source_document_id,
                    reason="missing text",
                )
            )
            continue

        if citation.get("kind") == "computed_table":
            # A computed-table citation proves the source table and records
            # the derivation, but it must not impersonate a verbatim quote.
            if not citation.get("ranges") or not citation.get("derivation"):
                mismatches.append(
                    CitationMismatch(
                        citation_id=citation["citation_id"],
                        document_id=document_id,
                        source_document_id=source_document_id,
                        reason="computed citation missing ranges or derivation",
                    )
                )
            continue

        text = text_path.read_text(encoding="utf-8")
        undecorated = _undecorated_text(text)
        if _contains_normalized(undecorated, citation["quoted_text"]):
            continue
        html_path = text_root / f"{source_document_id}.html"
        if html_path.exists() and _contains_normalized(
            _html_text(html_path.read_text(encoding="ascii")), citation["quoted_text"]
        ):
            continue
        pdf_path = text_root / f"{source_document_id}.pdf"
        pdf_text = _load_pdf_text(pdf_path)
        if pdf_text is not None and _contains_normalized(pdf_text, citation["quoted_text"]):
            continue
        if not _contains_normalized(undecorated, citation["quoted_text"]):
            mismatches.append(
                CitationMismatch(
                    citation_id=citation["citation_id"],
                    document_id=document_id,
                    source_document_id=source_document_id,
                    reason="quote not found",
                )
            )

    return CitationIntegrityReport(checked=len(citations), mismatches=mismatches)


def _resolve_source_document_id(citation: dict[str, Any], source_map: dict[str, str]) -> str:
    explicit = citation.get("source_document_id")
    if explicit:
        return str(explicit)
    document_id = str(citation["document_id"])
    return str(source_map.get(document_id, document_id))


def _detect_source_drift(text_root: Path, source_document_id: str, source_pins: dict[str, str]) -> str | None:
    expected = source_pins.get(source_document_id)
    if not expected:
        return None
    metadata_path = text_root / f"{source_document_id}.json"
    if not metadata_path.exists():
        return f"source drift: missing metadata for pinned document {source_document_id}"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    actual = str(metadata.get("content_hash") or "").lower()
    if actual != expected.lower():
        return f"source drift: expected sha256 {expected.lower()}, got {actual or 'missing'}"
    return None


def _load_pdf_text(pdf_path: Path) -> str | None:
    if not pdf_path.exists():
        return None
    try:
        import fitz
    except ImportError:
        return None

    pages: list[str] = []
    with fitz.open(pdf_path) as document:
        for page in document:
            pages.append(page.get_text("text"))
    return "\n".join(pages)


def _contains_normalized(haystack: str, needle: str) -> bool:
    normalized_haystack = _normalize_ws(haystack)
    normalized_needle = _normalize_ws(needle)
    return normalized_needle in normalized_haystack


def _undecorated_text(value: str) -> str:
    lines: list[str] = []
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("# Page "):
            continue
        if line.startswith("Header:"):
            lines.append(line.removeprefix("Header:").strip())
            continue
        lines.append(line)
    return "\n".join(lines)


def _html_text(value: str) -> str:
    """Extract stored HTML text for citation verification without network access."""

    class _TextParser(HTMLParser):
        _BLOCK_TAGS = {"br", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "p", "table", "td", "tr"}

        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.parts: list[str] = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag.lower() in self._BLOCK_TAGS:
                self.parts.append(" ")

        def handle_endtag(self, tag: str) -> None:
            if tag.lower() in self._BLOCK_TAGS:
                self.parts.append(" ")

        def handle_data(self, data: str) -> None:
            self.parts.append(data)

    parser = _TextParser()
    parser.feed(value)
    parser.close()
    return "".join(parser.parts)


def _normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", _normalize_punctuation(value)).strip()


def _normalize_punctuation(value: str) -> str:
    return normalize_punctuation(value)
