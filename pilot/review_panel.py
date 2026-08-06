"""Build a self-contained three-column review panel from a candidate workspace.

This pilot is a read-only projection of the candidate run.  It joins every
printed anchor from the source reports to the candidate row, then reads the
promoted operation, rule, and edge data from the candidate draft.  It does not
call a provider, write graph artifacts, or assign a human verdict.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from html import escape
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

import yaml

import cell_access


REPORT_SUFFIX = "_derive_cells_report.yaml"
OUTCOME_STATUSES = {"derived", "repaired", "review_gap", "skipped", "error", "errored"}
BRANCH_OPERATIONS = frozenset({"IF", "IF_ELSE", "LOOKUP_TABLE", "LOOKUP_BRACKET"})


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
        "label": cell_access.graph_node_label(graph, node_id).value,
    }


def _graph_tree(graph: Mapping[str, Any], node_id: str, stack: tuple[str, ...] = (), *, root: bool = False) -> dict[str, Any]:
    """Build a graph-shaped expression tree for flow projection."""

    if not node_id or node_id in stack:
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
        graph = _load_graph(root, year, document_id)
        graph_jargon_nodes.extend(_graph_jargon_nodes(document_id, graph))
        for index, anchor in enumerate(anchors, start=1):
            if not isinstance(anchor, Mapping):
                raise ValueError(f"{document_id}: denominator anchor {index} is not an object")
            line = _line(anchor.get("anchor") or anchor.get("line"))
            skip_reason = _text(anchor.get("skip_reason")).strip()
            source = None if skip_reason else _take(source_rows, line)
            candidate = None if skip_reason else _take(candidate_rows, line)
            row = _merge_anchor(document_id, index, anchor, source, candidate)
            projection = _graph_projection(row, graph)
            tree = projection.get("tree") if projection else None
            mode = _flow_mode(tree)
            row["graph"] = projection
            row["flow_mode"] = mode
            row["flow_depth"] = _tree_depth(tree) if isinstance(tree, Mapping) else 0
            row["hole"] = projection is None
            panels.append(row)

    mode_counts = {mode: sum(item["flow_mode"] == mode for item in panels) for mode in ("diagram", "chain", "none")}
    text_presence = {
        "caption": sum(item["label"] is not None for item in panels),
        "instruction": sum(item["instruction"] is not None for item in panels),
        "operation": sum(item["graph"] is not None for item in panels),
    }
    text_absence = {
        key: len(panels) - value for key, value in text_presence.items()
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
        "text_presence": text_presence,
        "text_absence": text_absence,
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


def _flow_tree_html(tree: Mapping[str, Any]) -> str:
    """Render a graph tree as nested flow boxes and arrow-labeled edges."""

    if tree.get("kind") != "operation":
        node_id = escape(_text(tree.get("node_id")))
        if tree.get("kind") == "constant":
            value = escape(_text(tree.get("value")))
            return f'<div class="flow-leaf"><code>{node_id}</code><span>constant_value={value}</span></div>'
        return f'<div class="flow-leaf"><code>{node_id}</code></div>'
    operation = escape(_text(tree.get("operation")))
    children = []
    for operand in tree.get("operands", []):
        if not isinstance(operand, Mapping) or not isinstance(operand.get("tree"), Mapping):
            continue
        role = escape(_text(operand.get("role")))
        child = _flow_tree_html(operand["tree"])
        children.append(f'<div class="flow-edge"><span class="flow-role">{role}</span><span class="arrow">-&gt;</span>{child}</div>')
    child_html = f'<div class="flow-children">{"".join(children)}</div>' if children else ""
    return f'<div class="flow-box"><strong>{operation}</strong>{child_html}</div>'


def _flow_html(row: Mapping[str, Any]) -> str:
    """Render the flow column according to the panel mode."""

    mode = _text(row.get("flow_mode"))
    tree = row.get("graph", {}).get("tree") if isinstance(row.get("graph"), Mapping) else None
    if not isinstance(tree, Mapping):
        return '<div class="flow-hole"><strong>No flow.</strong><p>The promoted operation is absent.</p></div>'
    depth = int(row.get("flow_depth") or 0)
    if mode == "none":
        return f'<p class="no-diagram">Depth {depth}, no diagram.</p>'
    return f'<div class="flow-{escape(mode)}"><p class="flow-kind">{escape(mode)}</p>{_flow_tree_html(tree)}</div>'


def _panel_html(row: Mapping[str, Any]) -> str:
    """Render one panel with stable metadata for browser and test inspection."""

    status = _text(row.get("status")) or "missing"
    hole = "true" if row.get("hole") else "false"
    return (
        f'<article class="review-panel" data-anchor="{escape(_text(row.get("anchor_id")), quote=True)}" '
        f'data-flow-mode="{escape(_text(row.get("flow_mode")), quote=True)}" data-hole="{hole}">'
        '<header class="panel-header">'
        f'<h2>{escape(_text(row.get("document_id")))} line {escape(_text(row.get("line")))}</h2>'
        f'<span class="status status-{escape(status)}">{escape(status)}</span>'
        f'<code>{escape(_text(row.get("anchor_id")))}</code></header>'
        '<div class="columns">'
        '<section class="column source-column"><h3>IRS text</h3>'
        f'{_source_block("Label", row.get("label"))}'
        f'{_source_block("Form face", row.get("form_face"))}'
        f'{_source_block("Instruction page", row.get("instruction"))}'
        '</section>'
        f'<section class="column operation-column"><h3>Operation</h3>{_operation_html(row)}</section>'
        f'<section class="column flow-column"><h3>Flow</h3>{_flow_html(row)}</section>'
        '</div></article>'
    )


def render_html(panel: Mapping[str, Any]) -> str:
    """Render a complete self-contained HTML review artifact."""

    modes = panel.get("flow_modes") or {}
    presence = panel.get("text_presence") if isinstance(panel.get("text_presence"), Mapping) else {}
    absence = panel.get("text_absence") if isinstance(panel.get("text_absence"), Mapping) else {}
    summary = (
        f"{_text(panel.get('denominator'))} printed anchors; "
        f"{len(panel.get('documents') or [])} documents; "
        f"{_text(modes.get('diagram', 0))} diagrams / "
        f"{_text(modes.get('chain', 0))} chains / "
        f"{_text(modes.get('none', 0))} none; "
        f"{_text(panel.get('holes', 0))} panels with a hole; "
        f"captions {presence.get('caption', 0)} present / {absence.get('caption', 0)} absent; "
        f"instruction sections {presence.get('instruction', 0)} present / {absence.get('instruction', 0)} absent; "
        f"operations {presence.get('operation', 0)} present / {absence.get('operation', 0)} absent."
    )
    jargon_nodes = panel.get("graph_jargon_nodes") or []
    jargon_html = ""
    if jargon_nodes:
        items = "".join(
            f'<li><code>{escape(_text(item.get("document_id")))}: '
            f'{escape(_text(item.get("node_id")))}</code></li>'
            for item in jargon_nodes
        )
        jargon_html = (
            '<details class="jargon-note"><summary>Graph terminology to report (not changed)</summary>'
            f"<ul>{items}</ul></details>"
        )
    panels = "\n".join(_panel_html(row) for row in panel.get("panels", []))
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Generated three-column review panel</title>
<style>
:root {{ color-scheme: light; font-family: Arial, sans-serif; background: #f3f5f7; color: #18212b; }}
body {{ margin: 0; padding: 24px; }}
main {{ max-width: 1900px; margin: 0 auto; }}
.summary {{ position: sticky; top: 0; z-index: 2; padding: 14px 18px; margin-bottom: 18px; background: #18212b; color: white; border-radius: 8px; box-shadow: 0 2px 8px #0004; }}
.summary h1 {{ margin: 0 0 6px; font-size: 1.25rem; }}
.summary p {{ margin: 0; }}
.review-panel {{ margin: 0 0 18px; background: white; border: 1px solid #cbd3dc; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px #0001; }}
.panel-header {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; padding: 11px 16px; background: #e8edf2; border-bottom: 1px solid #cbd3dc; }}
.panel-header h2 {{ margin: 0; font-size: 1rem; }}
.panel-header code {{ margin-left: auto; color: #44515f; }}
.status {{ padding: 3px 8px; border: 1px solid #8795a5; border-radius: 12px; font-size: .78rem; }}
.status-derived {{ background: #e5f5e9; }}
.status-repaired {{ background: #fff2c7; }}
.status-review_gap, .status-error, .status-errored, .status-missing {{ background: #ffdede; }}
.status-skipped {{ background: #eef0f3; }}
.columns {{ display: grid; grid-template-columns: minmax(260px, 1fr) minmax(280px, 1fr) minmax(280px, 1fr); gap: 0; }}
.column {{ min-width: 0; padding: 14px 16px 18px; }}
.column + .column {{ border-left: 1px solid #d8dee5; }}
.column h3 {{ margin: 0 0 12px; font-size: 1rem; }}
.column h4 {{ margin: 12px 0 5px; font-size: .84rem; color: #526171; }}
.source-block {{ margin: 0 0 10px; padding: 8px; border-left: 3px solid #6584a3; background: #f7f9fb; }}
.source-block.empty {{ border-left-color: #c78b22; background: #fffaf0; }}
.source-block h4 {{ margin: 0 0 5px; color: #18212b; }}
pre {{ margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; font: .82rem/1.35 Consolas, monospace; }}
code {{ overflow-wrap: anywhere; font-family: Consolas, monospace; font-size: .82rem; }}
.graph-operation span, .flow-kind {{ color: #526171; font-size: .82rem; }}
.operation-hole, .flow-hole {{ padding: 12px; border: 2px solid #c13c3c; background: #fff1f1; }}
.operation-hole strong, .flow-hole strong {{ color: #a32121; }}
ul {{ margin: 5px 0; padding-left: 20px; }}
li {{ margin: 4px 0; overflow-wrap: anywhere; }}
.graph-label {{ margin: 4px 0 0 0; color: #53606d; font-size: .74rem; }}
.no-diagram {{ padding: 12px; border: 1px dashed #8795a5; color: #526171; }}
.flow-diagram, .flow-chain {{ padding: 10px; border: 1px solid #8795a5; background: #fbfcfd; overflow-x: auto; }}
.flow-diagram {{ border-width: 2px; border-color: #596d82; }}
.flow-kind {{ margin: 0 0 8px; text-transform: uppercase; letter-spacing: .06em; }}
.flow-box {{ display: inline-block; min-width: 120px; padding: 8px; border: 2px solid #40566d; border-radius: 6px; background: #e7f0f8; }}
.flow-box strong {{ display: block; text-align: center; }}
.flow-children {{ margin-top: 8px; padding-left: 12px; border-left: 2px solid #9aa7b4; }}
.flow-edge {{ display: flex; align-items: flex-start; gap: 5px; margin: 7px 0; min-width: max-content; }}
.flow-role {{ color: #40566d; font: .74rem Consolas, monospace; }}
.arrow {{ color: #b06b00; font-weight: bold; }}
.flow-leaf {{ display: inline-flex; flex-direction: column; gap: 3px; min-width: 120px; padding: 7px; border: 1px solid #8795a5; border-radius: 4px; background: white; }}
.flow-leaf span {{ color: #526171; font: .72rem Consolas, monospace; }}
@media (max-width: 1050px) {{ .columns {{ grid-template-columns: 1fr; }} .column + .column {{ border-left: 0; border-top: 1px solid #d8dee5; }} .panel-header code {{ margin-left: 0; width: 100%; }} }}
</style>
</head>
<body><main>
<section class="summary"><h1>Generated three-column review panel</h1><p>{escape(summary)}</p>{jargon_html}</section>
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
        f"instruction sections {panel['text_presence']['instruction']} present / "
        f"{panel['text_absence']['instruction']} absent; "
        f"operations {panel['text_presence']['operation']} present / "
        f"{panel['text_absence']['operation']} absent"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
