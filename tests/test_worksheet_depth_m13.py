"""M13 regression coverage for schedule totals and worksheet routing seams."""

from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.engine import Engine, Graph
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
