"""Measure ownership of every acquired instruction-booklet source unit.

This is a deterministic, read-only witness for M20-S119.  It uses the current
instruction section locators, reports gaps instead of repairing them, and
joins truncated bodies back to the S116 reconciliation report.  The output
contains source offsets and UTF-8 byte counts, but never copies acquired prose.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

import yaml

from tax_graph.acquire.manifest import AcquisitionManifest, ManifestEntry, load_manifest
from tax_graph.config import get_config_value, load_config
from tax_graph.extract.instruction_sections import (
    InstructionSection,
    build_instruction_sections,
    _parse_headings,
)


TRUNCATED_BODY = "TRUNCATED_BODY"
OTHER_SECTION_TERRITORY = "OTHER_SECTION_TERRITORY"
NON_LINE_REGION = "NON_LINE_REGION"
JOIN_CELL_BUCKET = "CELL WITH NO INSTRUCTION + BOOKLET MENTIONS IT"
JOIN_STUB_BUCKET = "STUB SECTION"
LINE_MENTION_RE = re.compile(r"\blines?\s+([0-9]+[a-z]?)\b", re.IGNORECASE)


def _source_path(root: Path, year: str, document_id: str) -> Path:
    """Return the configured acquired-text path for one booklet."""
    config = load_config(root=root)
    raw_store = Path(get_config_value(config, "project.paths.raw_store", ".cache/raw"))
    if not raw_store.is_absolute():
        raw_store = root / raw_store
    return raw_store / year / f"{document_id}.txt"


def _instruction_entries(manifest: AcquisitionManifest) -> tuple[ManifestEntry, ...]:
    """Return every manifest entry that is an acquired instruction booklet."""
    return tuple(
        entry
        for entry in manifest.documents
        if entry.kind == "instructions"
    )


def _unique_sections(sections: Iterable[InstructionSection]) -> tuple[InstructionSection, ...]:
    """Remove repeated line-token projections of one section locator."""
    result: list[InstructionSection] = []
    seen: set[str] = set()
    for section in sections:
        if section.section_id in seen:
            continue
        seen.add(section.section_id)
        result.append(section)
    return tuple(result)


def _ascii_preview(value: str, limit: int = 240) -> str:
    """Return a short ASCII-only heading or source preview."""
    compact = " ".join(value.split())[:limit]
    return compact.encode("ascii", errors="replace").decode("ascii")


def _fingerprint(value: str) -> str:
    """Fingerprint a source slice without storing its contents."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _line_mentions(value: str) -> list[str]:
    """Return printed line addresses explicitly named by a source span."""
    return list(dict.fromkeys(match.group(1).lower() for match in LINE_MENTION_RE.finditer(value)))


def _numeric_parent(line: str) -> str | None:
    """Return the numeric parent of an alpha-suffixed printed line."""
    match = re.fullmatch(r"([0-9]+)[a-z]", str(line).strip().lower())
    return match.group(1) if match else None


def _line_match(target: str, governed_lines: Iterable[str]) -> str | None:
    """Return the relationship between a target line and governed lines."""
    normalized = str(target).strip().lower()
    governed = {str(line).strip().lower() for line in governed_lines}
    if normalized in governed:
        return "exact"
    parent = _numeric_parent(normalized)
    if parent is not None and parent in governed:
        return "numeric_parent"
    return None


def _byte_offsets(source: str) -> tuple[int, ...]:
    """Map each text offset to its corresponding UTF-8 byte offset."""
    offsets = [0]
    total = 0
    for character in source:
        total += len(character.encode("utf-8"))
        offsets.append(total)
    return tuple(offsets)


def _range_record(
    source: str,
    byte_offsets: tuple[int, ...],
    start: int,
    end: int,
) -> dict[str, Any]:
    """Serialize a half-open text range with its exact UTF-8 byte count."""
    return {
        "start": start,
        "end": end,
        "byte_start": byte_offsets[start],
        "byte_end": byte_offsets[end],
        "bytes": byte_offsets[end] - byte_offsets[start],
        "text_fingerprint": _fingerprint(source[start:end]),
        "preview": _ascii_preview(source[start:end]),
    }


