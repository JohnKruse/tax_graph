"""Regression test: execute the capital-gains slice and check expected values.

Example-driven (facts.yaml + expected.yaml) — the pattern that will scale into
the IRS Example Regression Suite (requirements doc §10.4).
"""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
from engine import Graph, Engine, load_facts  # noqa: E402

EXAMPLE = ROOT / "examples" / "capital_gains_basic"


def test_capital_gains_basic():
    facts = load_facts(EXAMPLE / "facts.yaml")
    result = Engine(Graph(2025)).execute(facts)
    expected = yaml.safe_load((EXAMPLE / "expected.yaml").read_text(encoding="utf-8"))["expected"]
    for node_id, want in expected.items():
        got = result.values[node_id]
        assert got == want, f"{node_id}: got {got}, want {want}"
