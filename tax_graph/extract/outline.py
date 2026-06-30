"""Outline-first extraction helpers.

These helpers create local, reviewable structure and evidence artifacts before
any graph objects are assembled. The artifacts live under ``_drafts`` and are
regenerated, not promoted directly into the authored graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

import yaml

from tax_graph.config import get_config_value, project_root
from tax_graph.extract.models import RelatedSourceInput, SourceDocumentInput


PART_RE = re.compile(r"\bpart\s+([ivxlcdm]+)\b", re.IGNORECASE)
COLUMN_RE = re.compile(r"\(([a-z])\)", re.IGNORECASE)
BOX_RE = re.compile(r"\bbox\s+([a-z])\b", re.IGNORECASE)
LINE_RE = re.compile(r"^-\s+([0-9]+[a-z]?|[a-z]):\s*(.*)$", re.IGNORECASE)
PAGE_RE = re.compile(r"^#\s+Page\s+([0-9]+)", re.IGNORECASE)
FORM_8949_SCHEDULE_D_TARGETS = {"1b", "2", "3", "8b", "9", "10"}


@dataclass(frozen=True)
class CandidateSpan:
    """A code-generated verbatim source span the model may select by id."""

    span_id: str
    document_id: str
    relationship: str
    locator: str
    text: str


@dataclass
class OutlineNode:
    """One node in a rendered form outline tree."""

    outline_id: str
    kind: str
    label: str
    page: int | None = None
    line_anchor: str | None = None
    columns: list[str] = field(default_factory=list)
    boxes: list[str] = field(default_factory=list)
    confidence: float = 1.0
    children: list["OutlineNode"] = field(default_factory=list)


@dataclass
class OutlineTree:
    """A document-level outline tree."""

    document_id: str
    kind: str
    children: list[OutlineNode] = field(default_factory=list)


@dataclass(frozen=True)
class OutboundFlow:
    """Intermediate cross-document flow declaration."""

    flow_id: str
    source_document_id: str
    source_outline_id: str
    source_node_id: str
    target_document_id: str
    target_line: str
    citation_span_ids: list[str]
    confidence: float = 0.8


def build_outline_tree(document: SourceDocumentInput) -> OutlineTree:
    """Build a mostly deterministic outline from rendered form text."""
    tree = OutlineTree(document_id=document.document_id, kind=document.kind)
    current_section: OutlineNode | None = None
    recent_headers: list[str] = []
    page: int | None = None

    for raw_line in document.text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        page_match = PAGE_RE.match(line)
        if page_match:
            page = int(page_match.group(1))
            continue

        if line.startswith("Header:"):
            header = line.removeprefix("Header:").strip()
            part_match = PART_RE.search(header)
            if part_match:
                current_section = OutlineNode(
                    outline_id=_section_id(part_match.group(1), len(tree.children) + 1),
                    kind="section",
                    label=header,
                    page=page,
                    boxes=_extract_boxes(header),
                )
                tree.children.append(current_section)
            recent_headers.append(header)
            recent_headers = recent_headers[-4:]
            continue

        line_match = LINE_RE.match(line)
        if not line_match:
            continue

        anchor = line_match.group(1).lower()
        body = line_match.group(2).strip()
        columns = _unique([*_extract_columns(" ".join(recent_headers)), *_extract_columns(body)])
        node = OutlineNode(
            outline_id=_line_id(current_section, anchor, body),
            kind=_classify_line(anchor, body, columns, headers=recent_headers),
            label=body or f"Line {anchor}",
            page=page,
            line_anchor=anchor,
            columns=columns,
        )
        if current_section is not None:
            current_section.children.append(node)
        else:
            tree.children.append(node)

    _attach_outbound_flow_cues(tree, document)
    return tree


def build_candidate_spans(document: SourceDocumentInput) -> list[CandidateSpan]:
    """Segment form and bundled sources into verbatim candidate spans."""
    spans: list[CandidateSpan] = []
    spans.extend(_spans_for_text(document.document_id, "source", document.text))
    for source in document.related_sources:
        spans.extend(_spans_for_related_source(source))
    return spans


def build_outbound_flows(
    document: SourceDocumentInput,
    *,
    outline: OutlineTree | None = None,
    spans: list[CandidateSpan] | None = None,
) -> list[OutboundFlow]:
    """Build intermediate outbound flow declarations from bundled evidence."""
    tree = outline if outline is not None else build_outline_tree(document)
    candidate_spans = spans if spans is not None else build_candidate_spans(document)
    flows: list[OutboundFlow] = []
    seen: set[tuple[str, str, str]] = set()
    for span in candidate_spans:
        if "schedule d" not in span.text.lower():
            continue
        for target_line in _schedule_d_targets(span.text):
            target_document_id = f"schedule_d_{document.year}"
            source_outline = _source_outline_for_target(tree, target_line)
            source_node = _source_node_id(document.document_id, source_outline, "column_h")
            identity = (source_node, target_document_id, target_line)
            if identity in seen:
                continue
            seen.add(identity)
            flows.append(
                OutboundFlow(
                    flow_id=_slug(f"flow_{source_node}_to_{target_document_id}_line_{target_line}"),
                    source_document_id=document.document_id,
                    source_outline_id=source_outline,
                    source_node_id=source_node,
                    target_document_id=target_document_id,
                    target_line=target_line,
                    citation_span_ids=[span.span_id],
                )
            )
    return flows


def write_outline_artifacts(
    document: SourceDocumentInput,
    *,
    root: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> Path:
    """Write outline and candidate-span artifacts under ``graph/<year>/_drafts``."""
    root_path = Path(root).resolve() if root is not None else project_root()
    settings = config or {}
    graph_dir = root_path / get_config_value(settings, "project.paths.graph_dir", "graph")
    draft_dir = graph_dir / document.year / "_drafts" / document.document_id
    draft_dir.mkdir(parents=True, exist_ok=True)

    outline = build_outline_tree(document)
    spans = build_candidate_spans(document)
    _write_yaml(draft_dir / "outline.yaml", outline_to_dict(outline))
    _write_yaml(draft_dir / "candidate_spans.yaml", [span_to_dict(span) for span in spans])
    outbound_flows = build_outbound_flows(document, outline=outline, spans=spans)
    if outbound_flows:
        _write_yaml(draft_dir / "outbound_flows.yaml", [flow_to_dict(flow) for flow in outbound_flows])
    return draft_dir


def outline_to_dict(tree: OutlineTree) -> dict[str, Any]:
    """Convert an outline tree into stable YAML-friendly data."""
    return {
        "document_id": tree.document_id,
        "kind": tree.kind,
        "children": [_node_to_dict(node) for node in tree.children],
    }


def span_to_dict(span: CandidateSpan) -> dict[str, Any]:
    """Convert a candidate span to YAML-friendly data."""
    return {
        "span_id": span.span_id,
        "document_id": span.document_id,
        "relationship": span.relationship,
        "locator": span.locator,
        "text": span.text,
    }


def flow_to_dict(flow: OutboundFlow) -> dict[str, Any]:
    """Convert an outbound flow to YAML-friendly data."""
    return {
        "flow_id": flow.flow_id,
        "source_document_id": flow.source_document_id,
        "source_outline_id": flow.source_outline_id,
        "source_node_id": flow.source_node_id,
        "target_document_id": flow.target_document_id,
        "target_line": flow.target_line,
        "citation_span_ids": flow.citation_span_ids,
        "confidence": flow.confidence,
    }


def _node_to_dict(node: OutlineNode) -> dict[str, Any]:
    data: dict[str, Any] = {
        "outline_id": node.outline_id,
        "kind": node.kind,
        "label": node.label,
        "confidence": node.confidence,
    }
    if node.page is not None:
        data["page"] = node.page
    if node.line_anchor:
        data["line_anchor"] = node.line_anchor
    if node.columns:
        data["columns"] = node.columns
    if node.boxes:
        data["boxes"] = node.boxes
    if node.children:
        data["children"] = [_node_to_dict(child) for child in node.children]
    return data


def _spans_for_related_source(source: RelatedSourceInput) -> list[CandidateSpan]:
    return _spans_for_text(source.document_id, source.relationship, source.text)


def _spans_for_text(document_id: str, relationship: str, text: str) -> list[CandidateSpan]:
    spans: list[CandidateSpan] = []
    page = 1
    index = 1
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        page_match = PAGE_RE.match(line)
        if page_match:
            page = int(page_match.group(1))
            continue
        spans.append(
            CandidateSpan(
                span_id=f"span_{_slug(document_id)}_{index:04d}",
                document_id=document_id,
                relationship=relationship,
                locator=f"page {page}, line {line_number}",
                text=line,
            )
        )
        index += 1
    return spans


def _classify_line(anchor: str, body: str, columns: list[str], *, headers: list[str]) -> str:
    lowered = body.lower()
    context = " ".join([*headers, body]).lower()
    if "schedule d" in lowered or anchor in {"3", "10"} and "schedule d" in context:
        return "outbound_flow_cue"
    if "total" in lowered or "add the amounts" in lowered:
        return "totals"
    if len(columns) >= 3 or anchor == "1" and columns:
        return "transaction_table"
    return "line"


def _attach_outbound_flow_cues(tree: OutlineTree, document: SourceDocumentInput) -> None:
    related_text = "\n".join(source.text for source in document.related_sources)
    if "schedule d" not in related_text.lower():
        return
    targets = _schedule_d_targets(related_text)
    if not targets:
        return
    cue = OutlineNode(
        outline_id="outbound_schedule_d",
        kind="outbound_flow_cue",
        label=f"Schedule D outbound flow candidates: {', '.join(targets)}",
        confidence=0.8,
    )
    tree.children.append(cue)


def _source_outline_for_target(tree: OutlineTree, target_line: str) -> str:
    preferred_section = _preferred_source_section(target_line)
    preferred = _find_totals_outline(tree.children, preferred_section=preferred_section)
    if preferred:
        return preferred
    fallback = _find_totals_outline(tree.children, preferred_section=None)
    return fallback or "outbound_schedule_d"


def _preferred_source_section(target_line: str) -> str | None:
    if target_line in {"1b", "2", "3"}:
        return "part_i"
    if target_line in {"8b", "9", "10"}:
        return "part_ii"
    return None


def _find_totals_outline(nodes: list[OutlineNode], *, preferred_section: str | None) -> str | None:
    for node in nodes:
        if preferred_section and node.outline_id != preferred_section:
            continue
        for child in node.children:
            if child.kind == "totals" and (not child.columns or "h" in child.columns):
                return child.outline_id
    if preferred_section:
        return None
    for node in nodes:
        if node.kind == "totals" and (not node.columns or "h" in node.columns):
            return node.outline_id
        found = _find_totals_outline(node.children, preferred_section=None)
        if found:
            return found
    return None


def _schedule_d_targets(text: str) -> list[str]:
    seen: list[str] = []
    for match in re.finditer(r"schedule\s+d[^.\n]*?line(?:s)?\s+([0-9a-z,\sand]+)", text, re.IGNORECASE):
        for target in re.findall(r"[0-9]+[a-z]?", match.group(1), re.IGNORECASE):
            normalized = target.lower()
            if normalized in FORM_8949_SCHEDULE_D_TARGETS and normalized not in seen:
                seen.append(normalized)
    return seen


def _section_id(part: str, fallback: int) -> str:
    roman = part.lower()
    return f"part_{roman}" if roman else f"section_{fallback}"


def _line_id(section: OutlineNode | None, anchor: str, body: str) -> str:
    prefix = section.outline_id if section else "root"
    return f"{prefix}_line_{_slug(anchor)}"


def _source_node_id(document_id: str, source_outline_id: str, column: str) -> str:
    return _slug(f"{document_id}_{source_outline_id}_{column}")


def _extract_columns(text: str) -> list[str]:
    return _unique(match.group(1).lower() for match in COLUMN_RE.finditer(text))


def _extract_boxes(text: str) -> list[str]:
    return _unique(match.group(1).upper() for match in BOX_RE.finditer(text))


def _unique(values) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "item"


def _write_yaml(path: Path, data: Any) -> None:
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=False)
    path.write_text(text, encoding="utf-8", newline="\n")
