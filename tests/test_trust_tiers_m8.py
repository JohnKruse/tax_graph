"""M8 Step 6: trust tiers, deterministic routing, metrics, report, draft delta."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from tax_graph.cli import verify_diff_drafts_command, verify_report_command
from tax_graph.extract.models import CheckIssue, DeterministicReport, DraftObject, ExtractionBatch
from tax_graph.extract.route import route_drafts, write_routed_drafts
from tax_graph.verify.metrics import build_metrics, classify_flag
from tax_graph.verify.tiers import TierInputs, assign_tier, collect_covered_nodes

ROOT = Path(__file__).resolve().parents[1]


def _node(node_id: str, *, kind: str = "nodes", confidence: float = 0.99) -> DraftObject:
    return DraftObject(
        kind=kind,
        data={"node_id" if kind == "nodes" else "decision_id": node_id, "document_id": "form_x"},
        source_span="span",
        extracted_by="model-a",
        confidence=confidence,
    )


def _batch(objects: list[DraftObject]) -> ExtractionBatch:
    return ExtractionBatch(document_id="form_x", year="2025", objects=objects)


@pytest.mark.m8
def test_tier_ladder_is_deterministic_from_check_outcomes():
    clean = _node("form_x_line_1")
    flagged = _node("form_x_line_2")
    flagged.flag("schema: bad")

    agreed = frozenset({("nodes", "form_x_line_1")})
    covered = frozenset({"form_x_line_1"})

    assert assign_tier(flagged, TierInputs()) == "T0"
    assert assign_tier(clean, None) == "T1"
    assert assign_tier(clean, TierInputs(nversion_agreed=frozenset())) == "T1"
    assert assign_tier(clean, TierInputs(nversion_agreed=agreed)) == "T2"
    assert assign_tier(clean, TierInputs(nversion_agreed=agreed, properties_ok=True)) == "T2"
    assert (
        assign_tier(clean, TierInputs(nversion_agreed=agreed, properties_ok=True, covered_nodes=covered))
        == "T3"
    )


@pytest.mark.m8
def test_routing_ignores_confidence_and_samples_deterministically():
    def make(confidence: float) -> list[DraftObject]:
        return [_node(f"form_x_line_{i}", confidence=confidence) for i in range(12)]

    routed_high = route_drafts(_batch(make(1.0)), DeterministicReport(issues=[]))
    routed_low = route_drafts(_batch(make(0.31)), DeterministicReport(issues=[]))

    ids = lambda objs: [(o.kind, o.object_id) for o in objs]
    assert ids(routed_high.accepted) == ids(routed_low.accepted)
    assert ids(routed_high.review) == ids(routed_low.review) == []
    assert ids(routed_high.calibration) == ids(routed_low.calibration)
    # 10% of 12 rounds up to 2 but the minimum of 5 wins.
    assert len(routed_high.calibration) == 5

    rerun = route_drafts(_batch(make(1.0)), DeterministicReport(issues=[]))
    assert ids(rerun.calibration) == ids(routed_high.calibration)


@pytest.mark.m8
def test_decisions_always_route_to_human_review():
    decision = _node("form_x_choice", kind="decisions")
    routed = route_drafts(_batch([decision]), DeterministicReport(issues=[]))
    assert routed.accepted == []
    assert routed.review == [decision]
    assert decision.tier == "T0"
    assert any("decision" in flag for flag in decision.flags)


@pytest.mark.m8
def test_metrics_capture_tiers_layers_and_telemetry(tmp_path):
    clean = _node("form_x_line_1")
    flagged = _node("form_x_line_2", confidence=0.5)
    flagged.flag("critic agreement required")
    batch = _batch([clean, flagged])
    report = DeterministicReport(issues=[CheckIssue("nodes", "form_x_line_2", "field grid: unmapped")])
    routed = route_drafts(batch, report, tier_inputs=TierInputs())
    routed = write_routed_drafts(batch, routed, root=tmp_path)

    metrics = yaml.safe_load((routed.output_dir / "metrics.yaml").read_text(encoding="utf-8"))
    assert metrics["document_id"] == "form_x"
    assert metrics["tiers"] == {"T0": 1, "T1": 1, "T2": 0, "T3": 0}
    assert metrics["flags_by_layer"] == {"critic": 1, "field_grid": 1}
    assert metrics["routing"] == {"accepted": 1, "review": 1, "calibration_sample": 1}
    assert metrics["confidence_telemetry"]["min"] == 0.5
    assert metrics["human_minutes"] is None
    assert metrics["worker_tokens"] is None
    assert metrics["worker_cost"] is None

    assert classify_flag("schema: missing property") == "schema"
    assert classify_flag("line 3 has no node") == "line_completeness"
    assert classify_flag("inline magic number 3000") == "parameters"


@pytest.mark.m8
def test_verify_report_rolls_up_metrics(tmp_path, capsys):
    drafts = tmp_path / "graph" / "2025" / "_drafts" / "form_x"
    drafts.mkdir(parents=True)
    (drafts / "metrics.yaml").write_text(
        yaml.safe_dump(
            {
                "document_id": "form_x",
                "objects_by_kind": {"nodes": 4},
                "routing": {"accepted": 3, "review": 1, "calibration_sample": 3},
                "tiers": {"T0": 1, "T1": 3, "T2": 0, "T3": 0},
                "human_minutes": None,
                "worker_tokens": 321,
                "worker_cost": 1.25,
                "escapes": 0,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "config").mkdir()
    shutil.copy(ROOT / "config" / "tax-graph.config.example.yaml", tmp_path / "config" / "tax-graph.config.yaml")

    assert verify_report_command(year="2025", root=tmp_path) == 0
    out = capsys.readouterr().out
    assert "form_x: objects=4" in out
    assert "tiers(T0/T1/T2/T3)=1/3/0/0" in out
    assert "human minutes per object: not yet recorded" in out
    assert "worker tokens recorded: 321" in out
    assert "worker cost recorded: 1.2500" in out
    assert "escapes found in calibration audits: 0" in out


@pytest.mark.m8
def test_covered_nodes_collects_expected_keys(tmp_path):
    example = tmp_path / "examples" / "sample"
    example.mkdir(parents=True)
    (example / "expected.yaml").write_text(
        yaml.safe_dump({"expected": {"form_x_line_1": 10}}), encoding="utf-8"
    )
    flat = tmp_path / "examples" / "flat"
    flat.mkdir()
    (flat / "expected.yaml").write_text(yaml.safe_dump({"form_x_line_9": 5}), encoding="utf-8")

    covered = collect_covered_nodes(tmp_path)
    assert covered == frozenset({"form_x_line_1", "form_x_line_9"})


@pytest.mark.m8
def test_diff_drafts_detects_added_removed_changed(tmp_path, capsys):
    root = tmp_path
    shutil.copytree(ROOT / "graph", root / "graph", ignore=shutil.ignore_patterns("_drafts", "*.sqlite"))
    shutil.copytree(ROOT / "schemas", root / "schemas")
    (root / "config").mkdir()
    shutil.copy(ROOT / "config" / "tax-graph.config.example.yaml", root / "config" / "tax-graph.config.yaml")

    draft_dir = root / "graph" / "2025" / "_drafts" / "form_8949_2025"
    draft_dir.mkdir(parents=True)
    live_nodes = yaml.safe_load(
        (ROOT / "graph" / "2025" / "nodes" / "capital-gains.yaml").read_text(encoding="utf-8")
    )
    doc_nodes = [node for node in live_nodes if node.get("document_id") == "form_8949_2025"]
    assert doc_nodes, "expected promoted 8949 nodes in the live graph"

    changed = yaml.safe_load(yaml.safe_dump(doc_nodes[0]))
    changed["label"] = "Changed label for delta test"
    kept = doc_nodes[1:-1]
    added = {
        "node_id": "form_8949_2025_part_iii_line_99_column_z",
        "document_id": "form_8949_2025",
        "label": "Phantom",
        "node_type": "form_line",
        "value_type": "currency",
    }
    (draft_dir / "nodes.yaml").write_text(
        yaml.safe_dump([changed, *kept, added], sort_keys=False), encoding="utf-8"
    )

    exit_code = verify_diff_drafts_command(doc="form_8949_2025", year="2025", root=root)
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "added: nodes/form_8949_2025_part_iii_line_99_column_z" in out
    assert f"changed: nodes/{changed['node_id']}" in out
    assert f"removed: nodes/{doc_nodes[-1]['node_id']}" in out
