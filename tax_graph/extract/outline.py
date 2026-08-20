"""Outline-first extraction helpers.

These helpers create local, reviewable structure and evidence artifacts before
any graph objects are assembled. The artifacts live under ``_drafts`` and are
regenerated, not promoted directly into the authored graph.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

import yaml

from tax_graph.acquire.text_normalize import normalize_punctuation
from tax_graph.config import get_config_value, project_root
from tax_graph.extract.models import RelatedSourceInput, SourceDocumentInput
from tax_graph.acquire.source_ranges import SourceTextIndex
from tax_graph.extract.evidence import normalize_evidence_text
from tax_graph.extract.structure import StructureFinding, StructureRow
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
    findings: tuple[dict[str, Any], ...] = ()
    extent: dict[str, Any] = field(default_factory=dict)
    source_ranges: tuple[dict[str, int], ...] = ()
    joined_from: tuple[str, ...] = ()
    evidence_text: str | None = None


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

    for _line_number, line in _assembled_legacy_lines(document.text):
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

    for row in _assemble_structure_rows(structure.rows, source_text=document.text):
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


def _assembled_legacy_lines(text: str) -> list[tuple[int, str]]:
    """Return text lines with legacy anchored rows assembled in source order.

    Older synthetic fixtures use ``- <anchor>:`` markup. A continuation belongs
    to the preceding row until a new anchor, header, page marker, or blank line
    appears. Joining with one space preserves the source order while making the
    outline label and its evidence span agree on the same logical row.
    """
    raw_lines = text.splitlines()
    assembled: list[tuple[int, str]] = []
    index = 0
    while index < len(raw_lines):
        line = raw_lines[index].strip()
        if not line:
            index += 1
            continue
        if LINE_RE.match(line):
            parts = [line]
            next_index = index + 1
            while next_index < len(raw_lines):
                continuation = raw_lines[next_index].strip()
                if (
                    not continuation
                    or PAGE_RE.match(continuation)
                    or continuation.startswith("Header:")
                    or LINE_RE.match(continuation)
                ):
                    break
                parts.append(continuation)
                next_index += 1
            assembled.append((index + 1, " ".join(parts)))
            index = next_index
            continue
        assembled.append((index + 1, line))
        index += 1
    return assembled


def _assemble_structure_rows(
    rows: tuple[StructureRow, ...],
    *,
    source_text: str | None = None,
) -> list[StructureRow]:
    """Assemble geometry rows into logical rows without changing row identity.

    A trailing printed anchor on a wrapped continuation is not a new row. A
    different anchor starts a new candidate row, while page and heading rows
    remain separate structure context. The first row retains the anchor and
    source offset; only its label geometry is widened by the continuation.
    """
    assembled: list[StructureRow] = []
    current: StructureRow | None = None
    repeated_anchor = False
    for index, row in enumerate(rows):
        if current is None:
            if row.line_anchor:
                current = row
                repeated_anchor = False
            else:
                assembled.append(row)
            continue

        next_row = rows[index + 1] if index + 1 < len(rows) else None
        source_gap_boundary = False
        sibling_boundary = _is_split_sibling_boundary(row, next_row, current)
        if sibling_boundary:
            source_gap_boundary = True
        elif not (
            current.line_anchor
            and (
                row.line_anchor == current.line_anchor
                or (row.line_anchor is None and repeated_anchor)
            )
        ):
            source_gap_boundary = _structure_row_gap_is_boundary(
                current,
                row,
                source_text=source_text,
            )
        if (
            _structure_row_is_boundary(row, current)
            or _is_split_form_footer(row, next_row)
            or source_gap_boundary
            or (
                row.line_anchor and row.line_anchor != current.line_anchor
            )
        ):
            assembled.append(current)
            current = row if row.line_anchor else None
            repeated_anchor = False
            if current is None:
                assembled.append(row)
            continue

        if row.line_anchor and row.line_anchor == current.line_anchor:
            repeated_anchor = True
        current = _join_structure_rows(current, row)

    if current is not None:
        assembled.append(current)
    return assembled


def _structure_row_gap_is_boundary(
    current: StructureRow,
    next_row: StructureRow,
    *,
    source_text: str | None,
) -> bool:
    """Return whether a skipped source row separates two geometry rows."""
    if not source_text or next_row.text_offset <= current.text_offset:
        return False
    source_lines = source_text[current.text_offset : next_row.text_offset].splitlines()
    for line in source_lines[1:]:
        stripped = line.strip()
        if not stripped or _is_cosmetic_source_line(stripped):
            return True
        if PAGE_RE.match(stripped) or stripped.startswith("Header:"):
            return True
    return False


def _structure_row_is_boundary(row: StructureRow, current: StructureRow) -> bool:
    """Return whether a geometry row ends the logical row currently open."""
    if row.page != current.page:
        return True
    text = row.text.strip()
    if not text or PAGE_RE.match(text) or text.startswith("Header:"):
        return True
    lowered = text.lower()
    if lowered.startswith("form ") and "page" in lowered:
        return True
    if re.match(r"^[0-9]+\s+form\s+\([0-9]{4}\)", lowered):
        return True
    return lowered.startswith(
        (
            "part ",
            "schedule ",
            "section ",
            "complete part ",
            "for paperwork reduction",
            "for disclosure",
            "to claim the child and dependent care credit",
            "credits",
        )
    )


def _is_split_form_footer(row: StructureRow, next_row: StructureRow | None) -> bool:
    """Recognize a footer split into a catalog number and ``Form (year)``."""
    if row.line_anchor or next_row is None or next_row.line_anchor:
        return False
    return bool(
        row.text.strip().isdigit()
        and re.match(r"^form\s+\([0-9]{4}\)", next_row.text.strip().lower())
    )


def _is_split_sibling_boundary(
    row: StructureRow,
    next_row: StructureRow | None,
    current: StructureRow,
) -> bool:
    """Keep a split sibling label from joining its preceding repeated anchor."""
    if row.line_anchor or next_row is None or not next_row.line_anchor or not current.line_anchor:
        return False
    match = re.match(r"^(?P<suffix>[a-z])(?:\s|$)", row.text.strip(), re.IGNORECASE)
    if not match:
        return False
    base = "".join(character for character in current.line_anchor if character.isdigit())
    return next_row.line_anchor.lower() == f"{base}{match.group('suffix').lower()}"


def _join_structure_rows(first: StructureRow, continuation: StructureRow) -> StructureRow:
    """Return one geometry row with source-ordered continuation text."""
    widget_names = tuple(dict.fromkeys((*first.widget_names, *continuation.widget_names)))
    return StructureRow(
        page=first.page,
        text=" ".join(part.text.strip() for part in (first, continuation) if part.text.strip()),
        x0=min(first.x0, continuation.x0),
        y0=min(first.y0, continuation.y0),
        x1=max(first.x1, continuation.x1),
        y1=max(first.y1, continuation.y1),
        text_offset=first.text_offset,
        line_anchor=first.line_anchor,
        printed_anchor=first.printed_anchor,
        widget_names=widget_names,
    )


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


def join_adjacent_source_spans(
    spans: list[CandidateSpan],
    *,
    source_text: str,
) -> list[CandidateSpan]:
    """Add joined source spans when stored offsets prove adjacency.

    The original per-line spans are retained. A joined span is derived only
    when one source range follows another with whitespace-only text between
    them. Text similarity is never used to create a join.
    """
    result: list[CandidateSpan] = []
    source_spans = [
        span for span in spans
        if span.relationship == "source" and not span.joined_from
    ]
    for first, following in zip(source_spans, source_spans[1:]):
        if len(first.source_ranges) == 1 and len(following.source_ranges) == 1:
            previous_end = int(first.source_ranges[0]["end"])
            following_start = int(following.source_ranges[0]["start"])
        else:
            continue
        if (
            following.document_id != first.document_id
            or following_start < previous_end
            or source_text[previous_end:following_start].strip()
        ):
            continue
        group = [first, following]
        if len(group) > 1:
            start = int(group[0].source_ranges[0]["start"])
            end = int(group[-1].source_ranges[0]["end"])
            result.append(
                CandidateSpan(
                    span_id=f"{group[0].span_id}_through_{group[-1].span_id.rsplit('_', 1)[-1]}",
                    document_id=first.document_id,
                    relationship="source",
                    locator=f"{group[0].locator} through {group[-1].locator}",
                    text=source_text[start:end],
                    evidence_text=normalize_evidence_text(source_text[start:end]),
                    owner_document_id=first.owner_document_id,
                    owner_lines=first.owner_lines,
                    section_id=first.section_id,
                    findings=tuple(item for span in group for item in span.findings),
                    extent=dict(first.extent),
                    source_ranges=({"start": start, "end": end},),
                    joined_from=tuple(span.span_id for span in group),
                )
            )
    return result


def build_candidate_spans(document: SourceDocumentInput) -> list[CandidateSpan]:
    """Segment form and bundled sources into verbatim candidate spans.

    Instruction spans are projections of the deterministic
    ``instruction_sections`` frame.  The raw-line fallback is retained only
    for legacy synthetic inputs that contain no line heading at all; it cannot
    create an instruction owner and therefore fails closed for the join.
    """
    spans: list[CandidateSpan] = []
    source_spans = _spans_for_text(document.document_id, "source", document.text)
    spans.extend(source_spans)
    spans.extend(join_adjacent_source_spans(source_spans, source_text=document.text))
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
    if span.evidence_text is not None:
        data["evidence_text"] = span.evidence_text
    if span.owner_document_id:
        data["owner_document_id"] = span.owner_document_id
    if span.owner_lines:
        data["owner_lines"] = list(span.owner_lines)
    if span.section_id:
        data["section_id"] = span.section_id
    if span.source_ranges:
        data["ranges"] = [dict(item) for item in span.source_ranges]
    if span.joined_from:
        data["joined_from"] = list(span.joined_from)
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
        return _spans_for_instruction_frame(frame, source_text=source.text)
    return _spans_for_text(source.document_id, source.relationship, source.text)


def _spans_for_instruction_frame(
    frame: InstructionSectionsFrame,
    *,
    source_text: str | None = None,
) -> list[CandidateSpan]:
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
                evidence_text=normalize_evidence_text(section.text),
                owner_document_id=section.document_id,
                owner_lines=section.line_tokens,
                section_id=section.section_id,
                source_ranges=(
                    {
                        "start": section.locator.start_offset,
                        "end": section.locator.end_offset,
                    },
                )
                if source_text is not None
                else (),
            )
        )
    return spans


def _spans_for_text(document_id: str, relationship: str, text: str) -> list[CandidateSpan]:
    spans: list[CandidateSpan] = []
    source_index = SourceTextIndex(text)
    cursor = 0
    page = 1
    index = 1
    source_lines = _assembled_legacy_lines(text) if relationship == "source" else [
        (line_number, raw_line.strip())
        for line_number, raw_line in enumerate(text.splitlines(), 1)
    ]
    for line_number, line in source_lines:
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
                evidence_text=normalize_evidence_text(line),
                source_ranges=source_index.ranges_for_quote(
                    line,
                    start=cursor,
                )
                or (),
            )
        )
        if spans[-1].source_ranges:
            cursor = spans[-1].source_ranges[-1]["end"]
        index += 1
    return spans


def _assembled_source_text(
    document: SourceDocumentInput,
    *,
    start_line: int,
    anchor: str,
) -> str:
    """Return one source row assembled from its physical text lines.

    The corrected form text is intentionally physical-line based. The separate
    anchor index tells us which following lines carry the same printed row; a
    different anchor, blank, page, or heading ends the row. This keeps assembly
    deterministic and prevents a continuation's trailing reference from
    becoming a new identity.
    """
    lines = document.text.splitlines()
    if start_line < 1 or start_line > len(lines):
        return ""
    geometry_text = _geometry_assembled_source_text(document, start_line=start_line, anchor=anchor)
    if geometry_text:
        return geometry_text
    anchor_lines = _source_anchor_lines(document)
    parts = [lines[start_line - 1].strip()]
    normalized_anchor = anchor.lower()
    for line_number in range(start_line + 1, len(lines) + 1):
        line = lines[line_number - 1].strip()
        if not line or _source_line_is_boundary(line):
            break
        if _is_cosmetic_source_line(line):
            break
        next_anchors = anchor_lines.get(line_number, set())
        if next_anchors and normalized_anchor not in next_anchors:
            break
        parts.append(line)
    return " ".join(part for part in parts if part)


def _geometry_assembled_source_text(
    document: SourceDocumentInput,
    *,
    start_line: int,
    anchor: str,
) -> str | None:
    """Return the assembled geometry row that owns a source line, if present."""
    if document.fields_path is None:
        return None

    result = _geometry_assembled_source_row(
        document,
        start_line=start_line,
        anchor=anchor,
    )
    return result[0].text if result is not None else None


def _geometry_assembled_source_row(
    document: SourceDocumentInput,
    *,
    start_line: int,
    anchor: str,
) -> tuple[StructureRow, tuple[StructureFinding, ...]] | None:
    """Return one geometry row and fail-closed packet findings, if any."""
    if document.fields_path is None:
        return None
    from tax_graph.extract.structure import build_structure_model

    structure = build_structure_model(document)
    if structure is None:
        return None
    assembled = _assemble_structure_rows(structure.rows, source_text=document.text)
    for row in assembled:
        if row.line_anchor != anchor:
            continue
        if _text_line_number(document.text, row.text_offset) == start_line:
            return row, _row_packet_findings(
                row,
                structure.rows,
                source_text=document.text,
            )
    return None


def _row_packet_findings(
    row: StructureRow,
    raw_rows: tuple[StructureRow, ...] | list[StructureRow],
    *,
    source_text: str,
) -> tuple[StructureFinding, ...]:
    """Find substantive geometry continuations lost after a repeated anchor.

    A repeated printed anchor is a known AcroForm interruption pattern. The
    geometry pass can see words after the marker while source-line assembly may
    stop at a dot-leader or field-marker line. A packet is complete only when
    those continuation words are present in the assembled row. The check is
    deliberately scoped to a repeated anchor so adjacent form columns and page
    furniture are not mistaken for one logical printed row.
    """
    candidates = [
        item
        for item in raw_rows
        if item.page == row.page and item.text_offset >= row.text_offset
    ]
    window: list[StructureRow] = []
    for item in candidates:
        if item.line_anchor and item.line_anchor != row.line_anchor:
            break
        window.append(item)
    same_anchor = [item for item in window if item.line_anchor == row.line_anchor]
    if len(same_anchor) < 2:
        return ()
    last_same_index = max(
        index for index, item in enumerate(window)
        if item.line_anchor == row.line_anchor
    )
    continuation = [
        item
        for item in _substantive_continuation_rows(
            window[last_same_index + 1 :],
            current=row,
        )
    ]
    if not continuation:
        return ()
    missing = _content_tokens(" ".join(item.text for item in continuation)) - _content_tokens(row.text)
    if not missing:
        return ()
    source_end = len(source_text)
    next_anchor = next(
        (
            item
            for item in candidates
            if item.text_offset > row.text_offset
            and item.line_anchor
            and item.line_anchor != row.line_anchor
        ),
        None,
    )
    if next_anchor is not None:
        source_end = next_anchor.text_offset
    interruption = ["repeated printed anchor"]
    source_window = source_text[same_anchor[-1].text_offset : source_end]
    if re.search(r"(?:^|\n)\s*(?:\.\s*){2,}(?:\n|$)", source_window):
        interruption.append("dot leaders")
    missing_text = ", ".join(sorted(missing)[:12])
    return (
        StructureFinding(
            code="row_packet_incomplete",
            page=row.page,
            detail=(
                f"line {row.line_anchor} has substantive geometry text after "
                f"{', '.join(interruption)} that is absent from the packet: {missing_text}"
            ),
            row_text=row.text,
        ),
    )


def _content_tokens(value: str) -> Counter[str]:
    """Return punctuation-insensitive content tokens for completeness checks."""
    normalized = normalize_punctuation(str(value or "")).lower()
    return Counter(re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*|\.[0-9]+", normalized))


def _substantive_continuation_rows(
    rows: list[StructureRow],
    *,
    current: StructureRow,
) -> list[StructureRow]:
    """Keep only continuation rows that can carry printed row content.

    Repeated-anchor packets can run into a following section or the form
    footer. Those rows are visible to geometry but are not continuation text
    for the current printed line. Stop at an explicit section boundary, and
    ignore only page furniture whose complete row shape is identifiable:
    bare numbers, page labels, catalog identifiers, and the ``Form (year)``
    footer with its creation date. Numeric bands such as ``17,000-19,000``
    remain substantive because they are not bare identifiers.
    """
    substantive: list[StructureRow] = []
    for item in rows:
        if not item.text:
            continue
        if _structure_row_is_boundary(item, current):
            break
        if _is_form_furniture_row(item.text):
            continue
        substantive.append(item)
    return substantive


def _is_form_furniture_row(text: str) -> bool:
    """Return whether a geometry row is identifiable page furniture."""
    normalized = " ".join(normalize_punctuation(str(text or "")).split()).lower()
    if not normalized:
        return True
    if re.fullmatch(r"\d{1,4}", normalized):
        return True
    if re.fullmatch(r"page(?:\s+\d{1,4})?", normalized):
        return True
    if re.fullmatch(r"(?:form\s+)?\d+\s+form\s*\(\d{4}\)(?:\s+\d+)?", normalized):
        return True
    if re.fullmatch(r"form\s+\d+(?:\s+\(\d{4}\))?(?:\s+\d+)?", normalized):
        return True
    if re.fullmatch(r"(?:\d+\s+)?form\s*\(\d{4}\)", normalized):
        return True
    if re.fullmatch(r"(?:\d+\s+)?form\s*\(\d{4}\)\s+created\s+\d{1,2}/\d{1,2}/\d{2,4}", normalized):
        return True
    if re.fullmatch(r"cat\.?\s+no\.?\s+[a-z0-9]+(?:\s+[a-z0-9]+)*", normalized):
        return True
    return False


def _source_anchor_lines(document: SourceDocumentInput) -> dict[int, set[str]]:
    """Index printed anchors by physical source-text line number."""
    lines = document.text.splitlines()
    by_line: dict[int, set[str]] = {}
    records = (document.fields or {}).get("line_anchors", [])
    if isinstance(records, list):
        for record in records:
            if not isinstance(record, dict):
                continue
            offset = record.get("text_offset")
            if not isinstance(offset, int) or not 0 <= offset < len(document.text):
                continue
            line_number = _text_line_number(document.text, offset)
            anchor = str(record.get("anchor", "")).strip().lower()
            if anchor:
                by_line.setdefault(line_number, set()).add(anchor)
    if by_line:
        return by_line
    for line_number, line in enumerate(lines, 1):
        match = LINE_RE.match(line.strip())
        if match:
            by_line.setdefault(line_number, set()).add(match.group(1).lower())
    return by_line


def _text_line_number(text: str, offset: int) -> int:
    """Return the one-based physical line containing a text offset."""
    prefix = text[:offset]
    line_number = len(prefix.splitlines())
    if not prefix or prefix[-1] in "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029":
        line_number += 1
    return line_number


def _source_line_is_boundary(line: str) -> bool:
    """Return whether a physical source line cannot continue a form row."""
    if PAGE_RE.match(line) or line.startswith("Header:"):
        return True
    lowered = line.lower()
    if lowered.startswith("form ") and "page" in lowered:
        return True
    return lowered.startswith(
        (
            "part ",
            "schedule ",
            "section ",
            "complete part ",
            "for paperwork reduction",
            "for disclosure",
            "credits",
        )
    )


def _is_cosmetic_source_line(line: str) -> bool:
    """Return whether a source line is a dot leader, not row content."""
    compact = "".join(line.split())
    return bool(compact) and all(char in "._" for char in compact)


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
    qualified_dividend_worksheet = "qualified dividends and capital gain tax worksheet" in lowered
    if (
        ("schedule d" in lowered and not qualified_dividend_worksheet)
        or anchor in {"3", "10"} and "schedule d" in context and not qualified_dividend_worksheet
    ):
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
    if preferred_section:
        for node in nodes:
            if not _matches_preferred_section(node, preferred_section):
                continue
            found = _find_totals_outline(node.children, preferred_section=None)
            if found:
                return found
        return None
    for node in nodes:
        if node.kind in {"totals", "outbound_flow_cue"} and (not node.columns or "h" in node.columns):
            return node.outline_id
        found = _find_totals_outline(node.children, preferred_section=None)
        if found:
            return found
    return None


def _matches_preferred_section(node: OutlineNode, preferred_section: str) -> bool:
    """Match legacy and geometry section ids for an outbound-flow half."""
    token = str(preferred_section).lower()
    outline_id = str(node.outline_id).lower()
    label = " ".join(str(node.label).lower().split())
    return outline_id == token or re.search(
        rf"(^|_){re.escape(token)}(?:_|$)",
        outline_id,
    ) is not None or re.search(
        rf"\bpart\s+{re.escape(token.removeprefix('part_'))}\b",
        label,
    ) is not None


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
