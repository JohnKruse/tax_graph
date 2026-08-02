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
from tax_graph.extract.instruction_sections import (
    InstructionSectionsFrame,
    build_instruction_sections,
    empty_instruction_sections_frame,
    write_instruction_sections_artifact,
)


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
    owner_document_id: str | None = None
    owner_lines: tuple[str, ...] = ()
    section_id: str | None = None


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


def node_type_for_outline(node: OutlineNode) -> str:
    """Return the schema node type implied by an outline kind."""
    if node.kind in {"section", "heading"}:
        return "concept"
    return "form_line"


def infer_value_type(node: OutlineNode, *, document: SourceDocumentInput | None = None) -> str:
    """Infer a schema value type from the printed control represented by a node."""
    if node.kind in {"section", "heading"}:
        return "string"

    label = node.label.lower()
    fields = (document.fields or {}).get("fields", []) if document else []
    line_fields = [
        field
        for field in fields
        if str(field.get("line_anchor", "")).lower() in _line_anchor_variants(node.line_anchor)
    ]
    if line_fields and all(str(field.get("field_type", "")).lower() == "checkbox" for field in line_fields):
        return "boolean"
    if any(term in label for term in ("date", "dated", "mm/dd", "calendar year")):
        return "date"
    if any(
        term in label
        for term in (
            "social security",
            "ssn",
            "employer identification",
            "identification number",
            "form number",
        )
    ):
        return "string"
    if any(
        term in label
        for term in (
            "name",
            "address",
            "description",
            "list type",
            "city",
            "state",
            "zip",
            "email",
            "phone",
        )
    ) and not _looks_like_amount_control(label):
        return "string"
    if any(term in label for term in ("check", "yes or no", "did you", "are you", "have you")) and not _looks_like_amount_control(label):
        return "boolean"
    return "currency"


def _looks_like_amount_control(label: str) -> bool:
    return any(
        term in label
        for term in (
            "amount",
            "tax",
            "wages",
            "income",
            "payment",
            "credit",
            "deduction",
            "contribution",
            "gain",
            "loss",
            "total",
            "add lines",
        )
    )


def _line_anchor_variants(anchor: str | None) -> set[str]:
    """Return the exact normalized spelling accepted for a line anchor.

    A numeric suffix fallback (for example, treating ``16`` as ``6``) was a
    legacy workaround for lossy text extraction. The corrected line-anchor
    index carries the complete printed anchor, so accepting a shorter numeric
    spelling can silently cite the wrong line.
    """
    if not anchor:
        return {""}
    return {anchor.lower()}


