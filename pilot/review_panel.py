"""Build a self-contained Tree and Math review panel from a candidate workspace.

This pilot is a read-only projection of the candidate run.  It joins every
printed anchor from the source reports to the candidate row, then reads the
promoted operation, rule, and edge data from the candidate draft.  It does not
call a provider, write graph artifacts, or assign a human verdict.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from html import escape
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

import yaml

try:
    from . import cell_access
except ImportError:
    import cell_access


REPORT_SUFFIX = "_derive_cells_report.yaml"
OUTCOME_STATUSES = {"derived", "repaired", "review_gap", "skipped", "error", "errored"}
FORM_LINE_RE = re.compile(r"_root_line_(?P<line>[0-9]+[a-z]?|[a-z])$")
STRUCTURAL_HOLE_REASONS = frozenset(
    {
        "structure_duplicate_anchor",
        "structure_header_anchor",
        "structure_non_cell_anchor",
    }
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
    model_outcome_value = cell_access.model_outcome(cell)
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
        "model_outcome": _text(model_outcome_value.value).strip(),
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


def _rule_parameters(graph: Mapping[str, Any], rule_ids: Sequence[str]) -> Mapping[str, Any]:
    """Return parameters for the first direct rule, if it is well formed."""
    rules = graph.get("rules")
    if not isinstance(rules, Mapping) or not rule_ids:
        return {}
    rule = rules.get(rule_ids[0])
    if not isinstance(rule, Mapping) or not isinstance(rule.get("parameters"), Mapping):
        return {}
    return rule["parameters"]


def _leaf(graph: Mapping[str, Any], node_id: str) -> dict[str, Any]:
    """Build a tree leaf from a graph node without inventing a label."""

    node = graph["nodes"].get(node_id)
    if not isinstance(node, Mapping):
        node = {}
    constant = node.get("constant_value")
    if constant is not None:
        return {"kind": "constant", "node_id": node_id, "value": constant}
    result = {
        "kind": "reference",
        "node_id": node_id,
        "line": _line_reference(node_id),
        "label": cell_access.graph_node_label(graph, node_id).value,
    }
    control_role = node.get("control_role")
    if control_role:
        result["control_role"] = str(control_role)
    return result


def _line_reference(node_id: str) -> str | None:
    """Return a printed line key for a plain form-line node id."""

    match = FORM_LINE_RE.search(node_id)
    return match.group("line") if match else None


def _is_referenced_line(node_id: str) -> bool:
    """Return whether a nested graph node is a printed line reference."""

    return _line_reference(node_id) is not None


def _graph_tree(graph: Mapping[str, Any], node_id: str, stack: tuple[str, ...] = (), *, root: bool = False) -> dict[str, Any]:
    """Build a graph-shaped expression tree for the review projection."""

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
    result = {
        "kind": "operation",
        "operation": operation,
        "node_id": node_id,
        "rule_ids": rule_ids,
        "operands": operands,
        "label": cell_access.graph_node_label(graph, node_id).value,
    }
    if operation == "IF_ELSE":
        parameters = _rule_parameters(graph, rule_ids)
        comparison = parameters.get("comparison")
        if isinstance(comparison, str) and comparison:
            result["comparison"] = comparison
        else:
            result["comparison_finding"] = (
                "missing IF_ELSE comparison at rule.parameters.comparison"
            )
        condition = next(
            (item["tree"] for item in operands if item.get("role") == "condition"),
            None,
        )
        if isinstance(condition, Mapping) and condition.get("control_role"):
            result["condition_control_role"] = condition["control_role"]
    return result


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
    return (
        "operation",
        _text(tree.get("operation")),
        _text(tree.get("comparison")),
        operands,
    )


def _tree_operation_count(tree: Mapping[str, Any]) -> int:
    """Count operation nodes in the visible expression tree."""

    if tree.get("kind") != "operation":
        return 0
    return 1 + sum(
        _tree_operation_count(item["tree"])
        for item in tree.get("operands", [])
        if isinstance(item, Mapping) and isinstance(item.get("tree"), Mapping)
    )


def _tree_operand_count(tree: Mapping[str, Any]) -> int:
    """Count operands in the visible expression tree."""

    if tree.get("kind") != "operation":
        return 0
    return sum(
        1 + _tree_operand_count(item["tree"])
        for item in tree.get("operands", [])
        if isinstance(item, Mapping) and isinstance(item.get("tree"), Mapping)
    )


def _hole_reason(row: Mapping[str, Any]) -> str:
    """Return the stored primary reason for a row without a generic hole label."""

    review_gap = _text(row.get("review_gap")).strip()
    if review_gap:
        return review_gap
    for finding in row.get("findings", []):
        if isinstance(finding, Mapping) and _text(finding.get("kind")).strip() == "skipped_anchor":
            return _text(finding.get("message") or finding.get("error")).strip() or "skipped_anchor"
    return "unclassified_hole"


def _hole_category(reason: str) -> str:
    """Group hole reasons for the corpus summary while retaining the exact row reason."""

    if reason == "selector_no_formula_cue":
        return "historical_selector"
    if reason in STRUCTURAL_HOLE_REASONS:
        return "structural"
    return "derivation"


def _hole_reason_summary(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Count exact reasons and the three review-facing reason categories."""

    reasons = Counter(_hole_reason(row) for row in rows if row.get("hole"))
    categories = Counter(
        _hole_category(reason)
        for reason, number in reasons.items()
        for _ in range(number)
    )
    return {
        "exact": dict(sorted(reasons.items())),
        "categories": {
            "historical_selector": categories.get("historical_selector", 0),
            "structural": categories.get("structural", 0),
            "derivation": categories.get("derivation", 0),
        },
    }


