"""Build a containment-owned section frame from acquired IRS instruction HTML.

This is the provider-free M20-S128 pilot.  It reads only acquired HTML and the
existing manifest/reconciliation population.  It does not change production
extraction, call a model, fetch a URL, or write graph artifacts.

The IRS HTML carries two structural signals that the PDF text loses:
``role-hd1``/``role-hd2``/``role-hd3`` heading ancestry and ``inlinehd``
run-in labels.  A section keeps that ancestry and is owned by the nearest
manifest document named by an ancestor.  The published ``publink`` id is an
opaque address; all stored offsets are explicitly UTF-8 byte offsets.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
import argparse
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

import yaml

from pilot.model_instruction_segmenter import (
    manifest_owner_document_ids,
    manifest_worksheet_document_ids,
)
from tax_graph.acquire.manifest import load_manifest


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

_LINE_RE = re.compile(r"^lines?\s+(.+)$", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[0-9]+[a-z]?", re.IGNORECASE)
_ROLE_RE = re.compile(r"^role-hd([123])$", re.IGNORECASE)
_ROLE_LEVELS = {
    "role-major-section": 1,
    "role-intro": 1,
    "role-spcinstr": 1,
    "role-subsect": 2,
    "role-step-hd5": 6,
}
_PUBLINK_RE = re.compile(r"publink", re.IGNORECASE)
_DOCUMENT_RE = re.compile(
    r"\b(?:form|schedule)\s+[0-9]+[a-z]?\b(?:[- ]?[a-z])?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class HtmlAnchor:
    """One unique body ``publink`` target in source-byte coordinates."""

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
class HtmlHeading:
    """One role heading and its ancestor titles."""

    level: int
    title: str
    role_class: str
    anchor_id: str | None
    start_offset: int
    end_offset: int
    ancestor_chain: tuple[str, ...]
    ancestor_anchor_ids: tuple[str | None, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe heading record."""
        return {
            "level": self.level,
            "title": self.title,
            "role_class": self.role_class,
            "anchor_id": self.anchor_id,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "ancestor_chain": list(self.ancestor_chain),
            "ancestor_anchor_ids": list(self.ancestor_anchor_ids),
        }


@dataclass(frozen=True)
class HtmlSection:
    """One line-bearing section owned from the HTML heading tree."""

    section_id: str
    owner_document_id: str
    owner_source: str
    anchor_id: str | None
    heading: str
    line_tokens: tuple[str, ...]
    ancestor_chain: tuple[str, ...]
    ancestor_anchor_ids: tuple[str | None, ...]
    start_offset: int
    end_offset: int
    source_text: str
    claim_kind: str
    line_anchored: bool
    topic_attributed: bool

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe section record."""
        return {
            "section_id": self.section_id,
            "owner_document_id": self.owner_document_id,
            "owner_source": self.owner_source,
            "anchor_id": self.anchor_id,
            "heading": self.heading,
            "line_tokens": list(self.line_tokens),
            "ancestor_chain": list(self.ancestor_chain),
            "ancestor_anchor_ids": list(self.ancestor_anchor_ids),
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "source_text": self.source_text,
            "claim_kind": self.claim_kind,
            "line_anchored": self.line_anchored,
            "topic_attributed": self.topic_attributed,
        }


@dataclass(frozen=True)
class HtmlSectionRejection:
    """One section-local ownership rejection."""

    heading: str
    reason: str
    foreign_document_id: str | None
    foreign_heading: str
    ancestor_chain: tuple[str, ...]
    anchor_id: str | None
    start_offset: int
    end_offset: int

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe rejection record."""
        return {
            "heading": self.heading,
            "reason": self.reason,
            "foreign_document_id": self.foreign_document_id,
            "foreign_heading": self.foreign_heading,
            "ancestor_chain": list(self.ancestor_chain),
            "anchor_id": self.anchor_id,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
        }


