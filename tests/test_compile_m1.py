from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from tax_graph.compile import build_sqlite
from tax_graph.engine import Engine, Graph, load_facts
from tax_graph.io.loader import GRAPH_KINDS, load_graph


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "capital_gains_basic"


@pytest.mark.m1
def test_build_sqlite_writes_expected_row_counts(tmp_path):
    result = build_sqlite("2025", root=ROOT, build_dir=tmp_path)
    # SQLite is deliberately project-only; local user extensions remain YAML
    # overlays and must not make this row-count test environment-dependent.
    loaded = load_graph("2025", root=ROOT, include_extensions=False)

    assert result.path == tmp_path / "tax_graph_2025.sqlite"
    assert result.path.exists()
    with sqlite3.connect(result.path) as conn:
        for kind in GRAPH_KINDS:
            assert conn.execute(f"SELECT COUNT(*) FROM {kind}").fetchone()[0] == len(loaded.items(kind))


@pytest.mark.m1
def test_build_sqlite_fts_finds_known_citation(tmp_path):
    result = build_sqlite("2025", root=ROOT, build_dir=tmp_path)

    with sqlite3.connect(result.path) as conn:
        rows = conn.execute(
            """
            SELECT object_id
            FROM graph_fts
            WHERE graph_fts MATCH ? AND kind = 'citations'
            ORDER BY object_id
            """,
            ('"Subtract column"',),
        ).fetchall()

    assert ("cite_8949_col_h_gain",) in rows


@pytest.mark.m1
def test_cli_build_writes_configured_sqlite_artifact(tmp_path):
    root = _copy_graph_project(tmp_path)

    result = subprocess.run(
        [sys.executable, "-m", "tax_graph.cli", "build", "2025", "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "tax_graph_2025.sqlite" in result.stdout
    assert (root / "compiled" / "tax_graph_2025.sqlite").exists()


@pytest.mark.m1
def test_sqlite_runtime_matches_yaml_values_and_trace(tmp_path):
    root = _copy_graph_project(tmp_path)
    build_sqlite("2025", root=root)
    facts = load_facts(EXAMPLE / "facts.yaml")

    yaml_graph = Graph(2025, root=root, source="yaml")
    sqlite_graph = Graph(2025, root=root, source="sqlite")
    auto_graph = Graph(2025, root=root)
    yaml_result = Engine(yaml_graph).execute(facts)
    sqlite_result = Engine(sqlite_graph).execute(facts)

    assert auto_graph.source == "sqlite"
    assert sqlite_result.values == yaml_result.values
    assert sqlite_result.trace == yaml_result.trace
    assert sqlite_result.values["form_1040_2025_line_7_capital_gain_loss"] == 2000


@pytest.mark.m1
def test_cli_run_can_execute_from_sqlite_source(tmp_path):
    root = _copy_graph_project(tmp_path)
    build_sqlite("2025", root=root)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tax_graph.cli",
            "run",
            "--facts",
            str(EXAMPLE / "facts.yaml"),
            "--source",
            "sqlite",
            "--no-record",
            "--root",
            str(root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "form_1040_2025_line_7_capital_gain_loss = 2000" in result.stdout


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