def build_panel(candidate_root: str | Path, *, top: int | None = None) -> dict[str, Any]:
    """Build printed-anchor data and optionally select the hardest operation rows."""

    if top is not None and top <= 0:
        raise ValueError("--top must be a positive integer")

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
            row["graph"] = projection
            row["hole"] = projection is None and row.get("model_outcome") != "model_stated_input"
            row["hole_reason"] = _hole_reason(row) if row["hole"] else ""
            row["hole_category"] = _hole_category(row["hole_reason"]) if row["hole"] else ""
            row["operation_count"] = _tree_operation_count(tree) if isinstance(tree, Mapping) else 0
            row["operand_count"] = _tree_operand_count(tree) if isinstance(tree, Mapping) else 0
            panels.append(row)

    full_panels = panels
    operation_rows = [row for row in full_panels if row["operation_count"] > 0]
    operation_distribution = Counter(row["operation_count"] for row in operation_rows)
    ranked = sorted(
        enumerate(operation_rows),
        key=lambda item: (-item[1]["operation_count"], -item[1]["operand_count"], item[0]),
    )
    for rank, (_, row) in enumerate(ranked, start=1):
        row["operation_rank"] = rank
    visible_panels = [row for _, row in ranked[:top]] if top is not None else full_panels
    text_presence = {
        "caption": sum(item["label"] is not None for item in full_panels),
        "instruction": sum(item["instruction"] is not None for item in full_panels),
        "operation": len(operation_rows),
    }
    text_absence = {
        key: len(full_panels) - value for key, value in text_presence.items()
    }
    instruction_row_count = sum(item["row_count"] for item in instruction_by_document.values())
    instruction_present = sum(item["present"] for item in instruction_by_document.values())
    instruction_coverage = {
        "row_count": instruction_row_count,
        "present": instruction_present,
        "absent": instruction_row_count - instruction_present,
        "documents": instruction_by_document,
    }
    return {
        "schema_version": 2,
        "kind": "review_panel",
        "source_candidate": str(root),
        "year": year,
        "documents": documents,
        "denominator": len(full_panels),
        "visible_denominator": len(visible_panels),
        "top": top,
        "holes": sum(1 for item in full_panels if item["hole"]),
        "hole_reasons": _hole_reason_summary(full_panels),
        "text_presence": text_presence,
        "text_absence": text_absence,
        "instruction_coverage": instruction_coverage,
        "operation_distribution": dict(sorted(operation_distribution.items())),
        "max_operands": max((item["operand_count"] for item in operation_rows), default=0),
        "graph_jargon_nodes": graph_jargon_nodes,
        "panels": visible_panels,
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
        if row.get("model_outcome") == "model_stated_input":
            return (
                '<div class="model-outcome"><strong>Model-stated input.</strong>'
                "<p>The form asks the filer to supply this value; no computation was emitted.</p></div>"
            )
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


def _math_text(tree: Mapping[str, Any], indent: int = 0) -> str:
    """Render Math with structural line breaks at operand boundaries."""

    if tree.get("kind") != "operation":
        return _leaf_text(tree)
    operation = _text(tree.get("operation")).upper() or "operation"
    operands = []
    for index, item in enumerate(tree.get("operands", [])):
        if not isinstance(item, Mapping) or not isinstance(item.get("tree"), Mapping):
            continue
        role = _tree_role(tree, index, _text(item.get("role")).strip())
        child = _math_text(item["tree"], indent + 4)
        if operation == "IF_ELSE" and index == 0:
            operands.append("comparison missing" if not tree.get("comparison") else role)
            continue
        if _role_is_implied(tree, index, _text(item.get("role")).strip()):
            role = ""
        operands.append(f"{role}={child}" if role else child)
    compact = f"{operation}({', '.join(operands)})"
    if "\n" not in compact and len(" " * indent + compact) <= 120:
        return compact
    lines = []
    for index, operand in enumerate(operands):
        parts = operand.splitlines()
        lines.append(" " * (indent + 4) + parts[0])
        lines.extend(parts[1:])
        if index < len(operands) - 1:
            lines[-1] += ","
    return f"{operation}(\n" + "\n".join(lines) + "\n" + " " * indent + ")"


_COMPARISON_SYMBOLS = {"gt": ">", "ge": ">=", "lt": "<", "le": "<=", "eq": "="}


def _tree_role(tree: Mapping[str, Any], index: int, role: str) -> str:
    """Render a human-facing branch test instead of a bare condition role."""
    if _text(tree.get("operation")).upper() != "IF_ELSE" or index != 0:
        return role
    operands = tree.get("operands") if isinstance(tree.get("operands"), list) else []
    condition = operands[0].get("tree") if operands and isinstance(operands[0], Mapping) else {}
    line = _text(condition.get("line")).strip() if isinstance(condition, Mapping) else ""
    if tree.get("condition_control_role") == "checkbox":
        return f"Line {line} checked?" if line else "checkbox checked?"
    comparison = _text(tree.get("comparison")).strip().lower()
    symbol = _COMPARISON_SYMBOLS.get(comparison)
    if symbol and line:
        return f"line {line} {symbol} threshold"
    return role or "condition"


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


def _tree_html(tree: Mapping[str, Any], seen: set[tuple[Any, ...]] | None = None) -> str:
    """Render the lossless expression tree, retaining informative edge roles."""

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
        display_role = _tree_role(tree, index, raw_role)
        role = "" if _role_is_implied(tree, index, raw_role) else escape(display_role)
        child = _tree_html(operand["tree"], seen)
        role_html = f'<span class="tree-role">{role}</span>' if role else ""
        edge_class = "tree-edge tree-edge-operation" if operand["tree"].get("kind") == "operation" else "tree-edge"
        children.append(f'<div class="{edge_class}">{child}{role_html}</div>')
    child_html = f'<div class="tree-children">{"".join(children)}</div>' if children else ""
    finding = tree.get("comparison_finding")
    finding_html = (
        f'<div class="tree-finding">{escape(_text(finding))}</div>'
        if finding
        else ""
    )
    return f'<div class="tree-box"><strong>{operation}</strong>{finding_html}{child_html}</div>'


def _hole_html(row: Mapping[str, Any]) -> str:
    """Render a hole with its stored reason and an expected-absence distinction."""

    reason = _text(row.get("hole_reason")) or "unclassified_hole"
    category = _text(row.get("hole_category")) or "derivation"
    if category == "historical_selector":
        detail = "This candidate predates S89 and must be regenerated before review."
    elif category == "structural":
        detail = "The source structure did not yield a promotable cell."
    else:
        detail = "The derivation did not produce a promotable operation."
    return (
        f'<div class="operation-hole hole-{escape(category)}">'
        f'<strong>{escape(category.replace("_", " ").title())}</strong>'
        f'<p class="hole-reason"><code>{escape(reason)}</code></p>'
        f"<p>{escape(detail)}</p></div>"
    )


def _panel_html(row: Mapping[str, Any]) -> str:
    """Render one full-width panel with stable metadata for browser inspection."""

    status = _text(row.get("status")) or "missing"
    hole = "true" if row.get("hole") else "false"
    source_details = "".join(
        _source_block(title, row.get(key))
        for title, key in (("Label", "label"), ("Form face", "form_face"), ("Instruction page", "instruction"))
    )
    tree = row.get("graph", {}).get("tree") if isinstance(row.get("graph"), Mapping) else None
    if isinstance(tree, Mapping):
        tree_html = _tree_html(tree)
        math_html = escape(_math_text(tree))
    elif row.get("model_outcome") == "model_stated_input":
        tree_html = (
            '<div class="model-outcome"><strong>Model-stated input</strong>'
            "<p>Input required from the filer.</p></div>"
        )
        math_html = "REQUIRE INPUT"
    else:
        tree_html = _hole_html(row)
        math_html = "No promoted expression."
    rank = row.get("operation_rank")
    rank_attribute = "" if rank is None else f' data-operation-rank="{escape(_text(rank), quote=True)}"'
    return (
        f'<article class="review-panel" data-anchor="{escape(_text(row.get("anchor_id")), quote=True)}" '
        f'data-hole="{hole}" data-hole-reason="{escape(_text(row.get("hole_reason")), quote=True)}"{rank_attribute}>'
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
        '</div></article>'
    )


def _operation_distribution_text(distribution: Mapping[Any, Any]) -> str:
    """Format the operation-count distribution for a human-readable summary."""

    return ", ".join(
        f"{_text(count)}: {_text(number)}" for count, number in sorted(distribution.items())
    ) or "none"


def render_html(panel: Mapping[str, Any]) -> str:
    """Render the complete self-contained Tree and Math review artifact."""

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
    reasons = panel.get("hole_reasons") if isinstance(panel.get("hole_reasons"), Mapping) else {}
    categories = reasons.get("categories") if isinstance(reasons.get("categories"), Mapping) else {}
    operation_distribution = panel.get("operation_distribution") if isinstance(panel.get("operation_distribution"), Mapping) else {}
    top = panel.get("top")
    visible = panel.get("visible_denominator", len(panel.get("panels") or []))
    operation_rows = presence.get("operation", 0)
    if top is None:
        focus_text = f"showing all {operation_rows} operation rows"
    else:
        focus_text = f"showing top {visible} of {operation_rows} operation rows, ranked by operation count then operand count"
    summary = (
        f"{_text(panel.get('denominator'))} printed anchors; {len(panel.get('documents') or [])} documents; "
        f"{focus_text}; operation counts {_operation_distribution_text(operation_distribution)}; "
        f"{_text(panel.get('holes', 0))} holes; "
        f"hole reasons {categories.get('historical_selector', 0)} historical selector / "
        f"{categories.get('structural', 0)} structural / {categories.get('derivation', 0)} derivation; "
        f"captions {presence.get('caption', 0)} present / {absence.get('caption', 0)} absent; "
        f"instruction rows {presence.get('instruction', 0)} present / {absence.get('instruction', 0)} absent; "
        f"operations {presence.get('operation', 0)} present / {absence.get('operation', 0)} absent; "
        f"candidate instruction coverage {instruction_coverage.get('present', 0)}/{instruction_coverage.get('row_count', 0)} present "
        f"({coverage_detail}); max operands {_text(panel.get('max_operands', 0))}."
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
<title>Generated Tree and Math review panel</title>
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
.review-columns {{ display: block; }}
.column {{ min-width: 0; padding: 14px 16px 18px; }}
.column h3 {{ margin: 0 0 12px; font-size: 1rem; }}
.column h3 + h3 {{ margin-top: 18px; }}
.tree-expression {{ padding: 10px; border: 1px solid #8795a5; background: #fbfcfd; overflow: auto; }}
.tree-box {{ display: inline-block; min-width: 125px; padding: 8px; border: 2px solid #40566d; border-radius: 6px; background: #e7f0f8; }}
.tree-box strong {{ display: block; text-align: left; }}
.tree-children {{ margin-top: 8px; border-left: 2px solid #9aa7b4; }}
.tree-edge {{ display: grid; grid-template-columns: max-content max-content; align-items: flex-start; column-gap: 8px; margin: 7px 0; min-width: max-content; }}
.tree-edge-operation {{ margin-left: 32px; }}
.tree-edge > :not(.tree-role) {{ grid-column: 1; }}
.tree-edge > .tree-role {{ grid-column: 2; align-self: center; }}
.tree-role {{ color: #18212b; font: .74rem Consolas, monospace; font-weight: bold; }}
.tree-leaf {{ display: inline-flex; min-width: 120px; padding: 7px; border: 1px solid #8795a5; border-radius: 4px; background: white; }}
.tree-reference {{ padding: 7px; border: 1px dashed #8795a5; background: white; }}
.tree-finding {{ margin-top: 5px; color: #a32121; font: .74rem Consolas, monospace; }}
.math-expression {{ min-height: 52px; padding: 10px; border: 1px solid #8795a5; background: #fbfcfd; white-space: pre-wrap; overflow-wrap: normal; }}
.graph-trace {{ margin-top: 12px; padding: 8px; border: 1px solid #d8dee5; background: #fafbfc; }}
.graph-trace summary {{ cursor: pointer; font-weight: bold; }}
.graph-trace h4 {{ margin: 10px 0 5px; font-size: .84rem; }}
.graph-trace ul {{ margin: 5px 0; padding-left: 20px; }}
.graph-trace .operation-hole {{ margin-top: 8px; padding: 8px; border: 2px solid #c13c3c; background: #fff1f1; }}
.operation-hole {{ padding: 12px; border: 2px solid #c13c3c; background: #fff1f1; }}
.model-outcome {{ padding: 12px; border: 2px solid #6584a3; background: #eef5fb; }}
.model-outcome strong {{ color: #40566d; }}
.hole-historical_selector {{ border-color: #718096; background: #f0f3f6; }}
.hole-historical_selector strong {{ color: #40566d; }}
.hole-structural {{ border-color: #c78b22; background: #fffaf0; }}
.hole-structural strong {{ color: #8a5a00; }}
.hole-derivation strong {{ color: #a32121; }}
.hole-reason {{ margin: 8px 0; }}
.operation-shape {{ color: #526171; font-size: .8rem; }}
.jargon-note {{ margin-top: 8px; }}
ul {{ margin: 5px 0; padding-left: 20px; }}
li {{ margin: 4px 0; overflow-wrap: anywhere; }}
@media (max-width: 1050px) {{ .panel-header code {{ margin-left: 0; width: 100%; }} .source-evidence-grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body><main data-tree-math-layout="true">
<section class="summary"><h1>Generated Tree and Math review panel</h1>
<p>{escape(summary)}</p>
<p>Tree and Math are two lossless projections of the promoted expression. The Tree shows containment and informative edge roles; Math flattens the same stored tree.</p>
{jargon_html}
</section>
{panels}
</main></body>
</html>
'''


def main(argv: list[str] | None = None) -> int:
    """Run the pilot from a candidate workspace path."""

    parser = argparse.ArgumentParser(description="Generate a Tree and Math review panel from a candidate workspace.")
    parser.add_argument("candidate_root", type=Path)
    parser.add_argument("--output", type=Path, default=Path(r"C:\tmp\m20_s84\review_panel.html"))
    parser.add_argument("--top", type=int, default=None, help="show the hardest N operation rows")
    args = parser.parse_args(argv)
    panel = build_panel(args.candidate_root, top=args.top)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(panel), encoding="utf-8", newline="\n")
    categories = panel["hole_reasons"]["categories"]
    focus = (
        f"showing top {panel['visible_denominator']} of {panel['text_presence']['operation']} operation rows"
        if panel["top"] is not None
        else f"showing all {panel['text_presence']['operation']} operation rows"
    )
    print(
        f"{output}: {panel['denominator']} anchors; {focus}; "
        f"operation counts {_operation_distribution_text(panel['operation_distribution'])}; "
        f"{panel['holes']} holes; hole reasons "
        f"{categories['historical_selector']} historical selector / "
        f"{categories['structural']} structural / {categories['derivation']} derivation; "
        f"captions {panel['text_presence']['caption']} present / "
        f"{panel['text_absence']['caption']} absent; "
        f"instruction rows {panel['text_presence']['instruction']} present / "
        f"{panel['text_absence']['instruction']} absent; "
        f"candidate instruction coverage {panel['instruction_coverage']['present']}/"
        f"{panel['instruction_coverage']['row_count']} present; "
        f"operations {panel['text_presence']['operation']} present / "
        f"{panel['text_absence']['operation']} absent; max operands {panel['max_operands']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
