#!/usr/bin/env python3
"""Compatibility wrapper for the packaged Tax Graph engine.

Usage:  python engine/engine.py <facts.yaml> [tax_year] [target_node_id]
"""

from __future__ import annotations

import pathlib
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tax_graph.engine import Engine, Graph, load_facts, render_trace  # noqa: E402


def main(facts_path, year="2025", target="form_1040_2025_line_7_capital_gain_loss"):
    graph = Graph(year, root=ROOT)
    facts = load_facts(pathlib.Path(facts_path))
    result = Engine(graph).execute(facts)

    print("=== computed values ===")
    for node_id in graph.nodes:
        print(f"  {node_id} = {result.values.get(node_id)}")
    if result.missing_required_inputs:
        print("\n=== missing required inputs ===")
        for node_id in result.missing_required_inputs:
            print(f"  {node_id}")
    print(f"\n=== audit trace: {target} ===")
    render_trace(target, result, graph)
    return result, target


if __name__ == "__main__":
    facts_arg = sys.argv[1] if len(sys.argv) > 1 else "examples/capital_gains_basic/facts.yaml"
    year_arg = sys.argv[2] if len(sys.argv) > 2 else "2025"
    target_arg = sys.argv[3] if len(sys.argv) > 3 else "form_1040_2025_line_7_capital_gain_loss"
    main(facts_arg, year_arg, target_arg)
