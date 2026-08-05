"""Build the deterministic three-column review artifact.

The review table is deliberately a projection.  It reads the cleaned source
frame and the graph projection, then renders both plus a deterministic
pseudocode view of the graph expression.  It never calls a model, edits graph
artifacts, or assigns a correctness verdict.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
import json
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping, Sequence

from tax_graph.config import project_root
from tax_graph.extract.cells import build_cell_frame_from_document
from tax_graph.extract.inputs import load_document_input
from tax_graph.io.loader import load_graph


_CONDITIONAL_RE = re.compile(r"\b(?:if|unless|when|either|otherwise|depending)\b", re.IGNORECASE)
_CAP_RE = re.compile(
    r"\b(?:cap(?:ped)?|maximum|limit(?:ed)?|no\s+more\s+than|not\s+exceed|up\s+to|"
    r"smaller\s+of|larger\s+of|whichever\s+is\s+(?:less|more))\b",
    re.IGNORECASE,
)
_DOLLAR_RE = re.compile(r"\$\s*[0-9][0-9,]*(?:\.[0-9]+)?")
_TABLE_RE = re.compile(r"\bcolumns?\b|\([a-z]\)", re.IGNORECASE)
_CROSS_DOCUMENT_RE = re.compile(
    r"\b(?:forms?|schedules?|worksheets?|pub\.?|publication)\s+[a-z0-9][a-z0-9-]*",
    re.IGNORECASE,
)
_SENTENCE_RE = re.compile(r"[^.!?]+(?:[.!?]+|$)", re.DOTALL)
_LINE_RE = re.compile(r"(?:^|_)line_([0-9]+[a-z]?|[a-z])(?:_|$)", re.IGNORECASE)
_LINE_LABEL_RE = re.compile(r"\b(?:line|lines)\s+([0-9]+[a-z]?|[a-z])\b", re.IGNORECASE)


@dataclass(frozen=True)
class SelectionScore:
    """Deterministic compound-instruction signals for one review row."""

    score: int
    conditionals: int
    caps: int
    dollar_constants: int
    table_columns: int
    cross_document_refs: int
    sentences: int

    def as_dict(self) -> dict[str, int]:
        """Return the signals in stable display order."""
        return {
            "score": self.score,
            "conditionals": self.conditionals,
            "caps": self.caps,
            "dollar_constants": self.dollar_constants,
            "table_columns": self.table_columns,
            "cross_document_refs": self.cross_document_refs,
            "sentences": self.sentences,
        }


@dataclass(frozen=True)
class ReviewTableRow:
    """One row in the input-versus-graph-versus-pseudocode review."""

    line: str
    label: str
    printed_instruction: str
    instruction_text: str
    expression: Any
    status: str
    failures: tuple[Any, ...]
    warnings: tuple[Any, ...]
    selection: SelectionScore


def score_instruction(text: str) -> SelectionScore:
    """Score compound tax instructions without using a model or graph state."""
    value = str(text or "")
    conditionals = len(_CONDITIONAL_RE.findall(value))
    caps = len(_CAP_RE.findall(value))
    dollar_constants = len(_DOLLAR_RE.findall(value))
    table_columns = len(_TABLE_RE.findall(value))
    cross_document_refs = len(_CROSS_DOCUMENT_RE.findall(value))
    sentences = len(_SENTENCE_RE.findall(value.strip())) if value.strip() else 0
    score = (
        conditionals * 3
        + caps * 2
        + dollar_constants * 2
        + table_columns * 2
        + cross_document_refs * 2
        + max(sentences - 1, 0)
    )
    return SelectionScore(
        score=score,
        conditionals=conditionals,
        caps=caps,
        dollar_constants=dollar_constants,
        table_columns=table_columns,
        cross_document_refs=cross_document_refs,
        sentences=sentences,
    )


def render_pseudocode(expression: Any) -> str:
    """Render a stored expression deterministically for human inspection.

    Both the extraction expression tree and the workbench graph projection are
    accepted.  Missing operands are printed as unresolved; this function never
    invents a reference from a label or position.
    """
    if not isinstance(expression, Mapping):
        return "UNRESOLVED: no expression tree was recorded"
    if "op" in expression:
        return _render_tree_node(expression, 0)
    if expression.get("kind") == "review_gap":
        reason = str(expression.get("reason") or "graph expression is unresolved")
        return f"UNRESOLVED: {reason}"
    if expression.get("operation") or expression.get("operands"):
        return _render_projection(expression)
    return "UNRESOLVED: stored graph record has no structured expression"


def build_review_table(
    root: str | Path,
    year: str | int,
    document_id: str,
    *,
    all_rows: bool = False,
    hardest: int | None = None,
) -> dict[str, Any]:
    """Build the read-only review payload for one acquired document.

    The source column comes from ``build_cell_frame_from_document`` so it is
    the cleaned text used by derivation.  Graph rows are read from the existing
    workbench projection when present, with a graph-only fallback for other
    documents.  No provider client is constructed.
    """
    if all_rows and hardest is not None:
        raise ValueError("--all-rows and --hardest cannot be used together")
    if hardest is not None and hardest < 1:
        raise ValueError("hardest must be at least 1")

    root_path = Path(root).resolve()
    document = load_document_input(document_id, year=year, root=root_path)
    source_rows = _source_rows(document)
    graph_rows = _graph_projection_rows(root_path, year, document_id)
    rows: list[ReviewTableRow] = []
    for source in source_rows:
        line = source["line"]
        graph = graph_rows.get(line)
        printed = str(source.get("printed_instruction") or "")
        selection = score_instruction(printed)
        rows.append(
            ReviewTableRow(
                line=line,
                label=str(source.get("label") or ""),
                printed_instruction=printed,
                instruction_text=str(source.get("instruction_text") or ""),
                expression=graph.get("expression") if graph else None,
                status=str(graph.get("status") or "not recorded") if graph else "not recorded",
                failures=tuple(graph.get("failures") or ()) if graph else ("graph expression not recorded",),
                warnings=tuple(graph.get("warnings") or ()) if graph else (),
                selection=selection,
            )
        )

    if hardest is not None:
        rows = sorted(rows, key=lambda row: (-row.selection.score, _line_sort_key(row.line), row.label))[:hardest]
        mode = f"hardest {hardest}"
    else:
        rows = sorted(rows, key=lambda row: (_line_sort_key(row.line), row.label))
        mode = "all rows" if all_rows else "all rows"

    return {
        "schema_version": 1,
        "year": str(year),
        "document_id": document_id,
        "selection_mode": mode,
        "source": "cleaned deterministic form frame",
        "rows": rows,
    }


def render_review_table_html(payload: Mapping[str, Any]) -> str:
    """Render a self-contained three-column review table without verdicts."""
    rows = payload.get("rows") or []
    body: list[str] = []
    for row in rows:
        if not isinstance(row, ReviewTableRow):
            raise TypeError("review table rows must be ReviewTableRow instances")
        graph_expression = _compact_json(row.expression) if row.expression is not None else "not recorded"
        failures = _render_verdicts(row.failures)
        warnings = _render_verdicts(row.warnings)
        body.append(
            "<tr>"
            f"<td><div class=\"line\">Line {_h(row.line)}</div>"
            f"<div class=\"label\">{_h(row.label) or 'unlabelled'}</div>"
            f"<pre>{_h(row.printed_instruction) or 'not recorded'}</pre>"
            f"{_instruction_note(row.instruction_text)}"
            f"<div class=\"score\"><strong>Selection signals:</strong> {_h(_selection_label(row.selection))}</div></td>"
            f"<td><div><strong>Status:</strong> {_h(row.status)}</div>"
            f"<details><summary>Exact expression</summary><pre>{_h(graph_expression)}</pre></details>"
            f"<div class=\"verdicts\"><strong>Validator findings:</strong>{failures}"
            f"<strong>Validator warnings:</strong>{warnings}</div></td>"
            f"<td><pre>{_h(render_pseudocode(row.expression))}</pre></td>"
            "</tr>"
        )
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>Three-column review - {_h(payload.get('document_id'))}</title>",
            "<style>",
            _CSS,
            "</style>",
            "</head>",
            "<body>",
            '<main class="shell">',
            f"<h1>Three-column review: {_h(payload.get('document_id'))}</h1>",
            f"<p class=\"meta\">Year {_h(payload.get('year'))}; selection {_h(payload.get('selection_mode'))}. "
            "The table shows evidence and machine state. The reviewer makes the judgment.</p>",
            '<table aria-label="Input graph pseudocode review">',
            "<thead><tr><th>Cleaned printed instruction</th><th>Graph expression and status</th><th>Pseudocode</th></tr></thead>",
            f"<tbody>{''.join(body)}</tbody>",
            "</table>",
            "</main>",
            "</body>",
            "</html>",
            "",
        ]
    )


def review_table_command(
    *,
    year: str = "2025",
    document_id: str,
    root: str | Path | None = None,
    output: str | Path | None = None,
    all_rows: bool = False,
    hardest: int | None = None,
) -> int:
    """Write the review table outside the repository and print its path."""
    root_path = Path(root).resolve() if root is not None else project_root()
    payload = build_review_table(
        root_path,
        year,
        document_id,
        all_rows=all_rows,
        hardest=hardest,
    )
    destination = _output_path(root_path, document_id, output)
    destination.write_text(render_review_table_html(payload), encoding="utf-8", newline="\n")
    print(f"review table: {destination}")
    print(f"rows: {len(payload['rows'])}; selection: {payload['selection_mode']}")
    return 0


def _source_rows(document: Any) -> list[dict[str, str]]:
    """Return source rows from the cleaned structure adapter."""
    try:
        frame = build_cell_frame_from_document(document)
    except (OSError, ValueError, KeyError, TypeError):
        return _fallback_source_rows(document)
    result: list[dict[str, str]] = []
    for row in frame.rows:
        printed = str(row.form_face_text or "").strip()
        if not printed:
            printed = str(row.label or "").strip()
        result.append(
            {
                "line": str(row.line).strip().lower(),
                "label": str(row.label or ""),
                "printed_instruction": printed,
                "instruction_text": str(row.instruction_text or ""),
            }
        )
    return result


def _fallback_source_rows(document: Any) -> list[dict[str, str]]:
    """Build a conservative line view when the structure adapter is unavailable."""
    result: list[dict[str, str]] = []
    for line in str(getattr(document, "text", "")).splitlines():
        match = _LINE_LABEL_RE.search(line)
        if not match:
            continue
        result.append(
            {
                "line": match.group(1).lower(),
                "label": "",
                "printed_instruction": line.strip(),
                "instruction_text": "",
            }
        )
    return result


def _graph_projection_rows(root: Path, year: str | int, document_id: str) -> dict[str, dict[str, Any]]:
    """Load graph-side review rows without constructing a provider client."""
    try:
        from workbench.generated_review import build_generated_document_cells

        projection = build_generated_document_cells(root, year, document_id)
        rows = {}
        for cell in projection.cells:
            line = _cell_line(cell)
            if not line:
                continue
            expression = cell.get("expression")
            failures = cell.get("validation_failures") or cell.get("findings") or ()
            if not failures and isinstance(expression, Mapping) and expression.get("kind") == "review_gap":
                failures = (str(expression.get("reason") or "graph expression is unresolved"),)
            item = {
                "expression": expression,
                "status": cell.get("generated_status") or cell.get("status") or "graph",
                "failures": failures,
                "warnings": cell.get("validation_warnings") or cell.get("warnings") or (),
            }
            if line in rows:
                rows[line] = {
                    "expression": None,
                    "status": "ambiguous",
                    "failures": (f"multiple graph rows matched printed line {line}",),
                    "warnings": (),
                }
            else:
                rows[line] = item
        if rows:
            return rows
    except (OSError, PermissionError, ValueError, KeyError, TypeError):
        pass
    return _graph_rows_from_loaded_graph(root, year, document_id)


def _graph_rows_from_loaded_graph(root: Path, year: str | int, document_id: str) -> dict[str, dict[str, Any]]:
    """Build a graph-only expression projection for documents without a draft view."""
    try:
        graph = load_graph(year, root)
    except (OSError, ValueError, KeyError):
        return {}
    nodes = [item for item in graph.items("nodes") if str(item.get("document_id") or "") == document_id]
    rules = {str(item.get("rule_id")): item for item in graph.items("rules")}
    edges = graph.items("edges")
    node_by_id = {str(item.get("node_id")): item for item in graph.items("nodes")}
    result: dict[str, dict[str, Any]] = {}
    for node in nodes:
        line = _node_line(str(node.get("node_id") or ""), str(node.get("label") or ""))
        if not line:
            continue
        if line in result:
            result[line] = {
                "expression": None,
                "status": "ambiguous",
                "failures": (f"multiple graph nodes matched printed line {line}",),
                "warnings": (),
            }
            continue
        target = str(node.get("node_id") or "")
        target_edges = [edge for edge in edges if str(edge.get("target") or "") == target]
        rule = rules.get(str(target_edges[0].get("rule_id") or "")) if target_edges else None
        operation = str((rule or {}).get("operation") or "").upper()
        operands = [
            _graph_operand(edge, node_by_id)
            for edge in target_edges
            if edge.get("source")
        ]
        expression = None
        if operation:
            expression = {
                "kind": operation.lower(),
                "operation": operation,
                "operands": operands,
            }
        result[line] = {
            "expression": expression,
            "status": "graph" if expression else "source-only",
            "failures": (),
            "warnings": (),
        }
    return result


def _graph_operand(edge: Mapping[str, Any], node_by_id: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Represent one graph edge operand without resolving missing nodes by guess."""
    node_id = str(edge.get("source") or "")
    source = node_by_id.get(node_id)
    label = str(source.get("label") or "").strip() if source else ""
    display = label or (f"node {node_id}" if node_id else "unresolvable operand")
    return {
        "kind": "reference",
        "label": display,
        "text": display,
        "role": str(edge.get("role") or "") or None,
        "ref": {
            "object_type": "node",
            "object_id": node_id,
            "display_label": label,
        },
    }


