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
from tax_graph.io.loader import load_yaml
from tax_graph.mcp import M2_TOOL_NAMES, MCP_TOOL_NAMES, build_mcp_server


ROOT = Path(__file__).resolve().parents[1]
FACTS_PATH = ROOT / "examples" / "capital_gains_basic" / "facts.yaml"


@pytest.mark.m2
def test_mcp_server_advertises_m2_tools():
    server = build_mcp_server(year="2025", root=ROOT, source="yaml")

    tools = asyncio.run(server.list_tools())

    assert tuple(sorted(tool.name for tool in tools)) == tuple(sorted(MCP_TOOL_NAMES))


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
    assert set(M2_TOOL_NAMES) <= set(payload["tools"])
    assert payload["tools"] == sorted(MCP_TOOL_NAMES)


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


@pytest.mark.m2
def test_server_instructions_include_behavior_contract():
    server = build_mcp_server(year="2025", root=ROOT, source="yaml")

    instructions = server.instructions

    assert "Never compute tax values yourself" in instructions
    assert "Never assert a tax rule without" in instructions
    assert "At a decision node" in instructions
    assert "Report missing inputs" in instructions


@pytest.mark.m2
def test_document_surfaces_decision_escape_hatch():
    server = build_mcp_server(year="2025", root=ROOT, source="yaml")

    document = _call_tool(server, "get_document", {"document_id": "form_8949_2025"})
    decision = document["decisions"][0]

    assert decision["question"]
    assert {option["option_type"] for option in decision["options"]} & {"other", "unsupported", "escalate"}


@pytest.mark.m2
def test_execute_tax_tree_returns_values_and_trace():
    server = build_mcp_server(year="2025", root=ROOT, source="yaml")
    facts = load_yaml(FACTS_PATH)

    result = _call_tool(server, "execute_tax_tree", {"facts": facts})

    assert result["values"]["form_1040_2025_line_7_capital_gain_loss"] == 2000
    assert result["missing_required_inputs"] == []
    assert result["trace"]["form_8949_2025_partii_gain_loss"]["operation"] == "SUBTRACT"


@pytest.mark.m2
def test_list_required_inputs_reports_missing_leaf():
    server = build_mcp_server(year="2025", root=ROOT, source="yaml")
    facts = load_yaml(FACTS_PATH)
    facts["facts"] = [
        fact
        for fact in facts["facts"]
        if fact["node_id"] != "form_1099b_2025_box_1e_cost_basis"
    ]

    result = _call_tool(server, "list_required_inputs", {"facts": facts})

    assert result["missing_required_inputs"] == ["form_1099b_2025_box_1e_cost_basis"]


@pytest.mark.m2
def test_explain_calculation_returns_rule_operands_and_citations():
    server = build_mcp_server(year="2025", root=ROOT, source="yaml")
    facts = load_yaml(FACTS_PATH)

    result = _call_tool(
        server,
        "explain_calculation",
        {"node_id": "form_8949_2025_partii_gain_loss", "facts": facts},
    )

    assert result["trace"]["operation"] == "SUBTRACT"
    assert {operand["role"] for operand in result["trace"]["inputs"]} == {"minuend", "subtrahend"}
    assert result["rule"]["rule_id"] == "subtract_currency"
    assert [citation["citation_id"] for citation in result["citations"]] == ["cite_8949_col_h_gain"]


@pytest.mark.m2
def test_export_audit_file_returns_human_readable_trace():
    server = build_mcp_server(year="2025", root=ROOT, source="yaml")
    facts = load_yaml(FACTS_PATH)

    result = _call_tool(
        server,
        "export_audit_file",
        {"target": "form_1040_2025_line_7_capital_gain_loss", "facts": facts},
    )

    assert "Form 1040, line 7" in result["audit_text"]
    assert "[SUM]" in result["audit_text"]
    assert "[SUBTRACT]" in result["audit_text"]
    assert "cite_8949_col_h_gain" in result["audit_text"]


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
