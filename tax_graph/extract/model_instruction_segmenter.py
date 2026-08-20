"""Build a model-owned, cell-naive segmentation of instruction booklets.

The model sees acquired instruction text only. It returns section boundaries
and ownership claims; the verifier binds every boundary to acquired bytes
before the extraction pipeline joins sections to form cells.

The model frame remains cell-naive. A topic section such as ``Part I. Interest``
can govern a group of lines without printing a line number in its own heading.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tax_graph.acquire.manifest import load_manifest  # noqa: E402
from tax_graph.acquire.html_source import HtmlSourceIndex  # noqa: E402
from tax_graph.config import (  # noqa: E402
    get_config_value,
    load_config,
    resolve_llm_model,
    resolve_llm_seed,
)
from tax_graph.extract.instruction_sections import (  # noqa: E402
    _context_for_heading,
    _default_document_id,
    _parse_headings,
    build_instruction_sections_file,
)


PROMPT_PATH = ROOT / "prompts" / "instruction_segmenter.md"
_LINE_TOKEN_RE = re.compile(r"^[0-9]+[a-z]?$", re.IGNORECASE)
_SLUG_RE = re.compile(r"[^a-z0-9]+", re.IGNORECASE)


class SegmenterError(ValueError):
    """Raised when a model response cannot be made into a source-backed frame."""


class ModelFrameVerificationError(SegmenterError):
    """Raised when a section fails the byte or heading witness."""


class _HeadingOffsetResolutionError(ModelFrameVerificationError):
    """Raised when a claimed heading cannot be uniquely rebound to source."""

    def __init__(
        self,
        *,
        start_byte: int,
        heading: str,
        reason: str,
        candidates: Sequence[int] = (),
    ) -> None:
        self.start_byte = start_byte
        self.heading = heading
        self.reason = reason
        self.candidates = tuple(candidates)
        super().__init__(
            f"{reason} for {heading!r} at byte {start_byte}"
            + (f": candidates={self.candidates!r}" if self.candidates else "")
        )


@dataclass(frozen=True)
class SourceChapter:
    """One deterministic form-context chapter in an acquired booklet."""

    index: int
    document_id: str
    start_byte: int
    end_byte: int

    def as_dict(self) -> dict[str, int | str]:
        """Return the raw-byte chapter coordinates used by a recording."""
        return {
            "index": self.index,
            "document_id": self.document_id,
            "start_byte": self.start_byte,
            "end_byte": self.end_byte,
        }


@dataclass(frozen=True)
class SourceWindow:
    """One UTF-8-safe source window with absolute byte coordinates."""

    index: int
    start_byte: int
    end_byte: int
    chapter_index: int | None = None
    chapter_document_id: str | None = None

    def as_dict(self) -> dict[str, int | str]:
        """Return the window coordinates used by a recorded response."""
        result: dict[str, int | str] = {
            "index": self.index,
            "start_byte": self.start_byte,
            "end_byte": self.end_byte,
        }
        if self.chapter_index is not None:
            result["chapter_index"] = self.chapter_index
        if self.chapter_document_id is not None:
            result["chapter_document_id"] = self.chapter_document_id
        return result


@dataclass(frozen=True)
class ModelSection:
    """A source-backed section proposed by the model."""

    section_id: str
    source_document_id: str
    document_id: str
    heading: str
    level: int
    governs: tuple[str, ...]
    start_byte: int
    end_byte: int

    def as_dict(self, source_bytes: bytes | None = None) -> dict[str, Any]:
        """Return the stable pilot frame shape without copying source prose."""
        record: dict[str, Any] = {
            "section_id": self.section_id,
            "source_document_id": self.source_document_id,
            "document_id": self.document_id,
            "heading": self.heading,
            "level": self.level,
            "governs": list(self.governs),
            "start_byte": self.start_byte,
            "end_byte": self.end_byte,
        }
        if source_bytes is not None:
            record["text_fingerprint"] = _fingerprint(
                source_bytes[self.start_byte : self.end_byte]
            )
        return record


@dataclass(frozen=True)
class ModelInstructionFrame:
    """The pilot's source-backed segmentation frame."""

    schema_version: int
    year: str
    source_document_id: str
    source_path: str | None
    sections: tuple[ModelSection, ...]
    coverage: dict[str, Any]

    def as_dict(self, source_bytes: bytes | None = None) -> dict[str, Any]:
        """Return a JSON/YAML-safe frame without acquired source text."""
        return {
            "schema_version": self.schema_version,
            "year": self.year,
            "source_document_id": self.source_document_id,
            "source_path": self.source_path,
            "sections": [section.as_dict(source_bytes) for section in self.sections],
            "coverage": dict(self.coverage),
        }


def _normalize_document_ids(
    document_ids: Iterable[str] | None,
) -> tuple[str, ...] | None:
    """Return a stable, non-empty manifest vocabulary when one is supplied."""
    if document_ids is None:
        return None
    normalized = tuple(
        sorted({str(value).strip() for value in document_ids if str(value).strip()})
    )
    if not normalized:
        raise ValueError("allowed document ids must contain at least one non-empty id")
    return normalized