def _cell_line(cell: Mapping[str, Any]) -> str:
    """Extract one printed line from a workbench projection cell."""
    for key in ("official_ref", "line", "line_anchor"):
        value = cell.get(key)
        if value:
            match = _LINE_LABEL_RE.search(str(value))
            return (match.group(1) if match else str(value)).lower()
    return _node_line(str(cell.get("node_id") or ""), str(cell.get("display_name") or ""))


def _node_line(node_id: str, label: str) -> str:
    """Extract a printed line only when the graph names it explicitly."""
    match = _LINE_RE.search(node_id) or _LINE_LABEL_RE.search(label)
    return match.group(1).lower() if match else ""


def _render_tree_node(node: Mapping[str, Any], indent: int) -> str:
    """Render one extraction expression-tree node."""
    prefix = " " * indent
    if "form" in node and "line" in node:
        return prefix + f"{node['form']} line {node['line']}"
    if "line" in node:
        return prefix + f"line {node['line']}"
    if "const" in node:
        return prefix + _constant_text(node["const"])
    if "node" in node:
        return prefix + f"node {node['node']}"
    operation = str(node.get("op") or "").upper()
    if not operation:
        return prefix + "[unresolvable operand]"
    words = _operation_words(operation)
    args = [item for item in node.get("args") or []]
    if operation == "LOOKUP_TABLE" or operation == "LOOKUP_BRACKET":
        lines = [prefix + words]
        for index, arg in enumerate(args):
            role = str(arg.get("role") or "") if isinstance(arg, Mapping) else ""
            role = role or f"operand {index + 1}"
            lines.extend(_indented(_render_tree_node(arg, 0), indent + 2, f"{role}: "))
        return "\n".join(lines)
    if operation == "IF":
        if len(args) != 2:
            return prefix + f"{words} [unresolvable branches]"
        lines = [prefix + words + " " + _single_line_operand(args[0])]
        lines.append(" " * (indent + 2) + "THEN " + _single_line_operand(args[1]))
        return "\n".join(lines)
    if operation == "IF_ELSE":
        if len(args) != 4:
            return prefix + f"{words} [unresolvable branches]"
        lines = [prefix + words]
        lines.append(" " * (indent + 2) + "condition: " + _single_line_operand(args[0]))
        lines.append(" " * (indent + 2) + "threshold: " + _single_line_operand(args[1]))
        lines.append(" " * (indent + 2) + "THEN: " + _single_line_operand(args[2]))
        lines.append(" " * (indent + 2) + "ELSE: " + _single_line_operand(args[3]))
        return "\n".join(lines)
    lines = [prefix + words]
    roles = _tree_roles(operation, len(args))
    for index, arg in enumerate(args):
        role = roles[index] if index < len(roles) else f"operand {index + 1}"
        child = _render_tree_node(arg, 0) if isinstance(arg, Mapping) else "[unresolvable operand]"
        lines.extend(_indented(child, indent + 2, f"{role}: "))
    return "\n".join(lines)


