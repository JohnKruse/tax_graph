"""M12 OTS sidecar adapter tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tax_graph.oracles.scenario import render_ots_8949_csv, render_ots_input_text
from tax_graph.output.sidecar import scenario_from_facts_document, write_ots_sidecar


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m12
def test_frozen_return_sidecar_reuses_differential_renderer(tmp_path: Path) -> None:
    facts = yaml.safe_load((ROOT / "tests/fixtures/sidecar_sample_facts.yaml").read_text())
    scenario = scenario_from_facts_document(facts, root=ROOT)
    paths = write_ots_sidecar(facts, tmp_path, root=ROOT)
    assert paths["input"].read_text(encoding="utf-8") == render_ots_input_text(
        scenario, spreadsheet_name=paths["csv"].name
    )
    assert paths["csv"].read_text(encoding="utf-8") == render_ots_8949_csv(scenario)
    assert "taxsolve_US_1040_2025" in paths["readme"].read_text(encoding="utf-8")


@pytest.mark.m12
def test_sidecar_preserves_holding_period_and_supplemental_inputs() -> None:
    facts = yaml.safe_load((ROOT / "tests/fixtures/sidecar_sample_facts.yaml").read_text())
    scenario = scenario_from_facts_document(facts, root=ROOT)
    assert scenario.normalized_lots[0].holding_period == "long_term"
    assert scenario.extra_ots_inputs["S2_1a"] == 194
    assert scenario.extra_ots_inputs["AMTws2g"] == 80


@pytest.mark.m12
def test_sidecar_rejects_return_without_required_8949_rows() -> None:
    with pytest.raises(ValueError, match="requires at least one Form 8949"):
        scenario_from_facts_document({"tax_year": 2025, "filing_status": "single", "facts": []}, root=ROOT)
