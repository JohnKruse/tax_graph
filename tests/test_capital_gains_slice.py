"""Regression test: execute the capital-gains slice and check expected values.

Example-driven (facts.yaml + expected.yaml) - the pattern that will scale into
the IRS Example Regression Suite (requirements doc Section 10.4).
"""
import pathlib

import pytest
import yaml

from tax_graph.engine import TABLE_FACTS_KEY, Engine, Graph, MISSING, load_facts

ROOT = pathlib.Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.m0

EXAMPLE = ROOT / "examples" / "capital_gains_basic"
TARGET = "form_1040_2025_line_7_capital_gain_loss"
PROCEEDS_NODE = "form_8949_2025_part_ii_line_1_column_d"
COST_NODE = "form_8949_2025_part_ii_line_1_column_e"
SUBTRACT_NODE = "form_8949_2025_part_ii_line_1_column_d_minus_e"


def test_capital_gains_basic():
    facts = load_facts(EXAMPLE / "facts.yaml")
    result = Engine(Graph(2025, root=ROOT, source="yaml")).execute(facts)
    expected = yaml.safe_load((EXAMPLE / "expected.yaml").read_text(encoding="utf-8"))["expected"]
    for node_id, want in expected.items():
        got = result.values[node_id]
        assert got == want, f"{node_id}: got {got}, want {want}"
    subtract_trace = result.trace[f"{SUBTRACT_NODE}#lot_1"]
    assert subtract_trace["operation"] == "SUBTRACT"
    assert "cite_8949_col_h_gain" in subtract_trace["citations"]


def test_missing_required_input_propagates():
    facts = load_facts(EXAMPLE / "facts.yaml")
    facts[TABLE_FACTS_KEY][0]["rows"][0]["columns"].pop("e")
    engine = Engine(Graph(2025, root=ROOT, source="yaml"))

    result = engine.execute(facts)

    missing_id = f"{COST_NODE}#lot_1"
    assert result.values[missing_id] is MISSING
    assert result.values[TARGET] is MISSING
    assert result.missing_required_inputs == [missing_id]
    assert engine.list_required_inputs(facts) == [missing_id]
    assert result.values[TARGET] != 12000


def test_required_null_fact_is_missing():
    facts = load_facts(EXAMPLE / "facts.yaml")
    facts[TABLE_FACTS_KEY][0]["rows"][0]["columns"]["d"] = None

    result = Engine(Graph(2025, root=ROOT, source="yaml")).execute(facts)

    assert result.values[f"{PROCEEDS_NODE}#lot_1"] is MISSING
    assert result.values[TARGET] is MISSING
