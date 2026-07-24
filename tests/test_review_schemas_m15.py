"""Schema and validation-helper tests for M15 Step 1."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from workbench.schema import (
    SchemaValidationError,
    load_schema,
    validate_review_expression,
    validate_review_manifest,
    validate_review_unit,
    validate_session_state,
)


ROOT = Path(__file__).resolve().parents[1]


def _location() -> dict[str, object]:
    return {
        "document_id": "form_1040_2025",
        "source_pdf_hash": "a" * 64,
        "page": 1,
        "rect": [1, 2, 3, 4],
        "locator_text": "Line 7",
    }


def _unit() -> dict[str, object]:
    return {
        "queue_id": "queue_1",
        "unit_id": "queue_1_line_7",
        "review_kind": "promotion_review",
        "required": True,
        "object_refs": [{"object_type": "node", "object_id": "form_1040_2025_line_7"}],
        "official_location": _location(),
        "analog_placement": {
            "page": 1,
            "anchor_rect": [1, 2, 3, 4],
            "lane": 0,
            "display_order": 0,
        },
        "semantic_class": "copy",
        "summary": "Copied from Schedule 1 line 10",
        "display_name": "Capital gain or loss",
        "display_name_provenance": "authored_address",
        "official_locator": "Form 1040 line 7",
        "review_prompt": "Confirm the copied source and destination field.",
        "expression": {
            "kind": "copy",
            "source": {
                "kind": "reference",
                "ref": {"object_type": "node", "object_id": "schedule_1_2025_line_10"},
            },
        },
        "source_refs": [
            {
                "direction": "source",
                "object_type": "node",
                "object_id": "schedule_1_2025_line_10",
            }
        ],
        "citation_refs": ["citation_1"],
        "witness_refs": ["pytest_green"],
        "confidence": 1,
        "trust": "machine_agreed",
        "coverage": {"state": "pending", "required_for_confirm": True},
    }


@pytest.mark.m15
def test_all_step_one_schemas_load_and_validate_their_schema() -> None:
    for name in ("review_manifest", "review_unit", "review_expression", "session_state"):
        assert load_schema(name)["$id"] == f"{name}.schema.json"


@pytest.mark.m15
def test_minimal_valid_projection_fixtures() -> None:
    expression = {
        "kind": "sum",
        "operands": [
            {"kind": "reference", "ref": {"object_type": "node", "object_id": "line_1"}},
            {"kind": "literal", "value": 2},
        ],
    }
    validate_review_expression(expression)
    validate_review_unit(_unit())
    validate_review_manifest(
        {
            "tax_year": 2025,
            "manifest_hash": "b" * 64,
            "entries": [
                {
                    "queue_id": "queue_1",
                    "review_kind": "promotion_review",
                    "status": "pending",
                    "units": [_unit()],
                }
            ],
        }
    )
    validate_session_state(
        {
            "tax_year": 2025,
            "queue_id": "queue_1",
            "manifest_hash": "d" * 64,
            "current_unit_id": "queue_1_line_7",
            "page": 1,
            "selection": {"unit_id": "queue_1_line_7", "side": "official", "rect": [1, 2, 3, 4]},
            "zoom": 1,
            "notes": "",
            "elapsed_active_seconds": 0,
            "visited_unit_ids": [],
            "unit_reviews": {
                "queue_1_line_7": {
                    "status": "approved",
                    "note": "Checked the cited line.",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


@pytest.mark.m15
@pytest.mark.parametrize(
    ("name", "payload"),
    [
        ("review_expression", {"kind": "copy", "unknown": True}),
        ("review_unit", {**_unit(), "unknown": True}),
        (
            "review_manifest",
            {"tax_year": 2025, "manifest_hash": "c" * 64, "entries": [{"units": []}]},
        ),
        (
            "session_state",
            {
                "tax_year": 2025,
                "queue_id": "queue_1",
                "manifest_hash": "d" * 64,
                "current_unit_id": None,
                "page": 1,
                "selection": None,
                "zoom": 1,
                "notes": "",
                "elapsed_active_seconds": -1,
                "visited_unit_ids": [],
                "updated_at": "not-a-date",
            },
        ),
    ],
)
def test_invalid_projection_fixtures_fail_closed(name: str, payload: dict[str, object]) -> None:
    with pytest.raises(SchemaValidationError):
        if name == "review_expression":
            validate_review_expression(payload)
        elif name == "review_unit":
            validate_review_unit(payload)
        elif name == "review_manifest":
            validate_review_manifest(payload)
        else:
            validate_session_state(payload)


@pytest.mark.m15
def test_schema_dir_can_be_overridden_for_artifact_validation(tmp_path: Path) -> None:
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    for name in ("review_manifest", "review_unit", "review_expression", "session_state"):
        source = ROOT / "schemas" / f"{name}.schema.json"
        (schema_dir / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    assert load_schema("review_unit", schema_dir=schema_dir)["title"] == "Tax Graph review workbench unit"
    validate_review_unit(_unit(), schema_dir=schema_dir)
