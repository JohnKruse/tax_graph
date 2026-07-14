"""M15 complete AcroForm field-disposition contract tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from tax_graph.output.field_maps import (
    migrate_field_dispositions,
    validate_exposed_pdf_fields,
    validate_field_maps,
)


ROOT = Path(__file__).resolve().parents[1]


def _fixture_root(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    (tmp_path / "schemas").mkdir()
    (tmp_path / "graph/2025/field_maps").mkdir(parents=True)
    (tmp_path / "graph/2025/field_inventories").mkdir(parents=True)
    (tmp_path / "schemas/field_map.schema.json").write_text(
        (ROOT / "schemas/field_map.schema.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    inventory = {
        "fields": [
            {"field_name": "f_text", "field_type": "Text", "page": 1},
            {"field_name": "f_check", "field_type": "CheckBox", "page": 1},
        ]
    }
    (tmp_path / "graph/2025/field_inventories/form_test_2025.json").write_text(
        json.dumps(inventory), encoding="utf-8"
    )
    field_map: dict[str, object] = {
        "schema_version": 2,
        "tax_year": 2025,
        "document_id": "form_test_2025",
        "inventory": "graph/2025/field_inventories/form_test_2025.json",
        "mappings": [
            {"slot": "wages", "field_name": "f_text", "format": "dollars", "node_id": "form_test_2025_line_1"}
        ],
        "excluded_nodes": [],
        "frontier_fields": [],
        "field_dispositions": [
            {
                "field_name": "f_text",
                "label": "Line 1 wages",
                "population_policy": "computed",
                "value_format": "dollars",
                "node_id": "form_test_2025_line_1",
            },
            {
                "field_name": "f_check",
                "label": "Unsupported election",
                "population_policy": "unsupported",
                "value_format": "checkbox",
                "reason": "Election logic is not modeled.",
                "downstream_effect": "The return cannot claim this election.",
                "missing_capability": "A cited qualification branch is required.",
            },
        ],
    }
    return tmp_path, field_map


def _write_map(root: Path, field_map: dict[str, object]) -> list[str]:
    (root / "graph/2025/field_maps/form_test_2025.yaml").write_text(
        yaml.safe_dump(field_map, sort_keys=False), encoding="utf-8"
    )
    return validate_field_maps(
        "2025", root, node_ids={"form_test_2025_line_1"}, frontier_ids=set()
    )


@pytest.mark.m15
def test_complete_field_disposition_fixture_is_valid(tmp_path: Path) -> None:
    root, field_map = _fixture_root(tmp_path)
    assert _write_map(root, field_map) == []


@pytest.mark.m15
@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda item: item["field_dispositions"].pop(), "field has no disposition"),
        (lambda item: item["field_dispositions"].append(copy.deepcopy(item["field_dispositions"][0])), "duplicate field disposition"),
        (lambda item: item["field_dispositions"][0].update(field_name="unknown"), "disposition references unknown field"),
    ],
)
def test_missing_duplicate_and_unknown_dispositions_fail(
    tmp_path: Path, mutation: object, message: str
) -> None:
    root, field_map = _fixture_root(tmp_path)
    mutation(field_map)  # type: ignore[operator]
    assert any(message in error for error in _write_map(root, field_map))


@pytest.mark.m15
def test_unsupported_requires_consequence_and_capability(tmp_path: Path) -> None:
    root, field_map = _fixture_root(tmp_path)
    unsupported = field_map["field_dispositions"][1]  # type: ignore[index]
    unsupported.pop("downstream_effect")
    errors = _write_map(root, field_map)
    assert any("schema" in error and "downstream_effect" in error for error in errors)


@pytest.mark.m15
@pytest.mark.parametrize(
    "policy",
    ["copied", "computed"],
)
def test_graph_operation_policy_requires_node_ref(tmp_path: Path, policy: str) -> None:
    root, field_map = _fixture_root(tmp_path)
    disposition = field_map["field_dispositions"][0]  # type: ignore[index]
    disposition["population_policy"] = policy
    disposition.pop("node_id")
    errors = _write_map(root, field_map)
    assert any("schema" in error and "node_id" in error for error in errors)


@pytest.mark.m15
def test_migration_is_idempotent_and_never_guesses_unmapped_policy(tmp_path: Path) -> None:
    root, field_map = _fixture_root(tmp_path)
    field_map.pop("schema_version")
    field_map.pop("field_dispositions")
    field_map["mappings"] = [
        {"slot": "taxpayer_name", "field_name": "f_text", "format": "text", "identity_slot": "taxpayer_name"}
    ]
    _write_map(root, field_map)
    target = root / "worklist.yaml"
    first = migrate_field_dispositions("2025", root, output_path=target)
    first_text = target.read_text(encoding="utf-8")
    second = migrate_field_dispositions("2025", root, output_path=target)
    assert target.read_text(encoding="utf-8") == first_text
    assert first == second
    report = first.documents[0]
    assert report.proposed_dispositions[0]["population_policy"] == "user_entered"
    assert report.authored_work == (
        {
            "field_name": "f_check",
            "field_type": "CheckBox",
            "page": 1,
            "reason": "unclassified legacy inventory field",
        },
    )


@pytest.mark.m15
def test_real_pdf_widget_preflight_detects_missing_maps() -> None:
    errors = validate_exposed_pdf_fields("2025", ROOT)
    assert any("form_w2_2025" in error and "missing committed field map" in error for error in errors)
    assert not any("instructions_form_1040_2025" in error for error in errors)
