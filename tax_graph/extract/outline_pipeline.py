"""Outline-first extraction orchestration."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from tax_graph.config import get_config_value
from tax_graph.documents import document_class_for
from tax_graph.extract.assembly import FormulaAssemblyFinding, _resolve_source_line, assemble_formula_plan
from tax_graph.extract.background import extract_background_controls
from tax_graph.extract.outline_checks import run_outline_artifact_checks
from tax_graph.extract.llm_client import LlmClient, is_transient_transport_error, response_telemetry
from tax_graph.extract.micro import extract_formula_plan, extract_non_formula_source
from tax_graph.extract.models import DraftObject, ExtractionBatch, SourceDocumentInput
from tax_graph.extract.instruction_ownership import (
    instruction_line_owners,
    instruction_span_ids_for_line,
)
from tax_graph.extract.outline import (
    CandidateSpan,
    OutlineNode,
    build_candidate_spans,
    build_outbound_flows,
    build_instruction_sections_frame,
    build_outline_tree,
    infer_value_type,
    node_type_for_outline,
    _line_anchor_variants,
)
from tax_graph.extract.tables import assemble_table_subunits


class SpanResolutionError(ValueError):
    """Raised when a printed line cannot be anchored to source evidence."""


NON_FORMULA_REVIEW_DOCUMENTS = frozenset({
    "form_1040_2025",
})


def generate_outline_first_drafts(
    document: SourceDocumentInput,
    *,
    client: LlmClient,
    config: dict[str, Any] | None = None,
    root: str | Path | None = None,
) -> ExtractionBatch:
    """Generate draft objects by walking deterministic outline nodes."""
    outline = build_outline_tree(document)
    instruction_frame = build_instruction_sections_frame(document, outline=outline)
    spans = build_candidate_spans(document)
    flows = build_outbound_flows(document, outline=outline, spans=spans)
    run_outline_artifact_checks(document, outline, spans, flows).raise_for_issues()
    model = _micro_model(config or {})
    llm_calls = []

    objects: list[DraftObject] = []
    micro_stats: dict[str, Any] = {
        "cells_attempted": 0,
        "cells_succeeded": 0,
        "cells_failed": 0,
        "failure_reasons_by_kind": {},
        "findings": [],
        "formula_cells": [],
        "non_formula_cells": [],
        "source_cells_attempted": 0,
        "source_cells_succeeded": 0,
        "source_cells_resolved": 0,
        "source_cells_failed": 0,
        "resolved_source_addresses": [],
        "wrong_owner_instruction_span_count": 0,
        "wrong_owner_instruction_addresses": [],
        "unresolved_line_refs": [],
        "resolved_line_refs": [],
        "review_gaps": [],
        "transport_failures": 0,
        "instruction_sections_coverage": instruction_frame.coverage,
    }
    line_index = _outline_line_index(document.document_id, outline.children)
    line_kinds, line_children = _outline_line_metadata(document.document_id, outline.children)
    instruction_owners = _instruction_owner_map(spans)
    for outline_node in _formula_outline_nodes(outline.children, document_id=document.document_id):
        node_spans = _spans_for_outline_node(
            document,
            outline_node,
            spans,
            document_id=document.document_id,
            table_mode=outline_node.kind in {"transaction_table", "totals"},
            instruction_owners=instruction_owners,
        )
        target_cell_id = _outline_node_id(document.document_id, outline_node)
        wrong_owner_spans = _wrong_owner_instruction_spans(
            outline_node,
            spans,
            instruction_owners,
            document_id=document.document_id,
        )
        instruction_span_ids = instruction_span_ids_for_line(
            spans,
            str(outline_node.line_anchor or ""),
            owners=instruction_owners,
            owner_document_id=document.document_id,
        )
        if wrong_owner_spans:
            micro_stats["wrong_owner_instruction_span_count"] += len(wrong_owner_spans)
            micro_stats["wrong_owner_instruction_addresses"].append(target_cell_id)
        cell_record = {
            "target_cell_id": target_cell_id,
            "line_anchor": str(outline_node.line_anchor or ""),
            "label": outline_node.label,
            "status": "review_gap",
            "has_expression": False,
            "has_verbatim_citation": False,
            "review_gap": "no expression produced",
            "wrong_owner_instruction_spans": len(wrong_owner_spans),
            "instruction_span_ids": instruction_span_ids,
            "has_form_face_citation": False,
            "has_instruction_citation": bool(instruction_span_ids),
        }
        micro_stats["formula_cells"].append(cell_record)
        plan = _deterministic_schedule_d_formula_plan(document, outline_node, node_spans)
        formula_model = str(model)
        if plan is None:
            micro_stats["cells_attempted"] += 1
            try:
                plan = extract_formula_plan(
                    outline_node=outline_node,
                    spans=node_spans,
                    client=client,
                    config=config,
                    root=root,
                    target_cell_id=target_cell_id,
                    table_mode=outline_node.kind in {"transaction_table", "totals"},
                )
                micro_stats["cells_succeeded"] += 1
                telemetry = response_telemetry(plan)
                if telemetry is not None:
                    llm_calls.append(telemetry)
                    formula_model = telemetry.resolved_model or formula_model
            except Exception as exc:
                micro_stats["cells_failed"] += 1
                _record_micro_failure(micro_stats, outline_node, exc)
                _record_review_gap(micro_stats, cell_record, f"micro extraction failed: {type(exc).__name__}: {exc}")
                continue
        else:
            formula_model = "deterministic-schedule-d-formula"
        try:
            batch = assemble_formula_plan(
                document,
                outline_node,
                plan,
                node_spans,
                model=formula_model,
                root=root,
                line_index=line_index,
                line_kinds=line_kinds,
                line_children=line_children,
                resolution_events=micro_stats["resolved_line_refs"],
            )
        except FormulaAssemblyFinding as exc:
            if plan is not None and formula_model != "deterministic-schedule-d-formula":
                micro_stats["cells_succeeded"] -= 1
                micro_stats["cells_failed"] += 1
            _record_micro_finding(micro_stats, exc.finding)
            _record_micro_failure(micro_stats, outline_node, exc)
            if exc.finding.get("code") in {"unresolved_source_line", "ambiguous_parent_source_line"}:
                micro_stats["unresolved_line_refs"].append(dict(exc.finding))
            _record_review_gap(micro_stats, cell_record, str(exc.finding.get("reason", exc)))
            continue
        except Exception as exc:
            if plan is not None and formula_model != "deterministic-schedule-d-formula":
                micro_stats["cells_succeeded"] -= 1
                micro_stats["cells_failed"] += 1
                _record_micro_failure(micro_stats, outline_node, exc)
                _record_review_gap(micro_stats, cell_record, f"assembly failed: {type(exc).__name__}: {exc}")
                continue
            raise
        rules = batch.items("rules")
        citations = {ref for rule in rules for ref in rule.data.get("citation_refs", [])}
        cell_record["has_expression"] = bool(rules)
        cell_record["has_verbatim_citation"] = bool(citations)
        cell_record["has_form_face_citation"] = bool(citations)
        cell_record["citation_refs"] = sorted(citations)
        if rules and citations:
            cell_record["status"] = "complete"
            cell_record.pop("review_gap", None)
        elif rules:
            _record_review_gap(micro_stats, cell_record, "expression produced without a matching verbatim citation")
        else:
            _record_review_gap(micro_stats, cell_record, "no expression rule produced")
        # The outline pass owns the deterministic cell/node spine for ordinary
        # lines. Micro extraction contributes only the expression and its source
        # evidence there; allowing it to emit nodes would let a model response
        # replace a stable line node. Existing table/totals assembly is retained
        # because those nodes are the deterministic table-template projection.
        objects.extend(
            obj
            for obj in batch.objects
            if obj.kind in {"citations", "edges", "rules"}
            or (
                obj.kind == "nodes"
                and (
                    outline_node.kind in {"transaction_table", "totals"}
                    or ("operation_plan" not in plan and obj.data.get("node_type") == "computed")
                )
            )
        )
    if document.document_id in NON_FORMULA_REVIEW_DOCUMENTS:
        _extract_non_formula_cells(
            document,
            outline.children,
            spans,
            client=client,
            config=config,
            root=root,
            line_index=line_index,
            instruction_owners=instruction_owners,
            model=model,
            stats=micro_stats,
            llm_calls=llm_calls,
        )
    background_stats, background_calls = extract_background_controls(
        document,
        spans,
        client=client,
        config=config,
        root=root,
    )
    micro_stats.update(background_stats)
    llm_calls.extend(background_calls)
    objects.extend(assemble_table_subunits(document, outline, objects, model="deterministic-table-detector"))
    objects.extend(_schedule_d_band_tables(document, outline.children, model="deterministic-schedule-d-band-detector"))
    objects.extend(_schedule_d_not_modeled_document(document, outline.children, model="deterministic-schedule-d-scope"))
    objects.extend(_outline_structure_objects(document, outline.children, spans, model=model))
    objects.extend(_write_in_amount_nodes(document, outline.children, spans, objects=objects, model=model))
    objects.extend(_simple_line_objects(document, outline.children, spans, objects=objects, model=model))
    objects.extend(_line_cue_objects(document, outline.children, spans, model=model))
    objects.extend(_generic_not_modeled_document(document, outline.children, objects=objects, model=model))

    return ExtractionBatch(
        document_id=document.document_id,
        year=document.year,
        objects=_dedupe_objects(objects),
        llm_calls=llm_calls,
        micro_stats=micro_stats,
    )


def _extract_non_formula_cells(
    document: SourceDocumentInput,
    nodes: list[OutlineNode],
    spans: list[CandidateSpan],
    *,
    client: LlmClient,
    config: dict[str, Any] | None,
    root: str | Path | None,
    line_index: dict[tuple[str, str], str],
    instruction_owners: dict[str, frozenset[str]],
    model: str,
    stats: dict[str, Any],
    llm_calls: list[Any],
) -> None:
    """Generate a source declaration for every non-formula line in the review slice."""
    formula_anchors = {
        str(node.line_anchor).lower()
        for node in _formula_outline_nodes(nodes, document_id=document.document_id)
        if node.line_anchor
    }
    for node in _non_formula_outline_nodes(nodes):
        anchor = str(node.line_anchor or "").lower()
        if not anchor or anchor in formula_anchors:
            continue
        target_cell_id = _outline_node_id(document.document_id, node)
        node_spans = _spans_for_outline_node(
            document,
            node,
            spans,
            document_id=document.document_id,
            instruction_owners=instruction_owners,
        )
        record: dict[str, Any] = {
            "target_cell_id": target_cell_id,
            "line_anchor": anchor,
            "label": node.label,
            "status": "review_gap",
            "source_kind": None,
            "form": "",
            "line": "",
            "box": "",
            "quote": "",
            "instruction_span_ids": [
                span_id
                for span_id in instruction_span_ids_for_line(
                    spans,
                    anchor,
                    owners=instruction_owners,
                    owner_document_id=document.document_id,
                )
            ],
            "has_form_face_citation": False,
            "has_instruction_citation": bool(
                instruction_span_ids_for_line(
                    spans,
                    anchor,
                    owners=instruction_owners,
                    owner_document_id=document.document_id,
                )
            ),
            "review_gap": "source declaration has not been generated",
        }
        stats.setdefault("non_formula_cells", []).append(record)
        stats["source_cells_attempted"] += 1
        try:
            plan = extract_non_formula_source(
                outline_node=node,
                spans=node_spans,
                client=client,
                config=config,
                target_cell_id=target_cell_id,
            )
            record.update(
                {
                    "source_kind": str(plan.get("source_kind") or ""),
                    "form": str(plan.get("form") or ""),
                    "line": str(plan.get("line") or ""),
                    "box": str(plan.get("box") or ""),
                    "quote": str(plan.get("quote") or ""),
                }
            )
            quote = record["quote"]
            record["citation_span_ids"] = [
                span.span_id for span in node_spans if _quote_matches(quote, span.text)
            ][:1]
            resolved = _resolve_declared_source(
                document,
                record,
                line_index=line_index,
            )
            record["resolved_source_id"] = resolved
            if record["source_kind"] == "filer_entry":
                record["resolved_source_id"] = "filer_entry"
                record["status"] = "complete"
                record.pop("review_gap", None)
            elif resolved:
                record["status"] = "complete"
                record.pop("review_gap", None)
                stats["source_cells_resolved"] += 1
                stats["resolved_source_addresses"].append(target_cell_id)
            else:
                record["review_gap"] = "source reference did not resolve to a canonical line"
                stats.setdefault("findings", []).append(
                    {
                        "code": "unresolved_non_formula_source",
                        "target_cell_id": target_cell_id,
                        "source_kind": record["source_kind"],
                        "form": record["form"],
                        "line": record["line"],
                        "reason": record["review_gap"],
                    }
                )
            stats["source_cells_succeeded"] += 1
            telemetry = response_telemetry(plan)
            if telemetry is not None:
                llm_calls.append(telemetry)
                record["model"] = telemetry.resolved_model or model
        except Exception as exc:
            stats["source_cells_failed"] += 1
            record["review_gap"] = f"source extraction failed: {type(exc).__name__}: {exc}"
            _record_micro_failure(stats, node, exc)


def _non_formula_outline_nodes(nodes: list[OutlineNode]) -> list[OutlineNode]:
    return [
        node
        for node in _flatten_nodes(nodes)
        if node.kind == "line" and node.line_anchor and _addressable_anchor(str(node.line_anchor))
    ]


def _resolve_declared_source(
    document: SourceDocumentInput,
    record: dict[str, Any],
    *,
    line_index: dict[tuple[str, str], str],
) -> str | None:
    """Resolve a model's printed source declaration through deterministic indexes."""
    if record.get("source_kind") not in {"form_line", "information_return"}:
        return None
    form = str(record.get("form") or "").strip()
    if not form:
        return None
    if record.get("source_kind") == "information_return":
        box = str(record.get("box") or "").strip().lower()
        if not box or not re.fullmatch(r"[0-9]+[a-z]?", box, re.IGNORECASE):
            return None
        return _canonical_external_source_id(form, document.year, box=box)
    line = str(record.get("line") or "").strip()
    if not line:
        return None
    resolved = _resolve_source_line(document, {"form": form, "line": line}, line_index=line_index)
    if resolved:
        return resolved
    if _is_external_form_reference(document, form):
        if re.fullmatch(r"[0-9]+[a-z]?", line, re.IGNORECASE):
            return _canonical_external_source_id(form, document.year, line=line)
    return None


