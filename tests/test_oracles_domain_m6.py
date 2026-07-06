from __future__ import annotations

import os
from pathlib import Path

import pytest

from tax_graph.cli import oracle_fuzz_command
from tax_graph.oracles.domain import assert_scenario_in_domain, generate_scenarios, load_domain_profile
from tax_graph.oracles.scenario import CapitalGainScenario, render_tax_graph_facts_document


ROOT = Path(__file__).resolve().parents[1]


def _profile():
    return load_domain_profile(ROOT / "oracles" / "domain_2025.yaml")


@pytest.mark.m6
def test_seeded_generator_is_deterministic():
    profile = _profile()

    first = generate_scenarios(profile, n=5, seed=123)
    second = generate_scenarios(profile, n=5, seed=123)

    assert first == second


@pytest.mark.m6
def test_generated_scenarios_stay_inside_profile_bounds():
    profile = _profile()

    scenarios = generate_scenarios(profile, n=100, seed=987)

    assert len(scenarios) == 100
    lot_counts = [len(scenario.normalized_lots) for scenario in scenarios]
    for scenario in scenarios:
        assert_scenario_in_domain(profile, scenario)
        render_tax_graph_facts_document(scenario)
        assert 1 <= len(scenario.normalized_lots) <= 15
        assert scenario.gain_loss >= -3000
    assert max(lot_counts) > 11
    assert any(lot.adjustment != 0 for scenario in scenarios for lot in scenario.normalized_lots)
    assert any(
        len(scenario.normalized_lots) >= 3
        and any(lot.gain_loss > 0 for lot in scenario.normalized_lots)
        and any(lot.gain_loss < 0 for lot in scenario.normalized_lots)
        for scenario in scenarios
    )


@pytest.mark.m6
def test_out_of_profile_scenario_is_refused():
    profile = _profile()
    scenario = CapitalGainScenario(
        scenario_id="too_much_loss",
        tax_year="2025",
        filing_status="single",
        description="Out of profile loss",
        date_acquired="01/15/2024",
        date_sold="06/01/2025",
        proceeds=0,
        cost=10000,
    )

    with pytest.raises(ValueError, match="net_gain_loss outside domain"):
        assert_scenario_in_domain(profile, scenario)


@pytest.mark.m6
@pytest.mark.oracle
def test_live_oracle_fuzz_command_runs_100_scenarios(tmp_path):
    if not os.environ.get("OTS_1040_2025_BIN"):
        pytest.skip("set OTS_1040_2025_BIN to run live OTS fuzz")

    exit_code = oracle_fuzz_command(
        year="2025",
        n=100,
        seed=2468,
        root=ROOT,
        output_dir=tmp_path,
        source="yaml",
    )

    assert exit_code == 0
