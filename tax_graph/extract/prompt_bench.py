"""Read-only prompt diagnostics for one small extraction target set.

The bench calls the same prompt builders and validators as extraction, but it
does not enter the extraction run or draft writer.  Its output is intentionally
returned in memory so a caller can print the exact prompt, response, and
validation decision without creating pipeline state.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tax_graph.config import get_config_value
from tax_graph.extract.background import (
    _background_max_tokens,
    _background_model,
    _background_prompt,
    background_evidence,
    background_policy_schema,
    load_background_fields,
    validate_background_policy,
)
from tax_graph.extract.llm_client import LlmClient
from tax_graph.extract.micro import (
    MicroExtractionError,
    _formula_prompt,
    _micro_max_tokens,
    _micro_model,
    _table_formula_prompt,
    _table_formula_schema,
    formula_micro_schema,
    validate_formula_plan,
)
from tax_graph.extract.observability import llm_call_target
from tax_graph.extract.outline import (
    CandidateSpan,
    build_candidate_spans,
    build_outline_tree,
)
from tax_graph.extract.outline_pipeline import (
    _formula_outline_nodes,
    _instruction_owner_map,
    _outline_node_id,
    _spans_for_outline_node,
)
from tax_graph.extract.models import SourceDocumentInput


def run_prompt_bench(
    document: SourceDocumentInput,
    target_ids: list[str],
    *,
    client: LlmClient,
    config: dict[str, Any] | None = None,
    root: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Run the real micro prompt path for a bounded list of target ids.

    A target id is either a field-map ``field_name``/``address_id`` or a
    deterministic formula cell id.  No draft, report, or promoted artifact is
    written by this function.
    """
    settings = config or {}
    spans = build_candidate_spans(document)
    fields = load_background_fields(root, document.year, document.document_id)
    field_by_id = {
        str(value): field
        for field in fields
        for value in (field.get("field_name"), field.get("address_id"))
        if value
    }
    outline = build_outline_tree(document)
    instruction_owners = _instruction_owner_map(spans)
    formula_targets = {}
    for node in _formula_outline_nodes(outline.children, document_id=document.document_id):
        formula_targets[_outline_node_id(document.document_id, node)] = node
        if node.line_anchor:
            formula_targets.setdefault(str(node.line_anchor), node)

    results = []
    for target_id in target_ids:
        target = str(target_id).strip()
        field = field_by_id.get(target)
        if field is not None:
            results.append(
                _bench_background_target(
                    target,
                    field,
                    spans,
                    client=client,
                    config=settings,
                    owner_document_id=document.document_id,
                )
            )
            continue
        node = formula_targets.get(target)
        if node is not None:
            node_spans = _spans_for_outline_node(
                document,
                node,
                spans,
                document_id=document.document_id,
                table_mode=node.kind in {"transaction_table", "totals"},
                instruction_owners=instruction_owners,
            )
            results.append(
                _bench_formula_target(
                    target,
                    node,
                    node_spans,
                    client=client,
                    config=settings,
                    root=root,
                )
            )
            continue
        results.append({
            "target_id": target,
            "target_type": "unknown",
            "prompt": "",
            "response": None,
            "accepted": False,
            "validation_error": "target id does not match a field-map control or formula cell",
            "matched_spans": [],
        })
    return results


def _bench_background_target(
    target_id: str,
    field: dict[str, Any],
    spans: list[CandidateSpan],
    *,
    client: LlmClient,
    config: dict[str, Any],
    owner_document_id: str | None = None,
) -> dict[str, Any]:
    evidence = background_evidence(field, spans, owner_document_id=owner_document_id)
    prompt = _background_prompt(field, evidence)
    response, error = _call_and_validate(
        target_id,
        prompt,
        background_policy_schema(),
        client=client,
        model=_background_model(config),
        max_tokens=_background_max_tokens(config),
        config=config,
        validator=lambda value: _validate_background_with_citation(value, evidence),
        purpose="tax_graph_background_policy",
    )
    return _bench_result(
        target_id,
        "control",
        prompt,
        response,
        error,
        evidence,
    )


def _bench_formula_target(
    target_id: str,
    node: Any,
    spans: list[CandidateSpan],
    *,
    client: LlmClient,
    config: dict[str, Any],
    root: str | Path | None,
) -> dict[str, Any]:
    table_mode = node.kind in {"transaction_table", "totals"}
    prompt = _table_formula_prompt(node, spans) if table_mode else _formula_prompt(node, spans)
    schema = _table_formula_schema(root=root) if table_mode else formula_micro_schema(root=root)
    response, error = _call_and_validate(
        target_id,
        prompt,
        schema,
        client=client,
        model=_micro_model(config),
        max_tokens=_micro_max_tokens(config),
        config=config,
        validator=lambda value: validate_formula_plan(
            value,
            spans=spans,
            root=root,
            outline_node=node,
        ),
        purpose="tax_graph_micro_formula",
    )
    return _bench_result(
        target_id,
        "cell",
        prompt,
        response,
        error,
        spans,
    )


def _validate_background_with_citation(
    response: dict[str, Any],
    evidence: list[CandidateSpan],
) -> None:
    validate_background_policy(response, evidence)
    quote = str(response["quote"])
    if not any(
        span.relationship == "source" and _quote_matches(quote, span.text)
        for span in evidence
    ):
        raise MicroExtractionError("background policy quote has no form-face citation")


def _call_and_validate(
    target_id: str,
    prompt: str,
    schema: dict[str, Any],
    *,
    client: LlmClient,
    model: str,
    max_tokens: int,
    config: dict[str, Any],
    validator,
    purpose: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """Call a provider and return its response plus a deterministic failure."""
    response = None
    try:
        with llm_call_target(target_id):
            response = client.structured_completion(
                prompt=prompt,
                schema=schema,
                model=model,
                max_tokens=max_tokens,
                temperature=_temperature(config),
                purpose=purpose,
            )
        validator(response)
    except Exception as exc:
        return response, f"{type(exc).__name__}: {exc}"
    return response, None


def _bench_result(
    target_id: str,
    target_type: str,
    prompt: str,
    response: dict[str, Any] | None,
    error: str | None,
    spans: list[CandidateSpan],
) -> dict[str, Any]:
    quote = response.get("quote") if isinstance(response, dict) else None
    matched = [
        {
            "span_id": span.span_id,
            "relationship": span.relationship,
            "locator": span.locator,
            "text": span.text,
        }
        for span in spans
        if isinstance(quote, str) and _quote_matches(quote, span.text)
    ]
    return {
        "target_id": target_id,
        "target_type": target_type,
        "prompt": prompt,
        "response": response,
        "accepted": error is None,
        "validation_error": error,
        "matched_spans": matched,
    }


def _temperature(config: dict[str, Any]) -> float:
    value = get_config_value(config, "llm.temperature", 0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _quote_matches(quote: str, source: str) -> bool:
    normalize = lambda value: " ".join(str(value).split())
    return normalize(quote) in normalize(source) or normalize(source) in normalize(quote)
