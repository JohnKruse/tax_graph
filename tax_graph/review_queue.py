"""Helpers for the committed deferred-review queue."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Iterable

import yaml


_DRAFT_OBJECT_KEYS = {
    "node": "node_id",
    "citation": "citation_id",
}
_MIN_MATCH_CHARS = 16
_MIN_MATCH_WORDS = 3


@dataclass(frozen=True)
class QueueReconciliationResult:
    """Counts and output path from one generated-review queue reconciliation."""

    queue_path: Path
    migrated: int
    orphaned: int
    orphaned_by_reason: dict[str, int]


def upsert_deferred_review_entry(
    *,
    root: str | Path,
    year: str | int,
    entry: dict[str, Any],
) -> Path:
    """Insert or replace one deferred-review entry by ``queue_id``."""
    return upsert_deferred_review_entries(root=root, year=year, entries=(entry,))


def upsert_deferred_review_entries(
    *,
    root: str | Path,
    year: str | int,
    entries: Iterable[dict[str, Any]],
) -> Path:
    """Insert or replace multiple deferred-review entries in one write."""
    new_entries = tuple(dict(entry) for entry in entries)
    root_path = Path(root).resolve()
    queue_path = root_path / "review_queue" / str(year) / "deferred_review.yaml"
    payload = _load_yaml(queue_path)
    if not isinstance(payload, dict):
        payload = {}
    existing_entries = payload.get("entries")
    if not isinstance(existing_entries, list):
        existing_entries = []
    updated = [item for item in existing_entries if isinstance(item, dict)]
    for entry in new_entries:
        queue_id = str(entry["queue_id"])
        replacement = dict(entry)
        for index, item in enumerate(updated):
            if str(item.get("queue_id")) == queue_id:
                updated[index] = replacement
                break
        else:
            updated.append(replacement)
    _write_yaml(
        queue_path,
        {
            "tax_year": int(year),
            "entries": updated,
        },
    )
    return queue_path


def reconcile_generated_review_queue(
    *,
    root: str | Path,
    year: str | int,
) -> QueueReconciliationResult:
    """Reconcile pending extraction scopes against settled draft object ids.

    Generated ids are not semantic identity. A missing old id is moved only when
    exactly one current object in the same document contains the old evidence,
    and the old id is retained in the destination ref's ``aliases``. A citation
    whose id was reused with changed evidence is a finding, not a rename. Missing,
    ambiguous, and dependency-unsafe refs are persisted in the queue's ``orphaned``
    bucket and removed from the active review scope.
    """
    root_path = Path(root).resolve()
    queue_path = root_path / "review_queue" / str(year) / "deferred_review.yaml"
    payload = _load_yaml(queue_path)
    if not isinstance(payload, dict):
        raise ValueError(f"review queue must be a mapping: {queue_path}")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError(f"review queue entries must be a list: {queue_path}")

    live_objects = _load_live_draft_objects(root_path, year)
    orphaned = payload.get("orphaned", [])
    if not isinstance(orphaned, list):
        raise ValueError(f"review queue orphaned bucket must be a list: {queue_path}")
    existing_orphans = {
        (
            str(item.get("queue_id")),
            str((item.get("original_ref") or {}).get("object_type")),
            str((item.get("original_ref") or {}).get("object_id")),
            str(item.get("reason")),
        )
        for item in orphaned
        if isinstance(item, dict)
    }

    reasons: Counter[str] = Counter()
    for entry in entries:
        if not isinstance(entry, dict) or not _pending_promotion(entry):
            continue
        scope = entry.get("review_scope")
        if not isinstance(scope, dict):
            continue
        refs = scope.get("object_refs")
        if not isinstance(refs, list):
            continue
        document_id = str(entry.get("document_id") or "")
        current = _load_draft_objects(root_path, year, document_id)
        if not current:
            continue
        unsafe_citations = _changed_citation_ids(live_objects["citation"], current["citation"])
        active_refs: list[dict[str, Any]] = []
        used_targets: set[tuple[str, str]] = {
            (str(ref.get("object_type") or ""), str(ref.get("object_id") or ""))
            for ref in refs
            if isinstance(ref, dict)
            and (
                str(ref.get("object_type") or "") not in _DRAFT_OBJECT_KEYS
                or (
                    str(ref.get("object_id") or "") in current.get(str(ref.get("object_type") or ""), {})
                    and not (
                        str(ref.get("object_type") or "") == "citation"
                        and str(ref.get("object_id") or "") in unsafe_citations
                    )
                )
            )
        }

        for ref in refs:
            if not isinstance(ref, dict):
                continue
            object_type = str(ref.get("object_type") or "")
            object_id = str(ref.get("object_id") or "")
            if object_type not in _DRAFT_OBJECT_KEYS or "/_drafts/" not in str(ref.get("source_path") or ""):
                active_refs.append(ref)
                used_targets.add((object_type, object_id))
                continue

            current_objects = current[object_type]
            current_object = current_objects.get(object_id)
            if current_object is not None:
                if object_type == "citation" and object_id in unsafe_citations:
                    _record_orphan(
                        orphaned,
                        existing_orphans,
                        entry,
                        ref,
                        reason="same_id_reused_with_changed_citation_evidence",
                        settled_ref=ref,
                        reasons=reasons,
                    )
                    continue
                active_refs.append(ref)
                used_targets.add((object_type, object_id))
                continue

            old_object = live_objects[object_type].get(object_id)
            if old_object is None:
                _record_orphan(
                    orphaned,
                    existing_orphans,
                    entry,
                    ref,
                    reason="missing_old_source",
                    reasons=reasons,
                )
                continue

            candidates = _content_candidates(
                object_type,
                old_object,
                current_objects,
                excluded=unsafe_citations if object_type == "citation" else set(),
            )
            if not _usable_match_text(object_type, old_object):
                reason = "insufficient_evidence_for_unique_match"
            elif len(candidates) > 1:
                reason = "ambiguous_content_match"
            elif not candidates:
                reason = "no_certain_content_match"
            elif (object_type, candidates[0]) in used_targets:
                reason = "multiple_old_reviews_matched_one_destination"
            else:
                replacement = dict(ref)
                replacement["object_id"] = candidates[0]
                aliases = list(replacement.get("aliases", []) or [])
                if object_id not in aliases:
                    aliases.append(object_id)
                replacement["aliases"] = sorted(set(str(alias) for alias in aliases))
                active_refs.append(replacement)
                used_targets.add((object_type, candidates[0]))
                continue
            _record_orphan(
                orphaned,
                existing_orphans,
                entry,
                ref,
                reason=reason,
                candidate_object_ids=candidates,
                reasons=reasons,
            )

        active_refs = _drop_unsafe_node_refs(
            active_refs,
            current=current,
            unsafe_citations=unsafe_citations,
            live_citations=live_objects["citation"],
            entry=entry,
            orphaned=orphaned,
            existing_orphans=existing_orphans,
            reasons=reasons,
        )
        scope["object_refs"] = active_refs

    payload["entries"] = entries
    payload["orphaned"] = orphaned
    _write_yaml(queue_path, payload)
    migration_aliases = {
        str(alias)
        for entry in entries
        if isinstance(entry, dict) and _pending_promotion(entry)
        for ref in (entry.get("review_scope") or {}).get("object_refs", []) or []
        if isinstance(ref, dict)
        for alias in ref.get("aliases", []) or []
    }
    final_reasons = Counter(
        str(item.get("reason"))
        for item in orphaned
        if isinstance(item, dict) and item.get("reason")
    )
    return QueueReconciliationResult(
        queue_path=queue_path,
        migrated=len(migration_aliases),
        orphaned=len(orphaned),
        orphaned_by_reason=dict(sorted(final_reasons.items())),
    )


def _pending_promotion(entry: dict[str, Any]) -> bool:
    """Return whether an entry is an active extracted promotion review."""
    status = str(entry.get("status") or entry.get("review_status") or "")
    return status == "pending" and str(entry.get("kind") or "") == "promotion_review"


def _load_live_draft_objects(root: Path, year: str | int) -> dict[str, dict[str, dict[str, Any]]]:
    """Load promoted node and citation payloads used as the old review witness."""
    result: dict[str, dict[str, dict[str, Any]]] = {kind: {} for kind in _DRAFT_OBJECT_KEYS}
    for kind, directory in (("node", "nodes"), ("citation", "citations")):
        key = _DRAFT_OBJECT_KEYS[kind]
        for path in (root / "graph" / str(year) / directory).glob("*.yaml"):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
            if not isinstance(data, list):
                continue
            result[kind].update(
                {
                    str(item[key]): item
                    for item in data
                    if isinstance(item, dict) and item.get(key)
                }
            )
    return result


def _load_draft_objects(
    root: Path,
    year: str | int,
    document_id: str,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Load the settled generated objects for one form document."""
    result: dict[str, dict[str, dict[str, Any]]] = {kind: {} for kind in _DRAFT_OBJECT_KEYS}
    draft_dir = root / "graph" / str(year) / "_drafts" / document_id
    for kind, filename in (("node", "nodes.yaml"), ("citation", "citations.yaml")):
        path = draft_dir / filename
        if not path.is_file():
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        if not isinstance(data, list):
            continue
        key = _DRAFT_OBJECT_KEYS[kind]
        result[kind] = {
            str(item[key]): item
            for item in data
            if isinstance(item, dict) and item.get(key)
        }
    return result


