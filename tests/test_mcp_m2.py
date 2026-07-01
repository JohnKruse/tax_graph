from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
from typing import Any
from pathlib import Path

import pytest

from tax_graph.compile import build_sqlite
from tax_graph.mcp import M2_TOOL_NAMES, build_mcp_server


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m2
def test_mcp_server_advertises_m2_tools():
    server = build_mcp_server(year="2025", root=ROOT, source="yaml")

    tools = asyncio.run(server.list_tools())

    assert tuple(sorted(tool.name for tool in tools)) == tuple(sorted(M2_TOOL_NAMES))


@pytest.mark.m2
def test_mcp_server_construction_is_runtime_light():
    script = """
import json
import sys
from tax_graph.mcp import build_mcp_server

server = build_mcp_server(year="2025", source="yaml")
loaded = [name for name in ("fitz", "mistralai") if name in sys.modules]
tools = sorted(tool.name for tool in __import__("asyncio").run(server.list_tools()))
print(json.dumps({"loaded": loaded, "tools": tools}))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["loaded"] == []
    assert payload["tools"] == sorted(M2_TOOL_NAMES)


@pytest.mark.m2
def test_read_only_tools_return_graph_objects_and_instance_addresses():
    server = build_mcp_server(year="2025", root=ROOT, source="yaml")

    document = _call_tool(server, "get_document", {"document_id": "form_8949_2025"})
    node = _call_tool(server, "get_node", {"node_id": "form_8949_2025_partii_gain_loss#broker_1"})

    assert document["document"]["title"] == "Form 8949"
    assert node["base_node_id"] == "form_8949_2025_partii_gain_loss"
    assert node["row_key"] == "broker_1"
    assert node["found"] is True
    assert "Runtime row instances" in node["instance_note"]


@pytest.mark.m2
def test_read_only_dependency_tools_walk_capital_gains_slice():
    server = build_mcp_server(year="2025", root=ROOT, source="yaml")

    dependencies = _call_tool(server, "get_dependencies", {"node_id": "schedule_d_2025_line_16_total"})
    downstream = _call_tool(
        server,
        "get_downstream_effects",
        {"node_id": "form_8949_2025_partii_total_gain_loss"},
    )

    assert {edge["source"] for edge in dependencies["dependencies"]} == {
        "schedule_d_2025_line_7_net_st",
        "schedule_d_2025_line_15_net_lt",
    }
    assert "form_1040_2025_line_7_capital_gain_loss" in downstream["reachable_node_ids"]


@pytest.mark.m2
def test_get_citation_by_id_and_fts_query(tmp_path):
    root = _copy_graph_project(tmp_path)
    build_sqlite("2025", root=root)
    server = build_mcp_server(year="2025", root=root, source="sqlite")

    citation = _call_tool(server, "get_citation", {"citation_id": "cite_8949_col_h_gain"})
    search = _call_tool(server, "get_citation", {"query": "Subtract"})

    assert "Subtract column" in citation["citation"]["quoted_text"]
    assert [match["citation_id"] for match in search["matches"]][:1] == ["cite_8949_col_h_gain"]


def _call_tool(server, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    _content, structured = asyncio.run(server.call_tool(name, arguments))
    return structured


def _copy_graph_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "graph", root / "graph", ignore=shutil.ignore_patterns("_drafts"))
    (root / "config").mkdir()
    (root / "config" / "tax-graph.config.yaml").write_text(
        "project:\n  paths:\n    build_dir: compiled\n",
        encoding="utf-8",
    )
    return root
