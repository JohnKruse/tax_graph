"""Phase M15 Step 3 verdict and pipeline round-trip tests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil

import pytest
import yaml

from tax_graph.review import apply_verdicts
from workbench.verdicts import emit_verdict, load_verdict


ROOT = Path(__file__).resolve().parents[1]


def _review_root(tmp_path: Path) -> Path:
    for name in (
        "node.schema.json",
        "deferred_review_queue.schema.json",
        "review_manifest.schema.json",
        "review_verdict.schema.json",
    ):
        (tmp_path / "schemas").mkdir(exist_ok=True)
        shutil.copy(ROOT / "schemas" / name, tmp_path / "schemas" / name)
    queue_dir = tmp_path / "review_queue" / "2025"
    queue_dir.mkdir(parents=True)
    (queue_dir / "deferred_review.yaml").write_text(
        """tax_year: 2025
entries:
- queue_id: q_node
  kind: promotion_review
  status: pending
  priority: high
  document_id: form_a_2025
  created_date: '2026-07-12'
  created_by: test
  summary: Review node
  artifact_paths:
  - graph/2025/nodes/review.yaml
  review_scope:
    scope_version: 1
    scope_type: promotion
    object_refs:
    - object_type: node
      object_id: node_a
      role: primary
      source_path: graph/2025/nodes/review.yaml
""",
        encoding="utf-8",
    )
    nodes_dir = tmp_path / "graph" / "2025" / "nodes"
    nodes_dir.mkdir(parents=True)
    (nodes_dir / "review.yaml").write_text(
        """- node_id: node_a
  document_id: form_a_2025
  label: Test node
  node_type: form_line
  value_type: currency
""",
        encoding="utf-8",
    )
    _write_manifest(tmp_path)
    return tmp_path


def _write_manifest(root: Path) -> str:
    sources = []
    for relative in (
        "review_queue/2025/deferred_review.yaml",
        "graph/2025/nodes/review.yaml",
    ):
        digest = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        sources.append({"path": relative, "content_hash": digest})
    body = {
        "schema_version": 1,
        "tax_year": 2025,
        "source_artifacts": sources,
        "entries": [
            {
                "queue_id": "q_node",
                "review_kind": "promotion_review",
                "status": "pending",
                "units": [
                    {
                        "queue_id": "q_node",
                        "unit_id": "q_node_node_a",
                        "review_kind": "promotion_review",
                        "required": True,
                        "object_refs": [
                            {
                                "object_type": "node",
                                "object_id": "node_a",
                                "artifact_path": "graph/2025/nodes/review.yaml",
                            }
                        ],
                        "official_location": None,
                        "analog_placement": None,
                        "semantic_class": "input",
                        "summary": "Review node",
                        "expression": {
                            "kind": "reference",
                            "ref": {"object_type": "node", "object_id": "node_a"},
                        },
                        "coverage": {"state": "pending", "required_for_confirm": True},
                    }
                ],
            }
        ],
    }
    canonical = json.dumps(body, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    manifest_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    payload = {**body, "manifest_hash": manifest_hash}
    path = root / ".workbench_state" / "2025" / "review_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return manifest_hash


@pytest.mark.m15
def test_verdict_emission_is_schemaed_hashed_and_append_only(tmp_path: Path) -> None:
    root = _review_root(tmp_path)
    result = emit_verdict(
        root=root,
        year=2025,
        queue_id="q_node",
        manifest_hash=_write_manifest(root),
        verdict_id="verdict_q_node_1",
        reviewer_id="john",
        human_minutes=2.5,
        verdict="confirmed",
        reviewed_at="2026-07-12T10:00:00Z",
    )
    loaded = load_verdict(result.path)
    assert loaded.payload["content_hash"]
    with pytest.raises(FileExistsError):
        emit_verdict(
            root=root,
            year=2025,
            queue_id="q_node",
            manifest_hash=_write_manifest(root),
            verdict_id="verdict_q_node_1",
            reviewer_id="john",
            human_minutes=1,
            verdict="confirmed",
        )


@pytest.mark.m15
def test_concurrent_duplicate_verdict_creation_is_exclusive(tmp_path: Path) -> None:
    root = _review_root(tmp_path)
    manifest_hash = _write_manifest(root)

    def create() -> str:
        result = emit_verdict(
            root=root,
            year=2025,
            queue_id="q_node",
            manifest_hash=manifest_hash,
            verdict_id="verdict_q_node_race",
            reviewer_id="john",
            human_minutes=1,
            verdict="confirmed",
            reviewed_at="2026-07-12T10:00:00Z",
        )
        return result.verdict_id

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(create) for _ in range(2)]
    outcomes = []
    for future in futures:
        try:
            outcomes.append(future.result())
        except FileExistsError:
            outcomes.append("exists")

    assert sorted(outcomes) == ["exists", "verdict_q_node_race"]
    load_verdict(root / "review_verdicts" / "2025" / "verdict_q_node_race.yaml")


@pytest.mark.m15
def test_apply_confirmed_verdict_updates_queue_graph_and_provenance(tmp_path: Path) -> None:
    root = _review_root(tmp_path)
    emitted = emit_verdict(
        root=root,
        year=2025,
        queue_id="q_node",
        manifest_hash=_write_manifest(root),
        verdict_id="verdict_q_node_1",
        reviewer_id="john",
        human_minutes=2.5,
        verdict="confirmed",
        reviewed_at="2026-07-12T10:00:00Z",
    )
    result = apply_verdicts(2025, root=root)
    assert result.confirmed == ("q_node",)
    queue = yaml.safe_load((root / "review_queue" / "2025" / "deferred_review.yaml").read_text(encoding="utf-8"))
    assert queue["entries"][0]["human_confirmed"] is True
    node = yaml.safe_load((root / "graph" / "2025" / "nodes" / "review.yaml").read_text(encoding="utf-8"))[0]
    assert node["human_confirmed"] is True
    assert node["verification_tier"] == "human-confirmed"
    assert node["human_review"]["reviewer_id"] == "john"
    assert emitted.payload["content_hash"] in (root / "review_provenance" / "2025" / "applied.yaml").read_text(encoding="utf-8")
    assert apply_verdicts(2025, root=root).applied == ()


@pytest.mark.m15
def test_unbounded_verdict_refuses_to_bulk_confirm_a_multi_object_file(tmp_path: Path) -> None:
    root = _review_root(tmp_path)
    # The target file gains a SECOND node and the queue entry has no
    # expected_nodes; a verdict with no object_ref must NOT confirm both.
    (root / "graph" / "2025" / "nodes" / "review.yaml").write_text(
        """- node_id: node_a
  document_id: form_a_2025
  label: Test node A
  node_type: form_line
  value_type: currency
