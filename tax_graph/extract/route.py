"""Route and write extracted draft objects for human review.

Routing is deterministic from check outcomes (M8): confidence scores are
recorded as telemetry but NEVER read by any routing decision. Humans see the
exception queue (flagged objects, decisions) plus a seeded calibration sample
of clean objects (docs/extraction-verification.md Section 3, layer L6).
"""

from __future__ import annotations

import hashlib
import math
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import yaml

from tax_graph.config import get_config_value, project_root
from tax_graph.extract.models import DRAFT_KINDS, DeterministicReport, DraftObject, ExtractionBatch, RoutedDrafts, SourceDocumentInput
from tax_graph.extract.outline import write_outline_artifacts
from tax_graph.extract.review_html import write_review_html
from tax_graph.verify.metrics import build_metrics, write_metrics
from tax_graph.verify.tiers import TierInputs, assign_tier


WRITE_KINDS = (*DRAFT_KINDS, "documents")


def route_drafts(
    batch: ExtractionBatch,
    report: DeterministicReport,
    *,
    config: dict[str, Any] | None = None,
    tier_inputs: TierInputs | None = None,
) -> RoutedDrafts:
    """Split drafts into accepted / human-review lists and assign trust tiers."""
    settings = config or {}
    require_critic = bool(get_config_value(settings, "extraction.require_critic_agreement", True))
    sample_rate = float(get_config_value(settings, "extraction.calibration_sample_rate", 0.10))
    sample_min = int(get_config_value(settings, "extraction.calibration_min", 5))
    accepted: list[DraftObject] = []
    review: list[DraftObject] = []

    for obj in batch.objects:
        if require_critic and not obj.critic_agrees:
            obj.flag("critic agreement required")
        if obj.kind == "decisions":
            obj.flag("decision objects always require human review")
        obj.tier = assign_tier(obj, tier_inputs)
        if obj.flags:
            review.append(obj)
        else:
            accepted.append(obj)

    calibration = _calibration_sample(
        batch.document_id, accepted, rate=sample_rate, minimum=sample_min
    )
    return RoutedDrafts(
        accepted=accepted,
        review=review,
        issues=report.issues,
        calibration=calibration,
        micro_stats=batch.micro_stats,
    )


def _calibration_sample(
    document_id: str,
    accepted: list[DraftObject],
    *,
    rate: float,
    minimum: int,
) -> list[DraftObject]:
    """Pick a deterministic audit sample of clean objects (10% min 5 default).

    Selection orders objects by a stable hash of document + identity, so the
    sample is reproducible and independent of extraction order, confidence,
    and clock.
    """
    if not accepted:
        return []
    count = min(len(accepted), max(minimum, math.ceil(rate * len(accepted))))

    def sort_key(obj: DraftObject) -> str:
        digest = hashlib.sha256(f"{document_id}/{obj.kind}/{obj.object_id}".encode("ascii"))
        return digest.hexdigest()

    return sorted(accepted, key=sort_key)[:count]


def write_routed_drafts(
    batch: ExtractionBatch,
    routed: RoutedDrafts,
    *,
    root: str | Path | None = None,
    config: dict[str, Any] | None = None,
    document: SourceDocumentInput | None = None,
) -> RoutedDrafts:
    """Write schema-pure draft YAML and review metadata under graph/<year>/_drafts."""
    root_path = Path(root).resolve() if root is not None else project_root()
    settings = config or {}
    graph_dir = root_path / get_config_value(settings, "project.paths.graph_dir", "graph")
    draft_dir = graph_dir / batch.year / "_drafts" / batch.document_id
    transport_failures = int(batch.micro_stats.get("transport_failures", 0))
    transport_failures += int(batch.micro_stats.get("background_transport_failures", 0))
    if transport_failures:
        # A completed-with-call-failures batch is a fail-closed observation, not
        # a replacement for the last usable draft. The logs and the returned
        # in-memory review gaps retain the failure for diagnosis.
        return RoutedDrafts(
            accepted=routed.accepted,
            review=routed.review,
            issues=routed.issues,
            output_dir=draft_dir if draft_dir.exists() else None,
            calibration=routed.calibration,
            micro_stats=batch.micro_stats,
        )
    draft_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix=f".{batch.document_id}.draft-", dir=str(draft_dir.parent)))
    try:
        if document is not None:
            write_outline_artifacts(document, config=settings, draft_dir=staging_dir)

        for kind in WRITE_KINDS:
            items = [obj.data for obj in batch.items(kind)]
            path = staging_dir / f"{kind}.yaml"
            if items:
                _write_yaml(path, items)

        _write_yaml(staging_dir / "provenance.yaml", [_provenance(obj) for obj in batch.objects])
        if batch.micro_stats:
            _write_yaml(staging_dir / "micro_extraction.yaml", batch.micro_stats)
            review_gaps = batch.micro_stats.get("review_gaps", [])
            if review_gaps:
                _write_yaml(staging_dir / "review_gaps.yaml", review_gaps)
        (staging_dir / "review.md").write_text(render_review(batch, routed), encoding="utf-8", newline="\n")
        write_metrics(staging_dir, build_metrics(batch, routed))
        if document is not None:
            write_review_html(staging_dir, batch=batch, routed=routed, document=document)
        _swap_staged_draft(staging_dir, draft_dir)
    except Exception:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        raise
    return RoutedDrafts(
        accepted=routed.accepted,
        review=routed.review,
        issues=routed.issues,
        output_dir=draft_dir,
        calibration=routed.calibration,
        micro_stats=batch.micro_stats,
    )


