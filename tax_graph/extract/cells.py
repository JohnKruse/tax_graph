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
import re
from typing import Any, Iterable, Mapping, Protocol, Sequence

from tax_graph.config import get_config_value
from tax_graph.extract.llm_client import LlmClient, response_telemetry
from tax_graph.extract.prompts import load_prompt_template, render_prompt


CELL_INPUT_FIELDS = (
    "form",
    "line",
    "label",
    "form_face_text",
    "instruction_text",
    "instruction_locator",
)


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
    from tax_graph.extract.outline_pipeline import _formula_outline_nodes, _span_for_line

    outline = build_outline_tree(document)
    instruction_frame = build_instruction_sections_frame(document, outline=outline)
    spans = build_candidate_spans(document)
    formula_nodes = _formula_outline_nodes(outline.children)
    printed_lines = sorted(
        {
            str(node.line_anchor).lower()
            for node in _flatten_outline_nodes(outline.children)
            if node.line_anchor
        },
        key=_line_sort_key,
    )
    rows: list[CellRecord] = []
    for node in formula_nodes:
        line = str(node.line_anchor or "").lower()
        if not line:
            continue
        form_span = _span_for_line(document, node, spans)
        sections = instruction_frame.for_line(document.document_id, line)
        instruction_text = "\n\n".join(section.text for section in sections)
        evidence_spans: list[dict[str, str]] = []
        if form_span is not None:
            evidence_spans.append(
                {
                    "span_id": form_span.span_id,
                    "text": clean_form_face_text(form_span.text, line),
                }
            )
        evidence_spans.extend(
            {"span_id": section.section_id, "text": section.text}
            for section in sections
        )
        rows.append(
            CellRecord(
                form=document.document_id,
                line=line,
                label=clean_form_face_text(node.label, line),
                form_face_text=clean_form_face_text(form_span.text, line) if form_span is not None else "",
                instruction_text=instruction_text,
                instruction_locator=sections[0].section_id if sections else "",
                metadata={
                    "instruction_owner_document_id": document.document_id,
                    "instruction_lines": [line],
                    "instruction_span_ids": [section.section_id for section in sections],
                    "form_face_span_id": form_span.span_id if form_span is not None else "",
                    "form_face_before": form_span.text if form_span is not None else "",
                    "label_before": node.label,
                    "printed_lines": printed_lines,
                    "evidence_spans": evidence_spans,
                },
            )
        )
    return CellFrame(rows)


