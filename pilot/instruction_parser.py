"""Pilot instruction parser for the M20-S75 corpus measurement.

This module deliberately stays under ``pilot/``.  It measures a proposed
instruction-section parser against the current OCR parser and the acquired
IRS HTML, but it does not replace the production parser or write graph data.

The two acquired sources remain separate in every returned section.  The HTML
line inventory is used only as a deterministic printed-line witness while the
OCR heading is repaired; source text and provenance are never merged by
fallback.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from tax_graph.acquire.instruction_html import parse_headings
from tax_graph.acquire.instruction_html import line_sections as html_line_sections
from tax_graph.extract.instruction_sections import (
    InstructionSection as CurrentInstructionSection,
    build_instruction_sections_file,
)


INSTRUCTION_FORMS: Mapping[str, str] = {
    "instructions_form_1040_2025": "form_1040_2025",
    "instructions_form_2441_2025": "form_2441_2025",
    "instructions_form_6251_2025": "form_6251_2025",
    "instructions_form_8949_2025": "form_8949_2025",
    "instructions_schedule_a_2025": "schedule_a_2025",
    "instructions_schedule_b_2025": "schedule_b_2025",
    "instructions_schedule_d_2025": "schedule_d_2025",
}

_PAGE_RE = re.compile(r"^#\s+Page\s+(?P<page>[0-9]+)\s*$", re.IGNORECASE)
_MARKDOWN_HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.*?)\s*$")
_BOLD_HEADING_RE = re.compile(r"^(?:\*\*|__)(?P<title>.+?)(?:\*\*|__)\s*$")
_LINE_HEADING_RE = re.compile(r"^lines?\s+(?P<rest>.+)$", re.IGNORECASE)
_TOKEN_RE = re.compile(r"(?P<token>[0-9]+[a-z]?)", re.IGNORECASE)
_CONNECTION_RE = re.compile(
    r"\s*(?:,\s*(?:and\s+)?|and\s+|through\s+|thru\s+|to\s+|or\s+|-\s*)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PilotSection:
    """One line-owned section from exactly one acquired source."""

    section_id: str
    source: str
    source_document_id: str
    owner_document_id: str
    line_tokens: tuple[str, ...]
    heading: str
    context_heading: str
    text: str
    start_line: int
    end_line: int
    start_offset: int
    end_offset: int
    heading_level: int
    page: int | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe evidence record."""

        return {
            "section_id": self.section_id,
            "source": self.source,
            "source_document_id": self.source_document_id,
            "owner_document_id": self.owner_document_id,
            "line_tokens": list(self.line_tokens),
            "heading": self.heading,
            "context_heading": self.context_heading,
            "text": self.text,
            "locator": {
                "start_line": self.start_line,
                "end_line": self.end_line,
                "start_offset": self.start_offset,
                "end_offset": self.end_offset,
                "heading_level": self.heading_level,
                "page": self.page,
            },
        }


@dataclass(frozen=True)
class _OCRHeading:
    """A Markdown or bold-only heading in the OCR text."""

    level: int
    title: str
    line_number: int
    line_index: int
    start_offset: int
    page: int | None


