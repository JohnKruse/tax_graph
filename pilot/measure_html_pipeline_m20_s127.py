"""Measure IRS HTML structure and instruction ownership against the PDF pipeline.

This is an offline M20-S127 pilot.  It reads acquired HTML and PDF text, the
manifest, the reconciliation population, and already-recorded model frames.
It does not call a provider, fetch a URL, alter production extraction, or
write graph artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import argparse
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

import yaml

from pilot.model_instruction_segmenter import build_frame_from_fixture
from pilot.model_instruction_segmenter import manifest_owner_document_ids
from tax_graph.acquire.manifest import load_manifest
from tax_graph.extract.instruction_sections import build_instruction_sections_file


ROOT = Path(__file__).resolve().parents[1]
YEAR = "2025"
BOOKLET_IDS = (
    "instructions_form_1040_2025",
    "instructions_form_1116_2025",
    "instructions_form_2441_2025",
    "instructions_form_6251_2025",
    "instructions_form_8949_2025",
    "instructions_schedule_a_2025",
    "instructions_schedule_b_2025",
    "instructions_schedule_d_2025",
)
MODEL_FIXTURES = {
    "instructions_form_1040_2025": "pilot/fixtures/instruction_segmenter_live_1040.json",
    "instructions_schedule_b_2025": "pilot/fixtures/instruction_segmenter_live_recordings.json",
    "instructions_schedule_d_2025": "pilot/fixtures/instruction_segmenter_live_recordings.json",
}
_LINE_RE = re.compile(r"^\s*lines?\s+(.+)$", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[0-9]+[a-z]?", re.IGNORECASE)
_PUBLINK_RE = re.compile(r"publink", re.IGNORECASE)
_ROLE_RE = re.compile(r"^role-hd", re.IGNORECASE)


@dataclass(frozen=True)
class HtmlAnchor:
    """One body ``publink`` target and its source location."""

    anchor_id: str
    title: str
    tag: str
    start_offset: int
    end_offset: int

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe anchor record."""
        return {
            "anchor_id": self.anchor_id,
            "title": self.title,
            "tag": self.tag,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
        }


@dataclass(frozen=True)
class HtmlTocEntry:
    """One nested table-of-contents link."""

    anchor_id: str
    title: str
    depth: int
    start_offset: int
    end_offset: int

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe table-of-contents record."""
        return {
            "anchor_id": self.anchor_id,
            "title": self.title,
            "depth": self.depth,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
        }


@dataclass(frozen=True)
class HtmlHeading:
    """One semantic HTML heading, including its role class when present."""

    level: int
    title: str
    anchor_id: str | None
    role_class: str | None
    start_offset: int
    end_offset: int

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe heading record."""
        return {
            "level": self.level,
            "title": self.title,
            "anchor_id": self.anchor_id,
            "role_class": self.role_class,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
        }


@dataclass(frozen=True)
class HtmlInlineHeading:
    """One bold run-in label marked with the IRS ``inlinehd`` class."""

    title: str
    anchor_id: str | None
    start_offset: int
    end_offset: int

    @property
    def line_tokens(self) -> tuple[str, ...]:
        """Return the printed line tokens named by this run-in label."""
        return _line_tokens(self.title)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe inline heading record."""
        return {
            "title": self.title,
            "anchor_id": self.anchor_id,
            "line_tokens": list(self.line_tokens),
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
        }


@dataclass(frozen=True)
class HtmlSection:
    """One line-bearing HTML section used by the deterministic arm."""

    section_id: str
    owner_document_id: str
    anchor_id: str | None
    heading: str
    line_tokens: tuple[str, ...]
    start_offset: int
    end_offset: int
    source_text: str

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe section record."""
        return {
            "section_id": self.section_id,
            "owner_document_id": self.owner_document_id,
            "anchor_id": self.anchor_id,
            "heading": self.heading,
            "line_tokens": list(self.line_tokens),
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "source_text": self.source_text,
        }


