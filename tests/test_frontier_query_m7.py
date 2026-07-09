from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tax_graph.acquire.manifest import load_manifest
from tax_graph.frontier.build import build_frontier_registry, summarize_frontier
from tax_graph.frontier.soi import load_soi_counts
from tax_graph.io.loader import load_graph


ROOT = Path(__file__).resolve().parents[1]


def _copy_frontier_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "graph", root / "graph")
    shutil.copytree(ROOT / "schemas", root / "schemas")
    shutil.copytree(ROOT / "config", root / "config")
    shutil.copytree(ROOT / "data", root / "data")
    return root


@pytest.mark.m7
def test_frontier_summary_worklist_and_coverage(tmp_path):
    root = _copy_frontier_root(tmp_path)
    build_frontier_registry("2025", root=root)

    summary = summarize_frontier("2025", root=root)
    graph = load_graph("2025", root)
    soi = load_soi_counts(root)
    manifest = load_manifest(root=root)
    weights = [entry["weight"] for entry in summary["worklist"]]
    modeled_docs = {doc["document_id"] for doc in graph.items("documents") if "document_id" in doc}
    in_scope_docs = {entry.document_id for entry in manifest.documents if entry.document_id in soi.counts}
    expected_full_weight = sum(soi.counts.values())
    expected_modeled_weight = sum(weight for doc, weight in soi.counts.items() if doc in modeled_docs)
    expected_in_scope_weight = sum(weight for doc, weight in soi.counts.items() if doc in in_scope_docs)
    expected_in_scope_modeled_weight = sum(
        weight for doc, weight in soi.counts.items() if doc in modeled_docs and doc in in_scope_docs
    )

    assert summary["coverage"] == {
        "modeled_weight": expected_modeled_weight,
        "full_universe_weight": expected_full_weight,
        "full_universe_percent": round((expected_modeled_weight / expected_full_weight) * 100.0, 1),
        "in_scope_modeled_weight": expected_in_scope_modeled_weight,
        "in_scope_weight": expected_in_scope_weight,
        "in_scope_percent": round((expected_in_scope_modeled_weight / expected_in_scope_weight) * 100.0, 1),
    }
    assert weights == sorted(weights, reverse=True)
    assert any(entry["frontier_id"] == "deferred_schedule_d_2025_line_20" for entry in summary["worklist"])


@pytest.mark.m7
def test_frontier_coverage_increases_when_weighted_form_is_modeled(tmp_path):
    root = _copy_frontier_root(tmp_path)
    documents_dir = root / "graph" / "2025" / "documents"
    (documents_dir / "schedule-b.yaml").unlink()
    before = summarize_frontier("2025", root=root)["coverage"]["full_universe_percent"]
    (documents_dir / "schedule-b.yaml").write_text(
        yaml.safe_dump(
            {
                "document_id": "schedule_b_2025",
                "title": "Schedule B",
                "tax_year": 2025,
                "document_type": "schedule",
                "source_url": "https://www.irs.gov/pub/irs-pdf/f1040sb.pdf",
                "status": "partial",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    after = summarize_frontier("2025", root=root)["coverage"]["full_universe_percent"]

    assert after > before


@pytest.mark.m7
def test_frontier_cli_text_and_json(tmp_path):
    root = _copy_frontier_root(tmp_path)
    build_frontier_registry("2025", root=root)

    text_result = subprocess.run(
        [sys.executable, "-m", "tax_graph.cli", "frontier", "--year", "2025", "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    json_result = subprocess.run(
        [sys.executable, "-m", "tax_graph.cli", "frontier", "--year", "2025", "--root", str(root), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert text_result.returncode == 0, text_result.stderr
    assert "covers ~" in text_result.stdout
    assert "SOI provenance: 2023" in text_result.stdout
    assert "schedule_d_2025 line 20" in text_result.stdout
    assert json_result.returncode == 0, json_result.stderr
    payload = json.loads(json_result.stdout)
    assert payload["coverage"]["full_universe_percent"] > 0
    # Worklist is weight-sorted descending; entries come and go as walls are
    # declared, so assert the ordering contract, not a hardcoded top entry.
    weights = [entry["weight"] for entry in payload["worklist"] if entry["weight"] is not None]
    assert weights == sorted(weights, reverse=True)
    assert 24000000 in weights  # schedule_d line 20 stays declared
