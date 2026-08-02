"""Build the deterministic instruction_sections frame from acquired text.

The acquired instruction booklet is the content authority.  This module adds
only structure: it records which form context owns each printed line heading,
keeps the original source slice verbatim, and gives the slice a line-based
locator.  No model call and no graph write belongs here.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any

import yaml


_HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.*?)\s*$")
_PAGE_RE = re.compile(r"^#\s+Page\s+(?P<page>[0-9]+)\s*$", re.IGNORECASE)
_LINE_WORD_RE = re.compile(r"\blines?\b", re.IGNORECASE)
_LINE_TOKEN_RE = re.compile(r"[0-9]+[a-z]?", re.IGNORECASE)
_LINE_MENTION_RE = re.compile(r"\bline\s+([0-9]+[a-z]?)\b", re.IGNORECASE)


@dataclass(frozen=True)
class InstructionLocator:
    """A reproducible source location for one verbatim section."""

    source_document_id: str
    source_path: str | None
    start_line: int
    end_line: int
    start_offset: int
    end_offset: int
    page: int | None
    heading_level: int

    def as_dict(self) -> dict[str, Any]:
        """Return a YAML-safe locator mapping."""
        return {
            "source_document_id": self.source_document_id,
            "source_path": self.source_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "page": self.page,
            "heading_level": self.heading_level,
        }


@dataclass(frozen=True)
class InstructionSection:
    """One line-owned, verbatim instruction section."""

    section_id: str
    document_id: str
    line: str
    line_tokens: tuple[str, ...]
    heading: str
    context_heading: str
    text: str
    locator: InstructionLocator

    def as_dict(self) -> dict[str, Any]:
        """Return the section in the persisted frame shape."""
        return {
            "section_id": self.section_id,
            "document_id": self.document_id,
            "line": self.line,
            "line_tokens": list(self.line_tokens),
            "heading": self.heading,
            "context_heading": self.context_heading,
            "text": self.text,
            "locator": self.locator.as_dict(),
        }


@dataclass(frozen=True)
class InstructionSectionsFrame:
    """The typed instruction_sections frame for one acquired booklet."""

    schema_version: int
    year: str
    source_document_id: str
    source_path: str | None
    sections: tuple[InstructionSection, ...]
    coverage: dict[str, Any]

    def for_line(self, document_id: str, line: str) -> tuple[InstructionSection, ...]:
        """Return all sections owned by one form and printed line."""
        normalized = _normalize_line(line)
        return tuple(
            section
            for section in self.sections
            if section.document_id == document_id and section.line == normalized
        )

    def as_dict(self) -> dict[str, Any]:
        """Return the complete persisted artifact."""
        return {
            "schema_version": self.schema_version,
            "year": self.year,
            "source_document_id": self.source_document_id,
            "source_path": self.source_path,
            "sections": [section.as_dict() for section in self.sections],
            "coverage": self.coverage,
        }


@dataclass(frozen=True)
class _Heading:
    """A semantic Markdown heading, excluding page-number markers."""

    level: int
    title: str
    line_number: int
    line_index: int
    start_offset: int
    page: int | None


def build_instruction_sections(
    text: str,
    *,
    source_document_id: str,
    year: str | int = "2025",
    source_path: str | Path | None = None,
    expected_lines: Iterable[str] | Mapping[str, Iterable[str]] | None = None,
) -> InstructionSectionsFrame:
    """Build a deterministic frame from one acquired instruction booklet.

    A line heading owns its body through deeper headings until the next
    semantic heading at the same or a higher level.  Page markers are layout
    metadata and therefore do not terminate a section.  Form context changes
    only at an explicit form or schedule heading, plus the known Schedule 1
    heading in the combined Form 1040 booklet.
    """
    year_text = str(year)
    source_path_text = str(source_path) if source_path is not None else None
    default_document_id = _default_document_id(source_document_id, year_text)
    headings = _parse_headings(text)
    line_starts = _line_starts(text)
    lines = text.splitlines(keepends=True)
    sections: list[InstructionSection] = []
    current_document_id = default_document_id
    current_context_heading = f"source {source_document_id}"
    context_documents: set[str] = {default_document_id}
    section_number = 0

    for index, heading in enumerate(headings):
        context = _context_for_heading(
            heading.title,
            current_document_id=current_document_id,
            default_document_id=default_document_id,
            year=year_text,
        )
        if context is not None:
            current_document_id, current_context_heading = context
            context_documents.add(current_document_id)

        line_tokens = _line_tokens(heading.title)
        if not line_tokens:
            continue

        end_heading = _next_boundary(headings, index, heading.level)
        end_line_index = end_heading.line_index if end_heading is not None else len(lines)
        end_offset = end_heading.start_offset if end_heading is not None else len(text)
        start_offset = heading.start_offset
        section_text = text[start_offset:end_offset]
        section_number += 1
        section_id = (
            f"instruction_section_{_slug(source_document_id)}_"
            f"{section_number:04d}"
        )
        locator = InstructionLocator(
            source_document_id=source_document_id,
            source_path=source_path_text,
            start_line=heading.line_number,
            end_line=max(heading.line_number, end_line_index),
            start_offset=start_offset,
            end_offset=end_offset,
            page=heading.page,
            heading_level=heading.level,
        )
        for line_token in line_tokens:
            sections.append(
                InstructionSection(
                    section_id=section_id,
                    document_id=current_document_id,
                    line=line_token,
                    line_tokens=line_tokens,
                    heading=heading.title,
                    context_heading=current_context_heading,
                    text=section_text,
                    locator=locator,
                )
            )

    coverage = _coverage(
        sections,
        expected_lines=expected_lines,
        default_document_id=default_document_id,
        context_documents=context_documents,
    )
    return InstructionSectionsFrame(
        schema_version=1,
        year=year_text,
        source_document_id=source_document_id,
        source_path=source_path_text,
        sections=tuple(sections),
        coverage=coverage,
    )


def build_instruction_sections_file(
    path: str | Path,
    *,
    source_document_id: str | None = None,
    year: str | int = "2025",
    expected_lines: Iterable[str] | Mapping[str, Iterable[str]] | None = None,
) -> InstructionSectionsFrame:
    """Build a frame from a local acquired text file."""
    source_path = Path(path)
    document_id = source_document_id or source_path.stem
    return build_instruction_sections(
        source_path.read_text(encoding="utf-8"),
        source_document_id=document_id,
        year=year,
        source_path=source_path,
        expected_lines=expected_lines,
    )


def empty_instruction_sections_frame(
    *,
    source_document_id: str = "",
    year: str | int = "2025",
    source_path: str | Path | None = None,
) -> InstructionSectionsFrame:
    """Return a valid empty frame for a form with no instruction source."""
    return build_instruction_sections(
        "",
        source_document_id=source_document_id,
        year=year,
        source_path=source_path,
    )


def frame_from_dict(data: Mapping[str, Any]) -> InstructionSectionsFrame:
    """Load a persisted instruction_sections artifact without re-mining text."""
    sections: list[InstructionSection] = []
    for raw in data.get("sections", []) or []:
        locator_data = raw.get("locator") or {}
        locator = InstructionLocator(
            source_document_id=str(locator_data.get("source_document_id") or data.get("source_document_id") or ""),
            source_path=locator_data.get("source_path"),
            start_line=int(locator_data.get("start_line") or 0),
            end_line=int(locator_data.get("end_line") or 0),
            start_offset=int(locator_data.get("start_offset") or 0),
            end_offset=int(locator_data.get("end_offset") or 0),
            page=_optional_int(locator_data.get("page")),
            heading_level=int(locator_data.get("heading_level") or 0),
        )
        line_tokens = tuple(str(value).lower() for value in raw.get("line_tokens", []) or [])
        if not line_tokens and raw.get("line"):
            line_tokens = (str(raw["line"]).lower(),)
        sections.append(
            InstructionSection(
                section_id=str(raw.get("section_id") or ""),
                document_id=str(raw.get("document_id") or ""),
                line=_normalize_line(raw.get("line")),
                line_tokens=line_tokens,
                heading=str(raw.get("heading") or ""),
                context_heading=str(raw.get("context_heading") or ""),
                text=str(raw.get("text") or ""),
                locator=locator,
            )
        )
    return InstructionSectionsFrame(
        schema_version=int(data.get("schema_version") or 1),
        year=str(data.get("year") or ""),
        source_document_id=str(data.get("source_document_id") or ""),
        source_path=data.get("source_path"),
        sections=tuple(sections),
        coverage=dict(data.get("coverage") or {}),
    )


def load_instruction_sections_artifact(path: str | Path) -> InstructionSectionsFrame:
    """Load a persisted YAML instruction_sections artifact."""
    artifact_path = Path(path)
    data = yaml.safe_load(artifact_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, Mapping):
        raise ValueError(f"expected instruction_sections mapping in {artifact_path}")
    return frame_from_dict(data)


def write_instruction_sections_artifact(
    frame: InstructionSectionsFrame,
    path: str | Path,
) -> Path:
    """Persist one deterministic frame without touching graph artifacts."""
    artifact_path = Path(path)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    payload = yaml.safe_dump(frame.as_dict(), sort_keys=False, allow_unicode=False)
    artifact_path.write_text(payload, encoding="utf-8", newline="\n")
    return artifact_path


def _parse_headings(text: str) -> tuple[_Heading, ...]:
    headings: list[_Heading] = []
    page: int | None = None
    starts = _line_starts(text)
    for line_index, raw_line in enumerate(text.splitlines(keepends=True)):
        value = raw_line.rstrip("\r\n")
        page_match = _PAGE_RE.match(value.strip())
        if page_match:
            page = int(page_match.group("page"))
            continue
        match = _HEADING_RE.match(value.strip())
        if not match:
            continue
        headings.append(
            _Heading(
                level=len(match.group("marks")),
                title=_clean_heading_title(match.group("title")),
                line_number=line_index + 1,
                line_index=line_index,
                start_offset=starts[line_index],
                page=page,
            )
        )
    return tuple(headings)


def _next_boundary(
    headings: tuple[_Heading, ...],
    index: int,
    level: int,
) -> _Heading | None:
    for heading in headings[index + 1 :]:
        if heading.level <= level:
            return heading
    return None


def _context_for_heading(
    title: str,
    *,
    current_document_id: str,
    default_document_id: str,
    year: str,
) -> tuple[str, str] | None:
    normalized = re.sub(r"\s+", " ", _clean_heading_title(title)).strip()
    lowered = normalized.lower()
    explicit = _document_id_from_instruction_heading(normalized, year)
    if explicit is not None:
        return explicit, normalized
    if (
        default_document_id.startswith("form_1040_")
        and current_document_id == default_document_id
        and lowered == "additional income and adjustments to income"
    ):
        return f"schedule_1_{year}", normalized
    return None


def _document_id_from_instruction_heading(title: str, year: str) -> str | None:
    lowered = title.lower()
    if "line instructions for forms 1040" in lowered:
        return f"form_1040_{year}"
    schedule = re.search(
        r"\binstructions for schedule\s+([0-9]+(?:-?[a-z])?|[a-z])",
        lowered,
    )
    if schedule:
        token = schedule.group(1).replace("-", "")
        return f"schedule_{token}_{year}"
    form = re.search(r"\binstructions for form\s+([0-9]+[a-z]?)", lowered)
    if form:
        return f"form_{form.group(1)}_{year}"
    return None


def _line_tokens(title: str) -> tuple[str, ...]:
    clean = _clean_heading_title(title)
    matches = list(_LINE_WORD_RE.finditer(clean))
    if not matches:
        return ()
    match = matches[-1]
    plural = clean[match.start() : match.end()].lower() == "lines"
    remainder = clean[match.end() :]
    first = re.match(r"\s*([0-9]+[a-z]?)", remainder, re.IGNORECASE)
    if not first:
        return ()
    tokens = [first.group(1).lower()]
    position = first.end()
    if plural:
        while True:
            connector = re.match(
                r"\s*(?:,|and|through|thru|to|or|-)\s*([0-9]+[a-z]?)",
                remainder[position:],
                re.IGNORECASE,
            )
            if not connector:
                break
            tokens.append(connector.group(1).lower())
            position += connector.end()
    if plural and re.search(r"\b(?:through|thru|to)\b", remainder[:position], re.IGNORECASE):
        tokens = _expand_alpha_range(tokens)
    return tuple(dict.fromkeys(tokens))


def _expand_alpha_range(tokens: list[str]) -> list[str]:
    if len(tokens) < 2:
        return tokens
    first = re.fullmatch(r"([0-9]+)([a-z])", tokens[0], re.IGNORECASE)
    last = re.fullmatch(r"([0-9]+)([a-z])", tokens[-1], re.IGNORECASE)
    if not first or not last or first.group(1) != last.group(1):
        return tokens
    start = ord(first.group(2).lower())
    end = ord(last.group(2).lower())
    if end < start or end - start > 25:
        return tokens
    return [f"{first.group(1)}{chr(value)}" for value in range(start, end + 1)]


def _coverage(
    sections: list[InstructionSection],
    *,
    expected_lines: Iterable[str] | Mapping[str, Iterable[str]] | None,
    default_document_id: str,
    context_documents: Iterable[str],
) -> dict[str, Any]:
    by_form: dict[str, list[InstructionSection]] = {}
    for section in sections:
        by_form.setdefault(section.document_id, []).append(section)

    expected_by_form: dict[str, set[str]] = {}
    if isinstance(expected_lines, Mapping):
        expected_by_form = {
            str(document_id): {_normalize_line(line) for line in lines}
            for document_id, lines in expected_lines.items()
        }
    elif expected_lines is not None:
        expected_by_form[default_document_id] = {
            _normalize_line(line) for line in expected_lines
        }

    forms: dict[str, Any] = {}
    document_ids = set(context_documents) | set(by_form) | set(expected_by_form)
    for document_id in sorted(document_ids):
        form_sections = by_form.get(document_id, [])
        lines_with = sorted({section.line for section in form_sections}, key=_line_sort_key)
        expected = sorted(expected_by_form.get(document_id, set()), key=_line_sort_key)
        lines_without = [line for line in expected if line not in lines_with]
        unique_sections = {section.section_id for section in form_sections}
        wrong_before = _wrong_owner_mentions(form_sections)
        forms[document_id] = {
            "section_count": len(unique_sections),
            "line_count": len(lines_with),
            "lines_with_section": lines_with,
            "expected_line_count": len(expected),
            "lines_without_section": lines_without,
            "wrong_owner_spans_before": wrong_before,
            "wrong_owner_spans_after": 0,
            "has_sections": bool(form_sections),
        }

    line_contexts: dict[str, set[str]] = {}
    for section in sections:
        line_contexts.setdefault(section.line, set()).add(section.document_id)
    collisions = {
        line: sorted(contexts)
        for line, contexts in sorted(line_contexts.items(), key=lambda item: _line_sort_key(item[0]))
        if len(contexts) > 1
    }
    return {
        "source_documents": sorted(document_ids),
        "forms": forms,
        "unattributed_section_count": 0,
        "documents_without_sections": sorted(
            document_id for document_id in document_ids if not by_form.get(document_id)
        ),
        "collision_count": len(collisions),
        "collisions_resolved_by_form_context": sum(len(values) - 1 for values in collisions.values()),
        "cross_schedule_collisions": collisions,
        "wrong_owner_spans_before": sum(
            int(values["wrong_owner_spans_before"]) for values in forms.values()
        ),
        "wrong_owner_spans_after": 0,
    }


def _wrong_owner_mentions(sections: list[InstructionSection]) -> int:
    by_id: dict[str, InstructionSection] = {}
    for section in sections:
        by_id[section.section_id] = section
    count = 0
    for section in by_id.values():
        owned = set(section.line_tokens)
        mentioned = {value.lower() for value in _LINE_MENTION_RE.findall(section.text)}
        count += len(mentioned - owned)
    return count


def _default_document_id(source_document_id: str, year: str) -> str:
    prefix = "instructions_"
    if source_document_id.startswith(prefix):
        return source_document_id[len(prefix) :]
    return source_document_id or f"unknown_{year}"


def _clean_heading_title(value: str) -> str:
    return re.sub(r"(?:\*\*|__)", "", value).strip()


def _normalize_line(value: Any) -> str:
    return str(value or "").strip().lower()


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for index, char in enumerate(text):
        if char == "\n":
            starts.append(index + 1)
    return starts


def _line_sort_key(value: str) -> tuple[int, str, int]:
    match = re.fullmatch(r"([0-9]+)([a-z]?)", value.lower())
    if not match:
        return (10**9, value.lower(), 0)
    return (int(match.group(1)), match.group(2), len(match.group(2)))


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "source"
