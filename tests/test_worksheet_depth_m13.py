"""M13 regression coverage for schedule totals and worksheet routing seams."""

from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.engine import TABLE_FACTS_KEY, Engine, Graph, load_facts
from tax_graph.record import build_return_record, ingest_prior_record


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m13
def test_schedule_internal_add_lines_feed_the_1040_spine() -> None:
    """Supplemental Schedule 1 inputs reach AGI and itemized totals are computed."""
    facts = {
        "filing_status": "single",
        "form_1040_2025_root_line_1a": 100000,
        "form_1040_2025_deduction_method": "itemized",
        "schedule_1_2025_part_i_line_8z": 125,
        "schedule_1_2025_part_ii_line_21": 75,
        "schedule_a_2025_root_line_a": 1000,
        "schedule_a_2025_root_line_b": 2000,
        "schedule_a_2025_root_line_c": 3000,
        "schedule_a_2025_root_line_e": 6000,
        "schedule_a_2025_root_line_6": 400,
        "schedule_a_2025_root_line_8": 500,
        "schedule_a_2025_root_line_9": 100,
        "schedule_a_2025_root_line_11b": 700,
        "schedule_a_2025_root_line_12": 800,
        "schedule_a_2025_root_line_13": 900,
        "schedule_a_2025_root_line_15": 1000,
        "schedule_a_2025_root_line_16_amount": 1100,
        "schedule_d_2025_line_7_net_st": 0,
    }

    result = Engine(Graph(2025, root=ROOT, source="yaml")).execute(facts)

    assert result.values["schedule_1_2025_part_i_line_9"] == 125
    assert result.values["schedule_1_2025_part_i_line_10"] == 125
    assert result.values["schedule_1_2025_part_ii_line_26"] == 75
    assert result.values["schedule_a_2025_root_line_d"] == 6000
    assert result.values["schedule_a_2025_root_line_17"] == 11500
    assert result.values["form_1040_2025_root_line_8"] == 125
    assert result.values["form_1040_2025_root_line_10"] == 75
    assert result.trace["schedule_a_2025_root_line_17"]["operation"] == "SUM"
    worksheet_trace = result.trace["schedule_1_2025_student_loan_interest_deduction_worksheet"]
    assert worksheet_trace["kind"] == "unresolved"
    assert worksheet_trace["frontier_id"] == "deferred_schedule_1_2025_student_loan_interest_deduction_worksheet"


@pytest.mark.m13
def test_capital_loss_carryover_worksheet_round_trips_short_and_long_term() -> None:
    """Worksheet limits a mixed loss and primes next-year Schedule D inputs."""
    graph = Graph(2025, root=ROOT, source="yaml")
    facts = {
        "filing_status": "single",
        "form_1040_2025_root_line_1a": 50000,
        "form_1040_2025_deduction_method": "standard",
        "schedule_d_2025_line_6_st_carryover": -7000,
        "schedule_d_2025_line_14_lt_carryover": -3000,
    }
    result = Engine(graph).execute(facts)

    assert result.values["schedule_d_2025_line_7_net_st"] == -7000
    assert result.values["schedule_d_2025_line_15_net_lt"] == -3000
    assert result.values["schedule_d_2025_line_21_capital_loss_limited"] == -3000
    assert result.values["schedule_d_2025_carryover_worksheet_line_4"] == 3000
    assert result.values["schedule_d_2025_carryover_worksheet_line_8"] == 4000
    assert result.values["schedule_d_2025_carryover_worksheet_line_13"] == 3000

    facts_document = {
        "tax_year": 2025,
        "filing_status": "single",
        "facts": [{"node_id": node_id, "value": value} for node_id, value in facts.items() if node_id != "filing_status"],
    }
    record = build_return_record(
        facts_document=facts_document,
        result=result,
        graph=graph,
        tax_graph_version="test-version",
        generated_date="2026-07-10",
    )
    block = record.carryforward_block.to_dict()

    assert block["capital_loss_raw"] == 10000
    assert [(item["kind"], item["amount"]) for item in block["carryforwards"]] == [
        ("capital_loss_short_term", 4000),
        ("capital_loss_long_term", 3000),
    ]
    ingestion = ingest_prior_record(block, graph)
    assert ingestion.facts == {
        "schedule_d_2025_line_6_st_carryover": -4000,
        "schedule_d_2025_line_14_lt_carryover": -3000,
    }