def _section_record(
    source: str,
    byte_offsets: tuple[int, ...],
    section: InstructionSection,
) -> dict[str, Any]:
    """Serialize one unique instruction section locator."""
    locator = section.locator
    record = _range_record(
        source,
        byte_offsets,
        locator.start_offset,
        locator.end_offset,
    )
    record.update(
        {
            "section_id": section.section_id,
            "owner_document_id": section.document_id,
            "lines": list(section.line_tokens),
            "heading": _ascii_preview(section.heading),
            "heading_level": locator.heading_level,
            "start_line": locator.start_line,
            "end_line": locator.end_line,
            "is_stub": not any(line.strip() for line in section.text.splitlines()[1:]),
        }
    )
    return record


def _coverage_parts(
    source_length: int,
    sections: Iterable[InstructionSection],
) -> list[tuple[int, int, tuple[str, ...]]]:
    """Sweep section locators into disjoint text ranges and active owners."""
    starts: dict[int, list[str]] = defaultdict(list)
    ends: dict[int, list[str]] = defaultdict(list)
    points = {0, source_length}
    for section in sections:
        start = section.locator.start_offset
        end = section.locator.end_offset
        if not 0 <= start <= end <= source_length:
            raise ValueError(
                f"section {section.section_id} has invalid locator {start}:{end} "
                f"for source length {source_length}"
            )
        if start == end:
            continue
        starts[start].append(section.section_id)
        ends[end].append(section.section_id)
        points.add(start)
        points.add(end)

    ordered_points = sorted(points)
    active: set[str] = set()
    parts: list[tuple[int, int, tuple[str, ...]]] = []
    for index, point in enumerate(ordered_points[:-1]):
        active.difference_update(ends.get(point, ()))
        active.update(starts.get(point, ()))
        next_point = ordered_points[index + 1]
        if point == next_point:
            continue
        owners = tuple(sorted(active))
        if parts and parts[-1][1] == point and parts[-1][2] == owners:
            parts[-1] = (parts[-1][0], next_point, owners)
        else:
            parts.append((point, next_point, owners))
    return parts


def _section_before(
    sections: tuple[InstructionSection, ...],
    start: int,
) -> InstructionSection | None:
    """Return the latest section ending at or before an unclaimed run."""
    candidates = [section for section in sections if section.locator.end_offset <= start]
    if not candidates:
        return None
    return max(candidates, key=lambda section: (section.locator.end_offset, section.section_id))


def _section_after(
    sections: tuple[InstructionSection, ...],
    end: int,
) -> InstructionSection | None:
    """Return the earliest section starting at or after an unclaimed run."""
    candidates = [section for section in sections if section.locator.start_offset >= end]
    if not candidates:
        return None
    return min(candidates, key=lambda section: (section.locator.start_offset, section.section_id))


def _heading_record(heading: Any) -> dict[str, Any]:
    """Serialize a parsed heading without copying acquired prose."""
    return {
        "title": _ascii_preview(heading.title),
        "level": heading.level,
        "line": heading.line_number,
        "start": heading.start_offset,
    }


def _classify_unclaimed(
    source: str,
    byte_offsets: tuple[int, ...],
    start: int,
    end: int,
    sections: tuple[InstructionSection, ...],
    headings: tuple[Any, ...],
) -> dict[str, Any]:
    """Classify one unclaimed span from the surrounding heading hierarchy."""
    record = _range_record(source, byte_offsets, start, end)
    previous = _section_before(sections, start)
    following = _section_after(sections, end)
    in_span = tuple(
        heading
        for heading in headings
        if start <= heading.start_offset < end
    )
    first_heading = in_span[0] if in_span else None
    classification = NON_LINE_REGION
    reason = "no_line_owned_section_in_heading_hierarchy"
    if previous is not None and first_heading is not None:
        previous_level = previous.locator.heading_level
        previous_is_stub = not any(
            line.strip() for line in previous.text.splitlines()[1:]
        )
        if first_heading.level == previous_level and previous_is_stub:
            classification = TRUNCATED_BODY
            reason = "same_level_heading_follows_stub_section"
        else:
            classification = OTHER_SECTION_TERRITORY
            reason = "heading_has_no_line_owned_section"
    elif first_heading is not None:
        reason = "front_matter_or_non_line_heading"

    record.update(
        {
            "classification": classification,
            "classification_reason": reason,
            "governs": _line_mentions(source[start:end]),
            "heading": _heading_record(first_heading) if first_heading is not None else None,
            "headings_in_span": [_heading_record(heading) for heading in in_span],
            "preceding_section_id": previous.section_id if previous is not None else None,
            "following_section_id": following.section_id if following is not None else None,
        }
    )
    return record