def _render_projection(expression: Mapping[str, Any]) -> str:
    """Render a deterministic workbench graph projection."""
    operation = str(expression.get("operation") or expression.get("kind") or "").upper()
    if not operation:
        return "UNRESOLVED: graph projection has no operation"
    operands = expression.get("operands")
    if not isinstance(operands, Sequence) or isinstance(operands, (str, bytes)):
        return "\n".join([_operation_words(operation), "  [unresolvable operands]"])
    if operation in {"IF", "IF_ELSE"}:
        required = 2 if operation == "IF" else 4
        if len(operands) < required:
            return f"{_operation_words(operation)} [unresolvable branches]"
        labels = [_projection_operand_text(item) for item in operands]
        if operation == "IF":
            return "\n".join([
                "IF " + labels[0],
                "  THEN " + labels[1],
            ])
        return "\n".join([
            "IF",
            "  condition: " + labels[0],
            "  threshold: " + labels[1],
            "  THEN: " + labels[2],
            "  ELSE: " + labels[3],
        ])
    lines = [_operation_words(operation)]
    for index, operand in enumerate(operands):
        if not isinstance(operand, Mapping):
            lines.append(f"  operand {index + 1}: [unresolvable operand]")
            continue
        role = str(operand.get("role") or f"operand {index + 1}")
        lines.append(f"  {role}: {_projection_operand_text(operand)}")
    return "\n".join(lines)


