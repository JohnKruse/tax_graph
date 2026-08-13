"""Measure source ranges for the current deterministic form-face projection.

This pilot is deliberately read-only. It loads the manifest-defined face
corpus, aligns each projected form-face evidence span to the acquired source,
and reports the ranges, gaps, overlaps, and refusal reasons. It does not
change production code, graph artifacts, or the manifest.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

import yaml

from tax_graph.acquire.manifest import AcquisitionManifest, ManifestEntry, load_manifest
from tax_graph.config import get_config_value, load_config
from tax_graph.extract.cells import CellRecord, build_cell_frame_from_document
from tax_graph.extract.inputs import load_document_input


FACE_KINDS = frozenset({"tax_form", "schedule", "source_document"})
TOKEN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|[0-9]+(?:[A-Za-z]+)?")
DOT_LEADER_RE = re.compile(r"(?:\.{2,}|\.\s+\.|_{2,}|\\_{2,})")
NOTE_RE = re.compile(r"\bnote\b", re.IGNORECASE)
ROUTING_RE = re.compile(
    r"\b(?:go\s+to\s+line|otherwise|skip\s+lines?|also\s+enter)\b",
    re.IGNORECASE,
)
LINE_RE = re.compile(r"\bline\s+([0-9]+[a-z]?)\b", re.IGNORECASE)
FURNITURE_RE = re.compile(
    r"\b(?:paperwork\s+reduction\s+act|privacy\s+act|cat\.?\s+no\.?|"
    r"attachment\s+sequence|created\s+[0-9/]+|omb\s+no\.?|"
    r"department\s+of\s+the\s+treasury|internal\s+revenue\s+service)\b",
    re.IGNORECASE,
)
RULE_CONDITION_RE = re.compile(
    r"\b(?:if|unless|when|only\s+if|otherwise|must|do\s+not|don't|"
    r"check\s+if|complete|attach|claim|file)\b",
    re.IGNORECASE,
)
RULE_OPERATION_RE = re.compile(
    r"\b(?:enter|add|subtract|multiply|divide|include|exclude|report|"
    r"apply|use|calculate|compute|sum|total|amount\s+from)\b",
    re.IGNORECASE,
)
THRESHOLD_RE = re.compile(
    r"\b(?:over|under|less\s+than|greater\s+than|more\s+than|"
    r"at\s+least|not\s+over|exceeds|equal(?:s)?|between)\b|\$\s*[0-9]",
    re.IGNORECASE,
)
MARKDOWN_TABLE_RE = re.compile(r"\|[^\r\n]*\|(?:\s*\|[^\r\n]*\|)+")


@dataclass(frozen=True)
class SourceToken:
    """One lexical token and its source character offsets."""

    value: str
    start: int
    end: int


@dataclass(frozen=True)
class SourceWindow:
    """The source interval in which one corpus document may claim text."""

    source_document_id: str
    start: int
    end: int
    owner_document_id: str


@dataclass(frozen=True)
class Alignment:
    """A completed lexical alignment from a face to source tokens."""

    token_indexes: tuple[int, ...]


def _token_value(value: str) -> str:
    """Normalize only lexical spelling needed for acquired-text comparison."""
    return value.casefold().replace("'", "")


def _tokens(text: str) -> tuple[SourceToken, ...]:
    """Return stable lexical tokens with source character offsets."""
    return tuple(
        SourceToken(_token_value(match.group(0)), match.start(), match.end())
        for match in TOKEN_RE.finditer(text)
    )


def _canonical_heading(value: str) -> str:
    """Collapse heading punctuation for the renderer's joined heading style."""
    return "".join(character.casefold() for character in value if character.isalnum())


def _heading_start(source: str, title: str) -> int | None:
    """Find a worksheet heading, including headings joined to ``Lines``."""
    wanted = _canonical_heading(title)
    offset = 0
    previous_nonempty = ""
    for line in source.splitlines(keepends=True):
        stripped = line.strip()
        heading_text = line.lstrip("#* ").strip()
        is_heading = line.lstrip().startswith("#")
        is_page_following_title = (
            bool(previous_nonempty)
            and _canonical_heading(previous_nonempty).startswith("page")
            and _canonical_heading(heading_text).startswith(wanted)
        )
        if (is_heading or is_page_following_title) and _canonical_heading(
            heading_text
        ).startswith(wanted):
            return offset
        if stripped:
            previous_nonempty = stripped
        offset += len(line)
    return None


