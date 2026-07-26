"""Focused M19-S2 tests for non-positional review-unit identity."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import workbench.manifest as manifest_module
from workbench.artifacts import ArtifactBundle, SqliteGraphArtifact
from workbench.manifest import (
    ManifestError,
    _validate_unit_id_collisions,
    build_manifest,
    derive_unit_id,
)
from workbench.schema import validate_session_state
from workbench.sessions import default_session, migrate_session_reviews


def _bundle(root: Path) -> ArtifactBundle:
    graph_path = root / "graph.sqlite"
    graph_path.write_bytes(b"synthetic graph")
    geometry_path = root / "node_geometry.json"
    geometry_path.write_text('{"tax_year": 2025, "entries": []}\n', encoding="utf-8")
    queue_path = root / "deferred_review.yaml"
    queue_path.write_text("tax_year: 2025\nentries: []\n", encoding="utf-8")
    field_map_path = root / "field_map.yaml"
    field_map_path.write_text(
        yaml.safe_dump(
            {
                "field_dispositions": [
                    {
                        "field_name": "field_addressed",
                        "label": "Addressed amount",
                        "address_id": "2025/document=form_test/section=income/control=amount",
                        "population_policy": "user_entered",
                        "value_format": "currency",
                    },
                    {
                        "field_name": "field_unaddressed",
                        "label": "Unaddressed amount",
                        "population_policy": "user_entered",
                        "value_format": "currency",
                    },
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return ArtifactBundle(
        root=root,
        tax_year=2025,
        graph=SqliteGraphArtifact(
            path=graph_path,
            tax_year=2025,
            schema_version=1,
            content_hash="a" * 64,
            objects_by_kind={kind: () for kind in manifest_module.GRAPH_OBJECT_KINDS},
            tax_table=(),
        ),
        geometry={"tax_year": 2025, "entries": []},
        review_queue={
            "tax_year": 2025,
            "entries": [
                {
                    "queue_id": "field_map_review_form_test",
                    "document_id": "form_test_2025",
                    "kind": "field_map_review",
                    "status": "pending",
                    "summary": "Synthetic field map review.",
                    "review_scope": {
                        "object_refs": [
                            {
                                "object_type": "field_control",
                                "object_id": "field_addressed",
                                "source_path": field_map_path.name,
                                "role": "primary",
                            },
                            {
                                "object_type": "field_control",
                                "object_id": "field_unaddressed",
                                "source_path": field_map_path.name,
                                "role": "primary",
                            },
                        ]
                    },
                }
            ],
        },
        drafts={},
        metrics={},
        nversion_reports={},
        mined_examples={},
        pdfs=(),
    )


@pytest.mark.m15
def test_two_manifest_builds_are_stable_and_mark_unaddressed_units(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = _bundle(tmp_path)
    monkeypatch.setattr(manifest_module, "load_artifact_bundle", lambda *args, **kwargs: bundle)

    first = build_manifest(
        tmp_path,
        2025,
        geometry_path=tmp_path / "node_geometry.json",
        queue_path=tmp_path / "deferred_review.yaml",
    )
    second = build_manifest(
        tmp_path,
        2025,
        geometry_path=tmp_path / "node_geometry.json",
        queue_path=tmp_path / "deferred_review.yaml",
    )

    assert first == second
    units = first["entries"][0]["units"]
    addressed, unaddressed = units
    assert addressed["address_status"] == "addressed"
    assert addressed["identity_source"] == "address_id"
    assert addressed["unit_id"].startswith("unit_address_")
    assert unaddressed["address_status"] == "unaddressed"
    assert unaddressed["identity_source"] == "field_name"
    assert "address_id" not in unaddressed
    assert unaddressed["unit_id"].startswith("unit_unaddressed_")
    assert all("ref_" not in unit["unit_id"] and "loc_" not in unit["unit_id"] for unit in units)


@pytest.mark.m15
def test_identity_qualifier_distinguishes_same_address_reviews() -> None:
    common = {
        "address_id": "2025/document=form_test/section=income/control=amount",
        "identity_source": "address_id",
        "document_id": "form_test_2025",
        "field_name": "",
        "object_type": "field_control",
        "object_id": "field",
    }
    primary = derive_unit_id(**common, review_kind="field_map_review", role="primary")
    expected = derive_unit_id(**common, review_kind="field_map_review", role="expected")
    assert primary != expected
    assert primary.isascii() and expected.isascii()
    assert "ref_" not in primary and "loc_" not in primary


@pytest.mark.m15
def test_duplicate_and_positional_ids_fail_closed() -> None:
    unit = {
        "unit_id": "unit_address_abc",
        "address_id": "2025/document=form_test/section=income/control=amount",
        "review_kind": "field_map_review",
        "identity_source": "address_id",
        "identity_qualifier": "field_map_review:primary:field_control",
        "object_refs": [{"object_type": "address", "object_id": "2025/document=form_test/section=income/control=amount"}],
    }
    with pytest.raises(ManifestError, match="duplicate review unit identity"):
        _validate_unit_id_collisions([{"units": [unit, dict(unit)]}])
    with pytest.raises(ManifestError, match="positional"):
        _validate_unit_id_collisions([{"units": [{**unit, "unit_id": "queue_ref_0000_loc_00_field"}]}])


def _review_unit(unit_id: str, address_id: str, *, role: str = "primary") -> dict[str, object]:
    return {
        "unit_id": unit_id,
        "review_kind": "field_map_review",
        "identity_source": "address_id",
        "identity_qualifier": f"field_map_review:{role}:field_control",
        "identity_document_id": "form_test_2025",
        "address_id": address_id,
        "object_refs": [
            {"object_type": "address", "object_id": address_id},
            {"object_type": "field_control", "object_id": "field_amount"},
        ],
    }


@pytest.mark.m15
def test_certain_migration_preserves_review_and_records_alias() -> None:
    address = "2025/document=form_test/section=income/control=amount"
    old = _review_unit("queue_ref_0000_loc_00_field_amount", address)
    new = _review_unit(
        derive_unit_id(
            address_id=address,
            identity_source="address_id",
            document_id="form_test_2025",
            field_name="",
            review_kind="field_map_review",
            role="primary",
            object_type="field_control",
            object_id="field_amount",
        ),
        address,
    )
    payload = {
        "unit_reviews": {
            old["unit_id"]: {
                "status": "approved",
                "note": "Reviewed before rebuild.",
                "updated_at": "2026-07-26T10:00:00+00:00",
            }
        }
    }

    migrated = migrate_session_reviews(payload, [old], [new])

    new_id = new["unit_id"]
    assert migrated["unit_reviews"][new_id]["status"] == "approved"
    assert migrated["orphaned_unit_reviews"] == {}
    assert new["aliases"] == [old["unit_id"]]


@pytest.mark.m15
def test_uncertain_migration_orphans_review_instead_of_guessing() -> None:
    address = "2025/document=form_test/section=income/control=amount"
    old = _review_unit("queue_ref_0000_loc_00_field_amount", address)
    new_a = _review_unit("unit_a", address, role="primary")
    new_b = _review_unit("unit_b", address, role="primary")
    payload = {
        **default_session(2025, "queue_1", "a" * 64, [new_a, new_b]),
        "unit_reviews": {
            old["unit_id"]: {
                "status": "approved",
                "note": "Do not move this without certainty.",
                "updated_at": "2026-07-26T10:00:00+00:00",
            }
        }
    }

    migrated = migrate_session_reviews(payload, [old], [new_a, new_b])

    assert migrated["unit_reviews"] == {}
    orphan = migrated["orphaned_unit_reviews"][old["unit_id"]]
    assert orphan["status"] == "orphaned"
    assert orphan["reason"] == "ambiguous identity match"
    assert orphan["note"] == "Do not move this without certainty."
    validate_session_state(migrated)
