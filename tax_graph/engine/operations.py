"""Primitive operations for deterministic Tax Graph execution."""

from __future__ import annotations

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
        return round(value)
    return value


def apply_operation(operation: str, operands: list[dict[str, Any]], rule: dict[str, Any]) -> Any:
    """Apply a v0 primitive operation to evaluated operands."""
    if any(is_missing(operand["value"]) for operand in operands):
        return MISSING

    if operation == "COPY":
        return operands[0]["value"]
    if operation == "SUM":
        return sum(_number_for_sum(operand, rule) for operand in operands)
    if operation == "SUBTRACT":
        roles = {operand["role"]: _number(operand["value"]) for operand in operands}
        return roles.get("minuend", 0) - roles.get("subtrahend", 0)
    if operation == "NEGATE":
        return -_number(operands[0]["value"])
    if operation == "MIN":
        return min(_number(operand["value"]) for operand in operands)
    if operation == "MAX":
        return max(_number(operand["value"]) for operand in operands)
    if operation == "LOOKUP_TABLE":
        return _lookup_table(operands)
    raise NotImplementedError(f"operation {operation} not implemented in v0")


def _number_for_sum(operand: dict[str, Any], rule: dict[str, Any]) -> int | float:
    if operand["value"] is None and not rule.get("parameters", {}).get("include_blank_as_zero", False):
        return 0
    return _number(operand["value"])


def _number(value: Any) -> int | float:
    return 0 if value is None else value


def _lookup_table(operands: list[dict[str, Any]]) -> Any:
    keys = [operand["value"] for operand in operands if operand.get("role") == "key"]
    if not keys:
        return MISSING
    key = str(keys[0])
    default = MISSING
    for operand in operands:
        role = operand.get("role")
        if role == "default":
            default = operand["value"]
        if role == key:
            return operand["value"]
    return default
