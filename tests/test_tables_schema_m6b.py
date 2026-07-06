from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from tax_graph.io.loader import load_graph
from tax_graph.validate import validate_graph, validate_taxpayer_facts_document


ROOT = Path(__file__).resolve().parents[1]
TABLE_ID = "form_8949_2025_part_ii_line_1"
COST_NODE = "form_8949_2025_part_ii_line_1_column_e"


def _copy_graph_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "graph", root / "graph", ignore=shutil.ignore_patterns("_drafts"))
    shutil.copytree(ROOT / "schemas", root / "schemas")
    return root


def _read_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, value) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _table_by_id(tables: list[dict], table_id: str) -> dict:
    return next(table for table in tables if table["table_id"] == table_id)


def _install_valid_table(root: Path) -> None:
    return None


@pytest.mark.m6b
def test_valid_table_definition_validates(tmp_path):
    root = _copy_graph_root(tmp_path)
    _install_valid_table(root)

    result = validate_graph("2025", root=root)

    assert result.ok, result.errors
    assert result.counts["tables"] == 2


@pytest.mark.m6b
def test_table_validation_fails_on_missing_template_node(tmp_path):
    root = _copy_graph_root(tmp_path)
    _install_valid_table(root)
    table_file = root / "graph" / "2025" / "tables" / "form-8949.yaml"
    tables = _read_yaml(table_file)
    _table_by_id(tables, TABLE_ID)["columns"][0]["template_node"] = "missing_node"
    _write_yaml(table_file, tables)

    result = validate_graph("2025", root=root)

    assert not result.ok
    assert any(f"table {TABLE_ID} column d -> missing node missing_node" in error for error in result.errors)


@pytest.mark.m6b
def test_table_validation_fails_on_inconsistent_member_metadata(tmp_path):
    root = _copy_graph_root(tmp_path)
    _install_valid_table(root)
    nodes_file = root / "graph" / "2025" / "nodes" / "capital-gains.yaml"
    nodes = _read_yaml(nodes_file)
    for node in nodes:
        if node["node_id"] == COST_NODE:
            node["column"] = "x"
    _write_yaml(nodes_file, nodes)

    result = validate_graph("2025", root=root)

    assert not result.ok
    assert any(f"node {COST_NODE} has column x" in error for error in result.errors)


@pytest.mark.m6b
def test_table_validation_fails_when_total_column_is_not_a_row_column(tmp_path):
    root = _copy_graph_root(tmp_path)
    _install_valid_table(root)
    table_file = root / "graph" / "2025" / "tables" / "form-8949.yaml"
    tables = _read_yaml(table_file)
    _table_by_id(tables, TABLE_ID)["totals"][0]["column_id"] = "z"
    _write_yaml(table_file, tables)

    result = validate_graph("2025", root=root)

    assert not result.ok
    assert any(f"table {TABLE_ID} total z -> total column is not a row column" in error for error in result.errors)


@pytest.mark.m6b
def test_table_facts_validate_against_input_columns(tmp_path):
    root = _copy_graph_root(tmp_path)
    _install_valid_table(root)
    graph = load_graph("2025", root=root)
    facts = {
        "tax_year": 2025,
        "facts": [],
        "tables": [
            {
                "table_id": TABLE_ID,
                "rows": [
                    {
                        "row_key": "lot_1",
                        "columns": {"d": 12000, "e": 10000},
                    }
                ],
            }
        ],
    }

    errors = validate_taxpayer_facts_document(facts, graph)

    assert errors == []


@pytest.mark.m6b
def test_table_facts_reject_unknown_and_computed_columns(tmp_path):
    root = _copy_graph_root(tmp_path)
    _install_valid_table(root)
    graph = load_graph("2025", root=root)
    facts = {
        "tax_year": 2025,
        "facts": [],
        "tables": [
            {
                "table_id": TABLE_ID,
                "rows": [
                    {
                        "row_key": "lot_1",
                        "columns": {"d": 12000, "h": 2000, "x": 1},
                    }
                ],
            }
        ],
    }

    errors = validate_taxpayer_facts_document(facts, graph)

    assert any("column h -> computed columns cannot be supplied" in error for error in errors)
    assert any("column x -> unknown input column" in error for error in errors)


@pytest.mark.m6b
def test_table_facts_reject_duplicate_row_keys_per_table(tmp_path):
    root = _copy_graph_root(tmp_path)
    _install_valid_table(root)
    graph = load_graph("2025", root=root)
    facts = {
        "tax_year": 2025,
        "facts": [],
        "tables": [
            {
                "table_id": TABLE_ID,
                "rows": [
                    {"row_key": "lot_1", "columns": {"d": 12000}},
                    {"row_key": "lot_1", "columns": {"e": 10000}},
                ],
            }
        ],
    }

    errors = validate_taxpayer_facts_document(facts, graph)

    assert any("row lot_1 -> duplicate row_key within table" in error for error in errors)
