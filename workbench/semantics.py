"""Artifact-only English and expression formatters for graph operations."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence


GraphIndex = Mapping[tuple[str, str], dict[str, Any]]
_SIMPLE_OPERATIONS = {"COPY", "SUM", "SUBTRACT", "NEGATE"}


class SemanticFormatError(ValueError):
    """Raised when a supported operation has an invalid operand shape."""


@dataclass(frozen=True)
class FormattedSemantics:
    """Human-readable text paired with its structured expression tree."""

    summary: str
    expression: dict[str, Any]
    semantic_class: str


def format_node_semantics(node_id: str, graph_index: GraphIndex) -> FormattedSemantics | None:
    """Format one computed node when it uses an S4 operation.

    Unsupported operations remain structure-only until their dedicated S5
    formatter lands. A node with multiple rule ids is likewise left alone so
    this step never guesses which computation the reviewer should see.
    """
    target = graph_index.get(("node", node_id))
    if target is None or target.get("table_id"):
        return None
    incoming = [
        edge
        for (object_type, _), edge in graph_index.items()
        if object_type == "edge" and edge.get("target") == node_id and edge.get("rule_id")
    ]
    rule_ids = {str(edge["rule_id"]) for edge in incoming}
    if len(rule_ids) != 1:
        return None
    rule = graph_index.get(("rule", next(iter(rule_ids))))
    if rule is None or str(rule.get("operation", "")).upper() not in _SIMPLE_OPERATIONS:
        return None
    nodes = {
        object_id: obj
        for (object_type, object_id), obj in graph_index.items()
        if object_type == "node"
    }
    if any(str(edge.get("source", "")) not in nodes for edge in incoming):
        return None
    return format_computation(target=target, rule=rule, operand_edges=incoming, nodes=nodes)


def format_computation(
    *,
    target: Mapping[str, Any],
    rule: Mapping[str, Any],
    operand_edges: Sequence[Mapping[str, Any]],
    nodes: Mapping[str, Mapping[str, Any]],
) -> FormattedSemantics:
    """Format a COPY, SUM, SUBTRACT, or NEGATE computation."""
    operation = str(rule.get("operation", "")).upper()
    if operation not in _SIMPLE_OPERATIONS:
        raise SemanticFormatError(f"S4 has no formatter for operation {operation or '<missing>'}")
    target_document = str(target.get("document_id", ""))
    target_line = _line_number(str(target.get("node_id", "")), target)
    operands = [
        _operand(edge, nodes=nodes, target_document=target_document, target_line=target_line)
        for edge in operand_edges
    ]
    citations = sorted(
        {
            str(citation_id)
            for item in [rule, *operand_edges]
            for citation_id in item.get("citation_refs", []) or []
        }
    )

    if operation == "COPY":
        source = _single_operand(operation, operands)
        summary = f"Copied from {source['label']}"
        expression = _expression(operation, summary, source=source["expression"], citations=citations)
        return FormattedSemantics(summary, expression, "copy")

    if operation == "NEGATE":
        source = _single_operand(operation, operands)
        summary = f"Negate {source['label']}"
        expression = _expression(operation, summary, source=source["expression"], citations=citations)
        return FormattedSemantics(summary, expression, "calculation")

    if operation == "SUM":
        if not operands:
            raise SemanticFormatError("SUM requires at least one addend")
        labels = [str(operand["label"]) for operand in operands]
        if all(label.startswith("line ") for label in labels):
            summary = "Add lines " + " + ".join(label.removeprefix("line ") for label in labels)
        else:
            summary = "Add " + " + ".join(labels)
        expression = _expression(
            operation,
            summary,
            operands=[operand["expression"] for operand in operands],
            citations=citations,
        )
        return FormattedSemantics(summary, expression, "calculation")

    by_role = {str(operand["role"]): operand for operand in operands}
    if set(by_role) != {"minuend", "subtrahend"} or len(operands) != 2:
        raise SemanticFormatError("SUBTRACT requires one minuend and one subtrahend")
    left = by_role["minuend"]
    right = by_role["subtrahend"]
    summary = f"Subtract {right['label']} from {left['label']}"
    expression = _expression(
        operation,
        summary,
        left=left["expression"],
        right=right["expression"],
        citations=citations,
    )
    return FormattedSemantics(summary, expression, "calculation")


def _operand(
    edge: Mapping[str, Any],
    *,
    nodes: Mapping[str, Mapping[str, Any]],
    target_document: str,
    target_line: str | None,
) -> dict[str, Any]:
    node_id = str(edge.get("source", ""))
    node = nodes.get(node_id)
    if not node_id or node is None:
        raise SemanticFormatError(f"operand node does not resolve: {node_id or '<missing>'}")
    label = _operand_label(node_id, node, target_document=target_document, target_line=target_line)
    ref = {"object_type": "node", "object_id": node_id, "display_label": label}
    return {
        "role": str(edge.get("role", "")),
        "label": label,
        "expression": {"kind": "reference", "ref": ref},
    }


def _single_operand(operation: str, operands: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if len(operands) != 1:
        raise SemanticFormatError(f"{operation} requires exactly one operand")
    return operands[0]


def _expression(operation: str, text: str, *, citations: Sequence[str], **children: Any) -> dict[str, Any]:
    expression: dict[str, Any] = {
        "kind": operation.lower(),
        "operation": operation,
        "text": text,
        **children,
    }
    if citations:
        expression["citation_refs"] = list(citations)
    return expression


def _operand_label(
    node_id: str,
    node: Mapping[str, Any],
    *,
    target_document: str,
    target_line: str | None,
) -> str:
    document_id = str(node.get("document_id", ""))
    line_number = _line_number(node_id, node)
    if line_number:
        target_group = re.match(r"^([0-9]+)[a-z]$", target_line or "")
        if document_id == target_document and line_number.isalpha() and target_group:
            line_number = f"{target_group.group(1)}{line_number}"
        line = f"line {line_number}"
        if document_id and document_id != target_document:
            return f"{_document_title(document_id)} {line}"
        return line
    label = str(node.get("label") or node_id).strip()
    return label or node_id


def _line_number(node_id: str, node: Mapping[str, Any]) -> str | None:
    label = str(node.get("label", "")).strip()
    printed_match = re.search(r"\b([0-9]+[a-z]?)\s*$", label, flags=re.IGNORECASE)
    if printed_match:
        return printed_match.group(1).lower()
    id_match = re.search(r"(?:^|_)line_([a-z0-9]+)(?:_|$)", node_id)
    return id_match.group(1) if id_match else None


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