@dataclass(frozen=True)
class HtmlStructure:
    """All measured structural records for one acquired HTML booklet."""

    source_document_id: str
    source_text: str
    anchors: tuple[HtmlAnchor, ...]
    toc_entries: tuple[HtmlTocEntry, ...]
    headings: tuple[HtmlHeading, ...]
    inline_headings: tuple[HtmlInlineHeading, ...]
    role_headings: tuple[HtmlHeading, ...]
    sections: tuple[HtmlSection, ...]
    structural_invariants: dict[str, Any]

    def as_dict(self, *, include_source: bool = False) -> dict[str, Any]:
        """Return the structural report without copying HTML by default."""
        result = {
            "source_document_id": self.source_document_id,
            "source_length": len(self.source_text),
            "anchors": [item.as_dict() for item in self.anchors],
            "toc_entries": [item.as_dict() for item in self.toc_entries],
            "headings": [item.as_dict() for item in self.headings],
            "inline_headings": [item.as_dict() for item in self.inline_headings],
            "role_headings": [item.as_dict() for item in self.role_headings],
            "sections": [item.as_dict() for item in self.sections],
            "structural_invariants": dict(self.structural_invariants),
        }
        if include_source:
            result["source_text"] = self.source_text
        return result


@dataclass
class _Element:
    """Internal HTML element capture state."""

    tag: str
    attrs: dict[str, str]
    start_offset: int
    end_offset: int = 0
    target_id: str | None = None
    capture_kind: str | None = None
    parts: list[str] | None = None
    ul_depth: int = 0


class _StructureParser(HTMLParser):
    """Capture source offsets and the small set of IRS HTML conventions."""

    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self._line_starts = [0]
        self._line_starts.extend(
            index + 1 for index, char in enumerate(source) if char == "\n"
        )
        self.stack: list[_Element] = []
        self.target_occurrences: list[tuple[str, str, int, int, str]] = []
        self.toc_entries: list[HtmlTocEntry] = []
        self.headings: list[HtmlHeading] = []
        self.inline_headings: list[HtmlInlineHeading] = []

    def _offset(self) -> int:
        line, column = self.getpos()
        return self._line_starts[line - 1] + column

    def _end_offset(self) -> int:
        start = self._offset()
        close = self.source.find(">", start)
        return close + 1 if close >= 0 else start

    def _ancestor_target(self) -> str | None:
        for element in reversed(self.stack):
            if element.target_id is not None:
                return element.target_id
        return None

    @staticmethod
    def _class_tokens(attrs: Mapping[str, str]) -> set[str]:
        return set(str(attrs.get("class") or "").split())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        attributes = {
            str(key).lower(): str(value or "") for key, value in attrs
        }
        start = self._offset()
        target_id = None
        if normalized_tag == "a":
            candidate = attributes.get("name", "")
            if _PUBLINK_RE.search(candidate):
                target_id = candidate
        elif normalized_tag == "div":
            candidate = attributes.get("id", "")
            if _PUBLINK_RE.search(candidate):
                target_id = candidate

        classes = self._class_tokens(attributes)
        capture_kind: str | None = None
        if normalized_tag == "a" and attributes.get("href", "").startswith("#"):
            target = attributes["href"][1:]
            if _PUBLINK_RE.search(target) and "text-overflow" in classes:
                capture_kind = "toc"
        if "inlinehd" in classes:
            capture_kind = "inline"
        heading_match = re.fullmatch(r"h([1-6])", normalized_tag)
        if heading_match:
            capture_kind = "heading"

        element = _Element(
            tag=normalized_tag,
            attrs=attributes,
            start_offset=start,
            target_id=target_id,
            capture_kind=capture_kind,
            parts=[] if capture_kind is not None else None,
            ul_depth=sum(item.tag == "ul" for item in self.stack) + (normalized_tag == "ul"),
        )
        self.stack.append(element)
        if target_id is not None:
            self.target_occurrences.append((target_id, normalized_tag, start, 0, ""))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        index = len(self.stack) - 1
        while index >= 0 and self.stack[index].tag != normalized_tag:
            index -= 1
        if index < 0:
            return
        element = self.stack[index]
        del self.stack[index:]
        element.end_offset = self._end_offset()
        text = _clean_text("".join(element.parts or []))
        if element.capture_kind == "toc":
            target = element.attrs.get("href", "")[1:]
            self.toc_entries.append(
                HtmlTocEntry(
                    anchor_id=target,
                    title=text,
                    depth=element.ul_depth,
                    start_offset=element.start_offset,
                    end_offset=element.end_offset,
                )
            )
        elif element.capture_kind == "heading":
            level = int(normalized_tag[1:])
            role_class = next(
                (
                    token
                    for token in self._class_tokens(element.attrs)
                    if _ROLE_RE.match(token)
                ),
                None,
            )
            self.headings.append(
                HtmlHeading(
                    level=level,
                    title=text,
                    anchor_id=None,
                    role_class=role_class,
                    start_offset=element.start_offset,
                    end_offset=element.end_offset,
                )
            )
        elif element.capture_kind == "inline":
            self.inline_headings.append(
                HtmlInlineHeading(
                    title=text,
                    anchor_id=self._ancestor_target_before(index),
                    start_offset=element.start_offset,
                    end_offset=element.end_offset,
                )
            )

        if element.target_id is not None:
            for occurrence_index in range(len(self.target_occurrences) - 1, -1, -1):
                target, occurrence_tag, start, end, title = self.target_occurrences[occurrence_index]
                if target == element.target_id and occurrence_tag == element.tag and start == element.start_offset and end == 0:
                    self.target_occurrences[occurrence_index] = (
                        target,
                        occurrence_tag,
                        start,
                        element.end_offset,
                        text,
                    )
                    break

    def _ancestor_target_before(self, stack_index: int) -> str | None:
        for element in reversed(self.stack[:stack_index]):
            if element.target_id is not None:
                return element.target_id
        return None

    def handle_data(self, data: str) -> None:
        if not data:
            return
        for element in self.stack:
            if element.parts is not None:
                element.parts.append(data)


