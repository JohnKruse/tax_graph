"""Rebind promoted core citations to acquired source ranges.

This stage is deterministic.  It reads the acquired text and the existing
promoted graph, then writes regenerated citation artifacts.  It never invents
prose or claims a human review decision.  Unclaimed source gaps remain a
read-only measurement until a consumer can carry their provenance into a row
packet; measuring a gap is not enough to promote it.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

import yaml

from tax_graph.acquire.manifest import load_manifest
from tax_graph.acquire.source_ranges import SourceTextIndex, normalize_source_quote
from tax_graph.config import get_config_value, load_config


HTML_LOCATOR_RE = re.compile(r"^html#", re.IGNORECASE)
LINE_LOCATOR_RE = re.compile(r"^page\s+[0-9]+,\s+line\s+([0-9]+)$", re.IGNORECASE)
LEGACY_RANGE_EXEMPTION = "negative_form_8978_adjustment_worksheet_schedule_2_2025"


def _raw_root(root: Path, year: str) -> Path:
    config = load_config(root=root)
    raw_store = Path(get_config_value(config, "project.paths.raw_store", ".cache/raw"))
    if not raw_store.is_absolute():
        raw_store = root / raw_store
    return raw_store / year


def _source_texts(root: Path, year: str, source_ids: Iterable[str]) -> dict[str, str]:
    raw_root = _raw_root(root, year)
    return {
        source_id: (raw_root / f"{source_id}.txt").read_text(encoding="utf-8")
        for source_id in sorted(set(source_ids))
    }


def _line_bounds(source: str, locator: str) -> tuple[int, int] | None:
    match = LINE_LOCATOR_RE.fullmatch(locator.strip())
    if match is None:
        return None
    line_number = int(match.group(1))
    lines = source.splitlines(keepends=True)
    if line_number < 1 or line_number > len(lines):
        return None
    start = sum(len(line) for line in lines[: line_number - 1])
    return start, start + len(lines[line_number - 1])


def _line_range(source: str, pattern: str, *, start: int = 0) -> tuple[dict[str, int], ...] | None:
    """Return the first complete physical source line matching a pattern."""
    offset = 0
    for line in source.splitlines(keepends=True):
        if offset >= start and re.search(pattern, line, re.IGNORECASE):
            return ({"start": offset, "end": offset + len(line.rstrip("\r\n"))},)
        offset += len(line)
    return None


def _worksheet_line_ranges(
    source: str,
    *,
    title: str,
    first_line: int,
    last_line: int,
) -> tuple[dict[str, int], ...] | None:
    """Return one worksheet's printed rows, including continuation rows."""
    title_start = source.find(title)
    if title_start < 0:
        return None
    first = re.search(rf"\|\s*{first_line}\.\s*\|", source[title_start:])
    if first is None:
        return None
    start = title_start + first.start()
    next_line = re.search(
        rf"\|\s*{last_line + 1}\.\s*\|", source[start + 1 :]
    )
    if next_line is not None:
        end = start + 1 + next_line.start()
    else:
        last = re.search(rf"\|\s*{last_line}\.\s*\|[^\n]*(?:\n|$)", source[start:])
        end = start + last.end() if last is not None else len(source)
    return ({"start": start, "end": end},)


def _tax_table_section_ranges(
    source: str,
    *,
    section: str,
    terms: Iterable[str],
) -> tuple[dict[str, int], ...] | None:
    """Return the threshold rows in one filing-status tax-table section."""
    heading = re.search(
        rf"\*\*Section {re.escape(section)}Use if your filing status is .*?\*\*",
        source,
        re.IGNORECASE,
    )
    if heading is None:
        return None
    next_heading = re.search(r"\*\*Section [A-D]Use if", source[heading.end() :], re.I)
    section_end = heading.end() + next_heading.start() if next_heading else len(source)
    section_text = source[heading.end() : section_end]
    ranges: list[dict[str, int]] = []
    offset = heading.end()
    wanted = tuple(terms)
    for line in section_text.splitlines(keepends=True):
        if "|" in line and any(f"Over ${term}" in line for term in wanted):
            ranges.append({"start": offset, "end": offset + len(line.rstrip("\r\n"))})
        offset += len(line)
    return tuple(ranges) or None


