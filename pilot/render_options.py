"""Generate five graph-backed renderings for the M20-S80 pilot.

The comparison is deliberately a projection.  It reads the candidate graph
and the joined source evidence through ``review_panel.build_panel``.  It does
not call a provider, write graph artifacts, or assign a human verdict.
"""

from __future__ import annotations

import argparse
from collections import Counter
from html import escape
from pathlib import Path
import re
from statistics import median
import sys
from typing import Any, Callable, Mapping

try:
    from .review_panel import (
        _text,
        build_panel,
    )
except ImportError:
    from review_panel import _text, build_panel

# When this file is invoked as ``python pilot\render_options.py``, Python puts
# ``pilot`` on sys.path but not the repository root that owns tax_graph.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tax_graph.operation_registry import operation_spec


FIXED_CELLS = (
    ("form_6251_2025", "18"),
    ("form_2441_2025", "8"),
    ("form_2441_2025", "20"),
    ("form_2441_2025", "23"),
    ("form_2441_2025", "25"),
)

RENDERING_NAMES = ("flowchart", "worksheet", "math", "english", "tree")
FLOW_MAX_WIDTH = 320.0
FLOW_NODE_WIDTH = 250.0
FLOW_X = (FLOW_MAX_WIDTH - FLOW_NODE_WIDTH) / 2
FLOW_GAP = 24.0
FLOW_BRANCH_OPERATIONS = frozenset({"IF", "IF_ELSE"})
_RANGE_RE = re.compile(r"(?:default|over)_([0-9]+)_([0-9]+|no_limit)$")
_OVER_RE = re.compile(r"over_([0-9]+)_no_limit$")
_SVG_VIEWBOX_RE = re.compile(r'viewBox="0 0 ([0-9.]+) ([0-9.]+)"')
_SVG_SIZE_RE = re.compile(r'<svg[^>]*\bwidth="([0-9.]+)"[^>]*\bheight="([0-9.]+)"')


def _operation_name(tree: Mapping[str, Any]) -> str:
    """Return the graph operation in the stable registry spelling."""

    return _text(tree.get("operation")).strip().upper()


def _constant_text(value: Any) -> str:
    """Render a graph constant in a compact human-facing form."""

    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, int) and value != 0:
        return f"${value:,}"
    if isinstance(value, float):
        return f"{value:g}"
    return _text(value)


def _role_text(role: Any) -> str:
    """Turn a graph branch role into readable range or status text."""

    value = _text(role).strip().lower()
    if not value:
        return "value"
    match = _RANGE_RE.fullmatch(value)
    if match:
        lower, upper = match.groups()
        if upper == "no_limit":
            return f"over ${int(lower):,}"
        return f"${int(lower):,}-${int(upper):,}"
    match = _OVER_RE.fullmatch(value)
    if match:
        return f"over ${int(match.group(1)):,}"
    return value.replace("_", " ")


def _leaf_text(tree: Mapping[str, Any], role: str = "") -> str:
    """Render a graph leaf without exposing its node id or raw OCR label."""

    if tree.get("kind") == "constant":
        return _constant_text(tree.get("value"))
    line = _text(tree.get("line")).strip()
    if line:
        return f"line {line}"
    label = _text(tree.get("label")).strip().lower()
    if "filing_status" in label or "filing status" in label:
        return "filing status"
    role_text = _role_text(role)
    return role_text if role_text not in {"value", "key"} else "input"


