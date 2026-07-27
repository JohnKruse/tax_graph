"""Form-complete, reading-order cell inventory for the review workbench.

The review unit is the form cell. The IRS designed the form as discrete cells; a
reviewer walks it top to bottom and hops freely, and each cell carries its own
printed instruction. So the workbench's cell list must come from the FORM - every
addressable, clickable control on the page - not from whichever cells happened to
land in the deferred-review queue.

This module assembles that list by joining four published artifacts on a single key:

- geometry (``graph/<year>/node_geometry.json``) is the spine: one physical clickable
  field per entry, with the page + rect the center pane draws;
- the address inventory (``graph/<year>/addresses/<doc>.yaml``) gives the authored
  reviewer-facing label, the printed line/box ref, and the control role;
- the field dispositions (``graph/<year>/field_maps/<doc>.yaml``) give the one
  population policy every control carries, plus its value format and, for the
  unsupported/blank policies, the reason;
- the node bindings (``graph/<year>/bindings/nodes/<doc>.yaml``) give the computing
  node an amount cell is filled from, so "what feeds this cell" is real.

It is projection-only and stdlib+yaml only: the workbench must not import the pipeline
package (the M17-S2 import-boundary lesson), so it reads the canonical serializations
directly and reuses only the stdlib-only ref deriver.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field as dataclass_field
import json
from pathlib import Path
import re
from typing import Any

import yaml

from workbench.refs import unit_ref_from_address


# Address kinds that name a reviewable cell (a control the filer/engine populates or
# checks). A promoted ``column`` is also reviewable: it is a physical instance of a
# concept-level repeatable field. Unpromoted containers remain invisible.
CELL_ADDRESS_KINDS = frozenset({"control", "option"})


@dataclass(frozen=True)
class DocumentCells:
    """The ordered, form-complete reviewable cell list for one document."""

    document_id: str
    cells: list[dict[str, Any]]
    pages: list[int] = dataclass_field(default_factory=list)
    page_geometry: list[dict[str, Any]] = dataclass_field(default_factory=list)


def build_document_cells(
    root: str | Path,
    year: str | int,
    document_id: str,
    *,
    geometry_entries: list[dict[str, Any]] | None = None,
    page_geometry: list[dict[str, Any]] | None = None,
    include_inputs: bool = True,
) -> DocumentCells:
    """Assemble the reading-order cell list for one document.

    Every physical field with page geometry becomes exactly one cell, ordered by
    (page, top, left) so the list flows the way the form reads. Cells are joined to
    their address, disposition, and node binding by identifier; a missing join is
    surfaced on the cell (e.g. ``population_policy: None``) rather than dropping it,
    so a coverage gap is visible in review instead of invisible.

    ``geometry_entries`` may pass an already-loaded geometry list (the whole
    document set is one 1.4 MB file, so the documents index loads it once and
    filters per document rather than re-reading it).
    """
    graph_dir = Path(root) / "graph" / str(year)
    if geometry_entries is None:
        geometry_payload = _load_geometry_payload(graph_dir / "node_geometry.json")
        geometry = [
            entry for entry in geometry_payload.get("entries", [])
            if _geometry_is_cell(entry) and str(entry.get("document_id") or "") == document_id
        ]
        page_geometry = [
            item for item in geometry_payload.get("pages", [])
            if isinstance(item, dict) and str(item.get("document_id") or "") == document_id
        ]
    else:
        geometry = [
            entry for entry in geometry_entries
            if _geometry_is_cell(entry) and str(entry.get("document_id") or "") == document_id
        ]
        page_geometry = [
            item for item in page_geometry or []
            if str(item.get("document_id") or "") == document_id
        ]
    addresses = _load_addresses(graph_dir / "addresses" / f"{document_id}.yaml")
    dispositions = _load_dispositions(graph_dir / "field_maps" / f"{document_id}.yaml")
    bindings = _load_node_bindings(graph_dir / "bindings" / "nodes" / f"{document_id}.yaml")
    citations = _load_citations(graph_dir / "citations")
    node_metadata = _load_node_metadata(graph_dir / "nodes")
    operations = _load_node_operations(graph_dir)
    # The operands of a computed cell are the graph edges feeding its node; resolving
    # them to refs needs the node->address map across every document (a sum can draw
    # from another form). Only loaded when a caller renders detail, not for counts.
    calc_inputs = _load_calc_edges(graph_dir) if include_inputs else {}
    node_to_ref = _load_node_ref_index(graph_dir) if include_inputs else {}

    ordered = sorted(
        geometry,
        key=lambda entry: (
            int(entry["page"]),
            round(float(entry["rect"][1]), 1),
            round(float(entry["rect"][0]), 1),
        ),
    )
    cells: list[dict[str, Any]] = []
    pages: set[int] = set()
    used_ids: set[str] = set()
    for order, entry in enumerate(ordered):
        address_id = str(entry.get("address_id") or "")
        address = addresses.get(address_id, {})
        if address and not _address_is_reviewable(address):
            # A geometry rect anchored to an unpromoted container is not a filer cell.
            continue
        disposition = dispositions.get(str(entry.get("field_name") or ""), {})
        binding = bindings.get(address_id)
        node_id = str(binding["node_id"]) if binding and binding.get("node_id") else None
        node_data = node_metadata.get(node_id, {}) if node_id else {}
        citation_address = {
            "citation_refs": [
                *(address.get("citation_refs", []) or []),
                *(node_data.get("citation_refs", []) or []),
            ]
        }
        citation_records = _citations(citation_address, citations)
        instruction_citations, authority_citations = _split_citations(citation_records)
        page = int(entry["page"])
        pages.add(page)
        cells.append(
            {
                "cell_id": _cell_id(entry, used_ids),
                "document_id": document_id,
                "inputs": _cell_inputs(node_id, calc_inputs, node_to_ref) if include_inputs else [],
                "address_id": address_id or None,
                "ref": unit_ref_from_address(
                    address_id,
                    disposition.get("occurrence") or address.get("occurrence"),
                ) if address_id else None,
                "concept_id": str(address.get("concept_id") or "") or None,
                "review_granularity": "concept" if address.get("concept_id") else None,
                "occurrence": disposition.get("occurrence") or address.get("occurrence"),
                "order": order,
                "page": page,
                "rect": [float(value) for value in entry["rect"]],
                "field_name": str(entry.get("field_name") or "") or None,
                "section": _breadcrumb(address),
                "official_ref": _official_ref(address),
                "control_role": str(address.get("control_role") or "") or None,
                "display_name": _display_name(address, disposition, entry),
                "population_policy": str(disposition.get("population_policy") or "") or None,
                "value_format": str(disposition.get("value_format") or "") or None,
                "repeatable": disposition.get("repeatable"),
                "policy_reason": str(disposition.get("reason") or "") or None,
                "downstream_effect": str(disposition.get("downstream_effect") or "") or None,
                "missing_capability": str(disposition.get("missing_capability") or "") or None,
                "node_id": node_id,
                "operation": operations.get(node_id),
                "instruction_citations": instruction_citations,
                "citations": authority_citations,
            }
        )
    return DocumentCells(
        document_id=document_id,
        cells=cells,
        pages=sorted(pages),
        page_geometry=sorted(page_geometry or [], key=lambda item: int(item["page"])),
    )


def _breadcrumb(address: dict[str, Any]) -> str | None:
    """Return the section/line token a cell hangs under, for a reading-order header."""
    for component in address.get("path", []) or []:
        if isinstance(component, dict) and component.get("kind") in {"section", "line", "table"}:
            token = str(component.get("token") or "")
            if token:
                return token
    return None


def _official_ref(address: dict[str, Any]) -> str | None:
    ref = address.get("official_ref")
    if ref:
        return str(ref)
    # Section-scoped header controls have no printed line number; fall back to the
    # section token so the reviewer still sees where it sits.
    return _breadcrumb(address)


def _display_name(
    address: dict[str, Any], disposition: dict[str, Any], entry: dict[str, Any]
) -> str:
    """Prefer the authored, reviewer-facing label; never a raw field name."""
    printed = str(address.get("printed_label") or "").strip()
    if printed and printed.lower() != str(entry.get("field_name") or "").lower():
        return printed
    label = str(disposition.get("label") or "").strip()
    if label:
        return label
    return printed or str(entry.get("field_name") or "unnamed control")


def _citations(
    address: dict[str, Any], citation_index: dict[str, dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Resolve address citation ids to verbatim, provenance-bearing records.

    An unresolved id is retained with null source fields so the workbench exposes a
    coverage problem instead of silently dropping it or fabricating citation text.
    """
    citation_index = citation_index or {}
    resolved: list[dict[str, Any]] = []
    for value in sorted({str(value) for value in address.get("citation_refs", []) or []}):
        record = citation_index.get(value)
        if record is None:
            resolved.append(
                {
                    "citation_id": value,
                    "quoted_text": None,
                    "locator": None,
                    "url": None,
                    "retrieved_date": None,
                    "source_document_id": None,
                    "resolved": False,
                }
            )
            continue
        resolved.append(dict(record, resolved=True))
    return resolved


