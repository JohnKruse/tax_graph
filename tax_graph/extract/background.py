"""Draft-only policy extraction for physical controls outside the formula spine.

The field map is the identity source for a physical control.  A model may classify
the control and select verbatim evidence, but it never supplies a field name,
address, or graph id.  This keeps the background-control pass correctable by a
human and prevents a model response from moving identity between widgets.
"""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import contextvars
from pathlib import Path
import re
from typing import Any

import yaml

from tax_graph.config import get_config_value
from tax_graph.extract.llm_client import LlmClient, is_transient_transport_error, response_telemetry
from tax_graph.extract.models import LlmCallTelemetry, SourceDocumentInput
from tax_graph.extract.observability import llm_call_target
from tax_graph.extract.outline import CandidateSpan
from tax_graph.extract.micro import MicroExtractionError


BACKGROUND_POLICY_DOCUMENTS = frozenset({
    "form_1040_2025",
    "schedule_1_2025",
    "schedule_a_2025",
})
BACKGROUND_POLICIES = frozenset({
    "user_entered",
    "decision_required",
    "intentionally_blank",
    "unsupported",
})
BACKGROUND_FAILOVER_CLASSES = frozenset({
    "filer_election",
    "filer_identity_admin",
    "filer_supplied_value",
    "computed_candidate",
})
_STOP_WORDS = frozenset({
    "a", "an", "and", "as", "at", "by", "check", "for", "from", "here",
    "if", "in", "line", "of", "on", "or", "see", "the", "to", "with",
})


def background_policy_schema() -> dict[str, Any]:
    """Return the closed schema for one background-control classification."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["population_policy", "quote", "reason"],
        "properties": {
            "population_policy": {
                "type": "string",
                "enum": sorted(BACKGROUND_POLICIES),
            },
            "quote": {"type": "string", "minLength": 1},
            "reason": {"type": "string", "minLength": 1},
        },
    }


def load_background_fields(
    root: str | Path | None,
    year: str | int,
    document_id: str,
) -> list[dict[str, Any]]:
    """Load the authored field dispositions used as the physical-control spine."""
    if root is None or document_id not in BACKGROUND_POLICY_DOCUMENTS:
        return []
    path = Path(root) / "graph" / str(year) / "field_maps" / f"{document_id}.yaml"
    if not path.is_file():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        return []
    return [
        dict(item)
        for item in payload.get("field_dispositions", []) or []
        if isinstance(item, dict) and item.get("field_name")
    ]


def extract_background_policy(
    field: dict[str, Any],
    spans: list[CandidateSpan],
    *,
    client: LlmClient,
    config: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Ask for one policy and return it with code-resolved citation span ids."""
    evidence = background_evidence(field, spans)
    if not evidence:
        raise MicroExtractionError("no deterministic form or instruction evidence for control")
    settings = config or {}
    target = str(field.get("field_name") or "")
    with llm_call_target(target):
        response = client.structured_completion(
            prompt=_background_prompt(field, evidence),
            schema=background_policy_schema(),
            model=_background_model(settings),
            max_tokens=_background_max_tokens(settings),
            temperature=_optional_float(get_config_value(settings, "llm.temperature", 0)),
            purpose="tax_graph_background_policy",
        )
    validate_background_policy(response, evidence)
    quote = str(response["quote"])
    citation_span_ids = [
        span.span_id
        for span in evidence
        if _quote_matches(quote, span.text)
    ]
    if not any(span.relationship == "source" for span in evidence if span.span_id in citation_span_ids):
        raise MicroExtractionError("background policy quote has no form-face citation")
    return response, citation_span_ids


def validate_background_policy(
    response: dict[str, Any],
    evidence: list[CandidateSpan],
) -> None:
    """Reject policy output that is not grounded in the supplied evidence."""
    if not isinstance(response, dict):
        raise MicroExtractionError("background policy response must be an object")
    policy = response.get("population_policy")
    if policy not in BACKGROUND_POLICIES:
        raise MicroExtractionError(f"unsupported background policy: {policy}")
    quote = response.get("quote")
    if not isinstance(quote, str) or not quote.strip():
        raise MicroExtractionError("background policy quote must be non-empty")
    reason = response.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise MicroExtractionError("background policy reason must be non-empty")
    if not any(_quote_matches(quote, span.text) for span in evidence):
        raise MicroExtractionError("background policy quote does not match supplied evidence")


