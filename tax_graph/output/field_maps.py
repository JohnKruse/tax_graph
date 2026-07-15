"""Load and validate AcroForm inventories and node-to-field maps."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable, Mapping

import yaml


@dataclass(frozen=True)
class FieldDispositionMigration:
    """Deterministic v1-to-v2 proposal plus fields requiring authored policy."""

    document_id: str
    proposed_dispositions: tuple[dict[str, Any], ...]
    authored_work: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class FieldDispositionMigrationResult:
    """Stable migration report for every existing field map."""

    documents: tuple[FieldDispositionMigration, ...]
    output_path: Path


def load_field_maps(year: str | int, root: str | Path) -> list[dict[str, Any]]:
    """Load field maps in stable document order."""
    directory = Path(root) / "graph" / str(year) / "field_maps"
    return [yaml.safe_load(path.read_text(encoding="utf-8")) for path in sorted(directory.glob("*.yaml"))]


def validate_field_maps(
    year: str | int,
    root: str | Path,
    *,
    node_ids: Iterable[str],
    frontier_ids: Iterable[str],
    check_exposed_pdfs: bool = False,
) -> list[str]:
    """Validate schemas and both sides of every authored field mapping."""
    root_path = Path(root)
    schema = json.loads((root_path / "schemas" / "field_map.schema.json").read_text(encoding="utf-8"))
    known_nodes = set(node_ids)
    known_frontier = set(frontier_ids)
    errors: list[str] = []
    address_ids: set[str] = set()
    widget_addresses: dict[tuple[str, str], str] = {}
    if (root_path / "graph" / str(year) / "addresses").is_dir():
        try:
            from tax_graph.addressing import load_address_artifacts
            artifacts = load_address_artifacts(year, root_path)
            address_ids = {item.address_id for item in artifacts.addresses}
            widget_addresses = {(item["document_id"], item["field_name"]): item["address_id"] for item in artifacts.widget_bindings}
        except (ValueError, OSError) as exc:
            errors.append(f"canonical addresses {year} -> {exc}")
    try:
        import jsonschema
    except ImportError:  # pragma: no cover - base dependency in supported installs.
        jsonschema = None

    for field_map in load_field_maps(year, root_path):
        document_id = field_map.get("document_id", "<unknown>")
        if jsonschema is not None:
            try:
                jsonschema.validate(field_map, schema)
            except jsonschema.ValidationError as exc:
                errors.append(f"field map {document_id} -> schema: {exc.message}")
                continue
        inventory_path = root_path / str(field_map["inventory"])
        if not inventory_path.exists():
            errors.append(f"field map {document_id} -> missing inventory {field_map['inventory']}")
            continue
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        inventory_items = inventory.get("fields", [])
        field_names = [item["field_name"] for item in inventory_items]
        fields = set(field_names)
        if len(fields) != len(field_names):
            errors.append(f"field map {document_id} -> inventory contains duplicate field names")
        mapped_fields: set[str] = set()
        mapped_nodes: set[str] = set()
        excluded_items = {item["node_id"]: item for item in field_map.get("excluded_nodes", [])}
        excluded_nodes = set(excluded_items)
        for mapping in field_map.get("mappings", []):
            field_name = mapping["field_name"]
            if field_name not in fields:
                errors.append(f"field map {document_id} -> unknown AcroForm field {field_name}")
            if field_name in mapped_fields:
                errors.append(f"field map {document_id} -> field mapped more than once: {field_name}")
            mapped_fields.add(field_name)
            address_id = mapping.get("address_id")
            if address_id:
                if address_id not in address_ids:
                    errors.append(f"field map {document_id} -> unknown address {address_id}")
                if widget_addresses.get((document_id, field_name)) != address_id:
                    errors.append(f"field map {document_id} -> widget binding disagrees for {field_name}")
            node_id = mapping.get("node_id")
            if node_id:
                if node_id not in known_nodes:
                    errors.append(f"field map {document_id} -> unknown node {node_id}")
                mapped_nodes.add(node_id)
        for node_id in excluded_nodes:
            if node_id not in known_nodes and not excluded_items[node_id].get("optional_extension"):
                errors.append(f"field map {document_id} -> excluded unknown node {node_id}")
        overlap = mapped_nodes & excluded_nodes
        for node_id in sorted(overlap):
            errors.append(f"field map {document_id} -> node both mapped and excluded: {node_id}")
        uncovered = {
            node_id
            for node_id in known_nodes
            if node_id.startswith(f"{document_id}_") and node_id not in mapped_nodes and node_id not in excluded_nodes
        }
        for node_id in sorted(uncovered):
            errors.append(f"field map {document_id} -> node is neither mapped nor explicitly excluded: {node_id}")
        for item in field_map.get("frontier_fields", []):
            if item["field_name"] not in fields:
                errors.append(f"field map {document_id} -> frontier field missing from inventory: {item['field_name']}")
        if field_map.get("schema_version") == 2:
            errors.extend(
                _validate_dispositions(
                    field_map,
                    fields=fields,
                    known_nodes=known_nodes,
                    known_frontier=known_frontier,
                )
            )
    if check_exposed_pdfs:
        errors.extend(validate_exposed_pdf_fields(year, root_path))
    return errors


def validate_exposed_pdf_fields(year: str | int, root: str | Path) -> list[str]:
    """Compare every exposed AcroForm widget with its committed inventory/map.

    Instruction PDFs and other PDFs with no widgets are intentionally exempt.
    PyMuPDF is imported only inside this build-time check so runtime modules stay
    free of build-only imports.
    """
    root_path = Path(root)
    pdf_root = root_path / ".cache" / "raw" / str(year)
    if not pdf_root.is_dir():
        return []
    maps = {item["document_id"]: item for item in load_field_maps(year, root_path)}
    errors: list[str] = []
    for pdf_path in sorted(pdf_root.glob("*.pdf")):
        stat = pdf_path.stat()
        widget_names = _enumerate_pdf_widgets_isolated(
            str(pdf_path.resolve()), stat.st_size, stat.st_mtime_ns
        )
        if not widget_names:
            continue
        document_id = pdf_path.stem
        field_map = maps.get(document_id)
        if field_map is None:
            errors.append(f"exposed AcroForm {document_id} -> missing committed field map and inventory")
            continue
        inventory_path = root_path / str(field_map["inventory"])
        if not inventory_path.is_file():
            errors.append(f"exposed AcroForm {document_id} -> missing inventory {field_map['inventory']}")
            continue
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        inventory_names = [str(item["field_name"]) for item in inventory.get("fields", [])]
        if len(inventory_names) != len(set(inventory_names)):
            errors.append(f"exposed AcroForm {document_id} -> inventory contains duplicate field names")
        missing = widget_names - set(inventory_names)
        extra = set(inventory_names) - widget_names
        if missing or extra:
            errors.append(
                f"exposed AcroForm {document_id} -> widget/inventory mismatch "
                f"(missing={len(missing)}, extra={len(extra)})"
            )
    return errors


@lru_cache(maxsize=256)
def _enumerate_pdf_widgets_isolated(pdf_path_text: str, size: int, mtime_ns: int) -> set[str]:
    """Inspect a PDF in a child process so validate stays runtime-light."""
    del size, mtime_ns
    pdf_path = Path(pdf_path_text)
    script = (
        "import fitz,json,sys; names=[]; "
        "doc=fitz.open(sys.argv[1]); "
        "[names.extend(str(w.field_name) for w in (p.widgets() or ()) if w.field_name) for p in doc]; "
        "doc.close(); print(json.dumps(names))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script, str(pdf_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        names = json.loads(completed.stdout)
        if len(names) != len(set(names)):
            raise ValueError(f"PDF contains duplicate terminal widget names: {pdf_path.name}")
        return set(names)
    cached_grid = pdf_path.with_suffix(".fields.json")
    if cached_grid.is_file():
        payload = json.loads(cached_grid.read_text(encoding="utf-8"))
        return {str(item["field_name"]) for item in payload.get("fields", [])}
    return set()


def enumerate_pdf_widgets(pdf_path: str | Path) -> set[str]:
    """Return the exact terminal AcroForm widget-name set from one PDF."""
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - exercised by minimal installs.
        raise RuntimeError("PyMuPDF is required for AcroForm widget preflight") from exc
    names: list[str] = []
    with fitz.open(str(pdf_path)) as document:
        for page in document:
            names.extend(
                str(widget.field_name)
                for widget in (page.widgets() or ())
                if widget.field_name
            )
    if len(names) != len(set(names)):
        duplicates = sorted({name for name in names if names.count(name) > 1})
        raise ValueError(f"PDF contains duplicate terminal widget names: {', '.join(duplicates[:5])}")
    return set(names)


def migrate_field_dispositions(
    year: str | int,
    root: str | Path,
    *,
    output_path: str | Path | None = None,
) -> FieldDispositionMigrationResult:
    """Build a deterministic authored-work list without guessing field policy.

    Existing identity mappings are provably user-entered. Existing graph-node
    mappings are provably graph-backed, but their exact operation is left for
    authors unless it is explicit in the legacy slot metadata. Frontier and
    otherwise-unclassified controls always remain authored work because the
    legacy records do not carry the consequence and capability fields required
    by the v2 contract.
    """
    root_path = Path(root)
    reports: list[FieldDispositionMigration] = []
    for field_map in load_field_maps(year, root_path):
        inventory = inventory_by_name(field_map, root_path)
        mapping_by_field = {item["field_name"]: item for item in field_map.get("mappings", [])}
        frontier_by_field = {item["field_name"]: item for item in field_map.get("frontier_fields", [])}
        proposed: list[dict[str, Any]] = []
        authored: list[dict[str, Any]] = []
        for field_name in sorted(inventory):
            field = inventory[field_name]
            mapping = mapping_by_field.get(field_name)
            if mapping and mapping.get("identity_slot"):
                proposed.append(
                    {
                        "field_name": field_name,
                        "label": _label_from_slot(str(mapping["slot"])),
                        "population_policy": "user_entered",
                        "value_format": _legacy_value_format(mapping, field),
                        "identity_slot": str(mapping["identity_slot"]),
                    }
                )
                continue
            reason = "unclassified legacy inventory field"
            if mapping and mapping.get("node_id"):
                reason = f"graph-backed mapping requires authored operation policy for {mapping['node_id']}"
            elif field_name in frontier_by_field:
                reason = f"frontier record requires authored consequence and missing capability: {frontier_by_field[field_name]['note']}"
            authored.append(
                {
                    "field_name": field_name,
                    "field_type": str(field.get("field_type", "Unknown")),
                    "page": int(field.get("page", 0)),
                    "reason": reason,
                }
            )
        reports.append(
            FieldDispositionMigration(
                document_id=str(field_map["document_id"]),
                proposed_dispositions=tuple(proposed),
                authored_work=tuple(authored),
            )
        )
    target = Path(output_path) if output_path is not None else root_path / "graph" / str(year) / "field_disposition_worklist.yaml"
    payload = {
        "schema_version": 1,
        "tax_year": int(year),
        "documents": [
            {
                "document_id": report.document_id,
                "proposed_dispositions": list(report.proposed_dispositions),
                "authored_work": list(report.authored_work),
            }
            for report in reports
        ],
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8", newline="\n")
    return FieldDispositionMigrationResult(documents=tuple(reports), output_path=target)


def _validate_dispositions(
    field_map: Mapping[str, Any],
    *,
    fields: set[str],
    known_nodes: set[str],
    known_frontier: set[str],
) -> list[str]:
    document_id = str(field_map.get("document_id", "<unknown>"))
    errors: list[str] = []
    dispositions = field_map.get("field_dispositions", [])
    names = [str(item.get("field_name", "")) for item in dispositions]
    disposition_fields = set(names)
    for duplicate in sorted({name for name in names if names.count(name) > 1}):
        errors.append(f"field map {document_id} -> duplicate field disposition: {duplicate}")
    for missing in sorted(fields - disposition_fields):
        errors.append(f"field map {document_id} -> field has no disposition: {missing}")
    for unknown in sorted(disposition_fields - fields):
        errors.append(f"field map {document_id} -> disposition references unknown field: {unknown}")

    disposition_by_field = {str(item.get("field_name")): item for item in dispositions}
    for mapping in field_map.get("mappings", []):
        disposition = disposition_by_field.get(str(mapping["field_name"]))
        if disposition is None:
            continue
        for ref in ("node_id", "identity_slot"):
            if mapping.get(ref) and disposition.get(ref) != mapping.get(ref):
                errors.append(
                    f"field map {document_id} -> disposition disagrees with mapping {mapping['field_name']} {ref}"
                )
    for frontier in field_map.get("frontier_fields", []):
        disposition = disposition_by_field.get(str(frontier["field_name"]))
        if disposition and disposition.get("population_policy") != "unsupported":
            errors.append(
                f"field map {document_id} -> frontier field must be unsupported: {frontier['field_name']}"
            )
    for disposition in dispositions:
        node_id = disposition.get("node_id")
        if node_id and node_id not in known_nodes:
            errors.append(f"field map {document_id} -> disposition references unknown node {node_id}")

    generic = "not mapped in the supported output profile"
    for excluded in field_map.get("excluded_nodes", []):
        if generic in str(excluded.get("reason", "")).lower():
            matching = [item for item in dispositions if item.get("node_id") == excluded.get("node_id")]
            if matching:
                errors.append(
                    f"field map {document_id} -> printable node has generic exclusion despite a field disposition: {excluded['node_id']}"
                )
    return errors


def _label_from_slot(slot: str) -> str:
    return " ".join(part for part in slot.replace("-", "_").split("_") if part).capitalize()


def _legacy_value_format(mapping: Mapping[str, Any], field: Mapping[str, Any]) -> str:
    legacy = str(mapping.get("format", ""))
    if legacy in {"dollars", "text", "checkbox"}:
        return legacy
    field_type = str(field.get("field_type", "")).lower()
    return "checkbox" if "check" in field_type or "button" in field_type else "text"


def inventory_by_name(field_map: Mapping[str, Any], root: str | Path) -> dict[str, dict[str, Any]]:
    """Return one field map's inventory indexed by AcroForm field name."""
    inventory = json.loads((Path(root) / str(field_map["inventory"])).read_text(encoding="utf-8"))
    return {item["field_name"]: item for item in inventory.get("fields", [])}
