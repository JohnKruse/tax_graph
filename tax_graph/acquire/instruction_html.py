"""Deterministic parsing and survey helpers for acquired IRS instruction HTML."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import re
from typing import Iterable


_LINE_HEADING_RE = re.compile(r"^lines?\s+(.+)$", re.IGNORECASE)
_LINE_TOKEN_RE = re.compile(r"^([0-9]+[a-z]?)\b", re.IGNORECASE)
_MULTI_TOKEN_RE = re.compile(r"[0-9]+[a-z]?", re.IGNORECASE)


@dataclass(frozen=True)
class InstructionHeading:
    """One HTML heading with its stable anchor and heading level."""

    level: int
    anchor_id: str
    text: str


@dataclass(frozen=True)
class InstructionSection:
    """A heading that names one or more printed lines."""

    heading: InstructionHeading
    line_tokens: tuple[str, ...]
    semantic_title: str
    parent_headings: tuple[str, ...]


class _HeadingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[InstructionHeading] = []
        self._active: tuple[int, str] | None = None
        self._parts: list[str] = []
        self._pending_anchor = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            attributes = dict(attrs)
            self._pending_anchor = str(attributes.get("name") or attributes.get("id") or "")
            return
        match = re.fullmatch(r"h([1-6])", tag.lower())
        if not match:
            return
        attributes = dict(attrs)
        self._active = (
            int(match.group(1)),
            str(attributes.get("id") or self._pending_anchor or ""),
        )
        self._parts = []
        self._pending_anchor = ""

    def handle_endtag(self, tag: str) -> None:
        if self._active is None or not re.fullmatch(r"h[1-6]", tag.lower()):
            return
        level, anchor_id = self._active
        text = " ".join("".join(self._parts).split())
        if text:
            self.headings.append(InstructionHeading(level, anchor_id, text))
        self._active = None
        self._parts = []

    def handle_data(self, data: str) -> None:
        if self._active is not None:
            self._parts.append(data)


def parse_headings(html_text: str) -> tuple[InstructionHeading, ...]:
    """Return the ordered HTML heading tree in source order."""
    parser = _HeadingParser()
    parser.feed(html_text)
    parser.close()
    return tuple(parser.headings)


def line_sections(html_text: str) -> tuple[InstructionSection, ...]:
    """Extract line-naming headings while preserving their parent heading path."""
    headings = parse_headings(html_text)
    parents: list[str] = []
    sections: list[InstructionSection] = []
    for index, heading in enumerate(headings):
        parents = parents[: heading.level - 1]
        match = _LINE_HEADING_RE.match(heading.text)
        if match:
            tokens, title = _line_tokens_and_title(match.group(1))
            if tokens:
                title = title or _following_semantic_title(headings, index, heading.level, tokens)
                sections.append(
                    InstructionSection(
                        heading=heading,
                        line_tokens=tokens,
                        semantic_title=title,
                        parent_headings=tuple(parents),
                    )
                )
        parents.append(heading.text)
    return tuple(sections)


def _following_semantic_title(
    headings: tuple[InstructionHeading, ...],
    index: int,
    level: int,
    tokens: tuple[str, ...],
) -> str:
    """Use the adjacent same-level semantic heading when the line heading is bare."""
    if index + 1 >= len(headings):
        return ""
    following = headings[index + 1]
    if following.level < level:
        return ""
    match = _LINE_HEADING_RE.match(following.text)
    if not match:
        return following.text if following.level >= level else ""
    following_tokens, following_title = _line_tokens_and_title(match.group(1))
    if following_title and set(tokens).intersection(following_tokens):
        return following_title
    return ""


def _line_tokens_and_title(rest: str) -> tuple[tuple[str, ...], str]:
    normalized = " ".join(rest.split())
    if " - " in normalized:
        token_text, title = normalized.split(" - ", 1)
    elif ": " in normalized:
        token_text, title = normalized.split(": ", 1)
    else:
        token_match = _LINE_TOKEN_RE.match(normalized)
        if not token_match:
            return (), ""
        tokens = [token_match.group(1)]
        cursor = token_match.end()
        while True:
            connector = re.match(
                r"\s*(?:,\s*(?:and\s+)?|(?:and|through|to)\s+|-\s*)",
                normalized[cursor:],
                re.IGNORECASE,
            )
            if not connector:
                break
            next_match = _LINE_TOKEN_RE.match(normalized[cursor + connector.end() :])
            if not next_match:
                break
            tokens.append(next_match.group(1))
            cursor += connector.end() + next_match.end()
        return tuple(token.lower() for token in tokens), normalized[cursor:].strip(" -:")
    tokens = tuple(_MULTI_TOKEN_RE.findall(token_text))
    return tuple(token.lower() for token in tokens), title.strip()


def heading_tree_lines(headings: Iterable[InstructionHeading]) -> list[str]:
    """Render a compact ASCII heading tree for a committed survey report."""
    return [f"{'  ' * max(0, item.level - 1)}- {item.text} [{item.anchor_id or 'no-id'}]" for item in headings]
