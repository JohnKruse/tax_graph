from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import shutil
import asyncio

import pytest
import yaml

from tax_graph.engine import Graph
from tax_graph.engine.engine import _unresolved_trace
from tax_graph.extension import accept_extension, package_extension, run_extension
from tax_graph.compile import build_sqlite
from tax_graph.io.loader import extension_content_hash, load_graph
from tax_graph.mcp import build_mcp_server


ROOT = Path(__file__).resolve().parents[1]


def _copy_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "graph", root / "graph", ignore=shutil.ignore_patterns("_drafts"))
    for name in ("schemas", "config", "data", "examples", "oracles", "review_queue"):
        shutil.copytree(ROOT / name, root / name)
    return root


def _fake_renderer(entry, *, pdf_path, output_dir, content_hash, config):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{entry.document_id}.txt").write_text("# Page 1\n- 1: Example line\n", encoding="utf-8")
    (output / f"{entry.document_id}.fields.json").write_text('{"fields": []}\n', encoding="utf-8")


def _fake_extractor(document_id, *, year, root, config, **kwargs):
    draft_dir = Path(config["project"]["paths"]["graph_dir"]) / str(year) / "_drafts" / document_id
    draft_dir.mkdir(parents=True, exist_ok=True)
    (draft_dir / "nodes.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "node_id": f"{document_id}_line_1",
                    "document_id": document_id,
                    "label": "Example extension line",
                    "node_type": "form_line",
                    "value_type": "currency",
                    "gate": "user",
                }
            ],
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return SimpleNamespace(output_dir=draft_dir, ok=True, review=[], issues=[])


@pytest.mark.m14
def test_extension_pipeline_accepts_overlay_and_exposes_user_provenance(tmp_path: Path):
    root = _copy_root(tmp_path)
    config = {"project": {"paths": {"raw_store": ".cache/raw"}}}
    result = run_extension(
        "schedule_x_2025",
        year="2025",
        root=root,
        url="https://www.irs.gov/pub/irs-prior/fx--2025.pdf",
        kind="schedule",
        config=config,
        fetch_bytes=lambda url, settings: b"synthetic pdf",
        renderer=_fake_renderer,
        extractor=_fake_extractor,
        today=__import__("datetime").date(2026, 7, 12),
    )

    assert result.routed_ok is True
    assert result.verification_tier == "T1"
    assert "gate: user" in (result.draft_dir / "nodes.yaml").read_text(encoding="utf-8")
    queue_entries = yaml.safe_load(result.review_queue_path.read_text(encoding="utf-8"))["entries"]
    queue_entry = next(item for item in queue_entries if item["document_id"] == "schedule_x_2025")
    assert queue_entry["human_confirmed"] is False

    accepted = accept_extension("schedule_x_2025", root=root, config=config)
    assert accepted.content_hash == extension_content_hash(accepted.extension_dir)
    loaded = load_graph("2025", root=root)
    node = next(item for item in loaded.items("nodes") if item["node_id"] == "schedule_x_2025_line_1")
    assert node["gate"] == "user"
    assert loaded.extension_hashes["schedule_x_2025"] == accepted.content_hash

    graph = Graph("2025", root=root, source="yaml")
    assert graph.provenance_for_node("schedule_x_2025_line_1") == {
        "gate": "user",
        "document_id": "schedule_x_2025",
        "artifact_hash": accepted.content_hash,
        "verification_tier": "T1",
    }

    packaged = package_extension("schedule_x_2025", root=root, config=config, output_dir=tmp_path / "dist")
    assert packaged.path.exists()
    assert "verification.md" in __import__("zipfile").ZipFile(packaged.path).namelist()

    server = build_mcp_server(year="2025", root=root, source="yaml")
    _content, node_response = asyncio.run(server.call_tool("get_node", {"node_id": "schedule_x_2025_line_1"}))
    assert node_response["provenance"]["gate"] == "user"
    assert node_response["provenance"]["artifact_hash"] == accepted.content_hash
    _content, document_response = asyncio.run(server.call_tool("get_document", {"document_id": "schedule_x_2025"}))
    assert document_response["verification"]["verification_tier"] == "T1"
    _content, execution = asyncio.run(server.call_tool("execute_tax_tree", {"facts": {}}))
    assert execution["provenance"]["schedule_x_2025_line_1"]["gate"] == "user"


@pytest.mark.m14
def test_extension_collision_and_tamper_are_hard_errors(tmp_path: Path):
    root = _copy_root(tmp_path)
    extension_dir = root / "graph_ext" / "2025" / "schedule_x_2025"
    extension_dir.mkdir(parents=True)
    (extension_dir / "documents.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "document_id": "schedule_x_2025",
                    "title": "X",
                    "tax_year": 2025,
                    "document_type": "schedule",
                    "status": "partial",
                    "gate": "user",
                }
            ],
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (extension_dir / "nodes.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "node_id": "form_1040_2025_line_7_capital_gain_loss",
                    "document_id": "schedule_x_2025",
                    "label": "collision",
                    "node_type": "fact",
                    "value_type": "currency",
                    "gate": "user",
                }
            ],
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (extension_dir / "extension.json").write_text(
        '{"content_hash": "' + extension_content_hash(extension_dir) + '", "document_id": "schedule_x_2025"}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="collision"):
        load_graph("2025", root=root)


@pytest.mark.m14
def test_extension_hash_stamp_detects_graph_tampering(tmp_path: Path):
    root = _copy_root(tmp_path)
    extension_dir = root / "graph_ext" / "2025" / "schedule_x_2025"
    extension_dir.mkdir(parents=True)
    document = {
        "document_id": "schedule_x_2025",
        "title": "X",
        "tax_year": 2025,
        "document_type": "schedule",
        "status": "partial",
        "gate": "user",
    }
    node = {
        "node_id": "schedule_x_2025_line_1",
        "document_id": "schedule_x_2025",
        "label": "X",
        "node_type": "fact",
        "value_type": "currency",
        "gate": "user",
    }
    (extension_dir / "documents.yaml").write_text(yaml.safe_dump([document], sort_keys=False), encoding="utf-8")
    (extension_dir / "nodes.yaml").write_text(yaml.safe_dump([node], sort_keys=False), encoding="utf-8")
    stamped = extension_content_hash(extension_dir)
    (extension_dir / "extension.json").write_text(
        '{"document_id": "schedule_x_2025", "content_hash": "' + stamped + '"}\n',
        encoding="utf-8",
    )
    node["label"] = "tampered"
    (extension_dir / "nodes.yaml").write_text(yaml.safe_dump([node], sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="content hash mismatch"):
        load_graph("2025", root=root)


@pytest.mark.m14
def test_sqlite_hash_stamp_and_frontier_escape_hatch(tmp_path: Path):
    root = _copy_root(tmp_path)
    build_sqlite("2025", root=root)
    graph_file = root / "graph" / "2025" / "documents" / "form-1040.yaml"
    graph_file.write_text(graph_file.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="content hash mismatch"):
        Graph("2025", root=root, source="sqlite")

    trace = _unresolved_trace(
        {"source": "schedule_x_2025_line_9", "role": "addend"},
        {
            "frontier_id": "frontier_schedule_x_line_9",
            "target": {"document_id": "schedule_x_2025", "line": "9"},
            "target_url": "https://www.irs.gov/pub/irs-prior/fx--2025.pdf",
        },
    )
    assert trace["extend_command"] == "tax-graph extend schedule_x_2025"
    assert trace["target_tier"] == "T1"
    assert trace["proposed_provenance"]["gate"] == "user"