def _children(tree: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    """Return valid graph operands with their stored semantic roles."""

    result = []
    for item in tree.get("operands", []):
        if not isinstance(item, Mapping) or not isinstance(item.get("tree"), Mapping):
            continue
        result.append((_text(item.get("role")).strip(), item["tree"]))
    return result


def _lookup_condition(role: str) -> str:
    """Return the human-facing condition represented by a lookup role."""

    return _role_text(role)


def _math_expr(tree: Mapping[str, Any], replacements: Mapping[int, str] | None = None) -> str:
    """Render one graph subtree as compact math without internal ids."""

    replacements = replacements or {}
    replacement = replacements.get(id(tree))
    if replacement:
        return replacement
    if tree.get("kind") != "operation":
        return _leaf_text(tree)
    operation = _operation_name(tree)
    children = _children(tree)
    values = [_math_expr(child, replacements) for _, child in children]
    if operation == "COPY":
        return values[0] if values else "input"
    if operation == "SUM":
        return " + ".join(values) or "sum"
    if operation == "SUBTRACT":
        return " - ".join(values) or "subtract"
    if operation == "MULTIPLY":
        return " * ".join(values) or "multiply"
    if operation == "DIVIDE":
        return " / ".join(values) or "divide"
    if operation == "MIN":
        return f"min({', '.join(values)})"
    if operation == "MAX":
        return f"max({', '.join(values)})"
    if operation == "NEGATE":
        return f"-({values[0]})" if values else "-(amount)"
    if operation == "ROUND":
        return f"round({values[0]})" if values else "round(amount)"
    if operation in {"LOOKUP_TABLE", "LOOKUP_BRACKET"}:
        if not values:
            return "lookup()"
        key = values[0]
        branches = [
            f"{_lookup_condition(role)} -> {_math_expr(child, replacements)}"
            for role, child in children[1:]
        ]
        return f"lookup({key}: {'; '.join(branches)})" if branches else f"lookup({key})"
    if operation == "IF":
        if len(values) >= 2:
            return f"{values[1]} if {values[0]} else absent"
        return "if condition then value"
    if operation == "IF_ELSE":
        if len(values) >= 4:
            return f"{values[2]} if {values[0]} <= {values[1]} else {values[3]}"
        return "if condition then value else value"
    if operation in {"AND", "OR"}:
        joiner = " and " if operation == "AND" else " or "
        return joiner.join(values) or operation.lower()
    if operation == "NOT":
        return f"not {values[0]}" if values else "not condition"
    if operation == "COMPARE":
        return " compared with ".join(values) or "comparison"
    if operation == "REQUIRE_INPUT":
        return values[0] if values else "input"
    return f"{operation.lower()}({', '.join(values)})"


def _operation_result_name(operation: str) -> str:
    """Return a short name for an intermediate result."""

    return {
        "MIN": "smallest value",
        "MAX": "largest value",
        "MULTIPLY": "multiplied amount",
        "SUBTRACT": "difference",
        "LOOKUP_TABLE": "selected value",
        "LOOKUP_BRACKET": "selected value",
        "IF_ELSE": "selected amount",
        "IF": "selected amount",
    }.get(operation, "intermediate value")


def _ledger_steps(tree: Mapping[str, Any], result_name: str) -> list[str]:
    """Return numbered worksheet rows from the graph operation tree."""

    counter = 0
    steps: list[str] = []

    def visit(node: Mapping[str, Any], name: str) -> str:
        nonlocal counter
        if node.get("kind") != "operation":
            return _leaf_text(node)
        child_names: dict[int, str] = {}
        for _, child in _children(node):
            if child.get("kind") == "operation":
                counter += 1
                child_name = f"t{counter} ({_operation_result_name(_operation_name(child))})"
                visit(child, child_name)
                child_names[id(child)] = child_name.split(" ", 1)[0]
        expression = _math_expr(node, child_names)
        steps.append(f"{name} = {expression}")
        return name

    visit(tree, result_name)
    return [f"Step {index}: {value}" for index, value in enumerate(steps, start=1)]


def _result_name(row: Mapping[str, Any]) -> str:
    """Return a printed result name for one panel row."""

    line = _text(row.get("line")).strip()
    return f"line {line}" if line else "result"


def _absence_text(row: Mapping[str, Any]) -> str:
    """Return a human-readable finding shared by every rendering."""

    def reason(value: Any) -> str:
        text = _text(value).strip()
        text = re.sub(r"^ValueError:\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^payload:\s*", "", text, flags=re.IGNORECASE)
        text = text.rstrip(".").strip()
        if "LOOKUP_TABLE arguments must be named leaf operands with a role" in text:
            return "lookup table inputs must be named leaf values with roles"
        text = text.replace("_", " ")
        return text or "the generated operation is unavailable"

    findings = row.get("findings")
    if isinstance(findings, list):
        for finding in findings:
            if isinstance(finding, Mapping):
                message = finding.get("message") or finding.get("error")
                if message:
                    return f"{_result_name(row)}: Review finding - {reason(message)}."
                kind = _text(finding.get("kind")).strip().replace("_", " ")
                if kind:
                    return f"{_result_name(row)}: Review finding - {kind}."
            elif finding:
                return f"{_result_name(row)}: Review finding - {reason(finding)}."
    return f"{_result_name(row)}: Review finding - the promoted operation is unavailable."


def render_worksheet(row: Mapping[str, Any]) -> str:
    """Render a graph as numbered filer-style worksheet steps."""

    tree = row.get("graph", {}).get("tree") if isinstance(row.get("graph"), Mapping) else None
    if not isinstance(tree, Mapping):
        return _absence_text(row)
    return "\n".join(_ledger_steps(tree, _result_name(row)))


def _math_lines(tree: Mapping[str, Any], result_name: str) -> list[str]:
    """Return named intermediate equations for one graph tree."""

    counter = 0
    lines: list[str] = []

    def visit(node: Mapping[str, Any], name: str) -> str:
        nonlocal counter
        if node.get("kind") != "operation":
            return _leaf_text(node)
        replacements: dict[int, str] = {}
        for _, child in _children(node):
            if child.get("kind") == "operation":
                counter += 1
                child_name = f"t{counter}"
                visit(child, child_name)
                replacements[id(child)] = child_name
        lines.append(f"{name} = {_math_expr(node, replacements)}")
        return name

    visit(tree, result_name)
    return lines


def render_math(row: Mapping[str, Any]) -> str:
    """Render a graph as one named equation per line."""

    tree = row.get("graph", {}).get("tree") if isinstance(row.get("graph"), Mapping) else None
    if not isinstance(tree, Mapping):
        return _absence_text(row)
    return "\n".join(_math_lines(tree, _result_name(row)))


def _english_clause(tree: Mapping[str, Any]) -> str:
    """Render one graph operation using its registry description."""

    operation = _operation_name(tree)
    children = _children(tree)
    if operation == "SUBTRACT" and len(children) >= 2:
        # The registry's internal operand names are useful to the validator but
        # are not language a reviewer sees on the form.  Put the printed values
        # directly into the IRS-shaped sentence.
        return f"Subtract {_math_expr(children[1][1])} from {_math_expr(children[0][1])}."
    spec = operation_spec(operation)
    description = spec.description if spec is not None else f"Apply {operation.lower()}."
    if operation in {"LOOKUP_TABLE", "LOOKUP_BRACKET"} and children:
        key = _math_expr(children[0][1])
        branches = "; ".join(
            f"use {_math_expr(child)} for {_lookup_condition(role)}" for role, child in children[1:]
        )
        return f"{description} The key is {key}; {branches}."
    if operation == "IF_ELSE" and len(children) >= 4:
        condition = _math_expr(children[0][1])
        threshold = _math_expr(children[1][1])
        yes = _math_expr(children[2][1])
        no = _math_expr(children[3][1])
        return f"{description} Use {yes} when {condition} is at most {threshold}; otherwise use {no}."
    return f"{description} The result is {_math_expr(tree)}."


def render_english(row: Mapping[str, Any]) -> str:
    """Render a graph as sentences whose operation wording comes from the registry."""

    tree = row.get("graph", {}).get("tree") if isinstance(row.get("graph"), Mapping) else None
    if not isinstance(tree, Mapping):
        return _absence_text(row)
    return f"{_result_name(row)}: {_english_clause(tree)}"


def _tree_lines(tree: Mapping[str, Any], indent: int = 0, role: str = "") -> list[str]:
    """Render the existing role-labelled tree without graph ids."""

    prefix = " " * indent
    if tree.get("kind") != "operation":
        label = _leaf_text(tree, role)
        return [f"{prefix}{role + ': ' if role else ''}{label}"]
    operation = _operation_name(tree)
    lines = [f"{prefix}{role + ': ' if role else ''}{operation}"]
    for child_role, child in _children(tree):
        lines.extend(_tree_lines(child, indent + 2, child_role))
    return lines


def render_tree(row: Mapping[str, Any]) -> str:
    """Render the current role-labelled tree as the comparison control."""

    tree = row.get("graph", {}).get("tree") if isinstance(row.get("graph"), Mapping) else None
    if not isinstance(tree, Mapping):
        return _absence_text(row)
    return "\n".join(_tree_lines(tree))


def _comparison_operator(row: Mapping[str, Any]) -> str:
    """Infer the printed comparison direction from the form-face evidence."""

    text = _text(row.get("form_face")).lower()
    if "or less" in text or "less than" in text or "at most" in text:
        return "<="
    if "or more" in text or "more than" in text or "at least" in text:
        return ">="
    return "compared with"


def _branch_question(tree: Mapping[str, Any], row: Mapping[str, Any]) -> str:
    """Build the question inside a flowchart decision diamond."""

    operation = _operation_name(tree)
    children = _children(tree)
    if operation == "IF_ELSE" and len(children) >= 2:
        condition = _math_expr(children[0][1])
        threshold = (
            "threshold"
            if children[1][1].get("kind") == "operation"
            else _math_expr(children[1][1])
        )
        operator = _comparison_operator(row)
        if operator == "compared with":
            return f"{condition} compared with {threshold}?"
        return f"{condition} {operator} {threshold}?"
    if operation in {"LOOKUP_TABLE", "LOOKUP_BRACKET"} and children:
        key = _math_expr(children[0][1])
        return f"Which value applies to {key}?"
    if children:
        return f"Is {_math_expr(children[0][1])} true?"
    return "Which result applies?"


def _svg_lines(x: float, y: float, text: str, *, width: int = 30) -> str:
    """Wrap one SVG label into readable text lines."""

    lines = _wrapped_lines(text, width)
    return "".join(
        f'<text x="{x:g}" y="{y + index * 16:g}" class="svg-label">{escape(line)}</text>'
        for index, line in enumerate(lines)
    )


def _wrapped_lines(text: str, width: int) -> list[str]:
    """Wrap a label into the same lines used for its SVG height."""

    lines: list[str] = []
    for paragraph in text.splitlines() or [text]:
        words = paragraph.split()
        current = ""
        for word in words:
            if current and len(current) + len(word) + 1 > width:
                lines.append(current)
                current = word
            else:
                current = f"{current} {word}".strip()
        if current or not words:
            lines.append(current)
    if not lines:
        lines.append("")
    return lines


def _flow_node_height(label: str, *, width: int = 25, minimum: float = 60.0) -> float:
    """Return a legible box height for a wrapped label."""

    return max(minimum, 26.0 + 16.0 * len(_wrapped_lines(label, width)))


def _operation_count(tree: Mapping[str, Any]) -> int:
    """Count operation nodes, including nested operations."""

    if tree.get("kind") != "operation":
        return 0
    return 1 + sum(
        _operation_count(child)
        for _, child in _children(tree)
        if isinstance(child, Mapping)
    )


def _flow_operand_text(child: Mapping[str, Any], role: str) -> str:
    """Render one operation input without inlining a nested operation."""

    if child.get("kind") == "operation":
        if _operation_name(child) in {"LOOKUP_TABLE", "LOOKUP_BRACKET"}:
            return "offset" if role == "subtrahend" else "selected value"
        return "amount"
    return _math_expr(child)


def _flow_operation_label(tree: Mapping[str, Any]) -> str:
    """Render exactly one operation for a flowchart or chain box."""

    operation = _operation_name(tree)
    children = _children(tree)
    values = [_flow_operand_text(child, role) for role, child in children]
    if operation == "COPY":
        return values[0] if values else "input"
    if operation == "SUM":
        return " + ".join(values) or "sum"
    if operation == "SUBTRACT":
        return " - ".join(values) or "subtract"
    if operation == "MULTIPLY":
        return " * ".join(values) or "multiply"
    if operation == "DIVIDE":
        return " / ".join(values) or "divide"
    if operation == "MIN":
        return f"min({', '.join(values)})"
    if operation == "MAX":
        if any(child.get("kind") == "operation" for _, child in children) and any(
            child.get("kind") == "constant" and child.get("value") == 0 for _, child in children
        ):
            values = [
                _flow_operand_text(child, role)
                for role, child in children
                if child.get("kind") == "operation"
            ] + [
                _flow_operand_text(child, role)
                for role, child in children
                if child.get("kind") != "operation"
            ]
        return f"max({', '.join(values)})"
    if operation == "NEGATE":
        return f"-({values[0]})" if values else "-(amount)"
    if operation == "ROUND":
        return f"round({values[0]})" if values else "round(amount)"
    if operation in {"AND", "OR"}:
        joiner = " and " if operation == "AND" else " or "
        return joiner.join(values) or operation.lower()
    if operation == "NOT":
        return f"not {values[0]}" if values else "not condition"
    if operation == "COMPARE":
        return " compared with ".join(values) or "comparison"
    if operation == "REQUIRE_INPUT":
        return values[0] if values else "input"
    return f"{operation.lower()}({', '.join(values)})"


def _chain_operations(tree: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return nested operations in dependency order for a vertical chain."""

    result: list[Mapping[str, Any]] = []

    def visit(node: Mapping[str, Any]) -> None:
        if node.get("kind") != "operation":
            return
        for _, child in _children(node):
            visit(child)
        result.append(node)

    visit(tree)
    return result


def _operation_chain_html(row: Mapping[str, Any], tree: Mapping[str, Any]) -> str:
    """Render multiple dependent operations as one vertical chain of boxes."""

    boxes = []
    for index, operation in enumerate(_chain_operations(tree), start=1):
        label = _flow_operation_label(operation)
        boxes.append(
            f'<div class="chain-box" data-operation="{escape(_operation_name(operation))}">'
            f'<span class="chain-step">Step {index}</span><code>{escape(label)}</code></div>'
        )
    return f'<div class="operation-chain"><div class="flow-kind">Operation chain</div>{"<div class=\"chain-then\">then</div>".join(boxes)}</div>'


def _has_flow_branch(tree: Mapping[str, Any]) -> bool:
    """Return whether a tree contains a true decision branch."""

    if tree.get("kind") != "operation":
        return False
    if _operation_name(tree) in FLOW_BRANCH_OPERATIONS:
        return True
    return any(
        _has_flow_branch(child)
        for _, child in _children(tree)
        if isinstance(child, Mapping)
    )


def _branch_children(tree: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    """Return result branches, excluding an operation's condition operands."""

    operation = _operation_name(tree)
    children = _children(tree)
    if operation == "IF":
        return children[1:]
    if operation == "IF_ELSE":
        return children[2:]
    return []


def _flowchart_svg(row: Mapping[str, Any], tree: Mapping[str, Any]) -> str:
    """Render a branch as a legible flow with separate inputs and arms."""

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    edge_labels: list[dict[str, Any]] = []
    node_counter = 0

    def add_node(kind: str, label: str, x: float, y: float, width: float, *, minimum: float = 60.0) -> dict[str, Any]:
        nonlocal node_counter
        node_counter += 1
        wrap_width = max(10, int(width / 7.0))
        height = _flow_node_height(label, width=wrap_width, minimum=minimum)
        node = {
            "id": f"n{node_counter}",
            "kind": kind,
            "label": label,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        }
        nodes.append(node)
        return node

    def add_edge(start: Mapping[str, Any], end: Mapping[str, Any], *, start_x: float | None = None, end_x: float | None = None, route_x: float | None = None, label: str = "") -> None:
        sx = start["x"] + start["width"] / 2 if start_x is None else start_x
        ex = end["x"] + end["width"] / 2 if end_x is None else end_x
        sy = start["y"] + start["height"]
        ey = end["y"]
        edges.append({"start_x": sx, "start_y": sy, "end_x": ex, "end_y": ey, "route_x": route_x, "label": label})
        if label:
            edge_labels.append({"x": (sx + ex) / 2, "y": (sy + ey) / 2 + 4, "text": label})

    def table_label(tree_node: Mapping[str, Any], role: str) -> str:
        title = {
            "threshold": "threshold",
            "subtrahend": "offset",
        }.get(role, "lookup table")
        rows = [title]
        for branch_role, child in _children(tree_node)[1:]:
            rows.append(f"{_lookup_condition(branch_role)}: {_math_expr(child)}")
        return "\n".join(rows)

    def branch_entries(node: Mapping[str, Any], role: str) -> list[tuple[Mapping[str, Any], str, str]]:
        """Return (source tree, node kind, label) entries in dependency order."""

        if node.get("kind") != "operation":
            return [(node, "value", _leaf_text(node, role))]
        operation = _operation_name(node)
        entries: list[tuple[Mapping[str, Any], str, str]] = []
        for child_role, child in _children(node):
            if child.get("kind") == "operation":
                entries.extend(branch_entries(child, child_role))
        if operation in {"LOOKUP_TABLE", "LOOKUP_BRACKET"}:
            entries.append((node, "table", table_label(node, role)))
        else:
            entries.append((node, "box", _flow_operation_label(node)))
        return entries

    def place_branch(role: str, child: Mapping[str, Any], x: float, top: float, width: float) -> tuple[dict[str, Any], dict[str, Any], float]:
        entries = branch_entries(child, role)
        placed: list[dict[str, Any]] = []
        current_top = top
        for source, kind, label in entries:
            minimum = 78.0 if kind == "table" else 60.0
            placed.append(add_node(kind, label, x, current_top, width, minimum=minimum))
            current_top = placed[-1]["y"] + placed[-1]["height"] + FLOW_GAP
        if not placed:
            placed.append(add_node("value", "value", x, top, width))
        by_source = {id(source): node for source, node in zip((item[0] for item in entries), placed)}
        source_to_node = {id(source): node for source, _, _ in entries for node in [by_source[id(source)]]}
        for source, kind, _ in entries:
            if kind not in {"box", "table"} or source.get("kind") != "operation":
                continue
            parent_node = source_to_node[id(source)]
            for child_role, nested in _children(source):
                if nested.get("kind") != "operation":
                    continue
                child_node = source_to_node.get(id(nested))
                if child_node is not None:
                    has_lookup_sibling = any(
                        sibling.get("kind") == "operation"
                        and _operation_name(sibling) in {"LOOKUP_TABLE", "LOOKUP_BRACKET"}
                        for sibling_role, sibling in _children(source)
                        if sibling_role != child_role
                    )
                    route_x = x - 16.0 if has_lookup_sibling and child_node["x"] == parent_node["x"] else None
                    add_edge(child_node, parent_node, route_x=route_x)
        root_node = source_to_node[id(child)]
        return placed[0], root_node, root_node["y"] + root_node["height"]

    # The pilot corpus has IF_ELSE as its branch form.  Keep a conservative
    # fallback for any future branch shape so a new cell remains visible.
    if _operation_name(tree) not in FLOW_BRANCH_OPERATIONS:
        node = add_node("box", _flow_operation_label(tree), FLOW_X, 20.0, FLOW_NODE_WIDTH)
        return _render_flow_svg(nodes, edges, edge_labels)

    children = _children(tree)
    if len(children) < 4:
        node = add_node("diamond", _branch_question(tree, row), FLOW_X, 20.0, FLOW_NODE_WIDTH, minimum=72.0)
        return _render_flow_svg(nodes, edges, edge_labels)

    source_width = 120.0
    source_x = 8.0
    table_x = 177.0
    source_nodes: list[dict[str, Any]] = []
    for role, child in children[:2]:
        if child.get("kind") == "operation" and _operation_name(child) in {"LOOKUP_TABLE", "LOOKUP_BRACKET"}:
            source_nodes.append(add_node("table", table_label(child, role), table_x, 20.0, 135.0, minimum=82.0))
        else:
            source_nodes.append(add_node("input", _math_expr(child), source_x if not source_nodes else table_x, 20.0, source_width))
    source_bottom = max(node["y"] + node["height"] for node in source_nodes)
    diamond_width = 160.0
    diamond = add_node("diamond", _branch_question(tree, row), (FLOW_MAX_WIDTH - diamond_width) / 2, source_bottom + FLOW_GAP, diamond_width, minimum=72.0)
    for source in source_nodes:
        add_edge(source, diamond, end_x=diamond["x"] + (30.0 if source is source_nodes[0] else diamond["width"] - 30.0))

    branch_top = diamond["y"] + diamond["height"] + FLOW_GAP * 2
    branch_width = 125.0
    left_x = 8.0
    right_x = 187.0
    branch_entries_for_edges: list[dict[str, Any]] = []
    branch_roots: list[dict[str, Any]] = []
    branch_bottoms: list[float] = []
    for index, (role, child) in enumerate(_branch_children(tree)):
        branch_entry, branch_root, branch_bottom = place_branch(role, child, left_x if index == 0 else right_x, branch_top, branch_width)
        branch_entries_for_edges.append(branch_entry)
        branch_roots.append(branch_root)
        branch_bottoms.append(branch_bottom)

    exit_x = diamond["x"] + diamond["width"] / 2
    for index, branch_entry in enumerate(branch_entries_for_edges):
        start_x = exit_x - 25.0 if index == 0 else exit_x + 25.0
        add_edge(diamond, branch_entry, start_x=start_x, label=("Yes" if index == 0 else "No"))

    result_label = _result_name(row)
    result = add_node("output", result_label, (FLOW_MAX_WIDTH - 140.0) / 2, max(branch_bottoms) + FLOW_GAP * 2, 140.0, minimum=60.0)
    for branch_root in branch_roots:
        add_edge(branch_root, result)
    return _render_flow_svg(nodes, edges, edge_labels)


def _render_flow_svg(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], edge_labels: list[dict[str, Any]]) -> str:
    """Validate and serialize the shared flow layout."""

    directions = []
    for edge in edges:
        dx = edge["end_x"] - edge["start_x"]
        dy = edge["end_y"] - edge["start_y"]
        direction = (0 if abs(dx) < 0.01 else (1 if dx > 0 else -1), 0 if abs(dy) < 0.01 else (1 if dy > 0 else -1))
        directions.append((round(edge["start_x"], 2), round(edge["start_y"], 2), direction))
    if len(directions) != len(set(directions)):
        raise ValueError("flow connectors share a start point and direction")

    def label_box(label: Mapping[str, Any]) -> tuple[float, float, float, float]:
        lines = _wrapped_lines(_text(label["text"]), 18)
        width = max(len(line) for line in lines) * 7.0 + 4.0
        height = len(lines) * 16.0
        return label["x"] - width / 2, label["y"] - height + 2.0, width, height

    for label in edge_labels:
        lx, ly, lw, lh = label_box(label)
        for node in nodes:
            if lx < node["x"] + node["width"] and lx + lw > node["x"] and ly < node["y"] + node["height"] and ly + lh > node["y"]:
                raise ValueError(
                    f"flow label {label['text']!r} falls inside {node['kind']} node box "
                    f"at {node['x']},{node['y']},{node['width']},{node['height']}"
                )

    max_x = FLOW_MAX_WIDTH
    max_y = max(130.0, max(node["y"] + node["height"] for node in nodes) + 24.0)
    svg_parts = [
        f'<svg class="flowchart-svg" width="{max_x:g}" height="{max_y:g}" viewBox="0 0 {max_x:g} {max_y:g}" role="img" aria-label="Generated flowchart" data-connector-starts-unique="true" data-edge-labels-outside-nodes="true">',
        '<defs><marker id="arrowhead" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 z" /></marker></defs>',
    ]
    for edge in edges:
        midpoint = (edge["start_y"] + edge["end_y"]) / 2
        route_x = edge.get("route_x")
        if route_x is None:
            path = f"M {edge['start_x']:g} {edge['start_y']:g} C {edge['start_x']:g} {midpoint:g}, {edge['end_x']:g} {midpoint:g}, {edge['end_x']:g} {edge['end_y']:g}"
        else:
            path = f"M {edge['start_x']:g} {edge['start_y']:g} C {route_x:g} {edge['start_y']:g}, {route_x:g} {edge['end_y']:g}, {edge['end_x']:g} {edge['end_y']:g}"
        svg_parts.append(f'<path class="svg-edge" d="{path}" marker-end="url(#arrowhead)" />')
    for label in edge_labels:
        svg_parts.append(_svg_lines(label["x"], label["y"], label["text"], width=18))
    for node in nodes:
        kind = node["kind"]
        x, y, width, height, label = node["x"], node["y"], node["width"], node["height"], node["label"]
        if kind == "diamond":
            points = f"{x + width / 2:g},{y:g} {x + width:g},{y + height / 2:g} {x + width / 2:g},{y + height:g} {x:g},{y + height / 2:g}"
            svg_parts.append(f'<polygon class="svg-diamond" points="{points}" />')
            svg_parts.append(_svg_lines(x + 30, y + 25, label, width=max(12, int(width / 7))))
        else:
            css_class = {"table": "svg-table-node", "input": "svg-input", "output": "svg-output"}.get(kind, "svg-box")
            svg_parts.append(f'<rect class="{css_class}" x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" rx="8" />')
            svg_parts.append(_svg_lines(x + 10, y + 22, label, width=max(10, int(width / 7))))
    svg_parts.append("</svg>")
    return "".join(svg_parts)


def _lookup_table_html(row: Mapping[str, Any], tree: Mapping[str, Any]) -> str:
    """Render a lookup operation as a readable table rather than a flow."""

    children = _children(tree)
    key = _math_expr(children[0][1]) if children else "input"
    rows = []
    for role, child in children[1:]:
        rows.append(
            f"<tr><th scope=\"row\">{escape(_lookup_condition(role))}</th>"
            f"<td>{escape(_math_expr(child))}</td></tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="2">No lookup bands were produced.</td></tr>')
    return (
        '<div class="lookup-table-wrap"><div class="flow-kind">Lookup table</div>'
        f"<p>Key: <code>{escape(key)}</code></p>"
        '<table class="lookup-table"><thead><tr><th>When</th><th>Use</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _operation_math_html(row: Mapping[str, Any], tree: Mapping[str, Any]) -> str:
    """Render an ordinary operation in the same compact math vocabulary."""

    return (
        '<div class="operation-math"><div class="flow-kind">Operation</div>'
        f"<code>{escape(f'{_result_name(row)} = {_math_expr(tree)}')}</code></div>"
    )


def _finding_html(row: Mapping[str, Any]) -> str:
    """Render an absent operation as a named, non-empty review finding."""

    return (
        '<div class="review-finding"><div class="flow-kind">Review finding</div>'
        f"<p>{escape(_absence_text(row))}</p></div>"
    )


def render_flowchart(row: Mapping[str, Any]) -> str:
    """Render a branch, lookup table, chain, operation, or finding."""

    tree = row.get("graph", {}).get("tree") if isinstance(row.get("graph"), Mapping) else None
    if not isinstance(tree, Mapping):
        return _finding_html(row)
    if _operation_name(tree) in {"LOOKUP_TABLE", "LOOKUP_BRACKET"}:
        return _lookup_table_html(row, tree)
    if _has_flow_branch(tree):
        return _flowchart_svg(row, tree)
    if _operation_count(tree) > 1:
        return _operation_chain_html(row, tree)
    return _operation_math_html(row, tree)


RENDERERS: dict[str, Callable[[Mapping[str, Any]], str]] = {
    "flowchart": render_flowchart,
    "worksheet": render_worksheet,
    "math": render_math,
    "english": render_english,
    "tree": render_tree,
}


def _size_for(name: str, content: str, row: Mapping[str, Any]) -> int:
    """Return the comparison size unit for one rendering."""

    if name == "flowchart":
        tree = row.get("graph", {}).get("tree") if isinstance(row.get("graph"), Mapping) else None
        if content.lstrip().startswith("<svg"):
            return max(1, content.count('class="svg-edge"'))
        if isinstance(tree, Mapping) and _operation_name(tree) in {"LOOKUP_TABLE", "LOOKUP_BRACKET"}:
            return max(1, content.count("<tr") - 1)
        return 1
    if name in {"worksheet", "math", "tree"}:
        return max(1, len(content.splitlines()))
    return len(content)


def _metric_unit(name: str) -> str:
    """Return the plain-language unit shown in the comparison summary."""

    return {
        "flowchart": "items",
        "worksheet": "rows",
        "math": "lines",
        "english": "characters",
        "tree": "lines",
    }[name]


def _distribution_text(metric: Mapping[str, Any]) -> str:
    """Render a compact size distribution for the comparison summary."""

    distribution = metric.get("distribution")
    if not isinstance(distribution, Mapping) or not distribution:
        return "none"
    return ", ".join(f"{_text(key)}={_text(value)}" for key, value in distribution.items())


def _svg_dimensions(content: str) -> dict[str, float] | None:
    """Return declared SVG width and height for the options report."""

    viewbox = _SVG_VIEWBOX_RE.search(content)
    size = _SVG_SIZE_RE.search(content)
    if not viewbox or not size:
        return None
    return {
        "width": float(size.group(1)),
        "height": float(size.group(2)),
        "viewbox_width": float(viewbox.group(1)),
        "viewbox_height": float(viewbox.group(2)),
    }


def _placeholder_reason(content: str) -> str | None:
    """Identify blank, placeholder, escaped-markup, or raw-payload output."""

    if not content.strip():
        return "empty output"
    lowered = content.lower()
    if "&lt;div" in lowered or "&lt;table" in lowered or "&lt;svg" in lowered:
        return "escaped markup"
    if "valueerror" in lowered or "{'kind'" in lowered or "{'message'" in lowered:
        return "raw payload dump"
    visible = re.sub(r"<[^>]+>", " ", content)
    normalized = " ".join(visible.split()).lower()
    if normalized in {"", "no branch", "no operation", "n/a", "none"}:
        return "placeholder text"
    return None


def _render_inventory(panel: Mapping[str, Any]) -> dict[str, Any]:
    """Render every denominator anchor with every option and collect failures."""

    inventory: dict[str, list[dict[str, Any]]] = {name: [] for name in RENDERING_NAMES}
    failures: dict[str, list[dict[str, str]]] = {name: [] for name in RENDERING_NAMES}
    for row in panel.get("panels", []):
        for name in RENDERING_NAMES:
            try:
                content = RENDERERS[name](row)
                if not isinstance(content, str) or not content.strip():
                    raise ValueError("renderer returned empty output")
                placeholder = _placeholder_reason(content)
                if placeholder:
                    raise ValueError(f"renderer returned {placeholder}")
                inventory[name].append(
                    {
                        "document_id": _text(row.get("document_id")),
                        "line": _text(row.get("line")),
                        "content": content,
                        "size": _size_for(name, content, row),
                        "svg_dimensions": _svg_dimensions(content),
                    }
                )
            except Exception as error:
                failures[name].append(
                    {
                        "document_id": _text(row.get("document_id")),
                        "line": _text(row.get("line")),
                        "error": f"{type(error).__name__}: {error}",
                    }
                )
    metrics = {}
    denominator = len(panel.get("panels", []))
    for name in RENDERING_NAMES:
        sizes = [item["size"] for item in inventory[name]]
        svg_items = [item for item in inventory[name] if item.get("svg_dimensions") is not None]
        metrics[name] = {
            "unit": _metric_unit(name),
            "attempted": denominator,
            "produced": len(inventory[name]),
            "failures": len(failures[name]),
            "empty_or_placeholder": sum(
                1 for item in failures[name] if "empty" in item["error"].lower() or "placeholder" in item["error"].lower()
            ),
            "max": max(sizes, default=0),
            "median": median(sizes) if sizes else 0,
            "distribution": dict(sorted(Counter(sizes).items())),
            "svg_dimensions": [
                {
                    "document_id": item["document_id"],
                    "line": item["line"],
                    **item["svg_dimensions"],
                }
                for item in svg_items
                if item.get("svg_dimensions") is not None
            ],
        }
    flow_svg_items = [item for item in inventory["flowchart"] if item.get("svg_dimensions") is not None]
    geometry_checks = {
        "svg_count": len(flow_svg_items),
        "connector_start_directions_unique": all(
            'data-connector-starts-unique="true"' in item["content"] for item in flow_svg_items
        ),
        "edge_labels_outside_nodes": all(
            'data-edge-labels-outside-nodes="true"' in item["content"] for item in flow_svg_items
        ),
    }
    return {"inventory": inventory, "failures": failures, "metrics": metrics, "geometry_checks": geometry_checks}


def build_comparison(panel: Mapping[str, Any]) -> dict[str, Any]:
    """Build the five-rendering comparison from a generated review panel."""

    rendered = _render_inventory(panel)
    selected = []
    for document_id, line in FIXED_CELLS:
        row = next(
            (item for item in panel.get("panels", []) if item.get("document_id") == document_id and item.get("line") == line),
            None,
        )
        if row is None:
            raise ValueError(f"fixed cell is missing: {document_id} line {line}")
        cell = {
            "document_id": document_id,
            "line": line,
            "form_face": row.get("form_face"),
            "instruction": row.get("instruction"),
            "hole": bool(row.get("hole")),
            "renderings": {},
        }
        for name in RENDERING_NAMES:
            item = next(
                item for item in rendered["inventory"][name]
                if item["document_id"] == document_id and item["line"] == line
            )
            cell["renderings"][name] = item
        selected.append(cell)
    return {
        "schema_version": 1,
        "kind": "rendering_comparison",
        "source_candidate": panel.get("source_candidate"),
        "denominator": panel.get("denominator", 0),
        "fixed_cells": [f"{document_id} line {line}" for document_id, line in FIXED_CELLS],
        "metrics": rendered["metrics"],
        "geometry_checks": rendered["geometry_checks"],
        "failures": rendered["failures"],
        "inventory": rendered["inventory"],
        "selected": selected,
    }


def _rendering_card(name: str, item: Mapping[str, Any]) -> str:
    """Render one selected cell option card."""

    content = _text(item.get("content"))
    previewable = name == "flowchart" and (
        content.lstrip().startswith("<svg")
        or '<table class="lookup-table">' in content
    )
    if previewable:
        title = f"{name.title()} rendering"
        body = (
            '<div class="preview-trigger" role="button" tabindex="0" '
            f'aria-label="Open enlarged {escape(title)}" '
            f'data-preview-title="{escape(title)}">'
            f'<div class="preview-content">{content}</div>'
            '<span class="preview-hint">Click to enlarge</span>'
            '</div>'
        )
    elif name == "flowchart" and content.lstrip().startswith("<div class=\""):
        body = content
    else:
        body = f"<pre>{escape(content)}</pre>"
    return (
        f'<section class="rendering-card rendering-{escape(name)}">'
        f"<h4>{escape(name.title())}</h4>"
        f'<p class="size">{escape(_text(item.get("size")))} {_metric_unit(name)}</p>'
        f"{body}</section>"
    )


def render_html(comparison: Mapping[str, Any]) -> str:
    """Render the self-contained five-option comparison page."""

    metrics = comparison.get("metrics") if isinstance(comparison.get("metrics"), Mapping) else {}
    metric_rows = []
    for name in RENDERING_NAMES:
        metric = metrics.get(name, {}) if isinstance(metrics, Mapping) else {}
        metric_rows.append(
            "<tr>"
            f"<th>{escape(name.title())}</th>"
            f"<td>{escape(_text(metric.get('produced', 0)))}/{escape(_text(metric.get('attempted', 0)))}</td>"
            f"<td>{escape(_text(metric.get('failures', 0)))}</td>"
            f"<td>{escape(_text(metric.get('empty_or_placeholder', 0)))}</td>"
            f"<td>{escape(_distribution_text(metric))}</td>"
            f"<td>{escape(_text(metric.get('median', 0)))} {escape(_text(metric.get('unit')))}</td>"
            f"<td>{escape(_text(metric.get('max', 0)))} {escape(_text(metric.get('unit')))}</td>"
            "</tr>"
        )
    cards = []
    for cell in comparison.get("selected", []):
        title = f"{_text(cell.get('document_id'))} line {_text(cell.get('line'))}"
        face = cell.get("form_face") or "No form-face text recorded."
        instruction = cell.get("instruction") or "No instruction text recorded."
        options = "".join(
            _rendering_card(name, cell["renderings"][name])
            for name in RENDERING_NAMES
        )
        cards.append(
            '<article class="cell-card">'
            f"<header><h2>{escape(title)}</h2><p><strong>Form face:</strong> {escape(_text(face))}</p>"
            f"<p><strong>Instruction:</strong> {escape(_text(instruction))}</p></header>"
            f'<div class="rendering-grid">{options}</div>'
            "</article>"
        )
    failures = comparison.get("failures") or {}
    failure_count = sum(len(values) for values in failures.values() if isinstance(values, list))
    failure_note = "All five renderers produced output for every printed anchor." if failure_count == 0 else f"{failure_count} renderer failures are listed below."
    failure_html = ""
    if failure_count:
        items = []
        for name, values in failures.items():
            for item in values:
                document_id = escape(_text(item.get("document_id"))) if isinstance(item, Mapping) else ""
                line = escape(_text(item.get("line"))) if isinstance(item, Mapping) else ""
                error = escape(_text(item.get("error"))) if isinstance(item, Mapping) else escape(_text(item))
                items.append(f"<li>{escape(name)} {document_id} line {line}: {error}</li>")
        failure_html = f'<details class="failures"><summary>Renderer failures</summary><ul>{"".join(items)}</ul></details>'
    svg_items = []
    for name in RENDERING_NAMES:
        metric = metrics.get(name, {}) if isinstance(metrics, Mapping) else {}
        dimensions = metric.get("svg_dimensions", []) if isinstance(metric, Mapping) else []
        for item in dimensions if isinstance(dimensions, list) else []:
            svg_items.append(
                f"<li>{escape(name)} - {escape(_text(item.get('document_id')))} line "
                f"{escape(_text(item.get('line')))}: "
                f"{escape(_text(item.get('width')))} x {escape(_text(item.get('height')))} "
                f"(viewBox {escape(_text(item.get('viewbox_width')))} x {escape(_text(item.get('viewbox_height')))})</li>"
            )
    svg_html = (
        '<details class="svg-dimensions"><summary>SVG dimensions</summary>'
        + (f"<ul>{''.join(svg_items)}</ul>" if svg_items else "<p>No SVGs were produced.</p>")
        + "</details>"
    )
    geometry = comparison.get("geometry_checks") if isinstance(comparison.get("geometry_checks"), Mapping) else {}
    connector_status = "checked" if geometry.get("connector_start_directions_unique") else "FAILED"
    label_status = "checked" if geometry.get("edge_labels_outside_nodes") else "FAILED"
    geometry_html = (
        "<p class=\"geometry-checks\">Flowchart geometry: "
        f"{escape(_text(geometry.get('svg_count', 0)))} SVGs checked; "
        f"connector start points and directions unique: "
        f"{connector_status}; "
        f"edge labels outside every other node box: "
        f"{label_status}.</p>"
    )
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Five generated cell renderings</title>
<style>
:root {{ color-scheme: light; font-family: Arial, sans-serif; background: #f1f4f7; color: #18212b; }}
body {{ margin: 0; padding: 22px; }}
main {{ max-width: 2200px; margin: 0 auto; }}
.summary {{ padding: 18px 20px; margin-bottom: 18px; background: #18212b; color: white; border-radius: 9px; }}
.summary h1 {{ margin: 0 0 8px; font-size: 1.35rem; }}
.summary p {{ margin: 6px 0; }}
table {{ border-collapse: collapse; margin-top: 14px; background: white; color: #18212b; }}
th, td {{ border: 1px solid #aab5c0; padding: 6px 9px; text-align: left; }}
th {{ background: #e4eaf0; }}
.cell-card {{ margin: 0 0 20px; background: white; border: 1px solid #c7d0d9; border-radius: 9px; overflow: hidden; }}
.cell-card > header {{ padding: 14px 16px; background: #e6edf3; border-bottom: 1px solid #c7d0d9; }}
.cell-card h2 {{ margin: 0 0 8px; font-size: 1.05rem; }}
.cell-card header p {{ margin: 5px 0; max-width: 1500px; }}
.rendering-grid {{ display: grid; grid-template-columns: repeat(5, minmax(320px, 1fr)); gap: 0; align-items: stretch; overflow-x: auto; }}
.rendering-card {{ min-width: 320px; padding: 12px; border-left: 1px solid #d4dce4; }}
.rendering-card:first-child {{ border-left: 0; }}
.rendering-card h4 {{ margin: 0; font-size: .98rem; }}
.size {{ margin: 4px 0 9px; color: #526171; font-size: .78rem; }}
pre {{ margin: 0; min-height: 100px; white-space: pre-wrap; overflow-wrap: anywhere; font: .78rem/1.35 Consolas, monospace; }}
.flowchart-svg {{ display: block; width: min(100%, 320px); height: auto; background: #fbfcfd; border: 1px solid #b4c0cb; }}
.preview-trigger {{ position: relative; cursor: zoom-in; outline: 0; }}
.preview-trigger:focus-visible {{ border-radius: 6px; box-shadow: 0 0 0 3px #1b6ca8; }}
.preview-trigger .preview-content {{ pointer-events: none; }}
.preview-hint {{ display: block; margin-top: 7px; color: #1b6ca8; font-size: .76rem; font-weight: bold; }}
.lookup-table-wrap, .operation-math, .review-finding {{ min-height: 100px; padding: 10px; border: 1px solid #8795a5; background: #fbfcfd; }}
.operation-chain {{ min-height: 100px; padding: 10px; border: 1px solid #8795a5; background: #fbfcfd; }}
.chain-box {{ padding: 9px 10px; border: 2px solid #40566d; border-radius: 8px; background: #e7f0f8; overflow-wrap: anywhere; }}
.chain-box code {{ font: .86rem Consolas, monospace; }}
.chain-step {{ display: block; margin-bottom: 5px; color: #526171; font-size: .72rem; font-weight: bold; text-transform: uppercase; }}
.chain-then {{ margin: 5px 0; color: #526171; font-size: .78rem; text-align: center; }}
.review-finding {{ border: 2px solid #bd3b3b; background: #fff0f0; color: #8b1d1d; }}
.flow-kind {{ margin-bottom: 8px; color: #526171; font-size: .78rem; font-weight: bold; text-transform: uppercase; letter-spacing: .05em; }}
.operation-math code {{ font: .9rem Consolas, monospace; overflow-wrap: anywhere; }}
.lookup-table-wrap p {{ margin: 0 0 8px; }}
.lookup-table {{ width: 100%; border-collapse: collapse; background: white; font-size: .78rem; }}
.lookup-table th, .lookup-table td {{ border: 1px solid #b4c0cb; padding: 5px 6px; text-align: left; vertical-align: top; }}
.lookup-table thead th {{ background: #e4eaf0; }}
.svg-box {{ fill: #e7f0f8; stroke: #40566d; stroke-width: 2; }}
.svg-input {{ fill: #f3f6f8; stroke: #526171; stroke-width: 2; }}
.svg-output {{ fill: #e7f0f8; stroke: #1f6a45; stroke-width: 2; }}
.svg-table-node {{ fill: #eef7ee; stroke: #356b42; stroke-width: 2; }}
.svg-diamond {{ fill: #fff3d1; stroke: #9a6b13; stroke-width: 2; }}
.svg-edge {{ fill: none; stroke: #526171; stroke-width: 1.5; }}
.svg-edge + text {{ fill: #526171; font-size: 12px; }}
.svg-label {{ fill: #18212b; font-size: 12px; }}
.geometry-checks {{ margin-top: 10px; font-weight: bold; }}
details {{ margin-top: 10px; }}
.rendering-lightbox {{ width: min(92vw, 1200px); max-width: 92vw; max-height: 92vh; padding: 0; border: 1px solid #8795a5; border-radius: 9px; overflow: hidden; color: #18212b; }}
.rendering-lightbox::backdrop {{ background: rgba(24, 33, 43, .72); }}
.lightbox-header {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 12px 16px; background: #18212b; color: white; }}
.lightbox-header h2 {{ margin: 0; font-size: 1rem; }}
.lightbox-close {{ padding: 6px 10px; border: 1px solid #d8e2eb; border-radius: 5px; background: white; color: #18212b; cursor: pointer; }}
.lightbox-body {{ max-height: calc(92vh - 70px); overflow: auto; padding: 18px; background: #f8fafc; }}
.lightbox-body .preview-content {{ pointer-events: auto; width: max-content; min-width: 100%; }}
.lightbox-body .flowchart-svg {{ width: auto; max-width: none; height: auto; }}
.lightbox-body .lookup-table-wrap {{ width: max-content; min-width: 760px; }}
.lightbox-body .lookup-table {{ width: max-content; min-width: 760px; font-size: 1rem; }}
@media (max-width: 1500px) {{ .rendering-grid {{ grid-template-columns: repeat(2, minmax(320px, 1fr)); }} .rendering-card:nth-child(3) {{ border-left: 0; border-top: 1px solid #d4dce4; }} .rendering-card:nth-child(n+3) {{ border-top: 1px solid #d4dce4; }} }}
@media (max-width: 700px) {{ body {{ padding: 8px; }} .rendering-grid {{ grid-template-columns: 1fr; }} .rendering-card, .rendering-card:nth-child(3) {{ border-left: 0; border-top: 1px solid #d4dce4; }} .rendering-card:first-child {{ border-top: 0; }} }}
</style>
</head>
<body><main>
<section class="summary"><h1>Five generated renderings of the same cells</h1>
<p>{escape(f"{_text(comparison.get('denominator'))} printed anchors evaluated. {failure_note}")}</p>
<p>Each option is generated from the candidate graph; the form face and instruction text remain source evidence for comparison.</p>
<table><thead><tr><th>Rendering</th><th>Produced</th><th>Failures</th><th>Empty/placeholder</th><th>Size distribution</th><th>Median</th><th>Maximum</th></tr></thead><tbody>{"".join(metric_rows)}</tbody></table>
{geometry_html}
{svg_html}
{failure_html}</section>
{"".join(cards)}
<dialog class="rendering-lightbox" id="rendering-lightbox" aria-labelledby="rendering-lightbox-title">
<div class="lightbox-header"><h2 id="rendering-lightbox-title">Enlarged rendering</h2><button class="lightbox-close" type="button" data-lightbox-close>Close</button></div>
<div class="lightbox-body" id="rendering-lightbox-content"></div>
</dialog>
<script>
(() => {{
  const dialog = document.getElementById("rendering-lightbox");
  const title = document.getElementById("rendering-lightbox-title");
  const content = document.getElementById("rendering-lightbox-content");
  if (!dialog || !title || !content) return;

  const close = () => {{
    if (typeof dialog.close === "function" && dialog.open) dialog.close();
    else dialog.removeAttribute("open");
    content.innerHTML = "";
  }};
  const open = (trigger) => {{
    const source = trigger.querySelector(".preview-content");
    if (!source) return;
    title.textContent = trigger.dataset.previewTitle || "Enlarged rendering";
    content.innerHTML = source.innerHTML;
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
  }};

  document.querySelectorAll(".preview-trigger").forEach((trigger) => {{
    trigger.addEventListener("click", () => open(trigger));
    trigger.addEventListener("keydown", (event) => {{
      if (event.key === "Enter" || event.key === " ") {{
        event.preventDefault();
        open(trigger);
      }}
    }});
  }});
  document.querySelector("[data-lightbox-close]").addEventListener("click", close);
  dialog.addEventListener("click", (event) => {{
    if (event.target === dialog) close();
  }});
  dialog.addEventListener("cancel", (event) => {{
    event.preventDefault();
    close();
  }});
  dialog.addEventListener("keydown", (event) => {{
    if (event.key === "Escape") {{
      event.preventDefault();
      close();
    }}
  }});
}})();
</script>
</main></body></html>'''


def main(argv: list[str] | None = None) -> int:
    """Build the comparison page from a candidate workspace."""

    parser = argparse.ArgumentParser(description="Generate five graph-backed cell renderings.")
    parser.add_argument("candidate_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    panel = build_panel(args.candidate_root)
    comparison = build_comparison(panel)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(comparison), encoding="utf-8", newline="\n")
    for name in RENDERING_NAMES:
        metric = comparison["metrics"][name]
        print(
            f"{name}: {metric['produced']}/{metric['attempted']} produced; "
            f"{metric['failures']} failures; empty/placeholder {metric['empty_or_placeholder']}; "
            f"distribution {metric['distribution']}; median {metric['median']} {metric['unit']}; "
            f"max {metric['max']} {metric['unit']}"
        )
        for dimension in metric.get("svg_dimensions", []):
            print(
                f"  SVG {dimension['document_id']} line {dimension['line']}: "
                f"{dimension['width']:g} x {dimension['height']:g} "
                f"(viewBox {dimension['viewbox_width']:g} x {dimension['viewbox_height']:g})"
            )
    print(f"{output}: {len(comparison['selected'])} fixed cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
