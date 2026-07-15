from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from tax_graph.addressing import CORE_RETURN_DOCUMENTS, build_address_campaign
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
    paths = [item["path"] for item in payload["registry"]["addresses"]]
    assert any(
        [part["kind"] for part in path[-3:]] == ["table", "row_template", "column"]
        and path[-1]["token"] == "d"
        for path in paths
    )
    bindings = payload["widget_bindings"]["bindings"]
    assert len({item["address_id"] for item in bindings}) < len(bindings)


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
