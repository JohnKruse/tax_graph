"""M20-S101 guards for maintenance ownership and tier/manifest drift."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tax_graph.acquire.corpus import reconcile_tier_manifest
from tax_graph.acquire.manifest import AcquisitionManifest, ManifestEntry, validate_manifest_data
from pilot.maintenance_report import build_refusal_report


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]


def _manifest_entry(document_id: str, *, region_of: str | None = None) -> ManifestEntry:
    if region_of:
        return ManifestEntry(
            document_id=document_id,
            kind="worksheet",
            region_of=region_of,
            region_title="Toy Worksheet",
            region_parent_sha256="a" * 64,
        )
    return ManifestEntry(
        document_id=document_id,
        kind="tax_form",
        ownership="project-maintained",
        url="https://www.irs.gov/pub/irs-prior/ftoy--2025.pdf",
    )


def test_live_manifest_marks_only_non_regions() -> None:
    data = yaml.safe_load((ROOT / "config" / "manifest.yaml").read_text(encoding="ascii"))
    entries = data["documents"]
    assert sum("ownership" in entry for entry in entries if "region" not in entry) == 26
    assert all("ownership" not in entry for entry in entries if "region" in entry)


def test_region_ownership_is_inherited_from_parent() -> None:
    manifest = AcquisitionManifest(
        tax_year=2025,
        documents=(
            _manifest_entry("instructions_toy_2025"),
            _manifest_entry("toy_worksheet_2025", region_of="instructions_toy_2025"),
        ),
    )

    assert manifest.owner_document_id("toy_worksheet_2025") == "instructions_toy_2025"
    assert manifest.ownership_for("toy_worksheet_2025") == "project-maintained"


def test_manifest_schema_requires_ownership_only_for_acquired_documents() -> None:
    schema = yaml.safe_load((ROOT / "schemas" / "manifest.schema.json").read_text(encoding="ascii"))
    missing_ownership = {
        "tax_year": 2025,
        "documents": [{
            "document_id": "form_toy_2025",
            "kind": "tax_form",
            "url": "https://www.irs.gov/pub/irs-prior/ftoy--2025.pdf",
        }],
    }
    with pytest.raises(Exception):
        validate_manifest_data(missing_ownership, root=ROOT)

    region_with_ownership = {
        "tax_year": 2025,
        "documents": [{
            "document_id": "worksheet_toy_2025",
            "kind": "worksheet",
            "ownership": "project-maintained",
            "region": {
                "source_document_id": "instructions_toy_2025",
                "title": "Toy Worksheet",
                "parent_sha256": "a" * 64,
            },
        }, {
            "document_id": "instructions_toy_2025",
            "kind": "instructions",
            "ownership": "project-maintained",
            "url": "https://www.irs.gov/pub/irs-prior/itoy--2025.pdf",
        }],
    }
    with pytest.raises(Exception):
        validate_manifest_data(region_with_ownership, root=ROOT)


def test_tier_guard_names_both_directions(tmp_path: Path) -> None:
    tier_path = tmp_path / "document_tiers.yaml"
    tier_path.write_text(
        yaml.safe_dump(
            {"tax_year": 2025, "tiers": {"T1": ["form_toy_2025", "tier_only_2025"]}},
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="ascii",
    )
    manifest = AcquisitionManifest(
        tax_year=2025,
        documents=(_manifest_entry("form_toy_2025"), _manifest_entry("manifest_only_2025")),
    )

    report = reconcile_tier_manifest(manifest, root=tmp_path, tier_path=tier_path)

    assert report.ok is False
    assert report.tier_not_in_manifest == ("tier_only_2025",)
    assert report.manifest_not_in_tier == ("manifest_only_2025",)
    assert "tier_only_2025" in report.format_report()
    assert "manifest_only_2025" in report.format_report()


def test_live_tier_and_manifest_inventories_are_reconciled() -> None:
    report = reconcile_tier_manifest(root=ROOT)

    assert report.ok is True
    assert report.tier_not_in_manifest == ()
    assert report.manifest_not_in_tier == ()
    assert len(report.manifest_document_ids) == 26


def _write_project_manifest(root: Path) -> None:
    (root / "config").mkdir(parents=True)
    (root / "schemas").mkdir()
    (root / "schemas" / "manifest.schema.json").write_text(
        (ROOT / "schemas" / "manifest.schema.json").read_text(encoding="ascii"),
        encoding="ascii",
    )
    (root / "config" / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "tax_year": 2025,
                "documents": [
                    {
                        "document_id": "form_toy_2025",
                        "kind": "tax_form",
                        "ownership": "project-maintained",
                        "url": "https://www.irs.gov/pub/irs-prior/ftoy--2025.pdf",
                    },
                    {
                        "document_id": "form_review_2025",
                        "kind": "tax_form",
                        "ownership": "review-cycle",
                        "url": "https://www.irs.gov/pub/irs-prior/freview--2025.pdf",
                    },
                ],
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="ascii",
    )
    (root / "config" / "document_tiers.yaml").write_text(
        yaml.safe_dump(
            {
                "tax_year": 2025,
                "core_documents": ["form_toy_2025"],
                "tiers": {"T1": ["form_toy_2025"], "review-cycle": ["form_review_2025"]},
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="ascii",
    )


def test_refusal_report_partitions_by_ownership_and_only_core_silent_refusal_fails(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _write_project_manifest(root)
    run = tmp_path / "run"
    run.mkdir()
    (run / "m20_s26_form_toy_2025_derive_cells_report.yaml").write_text(
        yaml.safe_dump(
            {
                "document_id": "form_toy_2025",
                "rows_detail": [
                    {"line": "1", "status": "error", "error": "missing operand"},
                    {"line": "2", "status": "error"},
                ],
                "denominator": {"anchors": [{"anchor": "3", "skip_reason": "no formula cue"}]},
            },
            sort_keys=False,
        ),
        encoding="ascii",
    )
    (run / "m20_s26_form_review_2025_derive_cells_report.yaml").write_text(
        yaml.safe_dump(
            {
                "document_id": "form_review_2025",
                "rows_detail": [{"line": "4", "status": "error", "error": "review later"}],
            },
            sort_keys=False,
        ),
        encoding="ascii",
    )

    report = build_refusal_report(run, root=root)

    assert report.ok is False
    assert [(item.document_id, item.reported, item.ownership) for item in report.records] == [
        ("form_review_2025", True, "review-cycle"),
        ("form_toy_2025", True, "project-maintained"),
        ("form_toy_2025", False, "project-maintained"),
        ("form_toy_2025", True, "project-maintained"),
    ]
    assert len(report.core_unreported) == 1
    assert "ownership=project-maintained" in report.format_report()
    assert "UNREPORTED" in report.format_report()


def test_refusal_report_inherits_region_ownership(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _write_project_manifest(root)
    data = yaml.safe_load((root / "config" / "manifest.yaml").read_text(encoding="ascii"))
    data["documents"].append(
        {
            "document_id": "worksheet_toy_2025",
            "kind": "worksheet",
            "region": {
                "source_document_id": "form_toy_2025",
                "title": "Toy Worksheet",
                "parent_sha256": "a" * 64,
            },
        }
    )
    (root / "config" / "manifest.yaml").write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=False),
        encoding="ascii",
    )
    run = tmp_path / "run"
    run.mkdir()
    (run / "worksheet-discovery-form_toy_2025.yaml").write_text(
        yaml.safe_dump(
            {
                "source_document_id": "form_toy_2025",
                "worksheets": [{
                    "document_id": "worksheet_toy_2025",
                    "status": "blocked",
                    "findings": [{"kind": "line_sequence_gap", "message": "line 2 missing"}],
                }],
            },
            sort_keys=False,
        ),
        encoding="ascii",
    )

    report = build_refusal_report(run, root=root)

    assert report.ok is True
    assert report.records[0].owner_document_id == "form_toy_2025"
    assert report.records[0].ownership == "project-maintained"
