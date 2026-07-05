from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest
import yaml

from tax_graph.compile import build_sqlite
from tax_graph.engine import Engine, Graph, load_facts


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "capital_gains_basic"
TABLE_ID = "form_8949_2025_partii_line_1"


def _copy_graph_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "graph", root / "graph", ignore=shutil.ignore_patterns("_drafts"))
    shutil.copytree(ROOT / "schemas", root / "schemas")
    (root / "config").mkdir()
    (root / "config" / "tax-graph.config.yaml").write_text(
        "project:\n  paths:\n    build_dir: compiled\n",
        encoding="utf-8",
    )
    return root


def _read_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, value) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _install_valid_table(root: Path) -> None:
    nodes_file = root / "graph" / "2025" / "nodes" / "capital-gains.yaml"
    nodes = _read_yaml(nodes_file)
    marks = {
        "form_8949_2025_partii_proceeds": ("d", "row_template"),
        "form_8949_2025_partii_cost": ("e", "row_template"),
        "form_8949_2025_partii_gain_loss": ("h", "row_template"),
        "form_8949_2025_partii_total_gain_loss": ("h", "total"),
    }
    for node in nodes:
        if node["node_id"] in marks:
            node["table_id"] = TABLE_ID
            node["column"] = marks[node["node_id"]][0]
            node["role"] = marks[node["node_id"]][1]
    _write_yaml(nodes_file, nodes)

    tables_dir = root / "graph" / "2025" / "tables"
    tables_dir.mkdir()
    _write_yaml(
        tables_dir / "form-8949.yaml",
        [
            {
                "table_id": TABLE_ID,
                "document_id": "form_8949_2025",
                "line_anchor": "Form 8949 Part II line 1",
                "columns": [
                    {
                        "column_id": "d",
                        "label": "Proceeds",
                        "kind": "input",
                        "template_node": "form_8949_2025_partii_proceeds",
                    },
                    {
                        "column_id": "e",
                        "label": "Cost or other basis",
                        "kind": "input",
                        "template_node": "form_8949_2025_partii_cost",
                    },
                    {
                        "column_id": "h",
                        "label": "Gain or loss",
                        "kind": "computed",
                        "template_node": "form_8949_2025_partii_gain_loss",
                    },
                ],
                "totals": [
                    {
                        "column_id": "h",
                        "total_node": "form_8949_2025_partii_total_gain_loss",
                    }
                ],
                "citation_refs": ["cite_8949_col_h_gain"],
            }
        ],
    )


@pytest.mark.m6b
def test_sqlite_round_trips_table_subunit_and_preserves_execution_parity(tmp_path):
    root = _copy_graph_project(tmp_path)
    _install_valid_table(root)

    build = build_sqlite("2025", root=root)
    facts = load_facts(EXAMPLE / "facts.yaml")
    yaml_graph = Graph("2025", root=root, source="yaml")
    sqlite_graph = Graph("2025", root=root, source="sqlite")
    yaml_result = Engine(yaml_graph).execute(facts)
    sqlite_result = Engine(sqlite_graph).execute(facts)

    with sqlite3.connect(build.path) as conn:
        table_count = conn.execute("SELECT COUNT(*) FROM tables").fetchone()[0]

    assert table_count == 1
    assert sqlite_graph.tables == yaml_graph.tables
    assert sqlite_graph.tables[TABLE_ID]["columns"][0]["template_node"] == "form_8949_2025_partii_proceeds"
    assert sqlite_result.values == yaml_result.values
    assert sqlite_result.trace == yaml_result.trace
