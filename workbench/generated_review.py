"""Project draft-only generated cells into the review workbench.

This module is a read-only workbench projection.  It never promotes draft
objects and it never edits the graph.  The form geometry remains the physical
spine; generated draft records add formula and background-policy evidence to
the complete physical cell inventory.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import yaml

from workbench.address_verdicts import expression_kind_bucket
from workbench.cell_inventory import DocumentCells, build_document_cells


GENERATED_REVIEW_DOCUMENTS = frozenset({
    "form_1040_2025",
    "schedule_1_2025",
    "schedule_a_2025",
    "schedule_2_2025",
    "schedule_3_2025",
})
FULL_FORM_REVIEW_DOCUMENTS = GENERATED_REVIEW_DOCUMENTS
GENERATED_OUTCOME_KINDS = frozenset({
    "computation",
    "filer_entry",
    "election",
    "information_return",
    "not_derivable",
})


_LINE_RUN_IN_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\*\*)?Line\s+([0-9]+[a-z]?)(?=[\s.*:]|$)",
    re.IGNORECASE,
)


def build_generated_document_cells(
    root: str | Path,
    year: str | int,
    document_id: str,
    *,
    geometry_entries: list[dict[str, Any]] | None = None,
    page_geometry: list[dict[str, Any]] | None = None,
    include_inputs: bool = True,
) -> DocumentCells:
    """Return the generated formula-cell slice over the physical form cells."""
    base = build_document_cells(
        root,
        year,
        document_id,
        geometry_entries=geometry_entries,
        page_geometry=page_geometry,
        include_inputs=include_inputs,
    )
    if document_id not in GENERATED_REVIEW_DOCUMENTS:
        return base
    draft = _load_draft(Path(root), year, document_id)
    micro = draft.get("micro_extraction", {})
    formula_cells = micro.get("formula_cells", [])
    if not isinstance(formula_cells, list):
        raise ValueError(f"generated draft has no formula_cells list: {document_id}")
    if not formula_cells:
        raise ValueError(f"generated draft has no formula cells: {document_id}")
    non_formula_cells = micro.get("non_formula_cells", [])
    records = [item for item in formula_cells + (non_formula_cells if isinstance(non_formula_cells, list) else []) if isinstance(item, dict)]
    records = _ensure_line_review_records(records, draft.get("outline"), document_id)

    rules = _records(draft.get("rules"))
    edges = _records(draft.get("edges"))
    decisions = _records(draft.get("decisions"))
    citations = _citation_index(draft.get("citations"))
    spans = _span_index(draft.get("candidate_spans"))
    background = _background_index(micro)
    outcomes = {
        str(item.get("target_cell_id") or ""): item
        for item in _records(micro.get("outcomes"))
        if item.get("target_cell_id")
    }
    instruction_ids_by_line = _instruction_span_index(
        spans,
        owner_document_id=(
            document_id
            if document_id == "form_1040_2025"
            or document_id in {"schedule_2_2025", "schedule_3_2025"}
            else None
        ),
        retain_foreign_owner_spans=document_id == "form_1040_2025",
    )
    provenance = _provenance(draft.get("metrics"))
    cells_by_anchor = _cells_by_anchor(base.cells)
    decision_cells, unplaceable = _project_decisions(
        decisions,
        micro,
        cells_by_anchor,
        document_id=document_id,
        provenance=provenance,
    )
    decision_ids = {str(item.get("decision_id") or "") for item in decisions}
    decisions_by_target = {
        str(item.get("sets_node") or ""): item
        for item in decisions
        if item.get("sets_node")
    }
    generated_by_cell_id: dict[str, dict[str, Any]] = {}
    for formula in records:
        anchor = _normalize_anchor(formula.get("line_anchor"))
        matches = cells_by_anchor.get(anchor, [])
        if not matches:
            # Some legacy address rows carry a stale official_ref, while the
            # geometry label still contains the printed line.  Use that label
            # only as a projection fallback; do not rewrite the address artifact.
            marker = re.compile(rf"(?:^|\s){re.escape(anchor)}\s*-\s*f1_", re.IGNORECASE)
            matches = [
                item for item in base.cells
                if marker.search(str(item.get("display_name") or ""))
                or marker.search(str(item.get("geometry_label") or ""))
            ]
        if not matches:
            if str(formula.get("decision_id") or "") in decision_ids:
                continue
            unplaceable.append(
                _unplaceable_record(
                    document_id,
                    formula,
                    reason="no physical cell matches the generated line anchor",
                    provenance=provenance,
                )
            )
            continue
        target = str(formula.get("target_cell_id") or "")
        base_cell = _choose_cell(matches, target)
        target_rules = [
            item for item in rules
            if str(item.get("rule_id") or "").startswith(f"rule_{target}_")
        ]
        target_edges = [
            item for item in edges
            if str(item.get("target") or "") == target
        ]
        rule = target_rules[0] if target_rules else {}
        operation = str(rule.get("operation") or "REVIEW_GAP").lower()
        outcome = outcomes.get(target, {})
        generated_kind = str(
            formula.get("outcome_kind")
            or outcome.get("kind")
            or ("election" if target in decisions_by_target else "")
        )
        if generated_kind not in GENERATED_OUTCOME_KINDS:
            generated_kind = ""
        expression = (
            _expression(target, formula, rule, target_edges, base.cells, base_cell)
            if not generated_kind or generated_kind == "computation"
            else _outcome_expression(
                generated_kind,
                formula,
                outcome,
                target,
                base_cell,
                decisions_by_target.get(target),
            )
        )
        decision = decisions_by_target.get(target)
        rule_citation_ids = [str(value) for value in rule.get("citation_refs", []) or []]
        if isinstance(decision, dict):
            rule_citation_ids.extend(
                str(value) for value in decision.get("citation_refs", []) or []
            )
        rule_citation_ids = list(dict.fromkeys(rule_citation_ids))
        rule_citations = [citations[value] for value in rule_citation_ids if value in citations]
        record_instruction_ids = [str(value) for value in formula.get("instruction_span_ids", []) or []]
        exact_instruction_ids = instruction_ids_by_line.get(anchor, [])
        if not exact_instruction_ids and any(
            _is_line_label_quote(item.get("quoted_text"))
            for item in base_cell.get("instruction_citations") or []
        ):
            cell_anchor = _normalize_anchor(base_cell.get("official_ref"))
            if cell_anchor != anchor:
                exact_instruction_ids = instruction_ids_by_line.get(cell_anchor, [])
        instruction_span_ids = (
            exact_instruction_ids
            if exact_instruction_ids
            else record_instruction_ids
        )
        instruction_citations = [
            _instruction_citation(str(span_id), span, anchor)
            for span_id in instruction_span_ids
            if (span := spans.get(str(span_id))) is not None
        ]
        if not instruction_span_ids:
            # A generated record may have no owned packet for its physical
            # cell.  Keep the inventory's existing instruction citation rather
            # than turning a previously cited cell into a silent gap.
            instruction_citations = list(base_cell.get("instruction_citations") or [])
        form_citations = [
            item for item in rule_citations
            if not str(item.get("source_document_id") or item.get("document_id") or "").startswith("instructions_")
        ]
        if not instruction_ids_by_line:
            instruction_citations.extend(
                item for item in rule_citations
                if str(item.get("source_document_id") or item.get("document_id") or "").startswith("instructions_")
            )
        if not rule_citations:
            form_citations = list(base_cell.get("citations") or [])
            form_citations.extend(
                _span_citation(spans[str(span_id)])
                for span_id in formula.get("citation_span_ids", []) or []
                if str(span_id) in spans and spans[str(span_id)].get("relationship") == "source"
            )
        kind = str(expression.get("kind") or "review_gap")
        try:
            risk_bucket = expression_kind_bucket(kind)
        except ValueError:
            risk_bucket = "NOT_REVIEWABLE"
        inferred_policy = {
            "ARITHMETIC": "computed",
            "COPY": "copied",
            "USER_ENTRY": "user_entered",
            "IMPORTED": "imported",
        }.get(risk_bucket)
        outcome_policy = {
            "filer_entry": "user_entered",
            "information_return": "imported",
            "election": "decision_required",
            "not_derivable": "unsupported",
        }.get(generated_kind)
        background_record = background.get(str(base_cell.get("field_name") or ""))
        formula_resolved = generated_kind != "not_derivable" and kind != "review_gap"
        # A background failover never replaces a formula or source result.
        # This is the projection-side guard for controls such as Form 1040 line
        # 32 whose field-map policy is stale but whose draft expression exists.
        policy_background = None if formula_resolved else background_record
        if outcome_policy:
            population_policy = outcome_policy
        elif formula_resolved and inferred_policy:
            population_policy = inferred_policy
        else:
            population_policy = _projected_policy(base_cell, policy_background, inferred_policy)
        review_gap = str(formula.get("review_gap") or "")
        cell = dict(base_cell)
        cell.update(
            {
                "generated": True,
                "review_source": "draft_only",
                "generated_target_cell_id": target,
                "generated_status": str(formula.get("status") or "review_gap"),
                "generated_kind": generated_kind or ("computation" if rule_citations else ""),
                "generated_model": str(formula.get("model") or provenance["model"]),
                "generated_provider": provenance["provider"],
                "generated_provenance": dict(provenance),
                "expression": expression,
                "operation": str(expression.get("operation") or operation).upper(),
                "inputs": [
                    {
                        "node_id": str(edge.get("source") or ""),
                        "role": str(edge.get("role") or "") or None,
                        "ref": _operand_label(str(edge.get("source") or ""), base.cells),
                        "display_name": _operand_label(str(edge.get("source") or ""), base.cells),
                    }
                    for edge in _effective_edges(str(rule.get("operation") or ""), target_edges)
                    if edge.get("source")
                ],
                "form_citations": form_citations,
                "instruction_citations": instruction_citations,
                "citations": form_citations,
                "review_gap": (
                    review_gap
                    or str(outcome.get("reason") or "")
                    or str(expression.get("reason") or "")
                    or None
                ),
                "kind_reason": (
                    str(outcome.get("reason") or "")
                    or str(expression.get("reason") or "")
                    or None
                ),
                "risk_bucket": risk_bucket,
                "population_policy": population_policy or "review_gap",
                "policy_origin": (
                    "derived"
                    if formula_resolved
                    else _policy_origin(base_cell, background_record, population_policy)
                ),
                "policy_basis": (
                    "formula_or_source"
                    if formula_resolved
                    else _policy_basis(base_cell, background_record)
                ),
                "policy_defaulted": False if formula_resolved else _policy_bool(background_record, "policy_defaulted"),
                "policy_derived": True if formula_resolved else _policy_bool(background_record, "policy_derived"),
                "failover_class": None if formula_resolved else _background_value(background_record, "failover_class"),
                "decisions": [],
            }
        )
        if not formula_resolved:
            _apply_background_overlay(cell, background_record, spans)
        generated_by_cell_id[str(base_cell["cell_id"])] = cell

    if document_id in FULL_FORM_REVIEW_DOCUMENTS:
        for base_cell in base.cells:
            cell_id = str(base_cell["cell_id"])
            if cell_id in generated_by_cell_id:
                continue
            generated_by_cell_id[cell_id] = _project_background_cell(
                base_cell,
                background.get(str(base_cell.get("field_name") or "")),
                spans,
                instruction_ids_by_line,
                provenance=provenance,
            )
        expected_count = len(base.cells)
    else:
        expected_count = len(records)

    if len(generated_by_cell_id) != expected_count:
        raise ValueError(f"generated draft cells were not projected: {document_id}")
    for cell_id, decisions_for_cell in decision_cells.items():
        if cell_id in generated_by_cell_id:
            generated_by_cell_id[cell_id]["decisions"] = decisions_for_cell
    generated = list(generated_by_cell_id.values())
    generated.sort(key=lambda item: (int(item.get("order", 0)), str(item.get("cell_id"))))
    return DocumentCells(
        document_id=base.document_id,
        cells=generated,
        pages=base.pages,
        page_geometry=base.page_geometry,
        unplaceable=unplaceable,
    )


def _load_draft(root: Path, year: str | int, document_id: str) -> dict[str, Any]:
    draft_dir = root / "graph" / str(year) / "_drafts" / document_id
    if not draft_dir.is_dir():
        raise ValueError(f"generated draft directory is missing: {draft_dir}")
    return {
        "micro_extraction": _yaml(draft_dir / "micro_extraction.yaml", {}),
        "outline": _yaml(draft_dir / "outline.yaml", {}),
        "rules": _yaml(draft_dir / "rules.yaml", []),
        "edges": _yaml(draft_dir / "edges.yaml", []),
        "decisions": _yaml(draft_dir / "decisions.yaml", []),
        "citations": _yaml(draft_dir / "citations.yaml", []),
        "candidate_spans": _yaml(draft_dir / "candidate_spans.yaml", []),
        "metrics": _yaml(draft_dir / "metrics.yaml", {}),
    }


def _yaml(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return default if value is None else value


def _records(value: Any) -> list[dict[str, Any]]:
    return [item for item in value or [] if isinstance(item, dict)]


def _citation_index(value: Any) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("citation_id")): dict(item)
        for item in _records(value)
        if item.get("citation_id")
    }


def _span_index(value: Any) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("span_id")): dict(item)
        for item in _records(value)
        if item.get("span_id")
    }


def _instruction_citation(
    span_id: str,
    span: dict[str, Any],
    line: str,
) -> dict[str, Any]:
    """Project one instruction span into the packet for a physical line.

    A shared instruction block is still the only evidence available for an
    owner without an individual run-in label.  When the acquired text does
    contain a line label, the workbench shows only that label's run.  The
    derived citation id is projection-local and keeps the source span id so a
    reviewer can trace it back to the unmodified draft artifact.
    """
    line = _normalize_anchor(line)
    segments = _instruction_run_in_segments(str(span.get("text") or ""))
    quoted_text = segments.get(line)
    citation = {
        "citation_id": (
            f"{span_id}__line_{line}" if quoted_text is not None else span_id
        ),
        "quoted_text": quoted_text if quoted_text is not None else span.get("text"),
        "locator": span.get("locator"),
        "url": None,
        "retrieved_date": None,
        "source_document_id": span.get("document_id"),
        "resolved": True,
    }
    if quoted_text is not None:
        citation["source_span_id"] = span_id
        citation["projection"] = "run_in_line"
    return citation


def _instruction_run_in_segments(text: str) -> dict[str, str]:
    """Return the text runs beginning at individual line labels.

    The family headings use ``Lines`` and are deliberately excluded.  Only a
    singular ``Line`` at the start of a markdown line is a run-in boundary;
    references such as ``see line 13b`` inside prose cannot split a packet.
    """
    markers: list[tuple[int, str]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        match = _LINE_RUN_IN_RE.match(line.rstrip("\r\n"))
        if match:
            markers.append((offset, match.group(1).lower()))
        offset += len(line)
    segments: dict[str, str] = {}
    for index, (start, line) in enumerate(markers):
        end = markers[index + 1][0] if index + 1 < len(markers) else len(text)
        segments.setdefault(line, text[start:end].strip())
    return segments


def _instruction_span_index(
    spans: dict[str, dict[str, Any]],
    *,
    owner_document_id: str | None = None,
    retain_foreign_owner_spans: bool = False,
) -> dict[str, list[str]]:
    """Rebuild line ownership from draft spans without importing the pipeline.

    Current candidate-span artifacts persist ``owner_lines`` from the typed
    instruction frame.  That explicit ownership is authoritative.  Older
    sidecars may lack it, so their first non-empty heading line remains a
    compatibility fallback.  When a shared booklet carries explicit ownership,
    the requested form's owner is applied before indexing the line packet.
    Form 1040 also retains a foreign-owner span when no Form 1040-owned span
    covers that line, preserving coverage for shared booklet material.  Once a
    local owner exists, foreign-owner spans are excluded from that line's
    packet so a run-in segment from another form cannot become primary.
    Several spans may own one line: a run-in projection for that line is as
    narrow as a single-line owner, while a content-bearing span wins a tie
    with an empty heading stub.
    """
    scoped_spans = [
        (span_id, span)
        for span_id, span in spans.items()
        if str(span.get("relationship") or "") != "source"
        and not (
            owner_document_id
            and not retain_foreign_owner_spans
            and str(span.get("owner_document_id") or "")
            and str(span.get("owner_document_id")) != owner_document_id
        )
    ]
    result: dict[str, list[str]] = {}
    current_document = ""
    current_lines: set[str] = set()
    current_level: int | None = None
    span_order = {span_id: index for index, (span_id, _) in enumerate(scoped_spans)}
    effective_widths: dict[tuple[str, str], int] = {}
    has_body: dict[str, bool] = {}

    def add_span(line: str, span_id: str, owned_lines: set[str], span: dict[str, Any]) -> None:
        result.setdefault(line, []).append(span_id)
        run_in_segments = _instruction_run_in_segments(str(span.get("text") or ""))
        effective_widths[(line, span_id)] = (
            1 if line in run_in_segments else len(owned_lines)
        )
        has_body[span_id] = _instruction_span_has_body(str(span.get("text") or ""))

    for span_id, span in scoped_spans:
        document_id = str(span.get("document_id") or "")
        if document_id != current_document:
            current_document = document_id
            current_lines = set()
            current_level = None
        text = str(span.get("text") or "").strip()
        explicit_lines = {
            str(value).strip().lower()
            for value in span.get("owner_lines", []) or []
            if str(value).strip()
        }
        if explicit_lines:
            current_lines = explicit_lines
            current_level = None
            for line in current_lines:
                add_span(line, span_id, current_lines, span)
            continue
        heading_line = next((line for line in text.splitlines() if line.strip()), "")
        line_heading = re.match(
            r"^(#{1,6})\s*(?:\*\*)?lines?\s+(.+?)\s*$",
            heading_line,
            re.IGNORECASE,
        )
        if line_heading:
            prefix = re.split(r"\s+-\s+|\s*:\s+", line_heading.group(2), maxsplit=1)[0]
            current_lines = {
                token.lower()
                for token in re.findall(r"\b[0-9]+[a-z]?\b", prefix, re.IGNORECASE)
            }
            current_level = len(line_heading.group(1))
            for line in current_lines:
                add_span(line, span_id, current_lines, span)
            continue
        heading = re.match(r"^\s*(#{1,6})\s+", text)
        if heading:
            if current_level is not None and len(heading.group(1)) <= current_level:
                current_lines = set()
                current_level = None
            for line in current_lines:
                add_span(line, span_id, current_lines, span)
            continue
        table_line = re.match(r"^\s*\|\s*(?:\*\*)?([0-9]+[a-z]?)\.", text, re.IGNORECASE)
        owned_lines = {table_line.group(1).lower()} if table_line else current_lines
        for line in owned_lines:
            add_span(line, span_id, owned_lines, span)
    if owner_document_id and retain_foreign_owner_spans:
        span_by_id = {span_id: span for span_id, span in scoped_spans}
        for line, span_ids in result.items():
            has_local_owner = any(
                str(span_by_id[span_id].get("owner_document_id") or "")
                == owner_document_id
                for span_id in span_ids
            )
            if has_local_owner:
                result[line] = [
                    span_id
                    for span_id in span_ids
                    if not str(span_by_id[span_id].get("owner_document_id") or "")
                    or str(span_by_id[span_id].get("owner_document_id"))
                    == owner_document_id
                ]
    for line, span_ids in result.items():
        span_ids.sort(
            key=lambda span_id: (
                effective_widths[(line, span_id)],
                0 if has_body[span_id] else 1,
                span_order[span_id],
            )
        )
    return result


def _instruction_span_has_body(text: str) -> bool:
    """Return whether a span contains content beyond a line heading."""
    return any(
        line.strip()
        and not re.match(
            r"^\s*(?:#{1,6}\s*)?(?:\*\*)?Lines?\b",
            line,
            re.IGNORECASE,
        )
        for line in text.splitlines()
    )


def _provenance(metrics: Any) -> dict[str, str]:
    data = metrics if isinstance(metrics, dict) else {}
    calls = _records(data.get("llm_calls"))
    call = next((item for item in calls if item.get("outcome") == "success"), calls[0] if calls else {})
    return {
        "model": str(call.get("resolved_model") or call.get("requested_model") or (data.get("models_used") or ["unknown"])[0]),
        "provider": str(call.get("resolved_provider") or (data.get("providers_used") or ["unknown"])[0]),
        "stage": "draft_micro_extraction",
    }


def _normalize_anchor(value: Any) -> str:
    return re.sub(r"^line\s+", "", str(value or "").strip().lower())


def _cells_by_anchor(cells: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for cell in cells:
        anchor = _normalize_anchor(cell.get("official_ref"))
        if anchor:
            result.setdefault(anchor, []).append(cell)
    return result


def _project_decisions(
    decisions: list[dict[str, Any]],
    micro: Any,
    cells_by_anchor: dict[str, list[dict[str, Any]]],
    *,
    document_id: str,
    provenance: dict[str, str],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Project generated elections onto physical cells or a visible form row."""
    metadata = _decision_metadata(micro)
    placed: list[tuple[str, bool, dict[str, Any]]] = []
    unplaceable: list[dict[str, Any]] = []
    for decision in decisions:
        decision_id = str(decision.get("decision_id") or "")
        meta = metadata.get(decision_id, {})
        original_anchor = _decision_anchor(decision, meta)
        matches = cells_by_anchor.get(original_anchor, [])
        placed_on_original = bool(matches)
        anchor = original_anchor
        anchor_source = "line"
        if not matches:
            for candidate in _decision_subline_candidates(decision, original_anchor):
                candidate_matches = cells_by_anchor.get(candidate, [])
                if candidate_matches:
                    matches = candidate_matches
                    anchor = candidate
                    anchor_source = "question_or_options"
                    break
        if not matches:
            unplaceable.append(
                _unplaceable_record(
                    document_id,
                    {
                        "target_cell_id": meta.get("target_cell_id") or decision.get("sets_node"),
                        "line_anchor": original_anchor,
                        "label": meta.get("label") or decision.get("question") or original_anchor,
                        "response_kind": "election",
                        "question": decision.get("question"),
                        "decision_id": decision_id,
                    },
                    reason=(
                        "no physical cell matches the generated line and no concrete "
                        "sub-line named by the question or options has a physical cell"
                    ),
                    provenance=provenance,
                    decision=decision,
                )
            )
            continue
        cell = _choose_decision_cell(matches, str(meta.get("target_cell_id") or decision.get("sets_node") or ""))
        placed.append(
            (
                str(cell.get("cell_id") or ""),
                placed_on_original,
                {
                    "decision_id": decision_id,
                    "question": " ".join(str(decision.get("question") or "").split()),
                    "options": [dict(item) for item in decision.get("options", []) if isinstance(item, dict)],
                    "citation_refs": [str(item) for item in decision.get("citation_refs", []) or []],
                    "target_cell_id": str(meta.get("target_cell_id") or decision.get("sets_node") or ""),
                    "line_anchor": original_anchor,
                    "anchor": anchor,
                    "anchor_source": anchor_source,
                    "generated": True,
                    "review_source": "draft_only",
                    "generated_model": provenance["model"],
                    "generated_provider": provenance["provider"],
                },
            )
        )

    placed.sort(key=lambda item: (not item[1], item[0], item[2]["decision_id"]))
    by_cell: dict[str, list[dict[str, Any]]] = {}
    for cell_id, _placed_on_original, projection in placed:
        existing = by_cell.setdefault(cell_id, [])
        if any(_decisions_equivalent(item, projection) for item in existing):
            continue
        existing.append(projection)
    return by_cell, unplaceable


