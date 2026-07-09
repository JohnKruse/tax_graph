"""M11 Step 5b: PolicyEngine liability witness over the frozen corpus (offline)."""

from pathlib import Path

import json
import pytest
import yaml

from tax_graph.oracles.pe_liability import (
    TABLE_REGION_TOLERANCE,
    run_pe_liability,
    scenario_inputs_from_facts,
)

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "examples" / "oracle_corpus"
FIXTURE = ROOT / "tests" / "fixtures" / "pe_liability_2025.json"


@pytest.mark.m11
def test_pe_liability_offline_fixture_agrees():
    report = run_pe_liability(year=2025, corpus_dir=CORPUS, offline_fixture=FIXTURE)
    assert report.ok
    assert len(report.results) == 20
    assert report.count("disagree") == 0
    assert report.count("fetch_error") == 0
    # Both agreement modes must actually occur: exact above the table region,
    # tolerance inside it (PE computes the bracket formula, not the tax table).
    assert report.count("agree_exact") > 0
    assert report.count("agree_within_table_tolerance") > 0


@pytest.mark.m11
def test_pe_liability_seeded_wrong_value_is_flagged(tmp_path):
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    first = sorted(data["scenarios"])[0]
    data["scenarios"][first]["tax"] = float(data["scenarios"][first]["tax"]) + (
        TABLE_REGION_TOLERANCE + 10
    )
    doctored = tmp_path / "pe_doctored.json"
    doctored.write_text(json.dumps(data), encoding="utf-8")

    report = run_pe_liability(year=2025, corpus_dir=CORPUS, offline_fixture=doctored)
    assert not report.ok
    assert report.count("disagree") == 1


@pytest.mark.m11
def test_scenario_inputs_classify_lot_terms_correctly():
    # Regression: "part_i" is a substring of "part_ii"; long-term rows must not
    # be swept into the short-term bucket (that misclassification moved LT gain
    # out of PolicyEngine's preferential amount and broke the breakpoint case).
    facts_doc = {
        "scenario_id": "t",
        "filing_status": "single",
        "facts": [],
        "tables": [
            {
                "table_id": "form_8949_2025_part_i_line_1",
                "rows": [{"row_key": "st", "columns": {"d": 100, "e": 40, "g": 0}}],
            },
            {
                "table_id": "form_8949_2025_part_ii_line_1",
                "rows": [{"row_key": "lt", "columns": {"d": 500, "e": 200, "g": 0}}],
            },
        ],
    }
    inputs = scenario_inputs_from_facts(facts_doc)
    assert inputs.short_term_gain == 60
    assert inputs.long_term_gain == 300


@pytest.mark.m11
def test_frozen_corpus_line16_values_present():
    manifest = yaml.safe_load((CORPUS / "corpus.yaml").read_text(encoding="utf-8"))
    for entry in manifest["entries"]:
        expected = yaml.safe_load(
            (CORPUS / str(entry["path"]) / "expected.yaml").read_text(encoding="utf-8")
        )["expected"]
        assert "form_1040_2025_root_line_16" in expected
        assert "form_1040_2025_root_line_15" in expected
