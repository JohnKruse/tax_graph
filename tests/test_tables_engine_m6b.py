from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from tax_graph.engine import Engine, Graph, MISSING, load_facts, render_trace
from tax_graph.mcp import build_mcp_server
from tax_graph.validate import validate_graph


ROOT = Path(__file__).resolve().parents[1]
TABLE_ID = "form_8949_2025_part_ii_line_1"
TARGET = "form_1040_2025_line_7_capital_gain_loss"
GAIN_NODE = "form_8949_2025_part_ii_line_1_column_h"
TOTAL_NODE = "form_8949_2025_part_ii_line_2_line_2_column_h_total"
ADJUSTMENT_NODE = "form_8949_2025_part_ii_line_1_column_g"
INTERMEDIATE_NODE = "form_8949_2025_part_ii_line_1_column_d_minus_e"


def _copy_graph_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "graph", root / "graph", ignore=shutil.ignore_patterns("_drafts"))
    shutil.copytree(ROOT / "schemas", root / "schemas")
    return root


def _read_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, value) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _install_table_graph(root: Path) -> None:
    return None


def _facts_document(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "tax_year": 2025,
        "filing_status": "single",
        "facts": [
            {"node_id": "schedule_d_2025_line_7_net_st", "value": 0},
        ],
        "tables": [{"table_id": TABLE_ID, "rows": rows}],
    }


def _facts_file(tmp_path: Path, rows: list[dict[str, Any]]) -> Path:
    path = tmp_path / "facts.yaml"
    _write_yaml(path, _facts_document(rows))
    return path


def _three_rows() -> list[dict[str, Any]]:
    return [
        {"row_key": "lot_gain", "columns": {"d": 12000, "e": 10000, "g": 0}},
        {"row_key": "lot_loss", "columns": {"d": 5000, "e": 7000, "g": 0}},
        {"row_key": "lot_adjusted", "columns": {"d": 1000, "e": 800, "g": 50}},
    ]


@pytest.mark.m6b
def test_engine_computes_table_rows_totals_and_instance_trace(tmp_path):
    root = _copy_graph_project(tmp_path)
    _install_table_graph(root)
    assert validate_graph("2025", root=root).ok
    graph = Graph("2025", root=root, source="yaml")

    result = Engine(graph).execute(load_facts(_facts_file(tmp_path, _three_rows())))

    assert result.values[f"{GAIN_NODE}#lot_gain"] == 2000
    assert result.values[f"{GAIN_NODE}#lot_loss"] == -2000
    assert result.values[f"{GAIN_NODE}#lot_adjusted"] == 250
    assert result.values[TOTAL_NODE] == 250
    assert result.values[TARGET] == 250
    total_trace = result.trace[TOTAL_NODE]
    assert total_trace["kind"] == "table_total"
    assert total_trace["instances"] == [
        f"{GAIN_NODE}#lot_gain",
        f"{GAIN_NODE}#lot_loss",
        f"{GAIN_NODE}#lot_adjusted",
    ]
    adjusted_trace = result.trace[f"{GAIN_NODE}#lot_adjusted"]
    assert adjusted_trace["operation"] == "SUM"
    assert {operand["node"] for operand in adjusted_trace["inputs"]} == {
        f"{INTERMEDIATE_NODE}#lot_adjusted",
        f"{ADJUSTMENT_NODE}#lot_adjusted",
    }


@pytest.mark.m6b
def test_engine_reports_missing_required_table_input_per_instance(tmp_path):
    root = _copy_graph_project(tmp_path)
    _install_table_graph(root)
    graph = Graph("2025", root=root, source="yaml")
    rows = [{"row_key": "lot_missing", "columns": {"e": 10000, "g": 0}}]
    facts = load_facts(_facts_file(tmp_path, rows))

    result = Engine(graph).execute(facts)

    missing_id = "form_8949_2025_part_ii_line_1_column_d#lot_missing"
    assert result.values[missing_id] is MISSING
    assert result.values[TOTAL_NODE] is MISSING
    assert result.values[TARGET] is MISSING
    assert missing_id in result.missing_required_inputs
    assert Engine(graph).list_required_inputs(facts) == [missing_id]


@pytest.mark.m6b
def test_zero_table_rows_total_to_zero_with_trace_note(tmp_path, capsys):
    root = _copy_graph_project(tmp_path)
    _install_table_graph(root)
    graph = Graph("2025", root=root, source="yaml")

    result = Engine(graph).execute(load_facts(_facts_file(tmp_path, [])))

    assert result.values[TOTAL_NODE] == 0
    assert result.values[TARGET] == 0
    assert result.trace[TOTAL_NODE]["note"] == "no instances supplied"
    render_trace(TOTAL_NODE, result, graph)
    assert "no instances supplied" in capsys.readouterr().out


@pytest.mark.m6b
def test_mcp_explain_calculation_returns_instance_trace(tmp_path):
    root = _copy_graph_project(tmp_path)
    _install_table_graph(root)
    server = build_mcp_server(year="2025", root=root, source="yaml")
    facts = _facts_document(_three_rows())

    result = _call_tool(
        server,
        "explain_calculation",
        {"node_id": f"{GAIN_NODE}#lot_adjusted", "facts": facts},
    )

    assert result["base_node_id"] == GAIN_NODE
    assert result["row_key"] == "lot_adjusted"
    assert result["trace"]["value"] == 250
    assert result["trace"]["operation"] == "SUM"
    assert {operand["node"] for operand in result["trace"]["inputs"]} == {
        f"{INTERMEDIATE_NODE}#lot_adjusted",
        f"{ADJUSTMENT_NODE}#lot_adjusted",
    }


def _call_tool(server, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    _content, structured = asyncio.run(server.call_tool(name, arguments))
    return structured