def _quote_matches(quote: str, source: str) -> bool:
    """Compare source evidence after folding line-break whitespace only."""
    normalize = lambda value: " ".join(str(value).split())
    return normalize(quote) in normalize(source) or normalize(source) in normalize(quote)


def _is_external_form_reference(document: SourceDocumentInput, form: str) -> bool:
    """Return whether a source declaration names a different form."""
    normalized = re.sub(r"[^a-z0-9]+", "", form.lower())
    current = document.document_id.lower()
    current_stem = current.removesuffix(f"_{document.year}")
    current_tokens = {re.sub(r"[^a-z0-9]+", "", value) for value in (current, current_stem)}
    if normalized in current_tokens:
        return False
    return not ("form1040" in normalized and "form1040" in re.sub(r"[^a-z0-9]+", "", current))


def _canonical_external_source_id(
    form: str,
    year: str | int,
    *,
    line: str | None = None,
    box: str | None = None,
) -> str:
    """Create a stable source identity from an explicit printed reference."""
    compact = re.sub(r"[^a-z0-9]+", "", form.lower())
    if compact in {"w2", "formw2"}:
        document_token = "form_w2"
    else:
        document_token = _slug(form)
        if not document_token.startswith(("form_", "schedule_")):
            document_token = f"form_{document_token}"
    if box:
        return _slug(f"{document_token}_{year}_box_{box}")
    return _slug(f"{document_token}_{year}_root_line_{line}")