def _tax_liability_ranges(source: str, citation_id: str) -> tuple[dict[str, int], ...] | None:
    """Map the legacy liability citations to the current source table rows."""
    worksheet_title = "# Qualified Dividends and Capital Gain Tax Worksheet"
    worksheet_match = re.search(r"_line_(\d+)(?:_(\d+))?$", citation_id)
    if citation_id.startswith("cite_1040_qdcgt_") and worksheet_match:
        first_line = int(worksheet_match.group(1))
        last_line = int(worksheet_match.group(2) or first_line)
        return _worksheet_line_ranges(
            source,
            title=worksheet_title,
            first_line=first_line,
            last_line=last_line,
        )
    if citation_id.endswith("standard_deduction"):
        return _line_range(source, r"\|\s*3\. Enter the amount shown below")
    if citation_id.endswith("line_16_tax_methods"):
        start = source.find("If your taxable income is less than $100,000")
        if start >= 0:
            end = source.find("\n\n", start)
            return ({"start": start, "end": end if end >= 0 else len(source)},)
        return None
    if citation_id.endswith("tax_table"):
        start = source.find("If your taxable income is less than $100,000")
        if start >= 0:
            end = source.find("\n\n", start)
            return ({"start": start, "end": end if end >= 0 else len(source)},)
        return None
    section_terms = {
        "single": ("A", ("250,525", "626,350")),
        "joint_qss": ("B", ("501,050", "751,600")),
        "mfs": ("C", ("250,525", "375,800")),
        "hoh": ("D", ("250,500", "626,350")),
    }
    for suffix, (section, terms) in section_terms.items():
        if not citation_id.endswith(f"tax_brackets_{suffix}"):
            continue
        return _tax_table_section_ranges(source, section=section, terms=terms)
    return None


def _eligible_citation(citation: Mapping[str, Any], core_ids: set[str]) -> bool:
    source_id = str(citation.get("source_document_id") or "")
    document_id = str(citation.get("document_id") or "")
    locator = str(citation.get("locator") or "")
    if not source_id or source_id not in core_ids:
        return False
    citation_id = str(citation.get("citation_id") or "")
    if not citation.get("quoted_text"):
        return False
    if citation.get("ranges") and not citation_id.startswith("cite_1040_"):
        return False
    if HTML_LOCATOR_RE.match(locator) or document_id == LEGACY_RANGE_EXEMPTION:
        return False
    return True


def _bind_citation(
    citation: dict[str, Any],
    *,
    source: str,
    index: SourceTextIndex,
    used_starts: set[int],
) -> bool:
    citation_id = str(citation.get("citation_id") or "")
    ranges = _tax_liability_ranges(source, citation_id)
    special_ranges = ranges is not None
    if ranges is None:
        bounds = _line_bounds(source, str(citation.get("locator") or ""))
        ranges = index.ranges_for_quote(
            str(citation.get("quoted_text") or ""),
            start=bounds[0] if bounds else 0,
            end=bounds[1] if bounds else None,
        )
        if ranges is None and bounds is not None:
            ranges = index.ranges_for_quote(
                str(citation.get("quoted_text") or ""),
            )
    if ranges is None:
        return False
    first_start = int(ranges[0]["start"])
    if first_start in used_starts and not special_ranges:
        ranges = index.ranges_for_quote(
            str(citation.get("quoted_text") or ""),
            start=first_start + 1,
        ) or ranges
    used_starts.add(int(ranges[0]["start"]))
    citation["ranges"] = [dict(item) for item in ranges]
    citation["quoted_text"] = normalize_source_quote(
        " ".join(source[int(item["start"]) : int(item["end"])] for item in ranges)
    )
    return True


