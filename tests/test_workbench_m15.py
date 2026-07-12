"""Phase M15 Step 1 tests for the artifact-only workbench seam."""

from __future__ import annotations

import ast
from pathlib import Path
import sqlite3

import pytest

from workbench.artifacts import (
    ArtifactValidationError,
    load_artifact_bundle,
    load_geometry,
    load_review_queue,
    load_sqlite_graph,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m15
def test_workbench_has_no_pipeline_imports() -> None:
    forbidden = {"tax_graph", "tax_graph.acquire", "tax_graph.extract"}
    violations: list[str] = []
    for path in (ROOT / "workbench").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any(name in forbidden or name.startswith("tax_graph.") for name in names):
                violations.append(f"{path}:{node.lineno}: {', '.join(names)}")
    assert not violations, "workbench imports pipeline code:\n" + "\n".join(violations)


@pytest.mark.m15
def test_sqlite_loader_reads_public_rows_in_read_only_mode(tmp_path: Path) -> None:
    path = tmp_path / "tax_graph_2025.sqlite"
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE nodes (node_id TEXT PRIMARY KEY, object_json TEXT NOT NULL);
            CREATE TABLE tax_table (income_min INTEGER, income_max INTEGER);
            INSERT INTO metadata VALUES ('tax_year', '2025');
            INSERT INTO metadata VALUES ('schema_version', '1');
            INSERT INTO metadata VALUES ('content_hash', 'abc');
            INSERT INTO nodes VALUES ('node_a', '{"node_id":"node_a","label":"A"}');
            INSERT INTO tax_table VALUES (0, 100);
            """
        )

    graph = load_sqlite_graph(path)
    assert graph.tax_year == 2025
    assert graph.objects("nodes") == ({"node_id": "node_a", "label": "A"},)
    assert graph.tax_table == ({"income_min": 0, "income_max": 100},)
    with pytest.raises(sqlite3.OperationalError):
        with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as conn:
            conn.execute("CREATE TABLE should_not_exist (value TEXT)")


@pytest.mark.m15
def test_public_json_and_yaml_schemas_are_enforced(tmp_path: Path) -> None:
    geometry = tmp_path / "node_geometry.json"
    geometry.write_text('{"tax_year":2025,"entries":[]}', encoding="utf-8")
    schema = ROOT / "schemas" / "node_geometry.schema.json"
    assert load_geometry(geometry, schema_path=schema)["tax_year"] == 2025

    queue = tmp_path / "deferred_review.yaml"
    queue.write_text("tax_year: 2025\nentries:\n- queue_id: q\n", encoding="utf-8")
    with pytest.raises(ArtifactValidationError):
        load_review_queue(queue, schema_path=ROOT / "schemas" / "deferred_review_queue.schema.json")


@pytest.mark.m15
def test_bundle_loads_drafts_metrics_nversion_examples_and_pdfs(tmp_path: Path) -> None:
    graph_path = tmp_path / "graph.sqlite"
    with sqlite3.connect(graph_path) as conn:
        conn.executescript(
            """
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE nodes (node_id TEXT PRIMARY KEY, object_json TEXT NOT NULL);
            INSERT INTO metadata VALUES ('tax_year', '2025');
            INSERT INTO metadata VALUES ('schema_version', '1');
            INSERT INTO metadata VALUES ('content_hash', 'abc');
            INSERT INTO nodes VALUES ('node_a', '{"node_id":"node_a"}');
            """
        )
    (tmp_path / "graph" / "2025").mkdir(parents=True)
    (tmp_path / "graph" / "2025" / "node_geometry.json").write_text(
        '{"tax_year":2025,"entries":[]}', encoding="utf-8"
    )
    (tmp_path / "schemas").mkdir()
    (tmp_path / "schemas" / "node_geometry.schema.json").write_text(
        (ROOT / "schemas" / "node_geometry.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "schemas" / "deferred_review_queue.schema.json").write_text(
        (ROOT / "schemas" / "deferred_review_queue.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "review_queue" / "2025").mkdir(parents=True)
    (tmp_path / "review_queue" / "2025" / "deferred_review.yaml").write_text(
        "tax_year: 2025\nentries: []\n", encoding="utf-8"
    )
    draft = tmp_path / "graph" / "2025" / "_drafts" / "form_a"
    draft.mkdir(parents=True)
    (draft / "metrics.yaml").write_text("document_id: form_a_2025\n", encoding="utf-8")
    (draft / "nversion.yaml").write_text("status: agreed\n", encoding="utf-8")
    (draft / "example_mining.yaml").write_text("examples: 0\n", encoding="utf-8")
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    (pdf_dir / "form_a.pdf").write_bytes(b"pdf")

    bundle = load_artifact_bundle(tmp_path, 2025, db_path=graph_path, pdf_dir=pdf_dir)
    assert bundle.metrics["graph/2025/_drafts/form_a/metrics.yaml"]["document_id"] == "form_a_2025"
    assert bundle.nversion_reports["graph/2025/_drafts/form_a/nversion.yaml"]["status"] == "agreed"
    assert bundle.mined_examples["graph/2025/_drafts/form_a/example_mining.yaml"]["examples"] == 0
    assert bundle.pdfs[0].sha256 == "c35b21d6ca39aa7cc3b79a705d989f1a6e88b99ab43988d74048799e3db926a3"
