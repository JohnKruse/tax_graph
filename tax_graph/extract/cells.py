"""Pure cell derivation and deterministic expression-tree projection.

The cell frame is the narrow boundary between source joins and graph assembly.
``derive_cells`` calls a caller-supplied provider and returns a new frame; it
never writes drafts, graph files, logs, or review state.  A provider failure
is recorded on the affected row so one bad request cannot erase the rest of a
run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
import json
import re
from typing import Any, Iterable, Mapping, Protocol, Sequence

from tax_graph.config import get_config_value
from tax_graph.extract.llm_client import LlmClient, response_telemetry
from tax_graph.extract.prompts import load_prompt_template, render_prompt
from tax_graph.extract.structure import split_caption_and_instruction
from tax_graph.io.loader import load_yaml
from tax_graph.operation_registry import (
    OPERATION_SPECS,
    IF_ELSE_COMPARISONS,
    operation_names,
    operation_numeric_roles,
    operation_roles,
    operation_spec,
    predicate_operations,
    prompt_operation_documentation,
    projection_rule_for,
)


CELL_INPUT_FIELDS = (
    "form",
    "line",
    "label",
    "form_face_text",
    "instruction_text",
    "instruction_locator",
)


def get_structural_skip_reason(metadata: Mapping[str, Any]) -> str | None:
    """Return the structural skip reason, or ``None`` when the row is routable.

    Structural provenance is the only row-level routing input.  Formula cues
    are denominator telemetry and must never be reconstructed here from old
    metadata fields.
    """
    value = metadata.get("structural_skip_reason")
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise TypeError("structural_skip_reason must be a string or None")
    return value


class CellClientFactory(Protocol):
    """Build a provider client from the resolved API key."""

    def __call__(self, api_key: str) -> LlmClient:
        """Return a configured structured-completion client."""


@dataclass
class CellRecord:
    """One input or derived cell, kept JSON-compatible at the edges."""

    form: str
    line: str
    label: str = ""
    form_face_text: str = ""
    instruction_text: str = ""
    instruction_locator: str = ""
    canonical_address: str = ""
    human_comment: str = ""
    expression: dict[str, Any] | None = None
    rendered: str = ""
    quote: str = ""
    quote_span_id: str = ""
    status: str = "pending"
    error: str | None = None
    model: str | None = None
    provider: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CellRecord":
        """Build a record while preserving unknown source metadata."""
        missing = [key for key in CELL_INPUT_FIELDS if key not in value]
        if missing:
            raise ValueError(f"cell is missing required fields: {', '.join(missing)}")
        known = {
            "form",
            "line",
            "label",
            "form_face_text",
            "instruction_text",
            "instruction_locator",
            "canonical_address",
            "human_comment",
            "expression",
            "rendered",
            "quote",
            "quote_span_id",
            "status",
            "error",
            "model",
            "provider",
            "prompt_tokens",
            "completion_tokens",
            "cost",
            "metadata",
        }
        return cls(
            **{key: value.get(key, getattr(cls, key, "")) for key in CELL_INPUT_FIELDS},
            canonical_address=str(value.get("canonical_address") or ""),
            human_comment=str(value.get("human_comment") or ""),
            expression=value.get("expression"),
            rendered=str(value.get("rendered") or ""),
            quote=str(value.get("quote") or ""),
            quote_span_id=str(value.get("quote_span_id") or ""),
            status=str(value.get("status") or "pending"),
            error=value.get("error"),
            model=value.get("model"),
            provider=value.get("provider"),
            prompt_tokens=_optional_int(value.get("prompt_tokens")),
            completion_tokens=_optional_int(value.get("completion_tokens")),
            cost=_optional_float(value.get("cost")),
            metadata={
                key: item
                for key, item in value.items()
                if key not in known
            } | dict(value.get("metadata") or {}),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a stable JSON-ready row without serializing provider objects."""
        result = {
            "form": self.form,
            "line": self.line,
            "label": self.label,
            "form_face_text": self.form_face_text,
            "instruction_text": self.instruction_text,
            "instruction_locator": self.instruction_locator,
            "canonical_address": self.canonical_address,
            "human_comment": self.human_comment,
            "expression": self.expression,
            "rendered": self.rendered,
            "quote": self.quote,
            "quote_span_id": self.quote_span_id,
            "status": self.status,
            "error": self.error,
            "model": self.model,
            "provider": self.provider,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost": self.cost,
        }
        result.update(self.metadata)
        return result


@dataclass
class CellFrame:
    """A typed list of cell records with a small coverage report."""

    rows: list[CellRecord]
    validation: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_rows(cls, rows: Iterable[CellRecord | Mapping[str, Any]]) -> "CellFrame":
        """Normalize mappings at the frame boundary."""
        return cls([
            row if isinstance(row, CellRecord) else CellRecord.from_mapping(row)
            for row in rows
        ])

    @property
    def coverage(self) -> dict[str, int]:
        """Count row outcomes without turning failures into a run-level exception."""
        counts: dict[str, int] = {"total": len(self.rows)}
        for row in self.rows:
            counts[row.status] = counts.get(row.status, 0) + 1
        return counts

    def as_dicts(self) -> list[dict[str, Any]]:
        """Return rows for JSON/markdown consumers."""
        return [row.as_dict() for row in self.rows]

    @property
    def validation_report(self) -> dict[str, Any]:
        """Return validator and repair telemetry for this derivation run."""
        return dict(self.validation)


