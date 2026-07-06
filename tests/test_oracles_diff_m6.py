from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.engine import TABLE_FACTS_KEY, Engine, Graph
from tax_graph.oracles.box_map import load_box_map
from tax_graph.oracles.diff import diff_engine_result
from tax_graph.oracles.ots import parse_ots_output
from tax_graph.oracles.scenario import CapitalGainScenario, render_tax_graph_facts_document


ROOT = Path(__file__).resolve().parents[1]
OTS_FIXTURES = ROOT / "tests" / "fixtures" / "ots"


def _box_map():
    return load_box_map(ROOT / "oracles" / "box_map_2025.yaml")


def _gain_scenario() -> CapitalGainScenario:
    return CapitalGainScenario(
        scenario_id="m6_single_lot_gain",
        tax_year="2025",
        filing_status="single",
        description="Fake LT lot",
        date_acquired="01/15/2024",
        date_sold="06/01/2025",
        proceeds=12000,
        cost=10000,
    )


def _loss_scenario() -> CapitalGainScenario:
    return CapitalGainScenario(
        scenario_id="m6_loss_beyond_limit",
        tax_year="2025",
        filing_status="single",
        description="Fake LT loss",
        date_acquired="01/15/2024",
        date_sold="06/01/2025",
        proceeds=0,
        cost=10000,
    )


@pytest.mark.m6
def test_diff_agrees_on_canned_ots_output():
    scenario = _gain_scenario()
    graph = Graph("2025", root=ROOT, source="yaml")
    facts = load_facts_from_scenario(scenario)
    result = Engine(graph).execute(facts)
    ots_values = parse_ots_output((OTS_FIXTURES / "ots_2025_single_lot_out.txt").read_text(encoding="utf-8"))

    report = diff_engine_result(result, ots_values, _box_map(), scenario=scenario)

    assert report.ok
    assert report.status == "agreed"
    assert not report.disagreements


@pytest.mark.m6
def test_diff_rejects_guard_violation_before_comparing_boxes():
    scenario = _gain_scenario()
    graph = Graph("2025", root=ROOT, source="yaml")
    result = Engine(graph).execute(load_facts_from_scenario(scenario))
    ots_values = parse_ots_output((OTS_FIXTURES / "ots_2025_single_lot_out.txt").read_text(encoding="utf-8"))
    ots_values["S1_8z"] = 50

    report = diff_engine_result(result, ots_values, _box_map(), scenario=scenario)

    assert report.status == "rejected"
    assert report.guard_violations[0].guard_id == "schedule_1_additional_income_inert"
    assert report.guard_violations[0].scenario["scenario_id"] == scenario.scenario_id
    assert not report.comparisons


@pytest.mark.m6
def test_diff_catches_swapped_8949_subtract_roles_at_8949_box():
    scenario = _gain_scenario()
    graph = Graph("2025", root=ROOT, source="yaml")
    _swap_8949_subtract_roles(graph)
    result = Engine(graph).execute(load_facts_from_scenario(scenario))
    ots_values = parse_ots_output((OTS_FIXTURES / "ots_2025_single_lot_out.txt").read_text(encoding="utf-8"))

    report = diff_engine_result(result, ots_values, _box_map(), scenario=scenario)

    disagreement_nodes = {item.node_id for item in report.disagreements}
    assert report.status == "disagreed"
    assert "form_8949_2025_part_ii_line_2_line_2_column_h_total" in disagreement_nodes
    assert "form_1040_2025_line_7_capital_gain_loss" in disagreement_nodes
    assert report.disagreements[0].scenario["scenario_id"] == scenario.scenario_id


@pytest.mark.m6
def test_diff_detects_loss_beyond_3000_limit_as_unmodeled_semantics():
    scenario = _loss_scenario()
    graph = Graph("2025", root=ROOT, source="yaml")
    result = Engine(graph).execute(load_facts_from_scenario(scenario))
    ots_values = parse_ots_output((OTS_FIXTURES / "ots_2025_loss_limit_out.txt").read_text(encoding="utf-8"))

    report = diff_engine_result(result, ots_values, _box_map(), scenario=scenario)

    disagreement_nodes = {item.node_id for item in report.disagreements}
    assert report.status == "disagreed"
    assert "form_1040_2025_line_7_capital_gain_loss" in disagreement_nodes


def load_facts_from_scenario(scenario: CapitalGainScenario):
    document = render_tax_graph_facts_document(scenario)
    facts = {fact["node_id"]: fact["value"] for fact in document["facts"]}
    facts[TABLE_FACTS_KEY] = document["tables"]
    return facts


def _swap_8949_subtract_roles(graph: Graph) -> None:
    for edge in graph.incoming["form_8949_2025_part_ii_line_1_column_d_minus_e"]:
        if edge["role"] == "minuend":
            edge["role"] = "subtrahend"
        elif edge["role"] == "subtrahend":
            edge["role"] = "minuend"
