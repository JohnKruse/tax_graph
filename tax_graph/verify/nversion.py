"""N-version extraction corroboration for assembled draft objects."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tax_graph.config import get_config_value
from tax_graph.extract.llm_client import LlmClient
from tax_graph.extract.models import DraftObject, ExtractionBatch, SourceDocumentInput
from tax_graph.extract.outline_pipeline import generate_outline_first_drafts


@dataclass(frozen=True)
class ObjectDiff:
    """One object-level disagreement between two extraction versions."""

    kind: str
    object_id: str
    reason: str
    primary: dict[str, Any] | None
    secondary: dict[str, Any] | None


@dataclass(frozen=True)
class ReviewEntry:
    """Human review entry showing both N-version answers side by side."""

    kind: str
    object_id: str
    reason: str
    primary: dict[str, Any] | None
    secondary: dict[str, Any] | None


@dataclass(frozen=True)
class NVersionReport:
    """N-version corroboration result for one document."""

    document_id: str
    primary_model: str
    secondary_model: str
    primary_family: str
    secondary_family: str
    status: str
    diffs: tuple[ObjectDiff, ...]
    review_entries: tuple[ReviewEntry, ...]

    @property
    def ok(self) -> bool:
        """Return whether the two assembled versions agreed."""
        return self.status == "agreed"


def run_nversion_extraction(
    document: SourceDocumentInput,
    *,
    primary_client: LlmClient,
    secondary_client: LlmClient,
    config: dict[str, Any] | None = None,
    root: str | Path | None = None,
) -> NVersionReport:
    """Run primary and secondary outline-first extraction and diff assembled objects."""
    settings = config or {}
    primary_config = deepcopy(settings)
    secondary_config = _secondary_config(settings)
    primary_batch = generate_outline_first_drafts(
        document,
        client=primary_client,
        config=primary_config,
        root=root,
    )
    secondary_batch = generate_outline_first_drafts(
        document,
        client=secondary_client,
        config=secondary_config,
        root=root,
    )
    return compare_batches(
        document_id=document.document_id,
        primary=primary_batch,
        secondary=secondary_batch,
        primary_model=_configured_model(primary_config),
        secondary_model=_configured_model(secondary_config),
        primary_family=str(get_config_value(settings, "llm.vendor_family", "primary")),
        secondary_family=str(get_config_value(settings, "llm.nversion_vendor_family", "secondary")),
    )


def compare_batches(
    *,
    document_id: str,
    primary: ExtractionBatch,
    secondary: ExtractionBatch,
    primary_model: str,
    secondary_model: str,
    primary_family: str = "primary",
    secondary_family: str = "secondary",
) -> NVersionReport:
    """Diff two assembled extraction batches by canonical object identity."""
    primary_by_id = _batch_data_by_identity(primary)
    secondary_by_id = _batch_data_by_identity(secondary)
    diffs: list[ObjectDiff] = []
    for identity in sorted(set(primary_by_id).union(secondary_by_id)):
        left = primary_by_id.get(identity)
        right = secondary_by_id.get(identity)
        if left is None:
            diffs.append(ObjectDiff(identity[0], identity[1], "missing_primary", None, right))
        elif right is None:
            diffs.append(ObjectDiff(identity[0], identity[1], "missing_secondary", left, None))
        elif left != right:
            diffs.append(ObjectDiff(identity[0], identity[1], "payload_diff", left, right))
    review_entries = tuple(
        ReviewEntry(
            kind=diff.kind,
            object_id=diff.object_id,
            reason=diff.reason,
            primary=diff.primary,
            secondary=diff.secondary,
        )
        for diff in diffs
    )
    return NVersionReport(
        document_id=document_id,
        primary_model=primary_model,
        secondary_model=secondary_model,
        primary_family=primary_family,
        secondary_family=secondary_family,
        status="agreed" if not diffs else "disagreed",
        diffs=tuple(diffs),
        review_entries=review_entries,
    )


def corroboration_provenance(batch: ExtractionBatch, report: NVersionReport) -> list[dict[str, Any]]:
    """Return provenance records indicating N-version agreement or review routing."""
    diff_ids = {(diff.kind, diff.object_id): diff for diff in report.diffs}
    records: list[dict[str, Any]] = []
    for obj in batch.objects:
        diff = diff_ids.get((obj.kind, obj.object_id))
        records.append(
            {
                "kind": obj.kind,
                "object_id": obj.object_id,
                "nversion_status": "disagreed" if diff else "agreed",
                "primary_model": report.primary_model,
                "secondary_model": report.secondary_model,
                "primary_family": report.primary_family,
                "secondary_family": report.secondary_family,
                "reason": diff.reason if diff else "",
            }
        )
    return records


def _batch_data_by_identity(batch: ExtractionBatch) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (obj.kind, obj.object_id): _object_payload(obj)
        for obj in batch.objects
    }


def _object_payload(obj: DraftObject) -> dict[str, Any]:
    return deepcopy(obj.data)


def _secondary_config(settings: dict[str, Any]) -> dict[str, Any]:
    secondary = deepcopy(settings)
    nversion_model = get_config_value(settings, "llm.nversion_model")
    if nversion_model:
        secondary.setdefault("llm", {})["micro_model"] = nversion_model
        secondary.setdefault("llm", {})["model"] = nversion_model
    return secondary


def _configured_model(settings: dict[str, Any]) -> str:
    model = get_config_value(settings, "llm.micro_model") or get_config_value(settings, "llm.model")
    return str(model or "configured-llm")