@dataclass(frozen=True)
class HtmlSectionFrame:
    """The complete offline frame for one acquired instruction booklet."""

    schema_version: int
    source_document_id: str
    source_length_bytes: int
    source_sha256: str
    offset_coordinate_space: str
    owner_document_ids: tuple[str, ...]
    worksheet_document_ids: tuple[str, ...]
    anchors: tuple[HtmlAnchor, ...]
    headings: tuple[HtmlHeading, ...]
    sections: tuple[HtmlSection, ...]
    rejected_sections: tuple[HtmlSectionRejection, ...]
    structural_invariants: dict[str, Any]
    score: dict[str, Any]

    def as_dict(self, *, include_source: bool = False, source_text: str = "") -> dict[str, Any]:
        """Return a JSON-safe frame without copying source HTML by default."""
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "source_document_id": self.source_document_id,
            "source_length_bytes": self.source_length_bytes,
            "source_sha256": self.source_sha256,
            "offset_coordinate_space": self.offset_coordinate_space,
            "owner_document_ids": list(self.owner_document_ids),
            "worksheet_document_ids": list(self.worksheet_document_ids),
            "anchors": [item.as_dict() for item in self.anchors],
            "headings": [item.as_dict() for item in self.headings],
            "sections": [item.as_dict() for item in self.sections],
            "rejected_sections": [item.as_dict() for item in self.rejected_sections],
            "structural_invariants": dict(self.structural_invariants),
            "score": dict(self.score),
        }
        if include_source:
            result["source_text"] = source_text
        return result


@dataclass
class _OpenElement:
    """Internal HTML parser state."""

    tag: str
    attrs: dict[str, str]
    start_char: int
    target_id: str | None = None
    capture_kind: str | None = None
    parts: list[str] | None = None
    container_target_id: str | None = None


@dataclass(frozen=True)
class _RawTarget:
    """An un-deduplicated target captured while parsing HTML."""

    anchor_id: str
    tag: str
    start_char: int
    end_char: int
    title: str


@dataclass(frozen=True)
class _RawHeading:
    """A role heading before ancestry and anchor binding."""

    level: int
    title: str
    role_class: str
    start_char: int
    end_char: int
    anchor_id: str | None


@dataclass(frozen=True)
class _RawInline:
    """An inline heading before ancestry and extent binding."""

    title: str
    start_char: int
    end_char: int
    container_target_id: str | None
    anchor_id: str | None


@dataclass(frozen=True)
class _RawBodySection:
    """A body section container used to widen claims to their source text."""

    start_char: int
    end_char: int
    target_id: str | None


