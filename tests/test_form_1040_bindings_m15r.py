from __future__ import annotations

import copy
from pathlib import Path

import pytest

from tax_graph.addressing import load_address_artifacts
from tax_graph.io.loader import load_graph
from tax_graph.output.field_maps import load_field_maps
from workbench.semantics import format_node_semantics


ROOT = Path(__file__).resolve().parents[1]


def _index():
    graph = load_graph(2025, ROOT, include_extensions=False)
    ids = {"documents": "document_id", "nodes": "node_id", "tables": "table_id", "edges": "edge_id", "rules": "rule_id", "citations": "citation_id", "decisions": "decision_id", "routing_edges": "routing_id", "triggers": "trigger_id", "expectations": "expectation_id"}
    index = {}
    for kind, items in graph.objects.items():
        object_type = kind[:-1] if kind.endswith("s") else kind
        for item in items:
            index[(object_type, str(item[ids[kind]]))] = copy.deepcopy(item)
    artifacts = load_address_artifacts(2025, ROOT)
    for address in artifacts.addresses:
        index[("address", address.address_id)] = address.raw
    for binding in artifacts.node_bindings:
        index[("node_binding", binding["node_id"])] = binding
    return index


@pytest.mark.m15r
def test_line_1z_uses_bound_addresses_under_hostile_label_mutations() -> None:
    index = _index()
    for (kind, _), item in index.items():
        if kind == "node":
            item["label"] = "Hostile W-2 box 2, Schedule 1 lines 26 and 31"
    formatted = format_node_semantics("form_1040_2025_root_line_z", index)
    assert formatted is not None
    assert formatted.summary == "Add lines 1a + 1b + 1c + 1d + 1e + 1f + 1g + 1h"


@pytest.mark.m15r
def test_every_1040_widget_has_binding_or_explicit_exemption() -> None:
    field_map = next(item for item in load_field_maps(2025, ROOT) if item["document_id"] == "form_1040_2025")
    artifacts = load_address_artifacts(2025, ROOT)
    bound = {item["field_name"] for item in artifacts.widget_bindings if item["document_id"] == "form_1040_2025"}
    exempt = {item["field_name"] for item in field_map["field_dispositions"] if not item.get("address_id")}
    assert len(bound) == 199 and not exempt
    assert bound | exempt == {item["field_name"] for item in field_map["field_dispositions"]}