def parse_html_structure(html_text: str, *, source_document_id: str) -> HtmlStructure:
    """Extract the HTML structure and line-bearing deterministic sections."""
    parser = _StructureParser(html_text)
    parser.feed(html_text)
    parser.close()

    raw_occurrences = parser.target_occurrences
    anchors_by_id: dict[str, HtmlAnchor] = {}
    duplicate_ids: set[str] = set()
    sorted_occurrences = sorted(raw_occurrences, key=lambda item: item[2])
    for occurrence_index, (anchor_id, tag, start, end, raw_title) in enumerate(
        sorted_occurrences
    ):
        if anchor_id in anchors_by_id:
            duplicate_ids.add(anchor_id)
            continue
        next_start = (
            sorted_occurrences[occurrence_index + 1][2]
            if occurrence_index + 1 < len(sorted_occurrences)
            else len(html_text)
        )
        title = _anchor_title(
            anchor_id,
            raw_title,
            start,
            end,
            parser.headings,
            parser.inline_headings,
            parser.toc_entries,
        )
        if not title:
            title = _nearby_title(html_text, start, next_start)
        anchors_by_id[anchor_id] = HtmlAnchor(
            anchor_id=anchor_id,
            title=title,
            tag=tag,
            start_offset=start,
            end_offset=end,
        )

    anchors = tuple(sorted(anchors_by_id.values(), key=lambda item: item.start_offset))
    headings = tuple(_attach_heading_anchors(parser.headings, raw_occurrences))
    inline_headings = tuple(
        _attach_inline_anchors(parser.inline_headings, raw_occurrences)
    )
    role_headings = tuple(item for item in headings if item.role_class is not None)
    sections = _build_html_sections(
        html_text,
        source_document_id=source_document_id,
        anchors=anchors,
        headings=headings,
        inline_headings=inline_headings,
    )
    anchor_ids = {item.anchor_id for item in anchors}
    toc_targets = {item.anchor_id for item in parser.toc_entries}
    section_offsets_valid = all(
        0 <= item.start_offset < item.end_offset <= len(html_text)
        for item in sections
    )
    sections_nonempty = all(_visible_text(item.source_text) for item in sections)
    invariants = {
        "anchor_ids_unique": not duplicate_ids,
        "toc_targets_exist": toc_targets <= anchor_ids,
        "section_offsets_valid": section_offsets_valid,
        "sections_nonempty": sections_nonempty,
        "duplicate_anchor_ids": sorted(duplicate_ids),
        "missing_toc_targets": sorted(toc_targets - anchor_ids),
        "invalid_section_ids": [
            item.section_id for item in sections if not (0 <= item.start_offset < item.end_offset <= len(html_text))
        ],
        "empty_section_ids": [
            item.section_id for item in sections if not _visible_text(item.source_text)
        ],
    }
    return HtmlStructure(
        source_document_id=source_document_id,
        source_text=html_text,
        anchors=anchors,
        toc_entries=tuple(parser.toc_entries),
        headings=headings,
        inline_headings=inline_headings,
        role_headings=role_headings,
        sections=sections,
        structural_invariants=invariants,
    )