class _HtmlFrameParser(HTMLParser):
    """Capture only body anchors, role headings, inline headings, and sections."""

    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self._line_starts = [0]
        self._line_starts.extend(index + 1 for index, char in enumerate(source) if char == "\n")
        self.stack: list[_OpenElement] = []
        self.targets: list[_RawTarget] = []
        self.headings: list[_RawHeading] = []
        self.inline_headings: list[_RawInline] = []
        self.body_sections: list[_RawBodySection] = []

    def _offset(self) -> int:
        line, column = self.getpos()
        return self._line_starts[line - 1] + column

    def _tag_end(self, start: int) -> int:
        close = self.source.find(">", start)
        return close + 1 if close >= 0 else start

    @staticmethod
    def _classes(attrs: Mapping[str, str]) -> set[str]:
        return set(str(attrs.get("class") or "").split())

    def _nearest_container(self) -> str | None:
        for element in reversed(self.stack):
            if element.tag == "div" and element.target_id is not None:
                return element.target_id
        return None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        attributes = {str(key).lower(): str(value or "") for key, value in attrs}
        start = self._offset()
        target_id: str | None = None
        if normalized_tag == "a":
            candidate = attributes.get("name", "")
            if _PUBLINK_RE.search(candidate):
                target_id = candidate
        elif normalized_tag == "div":
            candidate = attributes.get("id", "")
            if _PUBLINK_RE.search(candidate):
                target_id = candidate

        classes = self._classes(attributes)
        capture_kind: str | None = None
        role_level, role_class = _heading_role(classes)
        if role_level is not None:
            capture_kind = "heading"
        elif "inlinehd" in classes:
            capture_kind = "inline"

        element = _OpenElement(
            tag=normalized_tag,
            attrs=attributes,
            start_char=start,
            target_id=target_id,
            capture_kind=capture_kind,
            parts=[] if capture_kind is not None or target_id is not None else None,
            container_target_id=self._nearest_container(),
        )
        self.stack.append(element)
        if target_id is not None:
            self.targets.append(_RawTarget(target_id, normalized_tag, start, 0, ""))

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
        while len(self.stack) - 1 > index:
            self._finish(self.stack.pop())
        self._finish(self.stack.pop())

    def _finish(self, element: _OpenElement) -> None:
        end = self._tag_end(self._offset())
        text = _clean_text("".join(element.parts or []))
        if element.capture_kind == "heading":
            role_level, role_class = _heading_role(self._classes(element.attrs))
            if role_level is None or role_class is None:  # pragma: no cover - start tag selected it.
                return
            self.headings.append(
                _RawHeading(role_level, text, role_class, element.start_char, end, None)
            )
        elif element.capture_kind == "inline":
            self.inline_headings.append(
                _RawInline(
                    text,
                    element.start_char,
                    end,
                    element.container_target_id,
                    None,
                )
            )
        if element.tag == "div" and "section" in self._classes(element.attrs):
            self.body_sections.append(
                _RawBodySection(element.start_char, end, element.target_id)
            )
        if element.target_id is not None:
            for index in range(len(self.targets) - 1, -1, -1):
                target = self.targets[index]
                if (
                    target.anchor_id == element.target_id
                    and target.tag == element.tag
                    and target.start_char == element.start_char
                    and target.end_char == 0
                ):
                    self.targets[index] = _RawTarget(
                        target.anchor_id,
                        target.tag,
                        target.start_char,
                        end,
                        text,
                    )
                    break

    def handle_data(self, data: str) -> None:
        if not data:
            return
        for element in self.stack:
            if element.parts is not None:
                element.parts.append(data)