def extract_background_controls(
    document: SourceDocumentInput,
    spans: list[CandidateSpan],
    *,
    client: LlmClient,
    config: dict[str, Any] | None = None,
    root: str | Path | None = None,
) -> tuple[dict[str, Any], list[LlmCallTelemetry]]:
    """Classify unsupported physical controls without changing promoted artifacts.

    A supported response for an unsupported field is a filer failover, not a
    graph-derived value.  The distinction is recorded in ``policy_origin`` so
    the completeness report cannot turn a fallback into apparent extraction
    progress.  Controls whose labels state a computation remain review gaps.
    """
    if not document.fields or not document.fields.get("fields"):
        return {}, []
    fields = load_background_fields(root, document.year, document.document_id)
    if not fields:
        return {}, []

    records: list[dict[str, Any]] = []
    calls: list[LlmCallTelemetry] = []
    before = Counter(str(field.get("population_policy") or "unsupported") for field in fields)
    attempted = sum(
        str(field.get("population_policy") or "unsupported") == "unsupported"
        for field in fields
    )
    succeeded = failed = 0
    transport_failures = 0
    unsupported_results = _run_background_calls(
        [
            _with_field_page(document, field)
            for field in fields
            if str(field.get("population_policy") or "unsupported") == "unsupported"
        ],
        spans,
        client=client,
        config=config,
    )
    unsupported_index = 0
    for field in fields:
        field_name = str(field["field_name"])
        field = _with_field_page(document, field)
        authored_policy = str(field.get("population_policy") or "unsupported")
        record = {
            "field_name": field_name,
            "label": str(field.get("label") or ""),
            "value_format": str(field.get("value_format") or ""),
            "address_id": str(field.get("address_id") or ""),
            "population_policy": authored_policy,
            "status": "authored" if authored_policy != "unsupported" else "review_gap",
            "policy_origin": "authored" if authored_policy != "unsupported" else "review_gap",
            "policy_basis": "field_map" if authored_policy != "unsupported" else "unresolved",
            "policy_defaulted": False,
            "policy_derived": False,
            "failover_class": None,
            "has_policy": authored_policy != "unsupported",
            "has_form_face_citation": False,
            "has_instruction_citation": False,
            "citation_span_ids": [],
            "instruction_span_ids": [],
        }
        if authored_policy != "unsupported":
            records.append(record)
            continue

        response, citation_span_ids, error, telemetry = unsupported_results[unsupported_index]
        unsupported_index += 1
        if error is None and response is not None:
            policy = str(response["population_policy"])
            failover_class = _failover_class(field)
            if policy in {"user_entered", "decision_required"} and failover_class == "computed_candidate":
                error = MicroExtractionError(
                    "computed-looking control cannot fall back to a filer policy"
                )
            else:
                policy_origin = "defaulted" if policy in {"user_entered", "decision_required"} else "derived"
                policy_basis = "filer_fallback" if policy_origin == "defaulted" else "source_evidence"
                record.update(
                    {
                        "population_policy": policy,
                        "reason": str(response["reason"]),
                        "quote": str(response["quote"]),
                        "citation_span_ids": citation_span_ids,
                        "policy_origin": policy_origin if policy != "unsupported" else "review_gap",
                        "policy_basis": policy_basis if policy != "unsupported" else "unresolved",
                        "policy_defaulted": policy_origin == "defaulted" and policy != "unsupported",
                        "policy_derived": policy_origin == "derived" and policy != "unsupported",
                        "failover_class": failover_class,
                        "has_policy": policy != "unsupported",
                        "has_form_face_citation": any(
                            span.relationship == "source"
                            for span in spans
                            if span.span_id in citation_span_ids
                        ),
                        "instruction_span_ids": [
                            span.span_id
                            for span in spans
                            if span.relationship != "source" and span.span_id in citation_span_ids
                        ],
                    }
                )
                if policy == "unsupported":
                    record["status"] = "review_gap"
                    record["review_gap"] = "model could not establish a supported control policy"
                else:
                    record["status"] = "complete"
                    succeeded += 1
                if isinstance(telemetry, LlmCallTelemetry):
                    record["model"] = telemetry.resolved_model or telemetry.requested_model
                    record["provider"] = telemetry.resolved_provider or telemetry.provider
                    calls.append(telemetry)
                records.append(record)
                continue
        if error is not None or response is None:
            failed += 1
            if error is not None and is_transient_transport_error(error):
                transport_failures += 1
            record["failover_class"] = _failover_class(field)
            record["review_gap"] = (
                f"background policy extraction failed: {type(error).__name__}: {error}"
                if error is not None
                else "background policy extraction failed without a response"
            )
            if isinstance(telemetry, LlmCallTelemetry):
                calls.append(telemetry)
        records.append(record)

    after = Counter(str(record.get("population_policy") or "unsupported") for record in records)
    origins = Counter(str(record.get("policy_origin") or "review_gap") for record in records)
    origin_policy = Counter(
        (str(record.get("policy_origin") or "review_gap"), str(record.get("population_policy") or "unsupported"))
        for record in records
    )
    failover_classes = Counter(
        str(record.get("failover_class"))
        for record in records
        if record.get("failover_class")
    )
    stats = {
        "background_controls": records,
        "background_controls_total": len(records),
        "background_controls_attempted": attempted,
        "background_controls_succeeded": succeeded,
        "background_controls_failed": failed,
        "background_transport_failures": transport_failures,
        "background_policy_before": dict(sorted(before.items())),
        "background_policy_after": dict(sorted(after.items())),
        "background_policy_progress": before.get("unsupported", 0) - after.get("unsupported", 0),
        "background_policy_origin_counts": dict(sorted(origins.items())),
        "background_policy_after_by_origin": _nested_origin_counts(origin_policy),
        "background_failover_class_counts": dict(sorted(failover_classes.items())),
    }
    return stats, calls


