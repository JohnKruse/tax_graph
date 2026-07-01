"""HTML review artifact for extraction drafts."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
import json
import re
from typing import Any

import yaml

from tax_graph.extract.models import DRAFT_KINDS, DraftObject, ExtractionBatch, RoutedDrafts, SourceDocumentInput


@dataclass(frozen=True)
class SourceLine:
    """One rendered source line displayed in the visual review."""

    line_id: str
    document_id: str
    relationship: str
    number: int
    text: str


@dataclass(frozen=True)
class TableSlot:
    """One physical table row slot found in AcroForm fields."""

    part: str
    line_anchor: str
    row: int
    columns: tuple[str, ...]


def write_review_html(
    draft_dir: Path,
    *,
    batch: ExtractionBatch,
    routed: RoutedDrafts,
    document: SourceDocumentInput,
) -> Path:
    """Write a standalone visual review page beside ``review.md``."""
    path = draft_dir / "review.html"
    path.write_text(
        _ascii(render_review_html(batch=batch, routed=routed, document=document, draft_dir=draft_dir)),
        encoding="utf-8",
        newline="\n",
    )
    return path


def render_review_html(
    *,
    batch: ExtractionBatch,
    routed: RoutedDrafts,
    document: SourceDocumentInput,
    draft_dir: Path | None = None,
) -> str:
    """Render a standalone source-to-draft visual review page."""
    objects = batch.objects
    source_lines = _source_lines(document)
    source_links = _source_links(objects, source_lines)
    source_lines_by_id = {line.line_id: line for line in source_lines}
    accepted_ids = {(obj.kind, obj.object_id) for obj in routed.accepted}
    review_ids = {(obj.kind, obj.object_id) for obj in routed.review}
    outline = _load_yaml(draft_dir / "outline.yaml") if draft_dir else None
    outbound_flows = _load_yaml(draft_dir / "outbound_flows.yaml") if draft_dir else None

    parts = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>Extraction Review - {_h(batch.document_id)}</title>",
        "<style>",
        _CSS,
        "</style>",
        "</head>",
        "<body>",
        '<main class="shell">',
        _summary(batch, routed),
        _structure_panel(document, outline),
        '<section class="review-grid" aria-label="Visual extraction review">',
        '<section class="pane source-pane">',
        "<h2>Source Evidence</h2>",
        _source_panel(source_lines, source_links),
        "</section>",
        '<section class="pane draft-pane">',
        "<h2>Extracted Drafts</h2>",
        _object_panel(objects, source_links, source_lines_by_id, accepted_ids, review_ids),
        _issues_panel(routed),
        _outline_panel(outline),
        _outbound_panel(outbound_flows),
        "</section>",
        "</section>",
        "</main>",
        "<script>",
        _JS,
        "</script>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts) + "\n"


def _summary(batch: ExtractionBatch, routed: RoutedDrafts) -> str:
    return "\n".join(
        [
            '<header class="topbar">',
            "<div>",
            f"<h1>Extraction Review - {_h(batch.document_id)}</h1>",
            f'<p class="muted">Tax year {_h(batch.year)}. Drafts remain local under _drafts until human promotion.</p>',
            "</div>",
            '<dl class="metrics">',
            f"<div><dt>Accepted</dt><dd>{len(routed.accepted)}</dd></div>",
            f"<div><dt>Review</dt><dd>{len(routed.review)}</dd></div>",
            f"<div><dt>Issues</dt><dd>{len(routed.issues)}</dd></div>",
            "</dl>",
            "</header>",
        ]
    )


def _source_panel(source_lines: list[SourceLine], source_links: dict[str, list[DraftObject]]) -> str:
    grouped: dict[tuple[str, str], list[SourceLine]] = {}
    for line in source_lines:
        grouped.setdefault((line.document_id, line.relationship), []).append(line)

    parts: list[str] = []
    for (document_id, relationship), lines in grouped.items():
        parts.append('<article class="source-doc">')
        parts.append(f"<h3>{_h(document_id)} <span>{_h(relationship)}</span></h3>")
        parts.append('<ol class="source-lines">')
        for line in lines:
            linked = source_links.get(line.line_id, [])
            refs = " ".join(
                f'<button type="button" class="mini-ref" data-target="{_h(_object_dom_id(obj))}">{_h(_object_chip_label(obj))}</button>'
                for obj in linked[:4]
            )
            more = f'<span class="more">+{len(linked) - 4}</span>' if len(linked) > 4 else ""
            parts.append(
                f'<li id="{_h(line.line_id)}" data-line="{_h(line.line_id)}">'
                f'<span class="line-no">{line.number}</span>'
                f'<code>{_h(line.text)}</code>'
                f'<span class="refs">{refs}{more}</span>'
                "</li>"
            )
        parts.append("</ol>")
        parts.append("</article>")
    return "\n".join(parts)


def _object_panel(
    objects: list[DraftObject],
    source_links: dict[str, list[DraftObject]],
    source_lines_by_id: dict[str, SourceLine],
    accepted_ids: set[tuple[str, str]],
    review_ids: set[tuple[str, str]],
) -> str:
    object_to_lines = _object_to_lines(source_links)
    parts = ['<div class="object-groups">']
    for kind in DRAFT_KINDS:
        kind_objects = [obj for obj in objects if obj.kind == kind]
        if not kind_objects:
            continue
        parts.append(f"<h3>{_h(kind.title())}</h3>")
        for obj in kind_objects:
            status = "accepted" if (obj.kind, obj.object_id) in accepted_ids else "review" if (obj.kind, obj.object_id) in review_ids else "draft"
            evidence_links = " ".join(
                f'<a href="#{_h(line_id)}" data-target="{_h(line_id)}">{_h(_source_line_label(source_lines_by_id[line_id]))}</a>'
                for line_id in object_to_lines.get(obj.object_id, [])[:8]
                if line_id in source_lines_by_id
            )
            flags = "".join(f"<li>{_h(flag)}</li>" for flag in obj.flags)
            parts.append(
                "\n".join(
                    [
                        f'<article id="{_h(_object_dom_id(obj))}" class="object-card {status}" data-object="{_h(_object_dom_id(obj))}">',
                        '<div class="object-head">',
                        f"<strong>{_h(_object_title(obj))}</strong>",
                        f'<span class="badge">{_h(status)}</span>',
                        "</div>",
                        _object_facts(obj),
                        f'<details><summary>Raw schema object</summary><pre>{_h(_compact_json(obj.data))}</pre></details>',
                        f'<p class="evidence">Evidence: {evidence_links or "<span>none linked</span>"}</p>',
                        f'<p class="confidence">confidence={obj.confidence:.3f} critic_agrees={str(obj.critic_agrees).lower()}</p>',
                        f"<ul>{flags}</ul>" if flags else "",
                        "</article>",
                    ]
                )
            )
    parts.append("</div>")
    return "\n".join(parts)


def _structure_panel(document: SourceDocumentInput, outline: Any) -> str:
    slots = _table_slots(document)
    rows_by_table: dict[tuple[str, str], list[TableSlot]] = {}
    for slot in slots:
        rows_by_table.setdefault((slot.part, slot.line_anchor), []).append(slot)

    table_cards = []
    for (part, line_anchor), table_slots in sorted(rows_by_table.items(), key=lambda item: (_part_order(item[0][0]), item[0][1])):
        rows = sorted(table_slots, key=lambda slot: slot.row)
        columns = rows[0].columns if rows else ()
        table_cards.append(
            "\n".join(
                [
                    '<article class="structure-card">',
                    f"<h3>{_h(_part_label(part))} - IRS line {line_anchor} transaction table</h3>",
                    f'<p class="muted">{len(rows)} printed row slots. Columns: {_h(", ".join(columns))}.</p>',
                    f'<p><strong>Review labels:</strong> {_h(_row_range_label(line_anchor, rows))}</p>',
                    f'<p><strong>Row-template formula:</strong> line {line_anchor}[row].column_h = column_d - column_e + column_g.</p>',
                    f'<p><strong>Review-only slot label:</strong> {_h(part)}.line_{_h(line_anchor)}.row_01.column_h (physical geometry, not a runtime row key).</p>',
                    "</article>",
                ]
            )
        )

    outline_note = ""
    if outline:
        outline_note = '<p class="muted">Outline ids such as part_i_line_1 refer to IRS anchors/table templates, not a single printed row.</p>'

    return "\n".join(
        [
            '<section class="structure-panel">',
            "<h2>Form Structure</h2>",
            '<p class="muted">IRS line anchor = legal form line. Source L# = rendered text line. Row slot = physical blank table row from the field grid. Runtime instances use column_node#row_key, not row_01.</p>',
            outline_note,
            "".join(table_cards) if table_cards else '<p class="muted">No repeatable table row slots were found in the field grid.</p>',
            "</section>",
        ]
    )


def _issues_panel(routed: RoutedDrafts) -> str:
    if not routed.issues:
        return '<section class="side-section"><h3>Deterministic Issues</h3><p class="muted">none</p></section>'
    items = "\n".join(f"<li>{_h(issue.kind)}/{_h(issue.object_id)}: {_h(issue.reason)}</li>" for issue in routed.issues)
    return f'<section class="side-section"><h3>Deterministic Issues</h3><ul>{items}</ul></section>'


def _outline_panel(outline: Any) -> str:
    if not outline:
        return '<section class="side-section"><h3>Outline</h3><p class="muted">No outline artifact found.</p></section>'
    return "\n".join(
        [
            '<section class="side-section">',
            "<h3>Outline</h3>",
            _outline_nodes(outline.get("children", [])),
            "</section>",
        ]
    )


def _outline_nodes(nodes: list[dict[str, Any]]) -> str:
    if not nodes:
        return "<p class=\"muted\">none</p>"
    items = []
    for node in nodes:
        columns = f" columns={','.join(str(column) for column in node.get('columns', []))}" if node.get("columns") else ""
        items.append(
            "<li>"
            f"<strong>{_h(node.get('outline_id', ''))}</strong> "
            f"<span>{_h(node.get('kind', ''))}{_h(columns)}</span>"
            f"<p>{_h(node.get('label', ''))}</p>"
            f"{_outline_nodes(node.get('children', [])) if node.get('children') else ''}"
            "</li>"
        )
    return f'<ul class="outline-tree">{"".join(items)}</ul>'


def _outbound_panel(outbound_flows: Any) -> str:
    if not outbound_flows:
        return '<section class="side-section"><h3>Outbound Flows</h3><p class="muted">none</p></section>'
    rows = []
    for flow in outbound_flows:
        rows.append(
            "<tr>"
            f"<td>{_h(flow.get('source_node_id', ''))}</td>"
            f"<td>{_h(flow.get('target_document_id', ''))}</td>"
            f"<td>{_h(flow.get('target_line', ''))}</td>"
            f"<td>{_h(', '.join(str(item) for item in flow.get('citation_span_ids', [])))}</td>"
            "</tr>"
        )
    return "\n".join(
        [
            '<section class="side-section">',
            "<h3>Outbound Flows</h3>",
            '<table><thead><tr><th>Source</th><th>Target Doc</th><th>Line</th><th>Span</th></tr></thead>',
            f"<tbody>{''.join(rows)}</tbody></table>",
            "</section>",
        ]
    )


def _source_lines(document: SourceDocumentInput) -> list[SourceLine]:
    lines = _lines_for_text(document.document_id, "source", document.text)
    for source in document.related_sources:
        lines.extend(_lines_for_text(source.document_id, source.relationship, source.text))
    return lines


def _table_slots(document: SourceDocumentInput) -> list[TableSlot]:
    fields = (document.fields or {}).get("fields", [])
    row_pattern = re.compile(r"Table_Line(?P<line>[0-9]+)_Part(?P<part>[0-9]+)\[\d+\]\.Row(?P<row>[0-9]+)")
    rows: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for field in fields:
        match = row_pattern.search(str(field.get("field_name", "")))
        if not match:
            continue
        part = _part_id(match.group("part"))
        line_anchor = match.group("line")
        row = int(match.group("row"))
        rows.setdefault((part, line_anchor, row), []).append(field)

    slots = []
    for (part, line_anchor, row), row_fields in rows.items():
        ordered_fields = sorted(row_fields, key=lambda field: (int(field.get("x_cluster", 0)), str(field.get("field_name", ""))))
        columns = tuple(chr(ord("a") + index) for index, _field in enumerate(ordered_fields))
        slots.append(TableSlot(part=part, line_anchor=line_anchor, row=row, columns=columns))
    return slots


def _lines_for_text(document_id: str, relationship: str, text: str) -> list[SourceLine]:
    lines = []
    for number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        lines.append(
            SourceLine(
                line_id=f"line-{_slug(document_id)}-{number}",
                document_id=document_id,
                relationship=relationship,
                number=number,
                text=line,
            )
        )
    return lines


def _source_links(objects: list[DraftObject], source_lines: list[SourceLine]) -> dict[str, list[DraftObject]]:
    links: dict[str, list[DraftObject]] = {}
    for line in source_lines:
        normalized_line = _normalize(line.text)
        for obj in objects:
            if _object_mentions_line(obj, normalized_line):
                links.setdefault(line.line_id, []).append(obj)
    return links


def _object_mentions_line(obj: DraftObject, normalized_line: str) -> bool:
    source_span = _normalize(obj.source_span)
    if normalized_line and normalized_line in source_span:
        return True
    if obj.kind == "citations":
        quoted = _normalize(str(obj.data.get("quoted_text", "")))
        return bool(quoted and (quoted in normalized_line or normalized_line in quoted))
    return False


def _object_to_lines(source_links: dict[str, list[DraftObject]]) -> dict[str, list[str]]:
    object_to_lines: dict[str, list[str]] = {}
    for line_id, objects in source_links.items():
        for obj in objects:
            object_to_lines.setdefault(obj.object_id, []).append(line_id)
    return object_to_lines


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _compact_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


def _object_title(obj: DraftObject) -> str:
    if obj.kind == "rules":
        return f"Rule - {obj.data.get('operation', '')} - {_human_object_id(obj.object_id)}"
    if obj.kind == "nodes":
        label = str(obj.data.get("label") or "")
        context = _human_object_id(obj.object_id)
        return f"Node - {context}" + (f" - {label}" if label else "")
    if obj.kind == "edges":
        return f"Edge - {_human_object_id(str(obj.data.get('source', '')))} -> {_human_object_id(str(obj.data.get('target', '')))}"
    if obj.kind == "citations":
        return f"Citation - {_human_object_id(obj.object_id)}"
    return f"{obj.kind} - {_human_object_id(obj.object_id)}"


def _object_facts(obj: DraftObject) -> str:
    facts = []
    if obj.kind == "nodes":
        facts.extend(
            [
                ("id", obj.object_id),
                ("label", obj.data.get("label", "")),
                ("type", obj.data.get("node_type", "")),
                ("value", obj.data.get("value_type", "")),
            ]
        )
    elif obj.kind == "rules":
        facts.extend(
            [
                ("id", obj.object_id),
                ("operation", obj.data.get("operation", "")),
                ("description", obj.data.get("description", "")),
            ]
        )
    elif obj.kind == "edges":
        facts.extend(
            [
                ("id", obj.object_id),
                ("source", obj.data.get("source", "")),
                ("target", obj.data.get("target", "")),
                ("role", obj.data.get("role", "")),
            ]
        )
    elif obj.kind == "citations":
        quoted = str(obj.data.get("quoted_text", ""))
        facts.extend(
            [
                ("id", obj.object_id),
                ("document", obj.data.get("document_id", "")),
                ("locator", obj.data.get("locator", "")),
                ("quote", quoted[:220] + ("..." if len(quoted) > 220 else "")),
            ]
        )
    else:
        facts.append(("id", obj.object_id))
    rows = "".join(f"<dt>{_h(name)}</dt><dd>{_h(value)}</dd>" for name, value in facts if value != "")
    return f'<dl class="object-facts">{rows}</dl>'


def _object_chip_label(obj: DraftObject) -> str:
    prefix = {"nodes": "node", "rules": "rule", "edges": "edge", "citations": "cite", "decisions": "decision"}.get(obj.kind, obj.kind)
    if obj.kind == "rules":
        return f"{prefix}: {obj.data.get('operation', '')} {_short_object_id(obj.object_id)}"
    if obj.kind == "nodes":
        return f"{prefix}: {_short_object_id(obj.object_id)}"
    return f"{prefix}: {_short_object_id(obj.object_id)}"


def _source_line_label(line: SourceLine) -> str:
    document_label = "form" if line.relationship == "source" else _short_document_id(line.document_id)
    return f"{document_label} L{line.number}"


def _short_document_id(document_id: str) -> str:
    value = document_id.replace("instructions_", "instr_")
    return value.replace("_2025", "")


def _short_object_id(object_id: str) -> str:
    value = object_id.replace("form_8949_2025_", "")
    value = value.replace("instructions_form_8949_2025_", "instr_")
    return value


def _human_object_id(object_id: str) -> str:
    value = _short_object_id(object_id)
    replacements = {
        "part_i": "Part I",
        "part_ii": "Part II",
        "line_": "line ",
        "column_": "column ",
        "_total": " total",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = value.replace("_", " ")
    value = re.sub(r"\bline ([0-9]+) line \1\b", r"line \1", value)
    return value


def _part_id(number: str) -> str:
    return {"1": "part_i", "2": "part_ii"}.get(number, f"part_{number}")


def _part_label(part: str) -> str:
    return {"part_i": "Part I", "part_ii": "Part II"}.get(part, part.replace("_", " ").title())


def _part_order(part: str) -> int:
    return {"part_i": 1, "part_ii": 2}.get(part, 99)


def _row_range_label(line_anchor: str, rows: list[TableSlot]) -> str:
    if not rows:
        return "none"
    first = rows[0].row
    last = rows[-1].row
    return f"line {line_anchor}.{first:02d} through line {line_anchor}.{last:02d}"


def _object_dom_id(obj: DraftObject) -> str:
    return f"obj-{_slug(obj.kind)}-{_slug(obj.object_id)}"


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"


def _h(value: Any) -> str:
    return escape(str(value), quote=True)


def _ascii(text: str) -> str:
    return text.encode("ascii", "xmlcharrefreplace").decode("ascii")


_CSS = """
:root {
  color-scheme: light;
  --bg: #f6f7f2;
  --panel: #ffffff;
  --ink: #20231f;
  --muted: #62685f;
  --line: #d9ded2;
  --accent: #1f7a65;
  --accent-2: #8a4b2d;
  --warn: #a84b39;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.shell { max-width: 1680px; margin: 0 auto; padding: 20px; }
.topbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 16px;
}
h1, h2, h3 { margin: 0; font-weight: 700; letter-spacing: 0; }
h1 { font-size: 24px; }
h2 { font-size: 18px; margin-bottom: 12px; }
h3 { font-size: 14px; margin: 16px 0 8px; }
.muted { color: var(--muted); margin: 4px 0 0; }
.metrics { display: flex; gap: 10px; margin: 0; }
.metrics div {
  min-width: 88px;
  padding: 8px 10px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.metrics dt { color: var(--muted); font-size: 12px; }
.metrics dd { margin: 0; font-size: 22px; font-weight: 700; }
.review-grid {
  display: grid;
  grid-template-columns: minmax(420px, 1fr) minmax(520px, 1.15fr);
  gap: 16px;
  align-items: start;
}
.structure-panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 16px;
}
.structure-panel h2 { margin-bottom: 6px; }
.structure-card {
  display: inline-block;
  width: min(100%, 520px);
  vertical-align: top;
  border: 1px solid var(--line);
  border-left: 4px solid var(--accent-2);
  border-radius: 8px;
  padding: 10px;
  margin: 10px 10px 0 0;
  background: #fffefa;
}
.structure-card h3 { margin-top: 0; }
.structure-card p { margin: 6px 0 0; }
.pane {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  min-width: 0;
}
.source-pane, .draft-pane { max-height: calc(100vh - 128px); overflow: auto; }
.source-doc h3 span {
  color: var(--muted);
  font-weight: 600;
  margin-left: 6px;
}
.source-lines {
  list-style: none;
  margin: 0;
  padding: 0;
  border-top: 1px solid var(--line);
}
.source-lines li {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr) auto;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid var(--line);
}
.source-lines code {
  white-space: pre-wrap;
  word-break: break-word;
  font: 12px/1.35 ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
}
.line-no { color: var(--muted); text-align: right; font-variant-numeric: tabular-nums; }
.refs { display: flex; flex-wrap: wrap; gap: 4px; justify-content: flex-end; }
.mini-ref, .badge, .more {
  border: 1px solid var(--line);
  background: #eef4ef;
  color: var(--accent);
  border-radius: 999px;
  padding: 2px 6px;
  font-size: 11px;
}
.mini-ref { cursor: pointer; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.object-card {
  border: 1px solid var(--line);
  border-left: 4px solid var(--accent);
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 10px;
  background: #fffefa;
}
.object-card.review { border-left-color: var(--warn); }
.object-head { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
.object-head strong { min-width: 0; overflow-wrap: anywhere; }
.object-facts {
  display: grid;
  grid-template-columns: minmax(76px, auto) minmax(0, 1fr);
  gap: 4px 8px;
  margin: 8px 0;
}
.object-facts dt { color: var(--muted); font-weight: 700; }
.object-facts dd { margin: 0; overflow-wrap: anywhere; }
details {
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #f8f9f5;
}
summary {
  cursor: pointer;
  padding: 6px 8px;
  color: var(--muted);
  font-weight: 700;
}
pre {
  margin: 8px 0;
  padding: 8px;
  background: #f3f5ef;
  border-radius: 6px;
  overflow: auto;
  font: 12px/1.35 ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
}
.evidence, .confidence { margin: 6px 0 0; color: var(--muted); }
.evidence a {
  display: inline-block;
  margin: 2px 4px 2px 0;
  color: var(--accent-2);
}
.side-section {
  border-top: 1px solid var(--line);
  margin-top: 16px;
  padding-top: 12px;
}
.outline-tree { list-style: none; padding-left: 14px; }
.outline-tree li { border-left: 2px solid var(--line); padding-left: 10px; margin: 6px 0; }
.outline-tree p { margin: 2px 0 0; color: var(--muted); }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { border: 1px solid var(--line); padding: 6px; text-align: left; vertical-align: top; }
.active {
  outline: 2px solid var(--accent-2);
  outline-offset: 2px;
  background: #fff7df !important;
}
@media (max-width: 980px) {
  .topbar { display: block; }
  .metrics { margin-top: 12px; }
  .review-grid { grid-template-columns: 1fr; }
  .source-pane, .draft-pane { max-height: none; }
}
"""


_JS = """
const activeClass = "active";
function clearActive() {
  document.querySelectorAll("." + activeClass).forEach((el) => el.classList.remove(activeClass));
}
function activate(id) {
  const target = document.getElementById(id);
  if (!target) return;
  clearActive();
  target.classList.add(activeClass);
  target.scrollIntoView({ block: "center", behavior: "smooth" });
}
document.addEventListener("click", (event) => {
  const trigger = event.target.closest("[data-target]");
  if (!trigger) return;
  event.preventDefault();
  activate(trigger.dataset.target);
});
"""