def _sdtw_facts(*, wages: int, proceeds: int, cost: int, d18: int | None = None, d19: int | None = None) -> dict:
    facts = {
        "filing_status": "single",
        "form_1040_2025_root_line_1a": wages,
        "form_1040_2025_deduction_method": "standard",
        TABLE_FACTS_KEY: [
            {
                "table_id": "form_8949_2025_part_ii_line_1",
                "rows": [{"row_key": "lot_1", "columns": {"d": proceeds, "e": cost, "g": 0}}],
            },
        ],
    }
    if d18 is not None:
        facts["schedule_d_2025_line_18"] = d18
    if d19 is not None:
        facts["schedule_d_2025_line_19"] = d19
    return facts


@pytest.mark.m13
def test_sdtw_unrecaptured_1250_scenario_matches_hand_traced_irs_worksheet() -> None:
    """Single, wages 250000, LT gain 30000, line 19 = 10000.

    Hand-traced line by line from the cited 2025 Schedule D Tax Worksheet text:
    taxable income (ws1) = 264250; preferential pool ws13 = 20000 taxed at 15%
    (ws31 = 3000); the 1250 amount 10000 exceeds the 32%-threshold overlap so
    ws39 = 10000 taxed at 25% (ws40 = 2500); ordinary base ws21 = 234250 taxed
    via the bracket formula (ws44 = 40199 + 0.32 * 36950 = 52023). Line 16 =
    3000 + 2500 + 52023 = 57523. NOTE: the shipped OTS binary computes 55023
    here (it skips lines 33-43 because its gate is inverted relative to the
    IRS text); the IRS text is authoritative - see docs/oracle-strategy.md.
    """
    graph = Graph(2025, root=ROOT, source="yaml")
    values = Engine(graph).execute(_sdtw_facts(wages=250000, proceeds=40000, cost=10000, d19=10000)).values

    assert values["schedule_d_2025_line_17_gate"] == 30000
    assert values["schedule_d_2025_line_20_gate"] == 10000
    assert values["schedule_d_2025_sdtw_applies"] == 10000
    assert values["schedule_d_2025_tax_worksheet_line_13"] == 20000
    assert values["schedule_d_2025_tax_worksheet_line_21"] == 234250
    assert values["schedule_d_2025_tax_worksheet_line_31"] == 3000
    assert values["schedule_d_2025_tax_worksheet_line_39"] == 10000
    assert values["schedule_d_2025_tax_worksheet_line_40"] == 2500
    assert values["schedule_d_2025_tax_worksheet_line_43"] == 0
    assert values["schedule_d_2025_tax_worksheet_line_44"] == 52023
    assert values["schedule_d_2025_tax_worksheet_line_45"] == 57523
    assert values["form_1040_2025_root_line_16"] == 57523


@pytest.mark.m13
def test_sdtw_collectibles_28_pct_scenario_matches_hand_traced_irs_worksheet() -> None:
    """Single, wages 250000, LT gain 30000 all collectibles (line 18 = 30000).

    The whole gain leaves the 0/15/20 pool (ws13 = 0, ws31 = 0) and lands in
    the 28% remainder: ws42 = 30000, ws43 = 8400. Ordinary base ws21 = 234250
    (ws44 = 52023). Line 16 = 8400 + 52023 = 60423.
    """
    graph = Graph(2025, root=ROOT, source="yaml")
    values = Engine(graph).execute(_sdtw_facts(wages=250000, proceeds=40000, cost=10000, d18=30000)).values

    assert values["schedule_d_2025_tax_worksheet_line_13"] == 0
    assert values["schedule_d_2025_tax_worksheet_line_31"] == 0
    assert values["schedule_d_2025_tax_worksheet_line_42"] == 30000
    assert values["schedule_d_2025_tax_worksheet_line_43"] == 8400
    assert values["schedule_d_2025_tax_worksheet_line_44"] == 52023
    assert values["form_1040_2025_root_line_16"] == 60423


