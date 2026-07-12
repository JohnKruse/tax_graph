"""Phase M15 Step 3 verdict and pipeline round-trip tests."""

from __future__ import annotations

from pathlib import Path
import shutil

import pytest
import yaml

from tax_graph.review import apply_verdicts
from workbench.verdicts import emit_verdict, load_verdict


ROOT = Path(__file__).resolve().parents[1]


def _review_root(tmp_path: Path) -> Path:
    for name in ("node.schema.json", "deferred_review_queue.schema.json", "review_verdict.schema.json"):
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
    return tmp_path


@pytest.mark.m15
def test_verdict_emission_is_schemaed_hashed_and_append_only(tmp_path: Path) -> None:
    root = _review_root(tmp_path)
    result = emit_verdict(
        root=root,
        year=2025,
        queue_id="q_node",
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
            verdict_id="verdict_q_node_1",
            reviewer_id="john",
            human_minutes=1,
            verdict="confirmed",
        )


@pytest.mark.m15
def test_apply_confirmed_verdict_updates_queue_graph_and_provenance(tmp_path: Path) -> None:
    root = _review_root(tmp_path)
    emitted = emit_verdict(
        root=root,
        year=2025,
        queue_id="q_node",
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


@pytest.mark.m15
def test_edited_verdict_is_rejected_by_hash_check(tmp_path: Path) -> None:
    root = _review_root(tmp_path)
    emitted = emit_verdict(
        root=root,
        year=2025,
        queue_id="q_node",
        verdict_id="verdict_q_node_1",
        reviewer_id="john",
        human_minutes=2.5,
        verdict="confirmed",
    )
    text = emitted.path.read_text(encoding="utf-8").replace("human_minutes: 2.5", "human_minutes: 99.5")
    emitted.path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="content hash mismatch"):
        apply_verdicts(2025, root=root)