def _span_for_owner(
    sections: tuple[InstructionSection, ...],
    section_id: str,
) -> InstructionSection | None:
    """Find a section locator by its stable section id."""
    return next((section for section in sections if section.section_id == section_id), None)


def _join_row(
    target: Mapping[str, Any],
    *,
    booklet_id: str,
    booklet_report: Mapping[str, Any],
    target_type: str,
    source_bucket: str,
) -> dict[str, Any]:
    """Join one S116 cell or stub target to measured truncated bodies."""
    line = str(target.get("line") or "").lower()
    spans = [
        span
        for span in booklet_report.get("unclaimed_spans", ())
        if span.get("classification") == TRUNCATED_BODY
    ]
    candidates: list[dict[str, Any]] = []
    if target_type == "cell":
        for span in spans:
            relation = _line_match(line, span.get("governs") or ())
            if relation is None:
                continue
            candidates.append(
                {
                    "start": span["start"],
                    "end": span["end"],
                    "byte_start": span["byte_start"],
                    "byte_end": span["byte_end"],
                    "bytes": span["bytes"],
                    "classification": span["classification"],
                    "heading": span.get("heading"),
                    "relation": relation,
                    "preceding_section_id": span.get("preceding_section_id"),
                    "following_section_id": span.get("following_section_id"),
                }
            )

    row: dict[str, Any] = {
        "target_type": target_type,
        "booklet_id": booklet_id,
        "source_bucket": source_bucket,
        "line": line,
        "cell_id": target.get("cell_id"),
        "section_id": target.get("section_id"),
        "truncated_body_found": bool(candidates),
        "truncated_body_bytes": sum(int(item["bytes"]) for item in candidates),
        "truncated_body_spans": candidates,
    }
    if target_type == "stub_section":
        section_id = str(target.get("section_id") or "")
        section = _span_for_owner(
            tuple(booklet_report.get("_sections_for_join", ())),
            section_id,
        )
        if section is not None:
            end = section.locator.end_offset
            adjacent = [
                span
                for span in spans
                if int(span["start"]) == end
            ]
            adjacent_records = [
                {
                    "start": span["start"],
                    "end": span["end"],
                    "byte_start": span["byte_start"],
                    "byte_end": span["byte_end"],
                    "bytes": span["bytes"],
                    "classification": span["classification"],
                    "heading": span.get("heading"),
                    "relation": "immediately_follows_section",
                    "preceding_section_id": span.get("preceding_section_id"),
                    "following_section_id": span.get("following_section_id"),
                }
                for span in adjacent
            ]
            row["truncated_body_found"] = bool(adjacent_records)
            row["truncated_body_bytes"] = sum(
                int(item["bytes"]) for item in adjacent_records
            )
            row["truncated_body_spans"] = adjacent_records
            row["section_extent"] = {
                "start": section.locator.start_offset,
                "end": section.locator.end_offset,
                "heading_level": section.locator.heading_level,
            }
            row["immediately_following_truncated_body"] = bool(adjacent)
            row["immediately_following_truncated_body_bytes"] = sum(
                int(span["bytes"]) for span in adjacent
            )
            row["immediately_following_truncated_body_spans"] = adjacent_records
        else:
            row["section_extent"] = None
            row["immediately_following_truncated_body"] = False
            row["immediately_following_truncated_body_bytes"] = 0
            row["immediately_following_truncated_body_spans"] = []
    return row


