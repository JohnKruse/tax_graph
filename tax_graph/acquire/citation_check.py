"""Verify authored citation quotes against acquired source text."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any

from tax_graph.acquire.text_normalize import normalize_punctuation
from tax_graph.acquire.source_ranges import (
    SourceDocumentNotFound,
    SourceRangeOutOfBounds,
    SourceAlignment,
    SourceTextIndex,
    load_source_text,
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
class CitationUnverifiable:
    """A citation intentionally outside the current source-range contract."""

    citation_id: str
    document_id: str
    source_document_id: str
    reason: str


@dataclass(frozen=True)
class CitationIntegrityReport:
    """Citation integrity result."""

    checked: int
    mismatches: list[CitationMismatch]
    unverifiable_citations: list[CitationUnverifiable] = field(default_factory=list)
    range_telltales: list["CitationRangeTelltale"] = field(default_factory=list)
    provenance_findings: list["CitationProvenanceFinding"] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Whether every checked citation matched."""
        return not self.mismatches


@dataclass(frozen=True)
class CitationRangeTelltale:
    """Non-gating evidence about fragmented citation ranges."""

    citation_id: str
    document_id: str
    source_document_id: str
    fragment_lengths: tuple[int, ...]
    short_fragment_count: int
    gaps: tuple[int, ...]
    large_gap_count: int


@dataclass(frozen=True)
class CitationProvenanceFinding:
    """A range list whose quote also has a contiguous source location."""

    citation_id: str
    document_id: str
    source_document_id: str
    stored_ranges: tuple[dict[str, int], ...]
    correct_ranges: tuple[dict[str, int], ...]
    fragments: tuple[str, ...]
    gaps: tuple[int, ...]
    repair_quote: str | None = None
    repair_blocker: str | None = None


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
        require_ranges=False,
    )