def _run_background_calls(
    fields: list[dict[str, Any]],
    spans: list[CandidateSpan],
    *,
    client: LlmClient,
    config: dict[str, Any] | None,
) -> list[tuple[dict[str, Any] | None, list[str], Exception | None, LlmCallTelemetry | None]]:
    """Run unsupported-control calls concurrently, preserving result order."""
    if not fields:
        return []
    settings = config or {}
    configured = get_config_value(settings, "extraction.background_policy_concurrency")
    if configured is None:
        configured = get_config_value(settings, "extraction.concurrency", 8)
    workers = max(1, min(len(fields), int(configured)))

    def submit(field: dict[str, Any]):
        context = contextvars.copy_context()
        return context.run(_run_background_call, field, spans, client, settings)

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="tax-graph-background") as executor:
        futures = [executor.submit(submit, field) for field in fields]
        return [future.result() for future in futures]


def _run_background_call(
    field: dict[str, Any],
    spans: list[CandidateSpan],
    client: LlmClient,
    config: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str], Exception | None, LlmCallTelemetry | None]:
    """Execute one background call inside the copied observability context."""
    try:
        response, citation_span_ids = extract_background_policy(
            field,
            spans,
            client=client,
            config=config,
        )
        telemetry = response_telemetry(response)
        return response, citation_span_ids, None, telemetry
    except Exception as exc:
        return None, [], exc, None


def background_evidence(field: dict[str, Any], spans: list[CandidateSpan]) -> list[CandidateSpan]:
    """Select a small deterministic form-plus-instruction evidence packet."""
    tokens = set(_meaningful_tokens(" ".join([
        str(field.get("label") or ""),
        str(field.get("address_id") or "").replace("/", " ").replace("=", " "),
    ])))
    page = _field_page(field, spans)
    ranked: list[tuple[int, str, CandidateSpan]] = []
    for span in spans:
        span_tokens = set(_meaningful_tokens(span.text))
        overlap = len(tokens & span_tokens)
        if overlap == 0:
            continue
        score = overlap * 10
        if page is not None and _span_page(span) == page:
            score += 5
        if span.relationship != "source":
            score += 1
        ranked.append((score, span.span_id, span))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    selected = [item[2] for item in ranked[:8]]
    source_selected = [span for span in selected if span.relationship == "source"]
    if source_selected:
        return selected
    if page is not None:
        nearby = [span for span in spans if span.relationship == "source" and _span_page(span) == page]
        return selected + nearby[: max(0, 4 - len(selected))]
    return selected


