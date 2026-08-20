"""M20-S151 guard for the derived Form 2441 frontier."""

from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.frontier.build import build_frontier_registry
from tax_graph.frontier.soi import load_form_id_map


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]


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
