"""Measure heading ownership inside the M20-S119 unclaimed source spans.

This is a deterministic, read-only witness for M20-S120.  It splits each
unclaimed S119 span at every parsed heading, keeps the byte accounting exact,
and records which heading-local line mentions are reachable for the missing
cell join.  It does not repair instruction sections or write graph artifacts.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

import yaml

from pilot.instruction_extent_census import (
    _line_match,
    _normalized_source,
    build_instruction_extent_census,
)
from tax_graph.acquire.manifest import load_manifest


HEADING_NEVER_SECTIONED = "HEADING_NEVER_SECTIONED"
MENTIONED_IN_PROSE_ONLY = "MENTIONED_IN_PROSE_ONLY"
NON_LINE_CONTENT = "NON_LINE_CONTENT"
UNRESOLVED = "UNRESOLVED"
REASONS = (
    HEADING_NEVER_SECTIONED,
    MENTIONED_IN_PROSE_ONLY,
    NON_LINE_CONTENT,
    UNRESOLVED,
)

_LINE_MENTION_RE = re.compile(
    r"(?<![A-Za-z])lines?\s+([0-9]+[a-z]?)(?P<tail>\s*(?:,|and|through|thru|to|or|-)\s*[0-9]+[a-z]?)*",
    re.IGNORECASE,
)
_ALPHA_LINE_RE = re.compile(r"([0-9]+)([a-z])", re.IGNORECASE)
_NON_LINE_TITLE_RE = re.compile(
    r"^(?:future developments|what's new|reminders|table of contents|"
    r"purpose of form|who must file|form .* helpful hints)$",
    re.IGNORECASE,
)


def _fingerprint(value: str) -> str:
    """Return a content fingerprint without persisting acquired prose."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _ascii_title(value: str) -> str:
    """Normalize one acquired heading title to the authored ASCII contract."""
    return " ".join(value.split()).encode("ascii", errors="replace").decode("ascii")


def _expand_line_range(values: Iterable[str]) -> list[str]:
    """Expand an alpha range such as ``17a through 17z``."""
    tokens = [str(value).lower() for value in values]
    if len(tokens) < 2:
        return list(dict.fromkeys(tokens))
    first = _ALPHA_LINE_RE.fullmatch(tokens[0])
    last = _ALPHA_LINE_RE.fullmatch(tokens[-1])
    if not first or not last or first.group(1) != last.group(1):
        return list(dict.fromkeys(tokens))
    start = ord(first.group(2))
    end = ord(last.group(2))
    if end < start or end - start > 25:
        return list(dict.fromkeys(tokens))
    return [f"{first.group(1)}{chr(value)}" for value in range(start, end + 1)]


def _line_mentions(value: str) -> list[str]:
    """Return line tokens mentioned in one heading-local source slice.

    The acquired renderer occasionally welds ``WorksheetLines`` together.
    Splitting that camel-case boundary for matching only lets the measurement
    account for headings such as ``Capital Loss Carryover WorksheetLines 6 and
    14`` without changing the source or its offsets.
    """
    matching_text = re.sub(r"(?<=[a-z])(?=Lines?\b)", " ", value)
    result: list[str] = []
    for match in _LINE_MENTION_RE.finditer(matching_text):
        values = [match.group(1)]
        values.extend(
            re.findall(
                r"(?:,|and|through|thru|to|or|-)\s*([0-9]+[a-z]?)",
                match.group("tail") or "",
                re.IGNORECASE,
            )
        )
        result.extend(_expand_line_range(values))
    return list(dict.fromkeys(result))


def _range_record(source: str, byte_offsets: tuple[int, ...], start: int, end: int) -> dict[str, Any]:
    """Serialize a half-open range with exact source-byte accounting."""
    return {
        "start": start,
        "end": end,
        "byte_start": byte_offsets[start],
        "byte_end": byte_offsets[end],
        "bytes": byte_offsets[end] - byte_offsets[start],
        "text_fingerprint": _fingerprint(source[start:end]),
    }


def _content_kind(title: str, *, parent_start: int, parent_end: int) -> str:
    """Name deterministic negative-control headings without guessing repairs."""
    lowered = re.sub(r"\s+", " ", title).strip().lower()
    if "earned income credit (eic) table" in lowered:
        return "lookup_table"
    if _NON_LINE_TITLE_RE.fullmatch(lowered):
        return "front_matter"
    if lowered.startswith("instructions for ") and parent_start == 0:
        return "front_matter"
    if lowered in {"1040 (and", "instructions", "general instructions"} and parent_start == 0:
        return "front_matter"
    return "line_instruction_or_topic"


