from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tax_graph.frontier.build import build_frontier_registry, summarize_frontier


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
    weights = [entry["weight"] for entry in summary["worklist"]]

    assert summary["coverage"]["full_universe_percent"] > 0
    assert summary["coverage"]["full_universe_percent"] < 100
    assert summary["coverage"]["in_scope_percent"] == 100.0
    assert weights == sorted(weights, reverse=True)
    assert any(entry["frontier_id"] == "deferred_schedule_d_2025_line_20" for entry in summary["worklist"])


@pytest.mark.m7
def test_frontier_coverage_increases_when_weighted_form_is_modeled(tmp_path):
    root = _copy_frontier_root(tmp_path)
    before = summarize_frontier("2025", root=root)["coverage"]["full_universe_percent"]
    documents_dir = root / "graph" / "2025" / "documents"
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
    assert payload["worklist"][0]["weight"] == 24000000
