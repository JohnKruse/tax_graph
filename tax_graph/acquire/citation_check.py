"""Verify authored citation quotes against acquired source text."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from tax_graph.acquire.text_normalize import normalize_punctuation
from tax_graph.acquire.source_ranges import (
    SourceDocumentNotFound,
    SourceRangeOutOfBounds,
    SourceTextIndex,
    resolve_source_range,
)

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
    """Check range-bearing citation quotes against acquired text spans."""
    text_root = Path(text_dir)
    document_map = source_map or {}
    pin_map = source_pins or {}
    mismatches: list[CitationMismatch] = []
    checked = 0
    checked_sources: set[str] = set()

    for citation in citations:
        document_id = citation["document_id"]
        source_document_id = _resolve_source_document_id(citation, document_map)
        ranges = citation.get("ranges") or ()
        if citation.get("kind") != "computed_table" and not ranges:
            # Legacy HTML and intake citations predate source ranges.  They
            # are outside this range contract and cannot use a substrate
            # fallback without recreating the defect this check prevents.
            continue
        checked += 1
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

        if not ranges:
            # Computed-table citations are checked for their typed metadata
            # above, so this branch is only defensive for malformed input.
            continue
        try:
            first = ranges[0]
            last = ranges[-1]
            span = resolve_source_range(
                source_document_id,
                int(first["start"]),
                int(last["end"]),
                text_dir=text_root,
            )
        except SourceDocumentNotFound:
            mismatches.append(
                CitationMismatch(
                    citation_id=citation["citation_id"],
                    document_id=document_id,
                    source_document_id=source_document_id,
                    reason="missing text",
                )
            )
            continue
        except (KeyError, TypeError, ValueError, SourceRangeOutOfBounds) as exc:
            mismatches.append(
                CitationMismatch(
                    citation_id=citation["citation_id"],
                    document_id=document_id,
                    source_document_id=source_document_id,
                    reason=f"invalid source range: {exc}",
                )
            )
            continue
        quote = str(citation["quoted_text"])
        if _contains_normalized(span, quote):
            continue
        if _ordered_tokens_in_span(span, quote):
            continue
        mismatches.append(
            CitationMismatch(
                citation_id=citation["citation_id"],
                document_id=document_id,
                source_document_id=source_document_id,
                reason="quote not found in cited range",
            )
        )

    return CitationIntegrityReport(checked=checked, mismatches=mismatches)


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


def _contains_normalized(haystack: str, needle: str) -> bool:
    normalized_haystack = _normalize_ws(haystack)
    normalized_needle = _normalize_ws(needle)
    return normalized_needle in normalized_haystack


def _ordered_tokens_in_span(span: str, quote: str) -> bool:
    """Allow source-layout elision while keeping the cited span anchored."""
    source_tokens = SourceTextIndex(span).tokens
    quote_tokens = SourceTextIndex(quote).tokens
    if not source_tokens or not quote_tokens:
        return False
    if (
        source_tokens[0].start != quote_tokens[0].start
        or source_tokens[0].value != quote_tokens[0].value
    ):
        return False
    cursor = 0
    for wanted in quote_tokens:
        while cursor < len(source_tokens) and source_tokens[cursor].value != wanted.value:
            cursor += 1
        if cursor == len(source_tokens):
            return False
        cursor += 1
    return True


def _normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", _normalize_punctuation(value)).strip()


def _normalize_punctuation(value: str) -> str:
    return normalize_punctuation(value)