def _formula_outline_nodes(nodes: list[OutlineNode], *, document_id: str = "") -> list[OutlineNode]:
    selected: list[OutlineNode] = []
    for node in nodes:
        if _is_formula_node(node) and not (document_id.startswith("schedule_d_") and node.kind == "line"):
            selected.append(node)
        selected.extend(_formula_outline_nodes(node.children, document_id=document_id))
    return selected


def _is_formula_node(node: OutlineNode) -> bool:
    if node.kind == "transaction_table" and "h" in node.columns:
        return True
    if node.kind == "totals" and bool(node.columns):
        return True
    if node.kind != "line" or not node.line_anchor:
        return False
    label = node.label.lower()
    return any(
        cue in label
        for cue in (
            "add line",
            "add the amount",
            "subtract line",
            "amount from line",
            "amount of line",
            "more than line",
            "less than line",
            "combine line",
            "multiply line",
            "smaller of line",
            "larger of line",
            "one-half of line",
        )
    )


def _record_micro_failure(stats: dict[str, Any], node: OutlineNode, error: Exception) -> None:
    """Record one isolated cell failure without allowing it to kill the document."""
    kind = type(error).__name__
    reason = str(error).encode("ascii", errors="replace").decode("ascii")[:500]
    if is_transient_transport_error(error):
        stats["transport_failures"] = int(stats.get("transport_failures", 0)) + 1
    grouped = stats.setdefault("failure_reasons_by_kind", {})
    grouped.setdefault(kind, []).append(
        {
            "outline_id": node.outline_id,
            "line_anchor": node.line_anchor,
            "reason": reason,
        }
    )