def build_outline_tree(document: SourceDocumentInput) -> OutlineTree:
    """Build a deterministic outline, preferring geometry for acquired forms."""
    from tax_graph.extract.structure import build_structure_model, validate_anchor_identity

    structure = build_structure_model(document)
    if structure is not None:
        anchor_findings = validate_anchor_identity(structure)
        if anchor_findings:
            details = "; ".join(finding.detail for finding in anchor_findings)
            raise ValueError(f"{document.document_id}: anchor identity disagreement: {details}")
        return _build_geometry_outline(document, structure)

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
            if part_match and header.lower().startswith("part "):
                current_section = OutlineNode(
                    outline_id=_section_id(part_match.group(1), len(tree.children) + 1),
                    kind="section",
                    label=header,
                    page=page,
                    boxes=_extract_boxes(header),
                )
                tree.children.append(current_section)
                recent_headers = [header]
            else:
                _attach_header_to_previous_numeric_line(
                    current_section,
                    header,
                    document_id=document.document_id,
                    headers=[*recent_headers, header],
                )
            recent_headers.append(header)
            recent_headers = recent_headers[-8:]
            continue

        line_match = LINE_RE.match(line)
        if not line_match:
            continue

        raw_anchor = line_match.group(1).lower()
        body = line_match.group(2).strip()
        anchor = _canonical_line_anchor(raw_anchor, body)
        columns = _unique([*_extract_columns(" ".join(recent_headers)), *_extract_columns(body)])
        node = OutlineNode(
            outline_id=_line_id(current_section, anchor, body),
            kind=_classify_line(
                anchor,
                body,
                columns,
                headers=recent_headers,
                document_id=document.document_id,
            ),
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


def _build_geometry_outline(document: SourceDocumentInput, structure) -> OutlineTree:
    """Convert geometry rows into the outline shape consumed by extraction."""
    tree = OutlineTree(document_id=document.document_id, kind=document.kind)
    current_section: OutlineNode | None = None
    seen_ids: set[str] = set()
    geometry_only = not any(row.line_anchor for row in structure.rows)

    for row in structure.rows:
        lowered = row.text.lower().strip()
        if lowered.startswith("part ") or lowered.startswith("schedule "):
            section = OutlineNode(
                outline_id=_slug(f"section_{row.page}_{row.text}"),
                kind="section",
                label=row.text,
                page=row.page,
                boxes=_extract_boxes(row.text),
            )
            if section.outline_id not in seen_ids:
                tree.children.append(section)
                seen_ids.add(section.outline_id)
            current_section = section
            continue

        # A right-side printed reference with no caption is not a second row.
        if row.line_anchor and len(row.text.split()) <= 1:
            continue
        if not row.line_anchor:
            if row.text and (geometry_only or not tree.children):
                outline_id = _slug(f"row_{row.page}_{row.text}")
                if outline_id not in seen_ids:
                    tree.children.append(
                        OutlineNode(
                            outline_id=outline_id,
                            kind="heading",
                            label=row.text,
                            page=row.page,
                        )
                    )
                    seen_ids.add(outline_id)
            continue

        outline_id = _line_id(current_section, row.line_anchor, row.text)
        if outline_id in seen_ids:
            continue
        node = OutlineNode(
            outline_id=outline_id,
            kind=_classify_line(
                row.line_anchor,
                row.text,
                [],
                headers=[],
                document_id=document.document_id,
            ),
            label=row.text,
            page=row.page,
            line_anchor=row.line_anchor,
        )
        if current_section is not None:
            current_section.children.append(node)
        else:
            tree.children.append(node)
        seen_ids.add(outline_id)

    _merge_structure_anchor_index(document, structure.line_anchors)
    if not tree.children:
        raise ValueError(f"{document.document_id}: geometry structure produced no outline nodes")
    _attach_outbound_flow_cues(tree, document)
    return tree


def _merge_structure_anchor_index(document: SourceDocumentInput, records: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> None:
    """Replace legacy anchors with the current geometry-derived index in memory.

    The old renderer's index can contain a same-anchor entry at the wrong visual
    row. Appending geometry records leaves that stale entry first, so positional
    span resolution still cites the old location. Geometry is the S3b proposal
    for acquired PDFs; this replacement is in memory only and never rewrites the
    acquired field grid.
    """
    if document.fields is None:
        document.fields = {}
    existing: list[dict[str, Any]] = []
    seen: set[tuple[str, Any, Any]] = set()
    for record in records:
        key = (str(record.get("anchor", "")).lower(), record.get("page"), record.get("text_offset"))
        if key not in seen:
            existing.append(dict(record))
            seen.add(key)
    document.fields["line_anchors"] = existing


def build_candidate_spans(document: SourceDocumentInput) -> list[CandidateSpan]:
    """Segment form and bundled sources into verbatim candidate spans.

    Instruction spans are projections of the deterministic
    ``instruction_sections`` frame.  The raw-line fallback is retained only
    for legacy synthetic inputs that contain no line heading at all; it cannot
    create an instruction owner and therefore fails closed for the join.
    """
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
    draft_dir: str | Path | None = None,
) -> Path:
    """Write outline and candidate-span artifacts under ``graph/<year>/_drafts``."""
    if draft_dir is None:
        root_path = Path(root).resolve() if root is not None else project_root()
        settings = config or {}
        graph_dir = root_path / get_config_value(settings, "project.paths.graph_dir", "graph")
        output_dir = graph_dir / document.year / "_drafts" / document.document_id
    else:
        output_dir = Path(draft_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    outline = build_outline_tree(document)
    spans = build_candidate_spans(document)
    _write_yaml(output_dir / "outline.yaml", outline_to_dict(outline))
    _write_yaml(output_dir / "candidate_spans.yaml", [span_to_dict(span) for span in spans])
    instruction_frame = build_instruction_sections_frame(document, outline=outline)
    write_instruction_sections_artifact(instruction_frame, output_dir / "instruction_sections.yaml")
    outbound_flows = build_outbound_flows(document, outline=outline, spans=spans)
    if outbound_flows:
        _write_yaml(output_dir / "outbound_flows.yaml", [flow_to_dict(flow) for flow in outbound_flows])
    return output_dir


def build_instruction_sections_frame(
    document: SourceDocumentInput,
    *,
    outline: OutlineTree | None = None,
) -> InstructionSectionsFrame:
    """Build the persisted instruction frame for one form extraction."""
    tree = outline if outline is not None else build_outline_tree(document)
    expected_lines = {
        document.document_id: sorted(
            {
                str(node.line_anchor).lower()
                for node in _flatten_outline_nodes(tree.children)
                if node.line_anchor
            }
        )
    }
    source = next(
        (item for item in document.related_sources if item.relationship == "instructions"),
        None,
    )
    if source is None:
        return empty_instruction_sections_frame(
            source_document_id="",
            year=document.year,
            source_path=None,
        )
    return build_instruction_sections(
        source.text,
        source_document_id=source.document_id,
        year=document.year,
        source_path=source.text_path,
        expected_lines=expected_lines,
    )


def outline_to_dict(tree: OutlineTree) -> dict[str, Any]:
    """Convert an outline tree into stable YAML-friendly data."""
    return {
        "document_id": tree.document_id,
        "kind": tree.kind,
        "children": [_node_to_dict(node) for node in tree.children],
    }


def span_to_dict(span: CandidateSpan) -> dict[str, Any]:
    """Convert a candidate span to YAML-friendly data."""
    data = {
        "span_id": span.span_id,
        "document_id": span.document_id,
        "relationship": span.relationship,
        "locator": span.locator,
        "text": span.text,
    }
    if span.owner_document_id:
        data["owner_document_id"] = span.owner_document_id
    if span.owner_lines:
        data["owner_lines"] = list(span.owner_lines)
    if span.section_id:
        data["section_id"] = span.section_id
    return data


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


def _flatten_outline_nodes(nodes: list[OutlineNode]) -> list[OutlineNode]:
    """Return outline nodes in deterministic depth-first order."""
    flattened: list[OutlineNode] = []
    for node in nodes:
        flattened.append(node)
        flattened.extend(_flatten_outline_nodes(node.children))
    return flattened


def _spans_for_related_source(source: RelatedSourceInput) -> list[CandidateSpan]:
    frame = build_instruction_sections(
        source.text,
        source_document_id=source.document_id,
        source_path=source.text_path,
    )
    if frame.sections:
        return _spans_for_instruction_frame(frame)
    return _spans_for_text(source.document_id, source.relationship, source.text)


def _spans_for_instruction_frame(frame: InstructionSectionsFrame) -> list[CandidateSpan]:
    """Project each unique frame section into one evidence span."""
    spans: list[CandidateSpan] = []
    seen: set[str] = set()
    for section in frame.sections:
        if section.section_id in seen:
            continue
        seen.add(section.section_id)
        locator = section.locator
        page = f"page {locator.page}, " if locator.page is not None else ""
        spans.append(
            CandidateSpan(
                span_id=f"span_{_slug(frame.source_document_id)}_section_{len(spans) + 1:04d}",
                document_id=frame.source_document_id,
                relationship="instructions",
                locator=f"{page}lines {locator.start_line}-{locator.end_line}",
                text=section.text,
                owner_document_id=section.document_id,
                owner_lines=section.line_tokens,
                section_id=section.section_id,
            )
        )
    return spans


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


def _classify_line(
    anchor: str,
    body: str,
    columns: list[str],
    *,
    headers: list[str],
    document_id: str,
) -> str:
    lowered = body.lower()
    context = " ".join([*headers, body]).lower()
    if "schedule d" in lowered or anchor in {"3", "10"} and "schedule d" in context:
        return "outbound_flow_cue"
    if document_id.startswith("schedule_d_"):
        if anchor in FORM_8949_SCHEDULE_D_TARGETS and len(columns) >= 3:
            return "transaction_table"
        return "line"
    if _is_heading_line(body):
        return "heading"
    if "add the amounts" in lowered or lowered.startswith("totals."):
        return "totals"
    if len(columns) >= 3 or anchor == "1" and columns:
        return "transaction_table"
    return "line"


def _is_heading_line(body: str) -> bool:
    """Return whether a printed line is a non-fillable section heading."""
    lowered = body.strip().lower()
    if not lowered.endswith(":"):
        return False
    return not any(
        phrase in lowered
        for phrase in (
            "check",
            "enter",
            "list",
            "amount",
            "form number",
        )
    )


def _canonical_line_anchor(raw_anchor: str, body: str) -> str:
    """Prefer a complete printed line number when OCR split off its prefix."""
    raw_anchor = raw_anchor.lower()
    if raw_anchor.isdigit() or len(raw_anchor) != 1 or not raw_anchor.isalpha():
        return raw_anchor
    matches = re.findall(r"\b([0-9]+[a-z])\b", body.lower())
    matching = [match for match in matches if match.endswith(raw_anchor)]
    return matching[-1] if matching else raw_anchor


def _attach_header_to_previous_numeric_line(
    section: OutlineNode | None,
    header: str,
    *,
    document_id: str,
    headers: list[str],
) -> None:
    if section is None or not section.children:
        return
    node = section.children[-1]
    if not node.line_anchor or not node.line_anchor[0].isdigit():
        return
    columns = _extract_columns(header)
    if not columns and "schedule d" not in header.lower():
        return
    node.columns = _unique([*node.columns, *columns])
    node.kind = _classify_line(node.line_anchor, node.label, node.columns, headers=headers, document_id=document_id)


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
    return _unique(match.group(1).lower() for match in COLUMN_RE.finditer(text) if match.group(1).lower() in "abcdefgh")


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