def _source_path(root: Path, year: str, source_document_id: str) -> Path:
    """Return the acquired text path for a source document."""
    config = load_config(root=root)
    raw_store = Path(get_config_value(config, "project.paths.raw_store", ".cache/raw"))
    if not raw_store.is_absolute():
        raw_store = root / raw_store
    return raw_store / year / f"{source_document_id}.txt"


def _face_text(row: CellRecord) -> str:
    """Return the original form-face evidence span used by the cell frame."""
    span_id = str(row.metadata.get("form_face_span_id") or "")
    face = ""
    for span in row.metadata.get("evidence_spans") or []:
        if str(span.get("span_id") or "") == span_id:
            face = str(span.get("text") or "")
            break
    if not face:
        face = str(row.metadata.get("form_face_before") or row.form_face_text or "")
    # A routed worksheet note is deliberately measured as an unclaimed source
    # chunk governed by its target line. It must not be re-claimed by the
    # target row merely because the in-memory projection prepended it.
    for provenance in row.metadata.get("routed_note_provenance") or []:
        note = str(provenance.get("text") or "")
        note = re.sub(r"^\s*note\.\s*", "", note, flags=re.IGNORECASE)
        if note:
            face = face.replace(note, " ", 1)
    return face


def _positions(tokens: Iterable[SourceToken]) -> dict[str, tuple[int, ...]]:
    """Index token values to source-token positions."""
    result: dict[str, list[int]] = defaultdict(list)
    for index, token in enumerate(tokens):
        result[token.value].append(index)
    return {key: tuple(value) for key, value in result.items()}


def _align(
    source_tokens: tuple[SourceToken, ...],
    positions: Mapping[str, tuple[int, ...]],
    face_tokens: tuple[str, ...],
    *,
    start: int,
    end: int,
) -> Alignment | None:
    """Greedily align a face token sequence in source order inside a window."""
    if not face_tokens:
        return None
    best: tuple[tuple[int, int, int], tuple[int, ...]] | None = None
    for first in positions.get(face_tokens[0], ()):
        if source_tokens[first].start < start:
            continue
        matched = [first]
        current = first
        complete = True
        for wanted in face_tokens[1:]:
            next_index = next(
                (
                    candidate
                    for candidate in positions.get(wanted, ())
                    if candidate > current and source_tokens[candidate].end <= end
                ),
                None,
            )
            if next_index is None:
                complete = False
                break
            matched.append(next_index)
            current = next_index
        if complete and source_tokens[matched[-1]].end <= end:
            skipped_tokens = sum(
                max(0, current_index - previous_index - 1)
                for previous_index, current_index in zip(matched, matched[1:])
            )
            span = source_tokens[matched[-1]].end - source_tokens[matched[0]].start
            score = (span, skipped_tokens, matched[0])
            candidate = (score, tuple(matched))
            if best is None or candidate[0] < best[0]:
                best = candidate
    return Alignment(best[1]) if best is not None else None


def _range_break(gap: str) -> bool:
    """Return whether a tokenless source gap needs a separate source range."""
    return bool(DOT_LEADER_RE.search(gap))


def _ranges_for_alignment(
    source: str,
    source_tokens: tuple[SourceToken, ...],
    alignment: Alignment,
) -> tuple[dict[str, int], ...]:
    """Build source ranges and preserve dot-leader/layout gaps as boundaries."""
    indexes = alignment.token_indexes
    ranges: list[dict[str, int]] = []
    range_start = source_tokens[indexes[0]].start
    previous_end = source_tokens[indexes[0]].end
    for previous, current in zip(indexes, indexes[1:]):
        gap = source[source_tokens[previous].end : source_tokens[current].start]
        if _range_break(gap):
            ranges.append({"start": range_start, "end": previous_end})
            range_start = source_tokens[current].start
        previous_end = source_tokens[current].end
    ranges.append({"start": range_start, "end": previous_end})
    return tuple(ranges)