def parse_html_section_frame(
    html_text: str,
    *,
    source_document_id: str,
    root: str | Path = ROOT,
    owner_document_ids: Iterable[str] | None = None,
    worksheet_document_ids: Iterable[str] | None = None,
    all_manifest_document_ids: Iterable[str] | None = None,
) -> HtmlSectionFrame:
    """Build one containment-owned frame from acquired HTML text.

    The optional vocabularies are test seams.  Production callers use the
    manifest helpers, so this pilot cannot invent a second owner vocabulary.
    """
    root_path = Path(root).resolve()
    owners = frozenset(
        str(value).strip()
        for value in (
            owner_document_ids
            if owner_document_ids is not None
            else manifest_owner_document_ids(root_path, source_document_id=source_document_id)
        )
        if str(value).strip()
    )
    worksheets = frozenset(
        str(value).strip()
        for value in (
            worksheet_document_ids
            if worksheet_document_ids is not None
            else manifest_worksheet_document_ids(root_path, source_document_id=source_document_id)
        )
        if str(value).strip()
    )
    manifest = load_manifest(root=root_path) if all_manifest_document_ids is None else None
    all_ids = frozenset(
        str(value).strip()
        for value in (
            all_manifest_document_ids
            if all_manifest_document_ids is not None
            else (entry.document_id for entry in manifest.documents)
        )
        if str(value).strip()
    )
    aliases = _document_aliases(root_path, owners | all_ids)
    parser = _HtmlFrameParser(html_text)
    parser.feed(html_text)
    parser.close()
    source_bytes = html_text.encode("utf-8")
    byte_offsets = _byte_offsets(html_text)

    raw_targets = sorted(parser.targets, key=lambda item: item.start_char)
    duplicate_ids = sorted(
        anchor_id
        for anchor_id in {item.anchor_id for item in raw_targets}
        if sum(item.anchor_id == anchor_id for item in raw_targets) > 1
    )
    anchors: list[HtmlAnchor] = []
    seen_anchor_ids: set[str] = set()
    for target in raw_targets:
        if target.anchor_id in seen_anchor_ids:
            continue
        seen_anchor_ids.add(target.anchor_id)
        anchors.append(
            HtmlAnchor(
                anchor_id=target.anchor_id,
                title=target.title,
                tag=target.tag,
                start_offset=byte_offsets[target.start_char],
                end_offset=byte_offsets[target.end_char],
            )
        )

    raw_headings = sorted(parser.headings, key=lambda item: item.start_char)
    headings = _build_heading_tree(raw_headings, raw_targets, byte_offsets)
    raw_inlines = sorted(parser.inline_headings, key=lambda item: item.start_char)
    body_sections = tuple(sorted(parser.body_sections, key=lambda item: item.start_char))
    claims = _build_claims(raw_headings, raw_inlines, raw_targets, body_sections, html_text)

    sections: list[HtmlSection] = []
    rejected: list[HtmlSectionRejection] = []
    seen_claims: set[tuple[str | None, tuple[str, ...], int]] = set()
    for claim in claims:
        key = (claim.anchor_id, claim.line_tokens, claim.start_char)
        if key in seen_claims:
            continue
        seen_claims.add(key)
        ancestor_nodes = _ancestor_nodes(raw_headings, claim.context_char)
        if (
            claim.claim_kind == "role_heading"
            and ancestor_nodes
            and ancestor_nodes[-1].start_char == claim.context_char
        ):
            ancestor_nodes = ancestor_nodes[:-1]
        ancestor_chain = tuple(node.title for node in ancestor_nodes)
        ancestor_anchor_ids = tuple(
            _first_nested_anchor(node.start_char, node.end_char, raw_targets)
            for node in ancestor_nodes
        )
        owner = _resolve_owner(
            ancestor_chain,
            source_document_id=source_document_id,
            owner_document_ids=owners,
            all_manifest_document_ids=all_ids,
            aliases=aliases,
        )
        start = byte_offsets[claim.start_char]
        end = byte_offsets[claim.end_char]
        if owner.foreign_heading:
            rejected.append(
                HtmlSectionRejection(
                    heading=claim.heading,
                    reason="foreign_owner_rejected",
                    foreign_document_id=owner.foreign_document_id,
                    foreign_heading=owner.foreign_heading,
                    ancestor_chain=ancestor_chain,
                    anchor_id=claim.anchor_id,
                    start_offset=start,
                    end_offset=end,
                )
            )
            continue
        section = HtmlSection(
            section_id=f"html_{_slug(source_document_id)}_{len(sections) + 1:04d}",
            owner_document_id=owner.document_id,
            owner_source=owner.source,
            anchor_id=claim.anchor_id,
            heading=claim.heading,
            line_tokens=claim.line_tokens,
            ancestor_chain=ancestor_chain,
            ancestor_anchor_ids=ancestor_anchor_ids,
            start_offset=start,
            end_offset=end,
            source_text=html_text[claim.start_char : claim.end_char],
            claim_kind=claim.claim_kind,
            line_anchored=claim.line_anchored,
            topic_attributed=claim.topic_attributed,
        )
        sections.append(section)

    source_ranges_resolve = all(
        source_bytes[item.start_offset : item.end_offset].decode("utf-8") == item.source_text
        for item in sections
    )
    anchors_ranges_resolve = all(
        0 <= item.start_offset <= item.end_offset <= len(source_bytes)
        for item in anchors
    )
    section_ranges_valid = all(
        0 <= item.start_offset < item.end_offset <= len(source_bytes)
        for item in sections
    )
    invariants = {
        "anchor_ids_unique": not duplicate_ids,
        "anchor_ranges_valid": anchors_ranges_resolve,
        "section_offsets_valid": section_ranges_valid,
        "section_source_resolves": source_ranges_resolve,
        "sections_nonempty": all(_visible_text(item.source_text) for item in sections),
        "ancestor_chain_present": all(
            isinstance(item.ancestor_chain, tuple) for item in sections
        ),
        "duplicate_anchor_ids": duplicate_ids,
        "invalid_section_ids": [
            item.section_id for item in sections if not (0 <= item.start_offset < item.end_offset <= len(source_bytes))
        ],
        "empty_section_ids": [
            item.section_id for item in sections if not _visible_text(item.source_text)
        ],
    }
    return HtmlSectionFrame(
        schema_version=1,
        source_document_id=source_document_id,
        source_length_bytes=len(source_bytes),
        source_sha256=sha256(source_bytes).hexdigest(),
        offset_coordinate_space="utf8_bytes_of_acquired_html",
        owner_document_ids=tuple(sorted(owners)),
        worksheet_document_ids=tuple(sorted(worksheets)),
        anchors=tuple(anchors),
        headings=tuple(headings),
        sections=tuple(sections),
        rejected_sections=tuple(rejected),
        structural_invariants=invariants,
        score={
            "line_anchored_sections": sum(item.line_anchored for item in sections),
            "topic_attributed_sections": sum(item.topic_attributed for item in sections),
            "foreign_owner_rejected_sections": len(rejected),
        },
    )