@dataclass(frozen=True)
class CellValidationIssue:
    """One deterministic property failure or warning for a cell."""

    kind: str
    message: str
    hard: bool = True

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-ready validation issue."""
        return {"kind": self.kind, "message": self.message, "hard": self.hard}


def load_cell_prompt(
    config: Mapping[str, Any] | None = None,
    *,
    root: str | Path | None = None,
) -> str:
    """Load the cell prompt from config, with one documented project default."""
    settings = dict(config or {})
    path = get_config_value(
        settings,
        "extraction.prompts.cells",
        "prompts/derive_cells.md",
    )
    return load_prompt_template(path, root=root)


def build_cell_frame_from_document(document: Any) -> CellFrame:
    """Build the real form-to-instruction input frame without calling a model.

    The frame producer owns the joins.  It combines the geometry-derived form
    outline with the explicit instruction_sections frame and carries both
    inventories into row metadata so ``derive_cells`` can validate them.
    """
    from tax_graph.extract.outline import (
        _flatten_outline_nodes,
        build_candidate_spans,
        build_instruction_sections_frame,
        build_outline_tree,
    )
    from tax_graph.extract.outline_pipeline import (
        _flatten_nodes,
        _skip_reason_for_anchor,
        _span_for_line,
    )
    from tax_graph.extract.instruction_ownership import (
        instruction_line_owners,
        instruction_span_ids_for_line,
    )

    outline = build_outline_tree(document)
    instruction_frame = build_instruction_sections_frame(document, outline=outline)
    spans = build_candidate_spans(document)
    instruction_owners = instruction_line_owners(spans)
    instruction_spans_by_id = {
        span.span_id: span
        for span in spans
        if span.relationship == "instructions" and span.section_id
    }
    printed_nodes = [
        node
        for node in _flatten_nodes(outline.children)
        if node.line_anchor
    ]
    anchor_counts: dict[str, int] = {}
    for node in printed_nodes:
        anchor = str(node.line_anchor).lower()
        anchor_counts[anchor] = anchor_counts.get(anchor, 0) + 1
    root_header_anchors = {
        str(node.line_anchor).lower()
        for node in printed_nodes
        if node.outline_id.startswith("root_line_")
        and anchor_counts.get(str(node.line_anchor).lower(), 0) > 1
    }
    printed_lines = sorted(
        {
            str(node.line_anchor).lower()
            for node in printed_nodes
            if node.line_anchor
        },
        key=_line_sort_key,
    )
    rows: list[CellRecord] = []
    for node in printed_nodes:
        line = str(node.line_anchor or "").lower()
        if not line:
            continue
        structural_skip_reason = _skip_reason_for_anchor(
            node,
            outline_anchor_count=anchor_counts.get(line, 0),
            root_header_present=line in root_header_anchors,
        )
        # Formula cues are historical telemetry only.  A structurally valid
        # printed line reaches the model even when its label contains no cue;
        # the model can then state REQUIRE_INPUT with its evidence.
        form_span = _span_for_line(document, node, spans)
        instruction_span_ids = instruction_span_ids_for_line(
            spans,
            line,
            owners=instruction_owners,
            owner_document_id=document.document_id,
        )
        selected_section_ids = {
            instruction_spans_by_id[span_id].section_id
            for span_id in instruction_span_ids
            if span_id in instruction_spans_by_id
            and instruction_spans_by_id[span_id].section_id
        }
        direct_sections = tuple(
            section
            for section in instruction_frame.sections
            if section.section_id in selected_section_ids and section.line == line
        )
        if direct_sections:
            sections = direct_sections
        else:
            parent_line = line[:-1] if re.fullmatch(r"[0-9]+[a-z]", line) else ""
            sections = tuple(
                section
                for section in instruction_frame.sections
                if section.section_id in selected_section_ids and section.line == parent_line
            )
        instruction_match = (
            "direct"
            if any(section.line == line for section in sections)
            else "inherited"
            if sections
            else "none"
        )
        instruction_text = "\n\n".join(section.text for section in sections)
        evidence_spans: list[dict[str, str]] = []
        full_form_face = ""
        extent_diagnostic: dict[str, Any] = {
            "method": "fallback",
            "bracket_available": False,
            "disagreement": None,
            "fallback_face": "",
            "bracket_face": "",
        }
        caption_split = split_caption_and_instruction(node.label, line)
        if form_span is not None:
            bracket_text = str(form_span.extent.get("bracket_text") or "")
            full_form_face, extent_diagnostic = clean_form_face_text_with_extent(
                form_span.text,
                line,
                bracket_text=bracket_text or None,
                allow_shorter_bracket=document.source_document_id is not None,
            )
            caption_split = split_caption_and_instruction(full_form_face, line)
            form_face_text = caption_split.cell_instruction or full_form_face
            evidence_findings = list(form_span.findings)
            table_finding = _table_anchor_boundary_finding(
                form_span.text,
                # The finding is about the raw source packet's unresolved
                # repeated anchor. It must not disappear merely because a
                # bounded alternative was selected for the displayed face.
                cleaned_text=form_span.text,
                line=line,
            )
            if table_finding is not None:
                evidence_findings.append(table_finding)
            evidence_spans.append(
                {
                    "span_id": form_span.span_id,
                    "text": form_face_text,
                }
            )
        else:
            full_form_face = clean_form_face_text(node.label, line)
            caption_split = split_caption_and_instruction(full_form_face, line)
            form_face_text = caption_split.cell_instruction or full_form_face
            extent_diagnostic["fallback_face"] = form_face_text
            evidence_findings = []
        evidence_spans.extend(
            {"span_id": section.section_id, "text": section.text}
            for section in sections
        )
        governed_notes = list(
            (document.fields or {})
            .get("governed_note_provenance", {})
            .get(line, [])
        )
        # Keep the row evidence span source-owned and clean. The separately
        # governed note remains available on the cell face for prior-year
        # operand checks and retains its citation provenance in metadata.
        for note in governed_notes:
            note_text = re.sub(
                r"^\s*\*{0,2}note\.\*{0,2}\s*",
                "",
                str(note.get("text") or ""),
                flags=re.IGNORECASE,
            ).strip()
            if note_text:
                form_face_text = f"{note_text} {form_face_text}".strip()
        rows.append(
            CellRecord(
                form=document.document_id,
                line=line,
                label=caption_split.caption or "",
                form_face_text=form_face_text,
                instruction_text=instruction_text,
                instruction_locator=sections[0].section_id if sections else "",
                metadata={
                    "instruction_owner_document_id": document.document_id,
                    "instruction_lines": [line],
                    "instruction_span_ids": [section.section_id for section in sections],
                    "instruction_match": instruction_match,
                    "instruction_inherited": instruction_match == "inherited",
                    "form_face_span_id": form_span.span_id if form_span is not None else "",
                    "form_face_before": form_span.text if form_span is not None else "",
                    "evidence_findings": evidence_findings,
                    "label_before": node.label,
                    "caption": caption_split.caption,
                    "caption_status": caption_split.status,
                    "caption_finding": caption_split.finding or "",
                    "cell_instruction_before_split": full_form_face,
                    "clause_extent": extent_diagnostic,
                    "printed_lines": printed_lines,
                    "evidence_spans": evidence_spans,
                    "outline_id": node.outline_id,
                    "outline_kind": node.kind,
                    "structural_skip_reason": structural_skip_reason or None,
                    "governed_note_provenance": list(
                        (document.fields or {})
                        .get("governed_note_provenance", {})
                        .get(line, [])
                    ),
                },
            )
        )
    return CellFrame(rows)


def _table_anchor_boundary_finding(
    raw_text: str,
    *,
    cleaned_text: str,
    line: str,
) -> dict[str, Any] | None:
    """Name a repeated-anchor table whose text boundary is unresolved.

    A printed anchor can recur inside a decimal or threshold table.  In that
    case the deterministic cleaner cannot prove which occurrence closes the
    cell, so the evidence must remain visible as a finding instead of being
    passed to derivation as if it were a clean cell packet.
    """
    value = " ".join(str(raw_text or "").split())
    anchor = str(line or "").strip()
    if not value or not anchor or value != " ".join(str(cleaned_text or "").split()):
        return None
    token = re.escape(anchor)
    if not re.search(rf"(?<!\w){token}\s+[A-Z](?!\w)", value):
        return None
    table_cue = re.search(
        r"\b(?:decimal|threshold|amount)\b.*\b(?:shown below|table|over amount)\b",
        value,
        flags=re.IGNORECASE,
    )
    if table_cue is None:
        return None
    return {
        "code": "table_anchor_boundary",
        "detail": f"printed anchor {anchor} recurs inside a table; cell boundary is unresolved",
        "field_name": "",
        "row_text": value,
    }


def derive_cells(
    frame: CellFrame | Sequence[CellRecord | Mapping[str, Any]],
    prompt: str,
    api_key: str | None,
    *,
    client: LlmClient | None = None,
    client_factory: CellClientFactory | None = None,
    model: str | None = None,
    provider: str = "configured-provider",
    operations: Sequence[str] | None = None,
    human_comments: Mapping[str, str] | None = None,
    max_depth: int = 3,
    max_tokens: int = 4000,
    temperature: float | None = None,
    seed: int | None = None,
    reference_inventory: Mapping[str, Any] | None = None,
) -> CellFrame | list[dict[str, Any]]:
    """Derive every cell independently and return a new frame.

    ``client`` is the provider-agnostic seam used by production callers and
    fixture tests.  ``client_factory`` can construct it from ``api_key`` when
    the caller owns provider configuration.  With neither supplied, rows are
    marked ``error`` rather than silently selecting a vendor or writing state.
    The default expression depth is three so the provider schema can express
    the nested rules present in the source forms.  A list input returns a list
    for compatibility with lightweight callers; a ``CellFrame`` input returns
    a ``CellFrame``.
    """
    input_is_frame = isinstance(frame, CellFrame)
    source = frame if input_is_frame else CellFrame.from_rows(frame)
    result_rows: list[CellRecord] = []
    report: dict[str, Any] = {
        "attempted": 0,
        "repaired": 0,
        "gapped": 0,
        "errored": 0,
        "instruction_sections_dropped": 0,
        "instruction_drops_by_kind": {},
        "validator_failures_by_kind": {},
        "validator_warnings_by_kind": {},
    }
    active_client = client
    client_error: str | None = None
    if active_client is None and client_factory is not None:
        if not api_key:
            client_error = "missing api key for configured cell provider"
        else:
            try:
                active_client = client_factory(api_key)
            except Exception as exc:  # noqa: BLE001 - row-level failure contract
                client_error = f"client construction failed: {type(exc).__name__}: {exc}"
    if active_client is None and client_error is None:
        client_error = (
            "no configured cell provider client; pass client or client_factory "
            "instead of selecting a provider implicitly"
        )

    allowed_operations = list(operations or DEFAULT_OPERATIONS)
    for original in source.rows:
        row = CellRecord.from_mapping(original.as_dict())
        structural_skip_reason = get_structural_skip_reason(row.metadata)
        if structural_skip_reason:
            row.status = "skipped"
            row.error = None
            result_rows.append(row)
            continue
        input_failures = validate_cell_input(row)
        instruction_drops = tuple(
            issue
            for issue in input_failures
            if issue.kind in {"instruction_wrong_owner", "instruction_wrong_line"}
        )
        if instruction_drops:
            _drop_instruction_evidence(row, instruction_drops, report)
            input_failures = tuple(issue for issue in input_failures if issue not in instruction_drops)
        if input_failures:
            _record_issues(report, input_failures)
            _mark_error(
                row,
                _format_issues(input_failures),
                provider=provider,
                model=model,
            )
            report["errored"] += 1
            row.metadata["validation_failures"] = [item.as_dict() for item in input_failures]
            result_rows.append(row)
            continue
        if client_error:
            _mark_error(row, client_error, provider=provider, model=model)
            report["errored"] += 1
            result_rows.append(row)
            continue
        report["attempted"] += 1
        schema = expression_schema(
            allowed_operations,
            depth=max_depth,
        )
        if human_comments is not None:
            address = row.canonical_address or str(row.metadata.get("canonical_address") or "")
            row.human_comment = str(
                human_comments.get(address, row.human_comment) or ""
            )
        rendered_prompt = _render_cell_prompt(
            prompt,
            row,
            reference_inventory=reference_inventory,
        )
        first_failure: tuple[CellValidationIssue, ...] = ()
        try:
            request: dict[str, Any] = {
                "prompt": rendered_prompt,
                "schema": schema,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "purpose": "tax_graph_cell_derivation",
            }
            if seed is not None:
                request["seed"] = seed
            response = active_client.structured_completion(**request)
        except Exception as exc:  # noqa: BLE001 - provider failures stay row-local
            _mark_error(row, f"{type(exc).__name__}: {exc}", provider=provider, model=model)
            report["errored"] += 1
            result_rows.append(row)
            continue

        try:
            payload = getattr(response, "payload", response)
            _keep_attempted_payload(row, payload, attempt="first")
            if not isinstance(payload, Mapping):
                raise ValueError("provider returned a non-object payload")
            _apply_payload(
                row,
                payload,
                max_depth=max_depth,
                provider=provider,
                model=model,
            )
            _record_external_inputs(row, row.expression, reference_inventory)
            first_failure = tuple(
                validate_cell_output(
                    row,
                    row.expression,
                    row.quote,
                    max_depth=max_depth,
                    reference_inventory=reference_inventory,
                )[0]
            )
            telemetry = response_telemetry(response)
            if telemetry is not None:
                row.provider = telemetry.resolved_provider or telemetry.provider
                row.model = telemetry.resolved_model or telemetry.requested_model
                row.prompt_tokens = telemetry.prompt_tokens
                row.completion_tokens = telemetry.completion_tokens
                row.cost = telemetry.cost
        except Exception as exc:  # noqa: BLE001 - one row must not fail the frame
            issue = _exception_issue(exc)
            if issue.kind == "quote_span":
                _mark_error(row, f"{type(exc).__name__}: {exc}", provider=provider, model=model)
                report["errored"] += 1
                row.metadata["validation_failures"] = [issue.as_dict()]
                result_rows.append(row)
                continue
            first_failure = (issue,)

        if not first_failure:
            _record_warnings(
                report,
                row,
                max_depth=max_depth,
                reference_inventory=reference_inventory,
            )
            result_rows.append(row)
            continue

        _record_issues(report, first_failure)
        row.metadata["validation_failures"] = [item.as_dict() for item in first_failure]
        repair_prompt = _repair_prompt(rendered_prompt, row, first_failure)
        try:
            request = {
                "prompt": repair_prompt,
                "schema": schema,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "purpose": "tax_graph_cell_derivation_repair",
            }
            if seed is not None:
                request["seed"] = seed
            response = active_client.structured_completion(**request)
            payload = getattr(response, "payload", response)
            _keep_attempted_payload(row, payload, attempt="repair")
            if not isinstance(payload, Mapping):
                raise ValueError("provider returned a non-object payload")
            _apply_payload(
                row,
                payload,
                max_depth=max_depth,
                provider=provider,
                model=model,
            )
            _record_external_inputs(row, row.expression, reference_inventory)
            second_failures, _warnings = validate_cell_output(
                row,
                row.expression,
                row.quote,
                max_depth=max_depth,
                reference_inventory=reference_inventory,
            )
            if second_failures:
                _record_issues(report, second_failures)
                _mark_gap(row, second_failures, provider=provider, model=model)
                report["gapped"] += 1
                row.metadata["validation_failures"] = [item.as_dict() for item in second_failures]
            else:
                row.status = "repaired"
                row.metadata["repaired_after"] = [item.kind for item in first_failure]
                report["repaired"] += 1
            _record_warnings(
                report,
                row,
                max_depth=max_depth,
                reference_inventory=reference_inventory,
            )
        except Exception as exc:  # noqa: BLE001 - second failure is a named gap
            issue = _exception_issue(exc)
            _record_issues(report, (issue,))
            _mark_gap(row, (issue,), provider=provider, model=model)
            report["gapped"] += 1
            row.metadata["validation_failures"] = [issue.as_dict()]
        result_rows.append(row)

    output = CellFrame(result_rows, validation=report)
    return output if input_is_frame else output.as_dicts()


def _apply_payload(
    row: CellRecord,
    payload: Mapping[str, Any],
    *,
    max_depth: int,
    provider: str,
    model: str | None,
) -> None:
    expression = payload.get("expression")
    quote = payload.get("quote")
    validate_expression_tree(expression, max_depth=max_depth)
    if not isinstance(quote, str) or not quote.strip():
        raise ValueError("quote must be a non-empty string")
    known_spans = _known_quote_spans(row, quote)
    if not known_spans:
        raise ValueError("quote is not verbatim from the cell evidence")
    # Source identity is resolved from the verbatim match in code.  The model
    # must not select an id: asking it to do so makes a valid quote and a valid
    # source id independently satisfiable, even when they disagree.
    quote_span_id = known_spans[0][0]
    row.expression = dict(expression)
    row.metadata["model_outcome"] = (
        "model_stated_input"
        if str(expression.get("op") or "").upper() == "REQUIRE_INPUT"
        else "model_stated_expression"
    )
    row.rendered = render(expression)
    row.quote = quote
    row.quote_span_id = quote_span_id
    row.status = "derived"
    row.error = None
    row.provider = provider
    row.model = model


def validate_cell_input(row: CellRecord) -> tuple[CellValidationIssue, ...]:
    """Validate the source-side contracts before asking the provider.

    Real frames carry explicit owner metadata.  Older fixture frames only carry
    the locator and source text, so the metadata checks are conditional to keep
    that compatibility surface while still rejecting an explicit wrong owner.
    """
    issues: list[CellValidationIssue] = []
    metadata = row.metadata
    if not row.label.strip() and row.metadata.get("caption_status") not in {"none", "ambiguous"}:
        issues.append(CellValidationIssue("missing_label", "cell label is required"))
    if not row.form_face_text.strip() and not row.instruction_text.strip():
        issues.append(CellValidationIssue("missing_evidence", "at least one cited evidence source is required"))
    evidence_findings = metadata.get("evidence_findings") or []
    if evidence_findings:
        details = "; ".join(
            str(item.get("detail") or item.get("code") or "evidence finding")
            for item in evidence_findings
            if isinstance(item, Mapping)
        )
        issues.append(
            CellValidationIssue(
                "incomplete_evidence",
                f"form-face evidence packet is not complete: {details}",
            )
        )
    owner = metadata.get("instruction_owner_document_id") or metadata.get("instruction_document_id")
    if owner and str(owner) != row.form:
        issues.append(
            CellValidationIssue(
                "instruction_wrong_owner",
                f"instruction evidence belongs to {owner}, not {row.form}",
            )
        )
    owner_lines = metadata.get("instruction_lines") or metadata.get("instruction_line")
    if owner_lines:
        if isinstance(owner_lines, str):
            owner_lines = (owner_lines,)
        normalized = {str(value).strip().lower() for value in owner_lines}
        if row.line.strip().lower() not in normalized:
            issues.append(
                CellValidationIssue(
                    "instruction_wrong_line",
                    f"instruction evidence is for line(s) {sorted(normalized)}, not line {row.line}",
                )
            )
    if row.instruction_text.strip() and not row.instruction_locator.strip() and not metadata.get("evidence_spans"):
        issues.append(CellValidationIssue("missing_instruction_locator", "instruction evidence has no locator"))
    return tuple(issues)


def _clean_form_face_text_fallback(text: str, line: str) -> str:
    """Apply the existing local geometry cleanup without a printed bracket."""
    value = " ".join(str(text or "").split())
    anchor = str(line or "").strip()
    if not value or not anchor:
        return value
    token = re.compile(rf"(?<!\w){re.escape(anchor)}(?!\w)", re.IGNORECASE)
    matches = list(token.finditer(value))
    if not matches:
        return value

    suffix = anchor[-1:] if anchor[-1:].isalpha() else ""
    descriptive = [match for match in matches if value[match.end():].strip()]
    if descriptive:
        cleaned = value[descriptive[0].start():].strip()
        return re.sub(rf"\s+{re.escape(anchor)}$", "", cleaned, flags=re.IGNORECASE).strip()

    final = matches[-1]
    preceding = value[:final.start()].strip()
    if suffix and re.match(rf"{re.escape(suffix)}(?=\s|$)", preceding, re.IGNORECASE):
        preceding = preceding[len(suffix):].strip()
    return preceding


def clean_form_face_text(text: str, line: str) -> str:
    """Remove neighboring geometry text without changing source token order.

    This is the stable fallback used by synthetic inputs and by rows without
    a printed start/end bracket. Acquired forms pass the bracket alternative
    through ``clean_form_face_text_with_extent`` below.
    """
    return _clean_form_face_text_fallback(text, line)


def clean_form_face_text_with_extent(
    text: str,
    line: str,
    *,
    bracket_text: str | None = None,
    allow_shorter_bracket: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Select a printed-bracket clause for weak or bounded faces.

    The fallback remains authoritative for a useful existing face. The
    bracket is compared after caption/instruction projection so diagnostics
    describe exactly what the derivation model receives. A bracket is also
    preferred when the fallback is a strict substring of it, because that
    retains every fallback word while recovering the surrounding clause. It
    is also preferred when it is a strict substring of the fallback, but only
    when the caller has proved that the bracket builder is authoritative for
    this source kind. Region documents use the promoted citation layout and
    may opt in; acquired forms keep the fallback until their extent builder
    has the same provenance guarantee. Both candidates remain in the row
    metadata for human review and later measurement.
    """
    return _select_form_face_text_with_extent(
        text,
        line,
        bracket_text=bracket_text,
        prefer_shorter_bracket=allow_shorter_bracket,
        clean_bracket=not allow_shorter_bracket,
    )


