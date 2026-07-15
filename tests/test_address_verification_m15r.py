from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from tax_graph.addressing import AddressArtifacts, AddressError, load_address_artifacts
from tax_graph.addressing.registry import _validate_artifacts


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m15r
@pytest.mark.parametrize("case", yaml.safe_load((ROOT / "tax_graph/drills/address_drill_catalog.yaml").read_text(encoding="utf-8")))
def test_address_defect_classes_fail_at_binding_or_reference_layer(case: dict[str, str]) -> None:
    defect = case["defect"]
    original = load_address_artifacts(2025, ROOT)
    widgets = [dict(item) for item in original.widget_bindings]
    nodes = [dict(item) for item in original.node_bindings]
    references = [dict(item) for item in original.references]
    addresses = list(original.addresses)
    if defect == "swap_1b_1e":
        a = next(item for item in nodes if item["node_id"].endswith("line_1b"))
        b = next(item for item in nodes if item["node_id"].endswith("line_1e"))
        a["address_id"], b["address_id"] = b["address_id"], a["address_id"]
    elif defect == "amount_to_checkbox":
        item = next(item for item in nodes if item["node_id"].endswith("line_1b"))
        item["address_id"] = next(address.address_id for address in addresses if address.control_role == "checkbox")
    elif defect == "duplicate_option":
        option = next(address for address in addresses if "/option=" in address.address_id)
        addresses.append(option)
    else:
        references.append({"reference_id": "missing", "source_address_id": addresses[0].address_id,
                           "resolved_address_id": "2025/document=missing/line=1/control=amount"})
    mutated = AddressArtifacts(tuple(addresses), tuple(widgets), tuple(nodes), tuple(references))
    with pytest.raises(AddressError):
        _validate_artifacts(mutated)
