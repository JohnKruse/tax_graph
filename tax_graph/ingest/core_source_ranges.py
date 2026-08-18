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
from tax_graph.acquire.source_ranges import (
    SourceRangeError,
    SourceTextIndex,
    normalize_source_quote,
    resolve_source_range,
)
from tax_graph.config import get_config_value, load_config
from tax_graph.ingest.worksheet_harvest import (
    QDCGT_WORKSHEET_TARGET,
    _source_ranges_for_lines,
    _source_text_rows_for_target,
)


HTML_LOCATOR_RE = re.compile(r"^html#", re.IGNORECASE)
LINE_LOCATOR_RE = re.compile(r"^page\s+[0-9]+,\s+line\s+([0-9]+)$", re.IGNORECASE)
LEGACY_RANGE_EXEMPTION = "negative_form_8978_adjustment_worksheet_schedule_2_2025"
COMPUTED_TABLE_KIND = "computed_table"
COMPUTED_TABLE_CITATION_IDS = frozenset(
    {
        "cite_1040_tax_brackets_single",
        "cite_1040_tax_brackets_joint_qss",
        "cite_1040_tax_brackets_mfs",
        "cite_1040_tax_brackets_hoh",
    }
)
PARAPHRASE_CITATION_IDS = frozenset(
    {
        "cite_1040_line_16_tax_methods",
        "cite_1040_qdcgt_line_1",
        "cite_1040_qdcgt_line_10_12",
        "cite_1040_qdcgt_line_13_17",
        "cite_1040_qdcgt_line_18_21",
        "cite_1040_qdcgt_line_2",
        "cite_1040_qdcgt_line_22",
        "cite_1040_qdcgt_line_23_25",
        "cite_1040_qdcgt_line_24",
        "cite_1040_qdcgt_line_25",
        "cite_1040_qdcgt_line_3",
        "cite_1040_qdcgt_line_5",
        "cite_1040_qdcgt_line_6_9",
        "cite_1040_standard_deduction",
        "cite_1040_tax_table",
        "cite_schedule_d_carryover_line_1_2",
        "cite_schedule_d_carryover_line_3_4",
        "cite_schedule_d_carryover_line_5_8",
        "cite_schedule_d_carryover_line_8",
        "cite_schedule_d_carryover_line_9_13",
        "cite_sdtw_line_11_14",
        "cite_sdtw_line_15_22",
        "cite_sdtw_line_19_breakpoint",
        "cite_sdtw_line_1_6",
        "cite_sdtw_line_23_32",
        "cite_sdtw_line_33_34",
        "cite_sdtw_line_35_40",
        "cite_sdtw_line_41_44",
        "cite_sdtw_line_45_47",
        "cite_sdtw_line_7_10",
    }
)


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


def _tax_table_section_extent(
    source: str,
    *,
    section: str,
) -> tuple[dict[str, int], ...] | None:
    """Return the complete acquired rate-table section for a computed citation."""
    heading = re.search(
        rf"\*\*Section {re.escape(section)}Use if your filing status is .*?\*\*",
        source,
        re.IGNORECASE,
    )
    if heading is None:
        return None
    next_heading = re.search(r"\*\*Section [A-D]Use if", source[heading.end() :], re.I)
    next_page = re.search(r"\n# Page [0-9]+\s*\n", source[heading.end() :])
    boundaries = [
        heading.end() + match.start()
        for match in (next_heading, next_page)
        if match is not None
    ]
    end = min(boundaries) if boundaries else len(source)
    return ({"start": heading.start(), "end": end},)


def _source_quote(
    source: str,
    ranges: Iterable[Mapping[str, int]],
    *,
    source_document_id: str = "core_source",
) -> str:
    """Render a new quote only from the acquired ranges that own it."""
    return normalize_source_quote(
        " ".join(
            resolve_source_range(
                source_document_id,
                int(item["start"]),
                int(item["end"]),
                source_text=source,
            )
            for item in ranges
        )
    )


def _qdcgt_ranges(source: str, lines: Iterable[str]) -> tuple[dict[str, int], ...] | None:
    """Find QDCGT row ranges using the established worksheet row parser."""
    lines = tuple(lines)
    rows = _source_text_rows_for_target(source, QDCGT_WORKSHEET_TARGET)
    by_line, _ = _source_ranges_for_lines(source, rows, lines)
    ranges: list[dict[str, int]] = []
    for line in lines:
        ranges.extend(by_line.get(line, ()))
    return tuple(ranges) or None


def _markdown_row_ranges(
    source: str,
    *,
    title: str,
    lines: Iterable[str],
) -> tuple[dict[str, int], ...] | None:
    """Return the prose cell of each numbered Markdown worksheet row."""
    lines = tuple(lines)
    title_start = source.find(title)
    if title_start < 0:
        return None
    ranges: list[dict[str, int]] = []
    for line in lines:
        match = re.search(rf"(?m)^\|\s*{re.escape(line)}\.(?!\*)\s*", source[title_start:])
        if match is None:
            return None
        row_start = title_start + match.start()
        number_start = source.find(str(line), row_start, title_start + match.end())
        if number_start < 0:
            return None
        first_separator = source.find("|", number_start + len(str(line)) + 1)
        if first_separator < 0:
            return None
        after_number = source[number_start + len(str(line)) + 1 : first_separator]
        separator = (
            source.find("|", first_separator + 1)
            if not after_number.strip()
            else first_separator
        )
        if separator < 0:
            return None
        ranges.append({"start": number_start, "end": separator})
    return tuple(ranges) or None


