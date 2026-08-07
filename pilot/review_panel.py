"""Build a self-contained two-column review panel from a candidate workspace.

This pilot is a read-only projection of the candidate run.  It joins every
printed anchor from the source reports to the candidate row, then reads the
promoted operation, rule, and edge data from the candidate draft.  It does not
call a provider, write graph artifacts, or assign a human verdict.
The left column keeps two lossless projections of the promoted graph: a role-labelled
tree and the same tree flattened into math.  The right column renders the graph as a
vertical flow.  Positions carry meaning there: values enter from the top, results leave
from the bottom, and moderators enter from the right.  This is a read-only pilot
projection; it never calls a provider, writes graph artifacts, or assigns a verdict.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from html import escape
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

import yaml

try:
    from . import cell_access
except ImportError:
    import cell_access


REPORT_SUFFIX = "_derive_cells_report.yaml"
OUTCOME_STATUSES = {"derived", "repaired", "review_gap", "skipped", "error", "errored"}
BRANCH_OPERATIONS = frozenset({"IF", "IF_ELSE", "LOOKUP_TABLE", "LOOKUP_BRACKET"})
MODERATOR_ROLES = frozenset({"threshold", "key", "default", "multiplier", "subtrahend"})
FORM_LINE_RE = re.compile(r"_root_line_(?P<line>[0-9]+[a-z]?|[a-z])$")
FLOW_SVG_RE = re.compile(
    r'<svg[^>]*class="flow-svg"[^>]*width="(?P<width>[0-9.]+)"[^>]*height="(?P<height>[0-9.]+)"'
)


def _text(value: Any) -> str:
    """Return a source value as text without rewriting its contents."""

    return "" if value is None else str(value)


def _line(value: Any) -> str:
    """Return the case-insensitive printed-anchor key used by the reports."""

    return _text(value).strip().lower()


def _load_yaml(path: Path, *, default: Any = None) -> Any:
    """Load one YAML artifact, returning ``default`` for an empty file."""

    if not path.is_file():
        return default
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return default if value is None else value


def _as_list(value: Any) -> list[dict[str, Any]]:
    """Keep only object records from a YAML list."""

    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _indexed_rows(rows: Iterable[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Index rows by line while retaining order for duplicate printed lines."""

    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = _line(row.get("line"))
        if key:
            result[key].append(dict(row))
    return result


def _take(index: dict[str, list[dict[str, Any]]], key: str) -> dict[str, Any] | None:
    """Consume one row for an anchor, preserving duplicate-line alignment."""

    values = index.get(key) or []
    return values.pop(0) if values else None


def _take_candidate(
    index: dict[str, list[dict[str, Any]]],
    key: str,
    *,
    skipped_anchor: bool,
) -> dict[str, Any] | None:
    """Match candidate evidence without consuming an admitted duplicate for a header."""

    values = index.get(key) or []
    if not values:
        return None
    candidate = values[0]
    status = cell_access.candidate_status(cell_access.join_rows(candidate=candidate)).value
    is_skipped_candidate = status is not None and status.strip().lower() == "skipped"
    if skipped_anchor and not is_skipped_candidate:
        return None
    return values.pop(0)


def _find_report(candidate_root: Path, document_id: str) -> Path:
    """Find the one source report belonging to a candidate document."""

    matches = sorted(
        path
        for path in (candidate_root / "source_reports").glob(f"*{document_id}{REPORT_SUFFIX}")
        if path.is_file()
    )
    if len(matches) != 1:
        raise ValueError(f"expected one source report for {document_id}, found {len(matches)}")
    return matches[0]


def _draft_dir(candidate_root: Path, year: Any, document_id: str) -> Path:
    """Return the candidate draft directory for one source-report document."""

    return candidate_root / "graph" / str(year) / "_drafts" / document_id


def _candidate_rows(candidate_root: Path, year: Any, document_id: str) -> dict[str, list[dict[str, Any]]]:
    """Load candidate rows by line, with duplicate lines kept in order."""

    path = _draft_dir(candidate_root, year, document_id) / "rows.yaml"
    return _indexed_rows(_as_list(_load_yaml(path, default=[])))


def _instruction_coverage(rows_by_line: Mapping[str, list[Mapping[str, Any]]]) -> dict[str, Any]:
    """Count instruction text on every candidate row through the cell accessor."""

    rows = [row for values in rows_by_line.values() for row in values]
    present = sum(
        cell_access.instruction_section(cell_access.join_rows(candidate=row)).present
        for row in rows
    )
    return {
        "row_count": len(rows),
        "present": present,
        "absent": len(rows) - present,
    }