def _projection_operand_text(operand: Any) -> str:
    """Render one projection operand, retaining an explicit unresolved id."""
    if not isinstance(operand, Mapping):
        return "[unresolvable operand]"
    text = str(operand.get("text") or operand.get("label") or "").strip()
    if text:
        return text
    ref = operand.get("ref")
    object_id = ref.get("object_id") if isinstance(ref, Mapping) else ""
    return f"[unresolvable operand{': ' + str(object_id) if object_id else ''}]"


def _single_line_operand(value: Any) -> str:
    """Render an operand on one line without hiding nested structure."""
    if not isinstance(value, Mapping):
        return "[unresolvable operand]"
    rendered = _render_tree_node(value, 0).replace("\n", " / ")
    return rendered


def _indented(value: str, indent: int, prefix: str) -> list[str]:
    """Indent a possibly nested child under a named operation role."""
    lines = value.splitlines() or ["[unresolvable operand]"]
    return [" " * indent + prefix + lines[0].lstrip()] + [" " * (indent + len(prefix)) + line.lstrip() for line in lines[1:]]


def _operation_words(operation: str) -> str:
    """Use readable operation words while preserving the operation identity."""
    return {
        "LOOKUP_TABLE": "LOOKUP TABLE",
        "LOOKUP_BRACKET": "LOOKUP BRACKET",
        "REQUIRE_INPUT": "REQUIRE INPUT",
    }.get(operation, operation)