def _plain_worksheet_ranges(
    source: str,
    *,
    title: str,
    lines: Iterable[str],
) -> tuple[dict[str, int], ...] | None:
    """Return exact line-to-marker spans from a rendered worksheet."""
    lines = tuple(lines)
    title_start = source.find(title)
    if title_start < 0:
        return None
    ranges: list[dict[str, int]] = []
    for line in lines:
        match = re.search(rf"(?m)^{re.escape(line)}\.\s", source[title_start:])
        if match is None:
            return None
        start = title_start + match.start()
        marker = re.search(rf"\.\.\.\s*{re.escape(line)}\.", source[title_start + match.end() :])
        if marker is None:
            return None
        end = title_start + match.end() + marker.end()
        ranges.append({"start": start, "end": end})
    return tuple(ranges) or None


def _sdtw_ranges(source: str, lines: Iterable[str]) -> tuple[dict[str, int], ...] | None:
    """Combine the prose and continuation-table halves of Schedule D's worksheet."""
    selected = tuple(lines)
    first_lines = tuple(line for line in selected if int(line) <= 30)
    continuation_lines = tuple(line for line in selected if int(line) > 30)
    ranges: list[dict[str, int]] = []
    if first_lines:
        plain = _plain_worksheet_ranges(
            source,
            title="Schedule D Tax Worksheet",
            lines=first_lines,
        )
        if plain is None:
            return None
        ranges.extend(plain)
    if continuation_lines:
        continued = _markdown_row_ranges(
            source,
            title="Schedule D Tax WorksheetContinued",
            lines=continuation_lines,
        )
        if continued is None:
            return None
        ranges.extend(continued)
    return tuple(ranges) or None


def _paraphrase_ranges(source: str, citation_id: str) -> tuple[dict[str, int], ...] | None:
    """Locate the acquired source span that replaces one A9 paraphrase."""
    if citation_id.startswith("cite_1040_qdcgt_"):
        match = re.search(r"_line_(\d+)(?:_(\d+))?$", citation_id)
        if match is None:
            return None
        first = int(match.group(1))
        last = int(match.group(2) or first)
        return _qdcgt_ranges(source, (str(value) for value in range(first, last + 1)))
    if citation_id.startswith("cite_schedule_d_carryover_"):
        match = re.search(r"_line_(\d+)(?:_(\d+))?$", citation_id)
        if match is None:
            return None
        first = int(match.group(1))
        last = int(match.group(2) or first)
        return _markdown_row_ranges(
            source,
            title="Capital Loss Carryover WorksheetLines 6 and 14",
            lines=(str(value) for value in range(first, last + 1)),
        )
    if citation_id.startswith("cite_sdtw_"):
        if citation_id == "cite_sdtw_line_19_breakpoint":
            lines = ("19",)
        else:
            match = re.search(r"_line_(\d+)(?:_(\d+))?$", citation_id)
            if match is None:
                return None
            first = int(match.group(1))
            last = int(match.group(2) or first)
            lines = tuple(str(value) for value in range(first, last + 1))
        return _sdtw_ranges(source, lines)
    if citation_id == "cite_1040_standard_deduction":
        start = source.find("**Standard deduction amount increased.**")
        if start < 0:
            return None
        ranges: list[dict[str, int]] = []
        for pattern in (r"^-\s+\$15,750", r"^-\s+\$31,500", r"^-\s+\$23,625"):
            line_range = _line_range(source, pattern, start=start)
            if line_range is None:
                return None
            ranges.extend(line_range)
        return tuple(ranges)
    if citation_id in {"cite_1040_line_16_tax_methods", "cite_1040_tax_table"}:
        start = source.find("**Tax Table or Tax Computation Worksheet.**")
        if start < 0:
            return None
        end = source.find("\n\n", start)
        return ({"start": start, "end": end if end >= 0 else len(source)},)
    return None


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
    for suffix, (section, _terms) in section_terms.items():
        if not citation_id.endswith(f"tax_brackets_{suffix}"):
            continue
        return _tax_table_section_extent(source, section=section)
    return None


def _eligible_citation(citation: Mapping[str, Any], core_ids: set[str]) -> bool:
    source_id = str(citation.get("source_document_id") or "")
    document_id = str(citation.get("document_id") or "")
    locator = str(citation.get("locator") or "")
    if not source_id or source_id not in core_ids:
        return False
    if citation.get("kind") == COMPUTED_TABLE_KIND:
        return False
    if not citation.get("quoted_text"):
        return False
    if HTML_LOCATOR_RE.match(locator) or document_id == LEGACY_RANGE_EXEMPTION:
        return False
    return True


