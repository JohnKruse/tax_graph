"""Rebind promoted instruction citations to acquired HTML byte ranges."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
from typing import Any

import yaml

from tax_graph.acquire.citation_check import check_citation_integrity
from tax_graph.acquire.html_source import HtmlSourceIndex


TARGET_SOURCE_IDS = frozenset(
    {
        "instructions_form_1040_2025",
        "instructions_schedule_d_2025",
        "instructions_form_2441_2025",
        "instructions_form_8949_2025",
    }
)


def rebind_instruction_citations(
    *,
    root: str | Path,
    year: str | int = "2025",
    write: bool = False,
) -> dict[str, Any]:
    """Re-derive all affected ranges and leave other ranged citations byte-identical."""
    root_path = Path(root).resolve()
    raw_dir = root_path / ".cache" / "raw" / str(year)
    citation_dir = root_path / "graph" / str(year) / "citations"
    indexes = {
        source_id: HtmlSourceIndex(
            (raw_dir / f"{source_id}.html").read_text(encoding="utf-8")
        )
        for source_id in sorted(TARGET_SOURCE_IDS)
    }
    before: dict[str, tuple[dict[str, int], ...]] = {}
    changed_records: list[tuple[Path, str, dict[str, Any]]] = []
    affected = 0
    files: dict[Path, list[dict[str, Any]]] = {}
    for path in sorted(citation_dir.glob("*.yaml")):
        records = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        if not isinstance(records, list):
            continue
        files[path] = [dict(record) for record in records]
        for citation in files[path]:
            citation_id = str(citation.get("citation_id") or "")
            source_id = str(citation.get("source_document_id") or "")
            ranges = tuple(
                {"start": int(item["start"]), "end": int(item["end"])}
                for item in citation.get("ranges") or ()
            )
            if ranges:
                before[citation_id] = ranges
            if source_id not in TARGET_SOURCE_IDS or not ranges:
                continue
            index = indexes[source_id]
            new_ranges = _ranges_for_citation(index, citation, source_id)
            if new_ranges is None:
                raise ValueError(f"could not re-derive {citation_id} from {source_id}.html")
            citation["ranges"] = [dict(item) for item in new_ranges]
            if citation.get("kind") == "computed_table":
                citation.pop("quoted_text", None)
            else:
                citation["quoted_text"] = index.visible_text_for_ranges(new_ranges)
            changed_records.append((path, citation_id, citation))
            affected += 1

    if affected != 338:
        raise AssertionError(f"expected 338 affected ranged citations, found {affected}")

    if write:
        for path, records in files.items():
            original = path.read_text(encoding="utf-8")
            updated = _replace_records(original, records)
            if updated != original:
                path.write_text(updated, encoding="utf-8", newline="\n")

    unaffected_unchanged = 0
    for path, records in files.items():
        for citation in records:
            citation_id = str(citation.get("citation_id") or "")
            source_id = str(citation.get("source_document_id") or "")
            if source_id in TARGET_SOURCE_IDS:
                continue
            ranges = tuple(
                {"start": int(item["start"]), "end": int(item["end"])}
                for item in citation.get("ranges") or ()
            )
            if ranges and ranges == before.get(citation_id):
                unaffected_unchanged += 1
    report = {
        "affected_source_ids": sorted(TARGET_SOURCE_IDS),
        "affected_ranges_rederived": affected,
        "unaffected_ranges_unchanged": unaffected_unchanged,
        "write": write,
    }
    if write:
        all_records = [
            citation
            for records in files.values()
            for citation in records
            if citation.get("ranges")
        ]
        integrity = check_citation_integrity(all_records, text_dir=raw_dir)
        report["integrity_checked"] = integrity.checked
        report["integrity_mismatches"] = [item.citation_id for item in integrity.mismatches]
        if integrity.mismatches:
            raise AssertionError(f"HTML citation integrity failed: {report['integrity_mismatches']}")
    return report


def _ranges_for_citation(
    index: HtmlSourceIndex,
    citation: dict[str, Any],
    source_id: str,
) -> tuple[dict[str, int], ...] | None:
    citation_id = str(citation.get("citation_id") or "")
    if citation_id.startswith("cite_1040_tax_brackets_"):
        suffix = citation_id.removeprefix("cite_1040_tax_brackets_")
        markers = {
            "single": ("Section A-Use if", "Section B-Use if"),
            "joint_qss": ("Section B-Use if", "Section C-Use if"),
            "mfs": ("Section C-Use if", "Section D-Use if"),
            "hoh": ("Section D-Use if", None),
        }
        start_marker, end_marker = markers.get(suffix, (None, None))
        if start_marker is not None:
            start = index.source.find(start_marker)
            end = index.source.find(end_marker, start + 1) if end_marker else len(index.source)
            if start >= 0 and end >= 0:
                return (
                    {
                        "start": len(index.source[:start].encode("utf-8")),
                        "end": len(index.source[:end].encode("utf-8")),
                    },
                )
    if citation_id == "cite_1040_standard_deduction":
        return index.ranges_for_quote(
            "15,750-Single or Married filing separately. "
            "$31,500-Married filing jointly or Qualifying surviving spouse. "
            "$23,625-Head of household."
        )
    quote = str(citation.get("quoted_text") or "")
    if citation_id == "cite_credit_limit_worksheet_2025_lines_2":
        quote = quote.replace("line 6 (", "line 6l (")
    return index.ranges_for_quote(quote)


def _replace_records(original: str, records: list[dict[str, Any]]) -> str:
    """Replace only records whose source id is in the affected set."""
    lines = original.replace("\r\n", "\n").splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if line.startswith("- citation_id: ")]
    by_id = {str(record.get("citation_id") or ""): record for record in records}
    replacements: list[tuple[int, int, str]] = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        block = "".join(lines[start:end])
        parsed_payload = yaml.safe_load(block) or []
        parsed = parsed_payload[0] if isinstance(parsed_payload, list) else parsed_payload
        source_id = str(parsed.get("source_document_id") or "")
        citation_id = str(parsed.get("citation_id") or "")
        if source_id not in TARGET_SOURCE_IDS:
            continue
        replacement = yaml.safe_dump(
            [by_id[citation_id]],
            sort_keys=False,
            allow_unicode=False,
            width=120,
        )
        replacements.append((start, end, replacement))
    for start, end, replacement in reversed(replacements):
        lines[start:end] = [replacement]
    return "".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--year", default="2025")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    print(rebind_instruction_citations(root=args.root, year=args.year, write=args.write))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