@dataclass(frozen=True)
class _OwnerResolution:
    """Internal owner result."""

    document_id: str
    source: str
    foreign_document_id: str | None = None
    foreign_heading: str = ""


@dataclass(frozen=True)
class _Claim:
    """Internal line-bearing section claim."""

    heading: str
    line_tokens: tuple[str, ...]
    context_char: int
    start_char: int
    end_char: int
    anchor_id: str | None
    claim_kind: str
    line_anchored: bool
    topic_attributed: bool


def measure_corpus(root: str | Path = ROOT, *, year: str | int = YEAR) -> dict[str, Any]:
    """Build all eight frames and score the reconciliation population."""
    root_path = Path(root).resolve()
    booklet_frames: dict[str, HtmlSectionFrame] = {}
    for source_document_id in BOOKLET_IDS:
        path = root_path / ".cache" / "raw" / str(year) / f"{source_document_id}.html"
        if not path.is_file():
            raise FileNotFoundError(path)
        booklet_frames[source_document_id] = parse_html_section_frame(
            path.read_text(encoding="utf-8"),
            source_document_id=source_document_id,
            root=root_path,
        )
    cells = _load_cells(root_path)
    documents = _score_documents(cells, booklet_frames)
    return {
        "schema_version": 1,
        "round": "M20-S128",
        "year": str(year),
        "source_policy": {
            "html": "acquired IRS HTML only; no network or provider call",
            "ownership": "manifest owner vocabulary plus nearest heading containment",
            "anchors": "opaque IRS publink ids; not enumerated from the table of contents",
            "offsets": "UTF-8 byte offsets into the acquired HTML",
        },
        "booklets": {
            document_id: frame.as_dict()
            for document_id, frame in booklet_frames.items()
        },
        "documents": documents,
        "summary": {
            "booklet_count": len(booklet_frames),
            "document_count": len(documents),
            "cell_count": sum(item["cells"] for item in documents.values()),
            "structural_invariants_hold": all(
                all(
                    bool(value)
                    for key, value in frame.structural_invariants.items()
                    if key.endswith(("unique", "valid", "resolves", "nonempty", "present"))
                )
                for frame in booklet_frames.values()
            ),
        },
    }


def _load_cells(root: Path) -> dict[str, list[dict[str, str]]]:
    path = root / "plans" / "m20_s116_instruction_reconciliation.yaml"
    payload = yaml.safe_load(path.read_text(encoding="ascii")) or {}
    entries = load_manifest(root=root).by_document_id()
    result: dict[str, list[dict[str, str]]] = {}
    for document_id, document in (payload.get("documents") or {}).items():
        entry = entries.get(document_id)
        if entry is None:
            raise ValueError(f"reconciliation cell is absent from the manifest: {document_id}")
        result[document_id] = [
            {
                "cell_id": str(cell.get("cell_id") or ""),
                "document_id": str(document_id),
                "line": str(cell.get("line") or "").strip().lower(),
                "booklet_id": str(entry.instructions_document_id or ""),
            }
            for cell in document.get("cells", ())
        ]
    return result


