"""Build the graph-derived cell review projection without reading the queue."""

from __future__ import annotations

import hashlib
from pathlib import Path
from collections import Counter
from typing import Any

from workbench.address_verdicts import (
    derive_cell_coverage,
    expression_kind_bucket,
    report_blast_radius,
    unit_address,
    unit_fingerprint,
)
from workbench.manifest import build_manifest


def build_derived_cell_units(
    root: str | Path,
    year: str | int,
    *,
    geometry_entries: list[dict[str, Any]] | None = None,
    page_geometry: list[dict[str, Any]] | None = None,
    manifest: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return one address-keyed review unit for every reviewable graph cell."""
    root_path = Path(root).resolve()
    del geometry_entries, page_geometry
    manifest = manifest or build_manifest(root_path, year)
    sources = [
        source
        for entry in manifest.get("entries", []) or []
        if isinstance(entry, dict) and str(entry.get("review_kind")) == "form_cell"
        for source in entry.get("units", []) or []
        if isinstance(source, dict)
    ]
    address_counts = Counter(
        str(source.get("address_id") or "")
        for source in sources
        if str(source.get("address_id") or "")
    )
    units: list[dict[str, Any]] = []
    for source in sources:
        base_address = str(source.get("address_id") or "")
        if base_address or source.get("node_id"):
            address = _cell_address(
                source,
                year,
                node_id=str(source.get("node_id") or ""),
                duplicate=bool(base_address and address_counts[base_address] > 1),
            )
        else:
            address = _fallback_address(source, year)
        address = address or unit_address(source) or _fallback_address(source, year)
        if not address:
            raise ValueError(f"derived review unit has no canonical address: {source.get('unit_id', '<unknown>')}")
        unit_id = "derived_" + hashlib.sha256(address.encode("utf-8")).hexdigest()[:32]
        location = source.get("official_location")
        expression = source.get("expression") or {"kind": "reference"}
        kind_bucket = expression_kind_bucket(expression.get("kind"))
        unit: dict[str, Any] = {
            "unit_id": unit_id,
            "document_id": _document_id(source, source),
            "address": address,
            "address_id": address,
            "base_address_id": str(source.get("address_id") or "") or None,
            "node_id": str(source.get("node_id") or "") or None,
            "field_name": str(source.get("field_name") or "") or None,
            "display_name": str(source.get("display_name") or address),
            "expression": expression,
            "review_content": source.get("review_content") or {},
            "content_fingerprint": unit_fingerprint(source),
            "citation_refs": sorted(str(value) for value in source.get("citation_refs", []) or []),
            "identity_source": str(source.get("identity_source") or "object_id"),
            "kind_bucket": kind_bucket,
            "form_citations": list(source.get("form_citations", []) or []),
            "instruction_citations": list(source.get("instruction_citations", []) or []),
        }
        if isinstance(location, dict):
            unit["page"] = int(location["page"])
            unit["rect"] = list(location["rect"])
        units.append(unit)
    return units


def build_derived_coverage(
    root: str | Path,
    year: str | int,
    history: list[dict[str, Any]],
    *,
    geometry_entries: list[dict[str, Any]] | None = None,
    page_geometry: list[dict[str, Any]] | None = None,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Walk current graph cells against verdict history and return coverage plus findings."""
    units = build_derived_cell_units(
        root,
        year,
        geometry_entries=geometry_entries,
        page_geometry=page_geometry,
        manifest=manifest,
    )
    coverage = derive_cell_coverage(units, history)
    coverage["blast_radius"] = report_blast_radius(units, history)
    fallback = [
        {
            "code": "unaddressed_cell",
            "unit_id": unit["unit_id"],
            "document_id": unit["document_id"],
            "field_name": unit["field_name"],
            "reason": "no promoted address or bound node; field-qualified control identity used",
        }
        for unit in units
        if unit["identity_source"] == "field_name"
    ]
    coverage["findings"] = fallback
    coverage["identity_sources"] = {
        source: sum(unit["identity_source"] == source for unit in units)
        for source in ("address_id", "object_id", "node_id", "field_name")
    }
    coverage["kind_buckets"] = {
        bucket: sum(unit["kind_bucket"] == bucket for unit in units)
        for bucket in ("ARITHMETIC", "COPY", "USER_ENTRY", "IMPORTED", "PER_ROW", "NOT_REVIEWABLE")
    }
    coverage["denominator"] = len(units)
    return coverage


def _document_id(unit: dict[str, Any], entry: dict[str, Any]) -> str:
    location = unit.get("official_location")
    if isinstance(location, dict) and location.get("document_id"):
        return str(location["document_id"])
    if unit.get("identity_document_id"):
        return str(unit["identity_document_id"])
    return str(entry.get("queue_id") or "unlocated")


def _fallback_address(unit: dict[str, Any], year: str | int) -> str:
    field_name = str(unit.get("field_name") or "")
    document_id = _document_id(unit, unit)
    if field_name:
        return f"control/{document_id}/{field_name}"
    return ""


def _cell_address(
    cell: dict[str, Any],
    year: str | int,
    *,
    node_id: str = "",
    duplicate: bool = False,
) -> str:
    address = str(cell.get("address_id") or "").strip()
    if address and duplicate:
        occurrence = cell.get("occurrence")
        axes = occurrence.get("axes") if isinstance(occurrence, dict) else None
        if isinstance(axes, dict) and axes:
            suffix = "/occurrence=" + ",".join(f"{key}={axes[key]}" for key in sorted(axes))
            return address + suffix
        field_name = str(cell.get("field_name") or "").strip()
        if field_name:
            return address + "/field=" + field_name
    if address:
        return address
    if node_id:
        return node_id
    document_id = str(cell.get("document_id") or "unknown")
    field_name = str(cell.get("field_name") or "unknown")
    return f"control/{document_id}/{field_name}"
