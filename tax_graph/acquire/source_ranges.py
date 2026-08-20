"""Deterministic source-range binding for acquired text.

The range is the provenance.  A stored quote is only a convenient projection
of the acquired bytes and must be reconstructable from the range list.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Mapping

from tax_graph.acquire.html_source import HtmlSourceIndex, html_source_path


TOKEN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|[0-9]+(?:[A-Za-z]+)?")
DOT_LEADER_RE = re.compile(r"(?:\.{2,}|\.\s+\.|_{2,}|\\_{2,})")


class SourceRangeError(Exception):
    """Base class for typed failures while resolving an acquired source range."""


class SourceDocumentNotFound(SourceRangeError):
    """The acquired text file for a source document does not exist."""


class SourceRangeOutOfBounds(SourceRangeError):
    """A source range is outside the acquired source's coordinates."""


def load_source_text(
    source_document_id: str,
    *,
    text_dir: str | Path,
    prefer_html: bool = True,
) -> str:
    """Load one acquired source text with the range contract's newline rule."""
    html_path = html_source_path(text_dir, source_document_id) if prefer_html else None
    source_path = html_path or (Path(text_dir) / f"{source_document_id}.txt")
    if not source_path.exists():
        raise SourceDocumentNotFound(
            f"missing acquired source text for {source_document_id}: {source_path}"
        )
    with source_path.open("r", encoding="utf-8", newline=None) as handle:
        return handle.read()


def resolve_source_range(
    source_document_id: str,
    start: int,
    end: int,
    *,
    text_dir: str | Path | None = None,
    source_text: str | None = None,
) -> str:
    """Resolve a half-open range in the acquired source text.

    Form-face ranges are character offsets into the acquired ``.txt`` file
    after universal-newline handling. Instruction-document ranges are UTF-8
    byte offsets into the acquired ``.html`` file. The ``source_text`` escape
    hatch is only for callers that already hold that same acquired text; it
    does not permit an HTML or PDF fallback. Missing files and invalid ranges
    raise distinct typed failures, so neither can be mistaken for an empty
    span.
    """
    if (text_dir is None) == (source_text is None):
        raise ValueError("provide exactly one of text_dir or source_text")
    source_is_html = False
    if source_text is None:
        source_is_html = html_source_path(text_dir, source_document_id) is not None
        source_text = load_source_text(source_document_id, text_dir=text_dir)
    else:
        source_is_html = source_document_id.startswith("instructions_") and "<" in source_text[:1000]
    if (
        isinstance(start, bool)
        or isinstance(end, bool)
        or not isinstance(start, int)
        or not isinstance(end, int)
        or start < 0
        or end < start
        or end > (len(source_text.encode("utf-8")) if source_is_html else len(source_text))
    ):
        raise SourceRangeOutOfBounds(
            f"range {start}:{end} is outside {source_document_id} source "
            f"of length {len(source_text.encode('utf-8')) if source_is_html else len(source_text)}"
        )
    if source_is_html:
        return source_text.encode("utf-8")[start:end].decode("utf-8")
    return source_text[start:end]


@dataclass(frozen=True)
class SourceToken:
    """One lexical source token and its character offsets."""

    value: str
    start: int
    end: int


@dataclass(frozen=True)
class SourceAlignment:
    """One ordered lexical match in an acquired source."""

    token_indexes: tuple[int, ...]


