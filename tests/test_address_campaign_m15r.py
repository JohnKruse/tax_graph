from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from tax_graph.addressing import CORE_RETURN_DOCUMENTS, INFORMATION_RETURN_DOCUMENTS, build_address_campaign
from tax_graph.link import link_outbound_flows


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def campaign():
    return build_address_campaign(ROOT, CORE_RETURN_DOCUMENTS)


@pytest.mark.m15r
def test_core_campaign_reconciles_every_inventory_control(campaign) -> None:
    registry_schema = json.loads((ROOT / "schemas/address_registry.schema.json").read_text(encoding="utf-8"))
    binding_schema = json.loads((ROOT / "schemas/address_binding.schema.json").read_text(encoding="utf-8"))
    reference_schema = json.loads((ROOT / "schemas/address_reference.schema.json").read_text(encoding="utf-8"))
    assert tuple(campaign) == CORE_RETURN_DOCUMENTS
    for payload in campaign.values():
        coverage = payload["coverage"]
        assert coverage["inventory"] == coverage["addressed_widgets"] + coverage["exempt_widgets"]
        assert len(payload["widget_bindings"]["bindings"]) == coverage["addressed_widgets"]
        assert len(payload["node_bindings"]["bindings"]) == coverage["node_bindings"]
        assert all(item["status"] in {"pending_review", "provisional"} for item in payload["registry"]["addresses"])
        jsonschema.validate(payload["registry"], registry_schema)
        jsonschema.validate(payload["widget_bindings"], binding_schema)
        jsonschema.validate(payload["node_bindings"], binding_schema)
        jsonschema.validate(payload["references"], reference_schema)


@pytest.mark.m15r
def test_form_8949_uses_row_template_columns(campaign) -> None:
    payload = campaign["form_8949_2025"]
    assert payload["coverage"] == {
        "inventory": 202,
        "addressed_widgets": 200,
        "exempt_widgets": 2,
        "node_bindings": 16,
        "references": 6,
    }
    paths = [item["path"] for item in payload["registry"]["addresses"]]
    assert any(
        [part["kind"] for part in path[-3:]] == ["table", "row_template", "column"]
        and path[-1]["token"] == "d"
        for path in paths
    )
    bindings = payload["widget_bindings"]["bindings"]
    assert len({item["address_id"] for item in bindings}) < len(bindings)
    addresses = {item["address_id"]: item for item in payload["registry"]["addresses"]}
    assert addresses["2025/document=form_8949/table=part_i_line_1/row_template=transaction/column=a"]["printed_label"] == "Description of property"
    assert addresses["2025/document=form_8949/table=part_ii_line_2/row_template=total/column=e"]["printed_label"] == "Total cost or other basis"


@pytest.mark.m15r
def test_schedule_d_worksheet_steps_are_explicitly_bound(campaign) -> None:
    payload = campaign["schedule_d_2025"]
    bindings = {item["node_id"]: item for item in payload["node_bindings"]["bindings"]}
    for node_id in (
        "schedule_d_2025_carryover_worksheet_line_1",
        "schedule_d_2025_carryover_worksheet_line_13",
        "schedule_d_2025_tax_worksheet_line_1",
        "schedule_d_2025_tax_worksheet_line_47",
    ):
        assert bindings[node_id]["address_id"].split("/")[-1].startswith("worksheet_step=")


@pytest.mark.m15r
def test_form_8949_cross_form_claims_resolve_exactly() -> None:
    result = link_outbound_flows(2025, ROOT, write=False)
    assert len(result.realized) == 6
    assert result.unresolved == []
    assert len(result.rejected) == 2


@pytest.fixture(scope="module")
def information_campaign():
    return build_address_campaign(ROOT, INFORMATION_RETURN_DOCUMENTS)


@pytest.mark.m15r
def test_information_return_campaign_uses_typed_boxes_and_choices(information_campaign) -> None:
    schema = json.loads((ROOT / "schemas/address_registry.schema.json").read_text(encoding="utf-8"))
    for document_id, payload in information_campaign.items():
        coverage = payload["coverage"]
        assert coverage["inventory"] == coverage["addressed_widgets"] + coverage["exempt_widgets"]
        jsonschema.validate(payload["registry"], schema)
        if document_id == "form_13614_c_2025":
            assert coverage["addressed_widgets"] == coverage["inventory"]
            continue
        assert coverage["addressed_widgets"] > 0
        if document_id == "form_w2_2025":
            assert coverage["exempt_widgets"] == 0
            continue
        else:
            assert coverage["exempt_widgets"] > 0
        addressed = {item["address_id"]: item for item in payload["registry"]["addresses"]}
        for binding in payload["widget_bindings"]["bindings"]:
            path = addressed[binding["address_id"]]["path"]
            assert path[-2]["kind"] == "box"
            assert path[-1]["kind"] in {"control", "option"}


@pytest.mark.m15
def test_w2_campaign_collapses_official_copies_and_state_rows(information_campaign) -> None:
    payload = information_campaign["form_w2_2025"]
    assert payload["coverage"] == {
        "inventory": 272,
        "addressed_widgets": 272,
        "exempt_widgets": 0,
        "node_bindings": 0,
        "references": 0,
    }
    bindings = payload["widget_bindings"]["bindings"]
    assert len({item["address_id"] for item in bindings}) == 33
    addresses = {item["address_id"]: item for item in payload["registry"]["addresses"]}
    assert addresses["2025/document=form_w2/box=1/control=value"]["printed_label"] == (
        "Wages, tips, other compensation"
    )
    assert addresses[
        "2025/document=form_w2/box=12/row_template=entry/column=code"
    ]["printed_label"] == "Code"
    assert addresses[
        "2025/document=form_w2/table=state_local/row_template=jurisdiction/column=21"
    ]["printed_label"] == "Locality name"


@pytest.mark.m15r
def test_intake_runtime_facts_have_one_address_per_control(information_campaign) -> None:
    payload = information_campaign["form_13614_c_2025"]
    bindings = payload["widget_bindings"]["bindings"]
    assert len(bindings) == 297
    assert len({item["field_name"] for item in bindings}) == 297
    addresses = {item["address_id"]: item for item in payload["registry"]["addresses"]}
    assert all(addresses[item["address_id"]]["path"][-2] == {"kind": "section", "token": "intake"} for item in bindings)
    assert any(addresses[item["address_id"]]["kind"] == "option" for item in bindings)


@pytest.mark.m15r
def test_information_routes_retain_authored_provenance(information_campaign) -> None:
    for document_id, payload in information_campaign.items():
        field_map = yaml.safe_load(
            (ROOT / "graph/2025/field_maps" / f"{document_id}.yaml").read_text(encoding="utf-8")
        )
        dispositions = {item["field_name"]: item for item in field_map["field_dispositions"]}
        assert {item["field_name"] for item in payload["widget_bindings"]["bindings"]} == set(payload["field_addresses"])
        assert set(payload["field_addresses"]) <= set(dispositions)
        for field_name, address_id in payload["field_addresses"].items():
            disposition = dispositions[field_name]
            assert disposition["address_id"] == address_id
            assert disposition.get("source_ref") or disposition.get("runtime_fact_ref")
        for field_name in set(dispositions) - set(payload["field_addresses"]):
            assert dispositions[field_name]["population_policy"] in {
                "user_entered", "imported", "copied", "computed", "decision_required",
                "intentionally_blank", "unsupported",
            }
