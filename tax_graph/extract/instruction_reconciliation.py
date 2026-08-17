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
    instruction_span_resolution_for_line,
    instruction_span_ids_for_line,
    instruction_span_profile,
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
INSTRUCTION_BUCKETS = BUCKETS + (
    "STUB SECTION",
    "DEDUPED NESTED SECTION",
    "WORKSHEET",
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
    section_dispositions: dict[str, str] = {}
    cell_rows: list[dict[str, Any]] = []
    cell_buckets = {bucket: 0 for bucket in BUCKETS}
    instruction_buckets = {bucket: 0 for bucket in INSTRUCTION_BUCKETS}

    for index, cell in enumerate(cell_items, start=1):
        line = _value(cell, "line").lower()
        resolution = instruction_span_resolution_for_line(
            instruction_spans,
            line,
            owners=instruction_owners,
            owner_document_id=document_id,
        )
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
        for span_id in resolution["stubs"]:
            _record_disposition(section_dispositions, spans_by_id[span_id], "STUB SECTION")
        for dropped in resolution["dropped"]:
            dropped_span = spans_by_id.get(str(dropped.get("span_id") or ""))
            if dropped_span is not None:
                _record_disposition(
                    section_dispositions,
                    dropped_span,
                    "DEDUPED NESTED SECTION",
                )
        for span in matches:
            disposition = (
                "WORKSHEET"
                if span.span_id in resolution["worksheets"]
                else "MATCHED"
            )
            _record_disposition(section_dispositions, span, disposition)
        other_match_ids: list[str] = []
        for owner_document_id in owner_documents:
            other_resolution = instruction_span_resolution_for_line(
                    instruction_spans,
                    line,
                    owners=instruction_owners,
                    owner_document_id=owner_document_id,
                )
            other_match_ids.extend(other_resolution["selected_ids"])
        other_matches = [spans_by_id[span_id] for span_id in other_match_ids]
        if resolution["ambiguous"]:
            bucket = "AMBIGUOUS"
            for span in matches:
                _record_disposition(section_dispositions, span, "AMBIGUOUS")
        elif matches:
            bucket = "MATCHED"
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
            "match": (
                "inherited"
                if inherited and matches and not direct
                else "direct"
                if direct and not resolution["ambiguous"]
                else ""
            ),
            "section_ids": [span.section_id or span.span_id for span in matches],
            "instruction_attachments": [
                {
                    "span_id": span.span_id,
                    "section_id": span.section_id or span.span_id,
                    "specificity": resolution["specificity"].get(
                        span.span_id,
                        "general",
                    ),
                    "specificity_rank": resolution["specificity_rank"].get(
                        span.span_id,
                        1,
                    ),
                    "provenance": (
                        "WORKSHEET"
                        if span.span_id in resolution["worksheets"]
                        else "INSTRUCTION"
                    ),
                }
                for span in matches
            ],
            "instruction_dropped": list(resolution["dropped"]),
            "instruction_dropped_sections": list(resolution["dropped"]),
            "instruction_stub_section_ids": [
                spans_by_id[span_id].section_id or span_id
                for span_id in resolution["stubs"]
            ],
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
        profile = instruction_span_profile(span)
        bucket = section_dispositions.get(section_id)
        if profile["is_stub"]:
            bucket = "STUB SECTION"
        elif profile["provenance"] == "WORKSHEET":
            bucket = "WORKSHEET"
        elif bucket is None:
            bucket = "INSTRUCTION WITH NO CELL"
        instruction_buckets[bucket] += 1
        instruction_rows.append(
            {
                "section_id": section_id,
                "line": section_lines.get(section_id, ""),
                "bucket": bucket,
                "provenance": profile["provenance"],
                "specificity": profile["specificity"],
                "specificity_rank": profile["specificity_rank"],
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


_DISPOSITION_PRIORITY = {
    "DEDUPED NESTED SECTION": 1,
    "STUB SECTION": 2,
    "AMBIGUOUS": 5,
    "WORKSHEET": 3,
    "MATCHED": 4,
}


def _record_disposition(
    dispositions: dict[str, str],
    span: Any,
    disposition: str,
) -> None:
    """Keep the strongest packet disposition seen for one source section."""
    section_id = _value(span, "section_id") or _value(span, "span_id")
    if not section_id:
        return
    current = dispositions.get(section_id)
    if current is None or _DISPOSITION_PRIORITY.get(disposition, 0) >= _DISPOSITION_PRIORITY.get(current, 0):
        dispositions[section_id] = disposition


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
        "packet_policy": "M20-S118",
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