def derive_cells(
    frame: CellFrame | Sequence[CellRecord | Mapping[str, Any]],
    prompt: str,
    api_key: str | None,
    *,
    client: LlmClient | None = None,
    client_factory: CellClientFactory | None = None,
    model: str = "configured-llm",
    provider: str = "configured-provider",
    operations: Sequence[str] | None = None,
    human_comments: Mapping[str, str] | None = None,
    max_depth: int = 2,
    max_tokens: int = 4000,
    temperature: float | None = None,
    reference_inventory: Mapping[str, Any] | None = None,
) -> CellFrame | list[dict[str, Any]]:
    """Derive every cell independently and return a new frame.

    ``client`` is the provider-agnostic seam used by production callers and
    fixture tests.  ``client_factory`` can construct it from ``api_key`` when
    the caller owns provider configuration.  With neither supplied, rows are
    marked ``error`` rather than silently selecting a vendor or writing state.
    A list input returns a list for compatibility with lightweight callers;
    a ``CellFrame`` input returns a ``CellFrame``.
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
            response = active_client.structured_completion(
                prompt=rendered_prompt,
                schema=schema,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                purpose="tax_graph_cell_derivation",
            )
        except Exception as exc:  # noqa: BLE001 - provider failures stay row-local
            _mark_error(row, f"{type(exc).__name__}: {exc}", provider=provider, model=model)
            report["errored"] += 1
            result_rows.append(row)
            continue

        try:
            payload = getattr(response, "payload", response)
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
            response = active_client.structured_completion(
                prompt=repair_prompt,
                schema=schema,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                purpose="tax_graph_cell_derivation_repair",
            )
            payload = getattr(response, "payload", response)
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
    model: str,
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
    if not row.label.strip():
        issues.append(CellValidationIssue("missing_label", "cell label is required"))
    if not row.form_face_text.strip() and not row.instruction_text.strip():
        issues.append(CellValidationIssue("missing_evidence", "at least one cited evidence source is required"))
    metadata = row.metadata
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


def clean_form_face_text(text: str, line: str) -> str:
    """Remove neighboring geometry text without changing source token order.

    The deterministic geometry pass can combine adjacent columns or rows into
    one text row.  When the cell's anchor is followed by descriptive text, the
    label starts at the first such occurrence and a repeated trailing anchor is
    truncated.  When the anchor is only a final right-hand-column token, keep
    the preceding text, dropping a split leading suffix and that final token.
    Neither branch reorders or reconstructs text, so the returned value remains
    a literal substring of the acquired text after whitespace normalization.
    """
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
    instruction still establishes elsewhere in the packet.
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
            if reference_documents is None:
                hard.append(
                    CellValidationIssue(
                        "operand_inventory_unavailable",
                        f"cannot validate {operand_form} line {operand_line} without a document inventory",
                    )
                )
            elif operand_form not in reference_documents:
                if not _legitimate_external_reference(row, operand_form, operand_line):
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
    warnings.extend(_projection_warnings(row, expression))
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


def build_reference_inventory(graph: Any) -> dict[str, Any]:
    """Build the immutable graph inventory used to validate external operands.

    Derivation remains pure: callers load the graph and pass this projection in
    as input.  The inventory distinguishes documents, their printed lines,
    exact graph node ids, and the compact parameter/filer-fact id-label list
    rendered into the model prompt so a model cannot invent either a form
    reference or a filer-fact reference.
    """
    document_ids = {
        str(item.get("document_id") or "").strip().lower()
        for item in graph.items("documents")
        if item.get("document_id")
    }
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
    return {
        "document_ids": sorted(document_ids),
        "printed_lines": {
            document_id: sorted(lines, key=_line_sort_key)
            for document_id, lines in sorted(printed_lines.items())
        },
        "node_ids": sorted(node_ids),
        "graph_nodes": sorted(graph_nodes, key=lambda item: item["node_id"]),
        "graph_node_details": graph_node_details,
    }


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
    "IF": (None, "when_true"),
    "IF_ELSE": ("condition", "threshold", "when_true", "when_false"),
    "COMPARE": ("left", "right"),
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
    roles = _NUMERIC_ARGUMENT_ROLES.get(operation)
    if not roles:
        return []
    if len(roles) == 1:
        return [(index, roles[0]) for index in range(argument_count)]
    return [
        (index, role)
        for index, role in enumerate(roles[:argument_count])
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
    if "verbatim" in message:
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
    )
    findings = []
    for finding in projection.findings:
        match = re.fullmatch(r"no reusable rule for operation ([A-Z_]+)", finding)
        if match:
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


def _mark_gap(row: CellRecord, issues: Iterable[CellValidationIssue], *, provider: str, model: str) -> None:
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
        if set(node) not in ({"form", "line"}, {"form", "line", "role"}) or not str(node["form"]).strip() or not str(node["line"]).strip():
            raise ValueError("cross-form operand requires form and line")
        _validate_operand_role(node, allow_role=allow_role)
        return
    if "line" in node:
        if set(node) not in ({"line"}, {"line", "role"}) or not str(node["line"]).strip():
            raise ValueError("line operand must contain only a non-empty line")
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
    if set(node) != {"op", "args"}:
        raise ValueError("expression nodes require only op and args")
    op = str(node.get("op") or "").upper()
    if op not in DEFAULT_OPERATIONS:
        raise ValueError(f"unsupported expression operation: {op}")
    args = node.get("args")
    if not isinstance(args, list) or not args:
        raise ValueError(f"{op} requires at least one argument")
    if depth >= max_depth:
        if any(isinstance(arg, Mapping) and "op" in arg for arg in args):
            raise ValueError("expression tree exceeds configured depth")
    expected = {"COPY": 1, "NEGATE": 1, "ABS": 1, "ROUND": 1, "REQUIRE_INPUT": 1,
                "NOT": 1, "SUBTRACT": 2, "DIVIDE": 2, "MULTIPLY": 2,
                "COMPARE": 2, "IF": 2, "IF_ELSE": 4}
    if op in expected and len(args) != expected[op]:
        raise ValueError(f"{op} requires exactly {expected[op]} arguments")
    if op in {"AND", "OR"} and len(args) < 2:
        raise ValueError(f"{op} requires at least 2 arguments")
    _validate_argument_shapes(op, args)
    for arg in args:
        if not isinstance(arg, Mapping):
            raise ValueError("expression arguments must be objects")
        _validate_tree_node(
            arg,
            depth=depth + 1,
            max_depth=max_depth,
            allow_role=op == "LOOKUP_TABLE" and _is_leaf_operand(arg),
        )


PREDICATE_OPERATIONS = frozenset({"COMPARE", "AND", "OR", "NOT"})


def _validate_argument_shapes(operation: str, args: list[Any]) -> None:
    """Enforce the positional meanings of conditional expression arguments."""
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
    elif operation == "LOOKUP_TABLE":
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


def _is_predicate_expression(value: Any) -> bool:
    """Return whether an expression node produces a boolean predicate."""
    return (
        isinstance(value, Mapping)
        and str(value.get("op") or "").upper() in PREDICATE_OPERATIONS
    )


EXPRESSION_ARGUMENT_ROLES = {
    "IF": ("condition", "when_true"),
    "IF_ELSE": ("condition", "threshold", "when_true", "when_false"),
    "COMPARE": ("left", "right"),
    "AND": ("candidate",),
    "OR": ("candidate",),
    "NOT": ("operand",),
}


DEFAULT_OPERATIONS = (
    "COPY", "SUM", "SUBTRACT", "MULTIPLY", "DIVIDE", "MIN", "MAX", "NEGATE",
    "ABS", "ROUND", "LOOKUP_TABLE", "LOOKUP_BRACKET", "IF", "IF_ELSE", "AND",
    "OR", "NOT", "COMPARE", "REQUIRE_INPUT",
)


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
            "required": ["line", "role"],
            "properties": {"line": {"type": "string", "minLength": 1}, "role": role},
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["form", "line", "role"],
            "properties": {
                "form": {"type": "string", "minLength": 1},
                "line": {"type": "string", "minLength": 1},
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
        "required": ["op", "args"],
        "properties": {
            "op": {"type": "string", "enum": operations},
            "args": {"type": "array", "minItems": 1, "items": {"anyOf": operands}},
        },
    }

INFIX = {"SUM": " + ", "SUBTRACT": " - ", "MULTIPLY": " * ", "DIVIDE": " / "}


def render(node: Mapping[str, Any], in_infix: bool = False) -> str:
    """Render a validated expression tree for review and graph labels."""
    if "form" in node and "line" in node:
        return f"{node['form']} line {node['line']}"
    if "line" in node:
        return f"line {node['line']}"
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
    "SUM": ("addend",),
    "SUBTRACT": ("minuend", "subtrahend"),
    "DIVIDE": ("numerator", "denominator"),
    "MULTIPLY": ("factor",),
    "MAX": ("candidate",),
    "MIN": ("candidate",),
    "COPY": ("source",),
    "NEGATE": ("value",),
    "IF": EXPRESSION_ARGUMENT_ROLES["IF"],
    "IF_ELSE": EXPRESSION_ARGUMENT_ROLES["IF_ELSE"],
    "COMPARE": EXPRESSION_ARGUMENT_ROLES["COMPARE"],
    "AND": EXPRESSION_ARGUMENT_ROLES["AND"],
    "OR": EXPRESSION_ARGUMENT_ROLES["OR"],
    "NOT": EXPRESSION_ARGUMENT_ROLES["NOT"],
    "LOOKUP_TABLE": ("key", "value"),
}

RULE_FOR_OP = {
    "SUM": "sum_currency",
    "SUBTRACT": "subtract_currency",
    "MULTIPLY": "multiply_currency",
    "DIVIDE": "divide_currency",
    "MIN": "min_currency",
    "MAX": "max_currency",
    "NEGATE": "negate_currency",
    "ABS": "abs_currency",
    "ROUND": "round_currency",
    "COPY": "copy_currency_value",
    "LOOKUP_TABLE": "lookup_selected_value",
}


def _rule_for_op(operation: str, evidence_text: str) -> str | None:
    """Resolve one expression operation to an existing reusable graph rule."""
    if operation != "IF_ELSE":
        return RULE_FOR_OP.get(operation)
    comparison = _comparison_from_evidence(evidence_text)
    return {
        "less": "if_less_than_currency",
        "greater": "if_greater_than_currency",
    }.get(comparison)


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
) -> GraphProjection:
    """Flatten a tree into stable intermediate nodes and role-bearing edges.

    Conditional rule direction is resolved from the supplied evidence text.
    A missing direction remains a named finding rather than silently choosing a
    branch that may execute the wrong tax rule.
    """
    validate_expression_tree(expression)
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
        rule = _rule_for_op(op, self.evidence_text)
        if rule is None:
            if op == "IF_ELSE":
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
            return f"{_slug(str(operand['form']))}_line_{_slug(str(operand['line']))}"
        if "line" in operand:
            return f"{self.form}_root_line_{_slug(str(operand['line']))}"
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
    roles = ROLE_FOR_OP.get(operation, ("operand",))
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
        "graph_nodes": _graph_nodes_prompt(reference_inventory, row.form),
        "human_comment": row.human_comment,
    }
    try:
        return render_prompt(template, values)
    except ValueError as exc:
        raise ValueError(f"cell {exc}") from exc


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
    seen: set[str] = set()
    for operand in _expression_operands(expression):
        operand_form = str(operand.get("form") or "").strip().lower()
        operand_line = str(operand.get("line") or "").strip().lower()
        if (
            not operand_form
            or not operand_line
            or operand_form in reference_documents
            or not _legitimate_external_reference(row, operand_form, operand_line)
            or not re.fullmatch(r"[0-9]+[a-z]?", operand_line, re.IGNORECASE)
        ):
            continue
        node_id = _canonical_external_operand_id(operand_form, operand_line)
        if node_id in seen:
            continue
        seen.add(node_id)
        record: dict[str, Any] = {
            "node_id": node_id,
            "document_id": operand_form,
            "line": operand_line,
            "label": _external_reference_text(row, operand_form, operand_line),
            "node_type": "fact",
            "value_type": "currency",
            "required": "required",
            "status": "unresolved",
            "citation_refs": [row.quote_span_id] if row.quote_span_id else [],
        }
        records.append(record)
    if records:
        row.metadata["unresolved_external_nodes"] = records


def _legitimate_external_reference(row: CellRecord, form: str, line: str) -> bool:
    """Return true only when the row evidence names this external form and line."""
    evidence = " ".join((row.form_face_text, row.instruction_text, _evidence_span_text(row)))
    return _external_form_is_named(evidence, form) and _line_mentioned(evidence, line)


def _external_form_is_named(evidence: str, form: str) -> bool:
    """Match form ids against evidence after folding punctuation and year suffixes."""
    stem = re.sub(r"_[0-9]{4}$", "", str(form).strip().lower())
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


def _canonical_external_operand_id(form: str, line: str) -> str:
    """Reuse the outline pipeline's canonical id for an unseen form line."""
    from tax_graph.extract.outline_pipeline import _canonical_external_source_id

    match = re.search(r"_([0-9]{4})$", str(form))
    year = match.group(1) if match else "unknown"
    stem = str(form)[: match.start()] if match else str(form)
    return _canonical_external_source_id(stem, year, line=line)


def _known_quote_spans(row: CellRecord, quote: str) -> list[tuple[str, str]]:
    """Return input-owned span ids whose source contains the returned quote."""
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


def _mark_error(row: CellRecord, error: str, *, provider: str, model: str) -> None:
    row.status = "error"
    row.error = error
    row.provider = provider
    row.model = model


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_") or "item"


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
