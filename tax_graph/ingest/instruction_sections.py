"""Mine typed, read-only sections from acquired IRS instruction HTML."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
import re
from typing import Iterable

from tax_graph.acquire.instruction_html import InstructionHeading, line_sections, parse_headings


@dataclass(frozen=True)
class InstructionBlock:
    """One typed body block with a span into the acquired HTML source."""

    block_type: str
    text: str
    source_start: int
    source_end: int


@dataclass(frozen=True)
class MinedInstructionSection:
    """A line-addressed candidate emitted without writing graph artifacts."""

    document_id: str
    heading: InstructionHeading
    line_tokens: tuple[str, ...]
    semantic_title: str
    parent_headings: tuple[str, ...]
    source_start: int
    source_end: int
    blocks: tuple[InstructionBlock, ...]


def mine_instruction_html(html_text: str, *, document_id: str) -> tuple[MinedInstructionSection, ...]:
    """Return deterministic line sections from one acquired HTML document."""
    headings = parse_headings(html_text)
    candidates = line_sections(html_text)
    blocks_by_span = _blocks_by_span(html_text)
    mined: list[MinedInstructionSection] = []
    for candidate in candidates:
        start = candidate.heading.source_end
        semantic_heading = _semantic_heading(headings, candidate.heading, candidate.semantic_title)
        end = _next_heading_start(headings, candidate.heading, semantic_heading)
        body_start = semantic_heading.source_end if semantic_heading is not None else start
        blocks = tuple(block for block in blocks_by_span if body_start <= block.source_start < end)
        mined.append(
            MinedInstructionSection(
                document_id=document_id,
                heading=candidate.heading,
                line_tokens=candidate.line_tokens,
                semantic_title=candidate.semantic_title,
                parent_headings=candidate.parent_headings,
                source_start=candidate.heading.source_start,
                source_end=end,
                blocks=blocks,
            )
        )
    return tuple(mined)


def mine_instruction_html_file(path: str | Path, *, document_id: str) -> tuple[MinedInstructionSection, ...]:
    """Read one acquired HTML file and mine it without contacting the source URL."""
    source_path = Path(path)
    return mine_instruction_html(source_path.read_text(encoding="ascii"), document_id=document_id)


def _next_heading_start(
    headings: tuple[InstructionHeading, ...],
    heading: InstructionHeading,
    semantic_heading: InstructionHeading | None,
) -> int:
    index = headings.index(semantic_heading or heading)
    heading_level = heading.level
    for following in headings[index + 1 :]:
        if following.level <= heading_level:
            return following.source_start
    return 2**63 - 1


def _semantic_heading(
    headings: tuple[InstructionHeading, ...], heading: InstructionHeading, title: str
) -> InstructionHeading | None:
    if not title:
        return None
    index = headings.index(heading)
    if index + 1 < len(headings):
        following = headings[index + 1]
        if following.level >= heading.level and following.text == title:
            return following
    return None


def _blocks_by_span(html_text: str) -> tuple[InstructionBlock, ...]:
    parser = _BlockParser(html_text)
    parser.feed(html_text)
    parser.close()
    return tuple(parser.blocks)


class _BlockParser(HTMLParser):
    """Capture paragraph, list, and table blocks while retaining raw source spans."""

    _BLOCK_TAGS = {"p", "li", "table"}

    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.blocks: list[InstructionBlock] = []
        self._line_starts = [0]
        for index, char in enumerate(source):
            if char == "\n":
                self._line_starts.append(index + 1)
        self._tag: str | None = None
        self._start = 0
        self._parts: list[str] = []

    def _offset(self) -> int:
        line, column = self.getpos()
        return self._line_starts[line - 1] + column

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self._tag is None and tag in self._BLOCK_TAGS:
            self._tag = tag
            self._start = self._offset()
            self._parts = []

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._tag is not None and tag.lower() == "br":
            self._parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._tag != tag:
            return
        end = self._offset()
        close_end = self.source.find(">", end)
        source_end = close_end + 1 if close_end >= 0 else end
        text = _normalize_text("".join(self._parts))
        if text:
            self.blocks.append(
                InstructionBlock(
                    block_type=_classify_block(text, self._tag),
                    text=text,
                    source_start=self._start,
                    source_end=source_end,
                )
            )
        self._tag = None
        self._parts = []

    def handle_data(self, data: str) -> None:
        if self._tag is not None:
            self._parts.append(data)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _classify_block(text: str, tag: str) -> str:
    lowered = text.lower()
    if lowered.startswith("exception"):
        return "exception"
    if re.match(r"example(?:\s+[0-9]+)?\s*[:.]", lowered):
        return "example"
    if "worksheet" in lowered:
        return "worksheet"
    if lowered.startswith("definition"):
        return "definition"
    if "see " in lowered or "refer to " in lowered:
        return "cross_reference"
    if tag == "li":
        return "list_item"
    if tag == "table":
        return "table"
    return "paragraph"