def compare_form_face_text_with_extent(
    text: str,
    line: str,
    *,
    bracket_text: str | None = None,
    allow_shorter_bracket: bool = False,
) -> dict[str, Any]:
    """Compare the legacy and bounded face selections for one source row.

    This is a deterministic measurement seam for a producer change. The
    legacy result keeps the fallback unless the bracket is longer or contains
    it; the bounded result additionally trusts a shorter bracket when the
    fallback strictly contains it. No source text is authored or changed by
    this comparison. ``allow_shorter_bracket`` mirrors the production policy
    so the measurement reports the same source-kind boundary decision.
    """
    before, before_diagnostic = _select_form_face_text_with_extent(
        text,
        line,
        bracket_text=bracket_text,
        prefer_shorter_bracket=False,
        clean_bracket=True,
    )
    after, after_diagnostic = _select_form_face_text_with_extent(
        text,
        line,
        bracket_text=bracket_text,
        prefer_shorter_bracket=allow_shorter_bracket,
        clean_bracket=not allow_shorter_bracket,
    )
    return {
        "before": before,
        "after": after,
        "before_face": before_diagnostic["selected_face"],
        "after_face": after_diagnostic["selected_face"],
        "changed": before != after,
        "before_diagnostic": before_diagnostic,
        "after_diagnostic": after_diagnostic,
    }


def _select_form_face_text_with_extent(
    text: str,
    line: str,
    *,
    bracket_text: str | None,
    prefer_shorter_bracket: bool,
    clean_bracket: bool,
) -> tuple[str, dict[str, Any]]:
    """Apply one face-selection policy and retain both source candidates."""
    fallback = _clean_form_face_text_fallback(text, line)
    fallback_face = _cell_face_text(fallback, line)
    # The outline pipeline already bounded this candidate between printed
    # anchors. Running the anchor cleaner over it again can mistake a
    # legitimate reference such as "line 4" in a Note block for this row's
    # printed anchor.
    bracket = (
        _clean_form_face_text_fallback(bracket_text, line)
        if clean_bracket and bracket_text
        else " ".join(str(bracket_text or "").split()) if bracket_text else ""
    )
    bracket_face = _cell_face_text(bracket, line) if bracket else ""
    fallback_is_strict_substring = _is_strict_face_substring(fallback_face, bracket_face)
    bracket_is_strict_substring = _is_strict_face_substring(bracket_face, fallback_face)
    disagreement: str | None = None
    if bracket_face and fallback_face != bracket_face:
        disagreement = (
            "bracket_longer"
            if len(bracket_face) > len(fallback_face)
            else "fallback_longer"
        )
    use_bracket = bool(
        bracket
        and bracket_face
        and (
            (
                _weak_cell_face(fallback_face)
                and len(bracket_face) >= len(fallback_face)
            )
            or fallback_is_strict_substring
            or (
                prefer_shorter_bracket
                and bracket_is_strict_substring
                and not _weak_cell_face(bracket_face)
            )
        )
    )
    selected = bracket if use_bracket else fallback
    if use_bracket and fallback_is_strict_substring:
        selection_reason = "fallback_strict_substring"
    elif use_bracket and bracket_is_strict_substring:
        selection_reason = "bracket_strict_substring"
    elif use_bracket:
        selection_reason = "weak_fallback"
    else:
        selection_reason = "fallback"
    return selected, {
        "method": "bracket" if use_bracket else "fallback",
        "selection_reason": selection_reason,
        "bracket_available": bool(bracket),
        "disagreement": disagreement,
        "fallback_face": fallback_face,
        "bracket_face": bracket_face,
        "bracket_text": bracket,
        "selected_face": _cell_face_text(selected, line),
        "bracket_is_strict_substring": bracket_is_strict_substring,
    }


def _cell_face_text(value: str, line: str) -> str:
    split = split_caption_and_instruction(value, line)
    return split.cell_instruction or _clean_form_face_text_fallback(value, line)


def _weak_cell_face(value: str) -> bool:
    normalized = " ".join(str(value or "").split()).strip().lower()
    if not normalized:
        return True
    if normalized in {
        "( )",
        "()",
        ":",
        ': "',
        '"',
        "years",
        "instructions",
        "instructions.",
    }:
        return True
    return normalized.startswith("attach form") or normalized.startswith("form ")


def _is_strict_face_substring(needle: str, haystack: str) -> bool:
    """Return whether a non-empty fallback is strictly contained in a bracket face."""
    normalized_needle = " ".join(str(needle or "").split()).strip().casefold()
    normalized_haystack = " ".join(str(haystack or "").split()).strip().casefold()
    return bool(
        normalized_needle
        and normalized_haystack
        and normalized_needle != normalized_haystack
        and normalized_needle in normalized_haystack
    )


def _drop_instruction_evidence(
    row: CellRecord,
    issues: Sequence[CellValidationIssue],
    report: dict[str, Any],
) -> None:
    """Drop doubtful instruction sections while retaining form-face evidence."""
    prior_locator = row.instruction_locator
    if not row.metadata.get("form_face_span_id") and prior_locator:
        row.metadata["form_face_span_id"] = prior_locator
    dropped = row.metadata.setdefault("dropped_instruction_sections", [])
    if not isinstance(dropped, list):
        dropped = []
        row.metadata["dropped_instruction_sections"] = dropped
    dropped.extend(issue.as_dict() for issue in issues)
    row.metadata["instruction_text_before_drop"] = row.instruction_text
    row.instruction_text = ""
    row.instruction_locator = ""

    span_ids = row.metadata.get("instruction_span_ids") or ()
    if isinstance(span_ids, str):
        span_ids = (span_ids,)
    span_ids = {str(value) for value in span_ids if str(value)}
    if prior_locator:
        span_ids.add(str(prior_locator))
    evidence_spans = row.metadata.get("evidence_spans") or ()
    if isinstance(evidence_spans, Mapping):
        evidence_spans = (evidence_spans,)
    row.metadata["evidence_spans"] = [
        dict(item)
        for item in evidence_spans
        if isinstance(item, Mapping) and str(item.get("span_id") or "") not in span_ids
    ]
    report["instruction_sections_dropped"] += len(issues)
    counts = report["instruction_drops_by_kind"]
    for issue in issues:
        counts[issue.kind] = counts.get(issue.kind, 0) + 1


def validate_cell_output(
    row: CellRecord,
    expression: Mapping[str, Any] | None,
    quote: str,
    *,
    max_depth: int = 2,
    reference_inventory: Mapping[str, Any] | None = None,
) -> tuple[tuple[CellValidationIssue, ...], tuple[CellValidationIssue, ...]]:
    """Validate output properties and return hard failures plus warnings.

    These checks are deliberately source- and expression-based.  They do not
    consult promoted graph artifacts, and the operand-in-quote check is only a
    warning because a concise quote can legitimately omit an operand that the
    instruction still establishes elsewhere in the packet.  Source-backed
    operands require a numeric printed-line address; a table column is carried
    separately so a phrase such as ``2a, column (l)`` becomes line ``2a`` and
    column ``l`` before graph projection.
    """
    hard: list[CellValidationIssue] = []
    warnings: list[CellValidationIssue] = []
    if expression is None:
        return (CellValidationIssue("missing_expression", "provider returned no expression"),), ()
    try:
        validate_expression_tree(expression, max_depth=max_depth)
    except ValueError as exc:
        return (_exception_issue(exc),), ()

    operands = list(_expression_operands(expression))
    is_require_input = str(expression.get("op") or "").upper() == "REQUIRE_INPUT"
    current_form = row.form.strip().lower()
    current_line = row.line.strip().lower()
    available_lines = _available_lines(row)
    inventory = reference_inventory
    if inventory is None and isinstance(row.metadata.get("reference_inventory"), Mapping):
        inventory = row.metadata["reference_inventory"]
    reference_documents = _reference_document_ids(inventory)
    reference_node_ids = _reference_node_ids(inventory)
    direct_require_input_args = _node_args(expression) if is_require_input else []
    require_input_self = (
        is_require_input
        and len(direct_require_input_args) == 1
        and "line" in direct_require_input_args[0]
        and _operand_line(direct_require_input_args[0]) == current_line
        and (
            not direct_require_input_args[0].get("form")
            or str(direct_require_input_args[0].get("form")).strip().lower() == current_form
        )
    )
    if is_require_input:
        for reference in _form_face_source_references(row):
            hard.append(
                CellValidationIssue(
                    "external_reference_as_input",
                    f"form face cites {reference}; REQUIRE_INPUT is reserved for filer-supplied values",
                )
            )
    for operand in operands:
        operand_node = str(operand.get("node") or "").strip()
        operand_form = str(operand.get("form") or "").strip().lower()
        operand_line = str(operand.get("line") or "").strip().lower()
        if operand_node:
            if reference_node_ids is None:
                hard.append(
                    CellValidationIssue(
                        "operand_inventory_unavailable",
                        f"cannot validate graph node operand {operand_node} without a graph node inventory",
                    )
                )
            elif operand_node not in reference_node_ids:
                hard.append(
                    CellValidationIssue(
                        "operand_node_not_found",
                        f"graph node operand {operand_node} is not present in the graph",
                    )
                )
            continue
        if not operand_line:
            continue
        # Keep the existing unknown-document finding for an unsourced operand.
        # A non-canonical line is the more useful finding once the evidence
        # proves which external document the model intended to use.  An
        # explicitly qualified operand for the current form is source-backed
        # by its owner even when the row text does not repeat the form name.
        if (
            not re.fullmatch(r"[0-9]+[a-z]?", operand_line, re.IGNORECASE)
            and (
                not operand_form
                or operand_form == current_form
                or _legitimate_external_reference(
                    row,
                    operand_form,
                    operand_line,
                    reference_documents=reference_documents,
                )
            )
        ):
            hard.append(
                CellValidationIssue(
                    "operand_line_not_canonical",
                    f"operand line {operand_line!r} is not a canonical line address; "
                    "expected [0-9]+[a-z]?",
                )
            )
        is_require_input_self_operand = require_input_self and operand is direct_require_input_args[0]
        if not is_require_input_self_operand and not operand_form and operand_line == current_line:
            hard.append(CellValidationIssue("self_reference", f"expression references its own line {row.line}"))
        if not is_require_input_self_operand and operand_form and operand_form == current_form and operand_line == current_line:
            hard.append(CellValidationIssue("self_reference", f"expression references its own line {row.line}"))
        if not operand_form and available_lines and operand_line not in available_lines:
            hard.append(
                CellValidationIssue(
                    "operand_not_printed",
                    f"line {operand_line} is not a printed line on {row.form}",
                )
            )
        if operand_form:
            if _is_instruction_document_id(operand_form):
                hard.append(
                    CellValidationIssue(
                        "instructions_document_operand",
                        f"instructions document {operand_form} cannot be a graph operand",
                    )
                )
            elif reference_documents is None:
                hard.append(
                    CellValidationIssue(
                        "operand_inventory_unavailable",
                        f"cannot validate {operand_form} line {operand_line} without a document inventory",
                    )
                )
            elif operand_form not in reference_documents:
                prior_document = _prior_year_document_match(
                    operand_form,
                    reference_documents,
                    current_document_id=current_form,
                )
                if prior_document is not None:
                    if _prior_year_reference_is_source_backed(
                        row,
                        operand_form,
                        reference_documents,
                    ):
                        warnings.append(
                            CellValidationIssue(
                                "prior_year_reference",
                                f"{operand_form} line {operand_line} is supplied from the prior-year document "
                                f"{prior_document}; the prior-year value is an input",
                                hard=False,
                            )
                        )
                    else:
                        hard.append(
                            CellValidationIssue(
                                "operand_document_not_found",
                                f"cross-form operand names unknown document {operand_form}",
                            )
                        )
                else:
                    issue = CellValidationIssue(
                        "unresolved_external_reference",
                        f"cross-form operand names document {operand_form} line {operand_line} outside the document inventory",
                        hard=False,
                    )
                    if _legitimate_external_reference(
                        row,
                        operand_form,
                        operand_line,
                        reference_documents=reference_documents,
                    ):
                        warnings.append(issue)
                    else:
                        hard.append(
                            CellValidationIssue(
                                "operand_document_not_found",
                                f"cross-form operand names unknown document {operand_form}",
                            )
                        )
            else:
                cross_form_lines = _reference_lines(inventory, operand_form)
                if cross_form_lines is None:
                    hard.append(
                        CellValidationIssue(
                            "operand_inventory_unavailable",
                            f"cannot validate printed lines for {operand_form}",
                        )
                    )
                elif operand_line not in cross_form_lines:
                    hard.append(
                        CellValidationIssue(
                            "operand_not_printed",
                            f"line {operand_line} is not a printed line on {operand_form}",
                        )
                    )
        if not is_require_input_self_operand and not operand_form and not _line_mentioned(quote, operand_line):
            warnings.append(
                CellValidationIssue(
                    "operand_not_in_quote",
                    f"line {operand_line} is not mentioned in the selected quote",
                    hard=False,
                )
            )
        if not is_require_input_self_operand and operand_form and not _line_mentioned(quote, operand_line):
            warnings.append(
                CellValidationIssue(
                    "operand_not_in_quote",
                    f"{operand_form} line {operand_line} is not mentioned in the selected quote",
                    hard=False,
                )
            )

    type_issues, undetermined_nodes = _numeric_operand_type_issues(
        expression,
        inventory,
    )
    hard.extend(type_issues)
    if undetermined_nodes:
        row.metadata["operand_type_undetermined_nodes"] = sorted(undetermined_nodes)
    else:
        row.metadata.pop("operand_type_undetermined_nodes", None)

    lookup_evidence = _lookup_evidence_text(row)
    if lookup_evidence:
        for expression_node in _expression_nodes(expression):
            if str(expression_node.get("op") or "").upper() != "LOOKUP_TABLE":
                continue
            hard.extend(
                validate_lookup_table_completeness(
                    expression_node,
                    lookup_evidence,
                )
            )

    evidence = " ".join((row.form_face_text, row.instruction_text, _evidence_span_text(row))).lower()
    subtract_match = re.search(
        r"subtract\s+(?:line\s+)?([0-9]+[a-z]?)\s+from\s+(?:line\s+)?([0-9]+[a-z]?)",
        evidence,
        re.IGNORECASE,
    )
    if subtract_match:
        expected_left = subtract_match.group(2).lower()
        expected_right = subtract_match.group(1).lower()
        subtract_nodes = [node for node in _expression_nodes(expression) if str(node.get("op", "")).upper() == "SUBTRACT"]
        if not any(
            _operand_line(args[0]) == expected_left and _operand_line(args[1]) == expected_right
            for args in (_node_args(node) for node in subtract_nodes)
            if len(args) == 2
        ):
            hard.append(
                CellValidationIssue(
                    "subtract_direction",
                    f"instruction says subtract line {expected_right} from line {expected_left}",
                )
            )

    normalized_evidence = re.sub(r"\s+", " ", evidence)
    if re.search(r"if zero or less,? enter\s+-?0-", normalized_evidence, re.IGNORECASE):
        has_zero_floor = any(
            str(node.get("op", "")).upper() == "MAX"
            and any(
                _is_zero_floor_operand(arg, inventory)
                for arg in _node_args(node)
            )
            for node in _expression_nodes(expression)
        )
        if not has_zero_floor:
            hard.append(
                CellValidationIssue(
                    "missing_floor",
                    "evidence requires MAX(expression, 0) for the zero-or-less rule",
                )
            )
    warnings.extend(_projection_warnings(row, expression, max_depth=max_depth))
    return tuple(_unique_issues(hard)), tuple(_unique_issues(warnings))


