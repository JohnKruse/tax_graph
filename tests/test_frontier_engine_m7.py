from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from tax_graph.engine import Engine, Graph, MISSING, load_facts


ROOT = Path(__file__).resolve().parents[1]


def _copy_frontier_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "graph", root / "graph")
    shutil.copytree(ROOT / "schemas", root / "schemas")
    shutil.copytree(ROOT / "config", root / "config")
    shutil.copytree(ROOT / "data", root / "data")
    return root


def _read_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, value) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


@pytest.mark.m7
def test_engine_emits_unresolved_trace_for_frontier_upstream(tmp_path):
    root = _copy_frontier_root(tmp_path)
    edges_file = root / "graph" / "2025" / "edges" / "capital-gains.yaml"
    edges = _read_yaml(edges_file)
    edges.append(
        {
            "edge_id": "e_frontier_sd_9_to_15",
            "source": "schedule_d_2025_line_9_frontier",
            "target": "schedule_d_2025_line_15_net_lt",
            "relationship": "CALCULATES",
            "rule_id": "sum_currency",
            "role": "addend",
        }
    )
    _write_yaml(edges_file, edges)
    frontier = _read_yaml(root / "graph" / "2025" / "frontier.yaml")
    frontier["frontiers"].append(
        {
            "frontier_id": "flow_test_schedule_d_line_9",
            "kind": "outbound_flow",
            "source": {"document_id": "form_8949_2025"},
            "target": {"document_id": "schedule_d_2025", "line": "9"},
            "target_url": "https://www.irs.gov/pub/irs-pdf/f1040sd.pdf",
            "citation_ref": "cite_8949_line2_totals",
            "status": "declared",
            "weight": 24000000,
        }
    )
    _write_yaml(root / "graph" / "2025" / "frontier.yaml", frontier)

    result = Engine(Graph("2025", root=root, source="yaml")).execute(
        load_facts(ROOT / "examples" / "capital_gains_basic" / "facts.yaml")
    )

    assert result.values["schedule_d_2025_line_15_net_lt"] is MISSING
    trace = result.trace["schedule_d_2025_line_15_net_lt"]
    assert trace["kind"] == "unresolved"
    assert trace["frontier_id"] == "flow_test_schedule_d_line_9"
    assert trace["target_url"] == "https://www.irs.gov/pub/irs-pdf/f1040sd.pdf"
    assert trace["citation_ref"] == "cite_8949_line2_totals"
    assert "not yet modeled" in trace["note"]


@pytest.mark.m7
def test_engine_fully_modeled_chain_still_computes():
    result = Engine(Graph("2025", root=ROOT, source="yaml")).execute(
        load_facts(ROOT / "examples" / "capital_gains_basic" / "facts.yaml")
    )

    assert result.values["form_1040_2025_line_7_capital_gain_loss"] == 2000
