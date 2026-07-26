"""M19-S3a tests for structured-form concepts and physical occurrences."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from tax_graph.addressing.registry import load_address_artifacts
from tax_graph.output.concepts import (
    STRUCTURED_DOCUMENTS,
    ConceptError,
    build_document_concepts,
    retrieve_occurrences,
    retrieve_table_occurrence,
    validate_occurrence_contract,
    validate_concept_id,
)
from workbench.cell_inventory import build_document_cells


ROOT = Path(__file__).resolve().parents[1]
GEOMETRY = json.loads((ROOT / "graph/2025/node_geometry.json").read_text(encoding="utf-8"))["entries"]


def _addresses(document_id: str) -> list[dict[str, object]]:
    payload = yaml.safe_load(
        (ROOT / "graph/2025/addresses" / f"{document_id}.yaml").read_text(encoding="utf-8")
    )
    return payload["addresses"]


@pytest.mark.m19
def test_promoted_concept_inventories_and_placements_are_schema_valid() -> None:
    schema = json.loads((ROOT / "schemas/concept_inventory.schema.json").read_text(encoding="utf-8"))
    for document_id in STRUCTURED_DOCUMENTS:
        inventory, projections = build_document_concepts(ROOT, 2025, document_id)
        jsonschema.Draft202012Validator(schema).validate(inventory)
        assert projections
        for concept in inventory["concepts"]:
            validate_concept_id(concept["concept_id"])
            assert concept["review_granularity"] == "concept"
            assert concept["aliases"]
            for placement in concept["placements"]:
                assert placement["concept_id"] == concept["concept_id"]
                assert placement["printed_token"]

        live = {str(item["address_id"]): item for item in _addresses(document_id)}
        for address_id, projection in projections.items():
            assert live[address_id]["concept_id"] == projection["concept_id"]
            assert live[address_id]["placement"] == projection["placement"]
            assert live[address_id]["occurrence"] == projection["occurrence"]
            assert live[address_id]["logical_key"] in live[address_id]["aliases"]


@pytest.mark.m19
def test_owner_qualification_and_never_contains_rules_fail_closed() -> None:
    with pytest.raises(ConceptError):
        validate_concept_id("form_1040/identity/ssn")
    with pytest.raises(ConceptError):
        validate_concept_id("form_1040/line_33/amount")
    with pytest.raises(ConceptError):
        validate_concept_id("form_1040/identity/taxpayer/ssn_2025")

    dependent_ssn = next(
        item for item in _addresses("form_1040_2025") if item["address_id"].endswith("column=ssn")
    )
    assert dependent_ssn["concept_id"] == "form_1040/dependents/dependent/ssn"
    assert "line" not in dependent_ssn["concept_id"]
    assert "box" not in dependent_ssn["concept_id"]
    assert "2025" not in dependent_ssn["concept_id"]


@pytest.mark.m19
def test_repeatable_widgets_are_visible_instances_without_changing_concept_granularity() -> None:
    expected = {
        "form_1040_2025": 199,
        "form_8949_2025": 202,
        "form_w2_2025": 272,
        "form_1099_div_2025": 140,
        "form_1099_int_2025": 127,
        "form_1099b_2025": 163,
        "schedule_1a_2025": 54,
    }
    for document_id, total in expected.items():
        cells = build_document_cells(
            ROOT, 2025, document_id, geometry_entries=GEOMETRY, include_inputs=False
        ).cells
        assert len(cells) == total
        repeatable = [cell for cell in cells if cell.get("review_granularity") == "concept"]
        assert repeatable
        assert all(cell["concept_id"] for cell in repeatable)
        assert all(cell["occurrence"]["review_granularity"] == "concept" for cell in repeatable)

    dependents = build_document_cells(
        ROOT, 2025, "form_1040_2025", geometry_entries=GEOMETRY, include_inputs=False
    ).cells
    ssn_rows = [cell for cell in dependents if cell["concept_id"] == "form_1040/dependents/dependent/ssn"]
    assert len(ssn_rows) == 4
    assert {cell["repeatable"]["row_slot"] for cell in ssn_rows} == {1, 2, 3, 4}

    transactions = build_document_cells(
        ROOT, 2025, "form_8949_2025", geometry_entries=GEOMETRY, include_inputs=False
    ).cells
    proceeds = [
        cell for cell in transactions
        if cell["concept_id"] == "form_8949/short_term_transactions/transaction/proceeds"
    ]
    assert len(proceeds) == 11


@pytest.mark.m19
def test_line_oriented_documents_remain_without_s3a_concepts() -> None:
    for document_id in ("form_6251_2025", "schedule_1_2025", "schedule_2_2025", "schedule_d_2025"):
        for address in _addresses(document_id):
            assert "concept_id" not in address


@pytest.mark.m19
def test_address_loader_accepts_promoted_structured_placements() -> None:
    artifacts = load_address_artifacts(2025, ROOT)
    promoted = [item for item in artifacts.addresses if item.raw.get("concept_id")]
    assert len(promoted) == 191
    assert all(item.raw["placement"]["concept_id"] == item.raw["concept_id"] for item in promoted)


@pytest.mark.m19
def test_repeated_tables_are_retrievable_by_slot_axes() -> None:
    dependent_row = retrieve_table_occurrence(
        ROOT, 2025, "form_1040_2025", "form_1040/dependents/dependent/", row_slot=3
    )
    assert len(dependent_row) == 10
    assert {item["occurrence"]["axes"]["row_slot"] for item in dependent_row} == {3}
    assert "1040/dependents/dependent[3]/ssn" in {item["ref"] for item in dependent_row}

    w2_code = retrieve_occurrences(
        ROOT, 2025, "form_w2_2025", "form_w2/other_compensation/entry/code"
    )
    assert len(w2_code) == 24
    assert {item["occurrence"]["axes"]["copy"] for item in w2_code} == {"A", "B", "C", "D", "1", "2"}
    assert len({item["occurrence"]["key"] for item in w2_code}) == 24
    row_c = retrieve_occurrences(
        ROOT, 2025, "form_w2_2025", "form_w2/other_compensation/entry/code",
        axes={"copy": "A", "row_slot": 3},
    )
    assert len(row_c) == 1
    assert row_c[0]["ref"] == "w2/copy[A]/box12/entry[3]/code"

    state_row = retrieve_occurrences(
        ROOT, 2025, "form_1099b_2025", "form_1099b/state_local/jurisdiction/state",
        axes={"copy": "A", "row_slot": 2},
    )
    assert len(state_row) == 1
    assert state_row[0]["ref"].endswith("jurisdiction[2]/state")


@pytest.mark.m19
def test_repeated_singletons_fail_closed() -> None:
    with pytest.raises(ConceptError, match="repeated fields"):
        validate_occurrence_contract([
            {"concept_id": "form_w2/employee/ssn", "occurrence": {"kind": "singleton"}},
            {"concept_id": "form_w2/employee/ssn", "occurrence": {"kind": "singleton"}},
        ])
