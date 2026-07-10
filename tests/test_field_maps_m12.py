"""M12 AcroForm inventory and field-map validation tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from tax_graph.io.loader import load_graph
from tax_graph.output.field_maps import load_field_maps, validate_field_maps


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m12
def test_committed_field_maps_validate_both_directions() -> None:
    graph = load_graph("2025", ROOT)
    frontier = yaml.safe_load((ROOT / "graph/2025/frontier.yaml").read_text(encoding="utf-8"))
    errors = validate_field_maps(
        "2025",
        ROOT,
        node_ids=(node["node_id"] for node in graph.items("nodes")),
        frontier_ids=(entry["frontier_id"] for entry in frontier["frontiers"]),
    )
    assert errors == []
    maps = load_field_maps("2025", ROOT)
    assert {item["document_id"] for item in maps} >= {"form_1040_2025", "form_8949_2025", "schedule_d_2025"}


@pytest.mark.m12
def test_inventories_record_type_page_and_rect() -> None:
    inventory = json.loads((ROOT / "graph/2025/field_inventories/form_1040_2025.json").read_text())
    line_16 = next(item for item in inventory["fields"] if item["field_name"].endswith("f2_08[0]"))
    assert line_16["field_type"] == "Text"
    assert line_16["page"] == 2
    assert line_16["x1"] > line_16["x0"]
    assert line_16["y1"] > line_16["y0"]


@pytest.mark.m12
def test_broken_field_and_node_are_rejected(tmp_path: Path) -> None:
    graph_dir = tmp_path / "graph/2025/field_maps"
    inventory_dir = tmp_path / "graph/2025/field_inventories"
    schema_dir = tmp_path / "schemas"
    graph_dir.mkdir(parents=True)
    inventory_dir.mkdir(parents=True)
    schema_dir.mkdir()
    (schema_dir / "field_map.schema.json").write_text((ROOT / "schemas/field_map.schema.json").read_text())
    source = next(item for item in load_field_maps("2025", ROOT) if item["document_id"] == "form_1040_2025")
    broken = copy.deepcopy(source)
    broken["inventory"] = "graph/2025/field_inventories/form_1040_2025.json"
    broken["mappings"][0]["field_name"] = "missing_acroform_field"
    node_mapping = next(item for item in broken["mappings"] if "node_id" in item)
    node_mapping["node_id"] = "missing_graph_node"
    (graph_dir / "form_1040_2025.yaml").write_text(yaml.safe_dump(broken, sort_keys=False))
    (inventory_dir / "form_1040_2025.json").write_text(
        (ROOT / "graph/2025/field_inventories/form_1040_2025.json").read_text()
    )
    errors = validate_field_maps("2025", tmp_path, node_ids=set(), frontier_ids=set())
    assert any("unknown AcroForm field" in error for error in errors)
    assert any("unknown node missing_graph_node" in error for error in errors)
