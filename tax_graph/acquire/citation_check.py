"""Verify authored citation quotes against acquired source text."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

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
    return check_citation_integrity(graph.items("citations"), text_dir=text_dir, source_map=source_map)


def check_citation_integrity(
    citations: list[dict[str, Any]],
    *,
    text_dir: str | Path,
    source_map: dict[str, str] | None = None,
) -> CitationIntegrityReport:
    """Check citation quoted_text against acquired text files."""
    text_root = Path(text_dir)
    document_map = source_map or {}
    mismatches: list[CitationMismatch] = []

    for citation in citations:
        document_id = citation["document_id"]
        source_document_id = document_map.get(document_id, document_id)
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

        text = text_path.read_text(encoding="utf-8")
        if not _contains_normalized(text, citation["quoted_text"]):
            mismatches.append(
                CitationMismatch(
                    citation_id=citation["citation_id"],
                    document_id=document_id,
                    source_document_id=source_document_id,
                    reason="quote not found",
                )
            )

    return CitationIntegrityReport(checked=len(citations), mismatches=mismatches)


def _contains_normalized(haystack: str, needle: str) -> bool:
    return _normalize_ws(needle) in _normalize_ws(haystack)


def _normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
