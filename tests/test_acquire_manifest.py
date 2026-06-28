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
    assert len(manifest.documents) == 7
    assert set(manifest.by_document_id()) == {
        "form_8949_2025",
        "instructions_form_8949_2025",
        "schedule_d_2025",
        "instructions_schedule_d_2025",
        "form_1040_2025",
        "instructions_form_1040_2025",
        "form_1099b_2025",
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
