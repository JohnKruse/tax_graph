"""Pilot a model-owned, cell-naive segmentation of instruction booklets.

This module is deliberately confined to ``pilot/``.  The model sees acquired
instruction text only.  It returns section boundaries and ownership claims;
the deterministic verifier binds every boundary to the acquired bytes before
the scorer is allowed to look at any form cells.

The production instruction frame is not changed here.  This pilot keeps a
small parallel frame because a topic section such as ``Part I. Interest`` can
govern a group of lines without printing a line number in its own heading.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tax_graph.acquire.manifest import load_manifest  # noqa: E402
from tax_graph.config import (  # noqa: E402
    get_config_value,
    load_config,
    resolve_llm_model,
    resolve_llm_seed,
)
from tax_graph.extract.instruction_sections import (  # noqa: E402
    build_instruction_sections_file,
)


PROMPT_PATH = ROOT / "prompts" / "instruction_segmenter.md"
_LINE_TOKEN_RE = re.compile(r"^[0-9]+[a-z]?$", re.IGNORECASE)
_SLUG_RE = re.compile(r"[^a-z0-9]+", re.IGNORECASE)


class SegmenterError(ValueError):
    """Raised when a model response cannot be made into a source-backed frame."""


class ModelFrameVerificationError(SegmenterError):
    """Raised when a section fails the byte or heading witness."""


@dataclass(frozen=True)
class SourceWindow:
    """One UTF-8-safe source window with absolute byte coordinates."""

    index: int
    start_byte: int
    end_byte: int

    def as_dict(self) -> dict[str, int]:
        """Return the window coordinates used by a recorded response."""
        return {
            "index": self.index,
            "start_byte": self.start_byte,
            "end_byte": self.end_byte,
        }


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


def build_source_windows(
    source_bytes: bytes,
    *,
    max_window_bytes: int = 12000,
    overlap_bytes: int = 2000,
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
    if not source_bytes:
        return (SourceWindow(index=0, start_byte=0, end_byte=0),)

    boundaries = _utf8_boundaries(source_bytes)
    windows: list[SourceWindow] = []
    start = 0
    index = 0
    while start < len(source_bytes):
        candidate_end = min(len(source_bytes), start + max_window_bytes)
        end = _boundary_at_or_before(boundaries, candidate_end)
        if end <= start:
            raise ValueError("max_window_bytes falls inside an unrepresentable source character")
        windows.append(SourceWindow(index=index, start_byte=start, end_byte=end))
        if end == len(source_bytes):
            break
        next_start = _boundary_at_or_before(boundaries, end - overlap_bytes)
        if next_start <= start:
            raise ValueError("window overlap prevents progress")
        start = next_start
        index += 1
    return tuple(windows)


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
    return (
        f"{instructions.rstrip()}\n\n"
        f"Source booklet id: {source_document_id}\n"
        f"{owner_contract}"
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
        "purpose": "tax_graph_pilot_instruction_segmentation",
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
) -> ModelSection:
    """Validate and convert one response record before frame reconciliation."""
    if isinstance(raw, (list, tuple)):
        if len(raw) != 6:
            raise SegmenterError(
                "compact section response must have heading, level, start, end, "
                "document_id, and governs"
            )
        raw = dict(
            zip(
                ("heading", "level", "start_byte", "end_byte", "document_id", "governs"),
                raw,
            )
        )
    if not isinstance(raw, Mapping):
        raise SegmenterError("each recorded section must be an object or compact row")
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
        raise SegmenterError(f"section response is missing fields: {', '.join(missing)}")
    heading = raw["heading"]
    document_id = raw["document_id"]
    if not isinstance(heading, str) or not heading:
        raise SegmenterError("section heading must be a non-empty string")
    if not isinstance(document_id, str) or not document_id.strip():
        raise SegmenterError("section document_id must be a non-empty string")
    try:
        level = int(raw["level"])
        start_byte = int(raw["start_byte"])
        end_byte = int(raw["end_byte"])
    except (TypeError, ValueError) as exc:
        raise SegmenterError("section level and byte ranges must be integers") from exc
    if level < 1 or start_byte >= end_byte:
        raise SegmenterError("section level and byte range are invalid")
    if start_byte < window.start_byte or end_byte > window.end_byte:
        raise SegmenterError(
            f"section {start_byte}:{end_byte} escapes window "
            f"{window.start_byte}:{window.end_byte}"
        )
    if end_byte > len(source_bytes):
        raise SegmenterError("section ends outside source")
    if "text" in raw:
        claimed_text = raw["text"]
        actual_text = source_bytes[start_byte:end_byte].decode("utf-8")
        if claimed_text != actual_text:
            raise ModelFrameVerificationError(
                f"text does not match claimed range {start_byte}:{end_byte}"
            )
    normalized_document_id = document_id.strip()
    if allowed_document_ids is not None and normalized_document_id not in allowed_document_ids:
        allowed = ", ".join(sorted(allowed_document_ids)) or "<none>"
        raise ModelFrameVerificationError(
            f"document_id {normalized_document_id!r} is not an allowed owner for "
            f"{source_document_id}; allowed: {allowed}"
        )
    return ModelSection(
        section_id="",
        source_document_id=source_document_id,
        document_id=normalized_document_id,
        heading=heading,
        level=level,
        governs=_coerce_governs(raw["governs"]),
        start_byte=start_byte,
        end_byte=end_byte,
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
    dict[tuple[int, str], ModelSection],
    int,
    int,
    list[dict[str, Any]],
]:
    """Reconcile duplicate observations and retain only source-backed claims.

    Ownership conflicts retain the previous fail-closed behavior when a manifest
    vocabulary is supplied.  A conflicting ``governs`` claim is resolved from
    window context instead: the observation with the most trailing context wins,
    while ties and all-edge observations are rejected as ambiguous.
    """
    grouped: dict[tuple[int, str], list[tuple[ModelSection, SourceWindow]]] = {}
    for section, window in parsed:
        grouped.setdefault((section.start_byte, section.heading), []).append(
            (section, window)
        )

    unique: dict[tuple[int, str], ModelSection] = {}
    owner_conflict_count = 0
    governs_conflict_count = 0
    rejected_sections: list[dict[str, Any]] = []
    for key, claims in grouped.items():
        first_section = claims[0][0]
        owner_conflicts = [
            section for section, _window in claims
            if section.document_id != first_section.document_id
        ]
        if owner_conflicts and allowed_document_ids is not None:
            raise ModelFrameVerificationError(
                "overlapping windows disagree about document_id at "
                f"{first_section.start_byte}"
            )
        owner_conflict_count += len(owner_conflicts)

        governs_values = {section.governs for section, _window in claims}
        if len(governs_values) <= 1:
            unique[key] = first_section
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
                    "heading": first_section.heading,
                    "reason": "ambiguous_governs_conflict",
                    "ambiguity": ambiguity,
                    "competing_claims": [
                        _governs_claim(section, window)
                        for section, window in ordered_claims
                    ],
                }
            )
            continue
        unique[key] = winner[0]

    return (
        unique,
        owner_conflict_count,
        governs_conflict_count,
        rejected_sections,
    )


def build_model_frame(
    source_text: str,
    *,
    source_document_id: str,
    responses: Iterable[Mapping[str, Any]],
    year: str | int = "2025",
    source_path: str | Path | None = None,
    allowed_document_ids: Iterable[str] | None = None,
    drop_invalid_sections: bool = False,
) -> ModelInstructionFrame:
    """Reconcile recorded window responses into one verified model frame.

    Provider output is strict by default.  Recorded replay may explicitly drop
    source-unbacked proposals before verifying the remaining frame; the dropped
    count is retained in coverage so replay cannot hide model defects.
    """
    source_bytes = source_text.encode("utf-8")
    normalized_allowed_ids = _normalize_document_ids(allowed_document_ids)
    allowed_ids = (
        frozenset(normalized_allowed_ids)
        if normalized_allowed_ids is not None
        else None
    )
    parsed: list[tuple[ModelSection, SourceWindow]] = []
    response_count = 0
    for response_record in responses:
        response_count += 1
        try:
            window = SourceWindow(
                index=int(response_record["window_index"]),
                start_byte=int(response_record["window_start_byte"]),
                end_byte=int(response_record["window_end_byte"]),
            )
            raw_sections = response_record["response"]["sections"]
        except (KeyError, TypeError, ValueError) as exc:
            raise SegmenterError("invalid recorded window response envelope") from exc
        if not 0 <= window.start_byte <= window.end_byte <= len(source_bytes):
            raise SegmenterError(f"invalid response window: {window}")
        if not isinstance(raw_sections, list):
            raise SegmenterError("recorded response sections must be a list")
        for raw in raw_sections:
            parsed.append(
                (
                    _raw_section(
                        raw,
                        source_document_id=source_document_id,
                        window=window,
                        source_bytes=source_bytes,
                        allowed_document_ids=allowed_ids,
                    ),
                    window,
                )
            )

    (
        unique,
        owner_conflict_count,
        governs_conflict_count,
        rejected_sections,
    ) = _reconcile_window_sections(
        parsed,
        allowed_document_ids=allowed_ids,
    )
    observed_candidates = sorted(
        unique.values(), key=lambda item: (item.start_byte, item.end_byte)
    )
    observed: list[ModelSection] = []
    for section in observed_candidates:
        actual_heading = _source_line_at(source_bytes, section.start_byte)
        if not _heading_is_source_prefix(section.heading, actual_heading):
            if not drop_invalid_sections:
                observed.append(section)
                continue
            rejected_sections.append(
                {
                    "start_byte": section.start_byte,
                    "heading": section.heading,
                    "reason": "heading_not_at_source_offset",
                }
            )
            continue
        observed.append(section)
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
            "response_section_count": len(parsed),
            "unique_section_count": len(verified_sections),
            "duplicate_response_sections": len(parsed) - len(verified_sections),
            "boundary_repaired_sections": sum(
                section.end_byte != verified_sections[index].end_byte
                for index, section in enumerate(observed)
            ),
            "rejected_sections": rejected_sections,
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
        raise SegmenterError(f"invalid M20-S121 fixture: {fixture_path}")
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
    drop_invalid_sections: bool = True,
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
    return build_model_frame(
        source_text,
        source_document_id=source_document_id,
        responses=responses,
        year=year,
        source_path=path,
        allowed_document_ids=allowed_document_ids,
        drop_invalid_sections=drop_invalid_sections,
    )


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
    documents: dict[str, Any] = {}
    for document_id, raw_cells in sorted(cells_by_document.items()):
        cells = tuple(dict(cell) for cell in raw_cells)
        gained: list[str] = []
        wrong_owner: list[dict[str, Any]] = []
        baseline_correct = 0
        model_correct = 0
        model_reachable = 0
        for cell in cells:
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
                    wrong_owner.append(
                        {
                            "cell_id": cell_id,
                            "line": line,
                            "expected_document_id": document_id,
                            "actual_document_id": owner,
                            "section_id": section.get("section_id"),
                        }
                    )
        documents[document_id] = {
            "cell_count": len(cells),
            "baseline_correct": baseline_correct,
            "model_correct": model_correct,
            "model_reachable": model_reachable,
            "gained_correctly_owned": sorted(gained),
            "wrong_owner": wrong_owner,
            "wrong_owner_count": len(wrong_owner),
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
            "wrong_owner": sum(item["wrong_owner_count"] for item in documents.values()),
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
    manifest = load_manifest(root=root_path)
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
    for entry in manifest.documents:
        if entry.instructions_document_id != source_document_id:
            continue
        document = documents.get(entry.document_id) or {}
        result[entry.document_id] = tuple(
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
    )
    report["model_coverage"] = dict(frame.coverage)
    report["deterministic_section_count"] = len(deterministic)
    return report


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
    allowed_document_ids = manifest_owner_document_ids(
        ROOT,
        source_document_id=args.source_document_id,
    )
    windows = build_source_windows(
        source_bytes,
        max_window_bytes=args.max_window_bytes,
        overlap_bytes=args.overlap_bytes,
    )
    if args.dry_run:
        print(f"source bytes: {len(source_bytes)}")
        print(f"windows: {len(windows)}")
        print(
            build_window_prompt(
                source_bytes,
                windows[0],
                source_document_id=args.source_document_id,
                allowed_document_ids=allowed_document_ids,
            )
        )
        return 0
    if args.fixture is None:
        config = load_config(root=ROOT)
        records: list[dict[str, Any]] = []
        for window in windows:
            prompt = build_window_prompt(
                source_bytes,
                window,
                source_document_id=args.source_document_id,
                allowed_document_ids=allowed_document_ids,
            )
            response = call_model_window(
                prompt,
                config,
                allowed_document_ids=allowed_document_ids,
            )
            records.append(
                {
                    "window_index": window.index,
                    "window_start_byte": window.start_byte,
                    "window_end_byte": window.end_byte,
                    "response": dict(response),
                }
            )
        frame = build_model_frame(
            source_bytes.decode("utf-8"),
            source_document_id=args.source_document_id,
            responses=records,
            year=args.year,
            source_path=source_path,
            allowed_document_ids=allowed_document_ids,
        )
        output = args.output or Path(
            f"m20_s121_{_slug(args.source_document_id)}_responses.json"
        )
        output.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "booklets": {
                        args.source_document_id: {
                            "source_sha256": _fingerprint(source_bytes),
                            "responses": records,
                        }
                    },
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="ascii",
            newline="\n",
        )
        print(f"wrote {output}; sections={len(frame.sections)}")
        return 0

    frame = build_frame_from_fixture(
        source_path,
        source_document_id=args.source_document_id,
        fixture_path=args.fixture,
        year=args.year,
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
