"""Build and query the node-to-official-page geometry projection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tax_graph.output.field_maps import inventory_by_name, load_field_maps


def build_node_geometry(year: str | int, root: str | Path) -> dict[str, Any]:
    """Derive stable geometry entries from inventories and field maps."""
    entries: list[dict[str, Any]] = []
    for field_map in load_field_maps(year, root):
        inventory = inventory_by_name(field_map, root)
        for mapping in field_map.get("mappings", []):
            field = inventory[mapping["field_name"]]
            entry = {
                "document_id": field_map["document_id"],
                "slot": mapping["slot"],
                "field_name": mapping["field_name"],
                "page": field["page"],
                "rect": [field["x0"], field["y0"], field["x1"], field["y1"]],
            }
            if "node_id" in mapping:
                entry["node_id"] = mapping["node_id"]
            else:
                entry["identity_slot"] = mapping["identity_slot"]
            entries.append(entry)
    entries.sort(key=lambda item: (item["document_id"], item["page"], item["field_name"], item["slot"]))
    return {"tax_year": int(year), "entries": entries}


def write_node_geometry(year: str | int, root: str | Path) -> Path:
    """Write the committed geometry projection for a tax year."""
    path = Path(root) / "graph" / str(year) / "node_geometry.json"
    path.write_text(
        json.dumps(build_node_geometry(year, root), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def load_node_geometry(year: str | int, root: str | Path) -> dict[str, Any]:
    """Load the committed geometry projection."""
    path = Path(root) / "graph" / str(year) / "node_geometry.json"
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_node_geometry(node_id: str, *, year: str | int, root: str | Path) -> list[dict[str, Any]]:
    """Return every physical official-form location for a static node."""
    return [entry for entry in load_node_geometry(year, root)["entries"] if entry.get("node_id") == node_id]


def validate_node_geometry(year: str | int, root: str | Path) -> list[str]:
    """Validate schema and exact reproducibility from the authored field maps."""
    root_path = Path(root)
    path = root_path / "graph" / str(year) / "node_geometry.json"
    if not path.exists():
        return [f"node geometry {year} -> missing {path.relative_to(root_path)}"]
    committed = load_node_geometry(year, root_path)
    errors: list[str] = []
    try:
        import jsonschema

        schema = json.loads((root_path / "schemas/node_geometry.schema.json").read_text(encoding="utf-8"))
        jsonschema.validate(committed, schema)
    except jsonschema.ValidationError as exc:
        errors.append(f"node geometry {year} -> schema: {exc.message}")
    if committed != build_node_geometry(year, root_path):
        errors.append(f"node geometry {year} -> committed projection is stale")
    return errors
