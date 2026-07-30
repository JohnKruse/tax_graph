"""Per-extraction verification metrics and the cross-form verify report.

Each extraction run writes ``metrics.yaml`` beside ``review.md`` (design:
docs/extraction-verification.md Section 7). ``tax-graph verify report`` rolls
the per-form files up and prints the payoff lines: human minutes per promoted
object, worker-machine cost telemetry, and the escape count.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tax_graph.extract.models import CheckIssue, DraftObject, ExtractionBatch, RoutedDrafts
from tax_graph.verify.tiers import tier_distribution


METRICS_FILENAME = "metrics.yaml"

_LAYER_PATTERNS = (
    ("magic", "parameters"),
    ("schema", "schema"),
    ("field", "field_grid"),
    ("unmapped", "field_grid"),
    ("line ", "line_completeness"),
    ("citation", "citation"),
    ("quote", "citation"),
    ("critic", "critic"),
    ("decision", "decision_policy"),
    ("nversion", "nversion"),
    ("property", "properties"),
)


def classify_flag(reason: str) -> str:
    """Map a flag/issue reason onto the verification layer that raised it."""
    lowered = reason.lower()
    for token, layer in _LAYER_PATTERNS:
        if token in lowered:
            return layer
    return "other"


def build_metrics(batch: ExtractionBatch, routed: RoutedDrafts) -> dict[str, Any]:
    """Build the per-run verification metrics payload."""
    objects_by_kind: dict[str, int] = {}
    models_used: set[str] = set()
    confidences: list[float] = []
    flags_by_layer: dict[str, int] = {}
    for obj in batch.objects:
        objects_by_kind[obj.kind] = objects_by_kind.get(obj.kind, 0) + 1
        models_used.add(obj.extracted_by)
        confidences.append(float(obj.confidence))
        for reason in obj.flags:
            layer = classify_flag(reason)
            flags_by_layer[layer] = flags_by_layer.get(layer, 0) + 1
    for issue in routed.issues:
        layer = classify_flag(issue.reason)
        flags_by_layer[layer] = flags_by_layer.get(layer, 0) + 1

    llm_calls = [call.as_dict() for call in batch.llm_calls]
    token_values = [call.total_tokens for call in batch.llm_calls if call.total_tokens is not None]
    cost_values = [call.cost for call in batch.llm_calls if call.cost is not None]
    for call in batch.llm_calls:
        if call.resolved_model:
            models_used.add(call.resolved_model)

    return {
        "document_id": batch.document_id,
        "tax_year": batch.year,
        "objects_by_kind": dict(sorted(objects_by_kind.items())),
        "routing": {
            "accepted": len(routed.accepted),
            "review": len(routed.review),
            "calibration_sample": len(routed.calibration),
        },
        "tiers": tier_distribution(batch.objects),
        "flags_by_layer": dict(sorted(flags_by_layer.items())),
        "models_used": sorted(models_used),
        "llm_calls": llm_calls,
        "confidence_telemetry": _confidence_telemetry(confidences),
        "human_minutes": None,
        "worker_tokens": sum(token_values) if token_values else None,
        "worker_cost": sum(cost_values) if cost_values else None,
        "escapes": 0,
    }


def write_metrics(draft_dir: str | Path, metrics: dict[str, Any]) -> Path:
    """Write metrics.yaml beside the review artifacts."""
    path = Path(draft_dir) / METRICS_FILENAME
    text = yaml.safe_dump(metrics, sort_keys=False, allow_unicode=False)
    text.encode("ascii")
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def collect_metrics(root: str | Path, *, year: str, graph_dir: str = "graph") -> list[dict[str, Any]]:
    """Load every per-form metrics.yaml under graph/<year>/_drafts."""
    drafts_dir = Path(root) / graph_dir / str(year) / "_drafts"
    reports: list[dict[str, Any]] = []
    if not drafts_dir.is_dir():
        return reports
    for metrics_path in sorted(drafts_dir.glob(f"*/{METRICS_FILENAME}")):
        payload = yaml.safe_load(metrics_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            reports.append(payload)
    return reports


def render_report(reports: list[dict[str, Any]], *, year: str) -> str:
    """Render the cross-form verify report with the payoff lines."""
    lines = [f"=== verification report - {year} ==="]
    if not reports:
        lines.append("  no extraction metrics found (run tax-graph extract first)")
        return "\n".join(lines) + "\n"

    totals = {"T0": 0, "T1": 0, "T2": 0, "T3": 0}
    total_objects = 0
    total_review = 0
    total_calibration = 0
    total_escapes = 0
    minutes_known = 0.0
    minutes_recorded = False
    worker_tokens = 0
    worker_tokens_recorded = False
    worker_cost = 0.0
    worker_cost_recorded = False
    for report in reports:
        tiers = report.get("tiers", {})
        for tier in totals:
            totals[tier] += int(tiers.get(tier, 0))
        total_objects += sum(int(n) for n in report.get("objects_by_kind", {}).values())
        routing = report.get("routing", {})
        total_review += int(routing.get("review", 0))
        total_calibration += int(routing.get("calibration_sample", 0))
        total_escapes += int(report.get("escapes", 0))
        minutes = report.get("human_minutes")
        if minutes is not None:
            minutes_known += float(minutes)
            minutes_recorded = True
        tokens = report.get("worker_tokens")
        if tokens is not None:
            worker_tokens += int(tokens)
            worker_tokens_recorded = True
        cost = report.get("worker_cost")
        if cost is not None:
            worker_cost += float(cost)
            worker_cost_recorded = True
        lines.append(
            "  {doc}: objects={objects} tiers(T0/T1/T2/T3)={t0}/{t1}/{t2}/{t3} "
            "review={review} calibration={calibration} worker_tokens={tokens} worker_cost={cost}".format(
                doc=report.get("document_id", "?"),
                objects=sum(int(n) for n in report.get("objects_by_kind", {}).values()),
                t0=tiers.get("T0", 0),
                t1=tiers.get("T1", 0),
                t2=tiers.get("T2", 0),
                t3=tiers.get("T3", 0),
                review=routing.get("review", 0),
                calibration=routing.get("calibration_sample", 0),
                tokens=report.get("worker_tokens", "null"),
                cost=report.get("worker_cost", "null"),
            )
        )

    lines.append(
        f"  totals: objects={total_objects} "
        f"tiers(T0/T1/T2/T3)={totals['T0']}/{totals['T1']}/{totals['T2']}/{totals['T3']} "
        f"review={total_review} calibration={total_calibration}"
    )
    if minutes_recorded and total_objects:
        lines.append(
            f"  human minutes per object: {minutes_known / total_objects:.2f} (recorded at promotion)"
        )
    else:
        lines.append("  human minutes per object: not yet recorded (filled at promotion)")
    if worker_tokens_recorded:
        lines.append(f"  worker tokens recorded: {worker_tokens}")
    else:
        lines.append("  worker tokens recorded: not yet recorded")
    if worker_cost_recorded:
        lines.append(f"  worker cost recorded: {worker_cost:.4f}")
    else:
        lines.append("  worker cost recorded: not yet recorded")
    lines.append(f"  escapes found in calibration audits: {total_escapes}")
    return "\n".join(lines) + "\n"


def _confidence_telemetry(confidences: list[float]) -> dict[str, float] | None:
    if not confidences:
        return None
    return {
        "min": round(min(confidences), 3),
        "max": round(max(confidences), 3),
        "mean": round(sum(confidences) / len(confidences), 3),
    }
