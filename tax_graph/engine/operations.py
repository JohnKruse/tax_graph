"""Primitive operations for deterministic Tax Graph execution."""

from __future__ import annotations

import math
from typing import Any


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
    """Apply a v0 primitive operation to evaluated operands."""
    if operation == "IF_ELSE":
        return _if_else(operands, rule)
    if operation == "LOOKUP_TABLE":
        return _lookup_table(operands, rule, context or {})
    if any(is_missing(operand["value"]) for operand in operands):
        return MISSING
    if operation == "COPY":
        return operands[0]["value"]
    if operation == "SUM":
        return sum(_number_for_sum(operand, rule) for operand in operands)
    if operation == "SUBTRACT":
        roles = {operand["role"]: _number(operand["value"]) for operand in operands}
        return roles.get("minuend", 0) - roles.get("subtrahend", 0)
    if operation == "MULTIPLY":
        product = 1
        for operand in operands:
            product *= _number(operand["value"])
        return product
    if operation == "NEGATE":
        return -_number(operands[0]["value"])
    if operation == "MIN":
        return min(_number(operand["value"]) for operand in operands)
    if operation == "MAX":
        return max(_number(operand["value"]) for operand in operands)
    if operation == "LOOKUP_BRACKET":
        return _lookup_bracket(operands)
    raise NotImplementedError(f"operation {operation} not implemented in v0")


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
    if amount is None or not isinstance(brackets, list):
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

    comparison = str(rule.get("parameters", {}).get("comparison", "gt")).lower()
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


def _round_half_up(value: int | float) -> int:
    return math.floor(value + 0.5) if value >= 0 else math.ceil(value - 0.5)
