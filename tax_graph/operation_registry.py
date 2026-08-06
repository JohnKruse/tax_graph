"""Versioned operation contract shared by extraction, projection, and runtime.

This module is the authored source for the operation vocabulary.  The JSON
schemas, prompts, expression validator, graph projection, workbench, and
engine all consume this registry instead of maintaining parallel operation
lists.
"""

from __future__ import annotations

from dataclasses import dataclass


OPERATION_REGISTRY_VERSION = "1"
NAMED_OPERAND_ROLE = "<named>"


@dataclass(frozen=True)
class OperationSpec:
    """Contract for one operation offered to the extraction model."""

    name: str
    description: str
    roles: tuple[str, ...]
    min_args: int
    max_args: int | None
    runtime_handler: str
    projection_rule: str | None
    numeric_roles: tuple[str | None, ...] = ()
    predicate: bool = False
    named_leaf_roles: bool = False
    expandable: bool = False
    category: str = "value"
    runtime_notes: str = ""

    def accepts_count(self, count: int) -> bool:
        """Return whether this operation accepts an argument count."""
        return count >= self.min_args and (self.max_args is None or count <= self.max_args)

    def roles_for(self, count: int) -> tuple[str, ...]:
        """Return positional roles, repeating the final role for variadic ops."""
        if not self.roles:
            return ()
        if count <= len(self.roles):
            return self.roles[:count]
        if self.max_args is None:
            return self.roles + (self.roles[-1],) * (count - len(self.roles))
        return self.roles[:count]

    def numeric_roles_for(self, count: int) -> tuple[str | None, ...]:
        """Return positional roles that require numeric operands."""
        if count <= len(self.numeric_roles):
            return self.numeric_roles[:count]
        if self.max_args is None and self.numeric_roles:
            return self.numeric_roles + (self.numeric_roles[-1],) * (count - len(self.numeric_roles))
        return self.numeric_roles[:count]


OPERATION_SPECS: tuple[OperationSpec, ...] = (
    OperationSpec("COPY", "Copy one value from its source.", ("source",), 1, 1, "copy", "copy_currency_value", ("source",)),
    OperationSpec("SUM", "Add one or more values.", ("addend",), 1, None, "sum", "sum_currency", ("addend",), expandable=True),
    OperationSpec("SUBTRACT", "Subtract the subtrahend from the minuend.", ("minuend", "subtrahend"), 2, 2, "subtract", "subtract_currency", ("minuend", "subtrahend")),
    OperationSpec("MULTIPLY", "Multiply a value by a factor.", ("multiplicand", "multiplier"), 2, 2, "multiply", "multiply_currency", ("multiplicand", "multiplier")),
    OperationSpec("DIVIDE", "Divide the numerator by the denominator.", ("numerator", "denominator"), 2, 2, "divide", "divide_currency", ("numerator", "denominator"), runtime_notes="A zero divisor returns MISSING and is reported as an unresolved required value."),
    OperationSpec("MIN", "Use the smallest of two or more values.", ("candidate",), 2, None, "min", "min_currency", ("candidate",), expandable=True),
    OperationSpec("MAX", "Use the largest of two or more values.", ("candidate",), 2, None, "max", "max_currency", ("candidate",), expandable=True),
    OperationSpec("NEGATE", "Change the sign of one value.", ("amount",), 1, 1, "negate", "negate_currency", ("amount",)),
    OperationSpec("ROUND", "Round one value using the rule parameters.", ("amount",), 1, 1, "round", "round_currency", ("amount",), runtime_notes="Default mode is nearest whole dollar; an explicit increment and mode are part of the rule. Source: 2025 Instructions for Form 1040, Rounding Off to Whole Dollars, publink24811vd0e457."),
    OperationSpec("LOOKUP_TABLE", "Select a named branch using one key.", (), 2, None, "lookup_table", "lookup_selected_value", named_leaf_roles=True),
    OperationSpec("LOOKUP_BRACKET", "Calculate a value from a bracket table.", ("amount", "brackets"), 2, 2, "lookup_bracket", "lookup_bracket_tax", ("amount",)),
    OperationSpec("IF", "Use a value when a predicate is true.", ("condition", "when_true"), 2, 2, "if", None, (None, "when_true"), predicate=False, category="predicate", runtime_notes="Predicate expressions are represented inside a condition, not as standalone graph rules."),
    OperationSpec("IF_ELSE", "Choose between two values using a comparison.", ("condition", "threshold", "when_true", "when_false"), 4, 4, "if_else", None, ("condition", "threshold", "when_true", "when_false")),
    OperationSpec("AND", "Require every predicate to be true.", ("candidate",), 2, None, "and", None, predicate=True, expandable=True, category="predicate", runtime_notes="Predicate expressions are represented inside a condition, not as standalone graph rules."),
    OperationSpec("OR", "Accept when any predicate is true.", ("candidate",), 2, None, "or", None, predicate=True, expandable=True, category="predicate", runtime_notes="Predicate expressions are represented inside a condition, not as standalone graph rules."),
    OperationSpec("NOT", "Invert one predicate.", ("operand",), 1, 1, "not", None, predicate=True, category="predicate", runtime_notes="Predicate expressions are represented inside a condition, not as standalone graph rules."),
    OperationSpec("COMPARE", "Compare two values using the rule parameter.", ("left", "right"), 2, 2, "compare", None, ("left", "right"), predicate=True, category="predicate", runtime_notes="Predicate expressions are represented inside a condition, not as standalone graph rules."),
    OperationSpec("REQUIRE_INPUT", "Require the value supplied for one input line.", ("input",), 1, 1, "require_input", None, ("input",), category="disposition", runtime_notes="Marks a required input; it is not a computation rule."),
)