def _score_documents(
    cells: Mapping[str, Sequence[Mapping[str, str]]],
    frames: Mapping[str, HtmlSectionFrame],
) -> dict[str, Any]:
    documents: dict[str, Any] = {}
    for document_id, document_cells in sorted(cells.items()):
        booklet_id = str(document_cells[0]["booklet_id"]) if document_cells else ""
        frame = frames.get(booklet_id)
        if frame is None:
            continue
        line_matches = {
            (section.owner_document_id, token): section
            for section in frame.sections
            for token in section.line_tokens
        }
        line_anchored_ids = sorted(
            cell["cell_id"]
            for cell in document_cells
            if (document_id, cell["line"]) in line_matches
            and line_matches[(document_id, cell["line"])].line_anchored
        )
        topic_attributed_ids = sorted(
            cell["cell_id"]
            for cell in document_cells
            if (document_id, cell["line"]) in line_matches
            and line_matches[(document_id, cell["line"])].topic_attributed
        )
        score = {
            "line_anchored": len(line_anchored_ids),
            "topic_attributed": len(topic_attributed_ids),
            "foreign_owner_rejected": len(frame.rejected_sections),
            "line_anchored_cell_ids": line_anchored_ids,
            "topic_attributed_cell_ids": topic_attributed_ids,
            "foreign_owner_rejected_section_count": len(frame.rejected_sections),
        }
        documents[document_id] = {
            "booklet_id": booklet_id,
            "cells": len(document_cells),
            "score": score,
            "line_anchored": score["line_anchored"],
            "topic_attributed": score["topic_attributed"],
            "foreign_owner_rejected": score["foreign_owner_rejected"],
        }
    return documents


def _build_heading_tree(
    raw_headings: Sequence[_RawHeading],
    raw_targets: Sequence[_RawTarget],
    byte_offsets: Sequence[int],
) -> list[HtmlHeading]:
    stack: list[_RawHeading] = []
    result: list[HtmlHeading] = []
    for raw in raw_headings:
        while stack and stack[-1].level >= raw.level:
            stack.pop()
        result.append(
            HtmlHeading(
                level=raw.level,
                title=raw.title,
                role_class=raw.role_class,
                anchor_id=_first_nested_anchor(raw.start_char, raw.end_char, raw_targets),
                start_offset=byte_offsets[raw.start_char],
                end_offset=byte_offsets[raw.end_char],
                ancestor_chain=tuple(item.title for item in stack),
                ancestor_anchor_ids=tuple(
                    _first_nested_anchor(item.start_char, item.end_char, raw_targets)
                    for item in stack
                ),
            )
        )
        stack.append(raw)
    return result


def _heading_role(classes: Iterable[str]) -> tuple[int | None, str | None]:
    """Return the semantic tree level for one IRS role class.

    The major-section and subsection classes are the owner-bearing parents
    around the ``role-hd1``/``role-hd2``/``role-hd3`` leaves.  Their levels are
    kept above the line-heading levels so a Schedule 1 owner remains in the
    chain when its nested line headings begin.
    """
    for class_name in classes:
        match = _ROLE_RE.fullmatch(class_name)
        if match:
            return 3 + int(match.group(1)) - 1, class_name
    for class_name in classes:
        if class_name in _ROLE_LEVELS:
            return _ROLE_LEVELS[class_name], class_name
    return None, None


def _build_claims(
    raw_headings: Sequence[_RawHeading],
    raw_inlines: Sequence[_RawInline],
    raw_targets: Sequence[_RawTarget],
    body_sections: Sequence[_RawBodySection],
    source_text: str,
) -> list[_Claim]:
    claims: list[_Claim] = []
    for heading in raw_headings:
        tokens = _line_tokens(heading.title)
        if not tokens:
            continue
        start, end, anchor_id = _claim_extent(
            heading.start_char,
            heading.end_char,
            None,
            raw_targets,
            body_sections,
        )
        claims.append(
            _Claim(
                heading=heading.title,
                line_tokens=tokens,
                context_char=heading.start_char,
                start_char=start,
                end_char=end,
                anchor_id=anchor_id,
                claim_kind="role_heading",
                line_anchored=True,
                topic_attributed=False,
            )
        )
    for inline in raw_inlines:
        tokens = _line_tokens(inline.title)
        if not tokens:
            continue
        start, end, anchor_id = _claim_extent(
            inline.start_char,
            inline.end_char,
            inline.container_target_id,
            raw_targets,
            body_sections,
        )
        claims.append(
            _Claim(
                heading=inline.title,
                line_tokens=tokens,
                context_char=inline.start_char,
                start_char=start,
                end_char=end,
                anchor_id=anchor_id,
                claim_kind="inline_heading",
                line_anchored=True,
                topic_attributed=False,
            )
        )
    for target in raw_targets:
        tokens = _line_tokens(target.title)
        if not tokens:
            continue
        start, end, anchor_id = _claim_extent(
            target.start_char,
            target.end_char,
            target.anchor_id,
            raw_targets,
            body_sections,
        )
        claims.append(
            _Claim(
                heading=target.title,
                line_tokens=tokens,
                context_char=target.start_char,
                start_char=start,
                end_char=end,
                anchor_id=anchor_id,
                claim_kind="body_anchor",
                line_anchored=False,
                topic_attributed=True,
            )
        )
    priority = {"role_heading": 0, "inline_heading": 1, "body_anchor": 2}
    return sorted(
        claims,
        key=lambda item: (item.start_char, item.end_char, priority.get(item.claim_kind, 9)),
    )


