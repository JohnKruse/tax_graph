"""M20-S67 tests for the versioned operation registry and role contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tax_graph.engine.operations import MISSING, apply_operation, registered_operations
from tax_graph.operation_registry import (
    NAMED_OPERAND_ROLE,
    OPERATION_REGISTRY_VERSION,
    OPERATION_SPECS,
    operation_names,
    operation_model_roles,
    operation_projection_roles,
    prompt_operation_documentation,
    projection_rule_for,
)


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.m20


def test_registry_is_complete_and_checked_in_schemas_match() -> None:
    names = list(operation_names())
    assert OPERATION_REGISTRY_VERSION == "1"
    assert len(names) == len(OPERATION_SPECS) == len(set(names))
    assert all(spec.runtime_handler and spec.description for spec in OPERATION_SPECS)
    assert all(
        (spec.projection_rule or spec.name == "IF_ELSE")
        if spec.category == "value"
        else spec.projection_rule is None
        for spec in OPERATION_SPECS
    )

    rule_schema = json.loads((ROOT / "schemas" / "rule.schema.json").read_text(encoding="ascii"))
    assert rule_schema["properties"]["operation"]["enum"] == names
    for schema_name in ("review_expression.schema.json", "review_unit.schema.json"):
        schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="ascii"))
        assert schema["$defs"]["expression"]["properties"]["operation"]["enum"] == names


def test_registry_generates_prompt_contract() -> None:
    documentation = prompt_operation_documentation()
    assert f"operation registry version: {OPERATION_REGISTRY_VERSION}" in documentation
    assert all(spec.name in documentation for spec in OPERATION_SPECS)
    assert "LOOKUP_BRACKET" in documentation
    assert "REQUIRE_INPUT" in documentation
    assert "publink24811vd0e457" in documentation
    assert "ABS" not in operation_names()


def test_prompt_contract_exposes_only_named_lookup_roles() -> None:
    documentation = prompt_operation_documentation()
    lines = {
        line.split(":", 1)[0].removeprefix("- "): line
        for line in documentation.splitlines()
        if line.startswith("- ")
    }

    assert "roles=addend" not in lines["SUM"]
    assert "roles=minuend" not in lines["SUBTRACT"]
    assert "roles=named leaf roles" in lines["LOOKUP_TABLE"]
    assert operation_model_roles("SUM") == ()
    assert operation_model_roles("LOOKUP_TABLE") == (NAMED_OPERAND_ROLE,)
    assert operation_projection_roles("SUM", 2) == ("addend", "addend")
    assert operation_projection_roles("LOOKUP_TABLE", 2) == (NAMED_OPERAND_ROLE,)


def test_every_registered_operation_has_projection_and_runtime() -> None:
    assert registered_operations() == set(operation_names())
    for spec in OPERATION_SPECS:
        evidence = "the amount is less than the threshold"
        assert (projection_rule_for(spec.name, evidence) is not None) is (spec.category == "value")


def test_divide_by_zero_is_an_unresolved_required_value() -> None:
    operands = [
        {"role": "numerator", "value": 12},
        {"role": "denominator", "value": 0},
    ]
    assert apply_operation("DIVIDE", operands, {}) is MISSING


@pytest.mark.parametrize(
    ("operation", "operands", "rule", "expected"),
    [
        ("COPY", [{"role": "source", "value": 7}], {}, 7),
        ("SUM", [{"role": "addend", "value": 2}, {"role": "addend", "value": 3}], {}, 5),
        ("SUBTRACT", [{"role": "minuend", "value": 9}, {"role": "subtrahend", "value": 4}], {}, 5),
        ("MULTIPLY", [{"role": "multiplicand", "value": 3}, {"role": "multiplier", "value": 4}], {}, 12),
        ("DIVIDE", [{"role": "numerator", "value": 12}, {"role": "denominator", "value": 4}], {}, 3),
        ("MIN", [{"role": "candidate", "value": 9}, {"role": "candidate", "value": 4}], {}, 4),
        ("MAX", [{"role": "candidate", "value": 9}, {"role": "candidate", "value": 4}], {}, 9),
        ("NEGATE", [{"role": "amount", "value": 4}], {}, -4),
        ("ROUND", [{"role": "amount", "value": 4.6}], {}, 5),
        ("LOOKUP_TABLE", [{"role": "key", "value": "single"}, {"role": "single", "value": 10}], {}, 10),
        ("LOOKUP_BRACKET", [{"role": "amount", "value": 150}, {"role": "brackets", "value": [{"floor": 0, "rate": 0.1, "cumulative": 0}, {"floor": 100, "rate": 0.2, "cumulative": 10}]}], {}, 20),
        ("IF", [{"role": "condition", "value": True}, {"role": "when_true", "value": 8}], {}, 8),
        ("IF_ELSE", [{"role": "condition", "value": 2}, {"role": "threshold", "value": 3}, {"role": "when_true", "value": 8}, {"role": "when_false", "value": 1}], {"parameters": {"comparison": "lt"}}, 8),
        ("AND", [{"role": "candidate", "value": True}, {"role": "candidate", "value": True}], {}, True),
        ("OR", [{"role": "candidate", "value": False}, {"role": "candidate", "value": True}], {}, True),
        ("NOT", [{"role": "operand", "value": False}], {}, True),
        ("COMPARE", [{"role": "left", "value": 2}, {"role": "right", "value": 3}], {"parameters": {"comparison": "lt"}}, True),
        ("REQUIRE_INPUT", [{"role": "input", "value": 11}], {}, 11),
    ],
)
def test_registered_operation_executes(
    operation: str,
    operands: list[dict[str, object]],
    rule: dict[str, object],
    expected: object,
) -> None:
    assert apply_operation(operation, operands, rule) == expected
