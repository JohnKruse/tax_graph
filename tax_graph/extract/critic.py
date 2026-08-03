"""Independent critic pass for extracted drafts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tax_graph.config import get_config_value
from tax_graph.extract.llm_client import LlmClient, LlmUnavailable, response_telemetry
from tax_graph.extract.models import CriticFinding, CriticReport, ExtractionBatch, SourceDocumentInput
from tax_graph.extract.prompts import assemble_critic_prompt, critic_response_schema


def critique_drafts(
    document: SourceDocumentInput,
    batch: ExtractionBatch,
    *,
    client: LlmClient,
    config: dict[str, Any] | None = None,
    root: str | Path | None = None,
) -> CriticReport:
    """Ask an independent critic to re-derive source facts without generator reasoning."""
    settings = config or {}
    model = get_config_value(settings, "llm.model", "configured-llm")
    try:
        response = client.structured_completion(
            prompt=assemble_critic_prompt(document, batch=batch, config=settings, root=root),
            schema=critic_response_schema(),
            model=model,
            max_tokens=int(get_config_value(settings, "llm.critic_max_tokens", 8000)),
            temperature=_optional_float(get_config_value(settings, "llm.temperature")),
            purpose="tax_graph_critic",
        )
    except LlmUnavailable as exc:
        report = _unavailable_critic_report(batch, str(exc))
        apply_critic_report(batch, report)
        return report
    telemetry = response_telemetry(response)
    if telemetry is not None:
        batch.llm_calls.append(telemetry)
    report = parse_critic_response(response)
    apply_critic_report(batch, report)
    return report


def parse_critic_response(response: dict[str, Any]) -> CriticReport:
    """Parse critic findings from structured output."""
    findings = [
        CriticFinding(
            kind=str(item.get("kind", "")),
            object_id=str(item.get("object_id", "")),
            agrees=bool(item.get("agrees")),
            reason=str(item.get("reason", "")),
        )
        for item in response.get("findings", [])
        if isinstance(item, dict)
    ]
    return CriticReport(findings=findings)


def apply_critic_report(batch: ExtractionBatch, report: CriticReport) -> None:
    """Attach critic disagreement flags to draft objects."""
    for obj in batch.objects:
        # An expression is not reviewable unless the independent critic
        # explicitly considered both its verb and operand wiring.  Preserve
        # the historical permissive default for source nodes and citations,
        # but fail closed for the expression layer.
        if obj.kind in {"edges", "rules"} and not report.has_finding(obj.kind, obj.object_id):
            obj.critic_agrees = False
            obj.flag("critic did not review expression object")
        else:
            obj.critic_agrees = report.agrees(obj.kind, obj.object_id)
        if not obj.critic_agrees:
            reason = report.reason(obj.kind, obj.object_id) or "critic disagreement"
            obj.flag(f"critic disagreement: {reason}")


def _unavailable_critic_report(batch: ExtractionBatch, reason: str) -> CriticReport:
    return CriticReport(
        findings=[
            CriticFinding(
                kind=obj.kind,
                object_id=obj.object_id,
                agrees=False,
                reason=f"critic unavailable: {reason}",
            )
            for obj in batch.objects
        ]
    )


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
