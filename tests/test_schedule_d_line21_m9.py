from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.engine import Engine, Graph, MISSING, load_facts
from tax_graph.frontier.build import build_frontier_registry, load_frontier_registry
from tax_graph.validate import validate_graph


pytestmark = pytest.mark.m9

ROOT = Path(__file__).resolve().parents[1]
TARGET = "form_1040_2025_line_7_capital_gain_loss"
LINE_21 = "schedule_d_2025_line_21_capital_loss_limited"
LIMIT_SINGLE = "schedule_d_2025_capital_loss_limit_default"
LIMIT_MFS = "schedule_d_2025_capital_loss_limit_mfs"
# M13 Step 3 modeled line 20; the walls moved to the line 18/19 feeder worksheets.
WALL_28_RATE = "schedule_d_2025_28_rate_gain_worksheet"


def test_schedule_d_line_21_limits_single_capital_loss(tmp_path):
    facts_path = _facts_file(tmp_path, filing_status="single", proceeds=1000, basis=6000)

    result = Engine(Graph("2025", root=ROOT, source="yaml")).execute(load_facts(facts_path))

    assert result.values[LINE_21] == -3000
    assert result.values[TARGET] == -3000
    assert result.trace[LIMIT_SINGLE]["kind"] == "parameter"
    assert result.trace[LIMIT_SINGLE]["citations"] == ["cite_schedule_d_line21_loss_limit"]
    assert result.trace[LINE_21]["operation"] == "MAX"


def test_schedule_d_line_21_limits_mfs_capital_loss(tmp_path):
    facts_path = _facts_file(tmp_path, filing_status="married_filing_separately", proceeds=1000, basis=6000)

    result = Engine(Graph("2025", root=ROOT, source="yaml")).execute(load_facts(facts_path))

    assert result.values[LIMIT_MFS] == 1500
    assert result.values[LINE_21] == -1500
    assert result.values[TARGET] == -1500


def test_schedule_d_line_21_does_not_cap_gain(tmp_path):
    facts_path = _facts_file(tmp_path, filing_status="single", proceeds=12000, basis=10000)

    result = Engine(Graph("2025", root=ROOT, source="yaml")).execute(load_facts(facts_path))

    assert result.values[LINE_21] == 2000
    assert result.values[TARGET] == 2000


def test_schedule_d_parameters_validate_without_inline_magic_numbers():
    result = validate_graph("2025", root=ROOT)

    assert result.ok, result.errors


def test_schedule_d_feeder_worksheet_wall_has_unresolved_trace():
    result = Engine(Graph("2025", root=ROOT, source="yaml")).execute(
        {
            "filing_status": "single",
            "schedule_d_2025_line_7_net_st": 0,
        }
    )

    assert result.values[WALL_28_RATE] is MISSING
    trace = result.trace[WALL_28_RATE]
    assert trace["kind"] == "unresolved"
    assert trace["frontier_id"] == "deferred_schedule_d_2025_28_rate_gain_worksheet"
    assert trace["citation_ref"] == "cite_schedule_d_line18_28pct"


def test_frontier_build_includes_schedule_d_deferred_branch(tmp_path):
    result = build_frontier_registry("2025", root=ROOT, write=False)
    registry = result.registry

    entry = next(
        item
        for item in registry["frontiers"]
        if item["frontier_id"] == "deferred_schedule_d_2025_28_rate_gain_worksheet"
    )
    assert entry["kind"] == "deferred_branch"
    assert entry["target"]["node_id"] == "schedule_d_2025_28_rate_gain_worksheet_frontier"
    assert entry["status"] == "declared"
    assert not [
        item
        for item in registry["frontiers"]
        if item["frontier_id"].startswith("flow_schedule_d_2025_outbound_schedule_d")
    ]
    assert load_frontier_registry("2025", root=ROOT)["tax_year"] == 2025


def _facts_file(tmp_path, *, filing_status: str, proceeds: int, basis: int):
    path = tmp_path / f"{filing_status}.yaml"
    path.write_text(
        "\n".join(
            [
                "tax_year: 2025",
                f"filing_status: {filing_status}",
                "facts:",
                "  - node_id: schedule_d_2025_line_7_net_st",
                "    value: 0",
                "tables:",
                "  - table_id: form_8949_2025_part_ii_line_1",
                "    rows:",
                "      - row_key: loss_lot",
                "        columns:",
                f"          d: {proceeds}",
                f"          e: {basis}",
                "          g: 0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path
