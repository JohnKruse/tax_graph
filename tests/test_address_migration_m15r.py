from __future__ import annotations

import json
from pathlib import Path

import pytest

from tax_graph.addressing import AddressArtifacts, CanonicalAddress, AddressComponent
from tax_graph.addressing.migration import MigrationCandidate, migration_report, semantic_join_inventory


ROOT = Path(__file__).resolve().parents[1]


def _address(address_id: str, ref: str, *, alias: str = "") -> CanonicalAddress:
    path = (AddressComponent("document", "form_test"), AddressComponent("line", ref), AddressComponent("control", "amount"))
    raw = {"aliases": [alias] if alias else []}
    return CanonicalAddress(address_id, address_id.split("/", 1)[1], 2025, "form_test_2025", None, "control", path, ref, "amount", "pending_review", raw)


@pytest.mark.m15r
def test_migration_report_has_all_four_states_and_is_byte_stable() -> None:
    artifacts = AddressArtifacts((_address("2025/document=form_test/line=1/control=amount", "1", alias="duplicate"), _address("2025/document=form_test/line=2/control=amount", "2", alias="duplicate")))
    candidates = [
        MigrationCandidate("renamed_node", "form_test_2025", official_ref="1", control_role="amount"),
        MigrationCandidate("weak_evidence", "form_test_2025", official_ref="2", control_role="amount", evidence_complete=False),
        MigrationCandidate("trailing_number_label_99", "form_test_2025", alias="duplicate"),
        MigrationCandidate("missing_target", "form_test_2025", official_ref="3", control_role="amount"),
    ]
    first = migration_report(candidates, artifacts)
    second = migration_report(reversed(candidates), artifacts)
    assert first == second
    assert {item["state"] for item in first["results"]} == {"exact", "provisional", "ambiguous", "unresolved"}
    assert json.dumps(first, sort_keys=True).isascii()


@pytest.mark.m15r
def test_legacy_semantic_joins_are_explicit_and_bounded(tmp_path: Path) -> None:
    inventory = semantic_join_inventory(ROOT)
    assert len(inventory) == 6
    assert {item["disposition"] for item in inventory} == {"replace_r8", "replace_r9", "replace_r10"}
