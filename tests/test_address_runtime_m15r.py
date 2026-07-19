from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from tax_graph.io.loader import load_yaml
from tax_graph.mcp import build_mcp_server
from tax_graph.output.session import used_form_ids


ROOT = Path(__file__).resolve().parents[1]


def _call(server, name, arguments):
    _content, structured = asyncio.run(server.call_tool(name, arguments))
    return structured


@pytest.mark.m15r
def test_mcp_resolves_and_lists_canonical_addresses_without_breaking_node_tools() -> None:
    server = build_mcp_server(year="2025", root=ROOT, source="yaml")
    address_id = "2025/document=form_1040/line=1a/control=amount"
    resolved = _call(server, "resolve_address", {"address_id": address_id})
    listed = _call(server, "list_addresses", {"document_id": "form_1040_2025"})
    node = _call(server, "get_node", {"node_id": "form_1040_2025_root_line_1a"})
    assert resolved["state"] == "exact" and resolved["address"]["address_id"] == address_id
    assert listed["count"] == 249
    assert node["found"] is True


@pytest.mark.m15r
def test_used_forms_follow_graph_ownership_not_node_prefixes() -> None:
    facts = load_yaml(ROOT / "examples/capital_gains_multi_lot/facts.yaml")
    forms = used_form_ids(facts, project_root=ROOT, year=2025)
    assert {"form_1040_2025", "form_8949_2025", "schedule_d_2025"} <= set(forms)
    hostile = {"facts": [{"node_id": "not_a_document_prefix"}]}
    assert used_form_ids(hostile, project_root=ROOT, year=2025) == ("form_1040_2025",)
