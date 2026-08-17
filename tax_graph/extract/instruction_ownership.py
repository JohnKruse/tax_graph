"""Deterministic ownership for line-organized instruction sections.

Instruction pages carry their own structure.  A line heading owns its body
through deeper headings until the next heading at the same or a higher level.
This module keeps that source structure intact so a mention of another line
cannot steal an instruction citation.  The heading parser below is retained
only as a compatibility fallback for old synthetic spans and old draft
sidecars that lack explicit owner metadata; real pipeline spans come from the
typed instruction_sections frame and never pass through this inference path.
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
    """Return the final ordered packet spans for one line and form context.

    A specific heading wins.  When a printed sub-line such as ``11a`` has no
    specific owner, the numeric heading ``11`` owns its packet.  This is the
    only inheritance performed here; mentions in prose and table addresses
    remain outside the line-owner vocabulary. Empty stubs and nested parent
    sections are removed by the same resolution used by packet assembly.
    """
    return list(
        instruction_span_resolution_for_line(
            spans,
            anchor,
            owners=owners,
            owner_document_id=owner_document_id,
        )["selected_ids"]
    )


def instruction_span_resolution_for_line(
    spans: Iterable[Any],
    anchor: str,
    *,
    owners: Mapping[str, Iterable[str]] | None = None,
    owner_document_id: str | None = None,
) -> dict[str, Any]:
    """Resolve, order, and type one line's instruction packet attachments.

    ``candidate_ids`` is the raw owner-map result. ``selected_ids`` is the
    packet result after stub removal and literal nested-text containment. The
    latter is ordered from specific to general, preserving both when neither
    is safely removable.
    """
    span_list = list(spans)
    normalized = str(anchor or "").strip().lower()
    if not normalized:
        return {
            "candidate_ids": [],
            "selected_ids": [],
            "dropped": [],
            "stubs": [],
            "worksheets": [],
            "specificity": {},
            "specificity_rank": {},
            "attachments": [],
            "inherited": False,
            "ambiguous": False,
        }
    owner_map = owners or instruction_line_owners(span_list)
    candidates = _candidate_ids_for_line(
        span_list,
        normalized,
        owner_map,
        owner_document_id,
    )
    inherited = False
    if not candidates:
        parent = _numeric_parent(normalized)
        if parent is not None:
            candidates = _candidate_ids_for_line(
                span_list,
                parent,
                owner_map,
                owner_document_id,
            )
            inherited = bool(candidates)

    by_id = {
        str(_value(span, "span_id")): span
        for span in span_list
        if str(_value(span, "span_id"))
    }
    specificity_rank = {
        span_id: max(1, len(tuple(owner_map.get(span_id, ()))))
        for span_id in candidates
    }
    specificity = {
        span_id: "specific" if specificity_rank[span_id] == 1 else "general"
        for span_id in candidates
    }
    kind = {
        span_id: _section_kind(by_id[span_id])
        for span_id in candidates
        if span_id in by_id
    }
    stubs = [span_id for span_id in candidates if kind.get(span_id) == "stub"]
    worksheets = [
        span_id for span_id in candidates if kind.get(span_id) == "worksheet"
    ]
    usable = [span_id for span_id in candidates if span_id not in stubs]
    order = {span_id: index for index, span_id in enumerate(candidates)}
    usable.sort(
        key=lambda span_id: (
            specificity_rank[span_id],
            order[span_id],
        )
    )
    dropped: list[dict[str, Any]] = []
    dropped_ids: set[str] = set()
    for span_id in usable:
        span = by_id.get(span_id)
        if span is None:
            continue
        text = _value(span, "text")
        contained_children = [
            child_id
            for child_id in usable
            if child_id != span_id
            and _value(by_id.get(child_id), "text")
            and _value(by_id.get(child_id), "text").casefold() != text.casefold()
            and _value(by_id.get(child_id), "text").casefold() in text.casefold()
        ]
        if contained_children:
            survivor_id = min(
                contained_children,
                key=lambda child_id: len(_value(by_id.get(child_id), "text")),
            )
            dropped_ids.add(span_id)
            dropped.append(
                {
                    "span_id": span_id,
                    "section_id": _value(span, "section_id") or span_id,
                    "kept_span_id": survivor_id,
                    "reason": "nested_text_containment",
                }
            )
    for span_id in stubs:
        dropped_ids.add(span_id)
        dropped.append(
            {
                "span_id": span_id,
                "section_id": _value(by_id.get(span_id), "section_id") or span_id,
                "kept_span_id": None,
                "reason": "stub_section",
            }
        )
    selected = [span_id for span_id in usable if span_id not in dropped_ids]
    attachments = [
        {
            "span_id": span_id,
            "section_id": _value(by_id.get(span_id), "section_id") or span_id,
            "specificity": specificity[span_id],
            "specificity_rank": specificity_rank[span_id],
            "provenance": "WORKSHEET" if span_id in worksheets else "INSTRUCTION",
        }
        for span_id in selected
    ]
    rank_counts: dict[int, int] = {}
    for attachment in attachments:
        if attachment["provenance"] == "WORKSHEET":
            continue
        rank = int(attachment["specificity_rank"])
        rank_counts[rank] = rank_counts.get(rank, 0) + 1
    ambiguous = any(count > 1 for count in rank_counts.values())
    return {
        "candidate_ids": candidates,
        "selected_ids": selected,
        "dropped": dropped,
        "stubs": stubs,
        "worksheets": worksheets,
        "specificity": specificity,
        "specificity_rank": specificity_rank,
        "attachments": attachments,
        "inherited": inherited,
        "ambiguous": ambiguous,
    }


def _candidate_ids_for_line(
    spans: list[Any],
    line: str,
    owners: Mapping[str, Iterable[str]],
    owner_document_id: str | None,
) -> list[str]:
    """Return unique owned section ids in source order."""
    ids: list[str] = []
    seen: set[str] = set()
    for span in spans:
        span_id = str(_value(span, "span_id"))
        if (
            not span_id
            or span_id in seen
            or not _belongs_to_document(span, owner_document_id)
            or line not in {str(value).lower() for value in owners.get(span_id, ())}
        ):
            continue
        seen.add(span_id)
        ids.append(span_id)
    return ids


def _section_kind(span: Any) -> str:
    """Classify packet provenance without changing source ownership."""
    text = _value(span, "text")
    nonempty_lines = [line.strip() for line in text.splitlines() if line.strip()]
    body_lines = [
        line
        for line in nonempty_lines
        if not re.match(r"^#{1,6}\s+", line)
    ]
    if not body_lines:
        return "stub"
    headings = "\n".join(
        line for line in nonempty_lines if re.match(r"^#{1,6}\s+", line)
    )
    if re.search(r"worksheet", headings, re.IGNORECASE):
        return "worksheet"
    return "ordinary"


def instruction_span_profile(span: Any) -> dict[str, Any]:
    """Return stable provenance facts for a projected instruction span."""
    kind = _section_kind(span)
    owner_lines = _values(span, "owner_lines")
    specificity_rank = max(1, len(owner_lines))
    return {
        "provenance": "WORKSHEET" if kind == "worksheet" else "INSTRUCTION",
        "is_stub": kind == "stub",
        "specificity": "specific" if specificity_rank == 1 else "general",
        "specificity_rank": specificity_rank,
    }


def _numeric_parent(anchor: str) -> str | None:
    """Return the numeric heading for an alpha-suffixed printed sub-line."""
    match = re.fullmatch(r"([0-9]+)[a-z]", str(anchor).strip().lower())
    return match.group(1) if match else None


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