def _background_prompt(field: dict[str, Any], evidence: list[CandidateSpan]) -> str:
    rendered = "\n".join(
        f"- {span.span_id} ({span.relationship}, {span.locator}): {span.text}"
        for span in evidence
    )
    return "\n".join([
        "Classify one physical tax-form control for a draft review projection.",
        "Return exactly one population_policy: user_entered, decision_required,",
        "intentionally_blank, or unsupported.",
        "Use user_entered when the filer supplies the value, and decision_required",
        "when the answer is a meaningful yes/no or choice that affects the return.",
        "Use intentionally_blank only when the source explicitly establishes that the",
        "control stays blank. Use unsupported when the evidence is insufficient.",
        "Formula and source/import paths have priority. This background pass is only a",
        "filer failover after those paths produced no value. Never classify a control",
        "whose label states a computation as filer-entered or as a filer decision.",
        "Select quote verbatim from the evidence packet. Do not return field names,",
        "address ids, node ids, or any other internal identifiers.",
        "",
        f"control label: {field.get('label', '')}",
        f"value format: {field.get('value_format', '')}",
        "",
        "evidence packet:",
        rendered,
    ])


def _field_page(field: dict[str, Any], spans: list[CandidateSpan]) -> int | None:
    field_name = str(field.get("field_name") or "")
    # The field map has no geometry.  The page hint is attached to the span only
    # when the caller has included the field-grid label in the address packet.
    page_hint = field.get("page")
    if isinstance(page_hint, int):
        return page_hint
    return None


def _with_field_page(document: SourceDocumentInput, field: dict[str, Any]) -> dict[str, Any]:
    """Add the deterministic widget page without changing the field identity."""
    field_name = str(field.get("field_name") or "")
    for item in (document.fields or {}).get("fields", []) or []:
        if str(item.get("field_name") or "") == field_name and item.get("page") is not None:
            result = dict(field)
            result["page"] = int(item["page"])
            return result
    return field


def _span_page(span: CandidateSpan) -> int | None:
    match = re.search(r"\bpage\s+(\d+)\b", span.locator, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _meaningful_tokens(value: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", value.lower()) if token not in _STOP_WORDS and len(token) > 1]


def _failover_class(field: dict[str, Any]) -> str:
    """Classify the deterministic filer failover without inventing tax semantics."""
    label = str(field.get("label") or "").lower()
    value_format = str(field.get("value_format") or "").lower()
    if _looks_computed(label):
        return "computed_candidate"
    if value_format in {"checkbox", "radio", "choice"} or _has_label_term(
        label, ("check", "election", "yes", "option", "decision")
    ):
        return "filer_election"
    if value_format in {"date", "ssn", "ein"} or _has_label_term(
        label,
        (
            "name", "address", "city", "state", "province", "country", "postal", "zip",
            "ssn", "ein", "date", "year", "beginning", "ending", "phone", "email",
            "routing", "account", "pin", "identification", "preparer", "designee",
            "mm", "dd", "yyyy",
        ),
    ):
        return "filer_identity_admin"
    return "filer_supplied_value"


def _looks_computed(label: str) -> bool:
    """Detect computation language that must never be delegated to the filer."""
    return bool(re.search(
        r"\b(?:add|subtract|combine|multiply|divide|total|sum|smaller|larger|greater|lesser)\b",
        label,
    ))


def _has_label_term(label: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(term)}\b", label) for term in terms)


def _nested_origin_counts(values: Counter[tuple[str, str]]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for (origin, policy), count in sorted(values.items()):
        result.setdefault(origin, {})[policy] = count
    return result


def _quote_matches(quote: str, source: str) -> bool:
    normalize = lambda value: " ".join(str(value).split()).lower()
    return normalize(quote) in normalize(source) or normalize(source) in normalize(quote)


def _background_model(settings: dict[str, Any]) -> str:
    model = get_config_value(settings, "llm.micro_model")
    if model:
        return str(model)
    return str(get_config_value(settings, "llm.model", "configured-llm") or "configured-llm")


def _background_max_tokens(settings: dict[str, Any]) -> int:
    value = get_config_value(settings, "extraction.background_policy_max_tokens")
    if value is None:
        value = get_config_value(settings, "extraction.micro_max_tokens")
    if value is None:
        value = get_config_value(settings, "llm.micro_max_tokens", 4000)
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