class SourceTextIndex:
    """Index one acquired text once for repeatable quote binding."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.tokens = tuple(
            SourceToken(_token_value(match.group(0)), match.start(), match.end())
            for match in TOKEN_RE.finditer(text)
        )
        positions: dict[str, list[int]] = {}
        for index, token in enumerate(self.tokens):
            positions.setdefault(token.value, []).append(index)
        self.positions = {key: tuple(value) for key, value in positions.items()}

    def align(
        self,
        quote: str,
        *,
        start: int = 0,
        end: int | None = None,
    ) -> SourceAlignment | None:
        """Find the shortest source-order match for a quote in a byte window."""
        wanted = tuple(_token_value(match.group(0)) for match in TOKEN_RE.finditer(quote))
        if not wanted:
            return None
        wanted_normalized = normalize_source_quote(quote)
        limit = len(self.text) if end is None else end
        best: tuple[tuple[int, int, int, int], tuple[int, ...]] | None = None
        for first in self.positions.get(wanted[0], ()):
            if self.tokens[first].start < start:
                continue
            selected = [first]
            current = first
            for wanted_token in wanted[1:]:
                next_index = next(
                    (
                        candidate
                        for candidate in self.positions.get(wanted_token, ())
                        if candidate > current and self.tokens[candidate].end <= limit
                    ),
                    None,
                )
                if next_index is None:
                    break
                selected.append(next_index)
                current = next_index
            else:
                if self.tokens[selected[-1]].end <= limit:
                    skipped = sum(
                        max(0, current_index - previous_index - 1)
                        for previous_index, current_index in zip(
                            selected, selected[1:]
                        )
                    )
                    span = self.tokens[selected[-1]].end - self.tokens[selected[0]].start
                    # Prefer a contiguous source passage over a shorter span
                    # that skips unrelated lexical tokens.  The latter is
                    # especially dangerous in instruction tables, where
                    # repeated words such as "line" and "enter" occur on
                    # many neighbouring rows.
                    candidate_alignment = SourceAlignment(tuple(selected))
                    candidate_ranges = self.ranges_for_alignment(candidate_alignment)
                    exact = int(
                        self.quote_for_ranges(candidate_ranges) != wanted_normalized
                    )
                    score = (exact, skipped, span, selected[0])
                    candidate = (score, tuple(selected))
                    if best is None or candidate[0] < best[0]:
                        best = candidate
        return SourceAlignment(best[1]) if best is not None else None

    def ranges_for_alignment(
        self,
        alignment: SourceAlignment,
    ) -> tuple[dict[str, int], ...]:
        """Return ordered ranges that omit skipped source tokens and leaders."""
        indexes = alignment.token_indexes
        if not indexes:
            return ()
        ranges: list[dict[str, int]] = []
        range_start = self._token_start_with_punctuation(indexes[0])
        previous = indexes[0]
        for current in indexes[1:]:
            gap = self.text[self.tokens[previous].end : self.tokens[current].start]
            skipped_tokens = current - previous - 1
            if skipped_tokens or DOT_LEADER_RE.search(gap):
                ranges.append(
                    {
                        "start": range_start,
                        "end": self._token_end_with_punctuation(previous),
                    }
                )
                range_start = self._token_start_with_punctuation(current)
            previous = current
        ranges.append(
            {
                "start": range_start,
                "end": self._token_end_with_punctuation(previous),
            }
        )
        return tuple(ranges)

    def _token_end_with_punctuation(self, token_index: int) -> int:
        """Include punctuation attached to a matched source token."""
        end = self.tokens[token_index].end
        while end < len(self.text) and self.text[end] in ")]};:,!?+-%":
            end += 1
        if (
            end < len(self.text)
            and self.text[end] == "."
            and not DOT_LEADER_RE.match(self.text, end)
        ):
            end += 1
        # Form rows sometimes render an empty input marker as ``( )``.  It
        # is part of the stored quote even though parentheses are not lexical
        # tokens, so retain a punctuation-only balanced suffix after the last
        # matched word.  Stop at the closing delimiter; do not consume the
        # following row or a dot leader.
        cursor = end
        while cursor < len(self.text) and self.text[cursor].isspace():
            cursor += 1
        if cursor < len(self.text) and self.text[cursor] in "([{":
            closing = cursor
            while closing < len(self.text):
                character = self.text[closing]
                if character.isalnum():
                    break
                if character in ")]}":
                    end = closing + 1
                    break
                closing += 1
        elif cursor < len(self.text) and self.text[cursor] in ")]};:,!?+-%":
            while cursor < len(self.text) and self.text[cursor] in ")]};:,!?+-%":
                cursor += 1
            end = cursor
        return end

    def _token_start_with_punctuation(self, token_index: int) -> int:
        """Include an opening marker attached to the first source token."""
        start = self.tokens[token_index].start
        cursor = start
        while cursor > 0 and self.text[cursor - 1].isspace():
            cursor -= 1
        if cursor > 0 and self.text[cursor - 1] in "([{+-":
            start = cursor - 1
        return start

    def quote_for_ranges(self, ranges: Iterable[Mapping[str, int]]) -> str:
        """Render a normalized quote from source ranges without adding prose."""
        return normalize_source_quote(
            " ".join(
                resolve_source_range(
                    "source_index",
                    int(item["start"]),
                    int(item["end"]),
                    source_text=self.text,
                )
                for item in ranges
            )
        )

    def ranges_for_quote(
        self,
        quote: str,
        *,
        start: int = 0,
        end: int | None = None,
    ) -> tuple[dict[str, int], ...] | None:
        """Bind a quote and return source ranges, or ``None`` when absent."""
        alignment = self.align(quote, start=start, end=end)
        if alignment is None:
            return None
        return self.ranges_for_alignment(alignment)


def normalize_source_quote(value: str) -> str:
    """Normalize only layout whitespace in a source-derived quote."""
    return re.sub(r"\s+", " ", value).strip()


def _token_value(value: str) -> str:
    """Normalize lexical spelling while retaining punctuation in source slices."""
    return value.casefold().replace("'", "")
