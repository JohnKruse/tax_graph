from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tax_graph.acquire.manifest import IRS_PDF_URL_RE, load_manifest, validate_manifest_data


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m3
def test_manifest_loads_seeded_source_docs():
    manifest = load_manifest(root=ROOT)

    assert manifest.tax_year == 2025
    assert len(manifest.documents) == 45
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
        "form_1116_2025",
        "instructions_form_1116_2025",
        "publication_514_2025",
        "form_1099b_2025",
        "form_w2_2025",
        "form_1099_int_2025",
        "form_1099_div_2025",
        "form_13614_c_2025",
        "form_2441_2025",
        "instructions_form_2441_2025",
        "simplified_method_worksheet_2025",
        "social_security_benefits_worksheet_2025",
        "standard_deduction_worksheet_for_dependents_2025",
        "qualified_dividends_and_capital_gain_tax_worksheet_2025",
        "state_and_local_income_tax_refund_worksheet_2025",
        "self_employed_health_insurance_deduction_worksheet_2025",
        "ira_deduction_worksheet_2025",
        "student_loan_interest_deduction_worksheet_2025",
        "qualified_tips_from_more_than_one_employer_worksheet_keep_for_your_records_2025",
        "multiple_trades_or_businesses_worksheet_keep_for_your_records_2025",
        "qualified_overtime_compensation_from_more_than_one_employer_worksheet_keep_for_your_records_2025",
        "qualified_overtime_compensation_from_more_than_one_payor_worksheet_keep_for_your_records_2025",
        "negative_form_8978_adjustment_worksheet_schedule_2_2025",
        "capital_loss_carryover_worksheet_2025",
        "28_rate_gain_worksheet_2025",
        "unrecaptured_section_1250_gain_worksheet_2025",
        "schedule_d_tax_worksheet_2025",
        "credit_limit_worksheet_2025",
        "worksheet_a_worksheet_for_2024_expenses_paid_in_2025_2025",
    }


@pytest.mark.m3
def test_manifest_entries_validate_against_schema():
    data = yaml.safe_load((ROOT / "config" / "manifest.yaml").read_text(encoding="utf-8"))

    validate_manifest_data(data, root=ROOT)


@pytest.mark.m3
def test_manifest_urls_match_stable_irs_pdf_pattern():
    manifest = load_manifest(root=ROOT)

    assert all(
        entry.url is None or IRS_PDF_URL_RE.match(entry.url)
        for entry in manifest.documents
    )


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
    assert entries["form_2441_2025"].instructions_document_id == "instructions_form_2441_2025"
    assert entries["form_8949_2025"].expected_sha256 is not None
    assert entries["schedule_d_2025"].expected_sha256 is not None
    assert entries["form_1040_2025"].expected_sha256 is not None
    assert entries["form_2441_2025"].expected_sha256 == (
        "6c3c2d19163fa4c4de829abf9a89b43f08b4f4f3cb169740fc7da43e914269ce"
    )
    assert entries["instructions_form_2441_2025"].expected_sha256 == (
        "86f0669e78b1dc00bfb99e956673d4fccee9e40d6c44d53623dd08e62567fd39"
    )
    region = entries["qualified_dividends_and_capital_gain_tax_worksheet_2025"]
    assert region.is_region
    assert region.url is None
    assert region.region_of == "instructions_form_1040_2025"
    assert region.region_title == "Qualified Dividends and Capital Gain Tax Worksheet"
    assert region.region_parent_sha256 == (
        "0a1a74db99d1f481b49c6d59a928dbfc16f10c640e1dd502c72f3ac816e21ec7"
    )


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
        "instructions_form_2441_2025": "https://www.irs.gov/instructions/i2441",
        "instructions_form_1116_2025": "https://www.irs.gov/instructions/i1116",
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