def _claim_extent(
    start_char: int,
    end_char: int,
    preferred_target_id: str | None,
    raw_targets: Sequence[_RawTarget],
    body_sections: Sequence[_RawBodySection],
) -> tuple[int, int, str | None]:
    candidates = [
        item
        for item in body_sections
        if item.start_char <= start_char and end_char <= item.end_char
    ]
    if preferred_target_id is not None:
        preferred = [item for item in candidates if item.target_id == preferred_target_id]
        if preferred:
            candidates = preferred
    container = min(candidates, key=lambda item: item.end_char - item.start_char) if candidates else None
    target_id = container.target_id if container and container.target_id else preferred_target_id
    if target_id is None:
        target_id = _first_nested_anchor(start_char, end_char, raw_targets)
    if container is not None:
        return container.start_char, container.end_char, target_id
    return start_char, end_char, target_id


def _ancestor_nodes(raw_headings: Sequence[_RawHeading], offset: int) -> list[_RawHeading]:
    stack: list[_RawHeading] = []
    for heading in raw_headings:
        if heading.start_char > offset:
            break
        while stack and stack[-1].level >= heading.level:
            stack.pop()
        stack.append(heading)
    return stack


def _resolve_owner(
    ancestor_chain: Sequence[str],
    *,
    source_document_id: str,
    owner_document_ids: frozenset[str],
    all_manifest_document_ids: frozenset[str],
    aliases: Mapping[str, tuple[str, ...]],
) -> _OwnerResolution:
    default_owner = _default_owner(source_document_id)
    for title in reversed(tuple(ancestor_chain)):
        candidate_matches = _matching_document_ids(title, owner_document_ids, aliases)
        if candidate_matches:
            return _OwnerResolution(candidate_matches[0], "ancestor")
        outside_matches = _matching_document_ids(
            title,
            all_manifest_document_ids - owner_document_ids,
            aliases,
        )
        generic_outside = _generic_document_title(title)
        if outside_matches or generic_outside:
            foreign_id = outside_matches[0] if outside_matches else generic_outside
            return _OwnerResolution(
                default_owner,
                "rejected",
                foreign_document_id=foreign_id,
                foreign_heading=title,
            )
    return _OwnerResolution(default_owner, "default_form")


def _document_aliases(root: Path, document_ids: Iterable[str]) -> dict[str, tuple[str, ...]]:
    try:
        manifest = load_manifest(root=root)
    except FileNotFoundError:
        manifest = None
    entries = manifest.by_document_id() if manifest is not None else {}
    result: dict[str, tuple[str, ...]] = {}
    for document_id in document_ids:
        entry = entries.get(document_id)
        values: list[str] = []
        if entry is not None and entry.region_title:
            values.append(entry.region_title)
        match = re.fullmatch(r"(form|schedule)_(.+)_(20[0-9]{2})", document_id)
        if match:
            label = match.group(2).replace("_", " ")
            values.append(f"{match.group(1)} {label}")
        if entry is not None and entry.kind == "worksheet":
            year = str(manifest.tax_year) if manifest is not None else _document_year(document_id)
            values.append(document_id.removesuffix(f"_{year}").replace("_", " "))
        result[document_id] = tuple(
            sorted(
                {_compact(value) for value in values if _compact(value)},
                key=len,
                reverse=True,
            )
        )
    return result


