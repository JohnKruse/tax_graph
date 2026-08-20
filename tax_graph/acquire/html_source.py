"""Map visible instruction text to byte ranges in acquired IRS HTML."""

from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
from bisect import bisect_left, bisect_right
from pathlib import Path
import re
from typing import Iterable, Mapping


class HtmlSourceIndex:
    """Index the visible ``div.book`` text while retaining raw byte bounds."""

    def __init__(self, source: str) -> None:
        self.source = source
        byte_offsets = [0]
        total = 0
        for character in source:
            total += len(character.encode("utf-8"))
            byte_offsets.append(total)
        parser = _VisibleSourceParser(source, byte_offsets)
        parser.feed(source)
        parser.close()
        self.visible_text, self._char_ranges = _collapse_visible_text(
            parser.parts,
            parser.char_ranges,
        )
        self._normalized_text, self._normalized_ranges = _normalize_with_ranges(
            self.visible_text,
            self._char_ranges,
        )
        self._segmentable_text, self._segmentable_ranges = _segmentable_source(
            source,
            byte_offsets,
        )
        self._segmentable_byte_offsets = [0]
        for character in self._segmentable_text:
            self._segmentable_byte_offsets.append(
                self._segmentable_byte_offsets[-1]
                + len(character.encode("utf-8"))
            )

    @property
    def segmentable_text(self) -> str:
        """Return visible HTML text with structural block and heading lines."""
        return self._segmentable_text

    def raw_range_for_segment_bytes(
        self,
        start: int,
        end: int,
    ) -> dict[str, int] | None:
        """Map a segmentable-text UTF-8 range back to raw HTML bytes."""
        if (
            start < 0
            or end <= start
            or end > self._segmentable_byte_offsets[-1]
        ):
            return None
        start_index = bisect_left(self._segmentable_byte_offsets, start)
        end_index = bisect_left(self._segmentable_byte_offsets, end)
        if (
            start_index >= len(self._segmentable_byte_offsets)
            or end_index >= len(self._segmentable_byte_offsets)
            or self._segmentable_byte_offsets[start_index] != start
            or self._segmentable_byte_offsets[end_index] != end
        ):
            return None
        if end_index > len(self._segmentable_ranges) or start_index >= end_index:
            return None
        return {
            "start": self._segmentable_ranges[start_index][0],
            "end": self._segmentable_ranges[end_index - 1][1],
        }

    def ranges_for_quote(self, quote: str) -> tuple[dict[str, int], ...] | None:
        """Return one raw UTF-8 byte range for a visible quote."""
        wanted = _normalize_whitespace(quote)
        if not wanted:
            return None
        start = self._normalized_text.find(wanted)
        if start >= 0:
            end = start + len(wanted)
        else:
            token_match = _token_range(self._normalized_text, quote)
            if token_match is None:
                return None
            start, end = token_match
        if end > len(self._normalized_ranges):
            return None
        raw_start = self._normalized_ranges[start][0]
        raw_end = self._normalized_ranges[end - 1][1]
        return ({"start": raw_start, "end": raw_end},)

    def visible_text_for_ranges(
        self,
        ranges: Iterable[Mapping[str, int]],
    ) -> str:
        """Project raw HTML ranges back to normalized visible text."""
        parts: list[str] = []
        starts = [item[0] for item in self._normalized_ranges]
        ends = [item[1] for item in self._normalized_ranges]
        for item in ranges:
            start = int(item["start"])
            end = int(item["end"])
            left = bisect_left(starts, start)
            right = bisect_right(ends, end)
            parts.append(_normalize_whitespace(self._normalized_text[left:right]))
        return " ".join(part for part in parts if part)


