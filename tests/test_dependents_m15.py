"""M15 repeatable dependent facts and honest Form 1040 output tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tax_graph.engine import Engine, Graph
from tax_graph.io.loader import load_graph
from tax_graph.output import DependentAttachmentRequired, build_field_values, load_field_maps
from tax_graph.output.fill import DEPENDENTS_TABLE_GROUP
from workbench.cell_inventory import build_document_cells
from tax_graph.record import build_return_record
from tax_graph.validate import validate_taxpayer_facts_document


ROOT = Path(__file__).resolve().parents[1]


def _dependent(index: int, *, decisions: dict | None = None) -> dict:
    result = {
        "row_key": f"dependent_{index}",
        "first_name": f"First{index}",
        "last_name": f"Last{index}",
        "ssn": f"123-45-67{index:02d}",
        "relationship": "child",
        "source": {"document_label": "Filer intake", "extracted_by": "manual"},
    }
    if decisions is not None:
        result["eligibility_decisions"] = decisions
    return result


def _document(count: int) -> dict:
    return {
        "tax_year": 2025,
        "filing_status": "single",
        "facts": [{"node_id": "form_1040_2025_root_line_1a", "value": 1000}],
        "dependents": [_dependent(index) for index in range(1, count + 1)],
    }


def _values(document: dict) -> dict[str, str]:
    graph = Graph(2025, root=ROOT, source="yaml")
    result = Engine(graph).execute(
        {"form_1040_2025_root_line_1a": 1000, "filing_status": "single"}
    )
    field_map = next(
        item for item in load_field_maps(2025, ROOT) if item["document_id"] == "form_1040_2025"
    )
    return build_field_values(field_map, result, document, root=ROOT)[0]


@pytest.mark.m15
@pytest.mark.parametrize("count", [0, 1, 4])
def test_zero_one_and_four_dependents_validate_and_fill_deterministically(count: int) -> None:
    document = _document(count)
    assert validate_taxpayer_facts_document(document, load_graph("2025", ROOT)) == []
    values = _values(document)
    identity_fields = [
        f"topmostSubform[0].Page1[0].Table_Dependents[0].Row{row + 1}[0].f1_{31 + row * 4 + dependent:02d}[0]"
        for dependent in range(4)
        for row in range(4)
    ]
    assert sum(field in values for field in identity_fields) == count * 4
    if count:
        assert values[identity_fields[0]] == "First1"
        assert values[identity_fields[1]] == "Last1"
        if count >= 2:
            assert values[identity_fields[4]] == "First2"
        else:
            assert identity_fields[4] not in values


@pytest.mark.m15
def test_dependents_table_group_matches_filler_and_workbench_projection() -> None:
    field_map = next(
        item for item in load_field_maps(2025, ROOT) if item["document_id"] == "form_1040_2025"
    )
    dispositions = [
        item
        for item in field_map["field_dispositions"]
        if (item.get("repeatable") or {}).get("column") == "first_name"
    ]
    assert dispositions
    assert {item["repeatable"]["group"] for item in dispositions} == {DEPENDENTS_TABLE_GROUP}

    geometry = json.loads(
        (ROOT / "graph" / "2025" / "node_geometry.json").read_text(encoding="utf-8")
    )["entries"]
    cells = build_document_cells(
        ROOT, 2025, "form_1040_2025", geometry_entries=geometry, include_inputs=False
    ).cells
    projected = [
        cell for cell in cells if cell.get("concept_id") == "form_1040/dependents/dependent/first_name"
    ]
    assert projected
    assert {cell["repeatable"]["group"] for cell in projected} == {DEPENDENTS_TABLE_GROUP}


@pytest.mark.m15
def test_five_dependents_fail_closed_with_attachment_guidance() -> None:
    document = _document(5)
    with pytest.raises(DependentAttachmentRequired, match="attached dependent statement"):
        _values(document)


@pytest.mark.m15
def test_identity_never_auto_selects_credit_or_eligibility_boxes() -> None:
    values = _values(_document(4))
    assert not any(".c1_" in field and "Table_Dependents" in field for field in values)


@pytest.mark.m15
def test_explicit_provenanced_decision_can_select_one_credit_box() -> None:
    decision = {
        "child_tax_credit": {
            "value": True,
            "decided_by": "filer",
            "decided_date": "2026-07-14",
            "rationale": "Filer completed the qualification questions.",
        }
    }
    document = _document(1)
    document["dependents"][0] = _dependent(1, decisions=decision)
    values = _values(document)
    selected = "topmostSubform[0].Page1[0].Table_Dependents[0].Row7[0].Dependent1[0].c1_28[0]"
    other = "topmostSubform[0].Page1[0].Table_Dependents[0].Row7[0].Dependent1[0].c1_28[1]"
    assert selected in values
    assert other not in values


@pytest.mark.m15
def test_duplicate_runtime_dependent_keys_are_rejected() -> None:
    document = _document(2)
    document["dependents"][1]["row_key"] = document["dependents"][0]["row_key"]
    errors = validate_taxpayer_facts_document(document, load_graph("2025", ROOT))
    assert any("duplicate row_key" in error for error in errors)


@pytest.mark.m15
def test_return_record_surfaces_universal_gate_without_mutation() -> None:
    document = _document(1)
    before = copy.deepcopy(document)
    graph = Graph(2025, root=ROOT, source="yaml")
    result = Engine(graph).execute(
        {"form_1040_2025_root_line_1a": 1000, "filing_status": "single"}
    )
    record = build_return_record(facts_document=document, result=result, graph=graph)
    assert any("universal gate" in item for item in record.unsupported)
    assert any("explicit filer decisions" in item for item in record.unsupported)
    assert document == before
    assert "human_confirmed" not in repr(record.to_dict())