def _matching_document_ids(
    title: str,
    document_ids: Iterable[str],
    aliases: Mapping[str, tuple[str, ...]],
) -> list[str]:
    normalized = _compact(title)
    matches = [
        document_id
        for document_id in document_ids
        if any(
            alias and _document_alias_matches(title, document_id, alias)
            for alias in aliases.get(document_id, ())
        )
    ]
    return sorted(
        matches,
        key=lambda document_id: max((len(alias) for alias in aliases.get(document_id, ())), default=0),
        reverse=True,
    )


def _document_alias_matches(title: str, document_id: str, alias: str) -> bool:
    """Match a manifest alias without treating ``Schedule 1-A`` as ``1``."""
    identity = re.fullmatch(r"(form|schedule)_(.+)_(20[0-9]{2})", document_id)
    if identity:
        kind, label, _year = identity.groups()
        simple = re.fullmatch(r"([0-9]+)([a-z]?)", label)
        if simple:
            number, suffix = simple.groups()
            suffix_pattern = re.escape(suffix) if suffix else ""
            pattern = rf"\b{kind}\s+{number}"
            if suffix_pattern:
                pattern += rf"(?:\s*-\s*|\s*){suffix_pattern}"
            pattern += r"\b"
            return re.search(pattern, title, re.IGNORECASE) is not None

    normalized = _compact(title)
    position = normalized.find(alias)
    while position >= 0:
        end = position + len(alias)
        if end == len(normalized) or not normalized[end].isalnum():
            return True
        position = normalized.find(alias, position + 1)
    return False


def _generic_document_title(title: str) -> str | None:
    match = _DOCUMENT_RE.search(_clean_text(title))
    if not match:
        return None
    token = re.sub(r"[^a-z0-9]+", "_", match.group(0).lower()).strip("_")
    return token or "foreign_document"


def _first_nested_anchor(start: int, end: int, targets: Sequence[_RawTarget]) -> str | None:
    nested = [item for item in targets if start <= item.start_char < end]
    return min(nested, key=lambda item: item.start_char).anchor_id if nested else None


def _byte_offsets(source: str) -> list[int]:
    """Return the UTF-8 byte offset for every Python character boundary."""
    offsets = [0]
    total = 0
    for char in source:
        total += len(char.encode("utf-8"))
        offsets.append(total)
    return offsets


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


def _default_owner(source_document_id: str) -> str:
    return source_document_id.removeprefix("instructions_")


def _document_year(document_id: str) -> str:
    """Return the trailing tax year for a manifest-free test vocabulary."""
    match = re.search(r"_(20[0-9]{2})$", document_id)
    return match.group(1) if match else YEAR


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _clean_text(value).lower())


def _visible_text(value: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(value)
    parser.close()
    return _clean_text(parser.text)


class _VisibleTextParser(HTMLParser):
    """Extract visible text for the non-empty invariant."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_depth = 0

    @property
    def text(self) -> str:
        """Return captured visible text."""
        return "".join(self.parts)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style"}:
            self.ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"} and self.ignored_depth:
            self.ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.ignored_depth:
            self.parts.append(data)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "source"


def main(argv: Sequence[str] | None = None) -> int:
    """Write the M20-S128 frame report without touching project state."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--year", default=YEAR)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    report = measure_corpus(args.root, year=args.year)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
            encoding="ascii",
            newline="\n",
        )
    print(
        f"M20-S128: {report['summary']['booklet_count']} booklets, "
        f"{report['summary']['document_count']} documents, "
        f"{report['summary']['cell_count']} cells"
    )
    for document_id, data in report["documents"].items():
        print(
            f"{document_id}: cells={data['cells']}; "
            f"line_anchored={data['line_anchored']}; "
            f"topic_attributed={data['topic_attributed']}; "
            f"foreign_owner_rejected={data['foreign_owner_rejected']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