def _tree_roles(operation: str, count: int) -> tuple[str, ...]:
    """Return stable argument names for the bounded expression vocabulary."""
    roles = {
        "COPY": ("source",),
        "SUM": ("addend",),
        "SUBTRACT": ("minuend", "subtrahend"),
        "MULTIPLY": ("factor",),
        "DIVIDE": ("numerator", "denominator"),
        "MIN": ("candidate",),
        "MAX": ("candidate",),
        "NEGATE": ("value",),
        "ABS": ("value",),
        "ROUND": ("value",),
        "COMPARE": ("left", "right"),
        "AND": ("condition",),
        "OR": ("condition",),
        "NOT": ("condition",),
    }.get(operation, ())
    if len(roles) == 1:
        return roles * count
    return roles


def _constant_text(value: Any) -> str:
    """Render a scalar constant without changing its value."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _selection_label(selection: SelectionScore) -> str:
    """Format every selection signal for the table."""
    signals = selection.as_dict()
    return "; ".join(f"{key}={value}" for key, value in signals.items())


def _render_verdicts(values: Sequence[Any]) -> str:
    """Render validator findings or warnings without turning absence into approval."""
    if not values:
        return " <span class=\"muted\">not recorded</span>"
    items = []
    for value in values:
        if isinstance(value, Mapping):
            value = json.dumps(dict(value), sort_keys=True, ensure_ascii=True)
        items.append(f"<li>{_h(value)}</li>")
    return f"<ul>{''.join(items)}</ul>"


def _instruction_note(instruction_text: str) -> str:
    """Show the second evidence source without concatenating it into the first."""
    if not instruction_text.strip():
        return ""
    return f'<details class="secondary"><summary>Instruction source</summary><pre>{_h(instruction_text)}</pre></details>'


def _compact_json(value: Any) -> str:
    """Serialize an exact graph expression for the review artifact."""
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True)


def _output_path(root: Path, document_id: str, output: str | Path | None) -> Path:
    """Resolve an output file and refuse writes inside the source repository."""
    if output is None:
        directory = Path(tempfile.mkdtemp(prefix="tax_graph_review_table_"))
        return directory / f"{document_id}.html"
    destination = Path(output).resolve()
    try:
        destination.relative_to(root)
    except ValueError:
        destination.parent.mkdir(parents=True, exist_ok=True)
        return destination
    raise ValueError(f"review table output must be outside repository root: {destination}")


def _line_sort_key(value: str) -> tuple[int, str, int, str]:
    """Sort printed line labels naturally and keep nonnumeric labels stable."""
    text = str(value).strip().lower()
    match = re.fullmatch(r"([0-9]+)([a-z]?)", text)
    if not match:
        return (1, text, 0, text)
    return (0, "", int(match.group(1)), match.group(2))


def _h(value: Any) -> str:
    """HTML-escape a value, treating missing values as empty text."""
    return escape("" if value is None else str(value), quote=True)


_CSS = """
:root { color-scheme: light; font-family: system-ui, sans-serif; }
body { margin: 0; background: #f4f5f7; color: #1e2430; }
.shell { max-width: 1800px; margin: 0 auto; padding: 24px; }
h1 { margin: 0 0 8px; }
.meta, .muted { color: #5d6878; }
table { width: 100%; border-collapse: collapse; background: white; }
th, td { border: 1px solid #cbd2dc; padding: 10px; vertical-align: top; text-align: left; }
thead th { position: sticky; top: 0; background: #e8edf3; z-index: 1; }
.line { color: #5d6878; font: 0.82rem/1.4 ui-monospace, monospace; }
td:nth-child(1) { width: 35%; }
td:nth-child(2) { width: 35%; }
td:nth-child(3) { width: 30%; }
pre { margin: 8px 0 0; white-space: pre-wrap; overflow-wrap: anywhere; font: 0.88rem/1.4 ui-monospace, monospace; }
.label { font-weight: 650; }
.score { font: 0.82rem/1.45 ui-monospace, monospace; }
.verdicts { margin-top: 10px; }
.verdicts ul { margin: 4px 0 8px; padding-left: 20px; }
details { margin-top: 8px; }
summary { cursor: pointer; color: #294e80; }
""".strip()