def _expression_nodes(node: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield every expression node, including the root."""
    if "op" not in node:
        return
    yield node
    for arg in _node_args(node):
        if isinstance(arg, Mapping):
            yield from _expression_nodes(arg)


def _expression_operands(node: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield every leaf operand, including graph-node references."""
    if "op" not in node:
        yield node
        return
    for arg in _node_args(node):
        if isinstance(arg, Mapping):
            yield from _expression_operands(arg)


def _node_args(node: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return expression arguments that are mappings."""
    return [arg for arg in node.get("args", []) if isinstance(arg, Mapping)]


_LOOKUP_BAND_RE = re.compile(
    r"(?<![\w.])\$?\s*(?P<lower>\d[\d,]*(?:\.\d+)?)\s*"
    r"(?:-|\u2013|\u2014)\s*"
    r"(?P<upper>\$?\s*\d[\d,]*(?:\.\d+)?|no\s+limit|unlimited)"
    r"(?![\w.])",
    re.IGNORECASE,
)


def validate_lookup_table_completeness(
    expression: Mapping[str, Any],
    evidence_text: str,
) -> tuple[CellValidationIssue, ...]:
    """Fail closed when a banded lookup cannot be matched to its source table.

    A lookup with at least two printed numeric bands is treated as a decision
    table.  Every source band must have a corresponding numeric range in a
    branch role.  This validator never fills a missing range or infers one;
    it only reports source gaps, overlaps, omissions, and unverifiable bounds.
    Non-banded lookups, such as filing-status selections, are outside this
    check and remain governed by the named-role grammar.
    """
    source_bands = _source_lookup_bands(evidence_text)
    if len(source_bands) < 2:
        return ()

    issues: list[CellValidationIssue] = []
    source_issues = _band_continuity_issues(source_bands, source="source")
    issues.extend(source_issues)

    expression_bands: list[tuple[Decimal, Decimal | None]] = []
    unverifiable_roles: list[str] = []
    for operand in expression.get("args") or ():
        if not isinstance(operand, Mapping) or operand.get("role") == "key":
            continue
        role = str(operand.get("role") or "").strip().lower()
        band = _band_from_role(role)
        if band is None:
            unverifiable_roles.append(role or "<missing>")
        else:
            expression_bands.append(band)

    if unverifiable_roles:
        issues.append(
            CellValidationIssue(
                "lookup_table_bounds_unverifiable",
                "LOOKUP_TABLE source has numeric bands but these branch roles do not "
                f"state bounds: {', '.join(unverifiable_roles)}",
            )
        )
        return tuple(_unique_issues(issues))

    if len(expression_bands) != len(source_bands):
        issues.append(
            CellValidationIssue(
                "lookup_table_incomplete",
                "LOOKUP_TABLE has "
                f"{len(expression_bands)} branch bands but the source has "
                f"{len(source_bands)}; no missing band may be inferred",
            )
        )

    issues.extend(_band_continuity_issues(expression_bands, source="expression"))
    source_set = set(source_bands)
    expression_set = set(expression_bands)
    missing = sorted(source_set - expression_set, key=_band_sort_key)
    unexpected = sorted(expression_set - source_set, key=_band_sort_key)
    if missing:
        issues.append(
            CellValidationIssue(
                "lookup_table_missing_bands",
                "LOOKUP_TABLE is missing source bands: "
                + ", ".join(_format_band(band) for band in missing),
            )
        )
    if unexpected:
        issues.append(
            CellValidationIssue(
                "lookup_table_bounds_mismatch",
                "LOOKUP_TABLE contains bounds not present in the source: "
                + ", ".join(_format_band(band) for band in unexpected),
            )
        )
    return tuple(_unique_issues(issues))


def _lookup_evidence_text(row: CellRecord) -> str:
    """Choose the preferred row-scoped evidence source that contains a table."""
    candidates = (
        row.form_face_text,
        row.instruction_text,
        _evidence_span_text(row),
        row.quote,
    )
    for candidate in candidates:
        if len(_source_lookup_bands(candidate)) >= 2:
            return candidate
    return ""


def _source_lookup_bands(text: str) -> list[tuple[Decimal, Decimal | None]]:
    """Extract and deduplicate numeric bands from one source passage."""
    bands = []
    for match in _LOOKUP_BAND_RE.finditer(str(text or "")):
        lower = _decimal_token(match.group("lower"))
        upper_text = re.sub(r"\s+", " ", match.group("upper")).strip().lower()
        upper = None if upper_text in {"no limit", "unlimited"} else _decimal_token(upper_text)
        if lower is not None and (upper is None or upper > lower):
            bands.append((lower, upper))
    return sorted(set(bands), key=_band_sort_key)


def _band_from_role(role: str) -> tuple[Decimal, Decimal | None] | None:
    """Read a range role such as ``band_15000_to_17000``."""
    normalized = re.sub(r"^(?:band|range|from)_", "", role)
    numbers = [Decimal(value) for value in re.findall(r"\d+(?:\.\d+)?", normalized)]
    if "no_limit" in normalized or "unlimited" in normalized:
        if len(numbers) != 1:
            return None
        return numbers[0], None
    if normalized.startswith("under_") and len(numbers) == 1:
        return Decimal("0"), numbers[0]
    if normalized.startswith("over_") and len(numbers) == 1:
        return numbers[0], None
    if len(numbers) != 2:
        return None
    lower, upper = numbers
    return (lower, upper) if upper > lower else None


def _decimal_token(value: str) -> Decimal | None:
    """Parse a source amount without accepting malformed numeric text."""
    try:
        return Decimal(re.sub(r"[$,\s]", "", str(value)))
    except (InvalidOperation, ValueError):
        return None


def _band_continuity_issues(
    bands: Sequence[tuple[Decimal, Decimal | None]],
    *,
    source: str,
) -> list[CellValidationIssue]:
    """Report a gap or overlap between sorted finite bands."""
    issues: list[CellValidationIssue] = []
    ordered = sorted(bands, key=_band_sort_key)
    prior: tuple[Decimal, Decimal | None] | None = None
    for current in ordered:
        if prior is not None:
            if prior[1] is None:
                issues.append(
                    CellValidationIssue(
                        "lookup_table_band_overlap",
                        f"LOOKUP_TABLE {source} bands overlap at {_format_band(current)}",
                    )
                )
            elif current[0] < prior[1]:
                issues.append(
                    CellValidationIssue(
                        "lookup_table_band_overlap",
                        f"LOOKUP_TABLE {source} bands overlap at {_format_band(current)}",
                    )
                )
            elif current[0] > prior[1]:
                issues.append(
                    CellValidationIssue(
                        "lookup_table_band_gap",
                        f"LOOKUP_TABLE {source} bands have a gap between "
                        f"{_format_band(prior)} and {_format_band(current)}",
                    )
                )
        prior = current
    return issues


def _band_sort_key(band: tuple[Decimal, Decimal | None]) -> tuple[Decimal, Decimal]:
    """Sort bands by lower bound, then put an open upper bound last."""
    return band[0], band[1] if band[1] is not None else Decimal("Infinity")


def _format_band(band: tuple[Decimal, Decimal | None]) -> str:
    """Render a numeric band for a deterministic validator message."""
    lower = _format_decimal(band[0])
    upper = "no limit" if band[1] is None else _format_decimal(band[1])
    return f"{lower}-{upper}"


def _format_decimal(value: Decimal) -> str:
    """Render integral amounts without scientific notation."""
    return str(int(value)) if value == value.to_integral() else format(value, "f")


def _operand_line(node: Mapping[str, Any]) -> str:
    """Return an operand's normalized printed line."""
    return str(node.get("line") or "").strip().lower()


def _operand_column(node: Mapping[str, Any]) -> str:
    """Return an operand's normalized table-column token."""
    return str(node.get("column") or "").strip().lower()


def _is_zero_constant(node: Mapping[str, Any]) -> bool:
    """Return whether an operand is the numeric zero constant."""
    return "const" in node and isinstance(node.get("const"), (int, float)) and float(node["const"]) == 0


def _is_zero_floor_operand(
    node: Mapping[str, Any],
    inventory: Mapping[str, Any] | None,
) -> bool:
    """Return whether a floor operand is a literal or cited zero parameter."""
    if _is_zero_constant(node):
        return True
    node_id = str(node.get("node") or "").strip()
    if not node_id:
        return False
    details = _reference_node_details(inventory).get(node_id)
    return bool(
        details
        and details.get("node_type") == "parameter"
        and _is_zero_value(details.get("constant_value"))
    )


def _is_zero_value(value: Any) -> bool:
    """Return whether a graph constant is the numeric zero, excluding booleans."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and float(value) == 0


def _available_lines(row: CellRecord) -> set[str]:
    """Read optional printed-line inventory supplied by the upstream frame."""
    for key in ("printed_lines", "available_lines", "form_lines"):
        values = row.metadata.get(key)
        if values:
            if isinstance(values, str):
                values = values.split(",")
            return {str(value).strip().lower() for value in values}
    return set()


def build_reference_inventory(
    graph: Any,
    manifest: Any | None = None,
) -> dict[str, Any]:
    """Build the immutable inventory used to validate expression operands.

    The live graph is not the complete universe of documents a formula may
    reference: acquired manifest documents can be deliberately unmodeled, and
    a harvested worksheet can remain in ``_drafts`` until promotion.  Callers
    therefore pass the acquisition manifest alongside the loaded graph.  Draft
    worksheets contribute only their document title and printed-line inventory;
    they are never loaded as graph objects or promoted by this projection.
    """
    document_ids: set[str] = set()
    document_titles: dict[str, str] = {}
    for item in graph.items("documents"):
        document_id = str(item.get("document_id") or "").strip().lower()
        if not document_id:
            continue
        document_ids.add(document_id)
        title = str(item.get("title") or "").strip()
        if title:
            document_titles[document_id] = title

    for entry in _manifest_entries(manifest):
        document_id = _manifest_value(entry, "document_id").strip().lower()
        if not document_id:
            continue
        document_ids.add(document_id)
        title = _manifest_value(entry, "region_title")
        if title:
            document_titles[document_id] = title

    node_ids: set[str] = set()
    graph_nodes: list[dict[str, str]] = []
    graph_node_details: dict[str, dict[str, Any]] = {}
    printed_lines: dict[str, set[str]] = {}
    for item in graph.items("nodes"):
        node_id = str(item.get("node_id") or "").strip()
        document_id = str(item.get("document_id") or "").strip().lower()
        if node_id:
            node_ids.add(node_id)
            if item.get("node_type") in {"parameter", "fact"}:
                graph_nodes.append({
                    "node_id": node_id,
                    "label": str(item.get("label") or "").strip(),
                })
                graph_node_details[node_id] = {
                    "node_type": str(item.get("node_type") or ""),
                    "document_id": document_id,
                    "label": str(item.get("label") or "").strip(),
                    **(
                        {"constant_value": item["constant_value"]}
                        if "constant_value" in item
                        else {}
                    ),
                    **(
                        {"value_type": item["value_type"]}
                        if "value_type" in item
                        else {}
                    ),
                }
        if not document_id:
            continue
        match = re.search(r"(?:^|_)line_([0-9]+[a-z]?|[a-z])(?:_|$)", node_id.lower())
        if match:
            printed_lines.setdefault(document_id, set()).add(match.group(1))

    draft_documents, draft_lines = _draft_reference_inventory(graph, manifest)
    for document_id, title in draft_documents.items():
        document_ids.add(document_id)
        document_titles[document_id] = title
    for document_id, lines in draft_lines.items():
        document_ids.add(document_id)
        printed_lines.setdefault(document_id, set()).update(lines)

    document_inventory = [
        {
            "document_id": document_id,
            "title": _human_document_title(
                document_id,
                document_titles.get(document_id, ""),
            ),
        }
        for document_id in sorted(document_ids)
    ]
    return {
        "document_ids": sorted(document_ids),
        "document_inventory": document_inventory,
        "printed_lines": {
            document_id: sorted(lines, key=_line_sort_key)
            for document_id, lines in sorted(printed_lines.items())
        },
        "node_ids": sorted(node_ids),
        "graph_nodes": sorted(graph_nodes, key=lambda item: item["node_id"]),
        "graph_node_details": graph_node_details,
    }


def _manifest_entries(manifest: Any | None) -> Sequence[Any]:
    """Return manifest entries without coupling the inventory to its dataclass."""
    if manifest is None:
        return ()
    entries = (
        manifest.get("documents", ())
        if isinstance(manifest, Mapping)
        else getattr(manifest, "documents", ())
    )
    if isinstance(entries, Mapping):
        return tuple(entries.values())
    return tuple(entries or ())


def _manifest_value(entry: Any, key: str) -> str:
    """Read one manifest field from either a dataclass or a mapping."""
    if isinstance(entry, Mapping):
        return str(entry.get(key) or "").strip()
    return str(getattr(entry, key, "") or "").strip()


def _draft_reference_inventory(
    graph: Any,
    manifest: Any | None,
) -> tuple[dict[str, str], dict[str, set[str]]]:
    """Read titles and printed lines from manifest-backed worksheet drafts."""
    graph_dir = getattr(graph, "graph_dir", None)
    if graph_dir is None:
        return {}, {}
    draft_root = Path(graph_dir) / "_drafts"
    if not draft_root.is_dir():
        return {}, {}

    titles: dict[str, str] = {}
    lines: dict[str, set[str]] = {}
    for entry in _manifest_entries(manifest):
        kind = _manifest_value(entry, "kind").lower()
        is_region = bool(
            entry.get("region") or entry.get("is_region")
            if isinstance(entry, Mapping)
            else getattr(entry, "is_region", False)
        )
        if kind != "worksheet" and not is_region:
            continue
        document_id = _manifest_value(entry, "document_id").lower()
        if not document_id:
            continue
        draft_dir = draft_root / document_id
        if not draft_dir.is_dir():
            continue
        document_payload = _load_draft_items(draft_dir / "documents.yaml")
        for item in document_payload:
            if not isinstance(item, Mapping):
                continue
            item_id = str(item.get("document_id") or document_id).strip().lower()
            if item_id != document_id:
                continue
            title = str(item.get("title") or "").strip()
            if title:
                titles[document_id] = title
        for item in _load_draft_items(draft_dir / "nodes.yaml"):
            if not isinstance(item, Mapping):
                continue
            item_id = str(item.get("document_id") or document_id).strip().lower()
            if item_id != document_id:
                continue
            node_id = str(item.get("node_id") or "").strip().lower()
            match = re.search(r"(?:^|_)line_([0-9]+[a-z]?|[a-z])(?:_|$)", node_id)
            line = match.group(1) if match else str(item.get("line") or "").strip().lower()
            if line:
                lines.setdefault(document_id, set()).add(line)
    return titles, lines


def _load_draft_items(path: Path) -> list[Any]:
    """Load a draft YAML list, returning no items for an absent optional file."""
    if not path.is_file():
        return []
    value = load_yaml(path)
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _human_document_title(document_id: str, title: str) -> str:
    """Return a useful prompt title even when the source lacks document prose."""
    if title and not title.lower().startswith("header:"):
        return title
    stem = re.sub(r"_[0-9]{4}$", "", document_id.lower())
    words = stem.split("_")
    if words[:2] == ["instructions", "form"] and len(words) > 2:
        return "Instructions for Form " + " ".join(words[2:])
    if words[:2] == ["instructions", "schedule"] and len(words) > 2:
        return "Instructions for Schedule " + " ".join(words[2:])
    if words and words[0] == "form" and len(words) > 1:
        return "Form " + " ".join(words[1:])
    if words and words[0] == "schedule" and len(words) > 1:
        return "Schedule " + " ".join(words[1:])
    if title:
        return title
    return " ".join(word.capitalize() for word in words)


def _reference_document_ids(inventory: Mapping[str, Any] | None) -> set[str] | None:
    """Return normalized document ids, or None when no inventory was supplied."""
    if inventory is None:
        return None
    values = inventory.get("document_ids")
    if values is None:
        values = inventory.get("documents")
        if isinstance(values, Mapping):
            values = values.keys()
    if values is None:
        return set()
    return {str(value).strip().lower() for value in values if str(value).strip()}


_DOCUMENT_YEAR_RE = re.compile(r"_(?P<year>(?:19|20)\d{2})$")
_PRIOR_YEAR_CUE_RE = re.compile(
    r"\b(?:last\s+year(?:'s)?|prior[\s-]+year(?:'s)?|carryover|carried\s+over)\b",
    re.IGNORECASE,
)


def _document_year(document_id: str) -> int | None:
    """Return a document id's explicit tax year, if it has one."""
    match = _DOCUMENT_YEAR_RE.search(str(document_id or "").strip().lower())
    return int(match.group("year")) if match else None


def _document_stem(document_id: str) -> str:
    """Remove only the terminal year from a document id."""
    return _DOCUMENT_YEAR_RE.sub("", str(document_id or "").strip().lower())


def _prior_year_document_match(
    operand_document_id: str,
    document_ids: Iterable[str] | None,
    *,
    current_document_id: str = "",
) -> str | None:
    """Return the current-inventory document sharing a prior operand's stem.

    The match is deliberately inventory-backed.  A year-shaped id is not a
    prior-year reference merely because it looks old; the current run must
    hold exactly one document with the same semantic stem, and the row's
    evidence must still provide the prior-year cue before validation promotes
    it to a warning.
    """
    if document_ids is None:
        return None
    operand_id = str(operand_document_id or "").strip().lower()
    operand_year = _document_year(operand_id)
    stem = _document_stem(operand_id)
    if operand_year is None or not stem:
        return None
    current_year = _document_year(current_document_id)
    matches = sorted({
        candidate
        for candidate in document_ids
        if _document_stem(candidate) == stem
        and _document_year(candidate) is not None
        and _document_year(candidate) != operand_year
        and (current_year is None or _document_year(candidate) == current_year)
        and (current_year is None or operand_year < current_year)
    })
    return matches[0] if len(matches) == 1 else None


def _has_prior_year_cue(evidence: str, operand_year: int | None) -> bool:
    """Return whether source evidence explicitly identifies a prior year."""
    value = str(evidence or "")
    if _PRIOR_YEAR_CUE_RE.search(value):
        return True
    if operand_year is None:
        return False
    return bool(re.search(rf"\b{operand_year}\b", value))


def _prior_year_reference_is_source_backed(
    row: CellRecord,
    operand_document_id: str,
    reference_documents: Iterable[str] | None,
) -> bool:
    """Return whether a known year-shifted operand has source support."""
    if _prior_year_document_match(
        operand_document_id,
        reference_documents,
        current_document_id=row.form,
    ) is None:
        return False
    evidence = " ".join((row.form_face_text, row.instruction_text, _evidence_span_text(row)))
    return _has_prior_year_cue(evidence, _document_year(operand_document_id))


def _reference_node_ids(inventory: Mapping[str, Any] | None) -> set[str] | None:
    """Return exact graph node ids, or None when no inventory was supplied."""
    if inventory is None:
        return None
    values = inventory.get("node_ids")
    if values is None:
        return set()
    return {str(value).strip() for value in values if str(value).strip()}


def _reference_node_details(inventory: Mapping[str, Any] | None) -> dict[str, Mapping[str, Any]]:
    """Return metadata for inventory nodes, with a legacy-list fallback."""
    if inventory is None:
        return {}
    values = inventory.get("graph_node_details")
    if isinstance(values, Mapping):
        return {
            str(node_id): item
            for node_id, item in values.items()
            if isinstance(item, Mapping)
        }
    graph_nodes = inventory.get("graph_nodes")
    if not isinstance(graph_nodes, Sequence) or isinstance(graph_nodes, (str, bytes)):
        return {}
    return {
        str(item.get("node_id")): item
        for item in graph_nodes
        if isinstance(item, Mapping) and item.get("node_id")
    }


_NUMERIC_VALUE_TYPES = frozenset({
    "amount",
    "currency",
    "decimal",
    "float",
    "integer",
    "number",
    "numeric",
    "percent",
    "rate",
})
_NON_NUMERIC_VALUE_TYPES = frozenset({
    "boolean",
    "bool",
    "date",
    "enum",
    "string",
    "text",
})
_NUMERIC_ARGUMENT_ROLES = {
    spec.name: spec.numeric_roles
    for spec in OPERATION_SPECS
    if spec.numeric_roles
}


def _numeric_operand_type_issues(
    expression: Mapping[str, Any],
    inventory: Mapping[str, Any] | None,
) -> tuple[list[CellValidationIssue], set[str]]:
    """Reject known nonnumeric graph nodes in amount-valued expression slots.

    The expression grammar does not carry types, so this check only uses facts
    present in the caller-supplied graph inventory.  A missing or incomplete
    detail is reported to the row as undetermined and is intentionally not
    treated as a failure.
    """
    if inventory is None:
        return [], set()
    details_by_id = _reference_node_details(inventory)
    known_node_ids = _reference_node_ids(inventory)
    if not details_by_id and not known_node_ids:
        return [], set()

    issues: list[CellValidationIssue] = []
    undetermined: set[str] = set()
    for expression_node in _expression_nodes(expression):
        operation = str(expression_node.get("op") or "").upper()
        slots = _numeric_argument_slots(operation, len(expression_node.get("args") or []))
        args = expression_node.get("args") or []
        for index, role in slots:
            operand = args[index]
            if not isinstance(operand, Mapping) or "node" not in operand:
                continue
            node_id = str(operand.get("node") or "").strip()
            if not node_id:
                continue
            details = details_by_id.get(node_id)
            if details is None:
                if known_node_ids is not None and node_id in known_node_ids:
                    undetermined.add(node_id)
                continue
            classification = _classify_numeric_node(details)
            if classification is None:
                undetermined.add(node_id)
                continue
            if classification:
                continue
            node_type = str(details.get("node_type") or "unknown")
            value_type = str(details.get("value_type") or "").strip()
            observed = f"node_type {node_type}"
            if value_type:
                observed += f", value_type {value_type}"
            issues.append(
                CellValidationIssue(
                    "operand_type_mismatch",
                    f"{operation} argument {index + 1} ({role}) requires a numeric operand, "
                    f"but node {node_id} has {observed}",
                )
            )
    return _unique_issues(issues), undetermined


def _numeric_argument_slots(operation: str, argument_count: int) -> list[tuple[int, str]]:
    """Return positional amount slots for one expression operation."""
    roles = operation_numeric_roles(operation, argument_count)
    if not roles:
        return []
    return [
        (index, role)
        for index, role in enumerate(roles)
        if role is not None
    ]


def _classify_numeric_node(details: Mapping[str, Any]) -> bool | None:
    """Return numeric, nonnumeric, or unknown for one graph-node detail."""
    value_type = str(details.get("value_type") or "").strip().lower()
    if value_type in _NUMERIC_VALUE_TYPES:
        return True
    if value_type in _NON_NUMERIC_VALUE_TYPES:
        return False
    if value_type:
        return None

    if "constant_value" not in details:
        return None
    value = details.get("constant_value")
    if _is_zero_value(value) or (
        isinstance(value, (int, float)) and not isinstance(value, bool)
    ):
        return True
    return False


def _scoped_graph_nodes(
    inventory: Mapping[str, Any] | None,
    document_id: str,
) -> list[dict[str, str]]:
    """Return prompt-visible parameter/fact nodes for one document."""
    if inventory is None:
        return []
    values = inventory.get("graph_nodes")
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return []
    details = _reference_node_details(inventory)
    current = str(document_id or "").strip().lower()
    result: list[dict[str, str]] = []
    for item in values:
        if not isinstance(item, Mapping):
            continue
        node_id = str(item.get("node_id") or "").strip()
        if not node_id:
            continue
        detail = details.get(node_id, item)
        owner = str(detail.get("document_id") or "").strip().lower()
        is_global_filer_fact = (
            detail.get("node_type") == "fact"
            and node_id.startswith("taxpayer_")
        )
        if owner and owner != current and not is_global_filer_fact:
            continue
        result.append({
            "node_id": node_id,
            "label": " ".join(str(item.get("label") or detail.get("label") or "").split()),
        })
    return sorted(result, key=lambda item: item["node_id"])


def _reference_lines(inventory: Mapping[str, Any] | None, document_id: str) -> set[str] | None:
    """Return a document's normalized printed-line inventory."""
    if inventory is None:
        return None
    values = inventory.get("printed_lines")
    if values is None:
        values = inventory.get("lines")
    if not isinstance(values, Mapping):
        documents = inventory.get("documents")
        values = documents if isinstance(documents, Mapping) else None
    if not isinstance(values, Mapping) or document_id not in values:
        return None
    result = values[document_id]
    if isinstance(result, Mapping):
        result = result.get("lines") or result.get("printed_lines")
    if result is None:
        return None
    if isinstance(result, str):
        result = result.split(",")
    return {str(value).strip().lower() for value in result if str(value).strip()}


def _line_sort_key(value: str) -> tuple[int, str]:
    """Sort printed line tokens numerically, then by suffix."""
    match = re.fullmatch(r"([0-9]+)([a-z]*)", str(value).lower())
    return (int(match.group(1)), match.group(2)) if match else (10**9, str(value))


def _line_mentioned(text: str, line: str) -> bool:
    """Match a printed line reference without treating ``1`` as ``1a``.

    Singular references (``line 10``) and plural lists (``lines 1z, 2b,
    and 8``) are matched by exact printed-line tokens.  A range explicitly
    mentions every member of that range, so ``lines 1a through 1h`` counts as
    mentioning ``1c``; treating the IRS shorthand as unrelated would create a
    warning for a line the quote plainly covers.
    """
    target = str(line or "").strip().lower()
    if not target:
        return False
    value = " ".join(str(text or "").split()).lower()
    token = re.escape(target)
    if re.search(rf"(?<!\w)line\s+{token}(?!\w)", value, re.IGNORECASE):
        return True

    for clause_match in re.finditer(r"\blines\s+([^.;:!?]+)", value, re.IGNORECASE):
        clause = clause_match.group(1)
        references = re.findall(r"(?<!\w)([0-9]+[a-z]?)(?!\w)", clause, re.IGNORECASE)
        if target in references:
            return True
        for start, end in re.findall(
            r"(?<!\w)([0-9]+[a-z]?)\s+through\s+([0-9]+[a-z]?)(?!\w)",
            clause,
            re.IGNORECASE,
        ):
            if _line_sort_key(start) <= _line_sort_key(target) <= _line_sort_key(end):
                return True
    return False


def _evidence_span_text(row: CellRecord) -> str:
    """Return text from serialized mined evidence spans, if supplied."""
    values = row.metadata.get("evidence_spans") or ()
    if isinstance(values, Mapping):
        values = (values,)
    return " ".join(str(item.get("text") or "") for item in values if isinstance(item, Mapping))


_FORM_FACE_SOURCE_REFERENCE_RE = re.compile(
    r"\b(?:from|shown\s+on|reported\s+on)\s+(?:the\s+)?"
    r"(?P<kind>form(?:\(s\)|s)?|schedule)\s+(?P<name>[0-9]+[a-z]?(?:-[a-z0-9]+)?|[a-z][a-z0-9-]*)",
    re.IGNORECASE,
)
_WORKSHEET_FACE_SOURCE_REFERENCE_RE = re.compile(
    r"\bfrom\s+(?:the\s+)?(?P<name>[^.;:!?]{1,120}?\bworksheet)\b",
    re.IGNORECASE,
)


def _form_face_source_references(row: CellRecord) -> list[str]:
    """Return other form, schedule, or worksheet sources named on the face.

    The form face is the exact evidence layer for this decision.  Only source
    wording is considered: ``from`` and ``shown on`` identify where a value
    comes from, while wording such as ``also enter on Schedule 3`` describes
    an output destination and must not turn a filer input into a false finding.
    The current document is excluded so a form title or same-form reference
    cannot trigger the cross-form guard.  Named worksheets are included because
    they are document inputs with the same fail-closed treatment.
    """
    current = re.sub(r"_[0-9]{4}$", "", row.form.strip().lower())
    references: list[str] = []
    seen: set[str] = set()
    for match in _FORM_FACE_SOURCE_REFERENCE_RE.finditer(row.form_face_text):
        kind = match.group("kind").lower()
        kind = "form" if kind.startswith("form") else kind
        name = match.group("name").lower().replace("-", "_")
        if _is_information_return_reference(kind, name):
            continue
        document_stem = f"{kind}_{name}"
        if document_stem == current or document_stem in seen:
            continue
        seen.add(document_stem)
        references.append(f"{kind.title()} {match.group('name')}")
    for match in _WORKSHEET_FACE_SOURCE_REFERENCE_RE.finditer(row.form_face_text):
        display = " ".join(match.group("name").split())
        key = f"worksheet_{display.lower()}"
        if key in seen:
            continue
        seen.add(key)
        references.append(f"Worksheet {display}")
    return references


def _is_information_return_reference(kind: str, name: str) -> bool:
    """Return whether a named source is a filer-supplied information return.

    W-2s, every 1099 variant, and K-1s are records supplied by the filer.  A
    REQUIRE_INPUT for one of these records is therefore not a hidden
    cross-document computation and must not be rejected by the face-source
    guard.  This rule is based on the document family, not on one spelling of
    a particular form title.
    """
    normalized = str(name).strip().lower().replace("_", "-")
    if kind == "form" and (normalized == "w-2" or normalized == "w2"):
        return True
    if kind == "form" and re.fullmatch(r"1099(?:-[a-z0-9]+)?", normalized):
        return True
    return kind == "schedule" and normalized == "k-1"


def _unique_issues(issues: Iterable[CellValidationIssue]) -> list[CellValidationIssue]:
    """Deduplicate equivalent validator messages in stable order."""
    seen: set[tuple[str, str]] = set()
    result: list[CellValidationIssue] = []
    for issue in issues:
        key = (issue.kind, issue.message)
        if key not in seen:
            result.append(issue)
            seen.add(key)
    return result


def _exception_issue(exc: Exception) -> CellValidationIssue:
    """Convert a payload exception into a stable validator kind."""
    message = str(exc)
    if "IF_ELSE requires comparison" in message:
        kind = "missing_comparison"
    elif "IF_ELSE comparison must be" in message:
        kind = "invalid_comparison"
    elif "verbatim" in message:
        kind = "quote_not_verbatim"
    elif "known input evidence span" in message:
        kind = "quote_span"
    elif "expression" in message or "operation" in message:
        kind = "expression_shape"
    else:
        kind = "payload"
    return CellValidationIssue(kind, f"{type(exc).__name__}: {message}")


def _format_issues(issues: Iterable[CellValidationIssue]) -> str:
    """Format deterministic complaints for row errors and repair prompts."""
    return "; ".join(f"{issue.kind}: {issue.message}" for issue in issues)


def _repair_prompt(
    prompt: str,
    row: CellRecord,
    issues: Iterable[CellValidationIssue],
) -> str:
    """Feed the exact deterministic complaint back to the provider once."""
    return (
        f"{prompt}\n\nREPAIR REQUEST for {row.form} line {row.line}: "
        f"{_format_issues(issues)}. Return one corrected expression and a verbatim quote."
    )


def _record_issues(report: dict[str, Any], issues: Iterable[CellValidationIssue]) -> None:
    """Increment validator failure counts by kind."""
    counts = report["validator_failures_by_kind"]
    for issue in issues:
        counts[issue.kind] = counts.get(issue.kind, 0) + 1


def _record_warnings(
    report: dict[str, Any],
    row: CellRecord,
    *,
    max_depth: int,
    reference_inventory: Mapping[str, Any] | None = None,
) -> None:
    """Record non-blocking operand evidence warnings for a successful row."""
    if row.expression is None:
        return
    _hard, warnings = validate_cell_output(
        row,
        row.expression,
        row.quote,
        max_depth=max_depth,
        reference_inventory=reference_inventory,
    )
    if not warnings:
        return
    row.metadata["validation_warnings"] = [item.as_dict() for item in warnings]
    counts = report["validator_warnings_by_kind"]
    for issue in warnings:
        counts[issue.kind] = counts.get(issue.kind, 0) + 1


def _projection_warnings(
    row: CellRecord,
    expression: Mapping[str, Any],
    *,
    max_depth: int,
) -> list[CellValidationIssue]:
    """Return warnings using the row's primary evidence source.

    The form face is the evidence used to interpret a generated row.  Joining
    it with instruction prose can introduce a second comparison cue (for
    example, ``more than`` on the face and ``or more`` in the instructions)
    and turn an otherwise resolved direction into a false warning.  Fall back
    only when the primary source is absent.
    """
    if str(expression.get("op") or "").upper() == "REQUIRE_INPUT":
        return []
    evidence_text = next(
        (
            str(text).strip()
            for text in (row.form_face_text, row.instruction_text, row.quote)
            if str(text or "").strip()
        ),
        "",
    )
    projection = expression_to_graph(
        form=row.form,
        line=row.line,
        expression=expression,
        quote_span_id=row.quote_span_id,
        evidence_text=evidence_text,
        max_depth=max_depth,
    )
    findings = []
    for finding in projection.findings:
        match = re.fullmatch(r"no reusable rule for operation ([A-Z_]+)", finding)
        if match:
            operation = match.group(1)
            spec = operation_spec(operation)
            if spec is not None and spec.category != "value":
                continue
            findings.append(
                CellValidationIssue(
                    "unmapped_operation",
                    f"graph projection: {finding}",
                    hard=False,
                )
            )
        elif finding == "comparison direction unresolved for operation IF_ELSE":
            findings.append(
                CellValidationIssue(
                    "unresolved_comparison_direction",
                    "graph projection: comparison direction for IF_ELSE is not stated in the evidence",
                    hard=False,
                )
            )
    return findings


def _mark_gap(row: CellRecord, issues: Iterable[CellValidationIssue], *, provider: str, model: str | None) -> None:
    """Mark a row that failed its one allowed repair as a review gap."""
    _mark_error(row, f"validation gap after one repair: {_format_issues(issues)}", provider=provider, model=model)
    row.status = "error"


def validate_expression_tree(node: Any, *, max_depth: int = 2) -> None:
    """Validate a bounded tree without recursive JSON Schema references."""
    if not isinstance(node, Mapping):
        raise ValueError("expression must be an object")
    _validate_tree_node(node, depth=0, max_depth=max_depth)


def _validate_tree_node(
    node: Mapping[str, Any],
    *,
    depth: int,
    max_depth: int,
    allow_role: bool = False,
) -> None:
    if "form" in node and "line" in node:
        if set(node) not in (
            {"form", "line"},
            {"form", "line", "role"},
            {"form", "line", "column"},
            {"form", "line", "column", "role"},
        ) or not str(node["form"]).strip() or not str(node["line"]).strip():
            raise ValueError("cross-form operand requires form and line")
        _validate_operand_column(node)
        _validate_operand_role(node, allow_role=allow_role)
        return
    if "line" in node:
        if set(node) not in (
            {"line"},
            {"line", "role"},
            {"line", "column"},
            {"line", "column", "role"},
        ) or not str(node["line"]).strip():
            raise ValueError("line operand must contain only a non-empty line")
        _validate_operand_column(node)
        _validate_operand_role(node, allow_role=allow_role)
        return
    if "const" in node:
        if set(node) not in ({"const"}, {"const", "role"}) or not isinstance(node["const"], (int, float)) or isinstance(node["const"], bool):
            raise ValueError("const operand must contain one numeric value")
        _validate_operand_role(node, allow_role=allow_role)
        return
    if "node" in node:
        if set(node) not in ({"node"}, {"node", "role"}) or not str(node["node"]).strip():
            raise ValueError("node operand must contain one non-empty graph node id")
        _validate_operand_role(node, allow_role=allow_role)
        return
    if set(node) not in ({"op", "args"}, {"op", "args", "comparison"}):
        raise ValueError("expression nodes require only op, args, and optional comparison")
    op = str(node.get("op") or "").upper()
    spec = operation_spec(op)
    if spec is None:
        raise ValueError(f"unsupported expression operation: {op}")
    comparison = node.get("comparison")
    if op == "IF_ELSE" and comparison is not None:
        if not isinstance(comparison, str) or not comparison:
            raise ValueError("IF_ELSE comparison must be one of gt, ge, lt, le, eq")
        if comparison.lower() not in IF_ELSE_COMPARISONS:
            raise ValueError(
                "IF_ELSE comparison must be one of gt, ge, lt, le, eq"
            )
    elif comparison is not None:
        raise ValueError("comparison is only valid for IF_ELSE")
    args = node.get("args")
    if not isinstance(args, list) or not args:
        raise ValueError(f"{op} requires at least one argument")
    if depth >= max_depth:
        if any(isinstance(arg, Mapping) and "op" in arg for arg in args):
            raise ValueError("expression tree exceeds configured depth")
    if not spec.accepts_count(len(args)):
        if spec.max_args == spec.min_args:
            raise ValueError(f"{op} requires exactly {spec.min_args} arguments")
        raise ValueError(f"{op} requires at least {spec.min_args} arguments")
    _validate_argument_shapes(op, args)
    for arg in args:
        if not isinstance(arg, Mapping):
            raise ValueError("expression arguments must be objects")
        _validate_tree_node(
            arg,
            depth=depth + 1,
            max_depth=max_depth,
            allow_role=spec.named_leaf_roles and _is_leaf_operand(arg),
        )


PREDICATE_OPERATIONS = predicate_operations()


def _validate_argument_shapes(operation: str, args: list[Any]) -> None:
    """Enforce the positional meanings of conditional expression arguments."""
    spec = operation_spec(operation)
    if operation in {"IF_ELSE", "COMPARE"}:
        for index, arg in enumerate(args):
            if _is_predicate_expression(arg):
                role = EXPRESSION_ARGUMENT_ROLES[operation][index]
                raise ValueError(
                    f"{operation} argument {index + 1} ({role}) must be a value expression, "
                    f"not a predicate"
                )
    elif operation == "IF":
        if not _is_predicate_expression(args[0]):
            raise ValueError("IF argument 1 (condition) must be a predicate expression")
        if _is_predicate_expression(args[1]):
            raise ValueError("IF argument 2 (when_true) must be a value expression")
    elif operation in {"AND", "OR"}:
        if any(not _is_predicate_expression(arg) for arg in args):
            raise ValueError(f"{operation} arguments (candidate) must be predicate expressions")
    elif operation == "NOT" and not _is_predicate_expression(args[0]):
        raise ValueError("NOT argument 1 (operand) must be a predicate expression")
    elif spec is not None and spec.named_leaf_roles:
        if any(
            not _is_leaf_operand(arg)
            or not isinstance(arg.get("role"), str)
            or not arg["role"]
            for arg in args
        ):
            raise ValueError(
                "LOOKUP_TABLE arguments must be named leaf operands with a role"
            )
        roles = [arg["role"] for arg in args]
        if roles.count("key") != 1:
            raise ValueError("LOOKUP_TABLE requires exactly one key role")
        if len(set(roles)) != len(roles):
            raise ValueError("LOOKUP_TABLE roles must be unique")


def _is_leaf_operand(value: Any) -> bool:
    """Return whether a value is one of the four graph operand shapes."""
    return isinstance(value, Mapping) and "op" not in value and any(
        key in value for key in ("form", "line", "const", "node")
    )


def _validate_operand_role(node: Mapping[str, Any], *, allow_role: bool) -> None:
    """Validate a role only when the parent operation owns named branches."""
    if "role" not in node:
        return
    if node["role"] is None:
        return
    if not allow_role:
        raise ValueError("operand role is only valid on LOOKUP_TABLE arguments")
    role = node["role"]
    if not isinstance(role, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", role):
        raise ValueError("operand role must be a lowercase identifier")


def _validate_operand_column(node: Mapping[str, Any]) -> None:
    """Validate an optional table-column token on a line operand."""
    if "column" not in node or node["column"] is None:
        return
    column = node["column"]
    if not isinstance(column, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", column):
        raise ValueError("operand column must be a lowercase identifier")


def _is_predicate_expression(value: Any) -> bool:
    """Return whether an expression node produces a boolean predicate."""
    return (
        isinstance(value, Mapping)
        and str(value.get("op") or "").upper() in PREDICATE_OPERATIONS
    )


EXPRESSION_ARGUMENT_ROLES = {
    spec.name: spec.roles
    for spec in OPERATION_SPECS
    if spec.name in {"IF", "IF_ELSE", "COMPARE", "AND", "OR", "NOT"}
}


DEFAULT_OPERATIONS = operation_names()


def expression_schema(
    operations: Sequence[str] | None = None,
    depth: int = 2,
) -> dict[str, Any]:
    """Build a bounded nested expression schema without recursive ``$ref``."""
    allowed = list(operations or DEFAULT_OPERATIONS)
    return {
        "type": "object",
        "additionalProperties": False,
        # Source identity is deliberately absent.  The code-side verbatim
        # match assigns the span after the model returns its quote.
        "required": ["expression", "quote"],
        "properties": {
            "expression": _expression_node_schema(allowed, depth),
            "quote": {"type": "string", "minLength": 1},
        },
    }


def _expression_node_schema(operations: list[str], depth: int) -> dict[str, Any]:
    role = {
        "type": ["string", "null"],
        "pattern": "^[a-z][a-z0-9_]*$",
        "description": "Named lookup role; use key, default, or the exact branch key.",
    }
    operands: list[dict[str, Any]] = [
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["line", "column", "role"],
            "properties": {
                "line": {"type": "string", "minLength": 1},
                "column": {
                    "type": ["string", "null"],
                    "pattern": "^[a-z][a-z0-9_]*$",
                    "description": "Optional table column token, such as l for column (l).",
                },
                "role": role,
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["form", "line", "column", "role"],
            "properties": {
                "form": {"type": "string", "minLength": 1},
                "line": {"type": "string", "minLength": 1},
                "column": {
                    "type": ["string", "null"],
                    "pattern": "^[a-z][a-z0-9_]*$",
                    "description": "Optional table column token, such as l for column (l).",
                },
                "role": role,
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["const", "role"],
            "properties": {"const": {"type": "number"}, "role": role},
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["node", "role"],
            "properties": {"node": {"type": "string", "minLength": 1}, "role": role},
        },
    ]
    if depth > 0:
        operands.append(_expression_node_schema(operations, depth - 1))
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["op", "args", "comparison"],
        "properties": {
            "op": {"type": "string", "enum": operations},
            "args": {"type": "array", "minItems": 1, "items": {"anyOf": operands}},
            "comparison": {
                "type": ["string", "null"],
                "enum": [*IF_ELSE_COMPARISONS, None],
                "description": "Required for IF_ELSE; null for every other operation.",
            },
        },
    }

INFIX = {"SUM": " + ", "SUBTRACT": " - ", "MULTIPLY": " * ", "DIVIDE": " / "}


def render(node: Mapping[str, Any], in_infix: bool = False) -> str:
    """Render a validated expression tree for review and graph labels."""
    if "form" in node and "line" in node:
        suffix = f", column ({_operand_column(node)})" if _operand_column(node) else ""
        return f"{node['form']} line {node['line']}{suffix}"
    if "line" in node:
        suffix = f", column ({_operand_column(node)})" if _operand_column(node) else ""
        return f"line {node['line']}{suffix}"
    if "const" in node:
        value = node["const"]
        return str(int(value)) if float(value).is_integer() else str(value)
    if "node" in node:
        return f"node {node['node']}"
    op = str(node.get("op", "?")).upper()
    if op == "LOOKUP_TABLE":
        args = [
            f"{arg.get('role')}={render(arg)}"
            if isinstance(arg, Mapping) and arg.get("role")
            else render(arg)
            for arg in node.get("args") or []
        ]
        return f"lookup_table({', '.join(args)})"
    args = [render(arg, in_infix=op in INFIX and len(node.get("args") or []) > 1) for arg in node.get("args") or []]
    if op in INFIX and len(args) > 1:
        body = INFIX[op].join(args)
        return f"({body})" if in_infix else body
    return f"{op.lower()}({', '.join(args)})"


@dataclass(frozen=True)
class GraphProjection:
    """Deterministic graph objects produced from one derived expression."""

    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    rules: list[dict[str, Any]]
    findings: list[str]


ROLE_FOR_OP = {
    spec.name: spec.roles
    for spec in OPERATION_SPECS
    if spec.roles
}

RULE_FOR_OP = {
    spec.name: spec.projection_rule
    for spec in OPERATION_SPECS
    if spec.projection_rule is not None
}


def _rule_for_op(
    operation: str,
    evidence_text: str,
    comparison: str | None = None,
) -> str | None:
    """Resolve one expression operation to an existing reusable graph rule."""
    return projection_rule_for(operation, evidence_text, comparison)


def _comparison_from_evidence(evidence_text: str) -> str | None:
    """Read a conditional direction from the row's own source evidence."""
    text = " ".join(str(evidence_text or "").split()).lower()
    less = re.search(
        r"\b(?:less\s+than|or\s+less|at\s+most|no\s+more\s+than|below|under)\b",
        text,
    )
    greater = re.search(
        r"\b(?:more\s+than|or\s+more|greater\s+than|at\s+least|exceeds|above)\b",
        text,
    )
    if less and greater:
        return None
    if less:
        return "less"
    if greater:
        return "greater"
    return None


def expression_to_graph(
    *,
    form: str,
    line: str,
    expression: Mapping[str, Any],
    quote_span_id: str = "",
    evidence_text: str = "",
    max_depth: int = 3,
) -> GraphProjection:
    """Flatten a tree into stable intermediate nodes and role-bearing edges.

    Conditional rule direction is carried by each IF_ELSE expression node.
    The evidence remains available to the caller for source reconciliation, but
    projection never invents a comparison direction.  The default validation
    bound matches the derivation schema so nested source rules remain projectable.
    """
    validate_expression_tree(expression, max_depth=max_depth)
    converter = _GraphConverter(form, line, quote_span_id, evidence_text)
    converter.walk(expression, converter.target)
    return GraphProjection(converter.nodes, converter.edges, converter.rules, converter.findings)


class _GraphConverter:
    def __init__(self, form: str, line: str, citation: str, evidence_text: str):
        self.form = _slug(form)
        self.base = f"{self.form}_root_line_{_slug(line)}"
        self.target = self.base
        self.citation = citation
        self.evidence_text = evidence_text
        self.nodes: list[dict[str, Any]] = []
        self.edges: list[dict[str, Any]] = []
        self.rules: list[dict[str, Any]] = []
        self.findings: list[str] = []
        self._steps = 0

    def walk(self, node: Mapping[str, Any], target: str) -> None:
        op = str(node.get("op", "")).upper()
        comparison = node.get("comparison") if op == "IF_ELSE" else None
        rule = _rule_for_op(op, self.evidence_text, comparison)
        if rule is None:
            if op == "IF_ELSE" and comparison is None:
                self.findings.append("comparison direction unresolved for operation IF_ELSE")
            else:
                self.findings.append(f"no reusable rule for operation {op}")
            rule = f"unmapped_{op.lower()}"
        args = node.get("args") or []
        for index, arg in enumerate(args):
            if isinstance(arg, Mapping) and "op" in arg:
                self._steps += 1
                if op == "MAX" and index == 0 and str(arg.get("op", "")).upper() == "SUBTRACT":
                    intermediate = f"{target}_pre_floor"
                else:
                    intermediate = f"{target}_step{self._steps}"
                self._add_node(intermediate, f"{target} intermediate: {render(arg)}")
                self.walk(arg, intermediate)
                source = intermediate
            else:
                source = self._operand_id(arg)
            role = _role_for(op, index, arg)
            self.edges.append({
                "edge_id": f"e_{_slug(source)}_to_{_slug(target)}_{role}",
                "source": source,
                "target": target,
                "relationship": "CALCULATES",
                "rule_id": rule,
                "role": role,
                **({"citation_refs": [self.citation]} if self.citation else {}),
            })

    def _operand_id(self, operand: Any) -> str:
        if not isinstance(operand, Mapping):
            self.findings.append(f"unrecognised operand: {operand}")
            return f"{self.base}_unresolved"
        if "form" in operand and "line" in operand:
            return _canonical_line_node_id(
                str(operand["form"]),
                str(operand["line"]),
                _operand_column(operand),
            )
        if "line" in operand:
            return _canonical_line_node_id(
                self.form,
                str(operand["line"]),
                _operand_column(operand),
            )
        if "const" in operand:
            value = operand["const"]
            suffix = "zero_floor" if float(value) == 0 else f"const_{str(value).replace('.', '_')}"
            node_id = f"{self.form}_{suffix}"
            self._add_node(node_id, f"{self.form} constant {value}", node_type="parameter", constant_value=value)
            return node_id
        if "node" in operand:
            return str(operand["node"])
        self.findings.append(f"unrecognised operand: {operand}")
        return f"{self.base}_unresolved"

    def _add_node(
        self,
        node_id: str,
        label: str,
        *,
        node_type: str = "computed",
        constant_value: Any = None,
    ) -> None:
        if any(node["node_id"] == node_id for node in self.nodes):
            return
        node: dict[str, Any] = {
            "node_id": node_id,
            "document_id": self.form,
            "label": label,
            "node_type": node_type,
            "value_type": "currency",
            "required": "optional",
        }
        if constant_value is not None:
            node["constant_value"] = constant_value
        if self.citation:
            node["citation_refs"] = [self.citation]
        self.nodes.append(node)


def _role_for(operation: str, index: int, operand: Any | None = None) -> str:
    if operation == "LOOKUP_TABLE" and isinstance(operand, Mapping) and operand.get("role"):
        return str(operand["role"])
    roles = operation_roles(operation, index + 1) or ("operand",)
    return roles[index] if index < len(roles) else roles[-1]


def _render_cell_prompt(
    template: str,
    row: CellRecord,
    *,
    reference_inventory: Mapping[str, Any] | None = None,
) -> str:
    """Render one cell prompt with the bounded graph-input inventory."""
    printed_lines = sorted(_available_lines(row), key=_line_sort_key)
    values = {
        "form": row.form,
        "line": row.line,
        "label": row.label,
        "form_face_text": row.form_face_text,
        "instruction_text": row.instruction_text,
        "instruction_locator": row.instruction_locator,
        "printed_lines": ", ".join(printed_lines),
        "document_inventory": _document_inventory_prompt(reference_inventory),
        "graph_nodes": _graph_nodes_prompt(reference_inventory, row.form),
        "human_comment": row.human_comment,
        "operation_documentation": prompt_operation_documentation(),
    }
    try:
        return render_prompt(template, values)
    except ValueError as exc:
        raise ValueError(f"cell {exc}") from exc


def _document_inventory_prompt(inventory: Mapping[str, Any] | None) -> str:
    """Render the complete allowed cross-document inventory for the model."""
    if inventory is None:
        return "none available"
    values = inventory.get("document_inventory")
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return "none available"
    lines = []
    for item in values:
        if not isinstance(item, Mapping):
            continue
        document_id = str(item.get("document_id") or "").strip()
        title = " ".join(str(item.get("title") or "").split())
        if document_id:
            lines.append(f"- {document_id}: {title}" if title else f"- {document_id}")
    return "\n".join(lines) if lines else "none available"


def _graph_nodes_prompt(
    inventory: Mapping[str, Any] | None,
    document_id: str = "",
) -> str:
    """Render only parameter and filer-fact nodes for model operand selection."""
    if inventory is None:
        return "none available"
    if isinstance(inventory.get("graph_nodes"), Mapping):
        legacy = inventory["graph_nodes"]
        inventory = dict(inventory)
        inventory["graph_nodes"] = [
            {"node_id": node_id, "label": label}
            for node_id, label in legacy.items()
        ]
    lines = []
    for item in _scoped_graph_nodes(inventory, document_id):
        node_id = item["node_id"]
        label = item["label"]
        lines.append(f"- {node_id}: {label}" if label else f"- {node_id}")
    return "\n".join(lines) if lines else "none available"


def _record_external_inputs(
    row: CellRecord,
    expression: Mapping[str, Any] | None,
    reference_inventory: Mapping[str, Any] | None,
) -> None:
    """Record legitimate unseen-form operands as unresolved required inputs."""
    row.metadata.pop("unresolved_external_nodes", None)
    reference_documents = _reference_document_ids(reference_inventory)
    if expression is None or reference_documents is None:
        return
    records: list[dict[str, Any]] = []
    prior_year_node_ids: list[str] = []
    seen: set[str] = set()
    for operand in _expression_operands(expression):
        operand_form = str(operand.get("form") or "").strip().lower()
        operand_line = str(operand.get("line") or "").strip().lower()
        operand_column = _operand_column(operand)
        prior_year_reference = _prior_year_document_match(
            operand_form,
            reference_documents,
            current_document_id=row.form,
        )
        source_backed_prior_year = (
            prior_year_reference is not None
            and _prior_year_reference_is_source_backed(
                row,
                operand_form,
                reference_documents,
            )
        )
        if (
            not operand_form
            or not operand_line
            or operand_form in reference_documents
            or _is_instruction_document_id(operand_form)
            or (
                prior_year_reference is not None
                and not source_backed_prior_year
            )
            or (
                prior_year_reference is None
                and not _legitimate_external_reference(
                    row,
                    operand_form,
                    operand_line,
                    reference_documents=reference_documents,
                )
            )
            or not re.fullmatch(r"[0-9]+[a-z]?", operand_line, re.IGNORECASE)
        ):
            continue
        node_id = _canonical_external_operand_id(operand_form, operand_line, operand_column)
        if node_id in seen:
            continue
        seen.add(node_id)
        record: dict[str, Any] = {
            "node_id": node_id,
            "document_id": operand_form,
            "line": operand_line,
            **({"column": operand_column} if operand_column else {}),
            "label": _external_reference_text(row, operand_form, operand_line),
            "node_type": "fact",
            "value_type": "currency",
            "required": "required",
            "status": "unresolved",
            "citation_refs": [row.quote_span_id] if row.quote_span_id else [],
        }
        records.append(record)
        if source_backed_prior_year:
            prior_year_node_ids.append(node_id)
    if records:
        row.metadata["unresolved_external_nodes"] = records
    else:
        row.metadata.pop("unresolved_external_nodes", None)
    if prior_year_node_ids:
        row.metadata["prior_year_reference_nodes"] = sorted(prior_year_node_ids)
    else:
        row.metadata.pop("prior_year_reference_nodes", None)


def _legitimate_external_reference(
    row: CellRecord,
    form: str,
    line: str,
    *,
    reference_documents: Iterable[str] | None = None,
) -> bool:
    """Return true when the row evidence supports this external operand.

    The model may obtain the printed line from the external document's
    instructions rather than the current row's evidence.  A known prior-year
    operand instead needs a prior-year cue; an unknown same-year form needs a
    named form.  The line is preserved in the canonical node address and
    checked when the document is inducted.
    """
    del line
    evidence = " ".join((row.form_face_text, row.instruction_text, _evidence_span_text(row)))
    if _prior_year_document_match(
        form,
        reference_documents,
        current_document_id=row.form,
    ) is not None:
        return _has_prior_year_cue(evidence, _document_year(form))
    if _external_form_is_named(evidence, form):
        return True
    return (
        _document_year(form) is not None
        and _document_year(row.form) == _document_year(form)
        and _external_form_stem_is_named(evidence, form)
    )


def _external_form_is_named(evidence: str, form: str) -> bool:
    """Match a fully qualified document id without discarding its year."""
    normalized = str(form).strip().lower()
    words = normalized.replace("_", " ")
    year = _document_year(normalized)
    aliases = {words}
    if year is not None:
        base = _document_stem(normalized).replace("_", " ")
        aliases.update({f"{base} {year}", f"{year} {base}"})
    compact_evidence = re.sub(r"[^a-z0-9]+", "", evidence.lower())
    return any(
        re.sub(r"[^a-z0-9]+", "", alias) in compact_evidence
        for alias in aliases
    )


def _external_form_stem_is_named(evidence: str, form: str) -> bool:
    """Match a same-year external form when prose omits the tax year."""
    stem = _document_stem(form)
    aliases = {stem.replace("_", " ")}
    if stem.startswith("form_"):
        aliases.add(f"form {stem.removeprefix('form_').replace('_', ' ')}")
    elif stem.startswith("schedule_"):
        aliases.add(f"schedule {stem.removeprefix('schedule_').replace('_', ' ')}")
    compact_evidence = re.sub(r"[^a-z0-9]+", "", evidence.lower())
    return any(
        re.sub(r"[^a-z0-9]+", "", alias) in compact_evidence
        for alias in aliases
    )


def _external_reference_text(row: CellRecord, form: str, line: str) -> str:
    """Choose the verbatim source text that names an external required input."""
    sources = [row.form_face_text, row.instruction_text]
    values = row.metadata.get("evidence_spans") or ()
    if isinstance(values, Mapping):
        values = (values,)
    sources.extend(
        str(item.get("text") or "")
        for item in values
        if isinstance(item, Mapping)
    )
    for source in sources:
        if source and _external_form_is_named(source, form) and _line_mentioned(source, line):
            return source
    for source in sources:
        if source and _external_form_is_named(source, form):
            return source
    return next((source for source in sources if source), "")


def _canonical_external_operand_id(form: str, line: str, column: str = "") -> str:
    """Return the canonical line id for an operand's document.

    An operand's ``form`` is already a document id by contract, so this must
    not decompose and rebuild it.  The previous version split off the year and
    re-prefixed ``form_``, which is correct for a bare printed reference like
    ``8863`` and wrong for a document that already names itself: a worksheet
    became ``form_social_security_benefits_worksheet_2025_...`` and a worksheet
    with no year gained an ``_unknown`` segment.  Both then failed the graph
    writer's canonical-address check.  One builder, shared with ingestion.
    """
    return _canonical_line_node_id(str(form), str(line), str(column))


def _known_quote_spans(row: CellRecord, quote: str) -> list[tuple[str, str]]:
    """Return input-owned span ids whose source contains the returned quote."""
    if row.metadata.get("governed_note_provenance"):
        form_span_id = str(row.metadata.get("form_face_span_id") or "")
        if form_span_id and _contains_verbatim(row.form_face_text, quote):
            # The displayed face is an assembled packet: its row span is kept
            # clean, while the governed note remains separately traceable in
            # metadata. Accept the packet quote without fusing those source
            # chunks in the persisted citation.
            return [(form_span_id, row.form_face_text)]
    evidence_spans = row.metadata.get("evidence_spans")
    if evidence_spans:
        if isinstance(evidence_spans, Mapping):
            evidence_spans = (evidence_spans,)
        return [
            (str(item.get("span_id") or ""), str(item.get("text") or ""))
            for item in evidence_spans
            if isinstance(item, Mapping)
            and item.get("span_id")
            and item.get("text")
            and _contains_verbatim(str(item["text"]), quote)
        ]
    fallback_span_id = row.instruction_locator
    candidates = [
        (str(row.metadata.get("form_face_span_id") or fallback_span_id or ""), row.form_face_text),
        (
            str(row.metadata.get("instruction_span_id") or fallback_span_id or ""),
            row.instruction_text,
        ),
    ]
    return [
        (span_id, source)
        for span_id, source in candidates
        if span_id and source and _contains_verbatim(source, quote)
    ]


def _contains_verbatim(source: str, quote: str) -> bool:
    if quote in source:
        return True
    normalize = lambda value: " ".join(str(value).split())
    return normalize(quote) in normalize(source)


def _keep_attempted_payload(row: CellRecord, payload: Any, *, attempt: str) -> None:
    """Record what the model actually answered, including when it is rejected.

    A rejected payload used to go out of scope with the exception, leaving only
    the error string.  That made a failing row undiagnosable from a run: five
    rounds were spent inferring causes from rejection COUNTS because the answer
    itself was never written down.  Keep it verbatim and let the reader see it.
    """
    attempts = row.metadata.setdefault("attempted_payloads", [])
    if not isinstance(attempts, list):
        return
    attempts.append({
        "attempt": attempt,
        "payload": json.loads(json.dumps(payload, default=str)) if isinstance(payload, Mapping) else repr(payload),
    })


def _mark_error(row: CellRecord, error: str, *, provider: str, model: str | None) -> None:
    row.status = "error"
    row.error = error
    row.provider = provider
    row.model = model


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_") or "item"


def _canonical_line_node_id(document_id: str, line: str, column: str = "") -> str:
    """Return the canonical line or line-column id used by projection and stubs."""
    node_id = f"{_slug(document_id)}_root_line_{_slug(line)}"
    if str(column).strip():
        node_id += f"_column_{_slug(column)}"
    return node_id


def _is_instruction_document_id(document_id: str) -> bool:
    """Return whether an id names an instructions booklet, not a form input."""
    return str(document_id or "").strip().lower().startswith("instructions_")


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
