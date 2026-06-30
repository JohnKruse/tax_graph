"""Outline-first extraction orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tax_graph.config import get_config_value
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
)


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
        plan = extract_formula_plan(
            outline_node=outline_node,
            spans=spans,
            client=client,
            config=config,
            root=root,
        )
        batch = assemble_formula_plan(document, outline_node, plan, spans, model=str(model), root=root)
        objects.extend(batch.objects)
    objects.extend(_line_cue_objects(document, outline.children, spans, model=model))

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
        span = _span_for_line(node, spans)
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
            "node_type": "form_line",
            "value_type": "currency",
        }
        if citation_refs:
            data["citation_refs"] = citation_refs
        objects.append(DraftObject("nodes", data, source_span, model, 1.0))
    return objects


def _line_cue_nodes(nodes: list[OutlineNode]) -> list[OutlineNode]:
    selected: list[OutlineNode] = []
    for node in nodes:
        if node.kind == "outbound_flow_cue" and node.line_anchor:
            selected.append(node)
        selected.extend(_line_cue_nodes(node.children))
    return selected


def _span_for_line(node: OutlineNode, spans: list[CandidateSpan]) -> CandidateSpan | None:
    if not node.line_anchor:
        return None
    prefix = f"- {node.line_anchor}:"
    for span in spans:
        if span.relationship == "source" and span.text.startswith(prefix):
            return span
    return None


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