@pytest.mark.m13
def test_sdtw_gated_lines_stay_zero_when_line_1_equals_line_16() -> None:
    """Income at/below the 0% breakpoint: IRS says skip lines 23-43 entirely.

    This is the adversarial case from the Step 3 design review: a naive flat
    implementation of the nested gates misapplies preferential rates here.
    Wages 30000 + LT gain 20000 keeps ws1 = 34250 = ws16, so every gated line
    must be exactly zero - including line 43 when line 18 is nonzero (the
    double-gated 28% line, protected by the ws21 == ws14 invariant).
    """
    graph = Graph(2025, root=ROOT, source="yaml")

    values = Engine(graph).execute(_sdtw_facts(wages=30000, proceeds=25000, cost=5000, d19=3000)).values
    for line in ("23", "24", "31", "33", "34", "39", "40", "43"):
        assert values[f"schedule_d_2025_tax_worksheet_line_{line}"] == 0, line
    assert values["form_1040_2025_root_line_16"] == values["schedule_d_2025_tax_worksheet_line_47"]

    values = Engine(graph).execute(_sdtw_facts(wages=30000, proceeds=25000, cost=5000, d18=2000, d19=1000)).values
    assert values["schedule_d_2025_tax_worksheet_line_42"] == 0
    assert values["schedule_d_2025_tax_worksheet_line_43"] == 0


@pytest.mark.m13
def test_sdtw_route_flips_on_one_dollar_of_line_19() -> None:
    graph = Graph(2025, root=ROOT, source="yaml")
    without = Engine(graph).execute(_sdtw_facts(wages=250000, proceeds=40000, cost=10000)).values
    with_one = Engine(graph).execute(_sdtw_facts(wages=250000, proceeds=40000, cost=10000, d19=1)).values

    assert without["schedule_d_2025_sdtw_applies"] == 0
    assert with_one["schedule_d_2025_sdtw_applies"] == 1
    # At this income the two methods coincide in value; the route still flips.
    assert without["form_1040_2025_root_line_16"] == 56523
    assert with_one["form_1040_2025_root_line_16"] == 56523
    assert with_one["schedule_d_2025_tax_worksheet_line_47"] == 56523


@pytest.mark.m13
def test_sdtw_routing_leaves_existing_qdcgt_path_unchanged() -> None:
    graph = Graph(2025, root=ROOT, source="yaml")
    values = Engine(graph).execute(load_facts(ROOT / "examples/taxable_income_basic/facts.yaml")).values

    assert values["schedule_d_2025_sdtw_applies"] == 0
    assert values["form_1040_2025_root_line_16"] == 13777


@pytest.mark.m13
def test_sdtw_feeder_worksheets_stay_declared_walls() -> None:
    graph = Graph(2025, root=ROOT, source="yaml")
    result = Engine(graph).execute(_sdtw_facts(wages=250000, proceeds=40000, cost=10000, d19=10000))

    for node_id, frontier_id in (
        ("schedule_d_2025_28_rate_gain_worksheet", "deferred_schedule_d_2025_28_rate_gain_worksheet"),
        ("schedule_d_2025_unrecaptured_1250_worksheet", "deferred_schedule_d_2025_unrecaptured_1250_worksheet"),
    ):
        trace = result.trace[node_id]
        assert trace["kind"] == "unresolved"
        assert trace["frontier_id"] == frontier_id