def _record_micro_finding(stats: dict[str, Any], finding: dict[str, Any]) -> None:
    """Persist a fail-closed identity finding beside the draft metrics."""
    stats.setdefault("findings", []).append({str(key): value for key, value in finding.items()})


def _record_review_gap(stats: dict[str, Any], cell: dict[str, Any], reason: str) -> None:
    """Record an explicit per-cell gap instead of silently omitting a formula."""
    cell["status"] = "expression_without_citation" if cell.get("has_expression") else "review_gap"
    cell["review_gap"] = str(reason).encode("ascii", errors="replace").decode("ascii")[:500]
    stats.setdefault("review_gaps", []).append(dict(cell))


def _outline_line_index(document_id: str, nodes: list[OutlineNode]) -> dict[tuple[str, str], str]:
    """Build an unambiguous printed-line to canonical-node index."""
    index: dict[tuple[str, str], str] = {}
    ambiguous: set[tuple[str, str]] = set()
    for node in _flatten_nodes(nodes):
        if not node.line_anchor:
            continue
        key = (document_id.lower(), str(node.line_anchor).lower())
        value = _outline_node_id(document_id, node)
        if key in index and index[key] != value:
            ambiguous.add(key)
        else:
            index[key] = value
    for key in ambiguous:
        index.pop(key, None)
    return index


