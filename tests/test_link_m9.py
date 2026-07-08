from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from tax_graph.engine import Engine, Graph, load_facts
from tax_graph.frontier.build import build_frontier_registry
from tax_graph.link import link_outbound_flows


pytestmark = pytest.mark.m9

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "examples" / "capital_gains_basic" / "facts.yaml"
MULTI_FACTS = ROOT / "examples" / "capital_gains_multi_lot" / "facts.yaml"
TARGET = "form_1040_2025_line_7_capital_gain_loss"


def test_link_realizes_reviewed_8949_outbound_flows_idempotently(tmp_path):
    root = _copy_root(tmp_path)
    linked_path = root / "graph" / "2025" / "edges" / "linked-outbound.yaml"
    linked_path.unlink()

    first = link_outbound_flows("2025", root=root)
    first_text = linked_path.read_text(encoding="utf-8")
    second = link_outbound_flows("2025", root=root)

    assert first.path == linked_path
    assert len(first.realized) == 6
    assert first.unresolved == []
    assert [edge["target"] for edge in first.realized] == [
        "schedule_d_2025_part_i_line_1b_column_h",
        "schedule_d_2025_part_i_line_2_column_h",
        "schedule_d_2025_part_i_line_3_column_h",
        "schedule_d_2025_part_ii_line_10_column_h",
        "schedule_d_2025_part_ii_line_8b_column_h",
        "schedule_d_2025_part_ii_line_9_column_h",
    ]
    assert linked_path.read_text(encoding="utf-8") == first_text
    assert second.realized == first.realized


def test_frontier_flip_keeps_absent_targets_declared(tmp_path):
    root = _copy_root(tmp_path)
    flows_path = root / "graph" / "2025" / "_drafts" / "form_8949_2025" / "outbound_flows.yaml"
    flows = yaml.safe_load(flows_path.read_text(encoding="utf-8"))
    flows.append(
        {
            "flow_id": "flow_form_8949_2025_part_ii_line_2_column_h_to_schedule_d_2025_line_99",
            "source_document_id": "form_8949_2025",
            "source_outline_id": "part_ii_line_2",
            "source_node_id": "form_8949_2025_part_ii_line_2_column_h",
            "target_document_id": "schedule_d_2025",
            "target_line": "99",
            "citation_span_ids": ["span_form_8949_2025_0001"],
            "confidence": 0.8,
        }
    )
    flows_path.write_text(yaml.safe_dump(flows, sort_keys=False), encoding="utf-8")

    link_result = link_outbound_flows("2025", root=root)
    registry = build_frontier_registry("2025", root=root, write=False).registry
    outbound = [entry for entry in registry["frontiers"] if entry["kind"] == "outbound_flow"]
    by_line = {entry["target"]["line"]: entry for entry in outbound}

    assert len(link_result.realized) == 6
    assert link_result.unresolved[-1]["target_line"] == "99"
    assert by_line["1b"]["status"] == "modeled"
    assert by_line["2"]["status"] == "modeled"
    assert by_line["3"]["status"] == "modeled"
    assert by_line["8b"]["status"] == "modeled"
    assert by_line["9"]["status"] == "modeled"
    assert by_line["10"]["status"] == "modeled"
    assert by_line["99"]["status"] == "declared"
    assert "node_id" not in by_line["99"]["target"]


def test_promoted_schedule_d_links_preserve_capital_gains_parity():
    graph = Graph("2025", root=ROOT, source="yaml")

    basic = Engine(graph).execute(load_facts(FACTS))
    multi = Engine(graph).execute(load_facts(MULTI_FACTS))

    assert basic.values["schedule_d_2025_part_ii_line_8b_column_h"] == 2000
    assert basic.values["schedule_d_2025_line_15_net_lt"] == 2000
    assert basic.values[TARGET] == 2000
    assert multi.values["schedule_d_2025_part_ii_line_8b_column_h"] == 250
    assert multi.values["schedule_d_2025_line_15_net_lt"] == 250
    assert multi.values[TARGET] == 250


def _copy_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "graph", root / "graph", ignore=shutil.ignore_patterns("_drafts"))
    shutil.copytree(ROOT / "schemas", root / "schemas")
    shutil.copytree(ROOT / "config", root / "config")
    shutil.copytree(ROOT / "data", root / "data")
    _copy_required_drafts(root)
    return root


def _copy_required_drafts(root: Path) -> None:
    drafts_root = root / "graph" / "2025" / "_drafts"
    drafts_root.mkdir(parents=True, exist_ok=True)
    for document_id in ("form_8949_2025", "schedule_d_2025"):
        shutil.copytree(ROOT / "graph" / "2025" / "_drafts" / document_id, drafts_root / document_id)
