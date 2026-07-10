"""M12 formatting-only PDF fill tests."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from tax_graph.engine import Engine, Graph, TABLE_FACTS_KEY
from tax_graph.output import build_field_values, fill_official_pdf, load_field_maps


ROOT = Path(__file__).resolve().parents[1]


def _execute(document: dict) -> object:
    facts = {item["node_id"]: item.get("value") for item in document.get("facts", [])}
    facts["filing_status"] = document["filing_status"]
    facts[TABLE_FACTS_KEY] = document.get("tables", [])
    return Engine(Graph(2025, root=ROOT, source="yaml")).execute(facts)


def _map(document_id: str) -> dict:
    return next(item for item in load_field_maps(2025, ROOT) if item["document_id"] == document_id)


@pytest.mark.m12
@pytest.mark.parametrize("scenario", ["qdcgt", "table"])
def test_form_1040_field_value_goldens(scenario: str) -> None:
    if scenario == "qdcgt":
        document = {
            "tax_year": 2025,
            "filing_status": "single",
            "facts": [
                {"node_id": "form_1040_2025_root_line_1a", "value": 60000},
                {"node_id": "form_1040_2025_root_line_3a", "value": 5000},
                {"node_id": "form_1040_2025_deduction_method", "value": "standard"},
                {"node_id": "schedule_b_2025_root_line_6", "value": 5000},
                {"node_id": "schedule_d_2025_line_7_net_st", "value": 0},
            ],
            "tables": [],
        }
    else:
        document = yaml.safe_load((ROOT / "examples/taxable_income_basic/facts.yaml").read_text())
    values, notes = build_field_values(_map("form_1040_2025"), _execute(document), document, root=ROOT)
    golden = json.loads((ROOT / f"tests/fixtures/output/form_1040_{scenario}_fields.json").read_text())
    assert values == golden
    assert any(item["frontier_id"] == "deferred_form_1040_2025_total_tax_chain" for item in notes)
    assert "topmostSubform[0].Page2[0].f2_09[0]" not in values


@pytest.mark.m12
def test_8949_repeatable_row_maps_to_physical_slot() -> None:
    document = yaml.safe_load((ROOT / "examples/taxable_income_basic/facts.yaml").read_text())
    values, _notes = build_field_values(_map("form_8949_2025"), _execute(document), document, root=ROOT)
    assert values["topmostSubform[0].Page2[0].Table_Line1_Part2[0].Row1[0].f2_06[0]"] == "12000"
    assert values["topmostSubform[0].Page2[0].Table_Line1_Part2[0].Row1[0].f2_07[0]"] == "10000"
    assert values["topmostSubform[0].Page2[0].Table_Line1_Part2[0].Row1[0].f2_10[0]"] == "2000"


@pytest.mark.m12
def test_identity_fields_fill_only_when_supplied() -> None:
    document = yaml.safe_load((ROOT / "examples/taxable_income_basic/facts.yaml").read_text())
    document["identity"] = {"taxpayer_first_name": "Ada", "taxpayer_last_name": "Lovelace"}
    values, _notes = build_field_values(_map("form_1040_2025"), _execute(document), document, root=ROOT)
    assert values["topmostSubform[0].Page1[0].f1_14[0]"] == "Ada"
    assert values["topmostSubform[0].Page1[0].f1_15[0]"] == "Lovelace"
    assert "topmostSubform[0].Page1[0].f1_16[0]" not in values


@pytest.mark.m12
def test_real_official_pdf_round_trip_when_cached(tmp_path: Path) -> None:
    source = ROOT / ".cache/raw/2025/form_1040_2025.pdf"
    if not source.exists():
        pytest.skip("official cached PDF is required for the gated round-trip")
    document = yaml.safe_load((ROOT / "examples/taxable_income_basic/facts.yaml").read_text())
    values, notes = build_field_values(_map("form_1040_2025"), _execute(document), document, root=ROOT)
    filled = fill_official_pdf(
        source,
        tmp_path / "form_1040_2025.filled.pdf",
        document_id="form_1040_2025",
        field_values=values,
        blank_with_note=notes,
    )
    assert filled.field_values == values
    assert filled.output_path.exists()


@pytest.mark.m12
def test_output_module_does_not_import_pymupdf_eagerly() -> None:
    completed = subprocess.run(
        [sys.executable, "-c", "import sys; import tax_graph.output; print('fitz' in sys.modules)"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "False"
