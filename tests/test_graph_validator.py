from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from tax_graph.io.loader import load_yaml
from tax_graph.validate.graph_validator import validate_graph


ROOT = Path(__file__).resolve().parents[1]


def _copy_graph_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "graph", root / "graph")
    shutil.copytree(ROOT / "schemas", root / "schemas")
    return root


def _read_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, value) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


@pytest.mark.m0
def test_loader_normalizes_yaml_dates(tmp_path):
    path = tmp_path / "date.yaml"
    path.write_text("retrieved_date: 2026-06-28\n", encoding="utf-8")

    assert load_yaml(path) == {"retrieved_date": "2026-06-28"}


@pytest.mark.m0
def test_current_2025_graph_validates():
    result = validate_graph("2025", root=ROOT)

    assert result.ok, result.errors


@pytest.mark.m0
def test_validator_catches_duplicate_ids(tmp_path):
    root = _copy_graph_root(tmp_path)
    nodes_file = root / "graph" / "2025" / "nodes" / "capital-gains.yaml"
    nodes = _read_yaml(nodes_file)
    nodes.append(dict(nodes[0]))
    _write_yaml(nodes_file, nodes)

    result = validate_graph("2025", root=root)

    assert not result.ok
    assert any("duplicate node_id form_8949_2025_part_i_line_1_column_d" in error for error in result.errors)


@pytest.mark.m0
def test_validator_catches_dependency_cycles(tmp_path):
    root = _copy_graph_root(tmp_path)
    edges_file = root / "graph" / "2025" / "edges" / "capital-gains.yaml"
    edges = _read_yaml(edges_file)
    edges.append(
        {
            "edge_id": "e_1040_7_back_to_sd_7",
            "source": "form_1040_2025_line_7_capital_gain_loss",
            "target": "schedule_d_2025_line_7_net_st",
            "relationship": "FEEDS",
            "rule_id": "copy_currency_value",
        }
    )
    _write_yaml(edges_file, edges)

    result = validate_graph("2025", root=root)

    assert not result.ok
    assert any("dependency cycle detected" in error for error in result.errors)


@pytest.mark.m0
def test_validator_catches_cross_year_documents(tmp_path):
    root = _copy_graph_root(tmp_path)
    document_file = root / "graph" / "2025" / "documents" / "form-1040.yaml"
    document = _read_yaml(document_file)
    document["tax_year"] = 2024
    _write_yaml(document_file, document)

    result = validate_graph("2025", root=root)

    assert not result.ok
    assert any("tax_year 2024 does not match graph 2025" in error for error in result.errors)
