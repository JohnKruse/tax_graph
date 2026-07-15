"""Artifact-only English and expression formatters for review semantics."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence


GraphIndex = Mapping[tuple[str, str], dict[str, Any]]
SUPPORTED_OPERATIONS = frozenset({
    "COPY",
    "SUM",
    "SUBTRACT",
    "NEGATE",
    "LOOKUP_TABLE",
    "LOOKUP_BRACKET",
    "MAX",
    "MIN",
    "MULTIPLY",
    "IF_ELSE",
})


class SemanticFormatError(ValueError):
    """Raised when an operation lacks a formatter or has invalid operands."""


@dataclass(frozen=True)
class FormattedSemantics:
    """Human-readable text paired with its structured expression tree."""

    summary: str
    expression: dict[str, Any]
    semantic_class: str


def format_scope_semantics(scope_ref: Mapping[str, Any], graph_index: GraphIndex) -> FormattedSemantics | None:
    """Format one scoped graph, table, frontier, or review-gap object."""
    object_type = str(scope_ref.get("object_type", ""))
    object_id = str(scope_ref.get("object_id", ""))
    role = str(scope_ref.get("role", ""))
    if role == "excluded":
        return _review_gap_semantics(object_type, object_id)
    if object_type in {"frontier", "frontier_field"} or role == "frontier":
        return _frontier_semantics(object_type, object_id)
    if object_type == "table":
        table = graph_index.get(("table", object_id))
        return _table_semantics(table) if table else None
    if object_type not in {"node", "node_instance"}:
        return None
    return format_node_semantics(object_id.split("#", 1)[0], graph_index)


def format_node_semantics(node_id: str, graph_index: GraphIndex) -> FormattedSemantics | None:
    """Format one graph node without inventing missing graph relationships."""
    target = graph_index.get(("node", node_id))
    if target is None:
        return None
    if target.get("table_id"):
        return _table_member_semantics(target, graph_index)

    incoming = _incoming_edges(node_id, graph_index)
    if not incoming:
        return _leaf_semantics(target)
    rule_ids = {str(edge["rule_id"]) for edge in incoming}
    if len(rule_ids) != 1:
        return None
    rule = graph_index.get(("rule", next(iter(rule_ids))))
    if rule is None:
        raise SemanticFormatError(f"rule does not resolve for computed node {node_id}")
    return format_computation(
        target=target,
        rule=rule,
        operand_edges=incoming,
        nodes=_nodes(graph_index),
    )


def format_computation(
    *,
    target: Mapping[str, Any],
    rule: Mapping[str, Any],
    operand_edges: Sequence[Mapping[str, Any]],
    nodes: Mapping[str, Mapping[str, Any]],
) -> FormattedSemantics:
    """Format one supported operation into English and an expression tree."""
    operation = str(rule.get("operation", "")).upper()
    if operation not in SUPPORTED_OPERATIONS:
        raise SemanticFormatError(f"no formatter for operation {operation or '<missing>'}")
    target_document = str(target.get("document_id", ""))
    target_line = _official_ref(target)
    operands = [
        _operand(edge, nodes=nodes, target_document=target_document, target_line=target_line)
        for edge in operand_edges
    ]
    citations = _citations(rule, operand_edges)

    if operation == "COPY":
        source = _single_operand(operation, operands)
        return _formatted(operation, f"Copied from {source['label']}", "copy", citations, source=source["expression"])
    if operation == "NEGATE":
        source = _single_operand(operation, operands)
        return _formatted(
            operation,
            f"Negate {source['label']}",
            "calculation",
            citations,
            source=source["expression"],
        )
    if operation == "SUM":
        if not operands:
            raise SemanticFormatError("SUM requires at least one addend")
        labels = [str(operand["label"]) for operand in operands]
        text = (
            "Add lines " + " + ".join(label.removeprefix("line ") for label in labels)
            if all(label.startswith("line ") for label in labels)
            else "Add " + " + ".join(labels)
        )
        return _formatted(
            operation,
            text,
            "calculation",
            citations,
            operands=[operand["expression"] for operand in operands],
        )
    if operation == "SUBTRACT":
        by_role = _operands_by_role(operation, operands, {"minuend", "subtrahend"})
        left = by_role["minuend"]
        right = by_role["subtrahend"]
        return _formatted(
            operation,
            f"Subtract {right['label']} from {left['label']}",
            "calculation",
            citations,
            left=left["expression"],
            right=right["expression"],
        )
    if operation in {"MIN", "MAX"}:
        if len(operands) < 2 or any(operand["role"] != "candidate" for operand in operands):
            raise SemanticFormatError(f"{operation} requires at least two candidate operands")
        choice = "smaller" if operation == "MIN" else "larger"
        text = f"Use the {choice} of " + " and ".join(str(operand["label"]) for operand in operands)
        return _formatted(
            operation,
            text,
            "branch",
            citations,
            operands=[operand["expression"] for operand in operands],
        )
    if operation == "MULTIPLY":
        by_role = _operands_by_role(operation, operands, {"multiplicand", "multiplier"})
        amount = by_role["multiplicand"]
        factor = by_role["multiplier"]
        text = f"Multiply {amount['label']} by {factor['label']}"
        return _formatted(
            operation,
            text,
            "calculation",
            citations,
            source=amount["expression"],
            factor=factor["expression"],
            parameter_ref=str(factor["object_id"]),
        )
    if operation == "LOOKUP_BRACKET":
        by_role = _operands_by_role(operation, operands, {"amount", "brackets"})
        amount = by_role["amount"]
        brackets = by_role["brackets"]
        text = f"Calculate tax on {amount['label']} using {brackets['label']}"
        return _formatted(
            operation,
            text,
            "lookup",
            citations,
            source=amount["expression"],
            lookup_ref=str(brackets["object_id"]),
        )
    if operation == "LOOKUP_TABLE":
        return _format_lookup_table(operation, rule, operands, citations)
    return _format_if_else(operation, rule, operands, citations)


def _format_lookup_table(
    operation: str,
    rule: Mapping[str, Any],
    operands: Sequence[dict[str, Any]],
    citations: Sequence[str],
) -> FormattedSemantics:
    resource = str((rule.get("parameters") or {}).get("resource", ""))
    if resource:
        by_role = _operands_by_role(operation, operands, {"amount", "status"})
        text = f"Look up tax for {by_role['amount']['label']} using {by_role['status']['label']}"
        return _formatted(
            operation,
            text,
            "lookup",
            citations,
            operands=[by_role["amount"]["expression"], by_role["status"]["expression"]],
            lookup_ref=resource,
        )
    keys = [operand for operand in operands if operand["role"] == "key"]
    choices = [operand for operand in operands if operand["role"] != "key"]
    if len(keys) != 1 or not choices:
        raise SemanticFormatError("LOOKUP_TABLE requires one key and at least one keyed value")
    key = keys[0]
    text = f"Select the value matching {key['label']}"
    return _formatted(
        operation,
        text,
        "lookup",
        citations,
        operands=[operand["expression"] for operand in operands],
        lookup_ref=str(key["object_id"]),
    )


def _format_if_else(
    operation: str,
    rule: Mapping[str, Any],
    operands: Sequence[dict[str, Any]],
    citations: Sequence[str],
) -> FormattedSemantics:
    by_role = _operands_by_role(operation, operands, {"condition", "threshold", "when_true", "when_false"})
    comparison = str((rule.get("parameters") or {}).get("comparison", ""))
    comparison_text = {"lt": "is less than", "gt": "is greater than"}.get(comparison)
    if comparison_text is None:
        raise SemanticFormatError(f"IF_ELSE has unsupported comparison {comparison or '<missing>'}")
    condition = by_role["condition"]
    threshold = by_role["threshold"]
    when_true = by_role["when_true"]
    when_false = by_role["when_false"]
    predicate = f"{condition['label']} {comparison_text} {threshold['label']}"
    text = f"If {predicate}, use {when_true['label']}; otherwise use {when_false['label']}"
    return _formatted(
        operation,
        text,
        "branch",
        citations,
        branches=[{"when": predicate, "then": when_true["expression"]}],
        **{"else": when_false["expression"]},
    )


def _table_semantics(table: Mapping[str, Any]) -> FormattedSemantics:
    table_id = str(table.get("table_id", ""))
    anchor = str(table.get("line_anchor") or table_id)
    text = f"Repeatable table at {anchor}: one template row per transaction, plus totals"
    ref = {"object_type": "table", "object_id": table_id, "display_label": anchor}
    expression = {"kind": "repeatable_table", "text": text, "object_refs": [ref]}
    return FormattedSemantics(text, expression, "repeatable_table")


def _table_member_semantics(target: Mapping[str, Any], graph_index: GraphIndex) -> FormattedSemantics:
    node_id = str(target.get("node_id", ""))
    table_id = str(target.get("table_id", ""))
    column = str(target.get("column", ""))
    role = str(target.get("role", ""))
    table = graph_index.get(("table", table_id))
    anchor = str((table or {}).get("line_anchor") or table_id)
    node_ref = {"object_type": "node", "object_id": node_id, "display_label": str(target.get("label", node_id))}
    table_ref = {"object_type": "table", "object_id": table_id, "display_label": anchor}
    children: list[dict[str, Any]] = []
    if role == "total":
        text = f"Total column ({column}) across all transaction rows"
    else:
        incoming = _incoming_edges(node_id, graph_index)
        if incoming:
            rule_ids = {str(edge["rule_id"]) for edge in incoming}
            if len(rule_ids) != 1:
                raise SemanticFormatError(f"table member {node_id} has ambiguous rules")
            rule = graph_index.get(("rule", next(iter(rule_ids))))
            if rule is None:
                raise SemanticFormatError(f"table member rule does not resolve: {node_id}")
            core = format_computation(target=target, rule=rule, operand_edges=incoming, nodes=_nodes(graph_index))
            text = f"Per transaction, {core.summary[0].lower() + core.summary[1:]}"
            children.append(core.expression)
        else:
            label = str(target.get("label", node_id)).split(" - ", 1)[-1]
            text = f"Enter column ({column}) for each transaction: {label}"
    expression: dict[str, Any] = {
        "kind": "repeatable_table",
        "text": text,
        "object_refs": [table_ref, node_ref],
    }
    if children:
        expression["children"] = children
    return FormattedSemantics(text, expression, "repeatable_table")


def _leaf_semantics(node: Mapping[str, Any]) -> FormattedSemantics:
    node_id = str(node.get("node_id", ""))
    label = str(node.get("label") or node_id)
    node_type = str(node.get("node_type", ""))
    ref = {"object_type": "node", "object_id": node_id, "display_label": label}
    citations = sorted({str(value) for value in node.get("citation_refs", []) or []})
    if node_type == "parameter":
        value = node.get("constant_value")
        text = f"Cited parameter: {label} = {value}"
        expression: dict[str, Any] = {"kind": "parameter", "text": text, "value": value, "ref": ref}
        if citations:
            expression["citation_refs"] = citations
        return FormattedSemantics(text, expression, "parameter")
    if node_type == "computed":
        text = f"Review gap: {label} has no computation rule"
        expression = {
            "kind": "review_gap",
            "text": text,
            "reason": "Computed node has no incoming rule",
            "object_refs": [ref],
        }
        return FormattedSemantics(text, expression, "review_gap")
    document_id = str(node.get("document_id", ""))
    imported = node_type == "box" or document_id.startswith(("form_1099", "form_w2"))
    kind = "imported" if imported else "input"
    text = f"{'Imported' if imported else 'Input'}: {label}"
    return FormattedSemantics(text, {"kind": kind, "text": text, "ref": ref}, kind)


def _frontier_semantics(object_type: str, object_id: str) -> FormattedSemantics:
    label = object_id.replace("_", " ")
    text = f"Frontier: {label} is declared but not modeled"
    ref = {"object_type": object_type or "frontier", "object_id": object_id, "display_label": label}
    expression = {"kind": "frontier", "text": text, "reason": "Declared but not modeled", "object_refs": [ref]}
    return FormattedSemantics(text, expression, "frontier")


def _review_gap_semantics(object_type: str, object_id: str) -> FormattedSemantics:
    label = object_id.replace("_", " ")
    text = f"Review gap: {label} is excluded from the current mapping"
    ref = {"object_type": object_type or "object", "object_id": object_id, "display_label": label}
    expression = {"kind": "review_gap", "text": text, "reason": "Excluded from current mapping", "object_refs": [ref]}
    return FormattedSemantics(text, expression, "review_gap")


def _operand(
    edge: Mapping[str, Any],
    *,
    nodes: Mapping[str, Mapping[str, Any]],
    target_document: str,
    target_line: str | None,
) -> dict[str, Any]:
    node_id = str(edge.get("source", ""))
    node = nodes.get(node_id)
    if node is None:
        if node_id.endswith("_frontier"):
            label = "frontier " + node_id.removesuffix("_frontier").replace("_", " ")
            ref = {"object_type": "frontier", "object_id": node_id, "display_label": label}
            expression = {
                "kind": "frontier",
                "reason": "Declared but not modeled",
                "object_refs": [ref],
            }
            return {"role": str(edge.get("role", "")), "label": label, "expression": expression, "object_id": node_id}
        raise SemanticFormatError(f"operand node does not resolve: {node_id or '<missing>'}")
    label = _operand_label(node_id, node, target_document=target_document, target_line=target_line)
    ref = {"object_type": "node", "object_id": node_id, "display_label": label}
    return {
        "role": str(edge.get("role", "")),
        "label": label,
        "expression": {"kind": "reference", "ref": ref},
        "object_id": node_id,
    }


def _formatted(
    operation: str,
    text: str,
    semantic_class: str,
    citations: Sequence[str],
    **children: Any,
) -> FormattedSemantics:
    expression: dict[str, Any] = {"kind": operation.lower(), "operation": operation, "text": text, **children}
    if citations:
        expression["citation_refs"] = list(citations)
    return FormattedSemantics(text, expression, semantic_class)


def _single_operand(operation: str, operands: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if len(operands) != 1:
        raise SemanticFormatError(f"{operation} requires exactly one operand")
    return operands[0]


def _operands_by_role(
    operation: str,
    operands: Sequence[dict[str, Any]],
    expected_roles: set[str],
) -> dict[str, dict[str, Any]]:
    by_role = {str(operand["role"]): operand for operand in operands}
    if set(by_role) != expected_roles or len(operands) != len(expected_roles):
        raise SemanticFormatError(f"{operation} requires roles {', '.join(sorted(expected_roles))}")
    return by_role


def _citations(rule: Mapping[str, Any], edges: Sequence[Mapping[str, Any]]) -> list[str]:
    return sorted(
        {
            str(citation_id)
            for item in [rule, *edges]
            for citation_id in item.get("citation_refs", []) or []
        }
    )


def _incoming_edges(node_id: str, graph_index: GraphIndex) -> list[dict[str, Any]]:
    return [
        edge
        for (object_type, _), edge in graph_index.items()
        if object_type == "edge" and edge.get("target") == node_id and edge.get("rule_id")
    ]


def _nodes(graph_index: GraphIndex) -> dict[str, dict[str, Any]]:
    nodes = {
        object_id: dict(obj)
        for (object_type, object_id), obj in graph_index.items()
        if object_type == "node"
    }
    for node_id, node in nodes.items():
        binding = graph_index.get(("node_binding", node_id))
        address = graph_index.get(("address", str((binding or {}).get("address_id", ""))))
        if address and address.get("official_ref"):
            node["canonical_official_ref"] = str(address["official_ref"])
    return nodes


def _operand_label(
    node_id: str,
    node: Mapping[str, Any],
    *,
    target_document: str,
    target_line: str | None,
) -> str:
    if node.get("table_id") and node.get("column"):
        return _column_label(str(node["column"]))
    document_id = str(node.get("document_id", ""))
    line_number = _official_ref(node)
    if line_number:
        target_group = re.match(r"^([0-9]+)[a-z]$", target_line or "")
        if document_id == target_document and line_number.isalpha() and target_group:
            line_number = f"{target_group.group(1)}{line_number}"
        line = f"line {line_number}"
        if document_id and document_id != target_document:
            return f"{_document_title(document_id)} {line}"
        return line
    return str(node.get("label") or node_id).strip() or node_id


def _column_label(column: str) -> str:
    parts = column.split("_minus_")
    if len(parts) == 2:
        return f"column ({parts[0]}) minus column ({parts[1]})"
    return f"column ({column})"


def _official_ref(node: Mapping[str, Any]) -> str | None:
    return str(node["canonical_official_ref"]) if node.get("canonical_official_ref") else None


def _document_title(document_id: str) -> str:
    match = re.match(r"^(form|schedule)_([a-z0-9]+)_\d{4}$", document_id)
    if not match:
        return document_id.replace("_", " ").title()
    kind, name = match.groups()
    if name[:-1].isdigit() and name[-1:].isalpha():
        name = f"{name[:-1]}-{name[-1].upper()}"
    elif name.isalpha():
        name = name.upper()
    return f"{kind.title()} {name}"