def _prepare_computed_table_citation(
    citation: dict[str, Any],
    *,
    source: str,
) -> bool:
    """Record rate-table provenance without presenting the synthesis as a quote."""
    citation_id = str(citation.get("citation_id") or "")
    if citation_id not in COMPUTED_TABLE_CITATION_IDS:
        return False
    ranges = _tax_liability_ranges(source, citation_id)
    if ranges is None:
        raise ValueError(f"rate-table section not found for {citation_id}")
    sections = {
        "single": "Section A (Single)",
        "joint_qss": "Section B (Married filing jointly or Qualifying surviving spouse)",
        "mfs": "Section C (Married filing separately)",
        "hoh": "Section D (Head of household)",
    }
    suffix = next(
        suffix for suffix in sections if citation_id.endswith(f"tax_brackets_{suffix}")
    )
    citation["kind"] = COMPUTED_TABLE_KIND
    citation.pop("quoted_text", None)
    citation["ranges"] = [dict(item) for item in ranges]
    citation["derivation"] = (
        f"Computed from the acquired {sections[suffix]} rate table: use each row's "
        "marginal rate and subtraction amount to derive the cumulative tax at the "
        "filing-status bracket boundaries."
    )
    return True


def _reextract_paraphrase_citation(
    citation: dict[str, Any],
    *,
    source: str,
    source_document_id: str,
) -> bool:
    """Replace one A9 paraphrase with the exact source-owned text and ranges."""
    citation_id = str(citation.get("citation_id") or "")
    if citation_id not in PARAPHRASE_CITATION_IDS:
        return False
    ranges = _paraphrase_ranges(source, citation_id)
    if ranges is None:
        raise ValueError(f"source span not found for paraphrase citation {citation_id}")
    citation["quoted_text"] = _source_quote(
        source,
        ranges,
        source_document_id=source_document_id,
    )
    citation["ranges"] = [dict(item) for item in ranges]
    return True


def _ranges_match_quote(
    source: str,
    quote: str,
    ranges: Iterable[Mapping[str, Any]],
    *,
    source_document_id: str = "core_source",
) -> bool:
    """Return whether ranges reproduce the pinned quote without rewriting it."""
    try:
        reconstructed = normalize_source_quote(
            " ".join(
                resolve_source_range(
                    source_document_id,
                    int(item["start"]),
                    int(item["end"]),
                    source_text=source,
                )
                for item in ranges
            )
        )
    except (KeyError, TypeError, ValueError, SourceRangeError):
        return False
    return reconstructed == normalize_source_quote(quote)


def _bind_citation(
    citation: dict[str, Any],
    *,
    source: str,
    index: SourceTextIndex,
    used_starts: set[int],
) -> bool:
    citation_id = str(citation.get("citation_id") or "")
    source_document_id = str(citation.get("source_document_id") or citation.get("document_id") or "")
    quote = str(citation.get("quoted_text") or "")
    existing_ranges = citation.get("ranges") or ()
    if existing_ranges and _ranges_match_quote(
        source,
        quote,
        existing_ranges,
        source_document_id=source_document_id,
    ):
        return True
    ranges = _tax_liability_ranges(source, citation_id)
    special_ranges = ranges is not None
    if ranges is None:
        bounds = _line_bounds(source, str(citation.get("locator") or ""))
        ranges = index.ranges_for_quote(
            quote,
            start=bounds[0] if bounds else 0,
            end=bounds[1] if bounds else None,
        )
        if ranges is None and bounds is not None:
            ranges = index.ranges_for_quote(quote)
    if ranges is not None and not _ranges_match_quote(
        source,
        quote,
        ranges,
        source_document_id=source_document_id,
    ):
        ranges = index.ranges_for_quote(quote)
        special_ranges = False
    if ranges is None:
        citation.pop("ranges", None)
        return False
    first_start = int(ranges[0]["start"])
    if first_start in used_starts and not special_ranges:
        ranges = index.ranges_for_quote(
            quote,
            start=first_start + 1,
        ) or ranges
    if not _ranges_match_quote(
        source,
        quote,
        ranges,
        source_document_id=source_document_id,
    ):
        citation.pop("ranges", None)
        return False
    used_starts.add(int(ranges[0]["start"]))
    citation["ranges"] = [dict(item) for item in ranges]
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
    for path, records in records_by_path.items():
        for citation in records:
            source_id = str(citation.get("source_document_id") or "")
            if source_id in sources:
                _prepare_computed_table_citation(citation, source=sources[source_id])
    eligible_paths = {
        path
        for path, records in records_by_path.items()
        if any(
            _eligible_citation(item, core_ids)
            or item.get("kind") == COMPUTED_TABLE_KIND
            for item in records
        )
    }
    changed = 0
    findings: list[str] = []
    used_starts: dict[str, set[int]] = defaultdict(set)
    for path, records in records_by_path.items():
        for citation in records:
            source_id = str(citation.get("source_document_id") or "")
            if source_id in sources and _reextract_paraphrase_citation(
                citation,
                source=sources[source_id],
                source_document_id=source_id,
            ):
                changed += 1
                continue
            if not _eligible_citation(citation, core_ids):
                continue
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