def measure_corpus(root: str | Path = ROOT) -> dict[str, Any]:
    """Compute the eight HTML inventories and the three-arm cell report."""
    root_path = Path(root).resolve()
    structures: dict[str, HtmlStructure] = {}
    for source_document_id in BOOKLET_IDS:
        path = root_path / ".cache" / "raw" / YEAR / f"{source_document_id}.html"
        if not path.is_file():
            raise FileNotFoundError(path)
        structures[source_document_id] = parse_html_structure(
            path.read_text(encoding="utf-8"),
            source_document_id=source_document_id,
        )

    cells = _load_cells(root_path)
    pdf_deterministic = _build_pdf_deterministic(root_path)
    pdf_model = _build_pdf_model(root_path)
    html_sections = {
        source_document_id: structure.sections
        for source_document_id, structure in structures.items()
    }
    documents = _score_documents(
        cells,
        pdf_deterministic=pdf_deterministic,
        pdf_model=pdf_model,
        html_sections=html_sections,
    )
    disagreements = _open_disagreements(
        root_path,
        cells,
        pdf_deterministic=pdf_deterministic,
        pdf_model=pdf_model,
        html_structures=structures,
    )
    return {
        "schema_version": 1,
        "round": "M20-S127",
        "year": YEAR,
        "source_policy": {
            "html": "acquired IRS HTML only; no network or provider call",
            "pdf_deterministic": "current build_instruction_sections on acquired PDF text",
            "pdf_model": "paid recordings replayed through the existing verified frame builder",
            "html_deterministic": "publink targets, role-hd headings, and inlinehd labels; no model",
        },
        "booklets": {
            source_document_id: structures[source_document_id].as_dict()
            for source_document_id in BOOKLET_IDS
        },
        "documents": documents,
        "disagreements": disagreements,
        "summary": {
            "booklet_count": len(structures),
            "document_count": len(documents),
            "cell_count": sum(item["cells"] for item in documents.values()),
            "disagreement_count": len(disagreements),
            "structural_invariants_hold": all(
                all(
                    bool(value)
                    for key, value in structure.structural_invariants.items()
                    if key.endswith(("unique", "exist", "valid", "nonempty"))
                )
                for structure in structures.values()
            ),
        },
    }


def _load_cells(root: Path) -> dict[str, list[dict[str, Any]]]:
    path = root / "plans" / "m20_s116_instruction_reconciliation.yaml"
    payload = yaml.safe_load(path.read_text(encoding="ascii")) or {}
    manifest = load_manifest(root=root)
    entries = manifest.by_document_id()
    result: dict[str, list[dict[str, Any]]] = {}
    for document_id, document in (payload.get("documents") or {}).items():
        entry = entries.get(document_id)
        if entry is None or entry.instructions_document_id not in BOOKLET_IDS:
            raise ValueError(f"cell document is not mapped to an HTML booklet: {document_id}")
        result[document_id] = [
            {
                "cell_id": str(cell.get("cell_id") or ""),
                "document_id": document_id,
                "line": str(cell.get("line") or "").strip().lower(),
                "booklet_id": entry.instructions_document_id,
            }
            for cell in document.get("cells", ())
        ]
    return result


