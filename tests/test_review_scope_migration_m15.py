"""Tests for the M15 deferred-review scope migration."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from tax_graph.cli import migrate_review_scope_command
from tax_graph.review_scope import migrate_review_scope


ROOT = Path(__file__).resolve().parents[1]


def _write_queue(root: Path, entries: list[dict[str, object]]) -> Path:
    path = root / "review_queue" / "2025" / "deferred_review.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"tax_year": 2025, "entries": entries}, sort_keys=False), encoding="utf-8")
    return path


def _entry(queue_id: str, kind: str, **extra: object) -> dict[str, object]:
    return {
        "queue_id": queue_id,
        "kind": kind,
        "status": "pending",
        "priority": "medium",
        "document_id": "form_a_2025",
        "created_date": "2026-07-13",
        "created_by": "test",
        "summary": "Review a scoped object.",
        **extra,
    }


@pytest.mark.m15
def test_migration_backfills_explicit_scopes_and_is_idempotent(tmp_path: Path) -> None:
    field_map = tmp_path / "graph" / "2025" / "field_maps" / "form_a.yaml"
    field_map.parent.mkdir(parents=True)
    field_map.write_text(
        yaml.safe_dump(
            {
                "tax_year": 2025,
                "document_id": "form_a_2025",
                "inventory": "inventory.json",
                "mappings": [{"slot": "line_1", "field_name": "f1", "node_id": "node_a"}],
                "excluded_nodes": [{"node_id": "node_b", "reason": "not printed"}],
                "frontier_fields": [{"frontier_id": "frontier_a", "field_name": "f2", "note": "later"}],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    nodes = tmp_path / "graph" / "2025" / "nodes.yaml"
    nodes.write_text("- node_id: node_a\n", encoding="utf-8")
    review_dir = tmp_path / "graph" / "2025" / "_drafts" / "form_a_2025"
    review_dir.mkdir(parents=True)
    (review_dir / "review.md").write_text(
        "- nodes/node_a tier=T0 confidence=1.000\n",
        encoding="utf-8",
    )
    queue_path = _write_queue(
        tmp_path,
        [
            _entry("expected_entry", "irs_example_review", expected_nodes=["node_a#example_1"]),
            _entry(
                "field_entry",
                "field_map_review",
                artifact_paths=["graph/2025/field_maps/form_a.yaml"],
            ),
            _entry(
                "promotion_entry",
                "promotion_review",
                artifact_dir="graph/2025/_drafts/form_a_2025",
                artifact_paths=["graph/2025/nodes.yaml"],
            ),
            {**_entry("complete_entry", "promotion_review"), "status": "complete"},
        ],
    )
    output = tmp_path / "migrated.yaml"

    first = migrate_review_scope(root=tmp_path, queue_path=queue_path, output_path=output)
    first_bytes = output.read_bytes()
    second = migrate_review_scope(root=tmp_path, queue_path=output, output_path=output)

    assert first.changed_entries == ("expected_entry", "field_entry", "promotion_entry")
    assert second.changed_entries == ()
    assert output.read_bytes() == first_bytes
    payload = yaml.safe_load(output.read_text(encoding="utf-8"))
    scopes = {entry["queue_id"]: entry.get("review_scope") for entry in payload["entries"]}
    assert scopes["expected_entry"]["object_refs"][0]["object_type"] == "node_instance"
    assert {ref["object_id"] for ref in scopes["field_entry"]["object_refs"]} == {
        "node_a",
        "node_b",
        "frontier_a",
    }
    assert scopes["promotion_entry"]["object_refs"] == [
        {
            "object_type": "node",
            "object_id": "node_a",
            "source_path": "graph/2025/_drafts/form_a_2025/review.md",
            "role": "primary",
        }
    ]
    assert scopes["complete_entry"] is None
    schema = json.loads((ROOT / "schemas" / "deferred_review_queue.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(payload, schema)


@pytest.mark.m15
def test_migration_fails_closed_without_object_scope(tmp_path: Path) -> None:
    queue_path = _write_queue(tmp_path, [_entry("unscoped_entry", "promotion_review")])
    with pytest.raises(ValueError, match="document-wide scope is forbidden"):
        migrate_review_scope(root=tmp_path, queue_path=queue_path, output_path=tmp_path / "out.yaml")


@pytest.mark.m15
def test_cli_migrate_scope_reports_changed_entries(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    queue_path = _write_queue(
        tmp_path,
        [_entry("expected_entry", "irs_example_review", expected_nodes=["node_a#example_1"])],
    )
    assert migrate_review_scope_command(year="2025", root=tmp_path) == 0
    captured = capsys.readouterr().out
    assert "migrated review scopes: 1" in captured
    assert "expected_entry" not in captured
    assert "review_scope" in queue_path.read_text(encoding="utf-8")


@pytest.mark.m15
def test_live_queue_migration_gives_every_pending_entry_a_primary_target(tmp_path: Path) -> None:
    source = yaml.safe_load((ROOT / "review_queue" / "2025" / "deferred_review.yaml").read_text(encoding="utf-8"))
    entries = copy.deepcopy(source["entries"])
    for entry in entries:
        entry.pop("review_scope", None)
    queue_path = _write_queue(tmp_path, entries)
    output = tmp_path / "migrated.yaml"

    migrate_review_scope(root=ROOT, queue_path=queue_path, output_path=output)

    payload = yaml.safe_load(output.read_text(encoding="utf-8"))
    pending = [entry for entry in payload["entries"] if entry.get("status") == "pending" or entry.get("review_status") == "pending"]
    assert pending
    assert all(
        any(ref.get("role") == "primary" for ref in entry["review_scope"]["object_refs"])
        for entry in pending
    )
    by_id = {entry["queue_id"]: entry for entry in pending}
    decision_ids = {ref["object_id"] for ref in by_id["decision_review_1040_deduction_method"]["review_scope"]["object_refs"]}
    assert {"decision_1040_deduction_method", "standard", "itemized"} <= decision_ids
    routing_ids = {ref["object_id"] for ref in by_id["routing_review_schedule_d_2025_line_20_decision"]["review_scope"]["object_refs"]}
    assert "schedule_d_2025_line_20_gate" in routing_ids
    refs = [ref for entry in pending for ref in entry["review_scope"]["object_refs"]]
    field_controls = {
        (ref["source_path"], ref["object_id"])
        for ref in refs
        if ref["object_type"] == "field_control"
    }
    inventory_count = sum(
        len(json.loads(path.read_text(encoding="utf-8"))["fields"])
        for path in (ROOT / "graph" / "2025" / "field_inventories").glob("*.json")
    )
    assert len(field_controls) == inventory_count
    assert len(refs) < 4000