def parse_ocr_sections(
    text: str,
    *,
    source_document_id: str,
    known_lines: Iterable[str],
    known_sections: Iterable[PilotSection] = (),
) -> tuple[PilotSection, ...]:
    """Parse OCR headings with bold-heading and printed-line repairs.

    ``known_lines`` is a deterministic witness of printed line tokens from
    the HTML source.  A malformed OCR token such as ``3o`` is canonicalized
    to known token ``3`` only when the known token is a prefix of the OCR
    token.  The body remains the original OCR slice.
    """

    headings = _parse_ocr_headings(text)
    lines = text.splitlines(keepends=True)
    known = {str(value).strip().lower() for value in known_lines if str(value).strip()}
    witness_by_owner: dict[str, list[PilotSection]] = {}
    for section in known_sections:
        witness_by_owner.setdefault(section.owner_document_id, []).append(section)
    default_document_id = _default_document_id(source_document_id)
    current_document_id = default_document_id
    current_context_heading = f"source {source_document_id}"
    sections: list[PilotSection] = []
    section_number = 0

    for index, heading in enumerate(headings):
        context = _context_for_heading(
            heading.title,
            current_document_id=current_document_id,
            default_document_id=default_document_id,
        )
        if context is not None:
            current_document_id, current_context_heading = context

        match = _LINE_HEADING_RE.match(heading.title)
        if not match:
            continue
        line_tokens = _line_tokens_and_title(match.group("rest"), known)
        witness_tokens = _matching_witness_tokens(
            heading.title,
            owner_document_id=current_document_id,
            witness_sections=witness_by_owner.get(current_document_id, ()),
        )
        if witness_tokens:
            line_tokens = witness_tokens
        if not line_tokens:
            continue

        next_heading = _next_ocr_boundary(headings, index, heading.level)
        end_offset = next_heading.start_offset if next_heading else len(text)
        end_line_index = next_heading.line_index if next_heading else len(lines)
        section_number += 1
        sections.append(
            PilotSection(
                section_id=f"ocr_{_slug(source_document_id)}_{section_number:04d}",
                source="ocr",
                source_document_id=source_document_id,
                owner_document_id=current_document_id,
                line_tokens=line_tokens,
                heading=heading.title,
                context_heading=current_context_heading,
                text=text[heading.start_offset:end_offset],
                start_line=heading.line_number,
                end_line=max(heading.line_number, end_line_index),
                start_offset=heading.start_offset,
                end_offset=end_offset,
                heading_level=heading.level,
                page=heading.page,
            )
        )
    return tuple(sections)


def parse_html_sections(
    html_text: str,
    *,
    source_document_id: str,
) -> tuple[PilotSection, ...]:
    """Parse line headings from the acquired HTML with HTML provenance."""

    headings = parse_headings(html_text)
    existing_sections = html_line_sections(html_text)
    known_lines = {
        token
        for section in existing_sections
        for token in section.line_tokens
    }
    default_document_id = _default_document_id(source_document_id)
    current_document_id = default_document_id
    current_context_heading = f"source {source_document_id}"
    sections: list[PilotSection] = []
    section_number = 0

    for index, heading in enumerate(headings):
        context = _context_for_heading(
            heading.text,
            current_document_id=current_document_id,
            default_document_id=default_document_id,
        )
        if context is not None:
            current_document_id, current_context_heading = context

        match = _LINE_HEADING_RE.match(heading.text)
        if not match:
            continue
        line_tokens = _line_tokens_and_title(match.group("rest"), known_lines)
        if not line_tokens:
            continue

        next_heading = _next_html_boundary(headings, index, heading.level)
        end_offset = next_heading.source_start if next_heading else len(html_text)
        start_offset = heading.source_start
        section_number += 1
        sections.append(
            PilotSection(
                section_id=f"html_{_slug(source_document_id)}_{section_number:04d}",
                source="html",
                source_document_id=source_document_id,
                owner_document_id=current_document_id,
                line_tokens=line_tokens,
                heading=heading.text,
                context_heading=current_context_heading,
                text=_visible_html_text(html_text[start_offset:end_offset]),
                start_line=html_text.count("\n", 0, start_offset) + 1,
                end_line=html_text.count("\n", 0, end_offset) + 1,
                start_offset=start_offset,
                end_offset=end_offset,
                heading_level=heading.level,
            )
        )
    return tuple(sections)


