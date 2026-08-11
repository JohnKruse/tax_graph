from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from tax_graph.io.loader import load_graph


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "m15r"


def _schema(name: str) -> dict[str, object]:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def _registry() -> dict[str, object]:
    return yaml.safe_load((FIXTURE / "address_registry.yaml").read_text(encoding="utf-8"))


@pytest.mark.m15r
def test_representative_address_vocabulary_is_schema_valid() -> None:
    registry = _registry()
    jsonschema.Draft202012Validator(_schema("address_registry.schema.json")).validate(registry)
    kinds = {item["kind"] for item in registry["addresses"]}
    roles = {item["control_role"] for item in registry["addresses"]}
    assert {"document", "control", "option", "column"} <= kinds
    assert {"amount", "description", "checkbox", "radio"} <= roles


@pytest.mark.m15r
@pytest.mark.parametrize("mutation", [
    lambda item: item.update(extra="not allowed"),
    lambda item: item.update(parent_address_id=None),
    lambda item: item.update(control_role="amount", kind="line"),
    lambda item: item["path"].append({"kind": "line", "token": "Not ASCII"}),
    lambda item: item.update(status="reviewed"),
])
def test_registry_schema_rejects_invalid_shape_role_status_and_tokens(mutation) -> None:
    registry = copy.deepcopy(_registry())
    item = registry["addresses"][1]
    mutation(item)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(_schema("address_registry.schema.json")).validate(registry)


@pytest.mark.m15r
def test_binding_and_reference_schemas_are_strict() -> None:
    binding = {"schema_version": 1, "year": 2025, "document_id": "form_1040_2025", "binding_kind": "node", "bindings": [{"node_id": "form_1040_2025_line_1a", "address_id": "2025/form_1040/line=1/item=a/control=amount", "role": "value", "status": "exact"}]}
    reference = {"schema_version": 1, "year": 2025, "document_id": "form_1040_2025", "references": [{"reference_id": "ref_1", "source_address_id": "2025/form_1040/line=1/item=z/control=amount", "target_document_id": "schedule_1_2025", "target_official_ref": "26", "status": "unresolved", "evidence_hash": "b" * 64}]}
    jsonschema.validate(binding, _schema("address_binding.schema.json"))
    jsonschema.validate(reference, _schema("address_reference.schema.json"))
    binding["bindings"][0]["surprise"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(binding, _schema("address_binding.schema.json"))


@pytest.mark.m15r
def test_r1_baseline_matches_unmodified_project_graph() -> None:
    baseline = json.loads((FIXTURE / "baseline.json").read_text(encoding="utf-8"))
    graph = load_graph(2025, ROOT, include_extensions=False)
    # R1 freezes the pre-worksheet address graph. S100 intentionally promotes
    # worksheet-owned objects, which have no address bindings, so keep them
    # out of this historical contract instead of changing its baseline.
    worksheet_document_ids = {
        item["document_id"]
        for item in graph.items("documents")
        if item.get("document_type") == "worksheet"
    }
    graph_counts = {
        kind: sum(
            item.get("document_id") not in worksheet_document_ids
            for item in items
        )
        for kind, items in graph.objects.items()
    }
    assert graph_counts == baseline["graph_counts"]
    counts = {}
    for path in sorted((ROOT / "graph" / "2025" / "field_inventories").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        counts[path.stem] = len(payload["fields"])
    assert counts == baseline["field_inventory_counts"]
    assert baseline["legacy_line_disagreement_count"] == 80
