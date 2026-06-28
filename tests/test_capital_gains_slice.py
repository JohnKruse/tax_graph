"""Regression test: execute the capital-gains slice and check expected values.

Example-driven (facts.yaml + expected.yaml) — the pattern that will scale into
the IRS Example Regression Suite (requirements doc §10.4).
"""
import pathlib

import pytest
import yaml

from tax_graph.engine import Engine, Graph, MISSING, load_facts

ROOT = pathlib.Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.m0

EXAMPLE = ROOT / "examples" / "capital_gains_basic"


def test_capital_gains_basic():
    facts = load_facts(EXAMPLE / "facts.yaml")
    result = Engine(Graph(2025, root=ROOT)).execute(facts)
    expected = yaml.safe_load((EXAMPLE / "expected.yaml").read_text(encoding="utf-8"))["expected"]
    for node_id, want in expected.items():
        got = result.values[node_id]
        assert got == want, f"{node_id}: got {got}, want {want}"


def test_missing_required_input_propagates():
    facts = load_facts(EXAMPLE / "facts.yaml")
    facts.pop("form_1099b_2025_box_1e_cost_basis")
    engine = Engine(Graph(2025, root=ROOT))

    result = engine.execute(facts)

    assert result.values["form_1099b_2025_box_1e_cost_basis"] is MISSING
    assert result.values["form_1040_2025_line_7_capital_gain_loss"] is MISSING
    assert result.missing_required_inputs == ["form_1099b_2025_box_1e_cost_basis"]
    assert engine.list_required_inputs(facts) == ["form_1099b_2025_box_1e_cost_basis"]
    assert result.values["form_1040_2025_line_7_capital_gain_loss"] != 12000


def test_required_null_fact_is_missing():
    facts = load_facts(EXAMPLE / "facts.yaml")
    facts["form_1099b_2025_box_1e_cost_basis"] = None

    result = Engine(Graph(2025, root=ROOT)).execute(facts)

    assert result.values["form_1099b_2025_box_1e_cost_basis"] is MISSING
    assert result.values["form_1040_2025_line_7_capital_gain_loss"] is MISSING