def _outline_line_metadata(
    document_id: str,
    nodes: list[OutlineNode],
) -> tuple[dict[tuple[str, str], str], dict[tuple[str, str], list[str]]]:
    """Return node kinds and deterministic lettered-child ids for line resolution."""
    document_key = document_id.lower()
    kinds: dict[tuple[str, str], str] = {}
    children: dict[tuple[str, str], list[str]] = {}
    for node in _flatten_nodes(nodes):
        anchor = str(node.line_anchor or "").lower()
        if not anchor:
            continue
        key = (document_key, anchor)
        if key in kinds and kinds[key] != node.kind:
            kinds.pop(key, None)
        else:
            kinds[key] = node.kind
        if anchor[-1].isalpha() and anchor[:-1]:
            parent_key = (document_key, anchor[:-1])
            children.setdefault(parent_key, []).append(_outline_node_id(document_id, node))
    return kinds, {key: sorted(set(values)) for key, values in children.items()}


def _outline_node_id(document_id: str, node: OutlineNode) -> str:
    """Return the same stable id used by the outline projection."""
    import re

    return re.sub(r"[^a-z0-9]+", "_", f"{document_id}_{node.outline_id}".lower()).strip("_")


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
    table_mode: bool = False,
    instruction_owners: dict[str, frozenset[str]] | None = None,
) -> list[CandidateSpan]:
    """Select a small evidence packet for one micro-extraction prompt."""
    instruction_owners = instruction_owners or _instruction_owner_map(spans)
    selected: list[CandidateSpan] = []
    if node.line_anchor:
        instruction_hits: list[CandidateSpan] = []
        source_span = _span_for_line(document, node, spans)
        for span in spans:
            if span is source_span:
                selected.append(span)
                continue
            if span.relationship == "source":
                continue
            if _instruction_span_belongs_to_line(
                span,
                node.line_anchor,
                instruction_owners,
                owner_document_id=document_id,
            ):
                instruction_hits.append(span)
        if source_span is not None:
            source_spans = [span for span in spans if span.relationship == "source"]
            source_index = source_spans.index(source_span) if source_span in source_spans else -1
            if source_index >= 0:
                context = source_spans[max(0, source_index - 20): source_index + 21]
                selected.extend(span for span in context if span not in selected)
        selected.extend(instruction_hits[:3])
    if table_mode and node.columns:
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