def _changed_citation_ids(
    live: dict[str, dict[str, Any]],
    current: dict[str, dict[str, Any]],
) -> set[str]:
    """Return same-id citations whose source evidence or locator changed."""
    changed: set[str] = set()
    for object_id, current_item in current.items():
        old_item = live.get(object_id)
        if old_item is not None and any(
            old_item.get(key) != current_item.get(key)
            for key in ("quoted_text", "locator", "source_document_id")
        ):
            changed.add(object_id)
    return changed


def _content_candidates(
    object_type: str,
    old_object: dict[str, Any],
    current_objects: dict[str, dict[str, Any]],
    *,
    excluded: set[str],
) -> list[str]:
    """Find current objects containing the old evidence, without using position."""
    old_text = _evidence_text(object_type, old_object)
    if not old_text:
        return []
    candidates: list[str] = []
    for object_id, current_object in current_objects.items():
        if object_id in excluded:
            continue
        current_text = _evidence_text(object_type, current_object)
        if old_text == current_text or old_text in current_text or current_text in old_text:
            candidates.append(object_id)
    return sorted(candidates)


def _evidence_text(object_type: str, item: dict[str, Any]) -> str:
    """Normalize evidence while ignoring only generated line-label wrappers."""
    value = item.get("quoted_text") if object_type == "citation" else item.get("label")
    text = re.sub(r"\s+", " ", str(value or "").strip().lower())
    if object_type == "node":
        text = re.sub(r"^line\s+[0-9a-z]+:\s*", "", text)
    return text


