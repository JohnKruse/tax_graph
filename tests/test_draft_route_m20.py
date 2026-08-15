from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.extract.checks import _apply_issues
from tax_graph.extract.models import CheckIssue, DeterministicReport, DraftObject, ExtractionBatch, RoutedDrafts
from tax_graph.extract import route
from tax_graph.extract.route import _swap_staged_draft_contents, route_drafts, write_routed_drafts


@pytest.mark.m20
def test_deterministic_issue_flags_only_the_implicated_object():
    batch = ExtractionBatch(
        document_id="form_1040_2025",
        year="2025",
        objects=[
            DraftObject(
                "documents",
                {"document_id": "form_1040_2025"},
                "",
                "test",
                1.0,
            ),
            DraftObject(
                "nodes",
                {"node_id": "node_clean"},
                "",
                "test",
                1.0,
            ),
            DraftObject(
                "nodes",
                {"node_id": "node_bad"},
                "",
                "test",
                1.0,
            ),
        ],
    )
    issues = [
        CheckIssue("document", "form_1040_2025", "field grid: document issue"),
        CheckIssue("properties", "node_bad", "property_execution: node issue"),
    ]

    _apply_issues(batch, issues)
    routed = route_drafts(
        batch,
        DeterministicReport(issues=issues),
        config={"extraction": {"require_critic_agreement": False}},
    )

    assert {obj.object_id for obj in routed.review} == {"form_1040_2025", "node_bad"}
    assert [obj.object_id for obj in routed.accepted] == ["node_clean"]
    assert batch.by_identity()[("nodes", "node_clean")].flags == []


@pytest.mark.m20
def test_empty_regenerated_kind_removes_stale_draft_file(tmp_path: Path):
    draft_dir = tmp_path / "graph" / "2025" / "_drafts" / "schedule_a_2025"
    draft_dir.mkdir(parents=True)
    stale = draft_dir / "nodes.yaml"
    stale.write_text("- node_id: stale\n", encoding="ascii")

    batch = ExtractionBatch(
        document_id="schedule_a_2025",
        year="2025",
        objects=[],
    )
    routed = RoutedDrafts(
        accepted=[],
        review=[],
        issues=[],
        output_dir=None,
        calibration=[],
    )

    written = write_routed_drafts(batch, routed, root=tmp_path)

    assert written.output_dir == draft_dir
    assert not stale.exists()


@pytest.mark.m20
def test_route_writer_emits_expression_kinds(tmp_path: Path):
    batch = ExtractionBatch(
        document_id="form_1040_2025",
        year="2025",
        objects=[
            DraftObject(
                "rules",
                {"rule_id": "rule_sum", "operation": "SUM", "description": "Add values."},
                "",
                "generator",
                1.0,
            ),
            DraftObject(
                "edges",
                {
                    "edge_id": "edge_sum",
                    "source": "form_1040_2025_a",
                    "target": "form_1040_2025_b",
                    "relationship": "CALCULATES",
                    "rule_id": "rule_sum",
                    "role": "addend",
                },
                "",
                "generator",
                1.0,
            ),
        ],
    )
    routed = RoutedDrafts(accepted=[], review=[], issues=[], output_dir=None, calibration=[])

    written = write_routed_drafts(batch, routed, root=tmp_path)

    assert written.output_dir == tmp_path / "graph" / "2025" / "_drafts" / "form_1040_2025"
    assert (written.output_dir / "edges.yaml").exists()
    assert (written.output_dir / "rules.yaml").exists()


@pytest.mark.m20
def test_failed_staged_write_preserves_previous_draft_byte_for_byte(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    draft_dir = tmp_path / "graph" / "2025" / "_drafts" / "form_1040_2025"
    draft_dir.mkdir(parents=True)
    previous = {
        "nodes.yaml": "- node_id: previous\n",
        "edges.yaml": "- edge_id: previous\n",
        "rules.yaml": "- rule_id: previous\n",
    }
    for name, contents in previous.items():
        (draft_dir / name).write_text(contents, encoding="ascii")

    original_write_yaml = route._write_yaml
    calls = 0

    def fail_after_first_write(path: Path, data: object) -> None:
        nonlocal calls
        calls += 1
        original_write_yaml(path, data)
        if calls == 1:
            raise RuntimeError("simulated mid-run draft failure")

    monkeypatch.setattr(route, "_write_yaml", fail_after_first_write)
    batch = ExtractionBatch(
        document_id="form_1040_2025",
        year="2025",
        objects=[
            DraftObject(
                "nodes",
                {"node_id": "new"},
                "",
                "test",
                1.0,
            )
        ],
    )

    with pytest.raises(RuntimeError, match="simulated mid-run"):
        write_routed_drafts(batch, RoutedDrafts(accepted=[], review=[], issues=[]), root=tmp_path)

    assert {name: (draft_dir / name).read_text(encoding="ascii") for name in previous} == previous
    assert not list(draft_dir.parent.glob(".form_1040_2025.draft-*"))


@pytest.mark.m20
def test_transport_failed_batch_does_not_replace_previous_draft(tmp_path: Path):
    draft_dir = tmp_path / "graph" / "2025" / "_drafts" / "form_1040_2025"
    draft_dir.mkdir(parents=True)
    sentinel = draft_dir / "rules.yaml"
    sentinel.write_text("- rule_id: previous\n", encoding="ascii")

    batch = ExtractionBatch(
        document_id="form_1040_2025",
        year="2025",
        objects=[],
        micro_stats={"transport_failures": 1},
    )

    written = write_routed_drafts(batch, RoutedDrafts(accepted=[], review=[], issues=[]), root=tmp_path)

    assert written.output_dir == draft_dir
    assert sentinel.read_text(encoding="ascii") == "- rule_id: previous\n"


@pytest.mark.m20
def test_file_set_swap_fallback_replaces_complete_tree(tmp_path: Path):
    parent = tmp_path / "drafts"
    draft_dir = parent / "form_1040_2025"
    staging_dir = parent / ".form_1040_2025.draft"
    draft_dir.mkdir(parents=True)
    staging_dir.mkdir(parents=True)
    (draft_dir / "rules.yaml").write_text("- rule_id: previous\n", encoding="ascii")
    (draft_dir / "stale.yaml").write_text("stale\n", encoding="ascii")
    (staging_dir / "rules.yaml").write_text("- rule_id: new\n", encoding="ascii")
    (staging_dir / "nodes.yaml").write_text("- node_id: new\n", encoding="ascii")

    _swap_staged_draft_contents(staging_dir, draft_dir)

    assert (draft_dir / "rules.yaml").read_text(encoding="ascii") == "- rule_id: new\n"
    assert (draft_dir / "nodes.yaml").read_text(encoding="ascii") == "- node_id: new\n"
    assert not (draft_dir / "stale.yaml").exists()
    assert not staging_dir.exists()
