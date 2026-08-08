"""M20-S85 regression coverage for explicit IF_ELSE comparisons."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tax_graph.engine import Engine, MISSING
from tax_graph.extract.candidate import _candidate_row
from tax_graph.extract.cells import expression_schema
from tax_graph.validate.graph_validator import _validate_if_else_comparators


def _line_18_graph(comparison: str | None) -> SimpleNamespace:
    nodes = {
        "form_6251_2025_part_iii_line_17": {
            "node_id": "form_6251_2025_part_iii_line_17",
            "required": "required",
        },
        "form_6251_2025_threshold": {
            "node_id": "form_6251_2025_threshold",
            "constant_value": 239100,
        },
        "form_6251_2025_rate_26": {
            "node_id": "form_6251_2025_rate_26",
            "constant_value": 0.26,
        },
        "form_6251_2025_rate_28": {
            "node_id": "form_6251_2025_rate_28",
            "constant_value": 0.28,
        },
        "form_6251_2025_subtract_4782": {
            "node_id": "form_6251_2025_subtract_4782",
            "constant_value": 4782,
        },
        "form_6251_2025_line_18_true": {
            "node_id": "form_6251_2025_line_18_true",
        },
        "form_6251_2025_line_18_false_pre": {
            "node_id": "form_6251_2025_line_18_false_pre",
        },
        "form_6251_2025_line_18_false": {
            "node_id": "form_6251_2025_line_18_false",
        },
        "form_6251_2025_part_iii_line_18": {
            "node_id": "form_6251_2025_part_iii_line_18",
        },
    }
    rules = {
        "multiply_currency": {"rule_id": "multiply_currency", "operation": "MULTIPLY"},
        "subtract_currency": {"rule_id": "subtract_currency", "operation": "SUBTRACT"},
        "line_18_rule": {
            "rule_id": "line_18_rule",
            "operation": "IF_ELSE",
            **({"parameters": {"comparison": comparison}} if comparison else {}),
        },
    }
    edges = [
        {"source": "form_6251_2025_part_iii_line_17", "target": "form_6251_2025_line_18_true", "rule_id": "multiply_currency", "role": "multiplicand"},
        {"source": "form_6251_2025_rate_26", "target": "form_6251_2025_line_18_true", "rule_id": "multiply_currency", "role": "multiplier"},
        {"source": "form_6251_2025_part_iii_line_17", "target": "form_6251_2025_line_18_false_pre", "rule_id": "multiply_currency", "role": "multiplicand"},
        {"source": "form_6251_2025_rate_28", "target": "form_6251_2025_line_18_false_pre", "rule_id": "multiply_currency", "role": "multiplier"},
        {"source": "form_6251_2025_line_18_false_pre", "target": "form_6251_2025_line_18_false", "rule_id": "subtract_currency", "role": "minuend"},
        {"source": "form_6251_2025_subtract_4782", "target": "form_6251_2025_line_18_false", "rule_id": "subtract_currency", "role": "subtrahend"},
        {"source": "form_6251_2025_part_iii_line_17", "target": "form_6251_2025_part_iii_line_18", "rule_id": "line_18_rule", "role": "condition"},
        {"source": "form_6251_2025_threshold", "target": "form_6251_2025_part_iii_line_18", "rule_id": "line_18_rule", "role": "threshold"},
        {"source": "form_6251_2025_line_18_true", "target": "form_6251_2025_part_iii_line_18", "rule_id": "line_18_rule", "role": "when_true"},
        {"source": "form_6251_2025_line_18_false", "target": "form_6251_2025_part_iii_line_18", "rule_id": "line_18_rule", "role": "when_false"},
    ]
    incoming: dict[str, list[dict[str, object]]] = {}
    for index, edge in enumerate(edges):
        edge = {"edge_id": f"e_{index}", **edge}
        incoming.setdefault(str(edge["target"]), []).append(edge)
    return SimpleNamespace(
        nodes=nodes,
        rules=rules,
        incoming=incoming,
        tables={},
        tax_table=[],
        frontiers=[],
    )


@pytest.mark.m20
def test_form_6251_line_18_executes_both_arms_from_explicit_le() -> None:
    graph = _line_18_graph("le")
    target = "form_6251_2025_part_iii_line_18"

    below = Engine(graph).execute({"form_6251_2025_part_iii_line_17": 100000})
    above = Engine(graph).execute({"form_6251_2025_part_iii_line_17": 300000})

    assert below.values[target] == 26000
    assert above.values[target] == pytest.approx(79218)


@pytest.mark.m20
def test_missing_if_else_comparison_fails_closed_with_named_trace() -> None:
    graph = _line_18_graph(None)
    target = "form_6251_2025_part_iii_line_18"

    result = Engine(graph).execute({"form_6251_2025_part_iii_line_17": 100000})

    assert result.values[target] is MISSING
    assert result.trace[target]["kind"] == "missing_comparison"
    assert result.trace[target]["note"] == "IF_ELSE requires rule.parameters.comparison"


@pytest.mark.m20
def test_expression_wire_schema_requires_nullable_comparison_field() -> None:
    schema = expression_schema()
    expression = schema["properties"]["expression"]

    assert "comparison" in expression["required"]
    assert expression["properties"]["comparison"]["enum"] == ["gt", "ge", "lt", "le", "eq", None]


@pytest.mark.m20
def test_candidate_holds_back_comparatorless_expression() -> None:
    row = _candidate_row(
        "form_6251_2025",
        {
            "line": "18",
            "status": "derived",
            "label_after": "Alternative minimum tax",
            "expression": {
                "op": "IF_ELSE",
                "args": [{"line": "17"}, {"const": 239100}, {"const": 1}, {"const": 2}],
            },
            "quote": "If line 17 is $239,100 or less, multiply line 17 by 26%.",
            "quote_span_id": "span_18",
        },
        {},
    )

    assert row["candidate_status"] == "review_gap"
    assert row["review_gap"] == "IF_ELSE comparator is missing; candidate graph emission is blocked"
    assert any(item["kind"] == "missing_comparison" for item in row["findings"])


@pytest.mark.m20
def test_graph_validator_names_missing_if_else_comparison(tmp_path: Path) -> None:
    del tmp_path
    errors: list[str] = []
    graph = SimpleNamespace(
        items=lambda kind: (
            [{"rule_id": "if_less_than_currency", "operation": "IF_ELSE"}]
            if kind == "rules"
            else []
        )
    )

    _validate_if_else_comparators(graph, errors)

    assert any(
        "rule if_less_than_currency -> missing IF_ELSE comparison at parameters.comparison" in error
        for error in errors
    )