class _VisibleSourceParser(HTMLParser):
    """Capture visible text inside the semantic booklet region."""

    def __init__(self, source: str, byte_offsets: list[int]) -> None:
        super().__init__(convert_charrefs=False)
        self.source = source
        self.byte_offsets = byte_offsets
        self.parts: list[str] = []
        self.char_ranges: list[tuple[int, int]] = []
        self.stack: list[tuple[str, bool]] = []
        self.ignored_depth = 0
        self.line_starts = [0]
        self.line_starts.extend(
            index + 1 for index, value in enumerate(source) if value == "\n"
        )

    def _offset(self) -> int:
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def _active(self) -> bool:
        return any(is_book for _tag, is_book in self.stack) and not self.ignored_depth

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        is_book = tag.lower() == "div" and any(
            key.lower() == "class" and "book" in (value or "").split()
            for key, value in attrs
        )
        self.stack.append((tag.lower(), is_book))
        if tag.lower() in {"script", "style"}:
            self.ignored_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in {"script", "style"} and self.ignored_depth:
            self.ignored_depth -= 1
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == normalized:
                self.stack = self.stack[:index]
                return

    def _append(self, text: str, start: int, end: int) -> None:
        start_byte = self.byte_offsets[start]
        end_byte = self.byte_offsets[end]
        for character in text:
            self.parts.append(character)
            self.char_ranges.append((start_byte, end_byte))

    def handle_data(self, data: str) -> None:
        if not self._active():
            return
        start = self._offset()
        if self.source[start : start + len(data)] != data:
            start = self.source.find(data, start)
        if start < 0:
            return
        self._append(data, start, start + len(data))

    def handle_entityref(self, name: str) -> None:
        if self._active():
            start = self._offset()
            raw = f"&{name};"
            self._append(unescape(raw), start, start + len(raw))

    def handle_charref(self, name: str) -> None:
        if self._active():
            start = self._offset()
            raw = f"&#{name};"
            self._append(unescape(raw), start, start + len(raw))


class _SegmentableSourceParser(HTMLParser):
    """Build model-friendly lines while retaining raw source coordinates."""

    _BLOCK_TAGS = frozenset(
        {
            "article",
            "br",
            "div",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "li",
            "p",
            "section",
            "td",
            "th",
            "tr",
            "ul",
            "ol",
        }
    )

    def __init__(self, source: str, byte_offsets: list[int]) -> None:
        super().__init__(convert_charrefs=False)
        self.source = source
        self.byte_offsets = byte_offsets
        self.parts: list[str] = []
        self.char_ranges: list[tuple[int, int]] = []
        self.stack: list[tuple[str, bool]] = []
        self.ignored_depth = 0
        self.line_starts = [0]
        self.line_starts.extend(
            index + 1 for index, value in enumerate(source) if value == "\n"
        )

    def _offset(self) -> int:
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def _active(self) -> bool:
        return any(is_book for _tag, is_book in self.stack) and not self.ignored_depth

    def _tag_range(self, start: int) -> tuple[int, int]:
        end = self.source.find(">", start)
        if end < 0:
            end = start
        else:
            end += 1
        return self.byte_offsets[start], self.byte_offsets[end]

    def _append(self, text: str, start: int, end: int) -> None:
        start_byte = self.byte_offsets[start]
        end_byte = self.byte_offsets[end]
        for character in text:
            self.parts.append(character)
            self.char_ranges.append((start_byte, end_byte))

    def _append_boundary(self, raw_range: tuple[int, int]) -> None:
        if self.parts and self.parts[-1] == "\n":
            return
        self.parts.append("\n")
        self.char_ranges.append(raw_range)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        start = self._offset()
        raw_range = self._tag_range(start)
        was_active = self._active()
        if was_active and normalized in self._BLOCK_TAGS:
            self._append_boundary(raw_range)
        if was_active and normalized in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._append("#" * int(normalized[1]) + " ", start, start)
            if self.char_ranges:
                self.char_ranges[-(int(normalized[1]) + 1) :] = [
                    raw_range
                ] * (int(normalized[1]) + 1)
        is_book = normalized == "div" and any(
            key.lower() == "class" and "book" in (value or "").split()
            for key, value in attrs
        )
        self.stack.append((normalized, is_book))
        if normalized in {"script", "style"}:
            self.ignored_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in {"script", "style"} and self.ignored_depth:
            self.ignored_depth -= 1
        if self._active() and normalized in self._BLOCK_TAGS:
            self._append_boundary(self._tag_range(self._offset()))
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == normalized:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if self._active():
            start = self._offset()
            if self.source[start : start + len(data)] != data:
                start = self.source.find(data, start)
            if start >= 0:
                self._append(data, start, start + len(data))

    def handle_entityref(self, name: str) -> None:
        if self._active():
            start = self._offset()
            raw = f"&{name};"
            self._append(unescape(raw), start, start + len(raw))

    def handle_charref(self, name: str) -> None:
        if self._active():
            start = self._offset()
            raw = f"&#{name};"
            self._append(unescape(raw), start, start + len(raw))