def _fingerprint(value: str) -> str:
    """Return a stable fingerprint without copying acquired prose to output."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _ascii_preview(value: str, limit: int = 180) -> str:
    """Make a short report-safe preview of acquired text."""
    preview = " ".join(value.split())[:limit]
    return preview.encode("ascii", errors="replace").decode("ascii")


def _gap_kind(value: str) -> str:
    """Classify a meaningful source gap for the human measurement queue."""
    if NOTE_RE.search(value):
        return "note"
    if ROUTING_RE.search(value):
        return "routing_sentence"
    if re.search(r"\b(?:table|filing\s+status|if\s+your)\b", value, re.IGNORECASE):
        return "table_or_header"
    return "unclassified_source_chunk"


def _governs(value: str) -> list[str]:
    """Return printed line addresses named by an unclaimed chunk."""
    return list(dict.fromkeys(match.group(1).lower() for match in LINE_RE.finditer(value)))


def _meaningful_gap(value: str) -> bool:
    """Ignore whitespace and visual filler when reporting unclaimed runs."""
    return bool(re.sub(r"[\s._|\\-]+", "", value))


def _layout_only(value: str) -> tuple[bool, str]:
    """Recognize only source gaps that are mechanically safe to call scaffolding."""
    if FURNITURE_RE.search(value):
        return True, "page_or_form_furniture"
    if not re.search(r"[A-Za-z]", value):
        return True, "non_lexical_layout"
    words = re.findall(r"[A-Za-z]+", value)
    if words and all(len(word) == 1 for word in words) and DOT_LEADER_RE.search(value):
        return True, "field_marker_layout"
    if MARKDOWN_TABLE_RE.fullmatch(value.strip()):
        cells = [cell.strip() for cell in value.split("|") if cell.strip()]
        if cells and all(not re.search(r"[A-Za-z]{2,}", cell) for cell in cells):
            return True, "table_layout_markers"
    return False, ""


def partition_unclaimed_text(value: str, *, kind: str = "") -> tuple[str, str]:
    """Conservatively partition an unclaimed source gap for the S104 pilot.

    Scaffolding is limited to mechanically recognizable layout and page
    furniture. Rule-bearing requires an explicit condition, operation,
    routing instruction, threshold, or table rule. Everything else remains
    undecided so the measurement does not turn a growing cue list into a
    hidden extraction policy.
    """
    is_layout, layout_reason = _layout_only(value)
    if is_layout:
        return "scaffolding", layout_reason

    if ROUTING_RE.search(value):
        return "rule_bearing", "routing_instruction"
    if RULE_CONDITION_RE.search(value):
        return "rule_bearing", "condition_or_filer_instruction"
    if RULE_OPERATION_RE.search(value) and (
        LINE_RE.search(value) or THRESHOLD_RE.search(value)
    ):
        return "rule_bearing", "operation_instruction"
    if THRESHOLD_RE.search(value) and (
        LINE_RE.search(value) or re.search(r"\b(?:then|column|filing\s+status)\b", value, re.I)
    ):
        return "rule_bearing", "threshold"
    if kind == "table_or_header" and (
        LINE_RE.search(value) or re.search(r"\b(?:column|then|enter)\b", value, re.I)
    ):
        return "rule_bearing", "rule_table_header"
    if kind == "note" and re.search(r"\b(?:note|caution)\b", value, re.I):
        return "rule_bearing", "note_or_caution"
    return "undecided", "no_structural_rule_evidence"


def _corpus_entries(manifest: AcquisitionManifest) -> tuple[ManifestEntry, ...]:
    """Return the manifest-defined form/region corpus with no exclusion list."""
    return tuple(
        entry
        for entry in manifest.documents
        if entry.is_region or entry.kind in FACE_KINDS
    )


def _region_windows(
    *,
    source: str,
    parent_id: str,
    regions: Iterable[ManifestEntry],
) -> dict[str, SourceWindow]:
    """Locate all region windows in one acquired instruction source."""
    starts: dict[str, int] = {}
    for entry in regions:
        start = _heading_start(source, entry.region_title or entry.document_id)
        if start is not None:
            starts[entry.document_id] = start
    ordered = sorted(starts.items(), key=lambda item: item[1])
    result: dict[str, SourceWindow] = {}
    for index, (document_id, start) in enumerate(ordered):
        end = ordered[index + 1][1] if index + 1 < len(ordered) else len(source)
        result[document_id] = SourceWindow(parent_id, start, end, document_id)
    return result


def _window_for(
    entry: ManifestEntry,
    *,
    source: str,
    region_windows: Mapping[str, SourceWindow],
) -> SourceWindow:
    """Return a physical-document or worksheet source window."""
    if entry.is_region:
        window = region_windows.get(entry.document_id)
        if window is not None:
            return window
        return SourceWindow(
            entry.region_of or entry.document_id,
            0,
            len(source),
            entry.document_id,
        )
    return SourceWindow(entry.document_id, 0, len(source), entry.document_id)


def _row_record(
    row: CellRecord,
    *,
    source: str,
    source_tokens: tuple[SourceToken, ...],
    positions: Mapping[str, tuple[int, ...]],
    window: SourceWindow,
    cursor: int,
) -> tuple[dict[str, Any], tuple[dict[str, int], ...], int]:
    """Measure one row and return its record, claims, and next source cursor."""
    face = _face_text(row)
    face_tokens = tuple(token.value for token in _tokens(face))
    base: dict[str, Any] = {
        "line": row.line,
        "source_document_id": window.source_document_id,
        "source_window": {"start": window.start, "end": window.end},
        "face_fingerprint": _fingerprint(face),
        "face_token_count": len(face_tokens),
    }
    if not face_tokens:
        base.update(
            {
                "status": "unreconstructable",
                "reason": "empty_or_nonlexical_face",
                "ranges": [],
            }
        )
        return base, (), cursor

    alignment = _align(
        source_tokens,
        positions,
        face_tokens,
        start=max(cursor, window.start),
        end=window.end,
    )
    if alignment is None:
        base.update(
            {
                "status": "unreconstructable",
                "reason": "face_not_reconstructible_in_source_order",
                "ranges": [],
            }
        )
        return base, (), cursor

    ranges = _ranges_for_alignment(source, source_tokens, alignment)
    base.update(
        {
            "status": "multi_range" if len(ranges) > 1 else "single_range",
            "ranges": list(ranges),
        }
    )
    return base, ranges, source_tokens[alignment.token_indexes[-1]].end


def _add_unclaimed_runs(
    claims: list[tuple[str, SourceWindow, dict[str, int], str]],
    source_texts: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Report meaningful source runs between claims owned by different rows."""
    grouped: dict[tuple[str, int, int], list[tuple[dict[str, int], str]]] = defaultdict(list)
    for source_id, window, claimed, owner in claims:
        grouped[(source_id, window.start, window.end)].append((claimed, owner))

    unclaimed: list[dict[str, Any]] = []
    for (source_id, window_start, window_end), items in grouped.items():
        source = source_texts[source_id]
        ordered = sorted(items, key=lambda item: (item[0]["start"], item[0]["end"]))
        for (previous, previous_owner), (current, current_owner) in zip(ordered, ordered[1:]):
            if previous_owner == current_owner:
                continue
            start = previous["end"]
            end = current["start"]
            if start >= end:
                continue
            gap = source[start:end]
            if not _meaningful_gap(gap):
                continue
            partition, partition_reason = partition_unclaimed_text(
                gap, kind=_gap_kind(gap)
            )
            unclaimed.append(
                {
                    "source_document_id": source_id,
                    "document_id": previous_owner.split(":", 1)[0],
                    "source_window": {"start": window_start, "end": window_end},
                    "start": start,
                    "end": end,
                    "kind": _gap_kind(gap),
                    "partition": partition,
                    "partition_reason": partition_reason,
                    "governs": _governs(gap),
                    "text_fingerprint": _fingerprint(gap),
                    "preview": _ascii_preview(gap),
                    "between": [previous_owner, current_owner],
                }
            )
    return unclaimed