def _build_pdf_deterministic(root: Path) -> dict[str, tuple[Any, ...]]:
    result: dict[str, tuple[Any, ...]] = {}
    for source_document_id in BOOKLET_IDS:
        path = root / ".cache" / "raw" / YEAR / f"{source_document_id}.txt"
        frame = build_instruction_sections_file(
            path,
            source_document_id=source_document_id,
            year=YEAR,
        )
        result[source_document_id] = tuple(frame.sections)
    return result


def _build_pdf_model(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for source_document_id, fixture in MODEL_FIXTURES.items():
        source_path = root / ".cache" / "raw" / YEAR / f"{source_document_id}.txt"
        fixture_path = root / fixture
        result[source_document_id] = build_frame_from_fixture(
            source_path,
            source_document_id=source_document_id,
            fixture_path=fixture_path,
            allowed_document_ids=manifest_owner_document_ids(
                root,
                source_document_id=source_document_id,
            ),
            root=root,
        )
    return result


def _score_documents(
    cells: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    pdf_deterministic: Mapping[str, Sequence[Any]],
    pdf_model: Mapping[str, Any],
    html_sections: Mapping[str, Sequence[HtmlSection]],
) -> dict[str, Any]:
    documents: dict[str, Any] = {}
    for document_id, document_cells in sorted(cells.items()):
        booklet_id = str(document_cells[0]["booklet_id"]) if document_cells else ""
        pdf_sections = pdf_deterministic.get(booklet_id, ())
        html_booklet_sections = html_sections.get(booklet_id, ())
        arms = {
            "pdf_deterministic": _score_arm(
                document_cells,
                _pdf_deterministic_keys(pdf_sections),
                section_count=len(pdf_sections),
            ),
            "html_deterministic": _score_arm(
                document_cells,
                _html_keys(html_booklet_sections),
                section_count=len(html_booklet_sections),
            ),
        }
        model_frame = pdf_model.get(booklet_id)
        if model_frame is None:
            arms["pdf_model"] = {
                "available": False,
                "correctly_owned": None,
                "cell_ids": [],
                "section_count": None,
                "reason": "no paid recording for this booklet",
            }
        else:
            arms["pdf_model"] = _score_arm(
                document_cells,
                _model_keys(model_frame.sections),
                section_count=len(model_frame.sections),
            )
        documents[document_id] = {
            "booklet_id": booklet_id,
            "cells": len(document_cells),
            "arms": arms,
        }
    return documents


def _score_arm(
    cells: Sequence[Mapping[str, Any]],
    keys: set[tuple[str, str]],
    *,
    section_count: int,
) -> dict[str, Any]:
    matched = sorted(
        str(cell["cell_id"])
        for cell in cells
        if (str(cell["document_id"]), str(cell["line"])) in keys
    )
    return {
        "available": True,
        "correctly_owned": len(matched),
        "cell_ids": matched,
        "section_count": section_count,
    }


def _pdf_deterministic_keys(sections: Sequence[Any]) -> set[tuple[str, str]]:
    return {
        (str(section.document_id), str(section.line).lower())
        for section in sections
    }


def _model_keys(sections: Sequence[Any]) -> set[tuple[str, str]]:
    return {
        (str(section.document_id), str(token).lower())
        for section in sections
        for token in section.governs
        if _TOKEN_RE.fullmatch(str(token).strip())
    }


def _html_keys(sections: Sequence[HtmlSection]) -> set[tuple[str, str]]:
    return {
        (section.owner_document_id, token.lower())
        for section in sections
        for token in section.line_tokens
    }


def _open_disagreements(
    root: Path,
    cells: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    pdf_deterministic: Mapping[str, Sequence[Any]],
    pdf_model: Mapping[str, Any],
    html_structures: Mapping[str, HtmlStructure],
) -> list[dict[str, Any]]:
    """Return cell-level disagreements with source quotes, not just counts."""
    result: list[dict[str, Any]] = []
    for document_id, document_cells in sorted(cells.items()):
        booklet_id = str(document_cells[0]["booklet_id"]) if document_cells else ""
        txt_path = root / ".cache" / "raw" / YEAR / f"{booklet_id}.txt"
        txt_source = txt_path.read_bytes()
        html_source = html_structures[booklet_id].source_text
        for cell in document_cells:
            line = str(cell["line"])
            arm_matches: dict[str, list[dict[str, Any]] | None] = {
                "pdf_deterministic": _pdf_matches(
                    line,
                    document_id,
                    pdf_deterministic.get(booklet_id, ()),
                    txt_source,
                ),
                "html_deterministic": _html_matches(
                    line,
                    document_id,
                    html_structures[booklet_id].sections,
                    html_source,
                ),
            }
            model_frame = pdf_model.get(booklet_id)
            arm_matches["pdf_model"] = (
                _model_matches(line, document_id, model_frame.sections, txt_source)
                if model_frame is not None
                else None
            )
            answer_states = {
                arm: (
                    "unavailable"
                    if matches is None
                    else "matched"
                    if matches
                    else "no_match"
                )
                for arm, matches in arm_matches.items()
            }
            comparable_states = {
                arm: state
                for arm, state in answer_states.items()
                if state != "unavailable"
            }
            if len(set(comparable_states.values())) <= 1:
                continue
            result.append(
                {
                    "cell_id": cell["cell_id"],
                    "document_id": document_id,
                    "line": line,
                    "booklet_id": booklet_id,
                    "arms": arm_matches,
                    "answer_states": answer_states,
                }
            )
    return result


def _pdf_matches(
    line: str,
    document_id: str,
    sections: Sequence[Any],
    source_bytes: bytes,
) -> list[dict[str, Any]]:
    result = []
    for section in sections:
        if str(section.line).lower() != line:
            continue
        start = int(section.locator.start_offset)
        end = int(section.locator.end_offset)
        result.append(
            {
                "owner_document_id": str(section.document_id),
                "section_id": str(section.section_id),
                "heading": str(section.heading),
                "quote": _quote(source_bytes[start:end].decode("utf-8")),
                "locator": {"start_offset": start, "end_offset": end},
            }
        )
    return result


def _model_matches(
    line: str,
    document_id: str,
    sections: Sequence[Any],
    source_bytes: bytes,
) -> list[dict[str, Any]]:
    result = []
    for section in sections:
        if line not in {
            str(token).lower() for token in section.governs
        }:
            continue
        start = int(section.start_byte)
        end = int(section.end_byte)
        result.append(
            {
                "owner_document_id": str(section.document_id),
                "section_id": str(section.section_id),
                "heading": str(section.heading),
                "quote": _quote(source_bytes[start:end].decode("utf-8")),
                "locator": {"start_byte": start, "end_byte": end},
            }
        )
    return result


def _html_matches(
    line: str,
    document_id: str,
    sections: Sequence[HtmlSection],
    source_text: str,
) -> list[dict[str, Any]]:
    return [
        {
            "owner_document_id": section.owner_document_id,
            "section_id": section.section_id,
            "heading": section.heading,
            "quote": _quote(_visible_text(source_text[section.start_offset : section.end_offset])),
            "locator": {
                "start_offset": section.start_offset,
                "end_offset": section.end_offset,
            },
        }
        for section in sections
        if line in section.line_tokens
    ]


def _build_html_sections(
    source_text: str,
    *,
    source_document_id: str,
    anchors: Sequence[HtmlAnchor],
    headings: Sequence[HtmlHeading],
    inline_headings: Sequence[HtmlInlineHeading],
) -> tuple[HtmlSection, ...]:
    default_owner = _default_owner(source_document_id)
    events: list[tuple[int, str, Any]] = []
    events.extend((item.start_offset, "heading", item) for item in headings)
    events.extend((item.start_offset, "inline", item) for item in inline_headings)
    events.extend(
        (item.start_offset, "anchor", item)
        for item in anchors
        if _line_tokens(item.title)
    )
    events.sort(key=lambda item: item[0])
    current_owner = default_owner
    owner_by_offset: dict[int, str] = {}
    for offset, kind, item in events:
        if kind == "heading":
            context = _context_owner(item.title, default_owner, current_owner)
            if context is not None:
                current_owner = context
            owner_by_offset[offset] = current_owner

    sections: list[HtmlSection] = []
    seen: set[tuple[str | None, tuple[str, ...], int]] = set()
    for offset, kind, item in events:
        line_tokens = (
            item.line_tokens if kind == "inline" else _line_tokens(item.title)
        )
        if not line_tokens:
            continue
        owner = _owner_at_offset(offset, owner_by_offset, default_owner)
        if kind == "anchor":
            anchor_id = item.anchor_id
            heading = item.title
            containing_heading = next(
                (
                    candidate
                    for candidate in headings
                    if candidate.anchor_id == anchor_id
                    and candidate.start_offset <= item.start_offset < candidate.end_offset
                ),
                None,
            )
            start = (
                containing_heading.start_offset
                if containing_heading is not None
                else item.start_offset
            )
            end = (
                containing_heading.end_offset
                if containing_heading is not None
                else item.end_offset
            )
            source_slice = source_text[start:end]
        else:
            start = item.start_offset
            end = item.end_offset
            anchor_id = item.anchor_id
            heading = item.title
            source_slice = source_text[start:end]
        key = (anchor_id, tuple(line_tokens), start)
        if key in seen:
            continue
        seen.add(key)
        sections.append(
            HtmlSection(
                section_id=f"html_{_slug(source_document_id)}_{len(sections) + 1:04d}",
                owner_document_id=owner,
                anchor_id=anchor_id,
                heading=heading,
                line_tokens=tuple(line_tokens),
                start_offset=start,
                end_offset=end,
                source_text=source_slice,
            )
        )
    return tuple(sections)


def _attach_heading_anchors(
    headings: Sequence[HtmlHeading],
    occurrences: Sequence[tuple[str, str, int, int, str]],
) -> list[HtmlHeading]:
    return [
        HtmlHeading(
            level=item.level,
            title=item.title,
            anchor_id=_first_nested_anchor(item.start_offset, item.end_offset, occurrences),
            role_class=item.role_class,
            start_offset=item.start_offset,
            end_offset=item.end_offset,
        )
        for item in headings
    ]


def _attach_inline_anchors(
    headings: Sequence[HtmlInlineHeading],
    occurrences: Sequence[tuple[str, str, int, int, str]],
) -> list[HtmlInlineHeading]:
    return [
        HtmlInlineHeading(
            title=item.title,
            anchor_id=item.anchor_id
            or _first_nested_anchor(item.start_offset, item.end_offset, occurrences),
            start_offset=item.start_offset,
            end_offset=item.end_offset,
        )
        for item in headings
    ]


def _first_nested_anchor(
    start: int,
    end: int,
    occurrences: Sequence[tuple[str, str, int, int, str]],
) -> str | None:
    nested = [item for item in occurrences if start <= item[2] < end]
    return min(nested, key=lambda item: item[2])[0] if nested else None


def _anchor_title(
    anchor_id: str,
    raw_title: str,
    start: int,
    end: int,
    headings: Sequence[HtmlHeading],
    inline_headings: Sequence[HtmlInlineHeading],
    toc_entries: Sequence[HtmlTocEntry],
) -> str:
    nested_headings = [
        item.title
        for item in headings
        if start <= item.start_offset < max(end, start + 1)
    ]
    if nested_headings:
        return nested_headings[0]
    following_headings = [
        item.title
        for item in headings
        if start <= item.start_offset <= start + 2000
    ]
    if following_headings:
        return following_headings[0]
    nested_inline = [
        item.title
        for item in inline_headings
        if item.anchor_id == anchor_id
    ]
    if nested_inline:
        return nested_inline[0]
    if raw_title:
        return raw_title
    toc_titles = [item.title for item in toc_entries if item.anchor_id == anchor_id]
    return toc_titles[0] if toc_titles else ""


def _context_owner(
    title: str,
    default_owner: str,
    current_owner: str,
) -> str | None:
    normalized = re.sub(r"\s+", " ", title).strip().lower()
    if "line instructions for forms 1040" in normalized:
        return "form_1040_2025"
    schedule = re.search(
        r"\binstructions for schedule\s+([0-9]+(?:-?[a-z])?|[a-z])",
        normalized,
    )
    if schedule:
        return f"schedule_{schedule.group(1).replace('-', '')}_2025"
    form = re.search(r"\binstructions for form\s+([0-9]+[a-z]?)", normalized)
    if form:
        return f"form_{form.group(1)}_2025"
    if default_owner == "form_1040_2025" and normalized == "additional income and adjustments to income":
        return "schedule_1_2025"
    return current_owner


def _owner_at_offset(offset: int, owners: Mapping[int, str], default: str) -> str:
    prior = [position for position in owners if position <= offset]
    return owners[max(prior)] if prior else default


def _default_owner(source_document_id: str) -> str:
    if source_document_id.startswith("instructions_"):
        return source_document_id[len("instructions_") :]
    return source_document_id


def _line_tokens(title: str) -> tuple[str, ...]:
    match = _LINE_RE.match(_clean_text(title))
    if not match:
        return ()
    remainder = match.group(1)
    first = _TOKEN_RE.match(remainder)
    if first is None:
        return ()
    tokens = [first.group(0).lower()]
    position = first.end()
    while True:
        connector = re.match(
            r"\s*(?:,\s*(?:and\s+)?|and\s+|through\s+|thru\s+|to\s+|or\s+)",
            remainder[position:],
            re.IGNORECASE,
        )
        if connector is None:
            break
        next_position = position + connector.end()
        next_token = _TOKEN_RE.match(remainder[next_position:])
        if next_token is None:
            break
        tokens.append(next_token.group(0).lower())
        position = next_position + next_token.end()
    return tuple(dict.fromkeys(tokens))


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _visible_text(value: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(value)
    parser.close()
    return _clean_text(parser.text)


class _VisibleTextParser(HTMLParser):
    """Strip tags while preserving the acquired source wording."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored = 0

    @property
    def text(self) -> str:
        return " ".join(self.parts)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style"}:
            self._ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self._ignored:
            self._ignored -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored:
            self.parts.append(data)


def _quote(value: str, limit: int = 320) -> str:
    cleaned = _clean_text(value)
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 3] + "..."


def _nearby_title(source_text: str, start: int, next_start: int) -> str:
    """Use the first visible body wording when a target has no heading title."""
    window_end = min(next_start, start + 5000)
    visible = _visible_text(source_text[start:window_end])
    return _quote(visible, limit=220)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def main(argv: Sequence[str] | None = None) -> int:
    """Write the computed M20-S127 measurement report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    report = measure_corpus(args.root)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
            encoding="ascii",
            newline="\n",
        )
    print(
        f"M20-S127: {report['summary']['booklet_count']} booklets, "
        f"{report['summary']['document_count']} documents, "
        f"{report['summary']['cell_count']} cells, "
        f"{report['summary']['disagreement_count']} disagreements"
    )
    for document_id, data in report["documents"].items():
        arms = data["arms"]
        values = ", ".join(
            f"{name}={arm['correctly_owned'] if arm['available'] else 'unavailable'}"
            for name, arm in arms.items()
        )
        print(f"{document_id}: cells={data['cells']}; {values}")
    for item in report["disagreements"][:8]:
        print(f"DISAGREEMENT {item['cell_id']}: line {item['line']}")
        for arm_name, matches in item["arms"].items():
            if matches is None:
                print(f"  {arm_name}: unavailable")
            elif not matches:
                print(f"  {arm_name}: no match")
            else:
                for match in matches[:2]:
                    print(f"  {arm_name}: {match['owner_document_id']} - {match['quote']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