def rebind_core_source_ranges(
    *,
    root: str | Path,
    year: str | int = "2025",
) -> dict[str, Any]:
    """Regenerate existing core citations without promoting measured gaps.

    Source-extents measurement identifies candidate gaps, but this stage does
    not turn those candidates into graph citations.  A future promotion stage
    must first prove a real prose chunk, a line-specific governing relation,
    and a consumer that places the citation in the row's derivation packet.
    """
    root_path = Path(root).resolve()
    year_text = str(year)
    manifest = load_manifest(root=root_path)
    core_ids = {
        entry.document_id
        for entry in manifest.documents
        if entry.document_id in set(_load_core_document_ids(root_path))
    }
    citation_root = root_path / "graph" / year_text / "citations"
    generated_path = citation_root / "source-extents-m106.yaml"
    removed_gap_citations = 0
    if generated_path.exists():
        payload = yaml.safe_load(generated_path.read_text(encoding="ascii")) or []
        removed_gap_citations = len(payload) if isinstance(payload, list) else 0
    records_by_path: dict[Path, list[dict[str, Any]]] = {}
    source_ids: set[str] = set()
    for path in sorted(citation_root.glob("*.yaml")):
        if path == generated_path:
            continue
        payload = yaml.safe_load(path.read_text(encoding="ascii")) or []
        records = [dict(item) for item in payload]
        records_by_path[path] = records
        source_ids.update(
            str(item.get("source_document_id") or "")
            for item in records
            if item.get("source_document_id")
        )
    source_ids.update(
        entry.document_id
        for entry in manifest.documents
        if entry.document_id in core_ids
    )
    sources = _source_texts(root_path, year_text, source_ids)
    indexes = {source_id: SourceTextIndex(text) for source_id, text in sources.items()}
    eligible_paths = {
        path
        for path, records in records_by_path.items()
        if any(_eligible_citation(item, core_ids) for item in records)
    }
    changed = 0
    findings: list[str] = []
    used_starts: dict[str, set[int]] = defaultdict(set)
    for path, records in records_by_path.items():
        for citation in records:
            if not _eligible_citation(citation, core_ids):
                continue
            source_id = str(citation["source_document_id"])
            if _bind_citation(
                citation,
                source=sources[source_id],
                index=indexes[source_id],
                used_starts=used_starts[source_id],
            ):
                changed += 1
            else:
                findings.append(str(citation.get("citation_id") or ""))

    for path, records in records_by_path.items():
        if path not in eligible_paths:
            continue
        path.write_text(
            yaml.safe_dump(records, sort_keys=False, allow_unicode=False, width=120),
            encoding="ascii",
            newline="\n",
        )
    if generated_path.exists():
        generated_path.unlink()
    return {
        "core_documents": sorted(core_ids),
        "rebound": changed,
        "findings": sorted(findings),
        "generated_gap_citations": 0,
        "removed_gap_citations": removed_gap_citations,
        "generated_path": None,
    }


def _load_core_document_ids(root: Path) -> tuple[str, ...]:
    payload = yaml.safe_load((root / "config" / "document_tiers.yaml").read_text(encoding="ascii")) or {}
    return tuple(str(value) for value in payload.get("core_documents") or ())


def main() -> int:
    """Run the deterministic core source-range promotion stage."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--year", default="2025")
    args = parser.parse_args()
    result = rebind_core_source_ranges(root=args.root, year=args.year)
    print(
        "core source ranges: "
        f"rebound {result['rebound']}, "
        f"generated {result['generated_gap_citations']}, "
        f"removed {result['removed_gap_citations']}, "
        f"findings {len(result['findings'])}"
    )
    if result["findings"]:
        print("unrebound citations: " + ", ".join(result["findings"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
