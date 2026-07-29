"""Build the graph-derived cell review projection without reading the queue."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from workbench.address_verdicts import derive_cell_coverage, report_blast_radius, review_content_fingerprint
from workbench.cell_inventory import build_document_cells


def build_derived_cell_units(
    root: str | Path,
    year: str | int,
    *,
    geometry_entries: list[dict[str, Any]] | None = None,
    page_geometry: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Return one address-keyed review unit for every physical form control."""
    root_path = Path(root).resolve()
    if geometry_entries is None:
        import json

        geometry_payload = json.loads(
            (root_path / "graph" / str(year) / "node_geometry.json").read_text(encoding="utf-8")
        )
        geometry_entries = [item for item in geometry_payload.get("entries", []) if isinstance(item, dict)]
        page_geometry = [item for item in geometry_payload.get("pages", []) if isinstance(item, dict)]
    documents = sorted({str(item.get("document_id")) for item in geometry_entries if item.get("document_id")})
    geometry_node_ids = {
        (str(item.get("document_id") or ""), str(item.get("field_name") or "")): str(item.get("node_id") or "")
        for item in geometry_entries
        if isinstance(item, dict) and item.get("node_id") and item.get("field_name")
    }
    units: list[dict[str, Any]] = []
    for document_id in documents:
        cells = build_document_cells(
            root_path,
            year,
            document_id,
            geometry_entries=geometry_entries,
            page_geometry=page_geometry,
            include_inputs=False,
        ).cells
        base_counts: dict[str, int] = {}
        for cell in cells:
            base = str(cell.get("address_id") or "").strip()
            if base:
                base_counts[base] = base_counts.get(base, 0) + 1
        for cell in cells:
            node_id = str(cell.get("node_id") or geometry_node_ids.get((document_id, str(cell.get("field_name") or ""))) or "")
            address = _cell_address(
                cell,
                year,
                node_id=node_id,
                duplicate=base_counts.get(str(cell.get("address_id") or ""), 0) > 1,
            )
            cited_text = [
                str(item["quoted_text"])
                for item in (cell.get("instruction_citations", []) or []) + (cell.get("citations", []) or [])
                if isinstance(item, dict) and item.get("quoted_text")
            ]
            label = str(cell.get("display_name") or cell.get("field_name") or address)
            unit_id = "derived_" + hashlib.sha256(address.encode("utf-8")).hexdigest()[:32]
            unit: dict[str, Any] = {
                "unit_id": unit_id,
                "document_id": document_id,
                "address": address,
                "address_id": address,
                "base_address_id": str(cell.get("address_id") or "") or None,
                "node_id": node_id or None,
                "field_name": str(cell.get("field_name") or "") or None,
                "display_name": label,
                "review_content": {"label": label, "cited_text": cited_text},
                "content_fingerprint": review_content_fingerprint(label, cited_text),
                "page": int(cell["page"]),
                "rect": list(cell["rect"]),
                "citation_refs": sorted({
                    str(item.get("citation_id"))
                    for item in (cell.get("instruction_citations", []) or []) + (cell.get("citations", []) or [])
                    if isinstance(item, dict) and item.get("citation_id")
                }),
                "identity_source": "address_id" if cell.get("address_id") else ("node_id" if node_id else "field_name"),
            }
            units.append(unit)
    return units


def build_derived_coverage(
    root: str | Path,
    year: str | int,
    history: list[dict[str, Any]],
    *,
    geometry_entries: list[dict[str, Any]] | None = None,
    page_geometry: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Walk current cells against verdict history and return coverage plus findings."""
    units = build_derived_cell_units(
        root,
        year,
        geometry_entries=geometry_entries,
        page_geometry=page_geometry,
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
        for source in ("address_id", "node_id", "field_name")
    }
    coverage["denominator"] = len(units)
    return coverage


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