def _build_join(
    report: Mapping[str, Any],
    *,
    manifest: AcquisitionManifest,
    booklet_reports: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the complete S116 missing-cell and stub-section join."""
    entries = manifest.by_document_id()
    rows: list[dict[str, Any]] = []
    for document_id in sorted(report.get("documents", {})):
        document_report = report["documents"][document_id]
        entry = entries.get(document_id)
        booklet_id = entry.instructions_document_id if entry is not None else None
        if not booklet_id or booklet_id not in booklet_reports:
            raise ValueError(f"S116 target {document_id} has no measured booklet")
        booklet_report = booklet_reports[booklet_id]
        for cell in document_report.get("cells", ()):
            if cell.get("bucket") != JOIN_CELL_BUCKET:
                continue
            rows.append(
                _join_row(
                    cell,
                    booklet_id=booklet_id,
                    booklet_report=booklet_report,
                    target_type="cell",
                    source_bucket=JOIN_CELL_BUCKET,
                )
            )
        for instruction in document_report.get("instructions", ()):
            if instruction.get("bucket") != JOIN_STUB_BUCKET:
                continue
            rows.append(
                _join_row(
                    instruction,
                    booklet_id=booklet_id,
                    booklet_report=booklet_report,
                    target_type="stub_section",
                    source_bucket=JOIN_STUB_BUCKET,
                )
            )
    rows.sort(
        key=lambda row: (
            row["target_type"],
            str(row.get("cell_id") or ""),
            str(row.get("section_id") or ""),
        )
    )
    return {
        "source_report": "plans/m20_s116_instruction_reconciliation.yaml",
        "cell_bucket": JOIN_CELL_BUCKET,
        "stub_bucket": JOIN_STUB_BUCKET,
        "counts": {
            "cells": sum(row["target_type"] == "cell" for row in rows),
            "stub_sections": sum(row["target_type"] == "stub_section" for row in rows),
            "rows": len(rows),
            "cells_with_truncated_body": sum(
                row["target_type"] == "cell" and row["truncated_body_found"]
                for row in rows
            ),
            "stub_sections_with_immediately_following_truncated_body": sum(
                row["target_type"] == "stub_section"
                and row["immediately_following_truncated_body"]
                for row in rows
            ),
        },
        "rows": rows,
    }


def build_instruction_extent_census(
    *,
    root: str | Path,
    year: str | int = "2025",
    reconciliation_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build the read-only M20-S119 census and S116 causal join."""
    root_path = Path(root).resolve()
    year_text = str(year)
    manifest = load_manifest(root=root_path)
    booklet_reports: dict[str, dict[str, Any]] = {}
    for entry in sorted(_instruction_entries(manifest), key=lambda item: item.document_id):
        source_path = _source_path(root_path, year_text, entry.document_id)
        if not source_path.exists():
            raise FileNotFoundError(f"missing acquired instruction booklet: {source_path}")
        source = source_path.read_text(encoding="utf-8")
        frame = build_instruction_sections(
            source,
            source_document_id=entry.document_id,
            year=year_text,
            source_path=source_path,
        )
        sections = _unique_sections(frame.sections)
        byte_offsets = _byte_offsets(source)
        headings = _parse_headings(source)
        parts = _coverage_parts(len(source), sections)
        unclaimed_spans: list[dict[str, Any]] = []
        overlap_spans: list[dict[str, Any]] = []
        claimed_exactly_once_bytes = 0
        unclaimed_bytes = 0
        overlap_bytes = 0
        overlap_extra_claim_bytes = 0
        for start, end, owners in parts:
            bytes_in_part = byte_offsets[end] - byte_offsets[start]
            if len(owners) == 0:
                unclaimed_spans.append(
                    _classify_unclaimed(
                        source,
                        byte_offsets,
                        start,
                        end,
                        sections,
                        headings,
                    )
                )
                unclaimed_bytes += bytes_in_part
            elif len(owners) == 1:
                claimed_exactly_once_bytes += bytes_in_part
            else:
                overlap_record = _range_record(source, byte_offsets, start, end)
                overlap_record.update(
                    {
                        "claim_count": len(owners),
                        "section_ids": list(owners),
                    }
                )
                overlap_spans.append(overlap_record)
                overlap_bytes += bytes_in_part
                overlap_extra_claim_bytes += bytes_in_part * (len(owners) - 1)

        file_bytes = byte_offsets[-1]
        reconciled_bytes = claimed_exactly_once_bytes + unclaimed_bytes + overlap_bytes
        if reconciled_bytes != file_bytes:
            raise AssertionError(
                f"{entry.document_id}: census does not reconcile "
                f"{reconciled_bytes} != {file_bytes}"
            )
        classification_counts = {
            kind: sum(span["classification"] == kind for span in unclaimed_spans)
            for kind in (TRUNCATED_BODY, OTHER_SECTION_TERRITORY, NON_LINE_REGION)
        }
        classification_bytes = {
            kind: sum(
                int(span["bytes"])
                for span in unclaimed_spans
                if span["classification"] == kind
            )
            for kind in (TRUNCATED_BODY, OTHER_SECTION_TERRITORY, NON_LINE_REGION)
        }
        section_records = [
            _section_record(source, byte_offsets, section)
            for section in sections
        ]
        booklet_reports[entry.document_id] = {
            "source_path": str(source_path.relative_to(root_path)).replace("\\", "/"),
            "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "source_text_length": len(source),
            "file_size_bytes": file_bytes,
            "section_count": len(sections),
            "sections": section_records,
            "_sections_for_join": sections,
            "claims": {
                "claimed_exactly_once_bytes": claimed_exactly_once_bytes,
                "unclaimed_bytes": unclaimed_bytes,
                "overlap_bytes": overlap_bytes,
                "overlap_extra_claim_bytes": overlap_extra_claim_bytes,
                "claimed_exactly_once_plus_unclaimed_plus_overlap_bytes": reconciled_bytes,
                "reconciles_to_file_size": reconciled_bytes == file_bytes,
            },
            "classification_counts": classification_counts,
            "classification_bytes": classification_bytes,
            "overlaps": overlap_spans,
            "unclaimed_spans": unclaimed_spans,
        }

    if reconciliation_path is None:
        reconciliation_path = root_path / "plans" / "m20_s116_instruction_reconciliation.yaml"
    reconciliation_file = Path(reconciliation_path)
    if not reconciliation_file.is_absolute():
        reconciliation_file = root_path / reconciliation_file
    s116 = yaml.safe_load(reconciliation_file.read_text(encoding="ascii"))
    if not isinstance(s116, Mapping):
        raise ValueError(f"expected mapping in {reconciliation_file}")

    join = _build_join(
        s116,
        manifest=manifest,
        booklet_reports=booklet_reports,
    )
    for booklet_report in booklet_reports.values():
        booklet_report.pop("_sections_for_join", None)
    return {
        "schema_version": 1,
        "round": "M20-S119",
        "year": year_text,
        "scope": "manifest entries with kind=instructions",
        "source_unit": "UTF-8 bytes mapped from deterministic text offsets",
        "classification_policy": {
            TRUNCATED_BODY: "same-level heading after a section has no line-owned section",
            OTHER_SECTION_TERRITORY: "higher-level heading after a section has no line-owned section",
            NON_LINE_REGION: "front matter, deeper unowned heading, or no heading context",
        },
        "counts": {
            "instruction_booklets": len(booklet_reports),
            "sections": sum(report["section_count"] for report in booklet_reports.values()),
            "overlap_spans": sum(len(report["overlaps"]) for report in booklet_reports.values()),
            "unclaimed_spans": sum(
                len(report["unclaimed_spans"]) for report in booklet_reports.values()
            ),
        },
        "booklets": booklet_reports,
        "s116_join": join,
    }


def write_instruction_extent_census(report: Mapping[str, Any], path: str | Path) -> Path:
    """Write one ASCII-only checked-in census artifact."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        yaml.safe_dump(dict(report), sort_keys=False, allow_unicode=False),
        encoding="ascii",
        newline="\n",
    )
    return destination


def main() -> int:
    """Run the M20-S119 census and write its checked-in report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--year", default="2025")
    parser.add_argument(
        "--reconciliation",
        type=Path,
        default=Path("plans/m20_s116_instruction_reconciliation.yaml"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("plans/m20_s119_instruction_extent_census.yaml"),
    )
    args = parser.parse_args()
    report = build_instruction_extent_census(
        root=args.root,
        year=args.year,
        reconciliation_path=args.reconciliation,
    )
    output = args.output if args.output.is_absolute() else args.root / args.output
    write_instruction_extent_census(report, output)
    print(
        "instruction extent census: "
        f"{report['counts']['instruction_booklets']} booklets, "
        f"{report['counts']['sections']} sections, "
        f"{report['counts']['unclaimed_spans']} unclaimed spans, "
        f"{report['counts']['overlap_spans']} overlap spans"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