def _heading_record(heading: Mapping[str, Any]) -> dict[str, Any]:
    """Copy the stable, non-prose heading identity from S119."""
    return {
        "title": _ascii_title(str(heading.get("title") or "")),
        "level": int(heading.get("level") or 0),
        "line": int(heading.get("line") or 0),
        "start": int(heading.get("start") or 0),
    }


def _split_span(
    source: str,
    byte_offsets: tuple[int, ...],
    span: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Split one S119 unclaimed span at every heading boundary."""
    parent_start = int(span["start"])
    parent_end = int(span["end"])
    headings = sorted(
        (
            dict(heading)
            for heading in span.get("headings_in_span", ())
            if parent_start <= int(heading.get("start") or -1) < parent_end
        ),
        key=lambda heading: (int(heading.get("start") or 0), int(heading.get("line") or 0)),
    )
    boundaries = [parent_start]
    boundaries.extend(
        int(heading["start"])
        for heading in headings
        if int(heading["start"]) > parent_start
    )
    boundaries.append(parent_end)
    rows: list[dict[str, Any]] = []
    heading_by_start = {int(heading["start"]): heading for heading in headings}
    for start, end in zip(boundaries, boundaries[1:]):
        if end <= start:
            continue
        heading = heading_by_start.get(start)
        record = _range_record(source, byte_offsets, start, end)
        record.update(
            {
                "parent_start": parent_start,
                "parent_end": parent_end,
                "parent_classification": span.get("classification"),
                "heading": _heading_record(heading) if heading is not None else None,
                "boundary_kind": "heading" if heading is not None else "unheaded_prefix",
                "governs": _line_mentions(source[start:end]),
            }
        )
        record["content_kind"] = (
            _content_kind(
                str(heading.get("title") or ""),
                parent_start=parent_start,
                parent_end=parent_end,
            )
            if heading is not None
            else "unheaded_prose"
        )
        rows.append(record)
    if not rows:
        raise AssertionError(f"unclaimed span {parent_start}:{parent_end} produced no split rows")
    return rows


def _document_cells_by_booklet(
    root: Path,
    reconciliation: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Attach every S116 cell to the instruction booklet it reads."""
    manifest = load_manifest(root=root)
    entries = manifest.by_document_id()
    cells_by_booklet: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for document_id, document in reconciliation.get("documents", {}).items():
        entry = entries.get(document_id)
        booklet_id = entry.instructions_document_id if entry is not None else None
        if not booklet_id:
            continue
        for cell in document.get("cells", ()):
            row = dict(cell)
            row["document_id"] = document_id
            cells_by_booklet[booklet_id].append(row)
    return cells_by_booklet


def _attach_governed_cells(
    rows: list[dict[str, Any]],
    cells: Iterable[Mapping[str, Any]],
) -> None:
    """Record all known line cells named by each split heading."""
    for row in rows:
        governed: list[dict[str, Any]] = []
        for cell in cells:
            relation = _line_match(str(cell.get("line") or ""), row["governs"])
            if relation is None:
                continue
            governed.append(
                {
                    "cell_id": cell.get("cell_id"),
                    "document_id": cell.get("document_id"),
                    "line": str(cell.get("line") or "").lower(),
                    "s116_bucket": cell.get("bucket"),
                    "relation": relation,
                    "reason": (
                        NON_LINE_CONTENT
                        if row.get("content_kind") in {"lookup_table", "front_matter"}
                        else HEADING_NEVER_SECTIONED
                    ),
                }
            )
        row["governed_cells"] = sorted(
            governed,
            key=lambda item: (str(item.get("document_id")), str(item.get("cell_id"))),
        )


def _cell_classification(
    target: Mapping[str, Any],
    *,
    booklet_spans: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify one no-truncation S116 cell against split heading rows."""
    line = str(target.get("line") or "").lower()
    parent_matches: list[Mapping[str, Any]] = []
    candidates: list[Mapping[str, Any]] = []
    for span in booklet_spans:
        if _line_match(line, span.get("governs") or ()) is None:
            continue
        parent_matches.append(span)
        for row in span.get("split_rows", ()):
            if _line_match(line, row.get("governs") or ()) is not None:
                candidates.append(row)

    if not candidates:
        reason = MENTIONED_IN_PROSE_ONLY if parent_matches else UNRESOLVED
    elif all(row.get("content_kind") in {"lookup_table", "front_matter"} for row in candidates):
        reason = NON_LINE_CONTENT
    else:
        reason = HEADING_NEVER_SECTIONED

    headings = [
        {
            **dict(row["heading"]),
            "content_kind": row.get("content_kind"),
            "start": row["start"],
            "end": row["end"],
            "relation": _line_match(line, row.get("governs") or ()),
        }
        for row in sorted(candidates, key=lambda item: (item["start"], item["end"]))
        if row.get("heading") is not None
    ]
    return {
        "target_type": "cell",
        "booklet_id": target.get("booklet_id"),
        "source_bucket": target.get("source_bucket"),
        "line": line,
        "cell_id": target.get("cell_id"),
        "truncated_body_found": False,
        "reason": reason,
        "governing_headings": headings,
        "parent_spans": [
            {
                "start": span["start"],
                "end": span["end"],
                "classification": span.get("classification"),
            }
            for span in parent_matches
        ],
    }


def _ranking(
    missing_cells: Iterable[Mapping[str, Any]],
    *,
    all_cells_by_document: Mapping[str, list[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    """Rank heading groups by the missing cells they could recover."""
    groups: dict[tuple[str, int, str, int], set[str]] = defaultdict(set)
    for cell in missing_cells:
        if cell.get("reason") != HEADING_NEVER_SECTIONED:
            continue
        headings = cell.get("governing_headings") or []
        if not headings:
            continue
        heading = headings[0]
        key = (
            str(cell.get("booklet_id")),
            int(heading.get("level") or 0),
            str(heading.get("title") or ""),
            int(heading.get("start") or 0),
        )
        groups[key].add(str(cell.get("cell_id")))

    ranking = [
        {
            "booklet_id": booklet_id,
            "heading_level": level,
            "heading_title": title,
            "heading_start": start,
            "scope": "missing_booklet_mentions",
            "cells_recovered": len(cell_ids),
            "cell_ids": sorted(cell_ids),
        }
        for (booklet_id, level, title, start), cell_ids in groups.items()
    ]

    schedule_1a_cells = all_cells_by_document.get("schedule_1a_2025", ())
    if schedule_1a_cells:
        ranking.append(
            {
                "booklet_id": "instructions_form_1040_2025",
                "heading_level": 1,
                "heading_title": "Instructions for Schedule 1-A",
                "heading_start": 560429,
                "scope": "all_form_cells",
                "recovery_basis": "chapter_context_not_currently_sectioned",
                "cells_recovered": len(schedule_1a_cells),
                "cell_ids": sorted(str(cell.get("cell_id")) for cell in schedule_1a_cells),
            }
        )
    ranking.sort(
        key=lambda item: (
            -int(item["cells_recovered"]),
            str(item["booklet_id"]),
            int(item["heading_level"]),
            int(item["heading_start"]),
        )
    )
    return ranking


def build_instruction_extent_split(
    *,
    root: str | Path,
    year: str | int = "2025",
    census: Mapping[str, Any] | None = None,
    reconciliation_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build the deterministic M20-S120 split and reachability report."""
    root_path = Path(root).resolve()
    census_report = census or build_instruction_extent_census(root=root_path, year=year)
    if reconciliation_path is None:
        reconciliation_path = root_path / "plans" / "m20_s116_instruction_reconciliation.yaml"
    reconciliation_file = Path(reconciliation_path)
    if not reconciliation_file.is_absolute():
        reconciliation_file = root_path / reconciliation_file
    reconciliation = yaml.safe_load(reconciliation_file.read_text(encoding="ascii"))
    if not isinstance(reconciliation, Mapping):
        raise ValueError(f"expected mapping in {reconciliation_file}")

    cells_by_booklet = _document_cells_by_booklet(root_path, reconciliation)
    all_cells_by_document = {
        str(document_id): [dict(cell) for cell in document.get("cells", ())]
        for document_id, document in reconciliation.get("documents", {}).items()
    }
    booklet_reports: dict[str, dict[str, Any]] = {}
    all_split_rows: list[dict[str, Any]] = []
    for booklet_id, booklet in census_report["booklets"].items():
        source_path = root_path / str(booklet["source_path"])
        source, byte_offsets = _normalized_source(source_path.read_bytes())
        parent_reports: list[dict[str, Any]] = []
        for span in booklet.get("unclaimed_spans", ()):
            split_rows = _split_span(source, byte_offsets, span)
            _attach_governed_cells(split_rows, cells_by_booklet.get(booklet_id, ()))
            parent_report = {
                "start": span["start"],
                "end": span["end"],
                "byte_start": span["byte_start"],
                "byte_end": span["byte_end"],
                "bytes": span["bytes"],
                "classification": span.get("classification"),
                "governs": list(span.get("governs") or ()),
                "split_rows": split_rows,
            }
            parent_reports.append(parent_report)
            all_split_rows.extend(
                {
                    **row,
                    "booklet_id": booklet_id,
                }
                for row in split_rows
            )
        booklet_reports[booklet_id] = {
            "source_path": booklet["source_path"],
            "source_sha256": booklet["source_sha256"],
            "file_size_bytes": booklet["file_size_bytes"],
            "parent_span_count": len(parent_reports),
            "split_row_count": sum(len(report["split_rows"]) for report in parent_reports),
            "parent_spans": parent_reports,
        }

    missing_cells = []
    for row in census_report["s116_join"]["rows"]:
        if row.get("target_type") != "cell" or row.get("truncated_body_found"):
            continue
        booklet_id = str(row["booklet_id"])
        booklet_spans = booklet_reports[booklet_id]["parent_spans"]
        missing_cells.append(
            _cell_classification(
                {**row, "booklet_id": booklet_id},
                booklet_spans=booklet_spans,
            )
        )
    missing_cells.sort(key=lambda row: str(row.get("cell_id")))

    heading_rows = [row for row in all_split_rows if row.get("heading") is not None]
    negative_controls = {
        "earned_income_credit_table": {
            "actionable": False,
            "row_count": sum(row.get("content_kind") == "lookup_table" for row in heading_rows),
            "heading_titles": sorted(
                {row["heading"]["title"] for row in heading_rows if row.get("content_kind") == "lookup_table"}
            ),
        },
        "front_matter": {
            "actionable": False,
            "row_count": sum(row.get("content_kind") == "front_matter" for row in heading_rows),
            "heading_titles": sorted(
                {row["heading"]["title"] for row in heading_rows if row.get("content_kind") == "front_matter"}
            ),
        },
    }
    reason_counts = {reason: sum(row["reason"] == reason for row in missing_cells) for reason in REASONS}
    return {
        "schema_version": 1,
        "round": "M20-S120",
        "year": str(year),
        "source_report": "plans/m20_s119_instruction_extent_census.yaml",
        "source_unit": "UTF-8 bytes mapped from deterministic text offsets",
        "classification_policy": {
            HEADING_NEVER_SECTIONED: "heading-local line mention in an unclaimed span; no instruction section owns the range",
            MENTIONED_IN_PROSE_ONLY: "the parent span mentions the line but no split heading owns the mention",
            NON_LINE_CONTENT: "the only matching heading-local content is front matter or a lookup table",
            UNRESOLVED: "no unclaimed span in the booklet mentions the target line",
        },
        "counts": {
            "instruction_booklets": len(booklet_reports),
            "unclaimed_parent_spans": sum(report["parent_span_count"] for report in booklet_reports.values()),
            "split_rows": sum(report["split_row_count"] for report in booklet_reports.values()),
            "heading_rows": len(heading_rows),
            "cells_with_no_truncated_body": len(missing_cells),
            "reason_counts": reason_counts,
        },
        "booklets": booklet_reports,
        "cell_classifications": missing_cells,
        "recovery_ranking": _ranking(
            missing_cells,
            all_cells_by_document=all_cells_by_document,
        ),
        "negative_controls": negative_controls,
    }


def write_instruction_extent_split(report: Mapping[str, Any], path: str | Path) -> Path:
    """Write the ASCII-only checked-in S120 measurement artifact."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        yaml.safe_dump(dict(report), sort_keys=False, allow_unicode=False),
        encoding="ascii",
        newline="\n",
    )
    return destination


def main() -> int:
    """Build and write the M20-S120 measurement artifact."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--year", default="2025")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("plans/m20_s120_instruction_extent_split.yaml"),
    )
    args = parser.parse_args()
    report = build_instruction_extent_split(root=args.root, year=args.year)
    output = args.output if args.output.is_absolute() else args.root / args.output
    write_instruction_extent_split(report, output)
    print(
        "instruction extent split: "
        f"{report['counts']['instruction_booklets']} booklets, "
        f"{report['counts']['split_rows']} split rows, "
        f"{report['counts']['cells_with_no_truncated_body']} cells"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
