"""Route and write extracted draft objects for human review."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tax_graph.config import get_config_value, project_root
from tax_graph.extract.models import DRAFT_KINDS, DeterministicReport, DraftObject, ExtractionBatch, RoutedDrafts


def route_drafts(
    batch: ExtractionBatch,
    report: DeterministicReport,
    *,
    config: dict[str, Any] | None = None,
) -> RoutedDrafts:
    """Split drafts into auto-accepted and human-review lists."""
    settings = config or {}
    threshold = float(get_config_value(settings, "extraction.auto_accept_confidence", 0.95))
    require_critic = bool(get_config_value(settings, "extraction.require_critic_agreement", True))
    accepted: list[DraftObject] = []
    review: list[DraftObject] = []

    for obj in batch.objects:
        if obj.confidence < threshold:
            obj.flag(f"confidence {obj.confidence:.3f} below threshold {threshold:.3f}")
        if require_critic and not obj.critic_agrees:
            obj.flag("critic agreement required")
        if obj.flags:
            review.append(obj)
        else:
            accepted.append(obj)

    return RoutedDrafts(accepted=accepted, review=review, issues=report.issues)


def write_routed_drafts(
    batch: ExtractionBatch,
    routed: RoutedDrafts,
    *,
    root: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> RoutedDrafts:
    """Write schema-pure draft YAML and review metadata under graph/<year>/_drafts."""
    root_path = Path(root).resolve() if root is not None else project_root()
    settings = config or {}
    graph_dir = root_path / get_config_value(settings, "project.paths.graph_dir", "graph")
    draft_dir = graph_dir / batch.year / "_drafts" / batch.document_id
    draft_dir.mkdir(parents=True, exist_ok=True)

    for kind in DRAFT_KINDS:
        items = [obj.data for obj in batch.items(kind)]
        if items:
            _write_yaml(draft_dir / f"{kind}.yaml", items)

    _write_yaml(draft_dir / "provenance.yaml", [_provenance(obj) for obj in batch.objects])
    (draft_dir / "review.md").write_text(render_review(batch, routed), encoding="utf-8", newline="\n")
    return RoutedDrafts(
        accepted=routed.accepted,
        review=routed.review,
        issues=routed.issues,
        output_dir=draft_dir,
    )


def render_review(batch: ExtractionBatch, routed: RoutedDrafts) -> str:
    """Render a human-review report."""
    lines = [
        f"# Extraction Review - {batch.document_id}",
        "",
        f"Tax year: {batch.year}",
        f"Auto-accepted drafts: {len(routed.accepted)}",
        f"Human-review drafts: {len(routed.review)}",
        "",
        "Drafts remain under `_drafts` and must not be promoted without human review.",
        "",
        "## Auto-Accepted",
    ]
    lines.extend(_object_lines(routed.accepted, include_flags=False))
    lines.extend(["", "## Human Review"])
    lines.extend(_object_lines(routed.review, include_flags=True))
    if routed.issues:
        lines.extend(["", "## Deterministic Issues"])
        for issue in routed.issues:
            lines.append(f"- {issue.kind}/{issue.object_id}: {issue.reason}")
    return _assert_ascii("\n".join(lines).rstrip() + "\n")


def _object_lines(objects: list[DraftObject], *, include_flags: bool) -> list[str]:
    if not objects:
        return ["- none"]
    lines = []
    for obj in objects:
        lines.append(f"- {obj.kind}/{obj.object_id} confidence={obj.confidence:.3f}")
        if include_flags:
            for flag in obj.flags:
                lines.append(f"  - {flag}")
    return lines


def _provenance(obj: DraftObject) -> dict[str, Any]:
    return {
        "kind": obj.kind,
        "object_id": obj.object_id,
        "source_span": obj.source_span,
        "extracted_by": obj.extracted_by,
        "confidence": obj.confidence,
        "critic_agrees": obj.critic_agrees,
        "flags": obj.flags,
    }


def _write_yaml(path: Path, data: Any) -> None:
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=False)
    path.write_text(_assert_ascii(text), encoding="utf-8", newline="\n")


def _assert_ascii(text: str) -> str:
    text.encode("ascii")
    return text