def _instruction_span_belongs_to_line(
    span: CandidateSpan,
    anchor: str,
    instruction_owners: dict[str, frozenset[str]] | None = None,
    *,
    owner_document_id: str | None = None,
) -> bool:
    """Accept an instruction span only when its own entry is this line.

    Mentioning a line in a different line's instructions is not ownership. The
    old mention-based join attached the line 27b paragraph to Form 1040 line
    1z because it mentioned 1z. Explicit headings and table-row prefixes are
    the deterministic ownership signals; a bare mention remains excluded.
    """
    if owner_document_id and span.owner_document_id and span.owner_document_id != owner_document_id:
        return False
    owner = (instruction_owners or {}).get(span.span_id, ())
    if anchor.lower() not in {str(value).lower() for value in owner}:
        return False
    return True


def _instruction_owner_map(spans: list[CandidateSpan]) -> dict[str, frozenset[str]]:
    """Assign each instruction span to its nearest explicit line heading.

    Instruction documents commonly put a line heading on one span and the
    actual prose on following spans.  A mention-only join treated every such
    prose span as belonging to every line it mentioned.  Carrying the heading
    owner forward preserves the source's local structure while resetting at a
    non-line Markdown heading or at a new related document.
    """
    return instruction_line_owners(spans)


def _wrong_owner_instruction_spans(
    node: OutlineNode,
    spans: list[CandidateSpan],
    instruction_owners: dict[str, frozenset[str]] | None = None,
    *,
    document_id: str | None = None,
) -> list[CandidateSpan]:
    """Find instruction mentions that were previously eligible but are not owned."""
    anchor = str(node.line_anchor or "").lower()
    if not anchor:
        return []
    instruction_owners = instruction_owners or _instruction_owner_map(spans)
    phrase = f"line {anchor}"
    wrong: list[CandidateSpan] = []
    for span in spans:
        if span.relationship == "source" or phrase not in span.text.lower():
            continue
        if document_id and span.owner_document_id and span.owner_document_id != document_id:
            continue
        if not _direct_line_evidence(span.text, anchor):
            continue
        owner = (instruction_owners or {}).get(span.span_id, ())
        owned = {str(value).lower() for value in owner}
        if owned and anchor not in owned:
            wrong.append(span)
    return wrong


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
