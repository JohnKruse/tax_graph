"""M20-S151 guards for the manifest core set and derived Form 2441 frontier."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tax_graph.acquire.manifest import load_manifest, validate_manifest_data
from tax_graph.frontier.build import build_frontier_registry
from tax_graph.frontier.soi import load_form_id_map


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]


# Sourced from docs/tax_graph_requirements.md sections 9.2 and 9.3, plus the
# explicit Schedule A, Schedule 1-A, and Form 6251 additions in the M20-S151
# handoff. This is intentionally independent of the live manifest markers.
EXPECTED_CORE_DOCUMENTS = frozenset({
    "form_1040_2025",
    "instructions_form_1040_2025",
    "schedule_1_2025",
    "schedule_2_2025",
    "schedule_3_2025",
    "form_w2_2025",
    "form_1099_int_2025",
    "form_1099_div_2025",
    "schedule_b_2025",
    "form_1099b_2025",
    "form_8949_2025",
    "schedule_d_2025",
    "instructions_schedule_d_2025",
    "instructions_form_8949_2025",
    "schedule_a_2025",
    "schedule_1a_2025",
    "form_6251_2025",
})


def _marked_core_documents(data: dict) -> frozenset[str]:
    return frozenset(
        entry["document_id"]
        for entry in data["documents"]
        if entry.get("core") is True
    )


def test_live_manifest_core_set_matches_the_ruling() -> None:
    data = yaml.safe_load((ROOT / "config" / "manifest.yaml").read_text(encoding="ascii"))
    assert _marked_core_documents(data) == EXPECTED_CORE_DOCUMENTS
    assert len(_marked_core_documents(data)) == 17

    manifest = load_manifest(root=ROOT)
    assert {
        entry.document_id for entry in manifest.documents if entry.core
    } == EXPECTED_CORE_DOCUMENTS


def test_core_set_guard_detects_a_removed_marker() -> None:
    data = yaml.safe_load((ROOT / "config" / "manifest.yaml").read_text(encoding="ascii"))
    data["documents"] = [
        entry for entry in data["documents"] if entry["document_id"] != "form_1040_2025"
    ]
    with pytest.raises(AssertionError):
        assert _marked_core_documents(data) == EXPECTED_CORE_DOCUMENTS


def test_manifest_schema_accepts_core_marker() -> None:
    data = yaml.safe_load((ROOT / "config" / "manifest.yaml").read_text(encoding="ascii"))
    validate_manifest_data(data, root=ROOT)


def test_form_2441_frontier_entries_are_builder_derived() -> None:
    mapping = load_form_id_map(ROOT)
    assert mapping["Form 2441"] == "form_2441_2025"
    assert mapping["Instructions for Form 2441"] == "instructions_form_2441_2025"

    registry = build_frontier_registry("2025", root=ROOT, write=False).registry
    entries = [
        entry
        for entry in registry["frontiers"]
        if entry["kind"] == "form_reference"
        and entry["target"].get("document_id") == "form_2441_2025"
    ]
    assert len(entries) == 8
    assert {entry["status"] for entry in entries} == {"modeled"}
    assert {entry["weight"] for entry in entries} == {None}