def check_citation_integrity(
    citations: list[dict[str, Any]],
    *,
    text_dir: str | Path,
    source_map: dict[str, str] | None = None,
    source_pins: dict[str, str] | None = None,
    require_ranges: bool = True,
) -> CitationIntegrityReport:
    """Check citation quotes against acquired text spans.

    Promoted legacy HTML and intake citations may omit source ranges, so the
    graph-wide check leaves those records outside the range contract. Draft
    extraction checks pass ``require_ranges=True`` so an unverifiable model
    citation is reported instead of passing silently.
    """
    text_root = Path(text_dir)
    document_map = source_map or {}
    pin_map = source_pins or {}
    mismatches: list[CitationMismatch] = []
    unverifiable_citations: list[CitationUnverifiable] = []
    range_telltales: list[CitationRangeTelltale] = []
    provenance_findings: list[CitationProvenanceFinding] = []
    checked = 0
    checked_sources: set[str] = set()
    source_text_cache: dict[str, str] = {}

    for citation in citations:
        document_id = citation["document_id"]
        source_document_id = _resolve_source_document_id(citation, document_map)
        ranges = citation.get("ranges") or ()
        if citation.get("kind") != "computed_table" and not ranges:
            unverifiable_citations.append(
                CitationUnverifiable(
                    citation_id=citation["citation_id"],
                    document_id=document_id,
                    source_document_id=source_document_id,
                    reason="missing source ranges",
                )
            )
            if require_ranges:
                checked += 1
                mismatches.append(
                    CitationMismatch(
                        citation_id=citation["citation_id"],
                        document_id=document_id,
                        source_document_id=source_document_id,
                        reason="missing source ranges",
                    )
                )
            # Promoted legacy HTML and intake citations predate source ranges.
            # They are outside this range contract and cannot use a substrate
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
            resolved_ranges = tuple(
                {
                    "start": int(item["start"]),
                    "end": int(item["end"]),
                }
                for item in ranges
            )
            fragments = tuple(
                resolve_source_range(
                    source_document_id,
                    item["start"],
                    item["end"],
                    text_dir=text_root,
                )
                for item in resolved_ranges
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
        source_text = source_text_cache.get(source_document_id)
        if source_text is None:
            source_text = load_source_text(source_document_id, text_dir=text_root)
            source_text_cache[source_document_id] = source_text
        span = _join_source_fragments(source_text, resolved_ranges, fragments)
        telltale = _range_telltale(
            citation,
            source_document_id=source_document_id,
            ranges=resolved_ranges,
            fragments=fragments,
        )
        range_telltales.append(telltale)
        if telltale.large_gap_count:
            correct_ranges = _contiguous_quote_ranges(source_text, quote)
            repair_quote, repair_blocker = _repair_provenance(source_text, quote)
            if repair_quote is not None:
                correct_ranges = _contiguous_quote_ranges(source_text, repair_quote)
                if correct_ranges is not None:
                    correct_ranges = _split_table_separator_ranges(source_text, correct_ranges)
            if correct_ranges and correct_ranges != resolved_ranges:
                provenance_findings.append(
                    CitationProvenanceFinding(
                        citation_id=str(citation["citation_id"]),
                        document_id=document_id,
                        source_document_id=source_document_id,
                        stored_ranges=resolved_ranges,
                        correct_ranges=correct_ranges,
                        fragments=fragments,
                        gaps=telltale.gaps,
                        repair_quote=repair_quote,
                        repair_blocker=repair_blocker,
                    )
                )
        if _contains_normalized(span, quote):
            continue
        mismatches.append(
            CitationMismatch(
                citation_id=citation["citation_id"],
                document_id=document_id,
                source_document_id=source_document_id,
                reason="quote not found in cited range",
            )
        )

    return CitationIntegrityReport(
        checked=checked,
        mismatches=mismatches,
        unverifiable_citations=unverifiable_citations,
        range_telltales=range_telltales,
        provenance_findings=provenance_findings,
    )


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


def _range_telltale(
    citation: dict[str, Any],
    *,
    source_document_id: str,
    ranges: tuple[dict[str, int], ...],
    fragments: tuple[str, ...],
) -> CitationRangeTelltale:
    """Summarize fragmented ranges without making the summary a gate."""
    gaps = tuple(
        following["start"] - preceding["end"]
        for preceding, following in zip(ranges, ranges[1:])
    )
    fragment_lengths = tuple(len(fragment) for fragment in fragments)
    return CitationRangeTelltale(
        citation_id=str(citation["citation_id"]),
        document_id=str(citation["document_id"]),
        source_document_id=source_document_id,
        fragment_lengths=fragment_lengths,
        short_fragment_count=sum(length < 12 for length in fragment_lengths),
        gaps=gaps,
        large_gap_count=sum(gap > 1000 for gap in gaps),
    )


def _contiguous_quote_ranges(source_text: str, quote: str) -> tuple[dict[str, int], ...] | None:
    """Find a single contiguous token passage for provenance diagnosis."""
    source_index = SourceTextIndex(source_text)
    quote_tokens = SourceTextIndex(quote).tokens
    if not source_index.tokens or not quote_tokens:
        return None
    wanted = tuple(token.value for token in quote_tokens)
    width = len(wanted)
    for start in range(len(source_index.tokens) - width + 1):
        if tuple(
            source_index.tokens[start + offset].value for offset in range(width)
        ) != wanted:
            continue
        alignment = SourceAlignment(tuple(range(start, start + width)))
        return source_index.ranges_for_alignment(alignment)
    return None


def _repair_provenance(source_text: str, quote: str) -> tuple[str | None, str | None]:
    """Describe a minimal quote repair when the source lacks final punctuation."""
    trimmed = quote.rstrip()
    if trimmed.endswith("."):
        trimmed = trimmed[:-1].rstrip()
        if _contiguous_quote_ranges(source_text, trimmed) is not None:
            return (
                trimmed,
                "quoted_text has a trailing period that is absent from the source span",
            )
    return None, None


def _split_table_separator_ranges(
    source_text: str,
    ranges: tuple[dict[str, int], ...],
) -> tuple[dict[str, int], ...]:
    """Omit table and markdown separators while retaining source text."""
    split: list[dict[str, int]] = []
    for item in ranges:
        start = int(item["start"])
        end = _extend_markdown_suffix(source_text, start, int(item["end"]))
        cursor = start
        for match in re.finditer(
            r"\|+|\*{1,2}|(?<!\w)_{1,2}(?=\S)|(?<=\S)_{1,2}(?!\w)",
            source_text[start:end],
        ):
            separator = start + match.start()
            before_end = separator
            while before_end > cursor and source_text[before_end - 1].isspace():
                before_end -= 1
            if before_end > cursor:
                split.append({"start": cursor, "end": before_end})
            cursor = separator + len(match.group(0))
        if cursor < end:
            split.append({"start": cursor, "end": end})
    return tuple(split)


def _extend_markdown_suffix(source_text: str, start: int, end: int) -> int:
    """Include a closing emphasis marker and its following punctuation."""
    if end >= len(source_text) or source_text[end] not in "*_":
        return end
    marker = source_text[end]
    if marker not in source_text[start:end]:
        return end
    cursor = end
    while cursor < len(source_text) and source_text[cursor] == marker:
        cursor += 1
    while cursor < len(source_text) and source_text[cursor] in ".,;:!?)]}":
        cursor += 1
    return cursor


def _join_source_fragments(
    source_text: str,
    ranges: tuple[dict[str, int], ...],
    fragments: tuple[str, ...],
) -> str:
    """Join range fragments without inventing space before punctuation."""
    if not fragments:
        return ""
    span = fragments[0]
    for preceding, following, fragment in zip(ranges, ranges[1:], fragments[1:]):
        gap = source_text[int(preceding["end"]) : int(following["start"])]
        marker_only = bool(gap) and not gap.strip("*_ \t\r\n")
        separator = "" if marker_only and fragment[:1] in ".,;:!?)]}" else " "
        span += separator + fragment
    return span


def _normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", _normalize_punctuation(value)).strip()


def _normalize_punctuation(value: str) -> str:
    return normalize_punctuation(value)