def render_review(batch: ExtractionBatch, routed: RoutedDrafts) -> str:
    """Render a human-review report."""
    lines = [
        f"# Extraction Review - {batch.document_id}",
        "",
        f"Tax year: {batch.year}",
        f"Auto-accepted drafts: {len(routed.accepted)}",
        f"Human-review drafts: {len(routed.review)}",
        f"Calibration sample: {len(routed.calibration)}",
        "",
        "Drafts remain under `_drafts` and must not be promoted without human review.",
        "",
        "## Auto-Accepted",
    ]
    lines.extend(_object_lines(routed.accepted, include_flags=False))
    lines.extend(["", "## Human Review"])
    lines.extend(_object_lines(routed.review, include_flags=True))
    lines.extend(["", "## Calibration Sample (audit these cold; escapes join the drill catalog)"])
    lines.extend(_object_lines(routed.calibration, include_flags=False))
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
        tier = obj.tier or "T0"
        lines.append(f"- {obj.kind}/{obj.object_id} tier={tier} confidence={obj.confidence:.3f}")
        if include_flags:
            for flag in obj.flags:
                lines.append(f"  - {flag}")
    return lines


def _provenance(obj: DraftObject) -> dict[str, Any]:
    record = {
        "kind": obj.kind,
        "object_id": obj.object_id,
        "source_span": obj.source_span,
        "extracted_by": obj.extracted_by,
        "confidence": obj.confidence,
        "critic_agrees": obj.critic_agrees,
        "flags": obj.flags,
        "tier": obj.tier,
    }
    if obj.requested_model is not None:
        record["requested_model"] = obj.requested_model
    if obj.resolved_model is not None:
        record["resolved_model"] = obj.resolved_model
    if obj.resolved_provider is not None:
        record["resolved_provider"] = obj.resolved_provider
    return record


def _write_yaml(path: Path, data: Any) -> None:
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=False)
    path.write_text(_assert_ascii(text), encoding="utf-8", newline="\n")


def _swap_staged_draft(staging_dir: Path, draft_dir: Path) -> None:
    """Replace a complete draft directory while retaining rollback on failure."""
    backup_dir: Path | None = None
    if draft_dir.exists():
        backup_dir = draft_dir.with_name(f".{draft_dir.name}.previous-{uuid.uuid4().hex}")
        try:
            _rename_with_retry(draft_dir, backup_dir)
        except PermissionError:
            _swap_staged_draft_contents(staging_dir, draft_dir)
            return
    try:
        _rename_with_retry(staging_dir, draft_dir)
    except Exception:
        if backup_dir is not None and not draft_dir.exists():
            _rename_with_retry(backup_dir, draft_dir)
        raise
    if backup_dir is not None and backup_dir.exists():
        shutil.rmtree(backup_dir)


def _swap_staged_draft_contents(staging_dir: Path, draft_dir: Path) -> None:
    """Fallback swap when Windows denies renaming the existing directory.

    The old files move into a backup directory inside the staged tree before
    any new file is installed. If an install fails, both sets are restored so
    callers never observe a half-written draft.
    """
    backup_dir = staging_dir / ".previous"
    backup_dir.mkdir()
    old_names: list[str] = []
    new_names: list[str] = []
    try:
        for child in _list_children_with_retry(draft_dir):
            _rename_with_retry(child, backup_dir / child.name)
            old_names.append(child.name)
        for child in _list_children_with_retry(staging_dir):
            if child == backup_dir:
                continue
            _rename_with_retry(child, draft_dir / child.name)
            new_names.append(child.name)
        shutil.rmtree(backup_dir)
        staging_dir.rmdir()
    except Exception:
        for name in reversed(new_names):
            installed = draft_dir / name
            if installed.exists():
                _rename_with_retry(installed, staging_dir / name)
        for name in old_names:
            saved = backup_dir / name
            if saved.exists():
                _rename_with_retry(saved, draft_dir / name)
        raise


def _rename_with_retry(source: Path, target: Path) -> None:
    """Retry short-lived Windows sharing/ACL races around draft swaps."""
    for attempt in range(4):
        try:
            source.rename(target)
            return
        except PermissionError:
            if attempt == 3:
                raise
            time.sleep(0.25)


def _list_children_with_retry(directory: Path) -> list[Path]:
    """List a draft directory through a short-lived Windows access race."""
    for attempt in range(4):
        try:
            return sorted(directory.iterdir(), key=lambda path: path.name)
        except PermissionError:
            if attempt == 3:
                raise
            time.sleep(0.25)
    return []


def _assert_ascii(text: str) -> str:
    text.encode("ascii")
    return text
