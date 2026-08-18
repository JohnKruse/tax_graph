"""Widen the M20-S129 HTML frame using observed semantic title markup.

This provider-free pilot keeps the accepted M20-S129 frame contract and adds
only heading markup observed in the acquired IRS HTML.  The additions are
semantic title elements and title role classes, not arbitrary bold text.  A
generic ``span.bold`` is deliberately excluded because the same class is
used for prose emphasis and table labels.

The frame is measurement evidence only.  It does not call a model, fetch a
URL, change production extraction, or write graph artifacts.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from typing import Any, Iterable, Sequence

from pilot import html_document_frame_m20_s129 as s129
from pilot.html_section_frame_m20_s128 import (
    _HtmlFrameParser,
    _RawHeading,
    _ancestor_nodes,
    _byte_offsets,
    _clean_text,
    _document_aliases,
    _first_nested_anchor,
    _load_cells,
    _resolve_owner,
    _slug,
    _visible_text,
)
from pilot.model_instruction_segmenter import (
    build_frame_from_fixture,
    manifest_owner_document_ids,
    manifest_worksheet_document_ids,
)
from tax_graph.acquire.manifest import load_manifest


ROOT = Path(__file__).resolve().parents[1]
YEAR = "2025"
BOOKLET_IDS = s129.BOOKLET_IDS
MODEL_FIXTURES = s129.MODEL_FIXTURES
_REQUIRED_FRAME_INVARIANTS = s129._REQUIRED_FRAME_INVARIANTS
_TITLE_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6", "p"})
_EXTRA_ROLE_LEVELS = {
    "role-changes": 1,
    "role-geninstr": 1,
    "role-figure": 6,
    "role-eictable": 6,
    "role-taxtable": 6,
    "role-teletax-topics": 2,
    "role-budget": 2,
    "role-redact": 2,
    "role-topic": 3,
    "role-step-section": 6,
    "role-step": 7,
}


@dataclass
class _OpenElement:
    """One element captured while collecting extra title candidates."""

    tag: str
    attrs: dict[str, str | None]
    start_char: int
    parts: list[str]


class _ExtraTitleParser(HTMLParser):
    """Capture title-bearing elements not covered by the S128 vocabulary."""

    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self._line_starts = [0]
        self._line_starts.extend(index + 1 for index, char in enumerate(source) if char == "\n")
        self.stack: list[_OpenElement] = []
        self.elements: list[tuple[_OpenElement, int]] = []

    def _offset(self) -> int:
        line, column = self.getpos()
        return self._line_starts[line - 1] + column

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack.append(
            _OpenElement(
                tag=tag.lower(),
                attrs={str(key).lower(): value for key, value in attrs},
                start_char=self._offset(),
                parts=[],
            )
        )

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if not data:
            return
        for element in self.stack:
            element.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        index = len(self.stack) - 1
        while index >= 0 and self.stack[index].tag != normalized_tag:
            index -= 1
        if index < 0:
            return
        end = self._tag_end(self._offset())
        while len(self.stack) - 1 >= index:
            self.elements.append((self.stack.pop(), end))

    def _tag_end(self, start: int) -> int:
        close = self.source.find(">", start)
        return close + 1 if close >= 0 else start


def _extra_headings(html_text: str) -> tuple[_RawHeading, ...]:
    """Return only observed semantic title candidates outside S128 roles."""
    parser = _ExtraTitleParser(html_text)
    parser.feed(html_text)
    parser.close()
    headings: list[_RawHeading] = []
    for element, end_char in parser.elements:
        classes = set(str(element.attrs.get("class") or "").split())
        if element.tag not in _TITLE_TAGS:
            continue
        role_class = next(
            (class_name for class_name in classes if class_name.startswith("role-")),
            None,
        )
        if role_class is not None:
            level = _EXTRA_ROLE_LEVELS.get(role_class)
            if level is None:
                continue
        elif "title" in classes:
            # These titles are leaf evidence blocks in the observed IRS HTML.
            # Keep them below the existing role tree so they cannot evict a
            # worksheet owner from the ancestor chain.
            level = 8
        else:
            continue
        title = _clean_text("".join(element.parts))
        if not title:
            continue
        headings.append(
            _RawHeading(
                level=level,
                title=title,
                role_class=role_class or "title",
                start_char=element.start_char,
                end_char=end_char,
                anchor_id=None,
            )
        )
    return tuple(headings)


def parse_html_document_frame(
    html_text: str,
    *,
    source_document_id: str,
    root: str | Path = ROOT,
    owner_document_ids: Iterable[str] | None = None,
    worksheet_document_ids: Iterable[str] | None = None,
    all_manifest_document_ids: Iterable[str] | None = None,
) -> s129.HtmlDocumentFrame:
    """Tile one booklet using S129 roles plus observed title markup."""
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

    raw_parser = _HtmlFrameParser(html_text)
    raw_parser.feed(html_text)
    raw_parser.close()
    extra_headings = _extra_headings(html_text)
    book_parser = s129._BookRangeParser(html_text)
    book_parser.feed(html_text)
    book_parser.close()
    if not book_parser.ranges:
        raise ValueError(f"no div.book content region in {source_document_id}")
    if len(book_parser.ranges) != 1:
        raise ValueError(
            f"expected exactly one div.book content region in {source_document_id}; "
            f"found {len(book_parser.ranges)}"
        )
    content = book_parser.ranges[0]
    if content.end_char <= content.start_char:
        raise ValueError(f"empty div.book content region in {source_document_id}")

    source_bytes = html_text.encode("utf-8")
    byte_offsets = _byte_offsets(html_text)
    raw_targets = tuple(sorted(raw_parser.targets, key=lambda item: item.start_char))
    raw_headings = tuple(
        sorted(
            (*raw_parser.headings, *extra_headings),
            key=lambda item: (item.start_char, item.level, item.role_class),
        )
    )
    # S128's role tree remains the ownership authority.  The added title
    # events widen the byte frame but must not make a nested worksheet title
    # reassign a surrounding form cell to that worksheet.
    ownership_headings = tuple(sorted(raw_parser.headings, key=lambda item: item.start_char))
    raw_inlines = tuple(sorted(raw_parser.inline_headings, key=lambda item: item.start_char))
    events = s129._events_for_region(raw_headings, raw_inlines, raw_targets, content)
    boundaries = [content.start_char]
    boundaries.extend(item.start_char for item in events if item.start_char != content.start_char)
    boundaries = sorted(set(boundaries))
    boundaries.append(content.end_char)

    sections: list[s129.HtmlDocumentSection] = []
    rejected: list[s129.HtmlSectionRejection] = []
    for index, (start_char, end_char) in enumerate(zip(boundaries, boundaries[1:])):
        if end_char <= start_char:
            continue
        event = next((item for item in events if item.start_char == start_char), None)
        if event is None:
            event = s129._Event(start_char, "", (), "content_preamble", None, start_char)
        ancestor_nodes = _ancestor_nodes(ownership_headings, event.context_char)
        if event.claim_kind == "role_heading" and ancestor_nodes:
            if ancestor_nodes[-1].start_char == event.context_char:
                ancestor_nodes = ancestor_nodes[:-1]
        ancestor_chain = tuple(item.title for item in ancestor_nodes)
        ancestor_anchor_ids = tuple(
            _first_nested_anchor(item.start_char, item.end_char, raw_targets)
            for item in ancestor_nodes
        )
        owner = _resolve_owner(
            ancestor_chain,
            source_document_id=source_document_id,
            owner_document_ids=owners,
            all_manifest_document_ids=all_ids,
            aliases=aliases,
        )
        start_offset = byte_offsets[start_char]
        end_offset = byte_offsets[end_char]
        source_text = html_text[start_char:end_char]
        is_rejected = bool(owner.foreign_heading)
        section = s129.HtmlDocumentSection(
            section_id=f"html_document_{_slug(source_document_id)}_{index + 1:04d}",
            owner_document_id=None if is_rejected else owner.document_id,
            owner_source="rejected" if is_rejected else owner.source,
            anchor_id=event.anchor_id,
            heading=event.heading,
            line_tokens=event.line_tokens,
            ancestor_chain=ancestor_chain,
            ancestor_anchor_ids=ancestor_anchor_ids,
            start_offset=start_offset,
            end_offset=end_offset,
            source_text=source_text,
            claim_kind=event.claim_kind,
            rejected=is_rejected,
        )
        sections.append(section)
        if is_rejected:
            rejected.append(
                s129.HtmlSectionRejection(
                    heading=event.heading,
                    reason="foreign_owner_rejected",
                    foreign_document_id=owner.foreign_document_id,
                    foreign_heading=owner.foreign_heading,
                    ancestor_chain=ancestor_chain,
                    anchor_id=event.anchor_id,
                    start_offset=start_offset,
                    end_offset=end_offset,
                )
            )

    content_start = byte_offsets[content.start_char]
    content_end = byte_offsets[content.end_char]
    anchors = [
        item for item in raw_targets if content.start_char <= item.start_char < content.end_char
    ]
    anchor_ids = [item.anchor_id for item in anchors]
    invariants = {
        "content_region_valid": 0 <= content_start < content_end <= len(source_bytes),
        "sections_tile_content": s129._tiles(sections, content_start, content_end),
        "section_offsets_valid": all(
            0 <= item.start_offset < item.end_offset <= len(source_bytes) for item in sections
        ),
        "section_source_resolves": all(
            source_bytes[item.start_offset : item.end_offset].decode("utf-8")
            == item.source_text
            for item in sections
        ),
        "sections_nonempty": all(_visible_text(item.source_text) for item in sections),
        "no_toc_sections": all(item.start_offset >= content_start for item in sections),
        "anchor_ids_unique": len(anchor_ids) == len(set(anchor_ids)),
        "anchor_ranges_valid": all(
            0 <= byte_offsets[item.start_char] <= byte_offsets[item.end_char] <= len(source_bytes)
            for item in anchors
        ),
        "ancestor_chain_present": all(isinstance(item.ancestor_chain, tuple) for item in sections),
        "content_byte_count": content_end - content_start,
        "section_count": len(sections),
        "rejected_section_count": len(rejected),
    }
    return s129.HtmlDocumentFrame(
        schema_version=1,
        source_document_id=source_document_id,
        source_length_bytes=len(source_bytes),
        source_sha256=s129._sha256(source_bytes),
        offset_coordinate_space="utf8_bytes_of_acquired_html",
        content_start_offset=content_start,
        content_end_offset=content_end,
        content_region_source="div.book",
        owner_document_ids=tuple(sorted(owners)),
        worksheet_document_ids=tuple(sorted(worksheets)),
        sections=tuple(sections),
        rejected_sections=tuple(rejected),
        structural_invariants=invariants,
    )


def _compact_heading(value: str) -> str:
    """Fold OCR and HTML punctuation for local gap accounting only."""
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def _heading_is_represented(model_heading: str, html_heading: str) -> bool:
    """Allow a clean HTML suffix without matching a longer numeric token."""
    model_key = _compact_heading(model_heading).lstrip("#")
    html_key = _compact_heading(html_heading)
    if not model_key:
        return False
    if html_key == model_key:
        return True
    if not html_key.startswith(model_key):
        return False
    return not html_key[len(model_key) :].startswith(tuple("0123456789"))


def _model_only_non_page_sections(root: Path) -> tuple[Any, ...]:
    """Return the S129 1040 comparison population without page markers."""
    source_document_id = "instructions_form_1040_2025"
    model = build_frame_from_fixture(
        root / ".cache" / "raw" / YEAR / "instructions_form_1040_2025.txt",
        source_document_id=source_document_id,
        fixture_path=root / MODEL_FIXTURES[source_document_id],
        allowed_document_ids=manifest_owner_document_ids(
            root,
            source_document_id=source_document_id,
        ),
        root=root,
    )
    baseline = s129.parse_html_document_frame(
        (root / ".cache" / "raw" / YEAR / "instructions_form_1040_2025.html").read_text(
            encoding="utf-8"
        ),
        source_document_id=source_document_id,
        root=root,
    )
    html_keys = Counter(
        s129._normalize_heading(section.heading)
        for section in baseline.sections
        if section.owner_document_id and s129._normalize_heading(section.heading)
    )
    used: Counter[str] = Counter()
    misses: list[Any] = []
    for section in model.sections:
        key = s129._normalize_heading(section.heading)
        if used[key] < html_keys[key]:
            used[key] += 1
        elif not key.startswith("page "):
            misses.append(section)
    return tuple(misses)


def _gap_report(
    root: Path,
    frame: s129.HtmlDocumentFrame,
) -> dict[str, Any]:
    """Report the S129 model-only population against widened title events."""
    misses = _model_only_non_page_sections(root)
    html_headings = tuple(
        _compact_heading(section.heading)
        for section in frame.sections
        if section.owner_document_id is not None and section.heading
    )
    represented = [
        section
        for section in misses
        if any(_heading_is_represented(section.heading, heading) for heading in html_headings)
    ]
    return {
        "baseline_model_only_non_page": len(misses),
        "represented_by_widened_heading": len(represented),
        "remaining_unsectioned": len(misses) - len(represented),
        "matching_note": (
            "Compact heading containment is used only to account for OCR punctuation and suffix "
            "damage; it is not a PDF-to-HTML score."
        ),
    }


def _line_anchored_report(
    root: Path,
    frames: dict[str, s129.HtmlDocumentFrame],
) -> dict[str, Any]:
    """Score the S128 reconciliation cells against the widened frame."""
    cells = _load_cells(root)
    result: dict[str, Any] = {}
    for document_id, document_cells in sorted(cells.items()):
        booklet_id = str(document_cells[0]["booklet_id"]) if document_cells else ""
        frame = frames.get(booklet_id)
        if frame is None:
            continue
        line_matches = {
            (section.owner_document_id, token): section
            for section in frame.sections
            if section.owner_document_id is not None
            for token in section.line_tokens
        }
        ids = sorted(
            cell["cell_id"]
            for cell in document_cells
            if (document_id, cell["line"]) in line_matches
        )
        result[document_id] = {
            "booklet_id": booklet_id,
            "cells": len(document_cells),
            "line_anchored": len(ids),
            "line_anchored_cell_ids": ids,
        }
    return result


def measure_corpus(root: str | Path = ROOT, *, year: str = YEAR) -> dict[str, Any]:
    """Build all eight widened frames and report structural and coverage evidence."""
    root_path = Path(root).resolve()
    frames: dict[str, s129.HtmlDocumentFrame] = {}
    for source_document_id in BOOKLET_IDS:
        source_path = root_path / ".cache" / "raw" / year / f"{source_document_id}.html"
        frames[source_document_id] = parse_html_document_frame(
            source_path.read_text(encoding="utf-8"),
            source_document_id=source_document_id,
            root=root_path,
        )
    report = {
        "round": "M20-S130",
        "source_policy": {
            "html": "acquired IRS HTML only; no network or provider call",
            "added_markup": sorted(_EXTRA_ROLE_LEVELS) + ["p.title", "h1-h6.title"],
            "excluded_markup": ["generic span.bold", "generic strong"],
            "offsets": "UTF-8 byte offsets into the acquired HTML",
        },
        "booklets": {
            source_document_id: {
                "content_start_offset": frame.content_start_offset,
                "content_end_offset": frame.content_end_offset,
                "section_count": len(frame.sections),
                "rejected_section_count": len(frame.rejected_sections),
                "structural_invariants": dict(frame.structural_invariants),
            }
            for source_document_id, frame in sorted(frames.items())
        },
        "documents": _line_anchored_report(root_path, frames),
        "gap": _gap_report(root_path, frames["instructions_form_1040_2025"]),
        "summary": {
            "booklet_count": len(frames),
            "structural_invariants_hold": all(
                all(frame.structural_invariants[key] is True for key in _REQUIRED_FRAME_INVARIANTS)
                for frame in frames.values()
            ),
        },
    }
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """Write the M20-S130 report only when an output path is explicitly supplied."""
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
        f"M20-S130: {report['summary']['booklet_count']} booklets; "
        f"structural_invariants_hold={report['summary']['structural_invariants_hold']}; "
        f"remaining_unsectioned={report['gap']['remaining_unsectioned']}"
    )
    for document_id, item in report["documents"].items():
        print(
            f"{document_id}: cells={item['cells']}; "
            f"line_anchored={item['line_anchored']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