def _segmentable_source(
    source: str,
    byte_offsets: list[int],
) -> tuple[str, list[tuple[int, int]]]:
    """Build a normalized, heading-aware view of one acquired HTML source."""
    parser = _SegmentableSourceParser(source, byte_offsets)
    parser.feed(source)
    parser.close()
    result: list[str] = []
    ranges: list[tuple[int, int]] = []
    for character, raw_range in zip(parser.parts, parser.char_ranges):
        if character == "\n":
            while result and result[-1] == " ":
                result.pop()
                ranges.pop()
            if result and result[-1] != "\n":
                result.append(character)
                ranges.append(raw_range)
            continue
        if character.isspace():
            if result and result[-1] not in {" ", "\n"}:
                result.append(" ")
                ranges.append(raw_range)
            continue
        result.append(character)
        ranges.append(raw_range)
    while result and result[-1] in {" ", "\n"}:
        result.pop()
        ranges.pop()
    first = 0
    while first < len(result) and result[first] in {" ", "\n"}:
        first += 1
    return "".join(result[first:]), ranges[first:]


def _collapse_visible_text(
    parts: list[str],
    char_ranges: list[tuple[int, int]],
) -> tuple[str, list[tuple[int, int]]]:
    result: list[str] = []
    ranges: list[tuple[int, int]] = []
    index = 0
    while index < len(parts):
        if parts[index].isspace():
            end = index + 1
            while end < len(parts) and parts[end].isspace():
                end += 1
            result.append(" ")
            ranges.append((char_ranges[index][0], char_ranges[end - 1][1]))
            index = end
            continue
        result.append(parts[index])
        ranges.append(char_ranges[index])
        index += 1
    text = "".join(result)
    left = len(text) - len(text.lstrip())
    right = len(text.rstrip())
    return text.strip(), ranges[left:right]


def _normalize_with_ranges(
    text: str,
    char_ranges: list[tuple[int, int]],
) -> tuple[str, list[tuple[int, int]]]:
    normalized = _normalize_whitespace(text)
    if normalized == text:
        return normalized, char_ranges
    result: list[str] = []
    ranges: list[tuple[int, int]] = []
    index = 0
    while index < len(text):
        if text[index].isspace():
            end = index + 1
            while end < len(text) and text[end].isspace():
                end += 1
            result.append(" ")
            ranges.append((char_ranges[index][0], char_ranges[end - 1][1]))
            index = end
            continue
        result.append(text[index])
        ranges.append(char_ranges[index])
        index += 1
    compact = "".join(result).strip()
    left = len("".join(result)) - len("".join(result).lstrip())
    right = len("".join(result).rstrip())
    return compact, ranges[left:right]


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


_TOKEN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|[0-9]+(?:[A-Za-z]+)?")


def _token_range(source: str, quote: str) -> tuple[int, int] | None:
    source_tokens = [
        (match.start(), match.end(), match.group(0).casefold().replace("'", ""))
        for match in _TOKEN_RE.finditer(source)
    ]
    wanted = [
        match.group(0).casefold().replace("'", "")
        for match in _TOKEN_RE.finditer(quote)
    ]
    if not wanted:
        return None
    positions: dict[str, list[int]] = {}
    for index, (_start, _end, value) in enumerate(source_tokens):
        positions.setdefault(value, []).append(index)
    best: tuple[int, int] | None = None
    for first in positions.get(wanted[0], []):
        start = source_tokens[first][0]
        selected = first
        wanted_index = 1
        while wanted_index < len(wanted):
            candidates = positions.get(wanted[wanted_index], [])
            position = bisect_right(candidates, selected)
            if position >= len(candidates):
                break
            selected = candidates[position]
            wanted_index += 1
        if wanted_index != len(wanted):
            continue
        candidate = (start, source_tokens[selected][1])
        if best is None or candidate[1] - candidate[0] < best[1] - best[0]:
            best = candidate
    return best


def _visible_fragment(value: str) -> str:
    parser = _FragmentParser()
    parser.feed(value)
    parser.close()
    return _normalize_whitespace("".join(parser.parts))


class _FragmentParser(HTMLParser):
    """Extract text from a raw range that starts and ends at text boundaries."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def html_source_path(text_dir: str | Path, source_document_id: str) -> Path | None:
    """Return the acquired HTML path when this instruction source has one."""
    path = Path(text_dir) / f"{source_document_id}.html"
    return path if path.exists() else None
