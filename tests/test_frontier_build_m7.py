from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from tax_graph.frontier.build import build_frontier_registry, load_frontier_registry


ROOT = Path(__file__).resolve().parents[1]
DRAFT_SNAPSHOTS = ROOT / "tests" / "fixtures" / "draft_snapshots"


def _copy_frontier_root(tmp_path: Path) -> Path:
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
    for document_id in ("form_8949_2025", "schedule_d_2025"):
        shutil.copytree(DRAFT_SNAPSHOTS / document_id, drafts_root / document_id)


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
    assert by_line["1b"]["status"] == "declared"
    assert by_line["8b"]["status"] == "declared"
    assert "node_id" not in by_line["8b"]["target"]
    assert all(entry["status"] == "declared" for entry in flows)
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


@pytest.mark.m7
def test_frontier_build_marks_rejected_flow_dispositions(tmp_path):
    root = _copy_frontier_root(tmp_path)
    shutil.copy2(ROOT / "graph" / "2025" / "flow-dispositions.yaml", root / "graph" / "2025" / "flow-dispositions.yaml")
    shutil.copytree(DRAFT_SNAPSHOTS / "form_6251_2025", root / "graph" / "2025" / "_drafts" / "form_6251_2025")

    registry = build_frontier_registry("2025", root=root, write=False).registry

    rejected = {
        entry["source"]["flow_id"]: entry
        for entry in registry["frontiers"]
        if entry["kind"] == "outbound_flow" and entry["status"] == "rejected"
    }
    assert set(rejected) == {
        "flow_form_6251_2025_outbound_schedule_d_column_h_to_schedule_d_2025_line_2",
        "flow_form_6251_2025_outbound_schedule_d_column_h_to_schedule_d_2025_line_3",
    }
    assert all(entry["disposition"] == "rejected" for entry in rejected.values())
    assert all("false positive" in entry["disposition_reason"].lower() for entry in rejected.values())