def measure_corpus(
    raw_root: str | Path,
    *,
    year: str | int = "2025",
) -> dict[str, Any]:
    """Measure current OCR, repaired OCR, and HTML across all seven documents."""

    root = Path(raw_root)
    documents: dict[str, Any] = {}
    for instruction_document_id, form_document_id in INSTRUCTION_FORMS.items():
        ocr_path = root / f"{instruction_document_id}.txt"
        html_path = root / f"{instruction_document_id}.html"
        if not ocr_path.is_file() or not html_path.is_file():
            raise FileNotFoundError(
                f"expected cached OCR and HTML for {instruction_document_id} under {root}"
            )

        html_sections = parse_html_sections(
            html_path.read_text(encoding="utf-8"),
            source_document_id=instruction_document_id,
        )
        known_lines = {
            token
            for section in html_sections
            for token in section.line_tokens
        }
        ocr_text = ocr_path.read_text(encoding="utf-8")
        repaired_sections = parse_ocr_sections(
            ocr_text,
            source_document_id=instruction_document_id,
            known_lines=known_lines,
            known_sections=html_sections,
        )
        current_sections = build_instruction_sections_file(
            ocr_path,
            source_document_id=instruction_document_id,
            year=year,
        )
        documents[instruction_document_id] = _document_measurement(
            instruction_document_id=instruction_document_id,
            form_document_id=form_document_id,
            current_sections=current_sections.sections,
            repaired_sections=repaired_sections,
            html_sections=html_sections,
            known_lines=known_lines,
        )

    return {
        "schema_version": 1,
        "year": str(year),
        "source_policy": {
            "ocr": "OCR structure proposal with original OCR text and provenance",
            "html": "HTML structure proposal with visible HTML text and provenance",
            "fallback": "none; both source records remain independently addressable",
        },
        "documents": documents,
    }


def _document_measurement(
    *,
    instruction_document_id: str,
    form_document_id: str,
    current_sections: Iterable[CurrentInstructionSection],
    repaired_sections: tuple[PilotSection, ...],
    html_sections: tuple[PilotSection, ...],
    known_lines: set[str],
) -> dict[str, Any]:
    current = tuple(current_sections)
    current_keys = {
        (section.document_id, section.line)
        for section in current
    }
    repaired_keys = _line_keys(repaired_sections)
    html_keys = _line_keys(html_sections)
    current_phantoms = sorted(
        {section.line for section in current if section.line not in known_lines}
    )
    repaired_phantoms = sorted(
        {
            token
            for section in repaired_sections
            for token in section.line_tokens
            if token not in known_lines
        }
    )
    source_findings = _source_findings(repaired_sections, html_sections)
    if not repaired_sections and not html_sections:
        source_findings.append(
            {
                "kind": "document_without_line_sections",
                "document_id": instruction_document_id,
                "message": "both acquired instruction sources produced no line sections",
            }
        )
    return {
        "form_document_id": form_document_id,
        "known_line_tokens": sorted(known_lines, key=_line_sort_key),
        "counts": {
            "ocr_today": len({section.section_id for section in current}),
            "ocr_with_fixes": len(repaired_sections),
            "html": len(html_sections),
        },
        "line_counts": {
            "ocr_today": len(current_keys),
            "ocr_with_fixes": len(repaired_keys),
            "html": len(html_keys),
        },
        "phantom_anchors": {
            "ocr_today": current_phantoms,
            "ocr_with_fixes": repaired_phantoms,
        },
        "gained_line_sections": [
            {"document_id": document_id, "line": line}
            for document_id, line in sorted(repaired_keys - current_keys)
        ],
        "html_only_line_sections": [
            {"document_id": document_id, "line": line}
            for document_id, line in sorted(html_keys - repaired_keys)
        ],
        "source_findings": source_findings,
        "sections": {
            "ocr_with_fixes": [section.as_dict() for section in repaired_sections],
            "html": [section.as_dict() for section in html_sections],
        },
    }