OPERATION_REGISTRY = {spec.name: spec for spec in OPERATION_SPECS}


def operation_names() -> tuple[str, ...]:
    """Return the stable ordered operation enum."""
    return tuple(spec.name for spec in OPERATION_SPECS)


def operation_spec(operation: str) -> OperationSpec | None:
    """Return the spec for a case-insensitive operation name."""
    return OPERATION_REGISTRY.get(str(operation or "").upper())


def operation_roles(operation: str, count: int) -> tuple[str, ...]:
    """Return positional roles for one operation and argument count."""
    spec = operation_spec(operation)
    return spec.roles_for(count) if spec is not None else ()


def operation_model_roles(operation: str) -> tuple[str, ...]:
    """Return the non-null operand roles the extraction model may supply.

    Ordinary operations are positional: their role names are assigned by the
    deterministic projection and are therefore not part of the model wire
    contract.  Named operations accept a role-shaped value whose concrete
    names come from the source document.
    """
    spec = operation_spec(operation)
    if spec is None or not spec.named_leaf_roles:
        return ()
    return (NAMED_OPERAND_ROLE,)


def operation_projection_roles(operation: str, count: int) -> tuple[str, ...]:
    """Return the roles the deterministic projection assigns for an operation."""
    spec = operation_spec(operation)
    if spec is None:
        return ()
    if spec.named_leaf_roles:
        return (NAMED_OPERAND_ROLE,)
    return spec.roles_for(count)


def operation_numeric_roles(operation: str, count: int) -> tuple[str | None, ...]:
    """Return numeric operand roles for one operation and argument count."""
    spec = operation_spec(operation)
    return spec.numeric_roles_for(count) if spec is not None else ()


def predicate_operations() -> frozenset[str]:
    """Return operations whose result is a predicate."""
    return frozenset(spec.name for spec in OPERATION_SPECS if spec.predicate)


def projection_rule_for(operation: str, evidence_text: str = "") -> str | None:
    """Resolve an operation to the reusable graph rule used by projection."""
    spec = operation_spec(operation)
    if spec is None:
        return None
    if spec.category != "value":
        return None
    if spec.name != "IF_ELSE":
        return spec.projection_rule
    text = " ".join(str(evidence_text or "").split()).lower()
    less = any(token in text for token in ("less than", "or less", "at most", "no more than", "below", "under"))
    greater = any(token in text for token in ("more than", "or more", "greater than", "at least", "exceeds", "above"))
    if less == greater:
        return None
    return "if_less_than_currency" if less else "if_greater_than_currency"


def prompt_operation_documentation() -> str:
    """Render the registry without leaking internal positional role names."""
    lines = [f"operation registry version: {OPERATION_REGISTRY_VERSION}"]
    for spec in OPERATION_SPECS:
        arity = str(spec.min_args) if spec.max_args == spec.min_args else f"{spec.min_args}+"
        line = f"- {spec.name}: {spec.description} category={spec.category}; args={arity}"
        if spec.named_leaf_roles:
            line += "; roles=named leaf roles"
        if spec.runtime_notes:
            line += f"; notes={spec.runtime_notes}"
        lines.append(line)
    return "\n".join(lines)


def schema_operation_enum() -> list[str]:
    """Return the operation enum for generated JSON schemas."""
    return list(operation_names())


__all__ = [
    "OPERATION_REGISTRY",
    "OPERATION_REGISTRY_VERSION",
    "OPERATION_SPECS",
    "NAMED_OPERAND_ROLE",
    "OperationSpec",
    "operation_names",
    "operation_numeric_roles",
    "operation_model_roles",
    "operation_projection_roles",
    "operation_roles",
    "operation_spec",
    "predicate_operations",
    "projection_rule_for",
    "prompt_operation_documentation",
    "schema_operation_enum",
]
