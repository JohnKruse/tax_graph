"""Tests for the M15 Step 3 review manifest projection."""

from __future__ import annotations

import copy
from pathlib import Path
import shutil

import pytest
import yaml

from workbench.manifest import build_manifest
from workbench.schema import validate_review_manifest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m15
def test_live_manifest_covers_every_pending_entry_and_is_stable() -> None:
    first = build_manifest(ROOT, 2025)
    second = build_manifest(ROOT, 2025)

    validate_review_manifest(first)
    assert first == second
    assert len(first["manifest_hash"]) == 64
    assert first["entries"]
    assert all(entry["units"] for entry in first["entries"])
    assert all(unit["analog_placement"] is None for entry in first["entries"] for unit in entry["units"])

    queue = yaml.safe_load((ROOT / "review_queue" / "2025" / "deferred_review.yaml").read_text(encoding="utf-8"))
    expected = {
        entry["queue_id"]
        for entry in queue["entries"]
        if entry.get("status") == "pending" or entry.get("review_status") == "pending"
    }
    assert {entry["queue_id"] for entry in first["entries"]} == expected


@pytest.mark.m15
def test_manifest_writes_stable_json_and_keeps_scope_roles_out_of_public_refs(tmp_path: Path) -> None:
    output = tmp_path / "manifest.json"
    payload = build_manifest(ROOT, 2025, output_path=output)

    assert output.exists()
    assert output.read_text(encoding="utf-8").endswith("\n")
    assert all(
        "role" not in object_ref
        for entry in payload["entries"]
        for unit in entry["units"]
        for object_ref in unit["object_refs"]
    )
    expression_kinds = {
        unit["expression"]["kind"]
        for entry in payload["entries"]
        for unit in entry["units"]
    }
    assert expression_kinds <= {
        "reference", "input", "imported", "copy", "sum", "subtract", "negate",
        "multiply", "lookup_table", "lookup_bracket", "max", "min", "if_else",
        "repeatable_table", "parameter", "frontier", "review_gap",
    }


@pytest.mark.m15
def test_manifest_hash_pins_every_file_in_example_artifact_directory(tmp_path: Path) -> None:
    source_dir = ROOT / "examples" / "irs_examples" / "instructions_schedule_d_2025" / "example_008"
    example_dir = tmp_path / "example_008"
    shutil.copytree(source_dir, example_dir)
    queue = yaml.safe_load((ROOT / "review_queue" / "2025" / "deferred_review.yaml").read_text(encoding="utf-8"))
    queue_copy = copy.deepcopy(queue)
    for entry in queue_copy["entries"]:
        if entry["queue_id"] != "irs_example_review_instructions_schedule_d_2025_example_008":
            continue
        for ref in entry["review_scope"]["object_refs"]:
            ref["source_path"] = str(example_dir)
    queue_path = tmp_path / "deferred_review.yaml"
    queue_path.write_text(yaml.safe_dump(queue_copy, sort_keys=False), encoding="utf-8")

    first = build_manifest(ROOT, 2025, queue_path=queue_path)
    pinned = {artifact["path"] for artifact in first["source_artifacts"]}
    assert {
        (example_dir / "expected.yaml").as_posix(),
        (example_dir / "facts.yaml").as_posix(),
        (example_dir / "provenance.yaml").as_posix(),
    } <= pinned

    facts_path = example_dir / "facts.yaml"
    facts_path.write_text(facts_path.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
    second = build_manifest(ROOT, 2025, queue_path=queue_path)

    assert second["manifest_hash"] != first["manifest_hash"]
