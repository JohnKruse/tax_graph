"""Deterministic source-range binding for acquired text.

The range is the provenance.  A stored quote is only a convenient projection
of the acquired bytes and must be reconstructable from the range list.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Mapping


TOKEN_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|[0-9]+(?:[A-Za-z]+)?")
DOT_LEADER_RE = re.compile(r"(?:\.{2,}|\.\s+\.|_{2,}|\\_{2,})")


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
        limit = len(self.text) if end is None else end
        best: tuple[tuple[int, int, int], tuple[int, ...]] | None = None
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
                    score = (skipped, span, selected[0])
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
        range_start = self.tokens[indexes[0]].start
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
                range_start = self.tokens[current].start
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
        while end < len(self.text) and self.text[end] in ")]};:,":
            end += 1
        return end

    def quote_for_ranges(self, ranges: Iterable[Mapping[str, int]]) -> str:
        """Render a normalized quote from source ranges without adding prose."""
        return normalize_source_quote(
            " ".join(
                self.text[int(item["start"]) : int(item["end"])] for item in ranges
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