def _source_findings(
    ocr_sections: tuple[PilotSection, ...],
    html_sections: tuple[PilotSection, ...],
) -> list[dict[str, Any]]:
    """Report source disagreement without selecting a source as fallback."""

    ocr_by_line = _first_by_line(ocr_sections)
    html_by_line = _first_by_line(html_sections)
    findings: list[dict[str, Any]] = []
    for key in sorted(set(ocr_by_line) | set(html_by_line)):
        ocr = ocr_by_line.get(key)
        html = html_by_line.get(key)
        if ocr is None or html is None:
            findings.append(
                {
                    "kind": "source_line_presence_disagreement",
                    "document_id": key[0],
                    "line": key[1],
                    "ocr_heading": ocr.heading if ocr else None,
                    "html_heading": html.heading if html else None,
                }
            )
            continue
        if _heading_key(ocr.heading) != _heading_key(html.heading):
            findings.append(
                {
                    "kind": "source_section_disagreement",
                    "document_id": key[0],
                    "line": key[1],
                    "ocr_heading": ocr.heading,
                    "html_heading": html.heading,
                }
            )
    return findings


def _parse_ocr_headings(text: str) -> tuple[_OCRHeading, ...]:
    headings: list[_OCRHeading] = []
    offsets = _line_starts(text)
    page: int | None = None
    for line_index, raw_line in enumerate(text.splitlines(keepends=True)):
        value = raw_line.rstrip("\r\n").strip()
        page_match = _PAGE_RE.match(value)
        if page_match:
            page = int(page_match.group("page"))
            continue
        match = _MARKDOWN_HEADING_RE.match(value)
        if match:
            title = _clean_heading(match.group("title"))
            headings.append(
                _OCRHeading(
                    level=len(match.group("marks")),
                    title=title,
                    line_number=line_index + 1,
                    line_index=line_index,
                    start_offset=offsets[line_index],
                    page=page,
                )
            )
            continue
        bold_match = _BOLD_HEADING_RE.match(value)
        if bold_match:
            headings.append(
                _OCRHeading(
                    level=3,
                    title=_clean_heading(bold_match.group("title")),
                    line_number=line_index + 1,
                    line_index=line_index,
                    start_offset=offsets[line_index],
                    page=page,
                )
            )
    return tuple(headings)


def _line_tokens_and_title(rest: str, known_lines: Iterable[str]) -> tuple[str, ...]:
    """Parse only the line-heading token list, not numbers in the title."""

    known = {str(value).lower() for value in known_lines}
    position = 0
    tokens: list[str] = []
    while True:
        leading = re.match(r"\s*", rest[position:])
        position += leading.end()
        match = _TOKEN_RE.match(rest[position:])
        if not match:
            break
        raw = match.group("token").lower()
        tokens.append(_canonical_token(raw, known))
        position += match.end()
        connector = _CONNECTION_RE.match(rest[position:])
        if not connector:
            break
        next_position = position + connector.end()
        if not _TOKEN_RE.match(rest[next_position:]):
            break
        position = next_position
    return tuple(dict.fromkeys(tokens))


def _matching_witness_tokens(
    heading: str,
    *,
    owner_document_id: str,
    witness_sections: Iterable[PilotSection],
) -> tuple[str, ...]:
    """Use an exact heading-body match to resolve OCR glyph confusion.

    This is not a source fallback.  The HTML section stays a separate record,
    and the comparison report still records the heading disagreement.  The
    witness only prevents an OCR glyph such as capital ``I`` from changing a
    printed ``2l`` identity.
    """

    body = _heading_body_key(heading)
    if not body:
        return ()
    matches = [
        section
        for section in witness_sections
        if section.owner_document_id == owner_document_id
        and _heading_body_key(section.heading) == body
    ]
    token_sets = {section.line_tokens for section in matches}
    if len(token_sets) != 1:
        return ()
    return next(iter(token_sets))


def _heading_body_key(value: str) -> str:
    match = _LINE_HEADING_RE.match(_clean_heading(value))
    if not match:
        return ""
    rest = match.group("rest")
    token = _TOKEN_RE.match(rest)
    if token:
        rest = rest[token.end() :]
    return re.sub(r"[^a-z0-9]+", "", rest.lower())


