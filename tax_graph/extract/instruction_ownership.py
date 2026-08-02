"""Deterministic ownership for line-organized instruction sections.

Instruction pages carry their own structure.  A line heading owns its body
through deeper headings until the next heading at the same or a higher level.
This module keeps that source structure intact so a mention of another line
cannot steal an instruction citation.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import re
from typing import Any


_LINE_HEADING_RE = re.compile(
    r"^(?P<marks>#{1,6})\s*(?:\*\*)?lines?\s+(?P<rest>.+?)\s*$",
    re.IGNORECASE,
)
_TABLE_LINE_RE = re.compile(r"^\s*\|\s*(?:\*\*)?([0-9]+[a-z]?)\.", re.IGNORECASE)
_LINE_TOKEN_RE = re.compile(r"\b([0-9]+[a-z]?)\b", re.IGNORECASE)


def instruction_line_owners(spans: Iterable[Any]) -> dict[str, frozenset[str]]:
    """Map each instruction span id to the printed line(s) that own it."""
    owners: dict[str, frozenset[str]] = {}
    current_document = ""
    current_lines: frozenset[str] = frozenset()
    current_level: int | None = None
    for span in spans:
        span_id = _value(span, "span_id")
        relationship = _value(span, "relationship")
        document_id = _value(span, "document_id")
        text = _value(span, "text")
        if relationship == "source" or not span_id:
            continue
        if document_id != current_document:
            current_document = document_id
            current_lines = frozenset()
            current_level = None

        # Real pipeline spans are projections of the persisted
        # instruction_sections frame.  Their explicit owner is authoritative;
        # do not infer it again from prose or from a competing heading parser.
        explicit_owner = _values(span, "owner_lines")
        if explicit_owner:
            owners[span_id] = frozenset(explicit_owner)
            continue

        heading = _line_heading(text)
        if heading is not None:
            level, lines = heading
            current_lines = lines
            current_level = level
            owners[span_id] = lines
            continue

        heading_level = _heading_level(text)
        if heading_level is not None:
            if current_level is not None and heading_level <= current_level:
                current_lines = frozenset()
                current_level = None
            if current_lines:
                owners[span_id] = current_lines
            continue

        table_line = _table_line(text)
        if table_line:
            owners[span_id] = frozenset({table_line})
        elif current_lines:
            owners[span_id] = current_lines
    return owners


def instruction_span_ids_for_line(
    spans: Iterable[Any],
    anchor: str,
    *,
    owners: Mapping[str, Iterable[str]] | None = None,
    owner_document_id: str | None = None,
) -> list[str]:
    """Return exact-owned instruction spans for one line and form context."""
    normalized = str(anchor or "").strip().lower()
    if not normalized:
        return []
    owner_map = owners or instruction_line_owners(spans)
    return [
        str(_value(span, "span_id"))
        for span in spans
        if str(_value(span, "span_id"))
        and _belongs_to_document(span, owner_document_id)
        and normalized in {str(value).lower() for value in owner_map.get(str(_value(span, "span_id")), ())}
    ]


def _belongs_to_document(span: Any, owner_document_id: str | None) -> bool:
    """Keep shared-booklet sections in the form context that owns them."""
    if not owner_document_id:
        return True
    explicit_owner = _value(span, "owner_document_id")
    return not explicit_owner or explicit_owner == owner_document_id


def _line_heading(text: str) -> tuple[int, frozenset[str]] | None:
    match = _LINE_HEADING_RE.match(str(text).strip())
    if not match:
        return None
    rest = match.group("rest")
    # Only the heading's line token prefix is structural.  A title may contain
    # years and other numbers, so stop before the common title delimiters.
    prefix = re.split(r"\s+-\s+|\s*:\s+", rest, maxsplit=1)[0]
    tokens = tuple(token.lower() for token in _LINE_TOKEN_RE.findall(prefix))
    if not tokens:
        return None
    return len(match.group("marks")), frozenset(tokens)


def _heading_level(text: str) -> int | None:
    match = re.match(r"^\s*(#{1,6})\s+", str(text))
    return len(match.group(1)) if match else None


def _table_line(text: str) -> str | None:
    match = _TABLE_LINE_RE.match(str(text))
    return match.group(1).lower() if match else None


def _value(item: Any, key: str) -> str:
    if isinstance(item, Mapping):
        return str(item.get(key) or "")
    return str(getattr(item, key, "") or "")


def _values(item: Any, key: str) -> tuple[str, ...]:
    """Read a serialized or dataclass sequence without changing its values."""
    if isinstance(item, Mapping):
        value = item.get(key) or ()
    else:
        value = getattr(item, key, ()) or ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(entry) for entry in value)