def _source_rows(report: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Load derivation rows by line, with duplicate lines kept in order."""

    return _indexed_rows(_as_list(report.get("rows_detail")))


def _merge_anchor(
    document_id: str,
    index: int,
    anchor: Mapping[str, Any],
    source: Mapping[str, Any] | None,
    candidate: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Join one denominator anchor to source and candidate row evidence."""

    line = _line(anchor.get("anchor") or anchor.get("line"))
    skip_reason = _text(anchor.get("skip_reason")).strip()
    source_row = dict(source) if source is not None else {}
    candidate_row = dict(candidate) if candidate is not None else {}
    cell = cell_access.join_rows(anchor=anchor, source=source_row, candidate=candidate_row)
    source_status_value = cell_access.source_status(cell)
    candidate_status_value = cell_access.candidate_status(cell)
    source_status = _text(source_status_value.value).strip().lower()
    candidate_status = _text(candidate_status_value.value).strip().lower()
    status_value = cell_access.status(cell)
    status = status_value.value.strip().lower() if status_value.value is not None else ""
    if not status:
        status = "skipped" if skip_reason else "missing"
    if skip_reason:
        status = "skipped"

    label = cell_access.label(cell).value
    form_face = cell_access.form_face(cell).value
    instruction = cell_access.instruction_section(cell).value
    findings = list(cell_access.findings(cell))
    if skip_reason and not findings:
        findings = [{"kind": "skipped_anchor", "message": skip_reason}]
    if not skip_reason and source is None:
        findings.append({"kind": "missing_source_row", "message": "source report row is absent"})
    if not skip_reason and candidate is None:
        findings.append({"kind": "missing_candidate_row", "message": "candidate row is absent"})
    review_gap_value = cell_access.review_gap(cell)
    review_gap = review_gap_value.value.strip() if review_gap_value.value is not None else ""
    if not review_gap and status in {"error", "errored", "missing"}:
        error_value = cell_access.error(cell)
        review_gap = error_value.value.strip() if error_value.value is not None else ""
    if review_gap and not any(_finding_text(item) == review_gap for item in findings):
        findings.append({"kind": "review_gap", "message": review_gap})

    return {
        "document_id": document_id,
        "year": _text(anchor.get("year") or source_row.get("year") or "2025"),
        "anchor_index": index,
        "anchor_id": f"{document_id}#anchor={index}:line={line}",
        "line": line,
        "label": label,
        "form_face": form_face,
        "instruction": instruction,
        "status": status,
        "source_status": source_status,
        "candidate_status": candidate_status,
        "findings": findings,
        "review_gap": review_gap,
        "node_id": _text(cell_access.node_id(cell).value).strip(),
        "candidate_expression": cell_access.expression(cell),
        "candidate_rendered": cell_access.rendered_wording(cell).value,
        "quote": cell_access.quote(cell).value,
        "quote_span_id": cell_access.quote_span_id(cell).value,
    }


def _load_graph(candidate_root: Path, year: Any, document_id: str) -> dict[str, Any]:
    """Load the candidate graph records used by the operation column."""

    draft = _draft_dir(candidate_root, year, document_id)
    nodes = {
        _text(item.get("node_id")): item
        for item in _as_list(_load_yaml(draft / "nodes.yaml", default=[]))
        if _text(item.get("node_id"))
    }
    edges = _as_list(_load_yaml(draft / "edges.yaml", default=[]))
    rules = {
        _text(item.get("rule_id")): item
        for item in _as_list(_load_yaml(draft / "rules.yaml", default=[]))
        if _text(item.get("rule_id"))
    }
    edges_by_target: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        target = _text(edge.get("target"))
        if target:
            edges_by_target[target].append(edge)
    return {
        "nodes": nodes,
        "edges": edges,
        "rules": rules,
        "edges_by_target": edges_by_target,
    }


def _graph_jargon_nodes(document_id: str, graph: Mapping[str, Any]) -> list[dict[str, str]]:
    """Report graph node ids and labels containing the banned human-facing term."""

    result = []
    for node_id, node in graph["nodes"].items():
        label = cell_access.graph_node_label(graph, node_id).value
        label = "" if label is None else label
        if "floor" in node_id.lower() or "floor" in label.lower():
            result.append({"document_id": document_id, "node_id": node_id})
    return result


def _target_rules(graph: Mapping[str, Any], node_id: str) -> tuple[list[str], list[str]]:
    """Return direct rule ids and their operations for one graph target."""

    edges = graph["edges_by_target"].get(node_id, [])
    rules = graph["rules"]
    rule_ids: list[str] = []
    operations: list[str] = []
    for edge in edges:
        rule_id = _text(edge.get("rule_id")).strip()
        if rule_id and rule_id not in rule_ids:
            rule_ids.append(rule_id)
        operation = _text((rules.get(rule_id) or {}).get("operation")).strip().upper()
        if operation and operation not in operations:
            operations.append(operation)
    return rule_ids, operations


def _leaf(graph: Mapping[str, Any], node_id: str) -> dict[str, Any]:
    """Build a flow leaf from a graph node without inventing a label."""

    node = graph["nodes"].get(node_id)
    if not isinstance(node, Mapping):
        node = {}
    constant = node.get("constant_value")
    if constant is not None:
        return {"kind": "constant", "node_id": node_id, "value": constant}
    return {
        "kind": "reference",
        "node_id": node_id,
        "line": _line_reference(node_id),
        "label": cell_access.graph_node_label(graph, node_id).value,
    }


def _line_reference(node_id: str) -> str | None:
    """Return a printed line key for a plain form-line node id."""

    match = FORM_LINE_RE.search(node_id)
    return match.group("line") if match else None


def _is_referenced_line(node_id: str) -> bool:
    """Return whether a nested graph node is a printed line reference."""

    return _line_reference(node_id) is not None


def _graph_tree(graph: Mapping[str, Any], node_id: str, stack: tuple[str, ...] = (), *, root: bool = False) -> dict[str, Any]:
    """Build a graph-shaped expression tree for flow projection."""

    if not node_id or node_id in stack:
        return _leaf(graph, node_id)
    if not root and _is_referenced_line(node_id):
        return _leaf(graph, node_id)
    rule_ids, operations = _target_rules(graph, node_id)
    node = graph["nodes"].get(node_id) or {}
    if not operations:
        return _leaf(graph, node_id)
    operation = operations[0]
    if operation == "REQUIRE_INPUT" and not root:
        return _leaf(graph, node_id)
    operands: list[dict[str, Any]] = []
    for edge in cell_access.graph_operands(graph, node_id):
        source = _text(edge.get("node_id"))
        child = _graph_tree(graph, source, stack + (node_id,))
        operands.append(
            {
                "role": edge["role"],
                "node_id": source,
                "edge_id": _text(edge.get("edge_id")),
                "tree": child,
            }
        )
    return {
        "kind": "operation",
        "operation": operation,
        "node_id": node_id,
        "rule_ids": rule_ids,
        "operands": operands,
        "label": cell_access.graph_node_label(graph, node_id).value,
    }


def _graph_projection(row: Mapping[str, Any], graph: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return the promoted graph operation and direct edge evidence for a row."""

    node_id = _text(row.get("node_id")).strip()
    if not node_id or node_id not in graph["nodes"]:
        return None
    rule_ids, operations = _target_rules(graph, node_id)
    if not operations:
        return None
    operands = list(cell_access.graph_operands(graph, node_id))
    return {
        "node_id": node_id,
        "operation": operations[0] if len(operations) == 1 else operations,
        "rule_ids": rule_ids,
        "operands": operands,
        "tree": _graph_tree(graph, node_id, root=True),
    }


def _finding_text(value: Any) -> str:
    """Render a finding record using only its stored fields."""

    if isinstance(value, Mapping):
        kind = _text(value.get("kind")).strip()
        message = _text(value.get("message") or value.get("error")).strip()
        if kind and message:
            return f"{kind}: {message}"
        return kind or message or _text(dict(value))
    return _text(value)


def _tree_depth(tree: Mapping[str, Any]) -> int:
    """Return operation depth, where a leaf has depth zero."""

    if tree.get("kind") != "operation":
        return 0
    children = [item.get("tree") for item in tree.get("operands", []) if isinstance(item, Mapping)]
    depths = [_tree_depth(child) for child in children if isinstance(child, Mapping)]
    return 1 + (max(depths) if depths else 0)


def _has_branch(tree: Mapping[str, Any]) -> bool:
    """Return whether a graph tree contains a branching operation."""

    if tree.get("kind") != "operation":
        return False
    if _text(tree.get("operation")).upper() in BRANCH_OPERATIONS:
        return True
    return any(
        _has_branch(item["tree"])
        for item in tree.get("operands", [])
        if isinstance(item, Mapping) and isinstance(item.get("tree"), Mapping)
    )


def _flow_mode(tree: Mapping[str, Any] | None) -> str:
    """Apply review notation rule 9 to one projected graph tree."""

    if not tree or tree.get("kind") != "operation":
        return "none"
    if _has_branch(tree):
        return "diagram"
    return "chain" if _tree_depth(tree) > 1 else "none"


def _tree_key(tree: Mapping[str, Any]) -> tuple[Any, ...]:
    """Return a structural key used to share repeated operation subtrees."""

    if tree.get("kind") != "operation":
        if tree.get("kind") == "constant":
            return ("constant", _text(tree.get("value")))
        return ("reference", _text(tree.get("line")) or _text(tree.get("node_id")))
    operands = tuple(
        (
            _text(item.get("role")),
            _tree_key(item["tree"]),
        )
        for item in tree.get("operands", [])
        if isinstance(item, Mapping) and isinstance(item.get("tree"), Mapping)
    )
    return ("operation", _text(tree.get("operation")), operands)


def _flow_arrow_count(tree: Mapping[str, Any], seen: set[tuple[Any, ...]] | None = None) -> int:
    """Count arrows the flow renderer will emit, sharing repeated operations."""

    if tree.get("kind") != "operation":
        return 0
    seen = set() if seen is None else seen
    key = _tree_key(tree)
    if key in seen:
        return 0
    seen.add(key)
    return sum(
        1 + _flow_arrow_count(item["tree"], seen)
        for item in tree.get("operands", [])
        if isinstance(item, Mapping) and isinstance(item.get("tree"), Mapping)
    )


def build_panel(candidate_root: str | Path) -> dict[str, Any]:
    """Build all printed-anchor panels from one real candidate workspace."""

    root = Path(candidate_root).resolve()
    manifest = _load_yaml(root / "candidate.yaml", default={})
    if not isinstance(manifest, Mapping):
        raise ValueError(f"candidate manifest is not an object: {root / 'candidate.yaml'}")
    documents = [_text(value) for value in manifest.get("documents", []) if _text(value)]
    if not documents:
        raise ValueError("candidate manifest has no documents")
    year = _text(manifest.get("year") or "2025")
    panels: list[dict[str, Any]] = []
    graph_jargon_nodes: list[dict[str, str]] = []
    instruction_by_document: dict[str, dict[str, Any]] = {}
    for document_id in documents:
        report = _load_yaml(_find_report(root, document_id), default={})
        if not isinstance(report, Mapping):
            raise ValueError(f"source report for {document_id} is not an object")
        denominator = report.get("denominator")
        anchors = denominator.get("anchors") if isinstance(denominator, Mapping) else None
        if not isinstance(anchors, list):
            raise ValueError(f"source report for {document_id} has no denominator anchors")
        source_rows = _source_rows(report)
        candidate_rows = _candidate_rows(root, year, document_id)
        instruction_by_document[document_id] = _instruction_coverage(candidate_rows)
        graph = _load_graph(root, year, document_id)
        graph_jargon_nodes.extend(_graph_jargon_nodes(document_id, graph))
        for index, anchor in enumerate(anchors, start=1):
            if not isinstance(anchor, Mapping):
                raise ValueError(f"{document_id}: denominator anchor {index} is not an object")
            line = _line(anchor.get("anchor") or anchor.get("line"))
            skip_reason = _text(anchor.get("skip_reason")).strip()
            source = None if skip_reason else _take(source_rows, line)
            # A skipped operation still has valid candidate text evidence.  Keep the
            # candidate row attached so the source column answers the same question for
            # every printed anchor; the missing operation remains a visible hole.
            candidate = _take_candidate(candidate_rows, line, skipped_anchor=bool(skip_reason))
            row = _merge_anchor(document_id, index, anchor, source, candidate)
            projection = _graph_projection(row, graph)
            tree = projection.get("tree") if projection else None
            mode = _flow_mode(tree)
            row["graph"] = projection
            row["flow_mode"] = mode
            row["flow_depth"] = _tree_depth(tree) if isinstance(tree, Mapping) else 0
            row["flow_arrows"] = _flow_arrow_count(tree) if isinstance(tree, Mapping) else 0
            row["hole"] = projection is None
            flow_metrics = _flow_metrics(_flow_html(row))
            row["flow_svg_dimensions"] = flow_metrics["dimensions"]
            row["moderator_arrows"] = flow_metrics["moderator_arrows"]
            row["moderator_arrows_without_labels"] = flow_metrics["moderator_arrows_without_labels"]
            row["node_boxes_overlap_free"] = flow_metrics["node_boxes_overlap_free"]
            panels.append(row)

    mode_counts = {mode: sum(item["flow_mode"] == mode for item in panels) for mode in ("diagram", "chain", "none")}
    flow_arrow_distribution = Counter(
        item["flow_arrows"]
        for item in panels
        if item["flow_mode"] in {"diagram", "chain"}
    )
    text_presence = {
        "caption": sum(item["label"] is not None for item in panels),
        "instruction": sum(item["instruction"] is not None for item in panels),
        "operation": sum(item["graph"] is not None for item in panels),
    }
    text_absence = {
        key: len(panels) - value for key, value in text_presence.items()
    }
    instruction_row_count = sum(item["row_count"] for item in instruction_by_document.values())
    instruction_present = sum(item["present"] for item in instruction_by_document.values())
    instruction_coverage = {
        "row_count": instruction_row_count,
        "present": instruction_present,
        "absent": instruction_row_count - instruction_present,
        "documents": instruction_by_document,
    }
    flow_svg_dimensions = [
        {
            "document_id": item["document_id"],
            "line": item["line"],
            **item["flow_svg_dimensions"],
        }
        for item in panels
        if isinstance(item.get("flow_svg_dimensions"), Mapping)
    ]
    flow_geometry = {
        "svg_count": len(flow_svg_dimensions),
        "connector_start_directions_unique": len(flow_svg_dimensions)
        == sum(1 for item in panels if item.get("flow_svg_dimensions") is not None),
        "edge_labels_outside_nodes": len(flow_svg_dimensions)
        == sum(1 for item in panels if item.get("flow_svg_dimensions") is not None),
        "node_boxes_overlap_free": len(flow_svg_dimensions)
        == sum(1 for item in panels if item.get("node_boxes_overlap_free") is True),
        "moderator_arrows": sum(item["moderator_arrows"] for item in panels),
        "moderator_arrows_without_labels": sum(item["moderator_arrows_without_labels"] for item in panels),
    }
    return {
        "schema_version": 1,
        "kind": "review_panel",
        "source_candidate": str(root),
        "year": year,
        "documents": documents,
        "denominator": len(panels),
        "holes": sum(1 for item in panels if item["hole"]),
        "flow_modes": mode_counts,
        "flow_arrow_distribution": dict(sorted(flow_arrow_distribution.items())),
        "max_flow_arrows": max(flow_arrow_distribution, default=0),
        "text_presence": text_presence,
        "text_absence": text_absence,
        "instruction_coverage": instruction_coverage,
        "flow_geometry": flow_geometry,
        "flow_svg_dimensions": flow_svg_dimensions,
        "graph_jargon_nodes": graph_jargon_nodes,
        "panels": panels,
    }


def _source_block(title: str, value: str | None) -> str:
    """Render one separate source block without joining source layers."""

    if value is not None:
        content = value
    elif title == "Instruction page":
        content = "No joined instruction section."
    else:
        content = f"No {title.lower()} text recorded."
    empty = " empty" if value is None else ""
    return (
        f'<section class="source-block{empty}"><h4>{escape(title)}</h4>'
        f"<pre>{escape(content)}</pre></section>"
    )


def _finding_list(findings: Iterable[Any]) -> str:
    """Render stored findings as a visible list."""

    values = [_finding_text(item) for item in findings if _finding_text(item)]
    if not values:
        return "<p>No finding recorded.</p>"
    return "<ul>" + "".join(f"<li>{escape(value)}</li>" for value in values) + "</ul>"


def _operation_html(row: Mapping[str, Any]) -> str:
    """Render the graph operation column, including an explicit hole state."""

    graph = row.get("graph")
    if not isinstance(graph, Mapping):
        candidate_rendered_value = row.get("candidate_rendered")
        candidate_rendered = "" if candidate_rendered_value is None else str(candidate_rendered_value)
        attempted = (
            f'<h4>Candidate expression held back</h4><pre>{escape(candidate_rendered)}</pre>'
            if candidate_rendered_value is not None
            else ""
        )
        return (
            '<div class="operation-hole"><strong>No promoted graph operation.</strong>'
            f"{attempted}<h4>Finding</h4>{_finding_list(row.get('findings') if isinstance(row.get('findings'), list) else [])}</div>"
        )

    operation = graph.get("operation")
    operation_text = ", ".join(str(value) for value in operation) if isinstance(operation, list) else _text(operation)
    rendered_value = row.get("candidate_rendered")
    rendered_html = (
        escape(str(rendered_value))
        if rendered_value is not None
        else "No rendered expression in candidate report."
    )
    rule_ids = graph.get("rule_ids") if isinstance(graph.get("rule_ids"), list) else []
    rule_html = "<ul>" + "".join(f"<li><code>{escape(_text(value))}</code></li>" for value in rule_ids) + "</ul>"
    operands = graph.get("operands") if isinstance(graph.get("operands"), list) else []
    if operands:
        operand_html = "<ul>"
        for operand in operands:
            source = escape(_text(operand.get("node_id")))
            role = escape(_text(operand.get("role")))
            label_value = operand.get("label")
            label_html = (
                f'<pre class="graph-label">{escape(str(label_value))}</pre>'
                if label_value is not None
                else ""
            )
            operand_html += f"<li><code>{source}</code> <span>role={role}</span>{label_html}</li>"
        operand_html += "</ul>"
    else:
        operand_html = "<p>No promoted operands.</p>"
    return (
        f'<p class="graph-operation"><span>Graph operation</span> <code>{escape(operation_text)}</code></p>'
        f'<h4>Rendered expression</h4><pre>{rendered_html}</pre>'
        f'<h4>Rule id</h4>{rule_html}'
        f'<h4>Operands and edge roles</h4>{operand_html}'
    )


def _leaf_text(tree: Mapping[str, Any]) -> str:
    """Return a human-facing leaf label without exposing a graph node id."""

    if tree.get("kind") == "constant":
        return _text(tree.get("value"))
    line = _text(tree.get("line")).strip()
    if line:
        return f"line {line}"
    node_id = _text(tree.get("node_id")).lower()
    if "filing_status" in node_id:
        return "filing status"
    label = _text(tree.get("label")).strip()
    if label.lower().startswith("source "):
        return "source input"
    return label or "input"


def _math_text(tree: Mapping[str, Any]) -> str:
    """Flatten the lossless graph tree, omitting roles implied by position."""

    if tree.get("kind") != "operation":
        return _leaf_text(tree)
    operation = _text(tree.get("operation")).upper() or "operation"
    operands = []
    for index, item in enumerate(tree.get("operands", [])):
        if not isinstance(item, Mapping) or not isinstance(item.get("tree"), Mapping):
            continue
        role = _text(item.get("role")).strip()
        child = _math_text(item["tree"])
        if _role_is_implied(tree, index, role):
            role = ""
        operands.append(f"{role}={child}" if role else child)
    return f"{operation}({', '.join(operands)})"


def _role_is_implied(tree: Mapping[str, Any], index: int, role: str) -> bool:
    """Return whether an operation and operand position already state ``role``."""

    operation = _text(tree.get("operation")).upper()
    role = role.strip()
    if operation == "SUM":
        return role == "addend"
    if operation == "SUBTRACT":
        return role == ("minuend" if index == 0 else "subtrahend")
    if operation == "MULTIPLY":
        return role == ("multiplicand" if index == 0 else "multiplier")
    return False


def _flow_tree_html(tree: Mapping[str, Any], seen: set[tuple[Any, ...]] | None = None) -> str:
    """Render the lossless tree, retaining only roles not implied by position."""

    seen = set() if seen is None else seen
    if tree.get("kind") != "operation":
        return f'<div class="tree-leaf"><span>{escape(_leaf_text(tree))}</span></div>'
    key = _tree_key(tree)
    if key in seen:
        return '<div class="tree-reference">same expression as above</div>'
    seen.add(key)
    operation = escape(_text(tree.get("operation")))
    children = []
    for index, operand in enumerate(tree.get("operands", [])):
        if not isinstance(operand, Mapping) or not isinstance(operand.get("tree"), Mapping):
            continue
        raw_role = _text(operand.get("role")).strip()
        role = "" if _role_is_implied(tree, index, raw_role) else escape(raw_role)
        child = _flow_tree_html(operand["tree"], seen)
        role_html = f'<span class="tree-role">{role}</span>' if role else ""
        children.append(
            f'<div class="tree-edge">{role_html}'
            f'<span class="tree-arrow">-&gt;</span>{child}</div>'
        )
    child_html = f'<div class="tree-children">{"".join(children)}</div>' if children else ""
    return f'<div class="tree-box"><strong>{operation}</strong>{child_html}</div>'


def _flow_wrap(text: str, width: int) -> list[str]:
    """Wrap SVG labels deterministically so geometry matches visible text."""

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
        lines.append(current)
    return lines or [""]


def _flow_operation_label(tree: Mapping[str, Any]) -> str:
    """Name one flow box without inlining hidden graph identifiers."""

    operation = _text(tree.get("operation")).upper() or "OPERATION"
    normal = []
    for item in tree.get("operands", []):
        if not isinstance(item, Mapping) or not isinstance(item.get("tree"), Mapping):
            continue
        role = _text(item.get("role"))
        if role in MODERATOR_ROLES:
            continue
        child = item["tree"]
        normal.append("amount" if child.get("kind") == "operation" else _leaf_text(child))
    if operation == "MULTIPLY":
        return f"multiply: {' * '.join(normal) or 'amount'}"
    if operation == "SUBTRACT":
        return f"subtract: {' - '.join(normal) or 'amount'}"
    if operation == "SUM":
        return f"sum: {' + '.join(normal) or 'amount'}"
    if operation == "MAX":
        return f"max: {', '.join(normal) or 'amount'}"
    if operation == "MIN":
        return f"min: {', '.join(normal) or 'amount'}"
    if operation == "COPY":
        return normal[0] if normal else "copy"
    return operation


def _lookup_label(tree: Mapping[str, Any], role: str) -> str:
    """Render a lookup as a table node; its key and variants need no arrows."""

    lines = [role or "lookup table"]
    for item in tree.get("operands", []):
        if not isinstance(item, Mapping) or not isinstance(item.get("tree"), Mapping):
            continue
        item_role = _text(item.get("role")).strip() or "value"
        lines.append(f"{item_role}: {_leaf_text(item['tree'])}")
    return "\n".join(lines)


def _flow_svg(row: Mapping[str, Any], tree: Mapping[str, Any]) -> str:
    """Render a vertical flow with a single right-hand moderator gutter."""

    width = 620.0
    centre_x = 255.0
    gutter_x = 455.0
    node_width = 150.0
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    edge_labels: list[dict[str, Any]] = []
    node_number = 0
    vertical_gap = 18.0
    gutter_next_y = 18.0

    def measured_height(kind: str, label: str, node_width_value: float) -> float:
        lines = _flow_wrap(label, max(12, int(node_width_value / 7.0)))
        height = max(42.0, 22.0 + len(lines) * 16.0)
        if kind == "table":
            height = max(74.0, height)
        return height

    def add_node(kind: str, label: str, x: float, y: float, node_width_value: float = node_width) -> dict[str, Any]:
        nonlocal node_number
        node_number += 1
        node_height = measured_height(kind, label, node_width_value)
        node = {
            "kind": kind,
            "label": label,
            "x": x,
            "y": y,
            "width": node_width_value,
            "height": node_height,
            "number": node_number,
        }
        nodes.append(node)
        return node

    def centre(node: Mapping[str, Any]) -> float:
        return float(node["x"]) + float(node["width"]) / 2.0

    def add_edge(
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        *,
        role: str = "",
        label_x: float | None = None,
        label_y: float | None = None,
    ) -> None:
        edge = {
            "start_x": start_x,
            "start_y": start_y,
            "end_x": end_x,
            "end_y": end_y,
            "role": role,
        }
        edges.append(edge)
        if role:
            edge_labels.append(
                {
                    "x": (start_x + end_x) / 2.0 if label_x is None else label_x,
                    "y": (start_y + end_y) / 2.0 - 6.0 if label_y is None else label_y,
                    "text": role,
                    "role": role,
                }
            )

    def add_moderator(parent: Mapping[str, Any], item: Mapping[str, Any]) -> None:
        nonlocal gutter_next_y
        child = item["tree"]
        role = _text(item.get("role")).strip() or "moderator"
        if child.get("kind") == "operation" and _text(child.get("operation")).upper() in {"LOOKUP_TABLE", "LOOKUP_BRACKET"}:
            label = _lookup_label(child, role)
            kind = "table"
        elif child.get("kind") == "operation":
            label = _flow_operation_label(child)
            kind = "box"
        else:
            label = _leaf_text(child)
            kind = "value"
        moderator_height = measured_height(kind, label, 145.0)
        preferred_y = float(parent["y"]) + (float(parent["height"]) - moderator_height) / 2.0
        moderator_y = max(18.0, preferred_y, gutter_next_y)
        moderator = add_node(kind, label, gutter_x, moderator_y, 145.0)
        gutter_next_y = moderator["y"] + moderator["height"] + vertical_gap
        add_edge(
            moderator["x"],
            moderator["y"] + moderator["height"] / 2.0,
            parent["x"] + parent["width"],
            parent["y"] + parent["height"] / 2.0,
            role=role,
            label_x=(moderator["x"] + parent["x"] + parent["width"]) / 2.0,
            label_y=max(12.0, min(moderator["y"], parent["y"]) - 20.0),
        )

    def add_inputs(parent: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
        if not items:
            return
        input_width = 84.0
        input_gap = 18.0
        total_width = len(items) * input_width + max(0, len(items) - 1) * input_gap
        input_centre = centre(parent)
        input_centre = min(input_centre, gutter_x - vertical_gap - total_width / 2.0)
        input_centre = max(input_centre, vertical_gap + total_width / 2.0)
        start = input_centre - total_width / 2.0
        input_height = max(
            measured_height("input", _leaf_text(item["tree"]), input_width)
            for item in items
        )
        input_y = max(18.0, float(parent["y"]) - input_height - vertical_gap)
        for index, item in enumerate(items):
            child = item["tree"]
            input_node = add_node("input", _leaf_text(child), start + index * (input_width + input_gap), input_y, input_width)
            add_edge(
                centre(input_node),
                input_node["y"] + input_node["height"],
                centre(parent),
                parent["y"],
                role="",
            )

    def operation_order(root: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        result: list[Mapping[str, Any]] = []

        def visit(node: Mapping[str, Any]) -> None:
            if node.get("kind") != "operation":
                return
            operation = _text(node.get("operation")).upper()
            if operation in {"LOOKUP_TABLE", "LOOKUP_BRACKET"}:
                return
            for item in node.get("operands", []):
                if not isinstance(item, Mapping) or not isinstance(item.get("tree"), Mapping):
                    continue
                if _text(item.get("role")) in MODERATOR_ROLES:
                    continue
                visit(item["tree"])
            result.append(node)

        visit(root)
        return result

    def place_operation_chain(root: Mapping[str, Any], start_y: float, x: float) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        order = operation_order(root)
        if not order:
            return None, []
        layout: list[tuple[Mapping[str, Any], str, float, float]] = []
        previous_bottom = None
        for operation in order:
            label = _flow_operation_label(operation)
            operation_height = measured_height("box", label, node_width)
            direct_items = [
                item
                for item in operation.get("operands", [])
                if isinstance(item, Mapping)
                and isinstance(item.get("tree"), Mapping)
                and _text(item.get("role")) not in MODERATOR_ROLES
                and item["tree"].get("kind") != "operation"
            ]
            direct_height = max(
                (measured_height("input", _leaf_text(item["tree"]), 84.0) for item in direct_items),
                default=0.0,
            )
            if previous_bottom is None:
                operation_y = max(float(start_y) + direct_height + vertical_gap, 54.0)
            else:
                operation_y = previous_bottom + direct_height + 2.0 * vertical_gap
            layout.append((operation, label, operation_y, operation_height))
            previous_bottom = operation_y + operation_height
        placed: dict[int, dict[str, Any]] = {}
        for operation, label, operation_y, _ in layout:
            placed[id(operation)] = add_node("box", label, x, operation_y)
        for operation in order:
            parent = placed[id(operation)]
            normal_items: list[Mapping[str, Any]] = []
            for item in operation.get("operands", []):
                if not isinstance(item, Mapping) or not isinstance(item.get("tree"), Mapping):
                    continue
                role = _text(item.get("role"))
                child = item["tree"]
                if role in MODERATOR_ROLES:
                    add_moderator(parent, item)
                elif child.get("kind") == "operation" and id(child) in placed:
                    child_node = placed[id(child)]
                    add_edge(centre(child_node), child_node["y"] + child_node["height"], centre(parent), parent["y"], role="")
                elif child.get("kind") != "operation":
                    normal_items.append(item)
            add_inputs(parent, normal_items)
        return placed.get(id(root)), list(placed.values())

    def branch_child_items(root: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
        items = [
            ("when_true", item["tree"])
            for item in root.get("operands", [])
            if isinstance(item, Mapping) and _text(item.get("role")) == "when_true" and isinstance(item.get("tree"), Mapping)
        ]
        items.extend(
            ("when_false", item["tree"])
            for item in root.get("operands", [])
            if isinstance(item, Mapping) and _text(item.get("role")) == "when_false" and isinstance(item.get("tree"), Mapping)
        )
        return items

    root_operation = _text(tree.get("operation")).upper() if tree.get("kind") == "operation" else ""
    if root_operation in {"LOOKUP_TABLE", "LOOKUP_BRACKET"}:
        table = add_node("table", _lookup_label(tree, "lookup table"), centre_x - 75.0, 42.0, 190.0)
        output = add_node("output", _text(row.get("line")) and f"line {_text(row.get('line'))}" or "result", centre_x - 70.0, table["y"] + table["height"] + 54.0, 140.0)
        add_edge(centre(table), table["y"] + table["height"], centre(output), output["y"])
    elif root_operation in {"IF", "IF_ELSE"}:
        operands = [item for item in tree.get("operands", []) if isinstance(item, Mapping) and isinstance(item.get("tree"), Mapping)]
        condition = next((item for item in operands if _text(item.get("role")) == "condition"), None)
        threshold = next((item for item in operands if _text(item.get("role")) == "threshold"), None)
        condition_node = add_node("input", _leaf_text(condition["tree"]) if condition else "condition", centre_x - 60.0, 24.0, 120.0)
        diamond = add_node("diamond", f"{_leaf_text(condition['tree']) if condition else 'condition'}?", centre_x - 85.0, 142.0, 170.0)
        add_edge(centre(condition_node), condition_node["y"] + condition_node["height"], centre(diamond), diamond["y"], role="")
        if threshold is not None:
            add_moderator(diamond, threshold)
        branch_roots: list[dict[str, Any]] = []
        branch_bottoms: list[float] = []
        branch_specs = branch_child_items(tree)
        branch_start_y = 326.0
        next_branch_y = branch_start_y
        for index, (role, child) in enumerate(branch_specs[:2]):
            branch_x = 112.0 if index == 0 else 300.0
            root_node, branch_nodes = place_operation_chain(child, next_branch_y, branch_x)
            if root_node is None:
                root_node = add_node("value", _leaf_text(child), branch_x, next_branch_y, 120.0)
            branch_roots.append(root_node)
            branch_bottoms.append(max(node["y"] + node["height"] for node in branch_nodes) if branch_nodes else root_node["y"] + root_node["height"])
            next_branch_y = branch_bottoms[-1] + 2.0 * vertical_gap
            add_edge(
                diamond["x"] + (diamond["width"] * 0.35 if index == 0 else diamond["width"] * 0.65),
                diamond["y"] + diamond["height"],
                centre(root_node),
                root_node["y"],
                role="Yes" if index == 0 else "No",
                label_y=diamond["y"] + diamond["height"] + 22.0,
            )
        output_y = max(branch_bottoms, default=diamond["y"] + diamond["height"]) + 58.0
        output = add_node("output", _text(row.get("line")) and f"line {_text(row.get('line'))}" or "result", centre_x - 70.0, output_y, 140.0)
        for branch_root in branch_roots:
            add_edge(centre(branch_root), branch_root["y"] + branch_root["height"], centre(output), output["y"])
    else:
        root_node, _ = place_operation_chain(tree, 54.0, centre_x - 75.0)
        if root_node is None:
            root_node = add_node("value", _leaf_text(tree), centre_x - 75.0, 54.0)
        output = add_node("output", _text(row.get("line")) and f"line {_text(row.get('line'))}" or "result", centre_x - 70.0, root_node["y"] + root_node["height"] + 54.0, 140.0)
        add_edge(centre(root_node), root_node["y"] + root_node["height"], centre(output), output["y"])

    directions = []
    for edge in edges:
        dx = edge["end_x"] - edge["start_x"]
        dy = edge["end_y"] - edge["start_y"]
        direction = (0 if abs(dx) < 0.01 else (1 if dx > 0 else -1), 0 if abs(dy) < 0.01 else (1 if dy > 0 else -1))
        directions.append((round(edge["start_x"], 2), round(edge["start_y"], 2), direction))
    if len(directions) != len(set(directions)):
        raise ValueError("flow connectors share a start point and direction")

    node_overlaps = [
        (first, second)
        for index, first in enumerate(nodes)
        for second in nodes[index + 1 :]
        if first["x"] < second["x"] + second["width"]
        and first["x"] + first["width"] > second["x"]
        and first["y"] < second["y"] + second["height"]
        and first["y"] + first["height"] > second["y"]
    ]
    if node_overlaps:
        first, second = node_overlaps[0]
        raise ValueError(
            "flow node boxes overlap: "
            f"{first['kind']}#{first['number']} and {second['kind']}#{second['number']}"
        )

    def label_box(label: Mapping[str, Any]) -> tuple[float, float, float, float]:
        lines = _flow_wrap(_text(label["text"]), 16)
        label_width = max(len(line) for line in lines) * 7.0 + 6.0
        label_height = len(lines) * 15.0
        return label["x"] - label_width / 2.0, label["y"] - label_height, label_width, label_height

    for label in edge_labels:
        for _ in range(20):
            lx, ly, lw, lh = label_box(label)
            collisions = [
                node
                for node in nodes
                if lx < node["x"] + node["width"]
                and lx + lw > node["x"]
                and ly < node["y"] + node["height"]
                and ly + lh > node["y"]
            ]
            if not collisions:
                break
            label["y"] -= 20.0
        else:
            raise ValueError(f"flow label {label['text']!r} cannot be placed outside node boxes")

    max_y = max(150.0, max(node["y"] + node["height"] for node in nodes) + 36.0)

    def svg_text(x: float, y: float, value: str, *, css_class: str = "flow-svg-label", width_chars: int = 20) -> str:
        return "".join(
            f'<text x="{x:g}" y="{y + index * 15:g}" class="{css_class}">{escape(line)}</text>'
            for index, line in enumerate(_flow_wrap(value, width_chars))
        )

    parts = [
        f'<svg class="flow-svg" width="{width:g}" height="{max_y:g}" viewBox="0 0 {width:g} {max_y:g}" role="img" aria-label="Vertical flow diagram" data-connector-starts-unique="true" data-edge-labels-outside-nodes="true" data-moderator-arrows-labelled="true" data-node-boxes-overlap-free="true">',
        '<defs><marker id="flow-arrowhead" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 z" /></marker></defs>',
    ]
    for edge in edges:
        midpoint_y = (edge["start_y"] + edge["end_y"]) / 2.0
        route_x = edge["start_x"] if abs(edge["start_x"] - edge["end_x"]) < 0.01 else None
        if route_x is None:
            path = f'M {edge["start_x"]:g} {edge["start_y"]:g} C {edge["start_x"]:g} {midpoint_y:g}, {edge["end_x"]:g} {midpoint_y:g}, {edge["end_x"]:g} {edge["end_y"]:g}'
        else:
            path = f'M {edge["start_x"]:g} {edge["start_y"]:g} L {edge["end_x"]:g} {edge["end_y"]:g}'
        css_class = "flow-edge flow-edge-moderator" if edge.get("role") in MODERATOR_ROLES else "flow-edge"
        parts.append(f'<path class="{css_class}" d="{path}" marker-end="url(#flow-arrowhead)" />')
    for label in edge_labels:
        parts.append(svg_text(label["x"], label["y"], _text(label["text"]), css_class="flow-edge-label", width_chars=16))
    for node in nodes:
        kind = node["kind"]
        x, y, node_width_value, node_height = node["x"], node["y"], node["width"], node["height"]
        css_class = {
            "table": "flow-svg-table",
            "input": "flow-svg-input",
            "output": "flow-svg-output",
            "value": "flow-svg-input",
            "diamond": "flow-svg-diamond",
        }.get(kind, "flow-svg-box")
        if kind == "diamond":
            points = f"{x + node_width_value / 2:g},{y:g} {x + node_width_value:g},{y + node_height / 2:g} {x + node_width_value / 2:g},{y + node_height:g} {x:g},{y + node_height / 2:g}"
            parts.append(f'<polygon class="{css_class}" points="{points}" />')
            parts.append(svg_text(x + 18.0, y + 23.0, node["label"], width_chars=19))
        else:
            parts.append(f'<rect class="{css_class}" x="{x:g}" y="{y:g}" width="{node_width_value:g}" height="{node_height:g}" rx="7" />')
            parts.append(svg_text(x + 9.0, y + 20.0, node["label"], width_chars=max(12, int(node_width_value / 7.0))))
    parts.append("</svg>")
    return "".join(parts)


def _flow_html(row: Mapping[str, Any]) -> str:
    """Render the right-hand positional flow column or its named finding."""

    tree = row.get("graph", {}).get("tree") if isinstance(row.get("graph"), Mapping) else None
    if not isinstance(tree, Mapping):
        return '<div class="flow-hole"><strong>No promoted flow.</strong><p>The operation is absent; see the stored finding.</p></div>'
    return f'<div class="flow-diagram">{_flow_svg(row, tree)}</div>'


def _flow_metrics(flow_html: str) -> dict[str, Any]:
    """Extract declared SVG dimensions and moderator-label evidence."""

    match = FLOW_SVG_RE.search(flow_html)
    if not match:
        return {
            "dimensions": None,
            "moderator_arrows": 0,
            "moderator_arrows_without_labels": 0,
            "node_boxes_overlap_free": False,
        }
    return {
        "dimensions": {"width": float(match.group("width")), "height": float(match.group("height"))},
        "moderator_arrows": flow_html.count("flow-edge-moderator"),
        "moderator_arrows_without_labels": 0 if 'data-moderator-arrows-labelled="true"' in flow_html else flow_html.count("flow-edge-moderator"),
        "node_boxes_overlap_free": 'data-node-boxes-overlap-free="true"' in flow_html,
    }


def _panel_html(row: Mapping[str, Any]) -> str:
    """Render one two-column panel with stable metadata for browser inspection."""

    status = _text(row.get("status")) or "missing"
    hole = "true" if row.get("hole") else "false"
    source_details = "".join(
        _source_block(title, row.get(key))
        for title, key in (("Label", "label"), ("Form face", "form_face"), ("Instruction page", "instruction"))
    )
    tree = row.get("graph", {}).get("tree") if isinstance(row.get("graph"), Mapping) else None
    tree_html = _flow_tree_html(tree) if isinstance(tree, Mapping) else _finding_list(row.get("findings", []))
    math_html = escape(_math_text(tree)) if isinstance(tree, Mapping) else "No promoted expression."
    return (
        f'<article class="review-panel" data-anchor="{escape(_text(row.get("anchor_id")), quote=True)}" '
        f'data-flow-mode="{escape(_text(row.get("flow_mode")), quote=True)}" data-hole="{hole}">'
        '<header class="panel-header">'
        f'<h2>{escape(_text(row.get("document_id")))} line {escape(_text(row.get("line")))}</h2>'
        f'<span class="status status-{escape(status)}">{escape(status)}</span>'
        f'<code>{escape(_text(row.get("anchor_id")))}</code></header>'
        f'<details class="source-evidence"><summary>IRS source evidence</summary><div class="source-evidence-grid">{source_details}</div></details>'
        '<div class="review-columns">'
        '<section class="column expression-column"><h3>Tree</h3>'
        f'<div class="tree-expression">{tree_html}</div>'
        '<h3>Math</h3>'
        f'<pre class="math-expression">{math_html}</pre>'
        f'<details class="graph-trace"><summary>Graph trace</summary>{_operation_html(row)}</details>'
        '</section>'
        f'<section class="column flow-column"><h3>Flow</h3>{_flow_html(row)}</section>'
        '</div></article>'
    )


def render_html(panel: Mapping[str, Any]) -> str:
    """Render the complete self-contained two-column review artifact."""

    modes = panel.get("flow_modes") or {}
    presence = panel.get("text_presence") if isinstance(panel.get("text_presence"), Mapping) else {}
    absence = panel.get("text_absence") if isinstance(panel.get("text_absence"), Mapping) else {}
    instruction_coverage = panel.get("instruction_coverage")
    if not isinstance(instruction_coverage, Mapping):
        instruction_coverage = {}
    coverage_documents = instruction_coverage.get("documents")
    coverage_parts = []
    if isinstance(coverage_documents, Mapping):
        for document_id in panel.get("documents") or []:
            item = coverage_documents.get(document_id)
            if isinstance(item, Mapping):
                coverage_parts.append(f"{_text(document_id)} {_text(item.get('present', 0))}/{_text(item.get('row_count', 0))}")
    coverage_detail = "; ".join(coverage_parts)
    geometry = panel.get("flow_geometry") if isinstance(panel.get("flow_geometry"), Mapping) else {}
    dimensions = panel.get("flow_svg_dimensions") if isinstance(panel.get("flow_svg_dimensions"), list) else []
    dimension_items = "".join(
        f'<li>{escape(_text(item.get("document_id")))} line {escape(_text(item.get("line")))}: '
        f'{escape(_text(item.get("width")))} x {escape(_text(item.get("height")))}</li>'
        for item in dimensions
        if isinstance(item, Mapping)
    )
    summary = (
        f"{_text(panel.get('denominator'))} printed anchors; {len(panel.get('documents') or [])} documents; "
        f"{_text(modes.get('diagram', 0))} branching trees / {_text(modes.get('chain', 0))} deeper trees / "
        f"{_text(modes.get('none', 0))} shallow trees; {_text(panel.get('holes', 0))} named findings; "
        f"captions {presence.get('caption', 0)} present / {absence.get('caption', 0)} absent; "
        f"instruction rows {presence.get('instruction', 0)} present / {absence.get('instruction', 0)} absent; "
        f"operations {presence.get('operation', 0)} present / {absence.get('operation', 0)} absent; "
        f"candidate instruction coverage {instruction_coverage.get('present', 0)}/{instruction_coverage.get('row_count', 0)} present "
        f"({coverage_detail})."
    )
    jargon_nodes = panel.get("graph_jargon_nodes") or []
    jargon_html = ""
    if jargon_nodes:
        items = "".join(
            f'<li><code>{escape(_text(item.get("document_id")))}: {escape(_text(item.get("node_id")))}</code></li>'
            for item in jargon_nodes
        )
        jargon_html = '<details class="jargon-note"><summary>Graph terminology to report (not changed)</summary>' f"<ul>{items}</ul></details>"
    panels = "\n".join(_panel_html(row) for row in panel.get("panels", []))
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Generated two-column review panel</title>
<style>
:root {{ color-scheme: light; font-family: Arial, sans-serif; background: #f3f5f7; color: #18212b; }}
body {{ margin: 0; padding: 24px; }}
main {{ max-width: 1900px; margin: 0 auto; }}
.summary {{ position: sticky; top: 0; z-index: 2; padding: 14px 18px; margin-bottom: 18px; background: #18212b; color: white; border-radius: 8px; box-shadow: 0 2px 8px #0004; }}
.summary h1 {{ margin: 0 0 6px; font-size: 1.25rem; }}
.summary p {{ margin: 5px 0; }}
.review-panel {{ margin: 0 0 18px; background: white; border: 1px solid #cbd3dc; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px #0001; }}
.panel-header {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; padding: 11px 16px; background: #e8edf2; border-bottom: 1px solid #cbd3dc; }}
.panel-header h2 {{ margin: 0; font-size: 1rem; }}
.panel-header code {{ margin-left: auto; color: #44515f; }}
.status {{ padding: 3px 8px; border: 1px solid #8795a5; border-radius: 12px; font-size: .78rem; }}
.status-derived {{ background: #e5f5e9; }}
.status-repaired {{ background: #fff2c7; }}
.status-review_gap, .status-error, .status-errored, .status-missing {{ background: #ffdede; }}
.status-skipped {{ background: #eef0f3; }}
.source-evidence {{ padding: 8px 16px; border-bottom: 1px solid #d8dee5; background: #fafbfc; }}
.source-evidence summary {{ cursor: pointer; font-weight: bold; }}
.source-evidence-grid {{ display: grid; grid-template-columns: repeat(3, minmax(180px, 1fr)); gap: 10px; margin-top: 10px; }}
.source-block {{ min-width: 0; padding: 8px; border-left: 3px solid #6584a3; background: #f7f9fb; }}
.source-block.empty {{ border-left-color: #c78b22; background: #fffaf0; }}
.source-block h4 {{ margin: 0 0 5px; font-size: .84rem; }}
pre {{ margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; font: .82rem/1.35 Consolas, monospace; }}
code {{ overflow-wrap: anywhere; font-family: Consolas, monospace; font-size: .82rem; }}
.review-columns {{ display: grid; grid-template-columns: minmax(280px, 1fr) minmax(520px, 2fr); gap: 0; }}
.column {{ min-width: 0; padding: 14px 16px 18px; }}
.column + .column {{ border-left: 1px solid #d8dee5; }}
.column h3 {{ margin: 0 0 12px; font-size: 1rem; }}
.column h3 + h3 {{ margin-top: 18px; }}
.tree-expression {{ padding: 10px; border: 1px solid #8795a5; background: #fbfcfd; overflow: auto; }}
.tree-box {{ display: inline-block; min-width: 125px; padding: 8px; border: 2px solid #40566d; border-radius: 6px; background: #e7f0f8; }}
.tree-box strong {{ display: block; text-align: center; }}
.tree-children {{ margin-top: 8px; padding-left: 12px; border-left: 2px solid #9aa7b4; }}
.tree-edge {{ display: flex; align-items: flex-start; gap: 5px; margin: 7px 0; min-width: max-content; }}
.tree-role {{ color: #18212b; font: .74rem Consolas, monospace; font-weight: bold; }}
.tree-arrow {{ color: #18212b; font-weight: bold; }}
.tree-leaf {{ display: inline-flex; min-width: 120px; padding: 7px; border: 1px solid #8795a5; border-radius: 4px; background: white; }}
.tree-reference {{ padding: 7px; border: 1px dashed #8795a5; background: white; }}
.math-expression {{ min-height: 52px; padding: 10px; border: 1px solid #8795a5; background: #fbfcfd; }}
.graph-trace {{ margin-top: 12px; padding: 8px; border: 1px solid #d8dee5; background: #fafbfc; }}
.graph-trace summary {{ cursor: pointer; font-weight: bold; }}
.graph-trace h4 {{ margin: 10px 0 5px; font-size: .84rem; }}
.graph-trace ul {{ margin: 5px 0; padding-left: 20px; }}
.graph-trace .operation-hole {{ margin-top: 8px; padding: 8px; border: 2px solid #c13c3c; background: #fff1f1; }}
.flow-diagram {{ padding: 10px; border: 2px solid #596d82; background: #fbfcfd; overflow: auto; }}
.flow-hole {{ padding: 12px; border: 2px solid #c13c3c; background: #fff1f1; }}
.flow-hole strong {{ color: #a32121; }}
.flow-svg {{ display: block; width: 620px; max-width: none; height: auto; background: white; }}
.flow-edge {{ fill: none; stroke: #18212b; stroke-width: 1.6; }}
.flow-edge-moderator {{ stroke-width: 2; }}
.flow-edge-label {{ fill: #18212b; font: bold 12px Consolas, monospace; paint-order: stroke; stroke: white; stroke-width: 4px; stroke-linejoin: round; }}
.flow-svg-label {{ fill: #18212b; font: 12px Arial, sans-serif; }}
.flow-svg-box {{ fill: #e7f0f8; stroke: #18212b; stroke-width: 2; }}
.flow-svg-input {{ fill: #f3f6f8; stroke: #18212b; stroke-width: 2; }}
.flow-svg-output {{ fill: #e7f0f8; stroke: #18212b; stroke-width: 2.2; }}
.flow-svg-table {{ fill: #eef7ee; stroke: #18212b; stroke-width: 2; }}
.flow-svg-diamond {{ fill: #fff3d1; stroke: #18212b; stroke-width: 2; }}
.geometry-checks, .svg-dimensions {{ margin-top: 10px; }}
.jargon-note {{ margin-top: 8px; }}
ul {{ margin: 5px 0; padding-left: 20px; }}
li {{ margin: 4px 0; overflow-wrap: anywhere; }}
@media (max-width: 1050px) {{ .review-columns {{ grid-template-columns: 1fr; }} .column + .column {{ border-left: 0; border-top: 1px solid #d8dee5; }} .panel-header code {{ margin-left: 0; width: 100%; }} .source-evidence-grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body><main data-two-column-layout="true">
<section class="summary"><h1>Generated two-column review panel</h1>
<p>{escape(summary)}</p>
<p>Tree and Math occupy the left third; the positional Flow occupies the right two thirds. Values enter from the top, results leave from the bottom, and moderators enter from the right.</p>
<p class="geometry-checks">Flow SVGs: {escape(_text(geometry.get('svg_count', 0)))}; connector starts and directions: checked; edge labels outside node boxes: checked; moderator arrows: {escape(_text(geometry.get('moderator_arrows', 0)))}; moderator arrows without labels: {escape(_text(geometry.get('moderator_arrows_without_labels', 0)))}. Labels remain explicit when colour is removed.</p>
{jargon_html}
<details class="svg-dimensions"><summary>Flow SVG dimensions</summary><ul>{dimension_items or '<li>No flow SVGs were produced.</li>'}</ul></details>
</section>
{panels}
</main></body>
</html>
'''


def main(argv: list[str] | None = None) -> int:
    """Run the pilot from a candidate workspace path."""

    parser = argparse.ArgumentParser(description="Generate a three-column review panel from a candidate workspace.")
    parser.add_argument("candidate_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    panel = build_panel(args.candidate_root)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(panel), encoding="utf-8", newline="\n")
    print(
        f"{output}: {panel['denominator']} anchors; "
        f"{panel['flow_modes']['diagram']} diagrams / "
        f"{panel['flow_modes']['chain']} chains / "
        f"{panel['flow_modes']['none']} none; {panel['holes']} holes; "
        f"captions {panel['text_presence']['caption']} present / "
        f"{panel['text_absence']['caption']} absent; "
        f"instruction rows {panel['text_presence']['instruction']} present / "
        f"{panel['text_absence']['instruction']} absent; "
        f"candidate instruction coverage {panel['instruction_coverage']['present']}/"
        f"{panel['instruction_coverage']['row_count']} present; "
        f"operations {panel['text_presence']['operation']} present / "
        f"{panel['text_absence']['operation']} absent"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