def segmenter_schema(
    *,
    allowed_document_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Return the closed structured-output schema for one model window."""
    allowed_ids = _normalize_document_ids(allowed_document_ids)
    document_schema: dict[str, Any] = {"type": "string"}
    if allowed_ids is not None:
        document_schema["enum"] = list(allowed_ids)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["sections"],
        "properties": {
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "heading",
                        "level",
                        "start_byte",
                        "end_byte",
                        "document_id",
                        "governs",
                    ],
                    "properties": {
                        "heading": {"type": "string"},
                        "level": {"type": "integer", "minimum": 1},
                        "start_byte": {"type": "integer", "minimum": 0},
                        "end_byte": {"type": "integer", "minimum": 1},
                        "document_id": document_schema,
                        "governs": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            }
        },
    }


def _fingerprint(value: bytes) -> str:
    """Return a source fingerprint without persisting source prose."""
    return hashlib.sha256(value).hexdigest()


def _slug(value: str) -> str:
    """Create an ASCII-only stable fragment for generated section ids."""
    result = _SLUG_RE.sub("_", value.lower()).strip("_")
    return result or "source"


def _utf8_boundaries(source_bytes: bytes) -> tuple[int, ...]:
    """Return every byte offset that is a valid UTF-8 character boundary."""
    boundaries = [0]
    offset = 0
    for character in source_bytes.decode("utf-8"):
        offset += len(character.encode("utf-8"))
        boundaries.append(offset)
    return tuple(boundaries)


def _boundary_at_or_before(boundaries: tuple[int, ...], value: int) -> int:
    """Return the greatest valid UTF-8 boundary not past ``value``."""
    low = 0
    high = len(boundaries) - 1
    while low < high:
        middle = (low + high + 1) // 2
        if boundaries[middle] <= value:
            low = middle
        else:
            high = middle - 1
    return boundaries[low]


def _collapse_newlines(text: str) -> str:
    """Apply the same universal-newline normalization as the parser input."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _collapsed_char_to_raw_byte_offsets(raw_text: str) -> tuple[int, ...]:
    """Map normalized character offsets back to raw UTF-8 byte offsets."""
    offsets = [0]
    raw_index = 0
    raw_byte = 0
    while raw_index < len(raw_text):
        character = raw_text[raw_index]
        if character == "\r":
            if raw_index + 1 < len(raw_text) and raw_text[raw_index + 1] == "\n":
                raw_index += 2
                raw_byte += len("\r\n".encode("utf-8"))
            else:
                raw_index += 1
                raw_byte += len(character.encode("utf-8"))
            offsets.append(raw_byte)
            continue
        raw_index += 1
        raw_byte += len(character.encode("utf-8"))
        offsets.append(raw_byte)
    return tuple(offsets)


def build_source_chapters(
    source_bytes: bytes,
    *,
    source_document_id: str,
    year: str | int = "2025",
) -> tuple[SourceChapter, ...]:
    """Build raw-byte chapters from the deterministic form-context tracker.

    The production tracker parses universal-newline text and reports character
    offsets.  This pilot converts each context transition back into the raw
    UTF-8 byte space before any model window is created.
    """
    year_text = str(year)
    raw_text = source_bytes.decode("utf-8")
    normalized_text = _collapse_newlines(raw_text)
    normalized_to_raw = _collapsed_char_to_raw_byte_offsets(raw_text)
    default_document_id = _default_document_id(source_document_id, year_text)
    current_document_id = default_document_id
    transitions: list[tuple[int, str]] = [(0, current_document_id)]
    for heading in _parse_headings(normalized_text):
        context = _context_for_heading(
            heading.title,
            current_document_id=current_document_id,
            default_document_id=default_document_id,
            year=year_text,
        )
        if context is None or context[0] == current_document_id:
            continue
        raw_start_byte = normalized_to_raw[heading.start_offset]
        transitions.append((raw_start_byte, context[0]))
        current_document_id = context[0]

    chapters: list[SourceChapter] = []
    for index, (start_byte, document_id) in enumerate(transitions, start=1):
        end_byte = (
            transitions[index][0]
            if index < len(transitions)
            else len(source_bytes)
        )
        chapters.append(
            SourceChapter(
                index=index,
                document_id=document_id,
                start_byte=start_byte,
                end_byte=end_byte,
            )
        )
    return tuple(chapters)


def _validate_source_chapters(
    source_bytes: bytes,
    chapters: Sequence[SourceChapter],
) -> None:
    """Fail closed if chapter coordinates do not tile the raw source."""
    if not chapters:
        raise ValueError("source chapters must not be empty")
    expected_start = 0
    for chapter in chapters:
        if chapter.start_byte != expected_start:
            raise ValueError(
                "source chapters must tile from byte 0: "
                f"expected {expected_start}, got {chapter.start_byte}"
            )
        if not chapter.document_id.strip():
            raise ValueError("source chapter document_id must be non-empty")
        if not 0 <= chapter.start_byte <= chapter.end_byte <= len(source_bytes):
            raise ValueError(
                "source chapter range is outside source: "
                f"{chapter.start_byte}:{chapter.end_byte}"
            )
        if chapter.start_byte == chapter.end_byte and len(source_bytes) > 0:
            raise ValueError("non-empty source chapters must have positive length")
        expected_start = chapter.end_byte
    if expected_start != len(source_bytes):
        raise ValueError(
            "source chapters must tile to EOF: "
            f"claimed {expected_start}, source has {len(source_bytes)} bytes"
        )


def _build_source_windows_for_range(
    source_bytes: bytes,
    *,
    start_byte: int,
    end_byte: int,
    max_window_bytes: int,
    overlap_bytes: int,
) -> tuple[tuple[int, int], ...]:
    """Split one bounded raw-byte range without crossing its endpoints."""
    if start_byte == end_byte:
        return ((start_byte, end_byte),)
    boundaries = _utf8_boundaries(source_bytes)
    ranges: list[tuple[int, int]] = []
    start = start_byte
    while start < end_byte:
        candidate_end = min(end_byte, start + max_window_bytes)
        end = _boundary_at_or_before(boundaries, candidate_end)
        if end <= start:
            raise ValueError(
                "max_window_bytes falls inside an unrepresentable source character"
            )
        ranges.append((start, end))
        if end == end_byte:
            break
        next_start = max(
            start_byte,
            _boundary_at_or_before(boundaries, end - overlap_bytes),
        )
        if next_start <= start:
            raise ValueError("window overlap prevents progress")
        start = next_start
    return tuple(ranges)


def build_source_windows(
    source_bytes: bytes,
    *,
    max_window_bytes: int = 12000,
    overlap_bytes: int = 2000,
    chapters: Iterable[SourceChapter] | None = None,
) -> tuple[SourceWindow, ...]:
    """Split source into overlapping UTF-8-safe windows.

    Windows use absolute source byte coordinates.  The overlap is not a
    quality hint: it is the mechanical opportunity for two adjacent calls to
    see a heading and its following boundary together.
    """
    if max_window_bytes <= 0:
        raise ValueError("max_window_bytes must be positive")
    if overlap_bytes < 0 or overlap_bytes >= max_window_bytes:
        raise ValueError("overlap_bytes must be non-negative and smaller than the window")
    chapter_values = tuple(chapters) if chapters is not None else ()
    if chapters is not None:
        _validate_source_chapters(source_bytes, chapter_values)
        windows: list[SourceWindow] = []
        for chapter in chapter_values:
            for start_byte, end_byte in _build_source_windows_for_range(
                source_bytes,
                start_byte=chapter.start_byte,
                end_byte=chapter.end_byte,
                max_window_bytes=max_window_bytes,
                overlap_bytes=overlap_bytes,
            ):
                windows.append(
                    SourceWindow(
                        index=len(windows),
                        start_byte=start_byte,
                        end_byte=end_byte,
                        chapter_index=chapter.index,
                        chapter_document_id=chapter.document_id,
                    )
                )
        return tuple(windows)

    if not source_bytes:
        return (SourceWindow(index=0, start_byte=0, end_byte=0),)
    ranges = _build_source_windows_for_range(
        source_bytes,
        start_byte=0,
        end_byte=len(source_bytes),
        max_window_bytes=max_window_bytes,
        overlap_bytes=overlap_bytes,
    )
    return tuple(
        SourceWindow(index=index, start_byte=start, end_byte=end)
        for index, (start, end) in enumerate(ranges)
    )


def build_window_prompt(
    source_bytes: bytes,
    window: SourceWindow,
    *,
    source_document_id: str,
    allowed_document_ids: Iterable[str] | None = None,
    prompt_text: str | None = None,
) -> str:
    """Build a source-only prompt for one absolute-coordinate window.

    The allowed ids identify document owners in this booklet.  They are
    manifest identity, not form-cell context, so including them does not make
    the segmenter cell-aware.
    """
    instructions = prompt_text if prompt_text is not None else PROMPT_PATH.read_text(
        encoding="ascii"
    )
    source_text = _annotated_window_text(source_bytes, window)
    owner_ids = _normalize_document_ids(allowed_document_ids)
    owner_contract = ""
    if owner_ids is not None:
        owner_contract = (
            "Allowed document_id values for every section: "
            f"{', '.join(owner_ids)}\n"
            "The source booklet id is a source marker, never an owner, and must not "
            "be returned as document_id.\n"
        )
    chapter_contract = ""
    if window.chapter_document_id is not None:
        chapter_contract = (
            "This window is inside the chapter for form document_id "
            f"{window.chapter_document_id}. Do not claim another form as the "
            "owner; worksheet owners in the allowed vocabulary may still appear.\n"
        )
    return (
        f"{instructions.rstrip()}\n\n"
        f"Source booklet id: {source_document_id}\n"
        f"{owner_contract}"
        f"{chapter_contract}"
        f"Window index: {window.index}\n"
        f"Window byte range: {window.start_byte}..{window.end_byte}\n"
        "The lines below are acquired source; coordinate markers are not source text.\n"
        "BEGIN ACQUIRED SOURCE\n"
        f"{source_text}"
        "\nEND ACQUIRED SOURCE\n"
    )


def _annotated_window_text(source_bytes: bytes, window: SourceWindow) -> str:
    """Prefix each source line with its absolute byte start for model binding."""
    raw_window = source_bytes[window.start_byte : window.end_byte]
    pieces: list[str] = []
    offset = window.start_byte
    for raw_line in raw_window.splitlines(keepends=True):
        pieces.append(f"[[source_byte={offset}]]")
        pieces.append(raw_line.decode("utf-8"))
        offset += len(raw_line)
    if not pieces and raw_window:
        pieces.append(f"[[source_byte={window.start_byte}]]")
        pieces.append(raw_window.decode("utf-8"))
    return "".join(pieces)


def call_model_window(
    prompt: str,
    config: Mapping[str, Any],
    *,
    allowed_document_ids: Iterable[str] | None = None,
    max_tokens: int = 12000,
) -> Mapping[str, Any]:
    """Call the configured structured-output client for one pilot window."""
    from tax_graph.extract.llm_client import build_llm_client

    request: dict[str, Any] = {
        "prompt": prompt,
        "schema": segmenter_schema(allowed_document_ids=allowed_document_ids),
        "model": resolve_llm_model(config, "micro"),
        "max_tokens": max_tokens,
        "temperature": get_config_value(dict(config), "llm.temperature"),
        "purpose": "tax_graph_instruction_segmentation",
    }
    seed = resolve_llm_seed(config)
    if seed is not None:
        request["seed"] = seed
    client = build_llm_client(dict(config))
    return client.structured_completion(**request)


def _source_line_at(source_bytes: bytes, start_byte: int) -> str:
    """Return the exact UTF-8 source line beginning at a section boundary."""
    if start_byte < 0 or start_byte > len(source_bytes):
        raise ModelFrameVerificationError(f"section starts outside source: {start_byte}")
    line_end = source_bytes.find(b"\n", start_byte)
    if line_end < 0:
        line_end = len(source_bytes)
    return source_bytes[start_byte:line_end].decode("utf-8").rstrip("\r")


def _source_line_starts(source_bytes: bytes) -> tuple[int, ...]:
    """Return byte offsets that begin non-empty UTF-8 source lines."""
    starts = [0] if source_bytes else []
    search_from = 0
    while True:
        newline = source_bytes.find(b"\n", search_from)
        if newline < 0:
            break
        next_start = newline + 1
        if next_start < len(source_bytes):
            starts.append(next_start)
        search_from = next_start
    return tuple(starts)


def _normalize_heading_markup(value: str) -> str:
    """Remove leading Markdown presentation without changing heading text."""
    normalized = value.strip()
    normalized = re.sub(r"^#{1,6}[ \t]*", "", normalized)
    normalized = re.sub(r"^(?:\*{1,3}|_{1,3})[ \t]*", "", normalized)
    normalized = re.sub(r"(?:\*{1,3}|_{1,3})(?=[ \t]|$)", "", normalized)
    return " ".join(normalized.split())


def _heading_is_source_prefix(response_heading: str, source_line: str) -> bool:
    """Return whether a response heading starts the source line after markup."""
    response = _normalize_heading_markup(response_heading)
    source = _normalize_heading_markup(source_line)
    return bool(response) and source.startswith(response)


def _resolve_heading_offset(
    source_bytes: bytes,
    *,
    claimed_start_byte: int,
    heading: str,
) -> tuple[int, bool]:
    """Resolve a model heading to one nearby source line boundary.

    The search is intentionally lexical and bounded.  It accepts only a unique
    source line whose normalized text starts with the model heading; it never
    searches for a fuzzy or fabricated heading elsewhere in the booklet.
    """
    lower_bound = max(0, claimed_start_byte - 256)
    upper_bound = min(len(source_bytes) - 1, claimed_start_byte + 256)
    candidates = tuple(
        start_byte
        for start_byte in _source_line_starts(source_bytes)
        if lower_bound <= start_byte <= upper_bound
        and _heading_is_source_prefix(heading, _source_line_at(source_bytes, start_byte))
    )
    if len(candidates) == 1:
        return candidates[0], candidates[0] != claimed_start_byte
    if not candidates:
        raise _HeadingOffsetResolutionError(
            start_byte=claimed_start_byte,
            heading=heading,
            reason="heading_not_at_source_offset",
        )
    raise _HeadingOffsetResolutionError(
        start_byte=claimed_start_byte,
        heading=heading,
        reason="ambiguous_heading_source_offset",
        candidates=candidates,
    )


def manifest_owner_document_ids(
    root: str | Path,
    *,
    source_document_id: str,
) -> frozenset[str]:
    """Return manifest document ids that can own sections in one booklet."""
    manifest = load_manifest(root=Path(root).resolve())
    return frozenset(
        entry.document_id
        for entry in manifest.documents
        if entry.document_id != source_document_id
        and (
            entry.instructions_document_id == source_document_id
            or entry.region_of == source_document_id
        )
    )


def manifest_worksheet_document_ids(
    root: str | Path,
    *,
    source_document_id: str,
) -> frozenset[str]:
    """Return worksheet owners in one booklet's manifest vocabulary."""
    manifest = load_manifest(root=Path(root).resolve())
    return frozenset(
        entry.document_id
        for entry in manifest.documents
        if entry.kind == "worksheet"
        and (
            entry.instructions_document_id == source_document_id
            or entry.region_of == source_document_id
        )
    )


def _coerce_governs(value: Any) -> tuple[str, ...]:
    """Normalize one model ``governs`` list while preserving semantic labels."""
    if not isinstance(value, list):
        raise SegmenterError("section governs must be a list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise SegmenterError("section governs entries must be non-empty strings")
        normalized = item.strip()
        if normalized not in result:
            result.append(normalized)
    return tuple(result)


def _raw_section(
    raw: Mapping[str, Any] | Sequence[Any],
    *,
    source_document_id: str,
    window: SourceWindow,
    source_bytes: bytes,
    allowed_document_ids: frozenset[str] | None,
    chapter_document_id: str | None = None,
    worksheet_document_ids: frozenset[str] = frozenset(),
) -> tuple[ModelSection | None, bool, dict[str, Any] | None]:
    """Validate one response section without making the booklet fatal."""
    def reject(reason: str, detail: str | None = None) -> tuple[None, bool, dict[str, Any]]:
        record: dict[str, Any] = {"reason": reason}
        if isinstance(raw, Mapping):
            for key in ("start_byte", "heading", "document_id"):
                if key in raw:
                    record[key] = raw[key]
        if detail:
            record["detail"] = detail
        return None, False, record

    if isinstance(raw, (list, tuple)):
        if len(raw) != 6:
            return reject(
                "invalid_section_shape",
                "compact section response must have heading, level, start, end, "
                "document_id, and governs",
            )
        raw = dict(
            zip(
                ("heading", "level", "start_byte", "end_byte", "document_id", "governs"),
                raw,
            )
        )
    if not isinstance(raw, Mapping):
        return reject("invalid_section_shape", "section must be an object or compact row")
    required = {
        "heading",
        "level",
        "start_byte",
        "end_byte",
        "document_id",
        "governs",
    }
    missing = sorted(required - set(raw))
    if missing:
        return reject("missing_fields", ", ".join(missing))
    heading = raw["heading"]
    document_id = raw["document_id"]
    if not isinstance(heading, str) or not heading:
        return reject("invalid_heading", "section heading must be a non-empty string")
    if not isinstance(document_id, str) or not document_id.strip():
        return reject("invalid_document_id", "section document_id must be a non-empty string")
    try:
        level = int(raw["level"])
        start_byte = int(raw["start_byte"])
        end_byte = int(raw["end_byte"])
    except (TypeError, ValueError):
        return reject("invalid_numeric_fields", "level and byte ranges must be integers")
    if level < 1:
        return reject("invalid_level", "section level must be positive")
    if not window.start_byte <= start_byte < window.end_byte:
        return reject(
            "start_outside_window",
            f"section start {start_byte} is outside window "
            f"{window.start_byte}:{window.end_byte}",
        )
    if start_byte >= len(source_bytes):
        return reject("start_outside_source", f"section start {start_byte} is outside source")
    try:
        resolved_start_byte, offset_repaired = _resolve_heading_offset(
            source_bytes,
            claimed_start_byte=start_byte,
            heading=heading,
        )
    except _HeadingOffsetResolutionError as exc:
        record: dict[str, Any] = {
            "start_byte": exc.start_byte,
            "heading": exc.heading,
            "reason": exc.reason,
        }
        if exc.candidates:
            record["candidates"] = list(exc.candidates)
        return None, False, record
    if not window.start_byte <= resolved_start_byte < window.end_byte:
        return reject(
            "heading_outside_window",
            f"resolved heading start {resolved_start_byte} is outside window "
            f"{window.start_byte}:{window.end_byte}",
        )
    if "text" in raw:
        claimed_text = raw["text"]
        if not isinstance(claimed_text, str):
            return reject("invalid_text_witness", "text witness must be a string")
        if not resolved_start_byte <= end_byte <= len(source_bytes):
            return reject(
                "invalid_text_range",
                f"text witness range is invalid: {resolved_start_byte}:{end_byte}",
            )
        try:
            actual_text = source_bytes[resolved_start_byte:end_byte].decode("utf-8")
        except UnicodeDecodeError as exc:
            return reject("invalid_text_range", str(exc))
        if claimed_text != actual_text:
            return reject(
                "text_mismatch",
                f"text does not match claimed range {resolved_start_byte}:{end_byte}",
            )
    normalized_document_id = document_id.strip()
    if allowed_document_ids is not None and normalized_document_id not in allowed_document_ids:
        allowed = ", ".join(sorted(allowed_document_ids)) or "<none>"
        return reject(
            "disallowed_document_id",
            f"document_id {normalized_document_id!r} is not an allowed owner for "
            f"{source_document_id}; allowed: {allowed}",
        )
    if (
        chapter_document_id is not None
        and normalized_document_id != chapter_document_id
        and normalized_document_id not in worksheet_document_ids
    ):
        return reject(
            "chapter_owner_disagreement",
            f"document_id {normalized_document_id!r} is not the form owner "
            f"for chapter {chapter_document_id!r}; worksheet owners remain allowed",
        )
    try:
        governs = _coerce_governs(raw["governs"])
    except (SegmenterError, TypeError, ValueError) as exc:
        return reject("invalid_governs", str(exc))
    return (
        ModelSection(
            section_id="",
            source_document_id=source_document_id,
            document_id=normalized_document_id,
            heading=heading,
            level=level,
            governs=governs,
            start_byte=resolved_start_byte,
            end_byte=end_byte,
        ),
        offset_repaired,
        None,
    )


def verify_model_sections(
    source_bytes: bytes,
    sections: Sequence[ModelSection],
    *,
    source_document_id: str,
    allowed_document_ids: frozenset[str] | None = None,
) -> None:
    """Fail closed if model sections do not tile and bind to source bytes."""
    if not sections:
        raise ModelFrameVerificationError("model returned no sections")
    ordered = sorted(sections, key=lambda item: (item.start_byte, item.end_byte))
    expected_start = 0
    for section in ordered:
        if section.source_document_id != source_document_id:
            raise ModelFrameVerificationError(
                f"section has wrong source document: {section.source_document_id}"
            )
        if section.start_byte != expected_start:
            raise ModelFrameVerificationError(
                f"byte conservation failed before {section.heading!r}: "
                f"expected {expected_start}, got {section.start_byte}"
            )
        if not 0 <= section.start_byte < section.end_byte <= len(source_bytes):
            raise ModelFrameVerificationError(
                f"section range is outside source: {section.start_byte}:{section.end_byte}"
            )
        actual_heading = _source_line_at(source_bytes, section.start_byte)
        if not _heading_is_source_prefix(section.heading, actual_heading):
            raise ModelFrameVerificationError(
                f"heading mismatch at byte {section.start_byte}: "
                f"response={section.heading!r}, source={actual_heading!r}"
            )
        if section.level < 1:
            raise ModelFrameVerificationError("section heading level must be positive")
        if not section.document_id.strip():
            raise ModelFrameVerificationError("section document_id must be non-empty")
        if allowed_document_ids is not None and section.document_id not in allowed_document_ids:
            allowed = ", ".join(sorted(allowed_document_ids)) or "<none>"
            raise ModelFrameVerificationError(
                f"document_id {section.document_id!r} is not an allowed owner for "
                f"{source_document_id}; allowed: {allowed}"
            )
        expected_start = section.end_byte
    if expected_start != len(source_bytes):
        raise ModelFrameVerificationError(
            f"byte conservation failed at EOF: claimed {expected_start}, "
            f"source has {len(source_bytes)} bytes"
        )


def _governs_claim(
    section: ModelSection,
    window: SourceWindow,
) -> dict[str, Any]:
    """Serialize one competing window observation without copying source text."""
    following_context_bytes = window.end_byte - section.start_byte
    abuts_window_edge = (
        section.start_byte == window.start_byte
        or section.end_byte == window.end_byte
    )
    return {
        "window_index": window.index,
        "window_start_byte": window.start_byte,
        "window_end_byte": window.end_byte,
        "document_id": section.document_id,
        "governs": list(section.governs),
        "section_end_byte": section.end_byte,
        "following_context_bytes": following_context_bytes,
        "abuts_window_edge": abuts_window_edge,
    }


def _reconcile_window_sections(
    parsed: Sequence[tuple[ModelSection, SourceWindow]],
    *,
    allowed_document_ids: frozenset[str] | None,
) -> tuple[
    dict[int, ModelSection],
    int,
    int,
    list[dict[str, Any]],
]:
    """Reconcile duplicate observations and retain only source-backed claims.

    A source start byte identifies one section, even when overlapping windows
    preserve different heading markup.  The longest source-backed normalized
    heading wins, with the lowest window index breaking ties.  Ownership
    conflicts are rejected section-locally.  A conflicting ``governs`` claim is
    resolved from window context instead: the observation with the most trailing
    context wins, while ties and all-edge observations are rejected as ambiguous.
    """
    grouped: dict[int, list[tuple[ModelSection, SourceWindow]]] = {}
    for section, window in parsed:
        grouped.setdefault(section.start_byte, []).append((section, window))

    unique: dict[int, ModelSection] = {}
    owner_conflict_count = 0
    governs_conflict_count = 0
    rejected_sections: list[dict[str, Any]] = []
    for start_byte, claims in grouped.items():
        first_section = claims[0][0]
        heading_claim = min(
            claims,
            key=lambda item: (
                -len(_normalize_heading_markup(item[0].heading)),
                item[1].index,
            ),
        )
        selected_heading = heading_claim[0].heading
        owner_conflicts = [
            section for section, _window in claims
            if section.document_id != first_section.document_id
        ]
        if owner_conflicts:
            owner_conflict_count += len(owner_conflicts)
            rejected_sections.append(
                {
                    "start_byte": start_byte,
                    "heading": selected_heading,
                    "reason": "overlapping_document_id_conflict",
                    "competing_claims": [
                        _governs_claim(section, window)
                        for section, window in claims
                    ],
                }
            )
            continue

        governs_values = {section.governs for section, _window in claims}
        if len(governs_values) <= 1:
            unique[start_byte] = replace(first_section, heading=selected_heading)
            continue

        governs_conflict_count += 1
        ordered_claims = sorted(
            claims,
            key=lambda item: (
                item[1].index,
                item[1].start_byte,
                item[1].end_byte,
                item[0].end_byte,
            ),
        )
        if all(
            section.start_byte == window.start_byte
            or section.end_byte == window.end_byte
            for section, window in ordered_claims
        ):
            ambiguity = "all_observations_abut_window_edge"
            winner: tuple[ModelSection, SourceWindow] | None = None
        else:
            context_lengths = [
                window.end_byte - section.start_byte
                for section, window in ordered_claims
            ]
            greatest_context = max(context_lengths)
            winners = [
                claim
                for claim, context_length in zip(ordered_claims, context_lengths)
                if context_length == greatest_context
            ]
            ambiguity = "equal_following_context"
            winner = winners[0] if len(winners) == 1 else None

        if winner is None:
            rejected_sections.append(
                {
                    "start_byte": first_section.start_byte,
                    "heading": selected_heading,
                    "reason": "ambiguous_governs_conflict",
                    "ambiguity": ambiguity,
                    "competing_claims": [
                        _governs_claim(section, window)
                        for section, window in ordered_claims
                    ],
                }
            )
            continue
        unique[start_byte] = replace(winner[0], heading=selected_heading)

    return (
        unique,
        owner_conflict_count,
        governs_conflict_count,
        rejected_sections,
    )


def _chapter_for_window(
    window: SourceWindow,
    chapters: Sequence[SourceChapter],
) -> SourceChapter:
    """Return the sole chapter containing a response window."""
    matches = [
        chapter
        for chapter in chapters
        if chapter.start_byte <= window.start_byte
        and window.end_byte <= chapter.end_byte
    ]
    if len(matches) != 1:
        raise SegmenterError(
            "response window must lie inside exactly one source chapter: "
            f"{window.start_byte}:{window.end_byte}"
        )
    chapter = matches[0]
    if window.chapter_index is not None and window.chapter_index != chapter.index:
        raise SegmenterError(
            "response window chapter index disagrees with deterministic chapter: "
            f"{window.chapter_index} != {chapter.index}"
        )
    if (
        window.chapter_document_id is not None
        and window.chapter_document_id != chapter.document_id
    ):
        raise SegmenterError(
            "response window chapter document disagrees with deterministic chapter: "
            f"{window.chapter_document_id!r} != {chapter.document_id!r}"
        )
    return chapter


def build_model_frame(
    source_text: str,
    *,
    source_document_id: str,
    responses: Iterable[Mapping[str, Any]],
    year: str | int = "2025",
    source_path: str | Path | None = None,
    allowed_document_ids: Iterable[str] | None = None,
    chapters: Iterable[SourceChapter] | None = None,
    worksheet_document_ids: Iterable[str] = (),
) -> ModelInstructionFrame:
    """Reconcile window responses into one verified source-backed model frame."""
    source_bytes = source_text.encode("utf-8")
    normalized_allowed_ids = _normalize_document_ids(allowed_document_ids)
    allowed_ids = (
        frozenset(normalized_allowed_ids)
        if normalized_allowed_ids is not None
        else None
    )
    chapter_values = tuple(chapters) if chapters is not None else ()
    if chapters is not None:
        _validate_source_chapters(source_bytes, chapter_values)
    worksheet_ids = frozenset(
        str(value).strip()
        for value in worksheet_document_ids
        if str(value).strip()
    )
    parsed: list[tuple[ModelSection, SourceWindow]] = []
    response_count = 0
    response_section_count = 0
    heading_offset_repaired_count = 0
    section_rejections: list[dict[str, Any]] = []
    for response_record in responses:
        response_count += 1
        try:
            record_chapter_index = response_record.get("chapter_index")
            window = SourceWindow(
                index=int(response_record["window_index"]),
                start_byte=int(response_record["window_start_byte"]),
                end_byte=int(response_record["window_end_byte"]),
                chapter_index=(
                    int(record_chapter_index)
                    if record_chapter_index is not None
                    else None
                ),
                chapter_document_id=(
                    str(response_record["chapter_document_id"])
                    if response_record.get("chapter_document_id") is not None
                    else None
                ),
            )
            raw_sections = response_record["response"]["sections"]
        except (KeyError, TypeError, ValueError) as exc:
            raise SegmenterError("invalid recorded window response envelope") from exc
        if not 0 <= window.start_byte <= window.end_byte <= len(source_bytes):
            raise SegmenterError(f"invalid response window: {window}")
        chapter = _chapter_for_window(window, chapter_values) if chapter_values else None
        if not isinstance(raw_sections, list):
            raise SegmenterError("recorded response sections must be a list")
        for raw in raw_sections:
            response_section_count += 1
            section, offset_repaired, rejection = _raw_section(
                raw,
                source_document_id=source_document_id,
                window=window,
                source_bytes=source_bytes,
                allowed_document_ids=allowed_ids,
                chapter_document_id=chapter.document_id if chapter is not None else None,
                worksheet_document_ids=worksheet_ids,
            )
            if rejection is not None:
                section_rejections.append(rejection)
                continue
            if section is None:  # pragma: no cover - rejection path above is exhaustive.
                raise SegmenterError("section parser returned neither section nor rejection")
            parsed.append((section, window))
            if offset_repaired:
                heading_offset_repaired_count += 1

    (
        unique,
        owner_conflict_count,
        governs_conflict_count,
        reconciliation_rejections,
    ) = _reconcile_window_sections(
        parsed,
        allowed_document_ids=allowed_ids,
    )
    observed_candidates = sorted(
        unique.values(), key=lambda item: (item.start_byte, item.end_byte)
    )
    observed = observed_candidates
    ordered = tuple(
        ModelSection(
            section_id=section.section_id,
            source_document_id=section.source_document_id,
            document_id=section.document_id,
            heading=section.heading,
            level=section.level,
            governs=section.governs,
            start_byte=section.start_byte,
            end_byte=(
                observed[index + 1].start_byte
                if index + 1 < len(observed)
                else len(source_bytes)
            ),
        )
        for index, section in enumerate(observed)
    )
    verified_sections = tuple(
        ModelSection(
            section_id=(
                f"model_instruction_section_{_slug(source_document_id)}_{index:04d}"
            ),
            source_document_id=source_document_id,
            document_id=section.document_id,
            heading=section.heading,
            level=section.level,
            governs=section.governs,
            start_byte=section.start_byte,
            end_byte=section.end_byte,
        )
        for index, section in enumerate(ordered, start=1)
    )
    verify_model_sections(
        source_bytes,
        verified_sections,
        source_document_id=source_document_id,
        allowed_document_ids=allowed_ids,
    )
    return ModelInstructionFrame(
        schema_version=1,
        year=str(year),
        source_document_id=source_document_id,
        source_path=str(source_path) if source_path is not None else None,
        sections=verified_sections,
        coverage={
            "file_size_bytes": len(source_bytes),
            "response_window_count": response_count,
            "response_section_count": response_section_count,
            "unique_section_count": len(verified_sections),
            "duplicate_response_sections": len(parsed) - len(verified_sections),
            "boundary_repaired_sections": sum(
                section.end_byte != verified_sections[index].end_byte
                for index, section in enumerate(observed)
            ),
            "heading_offset_repaired_count": heading_offset_repaired_count,
            "rejected_sections": [*section_rejections, *reconciliation_rejections],
            "chapter_count": len(chapter_values),
            "chapter_owner_disagreement_count": sum(
                item.get("reason") == "chapter_owner_disagreement"
                for item in section_rejections
            ),
            "owner_conflict_count": owner_conflict_count,
            "governs_conflict_count": governs_conflict_count,
            "reconciles_to_file_size": True,
        },
    )


def load_recorded_fixture(
    path: str | Path,
    *,
    source_document_id: str,
    source_bytes: bytes,
) -> tuple[dict[str, Any], ...]:
    """Load and hash-check one recorded response fixture."""
    fixture_path = Path(path)
    payload = json.loads(fixture_path.read_text(encoding="ascii"))
    if not isinstance(payload, Mapping) or payload.get("schema_version") != 1:
        raise SegmenterError(f"invalid instruction segmentation fixture: {fixture_path}")
    booklet = (payload.get("booklets") or {}).get(source_document_id)
    if not isinstance(booklet, Mapping):
        raise SegmenterError(f"fixture has no booklet {source_document_id}")
    expected_hash = str(booklet.get("source_sha256") or "")
    if expected_hash != _fingerprint(source_bytes):
        raise SegmenterError(
            f"fixture source hash mismatch for {source_document_id}: "
            f"expected {expected_hash}, got {_fingerprint(source_bytes)}"
        )
    records = booklet.get("responses")
    if not isinstance(records, list):
        raise SegmenterError(f"fixture responses are not a list for {source_document_id}")
    return tuple(dict(record) for record in records)


def build_frame_from_fixture(
    source_path: str | Path,
    *,
    source_document_id: str,
    fixture_path: str | Path,
    year: str | int = "2025",
    allowed_document_ids: Iterable[str] | None = None,
    root: str | Path = ROOT,
) -> ModelInstructionFrame:
    """Build a verified model frame from a recorded response fixture."""
    path = Path(source_path)
    source_bytes = path.read_bytes()
    source_text = source_bytes.decode("utf-8")
    responses = load_recorded_fixture(
        fixture_path,
        source_document_id=source_document_id,
        source_bytes=source_bytes,
    )
    chapters = build_source_chapters(
        source_bytes,
        source_document_id=source_document_id,
        year=year,
    )
    return build_model_frame(
        source_text,
        source_document_id=source_document_id,
        responses=responses,
        year=year,
        source_path=path,
        allowed_document_ids=allowed_document_ids,
        chapters=chapters,
        worksheet_document_ids=manifest_worksheet_document_ids(
            root,
            source_document_id=source_document_id,
        ),
    )


def build_frame_from_source(
    source_path: str | Path,
    *,
    source_document_id: str,
    config: Mapping[str, Any],
    root: str | Path = ROOT,
    client: Any | None = None,
    year: str | int = "2025",
    max_window_bytes: int = 12000,
    overlap_bytes: int = 2000,
) -> ModelInstructionFrame:
    """Call the configured model over one acquired booklet and verify its frame."""
    path = Path(source_path)
    source_bytes = path.read_bytes()
    html_index = None
    if path.suffix.lower() == ".html":
        html_index = HtmlSourceIndex(source_bytes.decode("utf-8"))
        model_text = html_index.segmentable_text
        model_bytes = model_text.encode("utf-8")
    else:
        model_text = source_bytes.decode("utf-8")
        model_bytes = source_bytes
    chapters = build_source_chapters(
        model_bytes,
        source_document_id=source_document_id,
        year=year,
    )
    owner_ids = manifest_owner_document_ids(
        root,
        source_document_id=source_document_id,
    )
    worksheet_ids = manifest_worksheet_document_ids(
        root,
        source_document_id=source_document_id,
    )
    windows = build_source_windows(
        model_bytes,
        max_window_bytes=max_window_bytes,
        overlap_bytes=overlap_bytes,
        chapters=chapters,
    )
    records: list[dict[str, Any]] = []
    for window in windows:
        allowed_ids = _allowed_document_ids_for_window(
            owner_ids,
            chapter_document_id=window.chapter_document_id,
            worksheet_document_ids=worksheet_ids,
        )
        prompt = build_window_prompt(
            model_bytes,
            window,
            source_document_id=source_document_id,
            allowed_document_ids=allowed_ids,
        )
        if client is None:
            response = call_model_window(
                prompt,
                config,
                allowed_document_ids=allowed_ids,
            )
        else:
            request = {
                "prompt": prompt,
                "schema": segmenter_schema(allowed_document_ids=allowed_ids),
                "model": resolve_llm_model(config, "micro"),
                "max_tokens": 12000,
                "temperature": get_config_value(dict(config), "llm.temperature"),
                "purpose": "tax_graph_instruction_segmentation",
            }
            seed = resolve_llm_seed(config)
            if seed is not None:
                request["seed"] = seed
            response = client.structured_completion(**request)
        records.append(
            {
                "chapter_document_id": window.chapter_document_id,
                "chapter_index": window.chapter_index,
                "window_index": window.index,
                "window_start_byte": window.start_byte,
                "window_end_byte": window.end_byte,
                "response": dict(response),
            }
        )
    frame = build_model_frame(
        model_text,
        source_document_id=source_document_id,
        responses=records,
        year=year,
        source_path=path,
        allowed_document_ids=owner_ids,
        chapters=chapters,
        worksheet_document_ids=worksheet_ids,
    )
    if html_index is None:
        return frame
    mapped_sections: list[ModelSection] = []
    for section in frame.sections:
        raw_range = html_index.raw_range_for_segment_bytes(
            section.start_byte,
            section.end_byte,
        )
        if raw_range is None:
            raise SegmenterError(
                "model section does not map to acquired HTML bytes: "
                f"{section.start_byte}:{section.end_byte}"
            )
        mapped_sections.append(
            replace(
                section,
                start_byte=raw_range["start"],
                end_byte=raw_range["end"],
            )
        )
    coverage = dict(frame.coverage)
    coverage["model_coordinate_space"] = "segmentable_utf8_bytes"
    coverage["source_coordinate_space"] = "raw_html_utf8_bytes"
    coverage["source_file_size_bytes"] = len(source_bytes)
    return replace(frame, sections=tuple(mapped_sections), coverage=coverage)


def _line_tokens(governs: Iterable[str]) -> tuple[str, ...]:
    """Return only printed-line tokens from a mixed semantic governs list."""
    return tuple(
        token.lower()
        for token in governs
        if _LINE_TOKEN_RE.fullmatch(str(token).strip())
    )


def _baseline_sections(source_path: Path, source_document_id: str) -> tuple[dict[str, Any], ...]:
    """Project the deterministic parser into the scorer's common shape."""
    frame = build_instruction_sections_file(
        source_path,
        source_document_id=source_document_id,
        year="2025",
    )
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for section in frame.sections:
        if section.section_id in seen:
            continue
        seen.add(section.section_id)
        result.append(
            {
                "document_id": section.document_id,
                "governs": tuple(section.line_tokens),
                "section_id": section.section_id,
            }
        )
    return tuple(result)


def score_ab(
    *,
    source_document_id: str,
    model_frame: ModelInstructionFrame,
    deterministic_sections: Iterable[Mapping[str, Any]],
    cells_by_document: Mapping[str, Iterable[Mapping[str, Any]]],
    worksheet_document_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Score correct and wrong ownership after both segmenters ran.

    The scorer accepts cell records only here, after ``build_model_frame`` has
    verified the model response.  A model prompt therefore cannot accidentally
    become a cell-conditioned prompt through this reporting path.
    """
    model_sections = tuple(
        {
            "document_id": section.document_id,
            "governs": _line_tokens(section.governs),
            "section_id": section.section_id,
        }
        for section in model_frame.sections
    )
    baseline = tuple(dict(section) for section in deterministic_sections)
    cells_by_document = {
        document_id: tuple(dict(cell) for cell in raw_cells)
        for document_id, raw_cells in cells_by_document.items()
    }
    worksheet_ids = {str(value) for value in worksheet_document_ids}
    documents: dict[str, Any] = {}
    for document_id, raw_cells in sorted(cells_by_document.items()):
        gained: list[str] = []
        wrong_form_owner: list[dict[str, Any]] = []
        sibling_worksheet_owner: list[dict[str, Any]] = []
        baseline_correct = 0
        model_correct = 0
        model_reachable = 0
        for cell in raw_cells:
            line = str(cell.get("line") or "").strip().lower()
            cell_id = str(cell.get("cell_id") or "")
            baseline_matches = [
                section
                for section in baseline
                if line in {str(value).lower() for value in section.get("governs", ())}
            ]
            model_matches = [
                section
                for section in model_sections
                if line in {str(value).lower() for value in section.get("governs", ())}
            ]
            baseline_has_correct = any(
                section.get("document_id") == document_id for section in baseline_matches
            )
            model_has_correct = any(
                section.get("document_id") == document_id for section in model_matches
            )
            if baseline_has_correct:
                baseline_correct += 1
            if model_has_correct:
                model_correct += 1
            if model_matches:
                model_reachable += 1
            if not baseline_has_correct and model_has_correct:
                gained.append(cell_id)
            for section in model_matches:
                owner = str(section.get("document_id") or "")
                if owner != document_id:
                    finding = {
                        "cell_id": cell_id,
                        "line": line,
                        "expected_document_id": document_id,
                        "actual_document_id": owner,
                        "section_id": section.get("section_id"),
                    }
                    if owner in worksheet_ids:
                        sibling_worksheet_owner.append(finding)
                    else:
                        wrong_form_owner.append(finding)
        documents[document_id] = {
            "cell_count": len(raw_cells),
            "baseline_correct": baseline_correct,
            "model_correct": model_correct,
            "model_reachable": model_reachable,
            "gained_correctly_owned": sorted(gained),
            "wrong_form_owner": wrong_form_owner,
            "wrong_form_owner_count": len(wrong_form_owner),
            "sibling_worksheet_owner": sibling_worksheet_owner,
            "sibling_worksheet_owner_count": len(sibling_worksheet_owner),
        }
    return {
        "schema_version": 1,
        "source_document_id": source_document_id,
        "documents": documents,
        "totals": {
            "cells": sum(item["cell_count"] for item in documents.values()),
            "gained_correctly_owned": sum(
                len(item["gained_correctly_owned"]) for item in documents.values()
            ),
            "wrong_form_owner": sum(
                item["wrong_form_owner_count"] for item in documents.values()
            ),
            "sibling_worksheet_owner": sum(
                item["sibling_worksheet_owner_count"] for item in documents.values()
            ),
        },
    }


def load_reconciliation_cells(
    root: str | Path,
    *,
    source_document_id: str,
    reconciliation_path: str | Path | None = None,
) -> dict[str, tuple[dict[str, Any], ...]]:
    """Load only the post-segmentation cell population for one booklet."""
    root_path = Path(root).resolve()
    path = (
        Path(reconciliation_path)
        if reconciliation_path is not None
        else root_path / "plans" / "m20_s116_instruction_reconciliation.yaml"
    )
    if not path.is_absolute():
        path = root_path / path
    report = yaml.safe_load(path.read_text(encoding="ascii")) or {}
    documents = report.get("documents") or {}
    result: dict[str, tuple[dict[str, Any], ...]] = {}
    owner_document_ids = manifest_owner_document_ids(
        root_path,
        source_document_id=source_document_id,
    )
    for document_id in sorted(owner_document_ids):
        document = documents.get(document_id) or {}
        result[document_id] = tuple(
            dict(cell) for cell in document.get("cells", ())
        )
    return result


def build_ab_report(
    source_path: str | Path,
    *,
    source_document_id: str,
    fixture_path: str | Path,
    root: str | Path = ROOT,
    reconciliation_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run the fixture-backed model/deterministic A/B for one booklet."""
    path = Path(source_path)
    frame = build_frame_from_fixture(
        path,
        source_document_id=source_document_id,
        fixture_path=fixture_path,
        allowed_document_ids=manifest_owner_document_ids(
            root,
            source_document_id=source_document_id,
        ),
        root=root,
    )
    deterministic = _baseline_sections(path, source_document_id)
    cells = load_reconciliation_cells(
        root,
        source_document_id=source_document_id,
        reconciliation_path=reconciliation_path,
    )
    report = score_ab(
        source_document_id=source_document_id,
        model_frame=frame,
        deterministic_sections=deterministic,
        cells_by_document=cells,
        worksheet_document_ids=manifest_worksheet_document_ids(
            root,
            source_document_id=source_document_id,
        ),
    )
    report["model_coverage"] = dict(frame.coverage)
    report["deterministic_section_count"] = len(deterministic)
    return report


def _write_recording(
    output: Path,
    *,
    source_document_id: str,
    source_bytes: bytes,
    records: Sequence[Mapping[str, Any]],
) -> None:
    """Persist the paid model responses before any frame verification."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "booklets": {
                    source_document_id: {
                        "source_sha256": _fingerprint(source_bytes),
                        "responses": list(records),
                    }
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="ascii",
        newline="\n",
    )


def _allowed_document_ids_for_window(
    allowed_document_ids: Iterable[str],
    *,
    chapter_document_id: str | None,
    worksheet_document_ids: Iterable[str],
) -> frozenset[str]:
    """Limit a chapter window to its form plus the booklet worksheets."""
    allowed = {str(value).strip() for value in allowed_document_ids if str(value).strip()}
    if chapter_document_id is None:
        return frozenset(allowed)
    worksheets = {
        str(value).strip()
        for value in worksheet_document_ids
        if str(value).strip()
    }
    return frozenset(
        document_id
        for document_id in allowed
        if document_id == chapter_document_id or document_id in worksheets
    )


def main() -> int:
    """Run a fixture-backed pilot or print one live window prompt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_document_id")
    parser.add_argument("--year", default="2025")
    parser.add_argument("--fixture", type=Path, default=None)
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-window-bytes", type=int, default=12000)
    parser.add_argument("--overlap-bytes", type=int, default=2000)
    args = parser.parse_args()

    source_path = args.source or ROOT / ".cache" / "raw" / args.year / f"{args.source_document_id}.txt"
    source_bytes = source_path.read_bytes()
    chapters = build_source_chapters(
        source_bytes,
        source_document_id=args.source_document_id,
        year=args.year,
    )
    allowed_document_ids = manifest_owner_document_ids(
        ROOT,
        source_document_id=args.source_document_id,
    )
    try:
        worksheet_document_ids = manifest_worksheet_document_ids(
            ROOT,
            source_document_id=args.source_document_id,
        )
    except FileNotFoundError:
        # A provider-test harness may replace the owner lookup while using a
        # temporary root with no manifest.  The real owner lookup above still
        # fails closed when the configured manifest is absent.
        worksheet_document_ids = frozenset()
    windows = build_source_windows(
        source_bytes,
        max_window_bytes=args.max_window_bytes,
        overlap_bytes=args.overlap_bytes,
        chapters=chapters,
    )
    if args.dry_run:
        print(f"source bytes: {len(source_bytes)}")
        print(f"windows: {len(windows)}")
        print(
            build_window_prompt(
                source_bytes,
                windows[0],
                source_document_id=args.source_document_id,
                allowed_document_ids=_allowed_document_ids_for_window(
                    allowed_document_ids,
                    chapter_document_id=windows[0].chapter_document_id,
                    worksheet_document_ids=worksheet_document_ids,
                ),
            )
        )
        return 0
    if args.fixture is None:
        config = load_config(root=ROOT)
        records: list[dict[str, Any]] = []
        output = args.output or Path(
            f"m20_s124_{_slug(args.source_document_id)}_responses.json"
        )
        for window in windows:
            prompt = build_window_prompt(
                source_bytes,
                window,
                source_document_id=args.source_document_id,
                allowed_document_ids=_allowed_document_ids_for_window(
                    allowed_document_ids,
                    chapter_document_id=window.chapter_document_id,
                    worksheet_document_ids=worksheet_document_ids,
                ),
            )
            window_allowed_document_ids = _allowed_document_ids_for_window(
                allowed_document_ids,
                chapter_document_id=window.chapter_document_id,
                worksheet_document_ids=worksheet_document_ids,
            )
            response = call_model_window(
                prompt,
                config,
                allowed_document_ids=window_allowed_document_ids,
            )
            records.append(
                {
                    "chapter_document_id": window.chapter_document_id,
                    "chapter_index": window.chapter_index,
                    "window_index": window.index,
                    "window_start_byte": window.start_byte,
                    "window_end_byte": window.end_byte,
                    "response": dict(response),
                }
            )
            _write_recording(
                output,
                source_document_id=args.source_document_id,
                source_bytes=source_bytes,
                records=records,
            )
        frame = build_model_frame(
            source_bytes.decode("utf-8"),
            source_document_id=args.source_document_id,
            responses=records,
            year=args.year,
            source_path=source_path,
            allowed_document_ids=allowed_document_ids,
            chapters=chapters,
            worksheet_document_ids=worksheet_document_ids,
        )
        print(f"wrote {output}; sections={len(frame.sections)}")
        return 0

    frame = build_frame_from_fixture(
        source_path,
        source_document_id=args.source_document_id,
        fixture_path=args.fixture,
        year=args.year,
        allowed_document_ids=allowed_document_ids,
    )
    print(
        f"verified {args.source_document_id}: {len(frame.sections)} sections, "
        f"{frame.coverage['response_window_count']} response windows"
    )
    if args.output is not None:
        args.output.write_text(
            yaml.safe_dump(frame.as_dict(source_bytes), sort_keys=False, allow_unicode=False),
            encoding="ascii",
            newline="\n",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
