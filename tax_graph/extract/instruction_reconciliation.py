"""Reconcile printed form cells with their acquired instruction booklet.

The report is deliberately deterministic and read-only.  It keeps the form
inventory and the booklet inventory separate, then records every item in one
bucket so a parser gap cannot be mistaken for a genuine absence.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
import re
from typing import Any

import yaml

from tax_graph.extract.instruction_sections import InstructionSectionsFrame


BUCKETS = (
    "MATCHED",
    "CELL WITH NO INSTRUCTION + BOOKLET MENTIONS IT",
    "CELL WITH NO INSTRUCTION + BOOKLET DOES NOT MENTION IT",
    "INSTRUCTION WITH NO CELL",
    "AMBIGUOUS",
)

def reconcile_instruction_document(
    document_id: str,
    raw_booklet_text: str,
    frame: InstructionSectionsFrame,
    cells: Iterable[Any],
) -> dict[str, Any]:
    """Return a two-sided reconciliation for one form and its booklet.

    ``raw_booklet_text`` is used only for the missing-cell classification.  A
    missing parsed section is actionable when the source booklet names the
    line, which prevents the parser from laundering its own omission into a
    genuine absence.
    """
    cell_items = [
        cell
        for cell in cells
        if _value(cell, "form") == document_id and _value(cell, "line")
    ]
    sections = _unique_sections(frame, document_id)
    paired_section_ids: set[str] = set()
    section_bucket_overrides: dict[str, str] = {}
    cell_rows: list[dict[str, Any]] = []
    bucket_counts = {bucket: 0 for bucket in BUCKETS}

    for index, cell in enumerate(cell_items, start=1):
        line = _value(cell, "line").lower()
        direct = [section for section in sections if section.line == line]
        inherited = []
        if not direct:
            parent = _numeric_parent(line)
            if parent is not None:
                inherited = [section for section in sections if section.line == parent]
        matches = direct or inherited
        if len(matches) > 1:
            bucket = "AMBIGUOUS"
            for section in matches:
                paired_section_ids.add(section.section_id)
                section_bucket_overrides[section.section_id] = bucket
        elif matches:
            bucket = "MATCHED"
            paired_section_ids.add(matches[0].section_id)
        elif _booklet_mentions_line(raw_booklet_text, line):
            bucket = "CELL WITH NO INSTRUCTION + BOOKLET MENTIONS IT"
        else:
            bucket = "CELL WITH NO INSTRUCTION + BOOKLET DOES NOT MENTION IT"
        bucket_counts[bucket] += 1
        cell_rows.append(
            {
                "cell_id": f"{document_id}:line={line}:cell={index}",
                "line": line,
                "bucket": bucket,
                "match": "inherited" if inherited and not direct and len(matches) == 1 else "direct" if direct and len(matches) == 1 else "",
                "section_ids": [section.section_id for section in matches],
            }
        )

    instruction_rows: list[dict[str, Any]] = []
    for section in sections:
        if section.section_id in paired_section_ids:
            if section_bucket_overrides.get(section.section_id) == "AMBIGUOUS":
                bucket_counts["AMBIGUOUS"] += 1
                instruction_rows.append(
                    {
                        "section_id": section.section_id,
                        "line": section.line,
                        "bucket": "AMBIGUOUS",
                    }
                )
            continue
        bucket = "INSTRUCTION WITH NO CELL"
        bucket_counts[bucket] += 1
        instruction_rows.append(
            {
                "section_id": section.section_id,
                "line": section.line,
                "bucket": bucket,
            }
        )

    return {
        "document_id": document_id,
        "cell_count": len(cell_items),
        "instruction_section_count": len(sections),
        "bucket_counts": bucket_counts,
        "cells": cell_rows,
        "instructions": instruction_rows,
    }


def build_instruction_reconciliation_report(
    documents: Iterable[Mapping[str, Any]],
    *,
    table_addressed_cells: int = 0,
) -> dict[str, Any]:
    """Build the checked-in report for the supplied deterministic inputs.

    Each document mapping contains ``document_id``, ``raw_booklet_text``,
    ``frame``, and ``cells``.  Table-addressed cells are reported separately
    because this round intentionally does not invent a column owner vocabulary.
    """
    reports = {}
    for item in documents:
        report = reconcile_instruction_document(
            str(item["document_id"]),
            str(item.get("raw_booklet_text") or ""),
            item["frame"],
            item.get("cells") or (),
        )
        reports[report["document_id"]] = report

    line_cells = sum(int(report["cell_count"]) for report in reports.values())
    topic_documents = {
        document_id: report
        for document_id, report in reports.items()
        if document_id in {"schedule_1a_2025", "schedule_b_2025"}
    }
    topic_cell_count = sum(int(item["cell_count"]) for item in topic_documents.values())
    topic_matched_count = sum(
        int(item["bucket_counts"].get("MATCHED", 0))
        for item in topic_documents.values()
    )
    return {
        "schema_version": 1,
        "round": "M20-S116",
        "documents": reports,
        "families": {
            "line_anchored": {
                "cell_count": line_cells,
                "document_count": len(reports),
            },
            "topic_organized": {
                "documents": sorted(topic_documents),
                "cell_count": topic_cell_count,
                "matched_cell_count": topic_matched_count,
                "unmatched_cell_count": topic_cell_count - topic_matched_count,
                "instruction_section_count": sum(
                    int(item["instruction_section_count"]) for item in topic_documents.values()
                ),
            },
            "table_addressed": {
                "cell_count": int(table_addressed_cells),
                "matched_cell_count": 0,
                "bucket": "OUT OF SCOPE - NO TABLE/COLUMN OWNER",
                "instruction_section_count": 0,
            },
        },
    }


def write_instruction_reconciliation_report(
    report: Mapping[str, Any],
    path: str | Path,
) -> Path:
    """Write one deterministic YAML reconciliation artifact."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        yaml.safe_dump(dict(report), sort_keys=False, allow_unicode=False),
        encoding="ascii",
        newline="\n",
    )
    return destination


def _unique_sections(frame: InstructionSectionsFrame, document_id: str) -> list[Any]:
    seen: set[str] = set()
    result = []
    for section in frame.sections:
        if section.document_id != document_id or section.section_id in seen:
            continue
        seen.add(section.section_id)
        result.append(section)
    return result


def _booklet_mentions_line(text: str, line: str) -> bool:
    normalized = str(line).strip().lower()
    if not normalized:
        return False
    pattern = re.compile(
        rf"\blines?\b[^.\n]{{0,120}}\b{re.escape(normalized)}\b",
        re.IGNORECASE,
    )
    if pattern.search(text):
        return True
    parent = _numeric_parent(normalized)
    return parent is not None and bool(
        re.search(
            rf"\blines?\b[^.\n]{{0,120}}\b{re.escape(parent)}\b",
            text,
            re.IGNORECASE,
        )
    )


def _numeric_parent(line: str) -> str | None:
    match = re.fullmatch(r"([0-9]+)[a-z]", str(line).strip().lower())
    return match.group(1) if match else None


def _value(item: Any, key: str) -> str:
    if isinstance(item, Mapping):
        return str(item.get(key) or "")
    return str(getattr(item, key, "") or "")
