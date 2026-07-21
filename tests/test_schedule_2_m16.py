"""M16-S1 Schedule 2 Part I identity acceptance fixture."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
import yaml

from tax_graph.mcp import build_mcp_server


ROOT = Path(__file__).resolve().parents[1]
RAW_FIELDS = ROOT / ".cache/raw/2025/schedule_2_2025.fields.json"
FIELD_MAP = ROOT / "graph/2025/field_maps/schedule_2_2025.yaml"
WIDGET_BINDINGS = ROOT / "graph/2025/bindings/widgets/schedule_2_2025.yaml"
NODES = ROOT / "graph/2025/nodes/schedule-2.yaml"
CITATIONS = ROOT / "graph/2025/citations/schedule-2.yaml"


def _call_tool(server, name: str, arguments: dict[str, str]) -> dict:
    _content, structured = asyncio.run(server.call_tool(name, arguments))
    return structured


def _by_field(items: list[dict], field_name: str) -> dict:
    return next(item for item in items if item["field_name"] == field_name)


def test_schedule_2_part_i_raw_acroform_identity() -> None:
    """Lock the structure that the M16 resolver must use as its evidence."""
    raw = json.loads(RAW_FIELDS.read_text(encoding="utf-8"))["fields"]
    fields = {item["field_name"]: item for item in raw}

    checkbox_names = [
        "form1[0].Page1[0].Line4_ReadOrder[0].c1_3[0]",
        "form1[0].Page1[0].Line4_ReadOrder[0].c1_4[0]",
        "form1[0].Page1[0].Line4_ReadOrder[0].c1_5[0]",
    ]
    assert all(name in fields for name in checkbox_names)
    assert all(fields[name]["line_anchor"] == "1" for name in checkbox_names)
    assert [fields[name]["x0"] for name in checkbox_names] == [79.2, 158.4, 237.6]

    indented = fields["form1[0].Page1[0].Line4_ReadOrder[0].f1_14[0]"]
    far_right = fields["form1[0].Page1[0].f1_15[0]"]
    assert (indented["x0"], indented["x1"]) == (252.0, 324.0)
    assert (far_right["x0"], far_right["x1"]) == (504.0, 576.0)
    assert (indented["y0"], indented["y1"]) == (468.0, 480.0)
    assert (far_right["y0"], far_right["y1"]) == (468.0, 480.0)

    assert fields["form1[0].Page1[0].f1_11[0]"]["line_anchor"] == "z"
    assert fields["form1[0].Page1[0].f1_13[0]"]["line_anchor"] == "3"


@pytest.mark.xfail(
    strict=True,
    reason="M16-S1 acceptance fixture: Streams A and B must repair Schedule 2 identities and fail closed",
)
def test_schedule_2_part_i_m16_target_identities_and_fail_closed() -> None:
    """Require the Section 1 target identities and structural safety contract."""
    raw = json.loads(RAW_FIELDS.read_text(encoding="utf-8"))["fields"]
    fields = {item["field_name"]: item for item in raw}
    field_map = yaml.safe_load(FIELD_MAP.read_text(encoding="utf-8"))
    widget_map = yaml.safe_load(WIDGET_BINDINGS.read_text(encoding="utf-8"))
    nodes = yaml.safe_load(NODES.read_text(encoding="utf-8"))
    citations = yaml.safe_load(CITATIONS.read_text(encoding="utf-8"))
    node_by_id = {node["node_id"]: node for node in nodes}
    citation_by_id = {item["citation_id"]: item for item in citations}
    mapping_by_field = {item["field_name"]: item for item in field_map["mappings"]}
    widget_by_field = {item["field_name"]: item for item in widget_map["bindings"]}

    server = build_mcp_server(year="2025", root=ROOT, source="yaml")
    heading = _call_tool(server, "get_node", {"node_id": "schedule_2_2025_part_i_line_1"})
    line_1z = _call_tool(server, "get_node", {"node_id": "schedule_2_2025_part_i_line_1z"})
    assert heading["found"] is True
    assert heading["node"]["node_type"] != "form_line"
    assert heading["node"]["value_type"] != "currency"
    assert line_1z["found"] is True

    assert citation_by_id["cite_span_schedule_2_2025_0004"]["quoted_text"] == "- 1: Additions to tax:"
    assert node_by_id["schedule_2_2025_part_i_line_3"]["citation_refs"] == [
        "cite_span_schedule_2_2025_0019"
    ]

    expected_nodes = {
        "form1[0].Page1[0].f1_15[0]": "schedule_2_2025_part_ii_line_4",
        "form1[0].Page1[0].f1_13[0]": "schedule_2_2025_part_i_line_3",
        "form1[0].Page1[0].f1_11[0]": "schedule_2_2025_part_i_line_1z",
    }
    assert {field: mapping_by_field[field]["node_id"] for field in expected_nodes} == expected_nodes

    checkbox_fields = [
        "form1[0].Page1[0].Line4_ReadOrder[0].c1_3[0]",
        "form1[0].Page1[0].Line4_ReadOrder[0].c1_4[0]",
        "form1[0].Page1[0].Line4_ReadOrder[0].c1_5[0]",
    ]
    assert all(widget_by_field[field]["address_id"].endswith("line=4/control=checkbox") for field in checkbox_fields)

    printed_amount_fields = ["f1_11", "f1_12", "f1_13", "f1_15", "f1_16", "f1_17", "f1_18", "f1_19", "f1_20"]
    for suffix in printed_amount_fields:
        field_name = next(name for name in fields if name.endswith(f".{suffix}[0]"))
        mapping = mapping_by_field.get(field_name)
        dispositions = [item for item in field_map.get("dispositions", []) if item["field_name"] == field_name]
        assert mapping is not None or dispositions, f"{suffix} must resolve or be explicitly out of profile"

    expected_lines = {"f1_11": "1z", "f1_12": "2", "f1_13": "3", "f1_15": "4"}
    for suffix, line in expected_lines.items():
        field_name = next(name for name in fields if name.endswith(f".{suffix}[0]"))
        assert f"line={line}/" in mapping_by_field[field_name]["address_id"]