def _split_citations(
    citations: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separate instruction citations from governing form/authority citations.

    The citation records are already resolved from promoted artifacts. The source
    document role is the only routing signal: instruction text belongs in the
    instruction slot, while every other record remains authority for the dossier.
    Unresolved records stay in authority because their source role is unknown and
    the workbench must not infer it.
    """
    instruction: list[dict[str, Any]] = []
    authority: list[dict[str, Any]] = []
    for citation in citations:
        source_document_id = str(citation.get("source_document_id") or "")
        if source_document_id.startswith("instructions_"):
            instruction.append(citation)
        else:
            authority.append(citation)
    return instruction, authority


def _cell_id(entry: dict[str, Any], used: set[str]) -> str:
    """A stable, unique, ``[a-z0-9_]`` id per physical field.

    The session schema constrains review keys to ``^[a-z0-9_]+$``, so the raw
    AcroForm field name (with dots and brackets) is sanitized. Sanitization can
    collapse two distinct names onto one token, so a deterministic numeric suffix
    keeps the id unique within the document without depending on iteration order
    beyond the already-fixed reading order.
    """
    field_name = str(entry.get("field_name") or entry.get("address_id") or "cell")
    base = re.sub(r"[^a-z0-9]+", "_", field_name.lower()).strip("_") or "cell"
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}_{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def _geometry_is_cell(entry: Any) -> bool:
    """True when a geometry entry is a placeable physical field."""
    return (
        isinstance(entry, dict)
        and entry.get("page") is not None
        and isinstance(entry.get("rect"), list)
        and len(entry["rect"]) == 4
    )


def _address_is_reviewable(address: dict[str, Any]) -> bool:
    """Return whether an address names a control or promoted concept instance."""
    kind = str(address.get("kind") or "control")
    return kind in CELL_ADDRESS_KINDS or (kind == "column" and bool(address.get("concept_id")))


def build_documents_index(
    root: str | Path,
    year: str | int,
    document_ids: list[str],
    *,
    geometry_entries: list[dict[str, Any]],
    page_geometry: list[dict[str, Any]] | None = None,
    titles: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Summarize each document for the left-rail picker (id, title, pages, count).

    Loads no geometry itself: the caller passes the single already-loaded geometry
    list, and each document filters it. Documents with zero placeable cells are
    omitted so the picker never shows an unreviewable form.
    """
    titles = titles or {}
    summaries: list[dict[str, Any]] = []
    for document_id in sorted(set(document_ids)):
        document_page_geometry = [
            item for item in page_geometry or []
            if str(item.get("document_id") or "") == document_id
        ]
        built = build_document_cells(
            root,
            year,
            document_id,
            geometry_entries=geometry_entries,
            page_geometry=document_page_geometry,
            include_inputs=False,
        )
        if not built.cells:
            continue
        summaries.append(
            {
                "document_id": document_id,
                "title": titles.get(document_id, document_id),
                "pages": built.pages,
                "page_geometry": built.page_geometry,
                "cell_count": len(built.cells),
                "policy_counts": dict(sorted(
                    Counter(cell.get("population_policy") or "unknown" for cell in built.cells).items()
                )),
                "citation_counts": {
                    "cited": sum(
                        bool(cell.get("citations") or cell.get("instruction_citations"))
                        for cell in built.cells
                    ),
                    "uncited": sum(
                        not bool(cell.get("citations") or cell.get("instruction_citations"))
                        for cell in built.cells
                    ),
                },
            }
        )
    return summaries


def _load_geometry_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload


def _load_addresses(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        str(item["address_id"]): item
        for item in payload.get("addresses", []) or []
        if isinstance(item, dict) and item.get("address_id")
    }


def _load_dispositions(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        str(item["field_name"]): item
        for item in payload.get("field_dispositions", []) or []
        if isinstance(item, dict) and item.get("field_name")
    }


def _load_citations(directory: Path) -> dict[str, dict[str, Any]]:
    """Index promoted citation records without importing the pipeline package."""
    if not directory.is_dir():
        return {}
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        records = payload.get("citations", []) if isinstance(payload, dict) else payload
        for item in records or []:
            if not isinstance(item, dict) or not item.get("citation_id"):
                continue
            citation_id = str(item["citation_id"])
            record = {
                "citation_id": citation_id,
                "quoted_text": item.get("quoted_text"),
                "locator": item.get("locator"),
                "url": item.get("url"),
                "retrieved_date": _date_text(item.get("retrieved_date")),
                "source_document_id": item.get("source_document_id") or item.get("document_id"),
            }
            if item.get("semantic_title"):
                record["semantic_title"] = item["semantic_title"]
            result[citation_id] = record
    return result


def _load_node_metadata(directory: Path) -> dict[str, dict[str, Any]]:
    """Load node citation metadata for graph-backed cell authority."""
    if not directory.is_dir():
        return {}
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        records = payload.get("nodes", []) if isinstance(payload, dict) else payload
        for item in records or []:
            if isinstance(item, dict) and item.get("node_id"):
                result[str(item["node_id"])] = item
    return result


def _load_node_operations(graph_dir: Path) -> dict[str, str]:
    """Resolve a computed node's operation from its incoming graph edge rule."""
    rules: dict[str, str] = {}
    rules_dir = graph_dir / "rules"
    for path in sorted(rules_dir.glob("*.yaml")) if rules_dir.is_dir() else []:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        records = payload.get("rules", []) if isinstance(payload, dict) else payload
        for item in records or []:
            if isinstance(item, dict) and item.get("rule_id") and item.get("operation"):
                rules[str(item["rule_id"])] = str(item["operation"])
    operations: dict[str, str] = {}
    edges_dir = graph_dir / "edges"
    for path in sorted(edges_dir.glob("*.yaml")) if edges_dir.is_dir() else []:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        records = payload.get("edges", []) if isinstance(payload, dict) else payload
        for item in records or []:
            if not isinstance(item, dict) or not item.get("target"):
                continue
            operation = rules.get(str(item.get("rule_id") or ""))
            if operation:
                operations.setdefault(str(item["target"]), operation)
    return operations


def _date_text(value: Any) -> str | None:
    """Normalize YAML date scalars so the JSON projection stays string-valued."""
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _cell_inputs(
    node_id: str | None,
    calc_inputs: dict[str, list[str]],
    node_to_ref: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    """Resolve a computed cell's operand cells (the graph edges feeding its node)."""
    if not node_id:
        return []
    resolved: list[dict[str, Any]] = []
    for source_node in calc_inputs.get(node_id, []):
        target = node_to_ref.get(source_node)
        resolved.append(
            {
                "node_id": source_node,
                "ref": (target or {}).get("ref"),
                "display_name": (target or {}).get("display_name") or source_node,
            }
        )
    return resolved


def _load_calc_edges(graph_dir: Path) -> dict[str, list[str]]:
    """Map each target node to the source nodes that calculate into it.

    Edges are split across ``graph/<year>/edges/*.yaml`` by topic, not by document
    (a sum can draw from another form), so every edge file is indexed by target.
    """
    edges_dir = graph_dir / "edges"
    if not edges_dir.is_dir():
        return {}
    result: dict[str, list[str]] = {}
    for path in sorted(edges_dir.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        edges = payload.get("edges", []) if isinstance(payload, dict) else payload
        for edge in edges or []:
            if not isinstance(edge, dict):
                continue
            relationship = str(edge.get("relationship") or "").upper()
            if relationship and relationship not in {"CALCULATES", "SUMS", "FLOWS_TO", "COPIES"}:
                continue
            source = edge.get("source")
            target = edge.get("target")
            if source and target:
                result.setdefault(str(target), []).append(str(source))
    return result


def _load_node_ref_index(graph_dir: Path) -> dict[str, dict[str, str]]:
    """Map every value-bound node to its cell ref, across all documents.

    Lets a computed cell name its operands as quotable refs the reviewer can hop to,
    even when a source lives on another form.
    """
    result: dict[str, dict[str, str]] = {}
    bindings_dir = graph_dir / "bindings" / "nodes"
    if not bindings_dir.is_dir():
        return result
    addresses_dir = graph_dir / "addresses"
    label_by_address: dict[str, str] = {}
    for path in sorted(addresses_dir.glob("*.yaml")) if addresses_dir.is_dir() else []:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for item in payload.get("addresses", []) or []:
            if isinstance(item, dict) and item.get("address_id"):
                label_by_address[str(item["address_id"])] = str(item.get("printed_label") or "")
    for path in sorted(bindings_dir.glob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for item in payload.get("bindings", []) or []:
            if not isinstance(item, dict) or not item.get("node_id") or not item.get("address_id"):
                continue
            if str(item.get("role") or "value") != "value":
                continue
            address_id = str(item["address_id"])
            ref = unit_ref_from_address(address_id)
            result[str(item["node_id"])] = {
                "ref": ref or address_id,
                "display_name": label_by_address.get(address_id, ""),
            }
    return result


def _load_node_bindings(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    result: dict[str, dict[str, Any]] = {}
    for item in payload.get("bindings", []) or []:
        if not isinstance(item, dict) or not item.get("address_id"):
            continue
        # The value-role binding is the one that fills the printed amount cell.
        if str(item.get("role") or "value") == "value":
            result[str(item["address_id"])] = item
    return result