def measure_source_extents(*, root: str | Path, year: str | int = "2025") -> dict[str, Any]:
    """Measure all manifest-defined rows and return a serializable report."""
    root_path = Path(root).resolve()
    year_text = str(year)
    manifest = load_manifest(root=root_path)
    entries = _corpus_entries(manifest)
    all_manifest_ids = [entry.document_id for entry in entries]
    region_entries = [entry for entry in entries if entry.is_region]
    regions_by_parent: dict[str, list[ManifestEntry]] = defaultdict(list)
    for entry in region_entries:
        regions_by_parent[entry.region_of or ""].append(entry)

    source_texts: dict[str, str] = {}
    region_windows_by_source: dict[str, dict[str, SourceWindow]] = {}
    for entry in entries:
        source_id = entry.region_of if entry.is_region else entry.document_id
        source_key = source_id or entry.document_id
        if source_key in source_texts:
            continue
        path = _source_path(root_path, year_text, source_key)
        source_texts[source_key] = path.read_text(encoding="utf-8")
        region_windows_by_source[source_key] = _region_windows(
            source=source_texts[source_key],
            parent_id=source_key,
            regions=regions_by_parent.get(source_key, ()),
        )

    records: list[dict[str, Any]] = []
    claims: list[tuple[str, SourceWindow, dict[str, int], str]] = []
    source_cursors: dict[str, int] = {}
    for entry in entries:
        source_key = entry.region_of if entry.is_region else entry.document_id
        source_id = source_key or entry.document_id
        source = source_texts[source_id]
        window = _window_for(
            entry,
            source=source,
            region_windows=region_windows_by_source[source_id],
        )
        source_tokens = _tokens(source)
        positions = _positions(source_tokens)
        document = load_document_input(entry.document_id, year=year_text, root=root_path)
        frame = build_cell_frame_from_document(document)
        cursor = window.start
        for row in frame.rows:
            record, ranges, cursor = _row_record(
                row,
                source=source,
                source_tokens=source_tokens,
                positions=positions,
                window=window,
                cursor=cursor,
            )
            record["document_id"] = entry.document_id
            records.append(record)
            for claimed in ranges:
                owner = f"{entry.document_id}:{row.line}"
                claims.append((source_id, window, claimed, owner))
        source_cursors[entry.document_id] = cursor

    overlaps: list[dict[str, Any]] = []
    claims_by_source: dict[str, list[tuple[dict[str, int], str]]] = defaultdict(list)
    for source_id, _window, claimed, owner in claims:
        claims_by_source[source_id].append((claimed, owner))
    for source_id, items in claims_by_source.items():
        ordered = sorted(items, key=lambda item: (item[0]["start"], item[0]["end"]))
        for previous, current in zip(ordered, ordered[1:]):
            if (
                previous[0]["end"] > current[0]["start"]
                and previous[1] != current[1]
            ):
                overlaps.append(
                    {
                        "source_document_id": source_id,
                        "start": current[0]["start"],
                        "end": min(previous[0]["end"], current[0]["end"]),
                        "owners": [previous[1], current[1]],
                    }
                )

    status_counts = {
        status: sum(record["status"] == status for record in records)
        for status in ("single_range", "multi_range", "unreconstructable")
    }
    row_document_ids = sorted({str(record["document_id"]) for record in records})
    unclaimed = _add_unclaimed_runs(claims, source_texts)
    partition_counts = {
        partition: sum(item["partition"] == partition for item in unclaimed)
        for partition in ("scaffolding", "rule_bearing", "undecided")
    }
    rule_bearing_chars_by_document = {document_id: 0 for document_id in row_document_ids}
    for item in unclaimed:
        if item["partition"] == "rule_bearing":
            rule_bearing_chars_by_document[item["document_id"]] += item["end"] - item["start"]
    return {
        "schema_version": 2,
        "year": year_text,
        "documents": row_document_ids,
        "manifest_documents": sorted(all_manifest_ids),
        "excluded_documents": [],
        "counts": {
            "documents": len(row_document_ids),
            "manifest_documents": len(all_manifest_ids),
            "rows": len(records),
            "classification": status_counts,
            "overlaps": len(overlaps),
            "unclaimed_runs": len(unclaimed),
            "unclaimed_partitions": partition_counts,
            "unclaimed_rule_bearing_characters": sum(rule_bearing_chars_by_document.values()),
        },
        "rows": records,
        "overlaps": overlaps,
        "unclaimed_runs": unclaimed,
        "unclaimed_rule_bearing_characters_by_document": rule_bearing_chars_by_document,
        "source_cursors": source_cursors,
    }


def main() -> int:
    """Run the pilot and write a YAML measurement report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--year", default="2025")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = measure_source_extents(root=args.root, year=args.year)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        yaml.safe_dump(report, sort_keys=False, allow_unicode=False),
        encoding="ascii",
    )
    print(
        "source extents: "
        f"{report['counts']['rows']} rows, "
        f"{report['counts']['classification']}, "
        f"{report['counts']['unclaimed_runs']} unclaimed runs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
