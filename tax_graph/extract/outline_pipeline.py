"""Outline-first extraction orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tax_graph.config import get_config_value
from tax_graph.documents import document_class_for
from tax_graph.extract.assembly import assemble_formula_plan
from tax_graph.extract.outline_checks import run_outline_artifact_checks
from tax_graph.extract.llm_client import LlmClient
from tax_graph.extract.micro import extract_formula_plan
from tax_graph.extract.models import DraftObject, ExtractionBatch, SourceDocumentInput
from tax_graph.extract.outline import (
    CandidateSpan,
    OutlineNode,
    build_candidate_spans,
    build_outbound_flows,
    build_outline_tree,
    infer_value_type,
    node_type_for_outline,
    _line_anchor_variants,
)
from tax_graph.extract.tables import assemble_table_subunits


class SpanResolutionError(ValueError):
    """Raised when a printed line cannot be anchored to source evidence."""


def generate_outline_first_drafts(
    document: SourceDocumentInput,
    *,
    client: LlmClient,
    config: dict[str, Any] | None = None,
    root: str | Path | None = None,
) -> ExtractionBatch:
    """Generate draft objects by walking deterministic outline nodes."""
    outline = build_outline_tree(document)
    spans = build_candidate_spans(document)
    flows = build_outbound_flows(document, outline=outline, spans=spans)
    run_outline_artifact_checks(document, outline, spans, flows).raise_for_issues()
    model = _micro_model(config or {})

    objects: list[DraftObject] = []
    for outline_node in _formula_outline_nodes(outline.children):
        node_spans = _spans_for_outline_node(
            document,
            outline_node,
            spans,
            document_id=document.document_id,
        )
        plan = _deterministic_schedule_d_formula_plan(document, outline_node, node_spans)
        formula_model = str(model)
        if plan is None:
            plan = extract_formula_plan(
                outline_node=outline_node,
                spans=node_spans,
                client=client,
                config=config,
                root=root,
            )
        else:
            formula_model = "deterministic-schedule-d-formula"
        batch = assemble_formula_plan(document, outline_node, plan, node_spans, model=formula_model, root=root)
        objects.extend(batch.objects)
    objects.extend(assemble_table_subunits(document, outline, objects, model="deterministic-table-detector"))
    objects.extend(_schedule_d_band_tables(document, outline.children, model="deterministic-schedule-d-band-detector"))
    objects.extend(_schedule_d_not_modeled_document(document, outline.children, model="deterministic-schedule-d-scope"))
    objects.extend(_outline_structure_objects(document, outline.children, spans, model=model))
    objects.extend(_write_in_amount_nodes(document, outline.children, spans, objects=objects, model=model))
    objects.extend(_simple_line_objects(document, outline.children, spans, objects=objects, model=model))
    objects.extend(_line_cue_objects(document, outline.children, spans, model=model))
    objects.extend(_generic_not_modeled_document(document, outline.children, objects=objects, model=model))

    return ExtractionBatch(document_id=document.document_id, year=document.year, objects=_dedupe_objects(objects))


def _formula_outline_nodes(nodes: list[OutlineNode]) -> list[OutlineNode]:
    selected: list[OutlineNode] = []
    for node in nodes:
        if _is_formula_node(node):
            selected.append(node)
        selected.extend(_formula_outline_nodes(node.children))
    return selected


def _is_formula_node(node: OutlineNode) -> bool:
    if node.kind == "transaction_table" and "h" in node.columns:
        return True
    return node.kind == "totals" and bool(node.columns)


def _deterministic_schedule_d_formula_plan(
    document: SourceDocumentInput,
    node: OutlineNode,
    spans: list[CandidateSpan],
) -> dict[str, Any] | None:
    """Return the fixed Schedule D row-band column h formula when applicable."""
    if not document.document_id.startswith("schedule_d_"):
        return None
    if node.kind != "transaction_table" or not node.line_anchor:
        return None
    if node.line_anchor not in {"1b", "2", "3", "8b", "9", "10"}:
        return None
    if not {"d", "e", "g", "h"}.issubset(set(node.columns)):
        return None
    span_id = spans[0].span_id if spans else ""
    citation_span_ids = [span_id] if span_id else []
    return {
        "operation_plan": [
            {
                "output": "column_d_minus_e",
                "operation": "SUBTRACT",
                "inputs": [
                    {"name": "column_d", "role": "minuend"},
                    {"name": "column_e", "role": "subtrahend"},
                ],
                "citation_span_ids": citation_span_ids,
            },
            {
                "output": "column_h",
                "operation": "SUM",
                "inputs": [
                    {"name": "column_d_minus_e", "role": "addend"},
                    {"name": "column_g", "role": "addend"},
                ],
                "citation_span_ids": citation_span_ids,
            },
        ]
    }


def _spans_for_outline_node(
    document: SourceDocumentInput,
    node: OutlineNode,
    spans: list[CandidateSpan],
    *,
    document_id: str = "",
) -> list[CandidateSpan]:
    """Select a small evidence packet for one micro-extraction prompt."""
    selected: list[CandidateSpan] = []
    if node.line_anchor:
        line_phrase = f"line {node.line_anchor}"
        instruction_hits: list[CandidateSpan] = []
        source_span = _span_for_line(document, node, spans)
        for span in spans:
            lowered = span.text.lower()
            if span is source_span:
                selected.append(span)
            elif line_phrase in lowered and _direct_line_evidence(span.text, node.line_anchor):
                instruction_hits.append(span)
        selected.extend(instruction_hits[:3])
    if node.columns:
        column_terms = [f"({column})" for column in node.columns]
        column_hits: list[CandidateSpan] = []
        for span in spans:
            if span in selected:
                continue
            lowered = span.text.lower()
            if "column" in lowered and any(term in lowered for term in column_terms):
                column_hits.append(span)
        column_limit = 4 if document_id.startswith("schedule_d_") else 8
        selected.extend(column_hits[:column_limit])
    if not selected:
        selected = spans[:20]
    limit = 12 if document_id.startswith("schedule_d_") else 80
    return selected[:limit]


def _direct_line_evidence(text: str, anchor: str) -> bool:
    """Return true when an instruction span appears to discuss the exact line."""
    lowered = text.lower()
    line_phrase = f"line {anchor}".lower()
    if line_phrase not in lowered:
        return False
    direct_tokens = ("enter", "report", "include", "combine", "total", "add", "subtract")
    return any(token in lowered for token in direct_tokens)


def _dedupe_objects(objects: list[DraftObject]) -> list[DraftObject]:
    seen: set[tuple[str, str]] = set()
    deduped: list[DraftObject] = []
    for obj in objects:
        identity = (obj.kind, obj.object_id)
        if identity in seen:
            continue
        seen.add(identity)
        deduped.append(obj)
    return deduped


def _line_cue_objects(
    document: SourceDocumentInput,
    nodes: list[OutlineNode],
    spans: list[CandidateSpan],
    *,
    model: str,
) -> list[DraftObject]:
    objects: list[DraftObject] = []
    for node in _line_cue_nodes(nodes):
        span = _span_for_line(document, node, spans)
        citation_refs: list[str] = []
        source_span = ""
        if span:
            citation_id = f"cite_{_slug(span.span_id)}"
            citation_refs.append(citation_id)
            source_span = span.text
            objects.append(
                DraftObject(
                    "citations",
                    {
                        "citation_id": citation_id,
                        "document_id": span.document_id,
                        "locator": span.locator,
                        "quoted_text": span.text,
                    },
                    span.text,
                    model,
                    1.0,
                )
            )
        data = {
            "node_id": _slug(f"{document.document_id}_{node.outline_id}"),
            "document_id": document.document_id,
            "label": f"Line {node.line_anchor}: {node.label}" if node.line_anchor else node.label,
            "node_type": node_type_for_outline(node),
            "value_type": infer_value_type(node, document=document),
        }
        if citation_refs:
            data["citation_refs"] = citation_refs
        objects.append(DraftObject("nodes", data, source_span, model, 1.0))
    return objects


def _simple_line_objects(
    document: SourceDocumentInput,
    nodes: list[OutlineNode],
    spans: list[CandidateSpan],
    *,
    objects: list[DraftObject],
    model: str,
) -> list[DraftObject]:
    generated: list[DraftObject] = []
    for node in _flatten_nodes(nodes):
        if not _is_simple_line_node(node):
            continue
        if any(_object_mentions_line(obj, str(node.line_anchor or "")) for obj in objects + generated if obj.kind == "nodes"):
            continue
        if _skip_simple_line(node):
            continue
        span = _span_for_line(document, node, spans)
        citation_refs: list[str] = []
        source_span = ""
        if span:
            citation_id = f"cite_{_slug(span.span_id)}"
            citation_refs.append(citation_id)
            source_span = span.text
            generated.append(
                DraftObject(
                    "citations",
                    {
                        "citation_id": citation_id,
                        "document_id": span.document_id,
                        "locator": span.locator,
                        "quoted_text": span.text,
                    },
                    span.text,
                    model,
                    1.0,
                )
            )
        data = {
            "node_id": _slug(f"{document.document_id}_{node.outline_id}"),
            "document_id": document.document_id,
            "label": f"Line {node.line_anchor}: {node.label}" if node.line_anchor else node.label,
            "node_type": node_type_for_outline(node),
            "value_type": infer_value_type(node, document=document),
        }
        if citation_refs:
            data["citation_refs"] = citation_refs
        generated.append(DraftObject("nodes", data, source_span, model, 1.0))
    return generated


def _write_in_amount_nodes(
    document: SourceDocumentInput,
    nodes: list[OutlineNode],
    spans: list[CandidateSpan],
    *,
    objects: list[DraftObject],
    model: str,
) -> list[DraftObject]:
    flattened = _flatten_nodes(nodes)
    generated: list[DraftObject] = []
    for node in flattened:
        if not _is_write_in_amount_line(node, flattened):
            continue
        span = _span_for_line(document, node, spans)
        citation_refs: list[str] = []
        source_span = ""
        if span:
            citation_id = f"cite_{_slug(span.span_id)}"
            citation_refs.append(citation_id)
            source_span = span.text
            generated.append(
                DraftObject(
                    "citations",
                    {
                        "citation_id": citation_id,
                        "document_id": span.document_id,
                        "locator": span.locator,
                        "quoted_text": span.text,
                    },
                    span.text,
                    model,
                    1.0,
                )
            )
        line_anchor = str(node.line_anchor or "")
        amount_node = {
            "node_id": _slug(f"{document.document_id}_{node.outline_id}_amount"),
            "document_id": document.document_id,
            "label": f"Line {line_anchor}: {node.label} amount",
            "node_type": "form_line",
            "value_type": "currency",
        }
        description_node = {
            "node_id": _slug(f"{document.document_id}_{node.outline_id}_description"),
            "document_id": document.document_id,
            "label": f"Line {line_anchor}: {node.label} description",
            "node_type": "form_line",
            "value_type": "string",
        }
        if citation_refs:
            amount_node["citation_refs"] = citation_refs
            description_node["citation_refs"] = citation_refs
        generated.append(DraftObject("nodes", amount_node, source_span, model, 1.0))
        generated.append(DraftObject("nodes", description_node, source_span, model, 1.0))
    return generated


def _is_write_in_amount_line(node: OutlineNode, nodes: list[OutlineNode]) -> bool:
    if node.kind != "line" or not node.line_anchor:
        return False
    if not _addressable_anchor(str(node.line_anchor)):
        return False
    if "list type and amount" not in node.label.lower():
        return False
    anchor = str(node.line_anchor).lower()
    return any(
        _totals_rolls_through_anchor(candidate, anchor)
        for candidate in nodes
        if candidate.kind in {"line", "totals"}
    )


def _totals_rolls_through_anchor(node: OutlineNode, anchor: str) -> bool:
    label = node.label.lower()
    return f"through {anchor}" in label


def _is_simple_line_node(node: OutlineNode) -> bool:
    return node.kind in {"line", "totals"} and bool(node.line_anchor) and _addressable_anchor(str(node.line_anchor))


def _skip_simple_line(node: OutlineNode) -> bool:
    lowered = node.label.lower()
    if "list type and amount" in lowered:
        return True
    return False


def _simple_line_value_type(node: OutlineNode) -> str:
    """Backward-compatible wrapper for callers of the old scalar helper."""
    return infer_value_type(node)


def _outline_structure_objects(
    document: SourceDocumentInput,
    nodes: list[OutlineNode],
    spans: list[CandidateSpan],
    *,
    model: str,
) -> list[DraftObject]:
    """Emit non-fillable concepts for outline sections and printed headings."""
    generated: list[DraftObject] = []
    for node in _flatten_nodes(nodes):
        if node.kind not in {"section", "heading"}:
            continue
        span = _span_for_line(document, node, spans) if node.line_anchor else None
        citation_refs: list[str] = []
        source_span = ""
        if span:
            citation_id = f"cite_{_slug(span.span_id)}"
            citation_refs.append(citation_id)
            source_span = span.text
            generated.append(
                DraftObject(
                    "citations",
                    {
                        "citation_id": citation_id,
                        "document_id": span.document_id,
                        "locator": span.locator,
                        "quoted_text": span.text,
                    },
                    span.text,
                    model,
                    1.0,
                )
            )
        data = {
            "node_id": _slug(f"{document.document_id}_{node.outline_id}"),
            "document_id": document.document_id,
            "label": f"Line {node.line_anchor}: {node.label}" if node.line_anchor else node.label,
            "node_type": node_type_for_outline(node),
            "value_type": infer_value_type(node, document=document),
        }
        if citation_refs:
            data["citation_refs"] = citation_refs
        generated.append(DraftObject("nodes", data, source_span, model, 1.0))
    return generated


def _line_cue_nodes(nodes: list[OutlineNode]) -> list[OutlineNode]:
    selected: list[OutlineNode] = []
    for node in nodes:
        if node.kind == "outbound_flow_cue" and node.line_anchor:
            selected.append(node)
        selected.extend(_line_cue_nodes(node.children))
    return selected


def _schedule_d_band_tables(
    document: SourceDocumentInput,
    nodes: list[OutlineNode],
    *,
    model: str,
) -> list[DraftObject]:
    if not document.document_id.startswith("schedule_d_"):
        return []
    groups = [
        ("part_i", ["1b", "2", "3"]),
        ("part_ii", ["8b", "9", "10"]),
    ]
    by_section = {node.outline_id: node for node in nodes if node.kind == "section"}
    objects: list[DraftObject] = []
    for section_id, anchors in groups:
        section = by_section.get(section_id)
        if section is None:
            continue
        children = {child.line_anchor: child for child in section.children}
        if not all(anchor in children for anchor in anchors):
            continue
        first = children[anchors[0]]
        columns = [column for column in ["d", "e", "g", "h"] if column in first.columns]
        if len(columns) < 4:
            continue
        table_id = _slug(f"{document.document_id}_{section_id}_lines_{anchors[0]}_{anchors[-1]}")
        objects.append(
            DraftObject(
                "tables",
                {
                    "table_id": table_id,
                    "document_id": document.document_id,
                    "line_anchor": f"{section.label}, lines {anchors[0]}-{anchors[-1]}",
                    "description": "Schedule D row-band grouping for Form 8949 totals.",
                    "columns": [
                        {
                            "column_id": column,
                            "label": f"Column ({column})",
                            "kind": "computed" if column == "h" else "input",
                            "template_node": _slug(
                                f"{document.document_id}_{first.outline_id}_column_{column}"
                            ),
                        }
                        for column in columns
                    ],
                    "totals": [
                        {
                            "column_id": "h",
                            "total_node": _slug(
                                f"{document.document_id}_{children[anchors[-1]].outline_id}_column_h"
                            ),
                        }
                    ],
                },
                first.label,
                model,
                1.0,
            )
        )
    return objects


def _schedule_d_not_modeled_document(
    document: SourceDocumentInput,
    nodes: list[OutlineNode],
    *,
    model: str,
) -> list[DraftObject]:
    if not document.document_id.startswith("schedule_d_"):
        return []
    present_anchors = {node.line_anchor for node in _flatten_nodes(nodes) if node.line_anchor}
    deferred_lines = [
        ("1a", "summary transactions not sourced from Form 8949 totals in M9 Step 2"),
        ("4", "pass-through short-term gain or loss inputs deferred"),
        ("5", "pass-through short-term gain or loss inputs deferred"),
        ("6", "short-term capital loss carryover worksheet deferred"),
        ("7", "Part I subtotal modeled after promotion and link realization"),
        ("8a", "summary transactions not sourced from Form 8949 totals in M9 Step 2"),
        ("11", "pass-through long-term gain or loss inputs deferred"),
        ("12", "pass-through long-term gain or loss inputs deferred"),
        ("13", "capital gain distributions input deferred"),
        ("14", "long-term capital loss carryover worksheet deferred"),
        ("15", "Part II subtotal modeled after promotion and link realization"),
        ("16", "net capital gain or loss modeled in M9 Step 3"),
        ("17", "line 15 and line 16 decision cue modeled in M9 Step 3"),
        ("18", "28 percent rate gain worksheet deferred"),
        ("19", "unrecaptured Section 1250 gain worksheet deferred"),
        ("20", "qualified dividends and capital gain tax worksheet deferred"),
        ("21", "capital loss limit branch modeled in M9 Step 3"),
        ("22", "line 18 and line 19 decision cue deferred"),
    ]
    records = [
        {
            "field_id": f"schedule_d_{_slug(anchor)}_not_modeled",
            "line_anchor": anchor,
            "reason": reason,
        }
        for anchor, reason in deferred_lines
        if anchor in present_anchors
    ]
    records.extend(
        [
            {
                "field_id": "schedule_d_name_field_not_modeled",
                "field_name_pattern": r"^topmostSubform\[0\]\.Page1\[0\]\.f1_1\[0\]$",
                "reason": "taxpayer identity field is outside the computation graph",
            },
            {
                "field_id": "schedule_d_ssn_field_not_modeled",
                "field_name_pattern": r"^topmostSubform\[0\]\.Page1\[0\]\.f1_2\[0\]$",
                "reason": "taxpayer identity field is outside the computation graph",
            },
            {
                "field_id": "schedule_d_status_checkbox_not_modeled",
                "field_name_pattern": r"^topmostSubform\[0\]\.Page1\[0\]\.c1_1\[[01]\]$",
                "reason": "form status checkbox is outside the computation graph",
            },
            {
                "field_id": "schedule_d_row_1a_table_not_modeled",
                "field_name_pattern": "Row1a",
                "reason": "line 1a table fields are deferred with summary transactions",
            },
            {
                "field_id": "schedule_d_row_8a_table_not_modeled",
                "field_name_pattern": "Row8a",
                "reason": "line 8a table fields are deferred with summary transactions",
            },
            {
                "field_id": "schedule_d_line_20_checkbox_not_modeled",
                "field_name_pattern": r"^topmostSubform\[0\]\.Page2\[0\]\.c2_2\[[01]\]$",
                "reason": "line 20 and line 22 worksheet decision fields are deferred",
            },
            {
                "field_id": "schedule_d_line_21_amount_not_modeled",
                "field_name_pattern": r"^topmostSubform\[0\]\.Page2\[0\]\.f2_4\[0\]$",
                "reason": "line 21 capital loss limit branch is modeled in M9 Step 3",
            },
            {
                "field_id": "schedule_d_line_22_checkbox_not_modeled",
                "field_name_pattern": r"^topmostSubform\[0\]\.Page2\[0\]\.c2_3\[[01]\]$",
                "reason": "line 22 worksheet decision fields are deferred",
            },
        ]
    )
    return [
        DraftObject(
            "documents",
            {
                "document_id": document.document_id,
                "title": "Schedule D (Form 1040)",
                "tax_year": int(document.year),
                "document_type": "schedule",
                "document_class": document_class_for(
                    document_id=document.document_id,
                    document_type="schedule",
                ),
                "source_url": document.url,
                "status": "partial",
                "not_modeled_fields": records,
            },
            "",
            model,
            1.0,
        )
    ]


def _generic_not_modeled_document(
    document: SourceDocumentInput,
    nodes: list[OutlineNode],
    *,
    objects: list[DraftObject],
    model: str,
) -> list[DraftObject]:
    if document.document_id.startswith("schedule_d_"):
        return []
    anchors = sorted(
        {
            node.line_anchor
            for node in _flatten_nodes(nodes)
            if node.line_anchor and _addressable_anchor(str(node.line_anchor))
        },
        key=_line_sort_key,
    )
    anchors.extend(
        anchor
        for anchor in sorted(_field_line_anchors(document), key=_line_sort_key)
        if anchor not in anchors
    )
    modeled = {
        anchor
        for anchor in anchors
        if any(_object_mentions_line(obj, anchor) for obj in objects if obj.kind == "nodes")
    }
    not_modeled_fields = [
        {
            "field_id": f"{document.document_id}_{_slug(anchor)}_not_modeled",
            "line_anchor": anchor,
            "reason": "line remains unmodeled in the M10 Step 4 batch draft",
        }
        for anchor in anchors
        if anchor not in modeled
    ]
    if not not_modeled_fields and any(obj.kind == "documents" for obj in objects):
        return []
    return [
        DraftObject(
            "documents",
            {
                "document_id": document.document_id,
                "title": _document_title(document),
                "tax_year": int(document.year),
                "document_type": document.kind,
                "document_class": document_class_for(
                    document_id=document.document_id,
                    document_type=document.kind,
                ),
                "source_url": document.url,
                "status": "partial",
                "not_modeled_fields": not_modeled_fields,
            },
            "",
            model,
            1.0,
        )
    ]


def _flatten_nodes(nodes: list[OutlineNode]) -> list[OutlineNode]:
    flattened: list[OutlineNode] = []
    for node in nodes:
        flattened.append(node)
        flattened.extend(_flatten_nodes(node.children))
    return flattened


def _field_line_anchors(document: SourceDocumentInput) -> set[str]:
    anchors: set[str] = set()
    for field in (document.fields or {}).get("fields", []) or []:
        anchor = str(field.get("line_anchor", "")).strip().lower()
        if anchor and _addressable_anchor(anchor):
            anchors.add(anchor)
    return anchors


def _object_mentions_line(obj: DraftObject, anchor: str) -> bool:
    normalized = anchor.lower().replace("-", "_")
    haystacks = [
        str(obj.data.get("node_id", "")).lower(),
        str(obj.data.get("label", "")).lower(),
        str(obj.data.get("description", "")).lower(),
    ]
    return any(f"line_{normalized}" in value or f"line {anchor}" in value for value in haystacks)


def _document_title(document: SourceDocumentInput) -> str:
    for line in document.text.splitlines():
        title = line.strip()
        if title and not title.startswith("# Page"):
            return title
    return document.document_id


def _line_sort_key(anchor: str) -> tuple[int, str]:
    digits = "".join(ch for ch in anchor if ch.isdigit())
    suffix = "".join(ch for ch in anchor if ch.isalpha())
    return (int(digits or "0"), suffix)


def _addressable_anchor(anchor: str) -> bool:
    return any(ch.isdigit() for ch in anchor)


def _span_for_line(
    document: SourceDocumentInput,
    node: OutlineNode,
    spans: list[CandidateSpan],
) -> CandidateSpan | None:
    """Resolve a line node through the rendered line-anchor index.

    The text layer is complete and intentionally has no synthetic line prefix.
    ``line_anchors`` is therefore the positional authority: its offset identifies
    the source-text line whose generated candidate span is the evidence packet.
    Missing or malformed index entries fail closed instead of returning an empty
    outline that looks like a successful extraction.
    """
    if not node.line_anchor:
        return None
    index = (document.fields or {}).get("line_anchors")
    if not isinstance(index, list):
        # A document may legitimately carry no anchor index at all - form_13614_c_2025 is
        # an intake questionnaire with 297 widgets and zero printed line numbers. That is a
        # coverage fact to report, not a reason to abort the batch. Fail-closed lives at the
        # DOCUMENT level (an empty outline is an error, see outline_checks), not here.
        return None

    normalized_anchor = node.line_anchor.lower()
    variants = _line_anchor_variants(node.line_anchor)
    exact_entries = [
        entry
        for entry in index
        if isinstance(entry, dict) and str(entry.get("anchor", "")).lower() == normalized_anchor
    ]
    matching_entries = exact_entries or [
        entry
        for entry in index
        if isinstance(entry, dict) and str(entry.get("anchor", "")).lower() in variants
    ]
    if not matching_entries:
        # An anchor the index does not carry is an unresolved line, reported through the
        # document-level completeness check rather than as a fatal error mid-batch.
        return None

    source_line_numbers = {
        _line_number_at_offset(document.text, entry.get("text_offset"))
        for entry in matching_entries
        if _valid_text_offset(document.text, entry.get("text_offset"))
    }
    for span in spans:
        if span.relationship != "source" or span.document_id != document.document_id:
            continue
        line_number = _locator_line_number(span.locator)
        if line_number in source_line_numbers:
            return span

    return None


def _valid_text_offset(text: str, value: Any) -> bool:
    return isinstance(value, int) and 0 <= value < len(text)


def _line_number_at_offset(text: str, offset: int) -> int:
    prefix = text[:offset]
    line_number = len(prefix.splitlines())
    if not prefix or prefix[-1] in "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029":
        line_number += 1
    return line_number


def _locator_line_number(locator: str) -> int | None:
    import re

    match = re.search(r"\bline\s+(\d+)\b", locator.lower())
    return int(match.group(1)) if match else None


def _micro_model(settings: dict[str, Any]) -> str:
    model = get_config_value(settings, "llm.micro_model")
    if model:
        return str(model)
    fallback = get_config_value(settings, "llm.model", "configured-llm")
    return str(fallback or "configured-llm")


def _slug(value: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "item"
