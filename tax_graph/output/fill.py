"""Formatting-only official PDF form filler.

PyMuPDF is imported only inside PDF I/O functions so the normal runtime stays
base-dependency light.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from tax_graph.engine import MISSING, Result
from tax_graph.output.field_maps import inventory_by_name


DEPENDENTS_TABLE_GROUP = "dependents"


class PdfExtraRequired(RuntimeError):
    """Raised when a PDF export is requested without the optional extra."""


class DependentAttachmentRequired(ValueError):
    """Raised when Form 1040 needs an unsupported dependent attachment."""


@dataclass(frozen=True)
class FilledForm:
    """Result of filling and reopening one official form."""

    document_id: str
    output_path: Path
    field_values: dict[str, str]
    blank_with_note: tuple[dict[str, str], ...]


def build_field_values(
    field_map: Mapping[str, Any],
    result: Result,
    facts_document: Mapping[str, Any],
    *,
    root: str | Path,
) -> tuple[dict[str, str], tuple[dict[str, str], ...]]:
    """Format engine values and supplied identity facts for one field map."""
    inventory = inventory_by_name(field_map, root)
    frontier_fields = {item["field_name"] for item in field_map.get("frontier_fields", [])}
    blank_notes = tuple(dict(item) for item in field_map.get("frontier_fields", []))
    identity = dict(facts_document.get("identity") or {})
    identity.setdefault("filing_status", facts_document.get("filing_status"))
    dependents = list(facts_document.get("dependents", []) or [])
    if len(dependents) > 4:
        raise DependentAttachmentRequired(
            "Form 1040 supports four printed dependents; five or more require an attached dependent statement, which this output profile does not yet generate."
        )
    values: dict[str, str] = {}
    table_rows = {
        table.get("table_id"): list(table.get("rows") or [])
        for table in facts_document.get("tables", []) or []
    }

    for mapping in field_map.get("mappings", []):
        field_name = mapping["field_name"]
        if field_name in frontier_fields:
            continue
        if mapping.get("format") == "checkbox":
            if identity.get(mapping["identity_slot"]) == mapping.get("checkbox_value"):
                values[field_name] = str(inventory[field_name].get("on_state") or "Yes")
            continue
        if "identity_slot" in mapping:
            raw_value = identity.get(mapping["identity_slot"])
        elif str(mapping.get("slot", "")).startswith("table:"):
            raw_value = _table_slot_value(mapping, table_rows, result)
        else:
            raw_value = result.values.get(mapping["node_id"], MISSING)
        if raw_value is MISSING or raw_value is None or raw_value == "":
            continue
        values[field_name] = _format_value(raw_value, mapping.get("format", "text"))
    for disposition in field_map.get("field_dispositions", []) or []:
        repeatable = disposition.get("repeatable") or {}
        if repeatable.get("group") != DEPENDENTS_TABLE_GROUP:
            continue
        index = int(repeatable["row_slot"]) - 1
        if index >= len(dependents):
            continue
        dependent = dependents[index]
        column = str(repeatable["column"])
        if repeatable.get("role") == "identity":
            raw_value = dependent.get(column)
            if raw_value not in (None, ""):
                values[str(disposition["field_name"])] = str(raw_value)
            continue
        decision = (dependent.get("eligibility_decisions") or {}).get(column)
        if isinstance(decision, Mapping) and decision.get("value") is True:
            values[str(disposition["field_name"])] = str(
                inventory[str(disposition["field_name"])].get("on_state") or "Yes"
            )
    return values, blank_notes


def fill_official_pdf(
    pdf_path: str | Path,
    output_path: str | Path,
    *,
    document_id: str,
    field_values: Mapping[str, str],
    blank_with_note: tuple[dict[str, str], ...] = (),
) -> FilledForm:
    """Fill, reopen, and echo-check one official IRS PDF."""
    fitz = _fitz()
    source = Path(pdf_path)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(source) as document:
        seen: set[str] = set()
        for page in document:
            for widget in page.widgets() or []:
                if widget.field_name not in field_values:
                    continue
                widget.field_value = str(field_values[widget.field_name])
                widget.update()
                seen.add(widget.field_name)
        missing = set(field_values) - seen
        if missing:
            raise ValueError(f"fields absent from PDF {document_id}: {sorted(missing)}")
        document.save(destination)
    reread = read_pdf_field_values(destination, selected=set(field_values))
    intended = dict(field_values)
    if reread != intended:
        raise ValueError(f"filled PDF echo mismatch for {document_id}: intended={intended!r} reread={reread!r}")
    return FilledForm(document_id, destination, intended, blank_with_note)


def read_pdf_field_values(pdf_path: str | Path, *, selected: set[str] | None = None) -> dict[str, str]:
    """Read normalized nonblank AcroForm values from a PDF."""
    fitz = _fitz()
    values: dict[str, str] = {}
    with fitz.open(pdf_path) as document:
        for page in document:
            for widget in page.widgets() or []:
                if selected is not None and widget.field_name not in selected:
                    continue
                value = "" if widget.field_value in (None, "Off") else str(widget.field_value)
                if value:
                    values[widget.field_name] = value
    return values


def _table_slot_value(
    mapping: Mapping[str, Any],
    table_rows: Mapping[str, list[Mapping[str, Any]]],
    result: Result,
) -> Any:
    _prefix, table_id, row_text, _column = str(mapping["slot"]).split(":", 3)
    rows = table_rows.get(table_id, [])
    index = int(row_text) - 1
    if index >= len(rows):
        return MISSING
    row_key = rows[index].get("row_key")
    return result.values.get(f"{mapping['node_id']}#{row_key}", MISSING)


def _format_value(value: Any, style: str) -> str:
    if style != "dollars":
        return str(value)
    number = round(float(value))
    amount = str(abs(number))
    return f"({amount})" if number < 0 else amount


def _fitz() -> Any:
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - exercised in a clean base-deps subprocess.
        raise PdfExtraRequired("PDF export requires: pip install 'tax-graph[pdf]'") from exc
    return fitz
