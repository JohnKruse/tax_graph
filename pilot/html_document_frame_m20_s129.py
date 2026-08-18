"""Build the full-document HTML frame for the M20-S129 pilot.

This offline pilot extends the accepted M20-S128 containment frame without
changing it or touching production extraction.  The semantic ``div.book``
content region is tiled by every captured role heading and ``inlinehd`` label;
all offsets are UTF-8 byte offsets in the acquired HTML text.  Foreign-owner
sections remain in the tile as rejected intervals, so rejection cannot create
an unreported byte gap.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
import argparse
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

from pilot.html_section_frame_m20_s128 import (
    BOOKLET_IDS,
    HtmlSectionRejection,
    _HtmlFrameParser,
    _RawHeading,
    _RawInline,
    _RawTarget,
    _ancestor_nodes,
    _byte_offsets,
    _clean_text,
    _default_owner,
    _document_aliases,
    _first_nested_anchor,
    _line_tokens,
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
MODEL_FIXTURES = {
    "instructions_form_1040_2025": "pilot/fixtures/instruction_segmenter_live_1040.json",
    "instructions_schedule_b_2025": "pilot/fixtures/instruction_segmenter_live_recordings.json",
    "instructions_schedule_d_2025": "pilot/fixtures/instruction_segmenter_live_recordings.json",
}
_BOOK_RE = re.compile(r"^book$", re.IGNORECASE)
_REQUIRED_FRAME_INVARIANTS = (
    "content_region_valid",
    "sections_tile_content",
    "section_offsets_valid",
    "section_source_resolves",
    "sections_nonempty",
    "no_toc_sections",
    "anchor_ids_unique",
    "anchor_ranges_valid",
    "ancestor_chain_present",
)


@dataclass(frozen=True)
class HtmlDocumentSection:
    """One full-document content interval, accepted or rejected."""

    section_id: str
    owner_document_id: str | None
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
    rejected: bool

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
            "rejected": self.rejected,
        }


@dataclass(frozen=True)
class HtmlDocumentFrame:
    """The byte-conserving full-document frame for one HTML booklet."""

    schema_version: int
    source_document_id: str
    source_length_bytes: int
    source_sha256: str
    offset_coordinate_space: str
    content_start_offset: int
    content_end_offset: int
    content_region_source: str
    owner_document_ids: tuple[str, ...]
    worksheet_document_ids: tuple[str, ...]
    sections: tuple[HtmlDocumentSection, ...]
    rejected_sections: tuple[HtmlSectionRejection, ...]
    structural_invariants: dict[str, Any]

    def as_dict(self, *, include_source: bool = False, source_text: str = "") -> dict[str, Any]:
        """Return a JSON-safe frame without copying source HTML by default."""
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "source_document_id": self.source_document_id,
            "source_length_bytes": self.source_length_bytes,
            "source_sha256": self.source_sha256,
            "offset_coordinate_space": self.offset_coordinate_space,
            "content_start_offset": self.content_start_offset,
            "content_end_offset": self.content_end_offset,
            "content_region_source": self.content_region_source,
            "owner_document_ids": list(self.owner_document_ids),
            "worksheet_document_ids": list(self.worksheet_document_ids),
            "sections": [item.as_dict() for item in self.sections],
            "rejected_sections": [item.as_dict() for item in self.rejected_sections],
            "structural_invariants": dict(self.structural_invariants),
        }
        if include_source:
            result["source_text"] = source_text
        return result


@dataclass(frozen=True)
class _BookRange:
    """One semantic ``div.book`` range in character coordinates."""

    start_char: int
    end_char: int


@dataclass(frozen=True)
class _BookOpen:
    tag: str
    start_char: int
    is_book: bool


@dataclass(frozen=True)
class _Event:
    """One semantic start boundary before interval construction."""

    start_char: int
    heading: str
    line_tokens: tuple[str, ...]
    claim_kind: str
    anchor_id: str | None
    context_char: int


class _BookRangeParser(HTMLParser):
    """Find the main ``div.book`` region without interpreting its contents."""

    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self._line_starts = [0]
        self._line_starts.extend(index + 1 for index, char in enumerate(source) if char == "\n")
        self.stack: list[_BookOpen] = []
        self.ranges: list[_BookRange] = []

    def _offset(self) -> int:
        line, column = self.getpos()
        return self._line_starts[line - 1] + column

    def _tag_end(self, start: int) -> int:
        close = self.source.find(">", start)
        return close + 1 if close >= 0 else start

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {str(key).lower(): str(value or "") for key, value in attrs}
        classes = set(attributes.get("class", "").split())
        self.stack.append(
            _BookOpen(
                tag=tag.lower(),
                start_char=self._offset(),
                is_book=tag.lower() == "div" and any(_BOOK_RE.fullmatch(item) for item in classes),
            )
        )

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
        end = self._tag_end(self._offset())
        while len(self.stack) - 1 >= index:
            element = self.stack.pop()
            if element.is_book:
                self.ranges.append(_BookRange(element.start_char, end))


def parse_html_document_frame(
    html_text: str,
    *,
    source_document_id: str,
    root: str | Path = ROOT,
    owner_document_ids: Iterable[str] | None = None,
    worksheet_document_ids: Iterable[str] | None = None,
    all_manifest_document_ids: Iterable[str] | None = None,
) -> HtmlDocumentFrame:
    """Tile the semantic ``div.book`` region into full-document sections."""
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
    book_parser = _BookRangeParser(html_text)
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
    content_start = byte_offsets[content.start_char]
    content_end = byte_offsets[content.end_char]
    raw_targets = tuple(sorted(raw_parser.targets, key=lambda item: item.start_char))
    raw_headings = tuple(sorted(raw_parser.headings, key=lambda item: item.start_char))
    raw_inlines = tuple(sorted(raw_parser.inline_headings, key=lambda item: item.start_char))

    events = _events_for_region(raw_headings, raw_inlines, raw_targets, content)
    boundaries = [content.start_char]
    boundaries.extend(item.start_char for item in events if item.start_char != content.start_char)
    boundaries = sorted(set(boundaries))
    boundaries.append(content.end_char)

    sections: list[HtmlDocumentSection] = []
    rejected: list[HtmlSectionRejection] = []
    for index, (start_char, end_char) in enumerate(zip(boundaries, boundaries[1:])):
        if end_char <= start_char:
            continue
        event = next((item for item in events if item.start_char == start_char), None)
        if event is None:
            event = _Event(start_char, "", (), "content_preamble", None, start_char)
        ancestor_nodes = _ancestor_nodes(raw_headings, event.context_char)
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
        section = HtmlDocumentSection(
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
                HtmlSectionRejection(
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

    content_bytes = source_bytes[content_start:content_end]
    sections_tile = _tiles(sections, content_start, content_end)
    source_resolves = all(
        source_bytes[item.start_offset:item.end_offset].decode("utf-8") == item.source_text
        for item in sections
    )
    section_offsets_valid = all(
        0 <= item.start_offset < item.end_offset <= len(source_bytes) for item in sections
    )
    anchors = [item for item in raw_targets if content.start_char <= item.start_char < content.end_char]
    anchor_ids = [item.anchor_id for item in anchors]
    invariants = {
        "content_region_valid": 0 <= content_start < content_end <= len(source_bytes),
        "sections_tile_content": sections_tile,
        "section_offsets_valid": section_offsets_valid,
        "section_source_resolves": source_resolves,
        "sections_nonempty": all(_visible_text(item.source_text) for item in sections),
        "no_toc_sections": all(item.start_offset >= content_start for item in sections),
        "anchor_ids_unique": len(anchor_ids) == len(set(anchor_ids)),
        "anchor_ranges_valid": all(
            0 <= byte_offsets[item.start_char] <= byte_offsets[item.end_char] <= len(source_bytes)
            for item in anchors
        ),
        "ancestor_chain_present": all(isinstance(item.ancestor_chain, tuple) for item in sections),
        "content_byte_count": len(content_bytes),
        "section_count": len(sections),
        "rejected_section_count": len(rejected),
    }
    return HtmlDocumentFrame(
        schema_version=1,
        source_document_id=source_document_id,
        source_length_bytes=len(source_bytes),
        source_sha256=_sha256(source_bytes),
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


def measure_corpus(root: str | Path = ROOT, *, year: str = YEAR) -> dict[str, Any]:
    """Measure all eight HTML frames and compare three recorded model frames."""
    root_path = Path(root).resolve()
    frames: dict[str, HtmlDocumentFrame] = {}
    for source_document_id in BOOKLET_IDS:
        source_path = root_path / ".cache" / "raw" / year / f"{source_document_id}.html"
        frames[source_document_id] = parse_html_document_frame(
            source_path.read_text(encoding="utf-8"),
            source_document_id=source_document_id,
            root=root_path,
        )

    comparison: dict[str, Any] = {}
    for source_document_id, fixture in MODEL_FIXTURES.items():
        source_path = root_path / ".cache" / "raw" / year / f"{source_document_id}.txt"
        model_frame = build_frame_from_fixture(
            source_path,
            source_document_id=source_document_id,
            fixture_path=root_path / fixture,
            allowed_document_ids=manifest_owner_document_ids(
                root_path,
                source_document_id=source_document_id,
            ),
            root=root_path,
        )
        comparison[source_document_id] = _compare_frames(model_frame.sections, frames[source_document_id].sections)
    for source_document_id, frame in frames.items():
        comparison.setdefault(
            source_document_id,
            {
                "available": False,
                "reason": "no recorded model frame for this booklet",
                "html_full_section_count": len(frame.sections),
            },
        )

    return {
        "round": "M20-S129",
        "coordinate_note": "HTML offsets are UTF-8 bytes; model comparison is normalized heading text, not a byte match.",
        "booklets": {
            source_document_id: {
                "content_start_offset": frame.content_start_offset,
                "content_end_offset": frame.content_end_offset,
                "content_region_source": frame.content_region_source,
                "section_count": len(frame.sections),
                "rejected_section_count": len(frame.rejected_sections),
                "structural_invariants": dict(frame.structural_invariants),
            }
            for source_document_id, frame in sorted(frames.items())
        },
        "model_comparison": comparison,
        "summary": {
            "booklet_count": len(frames),
            "structural_invariants_hold": all(
                all(
                    frame.structural_invariants[key] is True
                    for key in _REQUIRED_FRAME_INVARIANTS
                )
                for frame in frames.values()
            ),
        },
    }


def _events_for_region(
    headings: Sequence[_RawHeading],
    inlines: Sequence[_RawInline],
    targets: Sequence[_RawTarget],
    region: _BookRange,
) -> tuple[_Event, ...]:
    """Return one deterministic event per role-heading or inline start."""
    candidates: list[_Event] = []
    for heading in headings:
        if region.start_char <= heading.start_char < region.end_char:
            candidates.append(
                _Event(
                    heading.start_char,
                    heading.title,
                    _line_tokens(heading.title),
                    "role_heading",
                    _first_nested_anchor(heading.start_char, heading.end_char, targets),
                    heading.start_char,
                )
            )
    for inline in inlines:
        if region.start_char <= inline.start_char < region.end_char:
            candidates.append(
                _Event(
                    inline.start_char,
                    inline.title,
                    _line_tokens(inline.title),
                    "inline_heading",
                    inline.anchor_id or inline.container_target_id,
                    inline.start_char,
                )
            )
    grouped: dict[int, list[_Event]] = {}
    for event in candidates:
        grouped.setdefault(event.start_char, []).append(event)
    events: list[_Event] = []
    for start_char in sorted(grouped):
        group = grouped[start_char]
        role = next((item for item in group if item.claim_kind == "role_heading"), None)
        chosen = role or group[0]
        line_tokens = tuple(dict.fromkeys(token for item in group for token in item.line_tokens))
        kinds = "+".join(sorted({item.claim_kind for item in group}))
        events.append(
            _Event(
                start_char,
                chosen.heading,
                line_tokens,
                kinds,
                chosen.anchor_id,
                chosen.context_char,
            )
        )
    return tuple(events)


def _tiles(sections: Sequence[HtmlDocumentSection], start: int, end: int) -> bool:
    """Check exact adjacency and coverage of the content region."""
    expected = start
    for section in sections:
        if section.start_offset != expected or section.end_offset <= section.start_offset:
            return False
        expected = section.end_offset
    return bool(sections) and expected == end


def _compare_frames(model_sections: Sequence[Any], html_sections: Sequence[HtmlDocumentSection]) -> dict[str, Any]:
    """Compare model and HTML headings as an owner-qualified multiset."""
    model_keys = Counter(
        (_normalize_heading(item.heading), str(item.document_id))
        for item in model_sections
        if _normalize_heading(item.heading)
    )
    html_comparison = [
        item
        for item in html_sections
        if item.owner_document_id is not None and _normalize_heading(item.heading)
    ]
    html_keys = Counter(
        (_normalize_heading(item.heading), item.owner_document_id)
        for item in html_comparison
    )
    matched = sum(min(count, html_keys[key]) for key, count in model_keys.items())
    return {
        "available": True,
        "model_section_count": len(model_sections),
        "html_full_section_count": len(html_sections),
        "html_heading_section_count": len(html_comparison),
        "model_sections_with_html_text_match": matched,
        "model_sections_missed_by_html": len(model_sections) - matched,
        "html_sections_missed_by_model": len(html_comparison) - matched,
        "match_basis": "owner-qualified normalized heading text; not a byte match",
    }


def _normalize_heading(value: str) -> str:
    """Normalize model markdown and HTML punctuation for a text comparison."""
    normalized = re.sub(r"^\s*#{1,6}\s*", "", str(value).strip())
    normalized = re.sub(r"[*_`]+", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip().casefold()
    return normalized.rstrip(".:;").strip()


def _sha256(source_bytes: bytes) -> str:
    import hashlib

    return hashlib.sha256(source_bytes).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    """Write the M20-S129 measurement report without touching project state."""
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
        f"M20-S129: {report['summary']['booklet_count']} booklets; "
        f"structural_invariants_hold={report['summary']['structural_invariants_hold']}"
    )
    for source_document_id, item in report["booklets"].items():
        print(
            f"{source_document_id}: sections={item['section_count']}; "
            f"rejected={item['rejected_section_count']}"
        )
    for source_document_id, item in sorted(report["model_comparison"].items()):
        if item.get("available"):
            print(
                f"{source_document_id}: model={item['model_section_count']}; "
                f"html_text_matches={item['model_sections_with_html_text_match']}; "
                f"model_missed={item['model_sections_missed_by_html']}; "
                f"html_missed={item['html_sections_missed_by_model']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