def _usable_match_text(object_type: str, item: dict[str, Any]) -> bool:
    """Reject short labels that cannot establish a unique evidence identity."""
    text = _evidence_text(object_type, item)
    return len(text) >= _MIN_MATCH_CHARS and len(text.split()) >= _MIN_MATCH_WORDS


def _drop_unsafe_node_refs(
    refs: list[dict[str, Any]],
    *,
    current: dict[str, dict[str, dict[str, Any]]],
    unsafe_citations: set[str],
    live_citations: dict[str, dict[str, Any]],
    entry: dict[str, Any],
    orphaned: list[dict[str, Any]],
    existing_orphans: set[tuple[str, str, str, str]],
    reasons: Counter[str],
) -> list[dict[str, Any]]:
    """Orphan nodes whose supporting generated citation is not safely settled."""
    active_citations = {
        str(ref.get("object_id"))
        for ref in refs
        if ref.get("object_type") == "citation"
    }
    result: list[dict[str, Any]] = []
    for ref in refs:
        if ref.get("object_type") != "node" or "/_drafts/" not in str(ref.get("source_path") or ""):
            result.append(ref)
            continue
        node = current["node"].get(str(ref.get("object_id")), {})
        citations = {str(value) for value in node.get("citation_refs", []) or []}
        unsafe = citations & unsafe_citations
        uncovered = {
            citation_id
            for citation_id in citations
            if citation_id not in active_citations and citation_id not in live_citations
        }
        if unsafe or uncovered:
            reason = "supporting_citation_changed" if unsafe else "supporting_citation_not_settled"
            candidates = sorted(unsafe | uncovered)
            _record_orphan(
                orphaned,
                existing_orphans,
                entry,
                ref,
                reason=reason,
                candidate_object_ids=candidates,
                reasons=reasons,
            )
            continue
        result.append(ref)
    return result


def _record_orphan(
    orphaned: list[dict[str, Any]],
    existing_orphans: set[tuple[str, str, str, str]],
    entry: dict[str, Any],
    original_ref: dict[str, Any],
    *,
    reason: str,
    candidate_object_ids: Iterable[str] = (),
    settled_ref: dict[str, Any] | None = None,
    reasons: Counter[str],
) -> None:
    """Persist one fail-closed orphan record and count its reason."""
    queue_id = str(entry.get("queue_id") or "")
    object_type = str(original_ref.get("object_type") or "")
    object_id = str(original_ref.get("object_id") or "")
    key = (queue_id, object_type, object_id, reason)
    if key not in existing_orphans:
        record: dict[str, Any] = {
            "queue_id": queue_id,
            "document_id": str(entry.get("document_id") or ""),
            "status": "orphaned",
            "reason": reason,
            "original_ref": dict(original_ref),
        }
        candidates = sorted(set(str(value) for value in candidate_object_ids))
        if candidates:
            record["candidate_object_ids"] = candidates
        if settled_ref is not None:
            record["settled_ref"] = dict(settled_ref)
        orphaned.append(record)
        existing_orphans.add(key)
    reasons[reason] += 1


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)
