"""Reconcile printed form cells with their acquired instruction booklet.

The report is deliberately deterministic and read-only.  It asks the same
ownership accessor used to assemble evidence packets, then records the form
cell and instruction-section populations separately so a parser gap cannot
be mistaken for a genuine absence.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
import re
from typing import Any

import yaml

from tax_graph.extract.instruction_sections import InstructionSectionsFrame
from tax_graph.extract.instruction_ownership import (
    instruction_line_owners,
    instruction_span_ids_for_line,
)
from tax_graph.extract.outline import _spans_for_instruction_frame


BUCKETS = (
    "MATCHED",
    "CELL WITH NO INSTRUCTION + BOOKLET MENTIONS IT",
    "CELL WITH NO INSTRUCTION + OTHER FORM OWNS LINE",
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
    genuine absence.  The cell side is owned exclusively by
    ``instruction_span_ids_for_line`` so the report cannot drift from the
    evidence packet builder.
    """
    cell_items = [
        cell
        for cell in cells
        if _value(cell, "form") == document_id and _value(cell, "line")
    ]
    instruction_spans = _spans_for_instruction_frame(
        frame,
        source_text=raw_booklet_text,
    )
    document_spans = [
        span
        for span in instruction_spans
        if span.owner_document_id == document_id
    ]
    instruction_owners = instruction_line_owners(instruction_spans)
    spans_by_id = {span.span_id: span for span in instruction_spans}
    section_lines = {
        span.section_id or span.span_id: span.owner_lines[0] if span.owner_lines else ""
        for span in instruction_spans
    }
    owner_documents = sorted(
        {
            span.owner_document_id
            for span in instruction_spans
            if span.owner_document_id and span.owner_document_id != document_id
        }
    )
    paired_section_ids: set[str] = set()
    section_bucket_overrides: dict[str, str] = {}
    cell_rows: list[dict[str, Any]] = []
    cell_buckets = {bucket: 0 for bucket in BUCKETS}
    instruction_buckets = {bucket: 0 for bucket in BUCKETS}

    for index, cell in enumerate(cell_items, start=1):
        line = _value(cell, "line").lower()
        match_ids = instruction_span_ids_for_line(
            instruction_spans,
            line,
            owners=instruction_owners,
            owner_document_id=document_id,
        )
        matches = [spans_by_id[span_id] for span_id in match_ids]
        direct = [
            span
            for span in matches
            if line in instruction_owners.get(span.span_id, frozenset())
        ]
        inherited = not direct and bool(matches)
        other_match_ids: list[str] = []
        for owner_document_id in owner_documents:
            other_match_ids.extend(
                instruction_span_ids_for_line(
                    instruction_spans,
                    line,
                    owners=instruction_owners,
                    owner_document_id=owner_document_id,
                )
            )
        other_matches = [spans_by_id[span_id] for span_id in other_match_ids]
        if len(matches) > 1:
            bucket = "AMBIGUOUS"
            for span in matches:
                section_id = span.section_id or span.span_id
                paired_section_ids.add(section_id)
                section_bucket_overrides[section_id] = bucket
        elif matches:
            bucket = "MATCHED"
            paired_section_ids.add(matches[0].section_id or matches[0].span_id)
        else:
            if other_matches:
                bucket = "CELL WITH NO INSTRUCTION + OTHER FORM OWNS LINE"
            elif _booklet_mentions_line(raw_booklet_text, line):
                bucket = "CELL WITH NO INSTRUCTION + BOOKLET MENTIONS IT"
            else:
                bucket = "CELL WITH NO INSTRUCTION + BOOKLET DOES NOT MENTION IT"
        cell_buckets[bucket] += 1
        cell_row = {
            "cell_id": f"{document_id}:line={line}:cell={index}",
            "line": line,
            "bucket": bucket,
            "match": "inherited" if inherited and len(matches) == 1 else "direct" if direct and len(matches) == 1 else "",
            "section_ids": [span.section_id or span.span_id for span in matches],
        }
        if bucket == "CELL WITH NO INSTRUCTION + OTHER FORM OWNS LINE":
            cell_row["other_form_document_ids"] = sorted(
                {
                    span.owner_document_id
                    for span in other_matches
                    if span.owner_document_id
                }
            )
            cell_row["other_form_section_ids"] = [
                span.section_id or span.span_id for span in other_matches
            ]
        cell_rows.append(cell_row)

    instruction_rows: list[dict[str, Any]] = []
    for span in document_spans:
        section_id = span.section_id or span.span_id
        if section_id in paired_section_ids:
            bucket = section_bucket_overrides.get(section_id, "MATCHED")
        else:
            bucket = "INSTRUCTION WITH NO CELL"
        instruction_buckets[bucket] += 1
        instruction_rows.append(
            {
                "section_id": section_id,
                "line": section_lines.get(section_id, ""),
                "bucket": bucket,
            }
        )

    return {
        "document_id": document_id,
        "cell_count": len(cell_items),
        "instruction_section_count": len(document_spans),
        "cell_buckets": cell_buckets,
        "instruction_buckets": instruction_buckets,
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
        int(item["cell_buckets"].get("MATCHED", 0))
        for item in topic_documents.values()
    )
    return {
        "schema_version": 1,
        "round": "M20-S117",
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
