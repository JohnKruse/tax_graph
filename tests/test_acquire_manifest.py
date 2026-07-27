from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tax_graph.acquire.manifest import IRS_PDF_URL_RE, load_manifest, validate_manifest_data


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m3
def test_manifest_loads_seeded_capital_gains_docs():
    manifest = load_manifest(root=ROOT)

    assert manifest.tax_year == 2025
    assert len(manifest.documents) == 21
    assert set(manifest.by_document_id()) == {
        "form_8949_2025",
        "instructions_form_8949_2025",
        "schedule_d_2025",
        "instructions_schedule_d_2025",
        "form_1040_2025",
        "instructions_form_1040_2025",
        "schedule_1_2025",
        "schedule_1a_2025",
        "schedule_2_2025",
        "schedule_3_2025",
        "schedule_a_2025",
        "instructions_schedule_a_2025",
        "schedule_b_2025",
        "instructions_schedule_b_2025",
        "form_6251_2025",
        "instructions_form_6251_2025",
        "form_1099b_2025",
        "form_w2_2025",
        "form_1099_int_2025",
        "form_1099_div_2025",
        "form_13614_c_2025",
    }


@pytest.mark.m3
def test_manifest_entries_validate_against_schema():
    data = yaml.safe_load((ROOT / "config" / "manifest.yaml").read_text(encoding="utf-8"))

    validate_manifest_data(data, root=ROOT)


@pytest.mark.m3
def test_manifest_urls_match_stable_irs_pdf_pattern():
    manifest = load_manifest(root=ROOT)

    assert all(IRS_PDF_URL_RE.match(entry.url) for entry in manifest.documents)


@pytest.mark.m3
def test_manifest_loads_form_instruction_relationships():
    manifest = load_manifest(root=ROOT)
    entries = manifest.by_document_id()

    assert entries["form_8949_2025"].instructions_document_id == "instructions_form_8949_2025"
    assert entries["schedule_d_2025"].instructions_document_id == "instructions_schedule_d_2025"
    assert entries["form_1040_2025"].instructions_document_id == "instructions_form_1040_2025"
    assert entries["schedule_1_2025"].instructions_document_id == "instructions_form_1040_2025"
    assert entries["schedule_1a_2025"].instructions_document_id == "instructions_form_1040_2025"
    assert entries["schedule_2_2025"].instructions_document_id == "instructions_form_1040_2025"
    assert entries["schedule_3_2025"].instructions_document_id == "instructions_form_1040_2025"
    assert entries["schedule_a_2025"].instructions_document_id == "instructions_schedule_a_2025"
    assert entries["schedule_b_2025"].instructions_document_id == "instructions_schedule_b_2025"
    assert entries["form_6251_2025"].instructions_document_id == "instructions_form_6251_2025"
    assert entries["form_8949_2025"].expected_sha256 is not None
    assert entries["schedule_d_2025"].expected_sha256 is not None
    assert entries["form_1040_2025"].expected_sha256 is not None


@pytest.mark.m18
def test_manifest_loads_structured_instruction_urls():
    manifest = load_manifest(root=ROOT)

    instruction_urls = {
        entry.document_id: entry.instruction_url
        for entry in manifest.documents
        if entry.instruction_url
    }
    assert instruction_urls == {
        "instructions_form_1040_2025": "https://www.irs.gov/instructions/i1040gi",
        "instructions_form_6251_2025": "https://www.irs.gov/instructions/i6251",
        "instructions_form_8949_2025": "https://www.irs.gov/instructions/i8949",
        "instructions_schedule_a_2025": "https://www.irs.gov/instructions/i1040sca",
        "instructions_schedule_b_2025": "https://www.irs.gov/instructions/i1040sb",
        "instructions_schedule_d_2025": "https://www.irs.gov/instructions/i1040sd",
    }


@pytest.mark.m3
def test_manifest_rejects_duplicate_document_ids():
    data = yaml.safe_load((ROOT / "config" / "manifest.yaml").read_text(encoding="utf-8"))
    data["documents"].append(dict(data["documents"][0]))

    with pytest.raises(ValueError, match="duplicate manifest document_id"):
        validate_manifest_data(data, root=ROOT)


@pytest.mark.m3
def test_manifest_rejects_non_irs_pdf_url():
    data = yaml.safe_load((ROOT / "config" / "manifest.yaml").read_text(encoding="utf-8"))
    data["documents"][0]["url"] = "https://www.irs.gov/forms-pubs/about-form-8949"

    with pytest.raises(Exception, match="does not match|stable IRS PDF"):
        validate_manifest_data(data, root=ROOT)


@pytest.mark.m3
def test_manifest_rejects_missing_instruction_relationship():
    data = yaml.safe_load((ROOT / "config" / "manifest.yaml").read_text(encoding="utf-8"))
    data["documents"][0]["instructions_document_id"] = "missing_instructions_2025"

    with pytest.raises(ValueError, match="references missing instructions"):
        validate_manifest_data(data, root=ROOT)
