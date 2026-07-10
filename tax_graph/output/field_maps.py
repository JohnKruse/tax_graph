"""Load and validate AcroForm inventories and node-to-field maps."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml


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
) -> list[str]:
    """Validate schemas and both sides of every authored field mapping."""
    root_path = Path(root)
    schema = json.loads((root_path / "schemas" / "field_map.schema.json").read_text(encoding="utf-8"))
    known_nodes = set(node_ids)
    known_frontier = set(frontier_ids)
    errors: list[str] = []
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
        fields = {item["field_name"] for item in inventory.get("fields", [])}
        mapped_fields: set[str] = set()
        mapped_nodes: set[str] = set()
        excluded_nodes = {item["node_id"] for item in field_map.get("excluded_nodes", [])}
        for mapping in field_map.get("mappings", []):
            field_name = mapping["field_name"]
            if field_name not in fields:
                errors.append(f"field map {document_id} -> unknown AcroForm field {field_name}")
            if field_name in mapped_fields:
                errors.append(f"field map {document_id} -> field mapped more than once: {field_name}")
            mapped_fields.add(field_name)
            node_id = mapping.get("node_id")
            if node_id:
                if node_id not in known_nodes:
                    errors.append(f"field map {document_id} -> unknown node {node_id}")
                mapped_nodes.add(node_id)
        for node_id in excluded_nodes:
            if node_id not in known_nodes:
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
    return errors


def inventory_by_name(field_map: Mapping[str, Any], root: str | Path) -> dict[str, dict[str, Any]]:
    """Return one field map's inventory indexed by AcroForm field name."""
    inventory = json.loads((Path(root) / str(field_map["inventory"])).read_text(encoding="utf-8"))
    return {item["field_name"]: item for item in inventory.get("fields", [])}
