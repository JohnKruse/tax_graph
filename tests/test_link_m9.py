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
DRAFT_SNAPSHOTS = ROOT / "tests" / "fixtures" / "draft_snapshots"
FACTS = ROOT / "examples" / "capital_gains_basic" / "facts.yaml"
MULTI_FACTS = ROOT / "examples" / "capital_gains_multi_lot" / "facts.yaml"
TARGET = "form_1040_2025_line_7_capital_gain_loss"


def test_link_realizes_reviewed_8949_outbound_flows_idempotently(tmp_path):
    root = _copy_root(tmp_path)
    linked_path = root / "graph" / "2025" / "edges" / "linked-outbound.yaml"
    first_text = linked_path.read_text(encoding="utf-8")
    first = link_outbound_flows("2025", root=root)
    second = link_outbound_flows("2025", root=root)

    assert first.path == linked_path
    assert len(first.realized) == 6
    assert first.unresolved == []
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
    assert len(link_result.unresolved) == 1
    assert link_result.unresolved[0]["target_line"] == "99"
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
    # Live drafts are gitignored (never committed), so tests copy frozen
    # snapshots from tests/fixtures/draft_snapshots instead of graph/<year>/_drafts.
    drafts_root = root / "graph" / "2025" / "_drafts"
    drafts_root.mkdir(parents=True, exist_ok=True)
    for document_id in ("form_8949_2025", "schedule_d_2025", "form_6251_2025"):
        shutil.copytree(DRAFT_SNAPSHOTS / document_id, drafts_root / document_id)


def test_link_skips_rejected_false_positive_flows(tmp_path):
    root = _copy_root(tmp_path)
    shutil.copy2(ROOT / "graph" / "2025" / "flow-dispositions.yaml", root / "graph" / "2025" / "flow-dispositions.yaml")

    result = link_outbound_flows("2025", root=root)

    assert len(result.realized) == 6
    assert result.unresolved == []
    assert [item["flow_id"] for item in result.rejected] == [
        "flow_form_6251_2025_outbound_schedule_d_column_h_to_schedule_d_2025_line_2",
        "flow_form_6251_2025_outbound_schedule_d_column_h_to_schedule_d_2025_line_3",
    ]
