from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from tax_graph.frontier.build import build_frontier_registry, load_frontier_registry


ROOT = Path(__file__).resolve().parents[1]


def _copy_frontier_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "graph", root / "graph")
    shutil.copytree(ROOT / "schemas", root / "schemas")
    shutil.copytree(ROOT / "config", root / "config")
    shutil.copytree(ROOT / "data", root / "data")
    return root


@pytest.mark.m7
def test_frontier_build_emits_8949_outbound_flows_with_schedule_d_weight(tmp_path):
    root = _copy_frontier_root(tmp_path)

    result = build_frontier_registry("2025", root=root)
    registry = load_frontier_registry("2025", root=root)
    flows = [entry for entry in registry["frontiers"] if entry["kind"] == "outbound_flow"]
    by_line = {entry["target"]["line"]: entry for entry in flows}

    assert result.path == root / "graph" / "2025" / "frontier.yaml"
    assert result.path.exists()
    assert set(by_line) >= {"1b", "2", "3", "8b", "9", "10"}
    assert by_line["1b"]["status"] == "modeled"
    assert by_line["8b"]["status"] == "modeled"
    assert by_line["8b"]["target"]["node_id"] == "schedule_d_2025_part_ii_line_8b_column_h"
    assert all(entry["status"] == "modeled" for entry in flows)
    assert all(entry["weight"] == 24000000 for entry in flows)
    assert all(entry["citation_ref"] == "cite_8949_line2_totals" for entry in flows)


@pytest.mark.m7
def test_frontier_build_detects_publication_references(tmp_path):
    root = _copy_frontier_root(tmp_path)
    citations_path = root / "graph" / "2025" / "citations" / "capital-gains.yaml"
    citations = yaml.safe_load(citations_path.read_text(encoding="utf-8"))
    citations.append(
        {
            "citation_id": "cite_pub_550_reference",
            "document_id": "schedule_d_2025",
            "quoted_text": "For more information, see Publication 550.",
            "url": "https://www.irs.gov/publications/p550",
        }
    )
    citations_path.write_text(yaml.safe_dump(citations, sort_keys=False), encoding="utf-8")

    registry = build_frontier_registry("2025", root=root).registry

    pub_refs = [entry for entry in registry["frontiers"] if entry["kind"] == "pub_reference"]
    assert pub_refs[0]["target"] == {"external_id": "publication_550"}
    assert pub_refs[0]["weight"] is None