def _decision_metadata(micro: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(micro, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for key in ("decision_cells", "outcomes"):
        for item in micro.get(key, []) or []:
            if not isinstance(item, dict) or not item.get("decision_id"):
                continue
            result.setdefault(str(item["decision_id"]), dict(item))
    return result


def _decision_anchor(decision: dict[str, Any], metadata: dict[str, Any]) -> str:
    for value in (
        metadata.get("line_anchor"),
        decision.get("sets_node"),
        decision.get("decision_id"),
    ):
        match = re.search(r"(?:^|_)line_([0-9]+[a-z]?)$", str(value or "").lower())
        if match:
            return _normalize_anchor(match.group(1))
        match = re.search(r"_([0-9]+[a-z]?)_filer_election$", str(value or "").lower())
        if match:
            return _normalize_anchor(match.group(1))
    return ""


def _decision_subline_candidates(decision: dict[str, Any], original_anchor: str) -> list[str]:
    texts = [str(decision.get("question") or "")]
    texts.extend(
        str(value)
        for option in decision.get("options", []) or []
        if isinstance(option, dict)
        for value in (option.get("label"), option.get("downstream_effect"))
        if value
    )
    result: list[str] = []
    for text in texts:
        for match in re.finditer(r"(?<![0-9])[0-9]{1,2}[a-z](?![a-z0-9])", text, re.IGNORECASE):
            anchor = _normalize_anchor(match.group(0))
            if anchor != original_anchor and anchor not in result:
                result.append(anchor)
    return result


def _choose_decision_cell(matches: list[dict[str, Any]], target: str) -> dict[str, Any]:
    exact = [item for item in matches if str(item.get("node_id") or "") == target]
    if exact:
        return exact[0]
    checkbox = [
        item for item in matches
        if str(item.get("control_role") or "").lower() == "checkbox"
        or str(item.get("address_id") or "").endswith("/control=checkbox")
    ]
    return checkbox[0] if checkbox else matches[0]


def _decisions_equivalent(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_question = _question_key(left.get("question"))
    right_question = _question_key(right.get("question"))
    if left_question and left_question == right_question:
        return True
    return bool(_choice_topics(left) and _choice_topics(left) == _choice_topics(right))


def _question_key(value: Any) -> str:
    return " ".join(
        token
        for token in re.findall(r"[a-z0-9]+", str(value or "").lower())
        if not re.fullmatch(r"[0-9]+[a-z]?", token)
    )


def _choice_topics(decision: dict[str, Any]) -> frozenset[str]:
    topics: set[str] = set()
    for option in decision.get("options", []) or []:
        if not isinstance(option, dict) or option.get("option_type") != "choice":
            continue
        text = " ".join(
            str(value)
            for value in (option.get("label"), option.get("downstream_effect"))
            if value
        ).lower()
        if "income tax" in text or "income taxes" in text:
            topics.add("income_taxes")
        if "general sales tax" in text or "general sales taxes" in text:
            topics.add("general_sales_taxes")
    return frozenset(topics)


def _unplaceable_record(
    document_id: str,
    record: dict[str, Any],
    *,
    reason: str,
    provenance: dict[str, str],
    decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    anchor = _normalize_anchor(record.get("line_anchor"))
    question = " ".join(str(record.get("question") or "").split())
    label = " ".join(str(record.get("label") or "").split()) or question or anchor or "Unplaceable generated row"
    kind = str(record.get("response_kind") or record.get("kind") or record.get("source_kind") or "generated")
    return {
        "row_id": f"unplaceable_{document_id}_{anchor or 'form_level'}_{kind}",
        "document_id": document_id,
        "target_cell_id": str(record.get("target_cell_id") or ""),
        "line_anchor": anchor,
        "label": label,
        "kind": kind,
        "reason": reason,
        "question": question,
        "decision_id": str(record.get("decision_id") or ""),
        "decision": dict(decision) if decision else None,
        "placement": "form_level",
        "unplaceable": True,
        "generated": True,
        "review_source": "draft_only",
        "generated_model": provenance["model"],
        "generated_provider": provenance["provider"],
        "generated_provenance": dict(provenance),
    }


def _choose_cell(matches: list[dict[str, Any]], target: str) -> dict[str, Any]:
    exact = [item for item in matches if str(item.get("node_id") or "") == target]
    return exact[0] if exact else matches[0]


def _outcome_expression(
    outcome_kind: str,
    formula: dict[str, Any],
    outcome: dict[str, Any],
    target: str,
    target_cell: dict[str, Any],
    decision: dict[str, Any] | None,
) -> dict[str, Any]:
    """Project a model-owned terminal outcome without relabeling it as a gap."""
    target_ref = _normalize_anchor(target_cell.get("official_ref")) or _normalize_anchor(
        formula.get("line_anchor")
    )
    if outcome_kind == "filer_entry":
        form, line, box = _filer_entry_source(outcome, formula, target_ref)
        if form and (line or box):
            source_label = _source_label(
                "information_return" if box else "form_line",
                form,
                line,
                box,
            )
            return {
                "kind": "input",
                "text": f"line {target_ref} = {source_label}",
                "source": {"kind": "input", "text": source_label},
            }
        return {
            "kind": "input",
            "text": f"line {target_ref} = entered by filer",
            "source": {"kind": "input", "text": "entered by filer"},
        }
    if outcome_kind == "information_return":
        form = str(outcome.get("form") or formula.get("form") or "")
        box = str(outcome.get("box") or formula.get("box") or "")
        source_label = _source_label("information_return", form, "", box)
        return {
            "kind": "imported",
            "text": f"line {target_ref} = {source_label}",
            "source": {"kind": "imported", "text": source_label},
        }
    if outcome_kind == "election":
        question = str(
            outcome.get("question")
            or (decision or {}).get("question")
            or formula.get("label")
            or f"line {target_ref} requires a filer decision"
        )
        return {"kind": "reference", "text": question}
    if outcome_kind == "not_derivable":
        reason = str(
            outcome.get("reason")
            or formula.get("reason")
            or formula.get("review_gap")
            or "the supplied evidence is insufficient"
        )
        return {
            "kind": "review_gap",
            "text": f"line {target_ref} = not derivable",
            "reason": reason,
        }
    if outcome_kind == "computation":
        return _expression(target, formula, {}, [], [], target_cell)
    return {
        "kind": "review_gap",
        "text": f"line {target_ref} = unresolved",
        "reason": "generated outcome kind is not recognized",
    }


def _expression(
    target: str,
    formula: dict[str, Any],
    rule: dict[str, Any],
    edges: list[dict[str, Any]],
    cells: list[dict[str, Any]],
    target_cell: dict[str, Any],
) -> dict[str, Any]:
    operation = str(rule.get("operation") or "").upper()
    if not operation:
        return _source_expression(formula, target, target_cell)
    effective_edges = _effective_edges(operation, edges)
    target_ref = _normalize_anchor(target_cell.get("official_ref")) or _normalize_anchor(formula.get("line_anchor"))
    operand_records = [
        {
            "node_id": str(edge.get("source") or ""),
            "role": str(edge.get("role") or "") or None,
            "ref": _operand_label(str(edge.get("source") or ""), cells),
            "display_name": _operand_label(str(edge.get("source") or ""), cells),
        }
        for edge in effective_edges
        if edge.get("source")
    ]
    rendered = _render_expression(operation, target_ref, operand_records)
    expression: dict[str, Any] = {
        "kind": _expression_kind(operation),
        "operation": operation,
        "text": rendered,
        "operands": [
            {
                "kind": "reference",
                "label": item["ref"],
                "text": item["ref"],
                "ref": {"object_type": "node", "object_id": item["node_id"], "display_label": item["ref"]},
            }
            for item in operand_records
        ],
    }
    if formula.get("status") != "complete":
        expression["kind"] = "review_gap"
        expression["reason"] = str(formula.get("review_gap") or "generated expression is incomplete")
    return expression


def _source_expression(formula: dict[str, Any], target: str, target_cell: dict[str, Any]) -> dict[str, Any]:
    """Build a review expression for a non-computed source declaration."""
    source_kind = str(formula.get("source_kind") or "")
    form = str(formula.get("form") or "").strip()
    line = str(formula.get("line") or "").strip()
    box = str(formula.get("box") or "").strip()
    target_ref = _normalize_anchor(target_cell.get("official_ref")) or _normalize_anchor(formula.get("line_anchor"))
    if source_kind == "filer_entry":
        form, line, box = _filer_entry_source(formula, formula, target_ref)
        if form and (line or box):
            source_label = _source_label(
                "information_return" if box else "form_line",
                form,
                line,
                box,
            )
            return {
                "kind": "input" if formula.get("status") == "complete" else "review_gap",
                "text": f"line {target_ref} = {source_label}",
                "source": {"kind": "input", "text": source_label},
            }
        return {
            "kind": "input" if formula.get("status") == "complete" else "review_gap",
            "text": f"line {target_ref} = entered by filer",
            "source": {"kind": "input", "text": "entered by filer"},
        }
    if source_kind in {"form_line", "information_return"} and form and (
        _meaningful_reference(line) or _meaningful_reference(box)
    ):
        source_label = _source_label(source_kind, form, line, box)
        kind = "cross_form_fetch" if _compact(form) not in _compact(str(target_cell.get("document_id") or "")) else "copy"
        if formula.get("status") != "complete":
            kind = "review_gap"
        return {
            "kind": kind,
            "text": f"line {target_ref} = {source_label}",
            "source": {"kind": "reference", "label": source_label, "text": source_label},
        }
    return {
        "kind": "review_gap",
        "text": f"line {target_ref} = unresolved source",
        "reason": str(formula.get("review_gap") or "source declaration is unresolved"),
    }


def _ensure_line_review_records(records: list[dict[str, Any]], outline: Any, document_id: str) -> list[dict[str, Any]]:
    """Keep the generated review denominator complete when older drafts lack source records."""
    if document_id != "form_1040_2025" or not isinstance(outline, dict):
        return records
    seen = {_normalize_anchor(item.get("line_anchor")) for item in records}
    children = outline.get("children", []) or []
    for item in _outline_lines(children):
        if not isinstance(item, dict):
            continue
        if item.get("kind") != "line" or not item.get("line_anchor"):
            continue
        anchor = _normalize_anchor(item.get("line_anchor"))
        if not any(char.isdigit() for char in anchor) or anchor in seen:
            continue
        records.append(
            {
                "target_cell_id": f"{document_id}_root_line_{anchor}",
                "line_anchor": anchor,
                "label": str(item.get("label") or ""),
                "status": "review_gap",
                "review_gap": "non-computed source extraction has not been generated",
                "source_kind": None,
                "form": "",
                "line": "",
                "box": "",
                "quote": "",
                "instruction_span_ids": [],
            }
        )
        seen.add(anchor)
    return records


def _outline_lines(items: list[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        result.append(item)
        result.extend(_outline_lines(item.get("children", []) or []))
    return result


def _effective_edges(operation: str, edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply positional roles only to legacy generated records with missing roles."""
    defaults = {
        "COPY": ("source",),
        "SUBTRACT": ("minuend", "subtrahend"),
        "DIVIDE": ("numerator", "denominator"),
        "MULTIPLY": ("multiplicand", "multiplier"),
        "NEGATE": ("amount",),
        "REQUIRE_INPUT": ("input",),
    }.get(operation, ())
    result = []
    for index, edge in enumerate(edges):
        item = dict(edge)
        if defaults and (not item.get("role") or str(item.get("role")) == "addend") and index < len(defaults):
            item["role"] = defaults[index]
        result.append(item)
    return result


def _expression_kind(operation: str) -> str:
    return {"REQUIRE_INPUT": "input"}.get(operation, operation.lower())


def _render_expression(operation: str, target: str, operands: list[dict[str, Any]]) -> str:
    labels = [str(item.get("ref") or "unresolved source") for item in operands]
    by_role = {str(item.get("role")): label for item, label in zip(operands, labels, strict=False)}
    if operation == "COPY" and labels:
        return f"line {target} = {labels[0]}"
    if operation == "SUM" and labels:
        return f"line {target} = " + " + ".join(labels)
    if operation == "SUBTRACT" and {"minuend", "subtrahend"} <= set(by_role):
        return f"line {target} = {by_role['minuend']} - {by_role['subtrahend']}"
    if operation == "DIVIDE" and {"numerator", "denominator"} <= set(by_role):
        return f"line {target} = {by_role['numerator']} / {by_role['denominator']}"
    if operation == "REQUIRE_INPUT":
        return f"line {target} = entered by filer"
    if operation in {"MIN", "MAX"}:
        return f"line {target} = {operation.lower()}(" + ", ".join(labels) + ")"
    return f"line {target} = {operation.lower()}(" + ", ".join(labels) + ")"


def _operand_label(node_id: str, cells: list[dict[str, Any]]) -> str:
    match = next((cell for cell in cells if str(cell.get("node_id") or "") == node_id), None)
    if match:
        ref = _normalize_anchor(match.get("official_ref"))
        if ref:
            return f"line {ref}"
        name = str(match.get("display_name") or "").strip()
        if name:
            return name
    match = re.search(r"_line_([0-9]+[a-z]?)(?:_|$)", node_id.lower())
    return f"line {match.group(1)}" if match else node_id.replace("_", " ")


def _source_label(source_kind: str, form: str, line: str, box: str) -> str:
    form_label = "W-2" if _compact(form) in {"w2", "formw2"} else form.replace("_", " ").strip().title()
    if source_kind == "information_return" and box:
        return f"{form_label} box {box}"
    return f"{form_label}, line {line}" if line else form_label


def _filer_entry_source(
    outcome: dict[str, Any],
    formula: dict[str, Any],
    target_ref: str,
) -> tuple[str, str, str]:
    """Return named filer-input identity from structured model fields."""
    form = str(outcome.get("form") or formula.get("form") or "").strip()
    line = str(outcome.get("line") or formula.get("line") or "").strip()
    box = str(outcome.get("box") or formula.get("box") or "").strip()
    return form, line, box


def _meaningful_reference(value: str) -> bool:
    """Reject model sentinel strings before rendering a source reference."""
    return str(value or "").strip().lower() not in {"", "none", "null", "n/a", "unknown"}


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _span_citation(span: dict[str, Any]) -> dict[str, Any]:
    return {
        "citation_id": span.get("span_id"),
        "quoted_text": span.get("text"),
        "locator": span.get("locator"),
        "url": None,
        "retrieved_date": None,
        "source_document_id": span.get("document_id"),
        "resolved": True,
    }


def _background_index(micro: Any) -> dict[str, dict[str, Any]]:
    """Index draft-only background records by their code-resolved field name."""
    if not isinstance(micro, dict):
        return {}
    return {
        str(item.get("field_name")): dict(item)
        for item in micro.get("background_controls", []) or []
        if isinstance(item, dict) and item.get("field_name")
    }


def _projected_policy(
    base_cell: dict[str, Any],
    background: dict[str, Any] | None,
    inferred: str | None,
) -> str:
    """Keep authored policy authoritative; replace unsupported only with a draft result."""
    authored = str(base_cell.get("population_policy") or "")
    if authored and authored != "unsupported":
        return authored
    if background and str(background.get("population_policy") or "") != "unsupported":
        return str(background["population_policy"])
    return authored or inferred or "review_gap"


def _apply_background_overlay(
    cell: dict[str, Any],
    background: dict[str, Any] | None,
    spans: dict[str, dict[str, Any]],
) -> None:
    """Apply a generated policy only when the draft record is for this field."""
    if not background:
        return
    citations = _background_citations(background, spans)
    cell["form_citations"] = _merge_citations(cell.get("form_citations") or cell.get("citations"), citations[0])
    cell["instruction_citations"] = _merge_citations(cell.get("instruction_citations"), citations[1])
    cell["citations"] = cell["form_citations"]
    if str(background.get("population_policy") or "") == "unsupported":
        cell["policy_origin"] = "review_gap"
        cell["policy_basis"] = "unresolved"
        cell["policy_defaulted"] = False
        cell["policy_derived"] = False
        cell["failover_class"] = _background_value(background, "failover_class")
        return
    if str(cell.get("population_policy") or "") != str(background.get("population_policy")):
        cell["population_policy"] = str(background["population_policy"])
        cell["expression"] = _background_expression(
            str(cell.get("official_ref") or "control"),
            str(background["population_policy"]),
            str(background.get("review_gap") or ""),
            str(background.get("failover_class") or ""),
        )
        cell["operation"] = ""
        cell["inputs"] = []
    cell["policy_reason"] = str(background.get("reason") or "") or None
    cell["downstream_effect"] = None
    cell["missing_capability"] = None
    cell["generated_status"] = str(background.get("status") or "complete")
    cell["review_gap"] = str(background.get("review_gap") or "") or None
    cell["policy_origin"] = str(background.get("policy_origin") or "derived")
    cell["policy_basis"] = str(background.get("policy_basis") or "source_evidence")
    cell["policy_defaulted"] = _policy_bool(background, "policy_defaulted")
    cell["policy_derived"] = _policy_bool(background, "policy_derived")
    cell["failover_class"] = _background_value(background, "failover_class")


def _project_background_cell(
    base_cell: dict[str, Any],
    background: dict[str, Any] | None,
    spans: dict[str, dict[str, Any]],
    instruction_ids_by_line: dict[str, list[str]],
    *,
    provenance: dict[str, str],
) -> dict[str, Any]:
    """Project one physical cell that has no formula/source outline record.

    A physical cell can remain outside the generated outline while its printed
    line still has an owned instruction span. Prefer that span over the
    inventory citation copied into the base cell; the inventory may only carry
    a neighboring line label for a repeated form row.
    """
    cell = dict(base_cell)
    authored_policy = str(base_cell.get("population_policy") or "")
    policy = _projected_policy(base_cell, background, None)
    if background and str(background.get("population_policy") or "") != "unsupported":
        policy = str(background["population_policy"])
    review_gap = str((background or {}).get("review_gap") or "")
    if not review_gap and policy == "unsupported":
        review_gap = "background control policy has not been generated"
    expression = _background_expression(
        str(base_cell.get("official_ref") or "control"),
        policy,
        review_gap,
        str((background or {}).get("failover_class") or ""),
    )
    background_citations = _background_citations(background or {}, spans)
    instruction_citations = _background_instruction_citations(
        base_cell,
        spans,
        instruction_ids_by_line,
    )
    status = str((background or {}).get("status") or ("authored" if authored_policy and authored_policy != "unsupported" else "review_gap"))
    cell.update(
        {
            "generated": True,
            "review_source": "draft_only",
            "generated_target_cell_id": None,
            "generated_status": status,
            "generated_model": str((background or {}).get("model") or ("deterministic-authored-policy" if status == "authored" else provenance["model"])),
            "generated_provider": str((background or {}).get("provider") or ("Tax Graph" if status == "authored" else provenance["provider"])),
            "generated_provenance": (
                {"stage": "authored_policy_projection"}
                if status == "authored"
                else dict(provenance)
            ),
            "expression": expression,
            "operation": "",
            "inputs": [],
            "form_citations": _merge_citations(base_cell.get("citations"), background_citations[0]),
            "instruction_citations": _merge_citations(
                instruction_citations,
                background_citations[1],
            ),
            "review_gap": review_gap or None,
            "risk_bucket": _background_risk_bucket(expression),
            "population_policy": policy,
            "policy_origin": _policy_origin(base_cell, background, policy),
            "policy_basis": _policy_basis(base_cell, background),
            "policy_defaulted": _policy_bool(background, "policy_defaulted"),
            "policy_derived": _policy_bool(background, "policy_derived"),
            "failover_class": _background_value(background, "failover_class"),
        }
    )
    if background and policy != "unsupported":
        cell["policy_reason"] = str(background.get("reason") or "") or None
        cell["downstream_effect"] = None
        cell["missing_capability"] = None
    cell["citations"] = cell["form_citations"]
    return cell


def _background_instruction_citations(
    base_cell: dict[str, Any],
    spans: dict[str, dict[str, Any]],
    instruction_ids_by_line: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Prefer owned line spans when projecting an unrecorded physical cell."""
    anchor = _normalize_anchor(base_cell.get("official_ref"))
    existing = list(base_cell.get("instruction_citations") or [])
    if not any(_is_line_label_quote(item.get("quoted_text")) for item in existing):
        return existing
    span_ids = instruction_ids_by_line.get(anchor, [])
    projected = [
        _instruction_citation(str(span_id), span, anchor)
        for span_id in span_ids
        if (span := spans.get(str(span_id))) is not None
    ]
    if not projected:
        return existing
    existing = [
        item
        for item in existing
        if not _is_line_label_quote(item.get("quoted_text"))
    ]
    return [*projected, *existing]


def _is_line_label_quote(value: Any) -> bool:
    """Return whether a citation quote is only a printed line label."""
    return bool(re.fullmatch(r"\s*Line\s+[0-9]+[a-z]?\.\s*", str(value or ""), re.IGNORECASE))


def _background_expression(
    ref: str,
    policy: str,
    review_gap: str,
    failover_class: str = "",
) -> dict[str, Any]:
    if policy == "user_entered":
        text = _failover_text("entered by filer", failover_class)
        return {
            "kind": "input",
            "text": f"{ref} = {text}",
            "source": {"kind": "input", "text": text},
        }
    if policy == "decision_required":
        text = _failover_text("decision required", failover_class)
        return {
            "kind": "input",
            "text": f"{ref} = {text}",
            "source": {"kind": "input", "text": text},
        }
    if policy == "intentionally_blank":
        return {
            "kind": "input",
            "text": f"{ref} = intentionally blank",
            "source": {"kind": "input", "text": "intentionally blank"},
        }
    return {
        "kind": "review_gap",
        "text": f"{ref} = unresolved background policy",
        "reason": review_gap or "background control policy is unresolved",
    }


def _background_risk_bucket(expression: dict[str, Any]) -> str:
    try:
        return expression_kind_bucket(str(expression.get("kind") or "review_gap"))
    except ValueError:
        return "NOT_REVIEWABLE"


def _background_citations(
    background: dict[str, Any],
    spans: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    form: list[dict[str, Any]] = []
    instructions: list[dict[str, Any]] = []
    for span_id in background.get("citation_span_ids", []) or []:
        span = spans.get(str(span_id))
        if not span:
            continue
        citation = _span_citation(span)
        if str(span.get("relationship") or "") == "source":
            form.append(citation)
        else:
            instructions.append(citation)
    return form, instructions


def _background_value(background: dict[str, Any] | None, key: str) -> Any:
    return None if not background else background.get(key)


def _policy_bool(background: dict[str, Any] | None, key: str) -> bool:
    return bool(_background_value(background, key))


def _policy_origin(
    base_cell: dict[str, Any],
    background: dict[str, Any] | None,
    policy: str,
) -> str:
    if background and background.get("policy_origin"):
        return str(background["policy_origin"])
    authored = str(base_cell.get("population_policy") or "")
    if authored and authored != "unsupported":
        return "authored"
    return "review_gap" if policy in {"", "unsupported", "review_gap"} else "derived"


def _policy_basis(base_cell: dict[str, Any], background: dict[str, Any] | None) -> str:
    if background and background.get("policy_basis"):
        return str(background["policy_basis"])
    return "field_map" if str(base_cell.get("population_policy") or "") not in {"", "unsupported"} else "unresolved"


def _failover_text(default: str, failover_class: str) -> str:
    return {
        "filer_election": "filer decision (ask at intake)",
        "filer_identity_admin": "filer identity/admin (ask at intake)",
        "filer_supplied_value": "filer-supplied value (ask at intake)",
    }.get(failover_class, default)


def _merge_citations(
    existing: Any,
    additions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in [*(existing or []), *additions]:
        if not isinstance(item, dict):
            continue
        citation_id = str(item.get("citation_id") or "")
        if citation_id and citation_id in seen:
            continue
        if citation_id:
            seen.add(citation_id)
        result.append(dict(item))
    return result
