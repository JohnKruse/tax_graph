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


def _zero_widened_tax_graph_facts():
    return {
        "schedule_1_2025_part_i_line_8z": 0,
        "schedule_1a_2025_part_i_line_2a": 0,
        "schedule_2_2025_part_i_line_1a": 0,
        "schedule_2_2025_part_ii_line_18": 0,
        "schedule_3_2025_part_i_line_1": 0,
        "schedule_3_2025_part_ii_line_13z": 0,
        "schedule_a_2025_root_line_a": 0,
        "schedule_a_2025_root_line_15": 0,
        "schedule_a_2025_root_line_16_amount": 0,
        "form_6251_2025_part_i_line_c": 0,
        "form_6251_2025_part_i_line_g": 0,
    }


def _zero_widened_ots_inputs():
    return {
        "S1_8z": 0,
        "S1A_2a": 0,
        "S2_1a": 0,
        "S2_17z": 0,
        "S3_1": 0,
        "S3_13z": 0,
        "A5a": 0,
        "A15": 0,
        "A16": 0,
        "AMTws2c": 0,
        "AMTws2g": 0,
    }


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
        extra_tax_graph_facts=_zero_widened_tax_graph_facts(),
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
        extra_tax_graph_facts=_zero_widened_tax_graph_facts(),
    )


def _widened_scenario() -> CapitalGainScenario:
    return CapitalGainScenario(
        scenario_id="m10_widened_oracle",
        tax_year="2025",
        filing_status="single",
        description="Widened oracle scenario",
        date_acquired="01/15/2024",
        date_sold="06/01/2025",
        proceeds=12000,
        cost=10000,
        taxable_interest=55,
        ordinary_dividends=65,
        extra_tax_graph_facts={
            "schedule_1_2025_part_i_line_8z": 125,
            "schedule_1a_2025_part_i_line_2a": 40,
            "schedule_2_2025_part_i_line_1a": 60,
            "schedule_2_2025_part_ii_line_18": 25,
            "schedule_3_2025_part_i_line_1": 90,
            "schedule_3_2025_part_ii_line_13z": 35,
            "schedule_a_2025_root_line_a": 400,
            "schedule_a_2025_root_line_15": 20,
            "schedule_a_2025_root_line_16_amount": 15,
            "form_6251_2025_part_i_line_c": 45,
            "form_6251_2025_part_i_line_g": 30,
        },
        extra_ots_inputs={
            "S1_8z": 125,
            "S1A_2a": 40,
            "S2_1a": 60,
            "S2_17z": 25,
            "S3_1": 90,
            "S3_13z": 35,
            "A5a": 400,
            "A15": 20,
            "A16": 15,
            "AMTws2c": 45,
            "AMTws2g": 30,
        },
    )


def _qdcgt_tax_scenario() -> CapitalGainScenario:
    return CapitalGainScenario(
        scenario_id="m11_qdcgt_tax_line",
        tax_year="2025",
        filing_status="single",
        description="QDCGT tax-line oracle scenario",
        date_acquired="01/15/2024",
        date_sold="06/01/2025",
        proceeds=10000,
        cost=10000,
        wages=60000,
        qualified_dividends=5000,
        ordinary_dividends=5000,
        extra_tax_graph_facts=_zero_widened_tax_graph_facts(),
        extra_ots_inputs=_zero_widened_ots_inputs(),
    )


def _regular_tax_scenario() -> CapitalGainScenario:
    return CapitalGainScenario(
        scenario_id="m11_regular_tax_table",
        tax_year="2025",
        filing_status="single",
        description="Regular-tax table oracle scenario",
        date_acquired="01/15/2024",
        date_sold="06/01/2025",
        proceeds=10000,
        cost=10000,
        wages=115749,
        extra_tax_graph_facts=_zero_widened_tax_graph_facts(),
        extra_ots_inputs=_zero_widened_ots_inputs(),
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
    ots_values["S1_3"] = 50

    report = diff_engine_result(result, ots_values, _box_map(), scenario=scenario)

    assert report.status == "rejected"
    assert report.guard_violations[0].guard_id == "schedule_1_business_income_inert"
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
def test_diff_agrees_on_loss_beyond_3000_limit_now_that_line_21_is_modeled():
    scenario = _loss_scenario()
    graph = Graph("2025", root=ROOT, source="yaml")
    result = Engine(graph).execute(load_facts_from_scenario(scenario))
    ots_values = parse_ots_output((OTS_FIXTURES / "ots_2025_loss_limit_out.txt").read_text(encoding="utf-8"))

    report = diff_engine_result(result, ots_values, _box_map(), scenario=scenario)

    assert report.ok
    assert report.status == "agreed"
    assert not report.disagreements


@pytest.mark.m10
def test_diff_agrees_on_widened_canned_ots_output():
    scenario = _widened_scenario()
    graph = Graph("2025", root=ROOT, source="yaml")
    facts = load_facts_from_scenario(scenario)
    result = Engine(graph).execute(facts)
    ots_values = parse_ots_output((OTS_FIXTURES / "ots_2025_widened_out.txt").read_text(encoding="utf-8"))

    report = diff_engine_result(result, ots_values, _box_map(), scenario=scenario)

    assert report.ok
    assert report.status == "agreed"
    assert not report.disagreements


@pytest.mark.m11
def test_diff_agrees_on_qdcgt_tax_line_canned_output():
    scenario = _qdcgt_tax_scenario()
    graph = Graph("2025", root=ROOT, source="yaml")
    facts = load_facts_from_scenario(scenario)
    result = Engine(graph).execute(facts)
    ots_values = parse_ots_output((OTS_FIXTURES / "ots_2025_qdcgt_tax_line_out.txt").read_text(encoding="utf-8"))

    report = diff_engine_result(result, ots_values, _box_map(), scenario=scenario)

    assert report.ok
    assert report.status == "agreed"
    assert not report.disagreements


@pytest.mark.m11
def test_diff_agrees_on_regular_tax_table_canned_output():
    scenario = _regular_tax_scenario()
    graph = Graph("2025", root=ROOT, source="yaml")
    facts = load_facts_from_scenario(scenario)
    result = Engine(graph).execute(facts)
    ots_values = parse_ots_output((OTS_FIXTURES / "ots_2025_regular_tax_table_out.txt").read_text(encoding="utf-8"))

    report = diff_engine_result(result, ots_values, _box_map(), scenario=scenario)

    assert report.ok
    assert report.status == "agreed"
    assert not report.disagreements


def load_facts_from_scenario(scenario: CapitalGainScenario):
    document = render_tax_graph_facts_document(scenario)
    facts = {fact["node_id"]: fact["value"] for fact in document["facts"]}
    if document.get("filing_status"):
        facts["taxpayer_2025_filing_status"] = document["filing_status"]
    facts[TABLE_FACTS_KEY] = document["tables"]
    return facts


def _swap_8949_subtract_roles(graph: Graph) -> None:
    for edge in graph.incoming["form_8949_2025_part_ii_line_1_column_d_minus_e"]:
        if edge["role"] == "minuend":
            edge["role"] = "subtrahend"
        elif edge["role"] == "subtrahend":
            edge["role"] = "minuend"
