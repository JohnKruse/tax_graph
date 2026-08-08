from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tax_graph.compile import build_sqlite
from tax_graph.engine import Engine, Graph


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m11
def test_qdcgt_worksheet_trace_matches_expected_on_yaml_and_sqlite(tmp_path):
    facts = {
        "filing_status": "single",
        "form_1040_2025_root_line_1a": 60000,
        "form_1040_2025_root_line_3a": 5000,
        "form_1040_2025_deduction_method": "standard",
        "schedule_b_2025_root_line_6": 5000,
        "schedule_d_2025_line_7_net_st": 0,
    }

    # Shipped-content parity: exclude any locally installed user extension so
    # yaml and the compiled sqlite compare the same objects (hermetic in the
    # normal dev state, where the M14 pilot extension is present).
    yaml_result = Engine(Graph(2025, root=ROOT, source="yaml", include_extensions=False)).execute(facts)

    build_root = tmp_path / "project"
    shutil.copytree(ROOT / "graph", build_root / "graph", ignore=shutil.ignore_patterns("_drafts"))
    shutil.copytree(ROOT / "schemas", build_root / "schemas")
    shutil.copytree(
        ROOT / "config",
        build_root / "config",
        ignore=shutil.ignore_patterns("tax-graph.config.yaml"),
    )
    shutil.copytree(ROOT / "data", build_root / "data")
    build_sqlite("2025", root=build_root)
    sqlite_result = Engine(Graph(2025, root=build_root, source="sqlite")).execute(facts)

    assert sqlite_result.values == yaml_result.values
    assert yaml_result.values["form_1040_2025_root_line_15"] == 49250
    assert yaml_result.values["form_1040_2025_qdcgt_line_4"] == 5000
    assert yaml_result.values["form_1040_2025_qdcgt_line_9"] == 4100
    assert yaml_result.values["form_1040_2025_qdcgt_line_12"] == 900
    assert yaml_result.values["form_1040_2025_qdcgt_line_18"] == 135
    assert yaml_result.values["form_1040_2025_qdcgt_line_22"] == 5075
    assert yaml_result.values["form_1040_2025_qdcgt_line_24"] == 5755
    assert yaml_result.values["form_1040_2025_qdcgt_line_25"] == 5210
    assert yaml_result.values["form_1040_2025_root_line_16"] == 5210
    assert yaml_result.trace["form_1040_2025_root_line_16"]["operation"] == "IF_ELSE"
    assert yaml_result.trace["form_1040_2025_qdcgt_line_22"]["operation"] == "IF_ELSE"
    assert yaml_result.trace["form_1040_2025_qdcgt_line_22_tax_table"]["operation"] == "LOOKUP_TABLE"
    assert "cite_1040_qdcgt_line_18_21" in yaml_result.trace["form_1040_2025_qdcgt_line_18"]["citations"]
    assert "cite_1040_qdcgt_line_23_25" in yaml_result.trace["form_1040_2025_qdcgt_line_25"]["citations"]


@pytest.mark.m11
def test_regular_tax_path_uses_tax_table_below_threshold_and_brackets_at_boundary():
    under_facts = {
        "filing_status": "single",
        "form_1040_2025_root_line_1a": 115749,
        "form_1040_2025_deduction_method": "standard",
        "schedule_d_2025_line_7_net_st": 0,
    }
    boundary_facts = {
        "filing_status": "single",
        "form_1040_2025_root_line_1a": 115750,
        "form_1040_2025_deduction_method": "standard",
        "schedule_d_2025_line_7_net_st": 0,
    }

    graph = Graph(2025, root=ROOT, source="yaml")
    under = Engine(graph).execute(under_facts)
    boundary = Engine(graph).execute(boundary_facts)

    assert under.values["form_1040_2025_root_line_15"] == 99999
    assert under.values["form_1040_2025_regular_tax_table_amount"] == 16909
    assert under.values["form_1040_2025_root_line_16"] == 16909
    assert under.trace["form_1040_2025_regular_tax"]["operation"] == "IF_ELSE"

    assert boundary.values["form_1040_2025_root_line_15"] == 100000
    assert boundary.values["form_1040_2025_regular_tax_bracket_amount"] == 16914
    assert boundary.values["form_1040_2025_root_line_16"] == 16914
    assert boundary.trace["form_1040_2025_regular_tax_bracket_amount"]["operation"] == "LOOKUP_BRACKET"


@pytest.mark.m11
def test_deduction_decision_selects_itemized_amount_and_is_exposed_in_graph():
    facts = {
        "filing_status": "single",
        "form_1040_2025_root_line_1a": 50000,
        "form_1040_2025_deduction_method": "itemized",
        "schedule_a_2025_root_line_16_amount": 20000,
        "schedule_d_2025_line_7_net_st": 0,
    }

    graph = Graph(2025, root=ROOT, source="yaml")
    result = Engine(graph).execute(facts)

    decision = graph.decisions["decision_1040_deduction_method"]
    assert decision["sets_node"] == "form_1040_2025_deduction_method"
    assert {option["option_id"] for option in decision["options"]} == {"standard", "itemized", "not_sure"}
    assert result.values["form_1040_2025_root_line_12e"] == 20000
    assert result.trace["form_1040_2025_root_line_12e"]["operation"] == "LOOKUP_TABLE"