- node_id: node_b
  document_id: form_a_2025
  label: Test node B
  node_type: form_line
  value_type: currency
""",
        encoding="utf-8",
    )
    manifest_hash = _write_manifest(root)
    emit_verdict(
        root=root,
        year=2025,
        queue_id="q_node",
        manifest_hash=manifest_hash,
        verdict_id="verdict_q_node_1",
        reviewer_id="john",
        human_minutes=2.5,
        verdict="confirmed",
        reviewed_at="2026-07-12T10:00:00Z",
    )
    with pytest.raises(ValueError, match="refusing to human-confirm"):
        apply_verdicts(2025, root=root)


@pytest.mark.m15
def test_edited_verdict_is_rejected_by_hash_check(tmp_path: Path) -> None:
    root = _review_root(tmp_path)
    emitted = emit_verdict(
        root=root,
        year=2025,
        queue_id="q_node",
        manifest_hash=_write_manifest(root),
        verdict_id="verdict_q_node_1",
        reviewer_id="john",
        human_minutes=2.5,
        verdict="confirmed",
    )
    text = emitted.path.read_text(encoding="utf-8").replace("human_minutes: 2.5", "human_minutes: 99.5")
    emitted.path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="content hash mismatch"):
        apply_verdicts(2025, root=root)


@pytest.mark.m15
def test_apply_rejects_verdict_after_reviewed_artifact_changes(tmp_path: Path) -> None:
    root = _review_root(tmp_path)
    emit_verdict(
        root=root,
        year=2025,
        queue_id="q_node",
        manifest_hash=_write_manifest(root),
        verdict_id="verdict_q_node_1",
        reviewer_id="john",
        human_minutes=1,
        verdict="confirmed",
    )
    node_path = root / "graph" / "2025" / "nodes" / "review.yaml"
    node_path.write_text(node_path.read_text(encoding="utf-8").replace("Test node", "Changed node"), encoding="utf-8")

    with pytest.raises(ValueError, match="source artifact changed"):
        apply_verdicts(2025, root=root)


@pytest.mark.m15
def test_apply_rejects_scoped_target_from_another_object(tmp_path: Path) -> None:
    root = _review_root(tmp_path)
    emit_verdict(
        root=root,
        year=2025,
        queue_id="q_node",
        manifest_hash=_write_manifest(root),
        verdict_id="verdict_q_node_1",
        reviewer_id="john",
        human_minutes=1,
        verdict="confirmed",
        object_ref={
            "artifact_path": "graph/2025/nodes/review.yaml",
            "object_kind": "nodes",
            "object_id": "node_b",
        },
    )

    with pytest.raises(ValueError, match="outside the queue review scope"):
        apply_verdicts(2025, root=root)
