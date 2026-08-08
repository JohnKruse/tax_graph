"""Primitive operations for deterministic Tax Graph execution."""

from __future__ import annotations

import math
from typing import Any

from tax_graph.operation_registry import OPERATION_SPECS, operation_spec


class _Missing:
    """Sentinel for a missing required value."""

    def __repr__(self) -> str:
        return "MISSING"

    def __str__(self) -> str:
        return "MISSING"


MISSING = _Missing()


def is_missing(value: Any) -> bool:
    """Return whether a value is the missing-required sentinel."""
    return value is MISSING


def round_value(value: Any, rule: dict[str, Any]) -> Any:
    """Apply the rule's rounding mode after an operation."""
    if is_missing(value) or value is None:
        return value

    mode = rule.get("rounding", "none")
    if mode in ("currency", "cents"):
        return round(value, 2)
    if mode == "dollar":
        return _round_half_up(value)
    return value


def apply_operation(
    operation: str,
    operands: list[dict[str, Any]],
    rule: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> Any:
    """Apply a registered operation to evaluated operands."""
    spec = operation_spec(operation)
    if spec is None:
        raise NotImplementedError(f"operation {operation} is not registered")
    operation = spec.name
    handler = _RUNTIME_HANDLERS.get(spec.runtime_handler)
    if handler is None:
        raise NotImplementedError(f"operation {operation} has no runtime handler")
    if operation not in {"IF", "IF_ELSE", "LOOKUP_TABLE", "LOOKUP_BRACKET", "AND", "OR", "NOT", "COMPARE"}:
        if any(is_missing(operand["value"]) for operand in operands):
            return MISSING
    return handler(operands, rule, context or {})


def _copy(operands: list[dict[str, Any]], rule: dict[str, Any], context: dict[str, Any]) -> Any:
    return operands[0]["value"]


def _sum(operands: list[dict[str, Any]], rule: dict[str, Any], context: dict[str, Any]) -> Any:
    return sum(_number_for_sum(operand, rule) for operand in operands)


def _subtract(operands: list[dict[str, Any]], rule: dict[str, Any], context: dict[str, Any]) -> Any:
    roles = {operand["role"]: _number(operand["value"]) for operand in operands}
    return roles.get("minuend", 0) - roles.get("subtrahend", 0)


def _multiply(operands: list[dict[str, Any]], rule: dict[str, Any], context: dict[str, Any]) -> Any:
    product = 1
    for operand in operands:
        product *= _number(operand["value"])
    return product


def _divide(operands: list[dict[str, Any]], rule: dict[str, Any], context: dict[str, Any]) -> Any:
    roles = {operand["role"]: _number(operand["value"]) for operand in operands}
    denominator = roles.get("denominator", 0)
    if denominator == 0:
        return MISSING
    return roles.get("numerator", 0) / denominator


def _minimum(operands: list[dict[str, Any]], rule: dict[str, Any], context: dict[str, Any]) -> Any:
    return min(_number(operand["value"]) for operand in operands)


def _maximum(operands: list[dict[str, Any]], rule: dict[str, Any], context: dict[str, Any]) -> Any:
    return max(_number(operand["value"]) for operand in operands)


def _negate(operands: list[dict[str, Any]], rule: dict[str, Any], context: dict[str, Any]) -> Any:
    return -_number(operands[0]["value"])


def _round(operands: list[dict[str, Any]], rule: dict[str, Any], context: dict[str, Any]) -> Any:
    value = operands[0]["value"]
    parameters = rule.get("parameters", {}) or {}
    mode = str(parameters.get("mode", "")).lower()
    if not mode:
        if rule.get("rounding") in ("currency", "cents"):
            return round_value(value, rule)
        return _round_half_up(value)
    increment = float(parameters.get("increment", 1))
    if increment <= 0:
        return MISSING
    scaled = value / increment
    if mode in {"nearest", "half_up"}:
        rounded = _round_half_up(scaled)
    elif mode == "up":
        rounded = math.ceil(scaled)
    elif mode == "down":
        rounded = math.floor(scaled)
    else:
        raise ValueError(f"unsupported ROUND mode: {mode}")
    return rounded * increment


def _if(operands: list[dict[str, Any]], rule: dict[str, Any], context: dict[str, Any]) -> Any:
    condition = operands[0]["value"]
    if is_missing(condition) or is_missing(operands[1]["value"]):
        return MISSING
    return operands[1]["value"] if bool(condition) else MISSING


def _and(operands: list[dict[str, Any]], rule: dict[str, Any], context: dict[str, Any]) -> Any:
    if any(is_missing(operand["value"]) for operand in operands):
        return MISSING
    return all(bool(operand["value"]) for operand in operands)


def _or(operands: list[dict[str, Any]], rule: dict[str, Any], context: dict[str, Any]) -> Any:
    if any(is_missing(operand["value"]) for operand in operands):
        return MISSING
    return any(bool(operand["value"]) for operand in operands)


def _not(operands: list[dict[str, Any]], rule: dict[str, Any], context: dict[str, Any]) -> Any:
    value = operands[0]["value"]
    return MISSING if is_missing(value) else not bool(value)


def _compare(operands: list[dict[str, Any]], rule: dict[str, Any], context: dict[str, Any]) -> Any:
    if any(is_missing(operand["value"]) for operand in operands):
        return MISSING
    left, right = operands[0]["value"], operands[1]["value"]
    comparison = str(rule.get("parameters", {}).get("comparison", "eq")).lower()
    if comparison in {"eq", "equal", "equals"}:
        return left == right
    if comparison in {"ne", "not_equal", "not equal"}:
        return left != right
    if comparison in {"gt", "greater", "greater_than"}:
        return left > right
    if comparison in {"ge", "greater_equal", "at_least"}:
        return left >= right
    if comparison in {"lt", "less", "less_than"}:
        return left < right
    if comparison in {"le", "less_equal", "at_most"}:
        return left <= right
    raise ValueError(f"unsupported COMPARE comparison: {comparison}")


def _require_input(operands: list[dict[str, Any]], rule: dict[str, Any], context: dict[str, Any]) -> Any:
    return operands[0]["value"]


def _number_for_sum(operand: dict[str, Any], rule: dict[str, Any]) -> int | float:
    if operand["value"] is None and not rule.get("parameters", {}).get("include_blank_as_zero", False):
        return 0
    return _number(operand["value"])


def _number(value: Any) -> int | float:
    return 0 if value is None else value


def _lookup_table(
    operands: list[dict[str, Any]],
    rule: dict[str, Any],
    context: dict[str, Any],
) -> Any:
    if rule.get("parameters", {}).get("resource") == "tax_table":
        return _lookup_tax_table(operands, context)
    keys = [operand["value"] for operand in operands if operand.get("role") == "key"]
    if not keys:
        return MISSING
    key = str(keys[0])
    default = MISSING
    selected_blank_is_missing = rule.get("parameters", {}).get("selected_blank_is_missing", False)
    for operand in operands:
        role = operand.get("role")
        if role == "default":
            default = operand["value"]
        if role == key:
            if selected_blank_is_missing and operand["value"] is None:
                return MISSING
            return operand["value"]
    return default


def _lookup_tax_table(operands: list[dict[str, Any]], context: dict[str, Any]) -> Any:
    amount = next((operand["value"] for operand in operands if operand.get("role") == "amount"), None)
    status = next((operand["value"] for operand in operands if operand.get("role") == "status"), None)
    if amount is None or status is None or is_missing(amount) or is_missing(status):
        return MISSING
    for entry in context.get("tax_table", []):
        if entry["income_min"] <= amount < entry["income_max"]:
            return (entry.get("taxes") or {}).get(str(status), MISSING)
    return MISSING


def _lookup_bracket(operands: list[dict[str, Any]]) -> Any:
    amount = next((operand["value"] for operand in operands if operand.get("role") == "amount"), None)
    brackets = next((operand["value"] for operand in operands if operand.get("role") == "brackets"), None)
    if amount is None or is_missing(amount) or not isinstance(brackets, list):
        return MISSING
    for tier in reversed(brackets):
        floor = _number(tier.get("floor"))
        if amount >= floor:
            cumulative = _number(tier.get("cumulative"))
            rate = _number(tier.get("rate"))
            return cumulative + rate * (amount - floor)
    return 0


def _if_else(operands: list[dict[str, Any]], rule: dict[str, Any]) -> Any:
    by_role = {operand.get("role"): operand["value"] for operand in operands}
    condition = by_role.get("condition")
    threshold = by_role.get("threshold")
    if is_missing(condition) or is_missing(threshold):
        return MISSING
    if condition is None or threshold is None:
        return MISSING

    parameters = rule.get("parameters")
    comparison = parameters.get("comparison") if isinstance(parameters, dict) else None
    if not isinstance(comparison, str) or not comparison:
        return MISSING
    comparison = comparison.lower()
    left = _number(condition)
    right = _number(threshold)
    if comparison == "gt":
        matched = left > right
    elif comparison == "ge":
        matched = left >= right
    elif comparison == "lt":
        matched = left < right
    elif comparison == "le":
        matched = left <= right
    elif comparison == "eq":
        matched = left == right
    else:
        raise ValueError(f"unsupported IF_ELSE comparison: {comparison}")

    chosen = by_role.get("when_true" if matched else "when_false")
    return MISSING if is_missing(chosen) else chosen


_RUNTIME_HANDLERS = {
    "copy": _copy,
    "sum": _sum,
    "subtract": _subtract,
    "multiply": _multiply,
    "divide": _divide,
    "min": _minimum,
    "max": _maximum,
    "negate": _negate,
    "round": _round,
    "lookup_table": lambda operands, rule, context: _lookup_table(operands, rule, context),
    "lookup_bracket": lambda operands, rule, context: _lookup_bracket(operands),
    "if": _if,
    "if_else": lambda operands, rule, context: _if_else(operands, rule),
    "and": _and,
    "or": _or,
    "not": _not,
    "compare": _compare,
    "require_input": _require_input,
}


def registered_operations() -> frozenset[str]:
    """Return operation names with registered runtime handlers."""
    return frozenset(
        spec.name
        for spec in OPERATION_SPECS
        if spec.runtime_handler in _RUNTIME_HANDLERS
    )


def _round_half_up(value: int | float) -> int:
    return math.floor(value + 0.5) if value >= 0 else math.ceil(value - 0.5)
