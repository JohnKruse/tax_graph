from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.engine import Engine, Graph, load_facts
from tax_graph.validate import validate_graph


ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "examples" / "capital_gains_basic" / "facts.yaml"
TARGET = "form_1040_2025_line_7_capital_gain_loss"
TABLE_ID = "form_8949_2025_part_ii_line_1"
GAIN_INSTANCE = "form_8949_2025_part_ii_line_1_column_h#lot_1"
SUBTRACT_INSTANCE = "form_8949_2025_part_ii_line_1_column_d_minus_e#lot_1"
TOTAL_NODE = "form_8949_2025_part_ii_line_2_line_2_column_h_total"


@pytest.mark.m6b
def test_promoted_form_8949_tables_validate_and_preserve_single_lot_parity():
    assert validate_graph("2025", root=ROOT).ok
    graph = Graph("2025", root=ROOT, source="yaml")

    result = Engine(graph).execute(load_facts(FACTS))

    assert graph.tables[TABLE_ID]["totals"][-1]["total_node"] == TOTAL_NODE
    assert result.values[GAIN_INSTANCE] == 2000
    assert result.values[TOTAL_NODE] == 2000
    assert result.values[TARGET] == 2000
    assert result.trace[TOTAL_NODE]["instances"] == [GAIN_INSTANCE]
    assert result.trace[SUBTRACT_INSTANCE]["operation"] == "SUBTRACT"
    assert "cite_8949_col_h_gain" in result.trace[SUBTRACT_INSTANCE]["citations"]