def _canonical_token(raw: str, known_lines: set[str]) -> str:
    if raw in known_lines:
        return raw
    candidates = [value for value in known_lines if raw.startswith(value)]
    same_number = [
        value
        for value in candidates
        if re.match(r"[0-9]+", value).group() == re.match(r"[0-9]+", raw).group()
    ]
    if same_number:
        return max(same_number, key=len)
    return raw


def _context_for_heading(
    title: str,
    *,
    current_document_id: str,
    default_document_id: str,
) -> tuple[str, str] | None:
    normalized = re.sub(r"\s+", " ", _clean_heading(title)).strip()
    lowered = normalized.lower()
    if default_document_id.startswith("form_1040_") and lowered == "additional income and adjustments to income":
        return f"schedule_1_{_year_from_document(default_document_id)}", normalized
    schedule = re.search(
        r"\binstructions for schedule\s+([0-9]+(?:-?[a-z])?|[a-z])",
        lowered,
    )
    if schedule:
        token = schedule.group(1).replace("-", "")
        return f"schedule_{token}_{_year_from_document(default_document_id)}", normalized
    form = re.search(r"\binstructions for form\s+([0-9]+[a-z]?)", lowered)
    if form:
        return f"form_{form.group(1)}_{_year_from_document(default_document_id)}", normalized
    if lowered.startswith("line instructions for forms 1040"):
        return f"form_1040_{_year_from_document(default_document_id)}", normalized
    return None


def _next_ocr_boundary(
    headings: tuple[_OCRHeading, ...],
    index: int,
    level: int,
) -> _OCRHeading | None:
    for heading in headings[index + 1 :]:
        if heading.level <= level:
            return heading
    return None


def _next_html_boundary(headings: tuple[Any, ...], index: int, level: int) -> Any | None:
    for heading in headings[index + 1 :]:
        if heading.level <= level:
            return heading
    return None


class _VisibleTextParser(HTMLParser):
    """Extract visible text from one HTML section without changing source bytes."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def _visible_html_text(value: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(value)
    parser.close()
    return " ".join("".join(parser.parts).split())


def _line_keys(sections: Iterable[Any]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for section in sections:
        owner = str(getattr(section, "owner_document_id", getattr(section, "document_id", "")))
        tokens = getattr(section, "line_tokens", None)
        if tokens is None:
            tokens = (str(getattr(section, "line", "")),)
        keys.update((owner, str(token).lower()) for token in tokens if str(token).strip())
    return keys


def _first_by_line(sections: Iterable[PilotSection]) -> dict[tuple[str, str], PilotSection]:
    result: dict[tuple[str, str], PilotSection] = {}
    for section in sections:
        for token in section.line_tokens:
            result.setdefault((section.owner_document_id, token), section)
    return result


def _heading_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _default_document_id(source_document_id: str) -> str:
    return source_document_id.removeprefix("instructions_")


def _year_from_document(document_id: str) -> str:
    match = re.search(r"_(20[0-9]{2})$", document_id)
    return match.group(1) if match else "2025"


def _clean_heading(value: str) -> str:
    return re.sub(r"(?:\*\*|__)", "", value).strip()


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for index, char in enumerate(text):
        if char == "\n":
            starts.append(index + 1)
    return starts


def _line_sort_key(value: str) -> tuple[int, str]:
    match = re.fullmatch(r"([0-9]+)([a-z]?)", value.lower())
    if not match:
        return (10**9, value.lower())
    return (int(match.group(1)), match.group(2))


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "source"


def main(argv: list[str] | None = None) -> int:
    """Write the seven-document pilot measurement report."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=Path(".cache/raw/2025"))
    parser.add_argument("--year", default="2025")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = measure_corpus(args.raw_root, year=args.year)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    for document_id, data in report["documents"].items():
        counts = data["counts"]
        phantoms = data["phantom_anchors"]["ocr_with_fixes"]
        print(
            f"{document_id}: OCR today {counts['ocr_today']}, "
            f"OCR with fixes {counts['ocr_with_fixes']}, HTML {counts['html']}, "
            f"fixed phantoms {len(phantoms)}"
        )
    print(f"report written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
