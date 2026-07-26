"""Non-authoritative, schema-validated review resume state."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable

from workbench.manifest import unit_identity_key
from workbench.schema import validate_session_state


def manifest_unit_ids(units: Iterable[dict[str, Any]]) -> frozenset[str]:
    """Return the unit ids in one manifest entry."""
    return frozenset(
        str(unit["unit_id"])
        for unit in units
        if isinstance(unit, dict) and unit.get("unit_id") is not None
    )


def validate_unit_review_scope(
    payload: dict[str, Any], units: Iterable[dict[str, Any]],
) -> None:
    """Reject review records that are not scoped to the manifest entry."""
    reviews = payload.get("unit_reviews", {})
    if not isinstance(reviews, dict):
        return
    unknown = sorted(set(reviews) - manifest_unit_ids(units))
    if unknown:
        raise ValueError(
            "session reviews units outside the queue entry: "
            + ", ".join(unknown)
        )


def session_progress(
    payload: dict[str, Any], units: Iterable[dict[str, Any]],
) -> dict[str, int]:
    """Derive approved and total unit counts without storing a summary."""
    unit_list = list(units)
    validate_unit_review_scope(payload, unit_list)
    unit_ids = manifest_unit_ids(unit_list)
    reviews = payload.get("unit_reviews", {})
    approved = sum(
        1
        for unit_id in unit_ids
        if isinstance(reviews, dict)
        and isinstance(reviews.get(unit_id), dict)
        and reviews[unit_id].get("status") == "approved"
    )
    return {"approved": approved, "total": len(unit_ids)}


def set_unit_review(
    payload: dict[str, Any],
    unit_id: str,
    units: Iterable[dict[str, Any]],
    *,
    approved: bool,
    note: str = "",
    updated_at: str | None = None,
) -> dict[str, Any]:
    """Set one scoped unit's approval and note in mutable session state."""
    unit_ids = manifest_unit_ids(units)
    if unit_id not in unit_ids:
        raise ValueError(f"unit_id is outside the queue entry: {unit_id}")
    reviews = payload.setdefault("unit_reviews", {})
    if not isinstance(reviews, dict):
        raise ValueError("session unit_reviews must be an object")
    reviews[unit_id] = {
        "status": "approved" if approved else "open",
        "note": note,
        "updated_at": updated_at or _now(),
    }
    return payload


def set_unit_approval(
    payload: dict[str, Any],
    unit_id: str,
    units: Iterable[dict[str, Any]],
    approved: bool,
    *,
    updated_at: str | None = None,
) -> dict[str, Any]:
    """Set approval while preserving the unit's existing note."""
    current = payload.get("unit_reviews", {}).get(unit_id, {})
    note = current.get("note", "") if isinstance(current, dict) else ""
    return set_unit_review(
        payload, unit_id, units, approved=approved, note=note, updated_at=updated_at,
    )


def set_unit_note(
    payload: dict[str, Any],
    unit_id: str,
    units: Iterable[dict[str, Any]],
    note: str,
    *,
    updated_at: str | None = None,
) -> dict[str, Any]:
    """Set a unit note while preserving its current approval status."""
    current = payload.get("unit_reviews", {}).get(unit_id, {})
    approved = isinstance(current, dict) and current.get("status") == "approved"
    return set_unit_review(
        payload, unit_id, units, approved=approved, note=note, updated_at=updated_at,
    )


def clear_unit_review(
    payload: dict[str, Any], unit_id: str, units: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Clear one scoped unit's mutable approval and note."""
    if unit_id not in manifest_unit_ids(units):
        raise ValueError(f"unit_id is outside the queue entry: {unit_id}")
    reviews = payload.get("unit_reviews", {})
    if isinstance(reviews, dict):
        reviews.pop(unit_id, None)
    return payload


def migrate_session_reviews(
    payload: dict[str, Any],
    old_units: Iterable[dict[str, Any]],
    new_units: list[dict[str, Any]],
) -> dict[str, Any]:
    """Migrate review records by identity and orphan uncertain records.

    The old manifest is required because a positional unit id cannot be
    decoded on its own. A record moves only when exactly one old unit and one
    new unit share the same non-positional identity key. The old id is added
    to the destination unit's ``aliases`` for auditability. Missing or
    ambiguous matches remain visible in ``orphaned_unit_reviews`` and never
    count as approved progress.
    """
    old_unit_list = list(old_units)
    new_by_id = {
        str(unit.get("unit_id")): unit
        for unit in new_units
        if isinstance(unit, dict) and unit.get("unit_id")
    }
    old_by_id = {
        str(unit.get("unit_id")): unit
        for unit in old_unit_list
        if isinstance(unit, dict) and unit.get("unit_id")
    }
    identity_matches: dict[str, list[dict[str, Any]]] = {}
    for unit in new_units:
        if not isinstance(unit, dict):
            continue
        identity = unit_identity_key(unit)
        if identity:
            identity_matches.setdefault(identity, []).append(unit)

    reviews = payload.get("unit_reviews", {})
    if not isinstance(reviews, dict):
        raise ValueError("session unit_reviews must be an object")
    migrated: dict[str, Any] = {}
    orphaned = payload.get("orphaned_unit_reviews", {})
    if not isinstance(orphaned, dict):
        raise ValueError("session orphaned_unit_reviews must be an object")
    orphaned = dict(orphaned)
    used_targets: set[str] = set()
    for old_id, review in reviews.items():
        old_id = str(old_id)
        if old_id in new_by_id:
            migrated[old_id] = review
            used_targets.add(old_id)
            continue
        old_unit = old_by_id.get(old_id)
        identity = unit_identity_key(old_unit) if old_unit else None
        candidates = identity_matches.get(identity or "", [])
        if len(candidates) == 1 and str(candidates[0]["unit_id"]) not in used_targets:
            destination = candidates[0]
            destination_id = str(destination["unit_id"])
            migrated[destination_id] = review
            used_targets.add(destination_id)
            aliases = destination.setdefault("aliases", [])
            if old_id not in aliases:
                aliases.append(old_id)
            continue
        reason = "no certain identity match"
        if len(candidates) > 1:
            reason = "ambiguous identity match"
        elif candidates:
            reason = "multiple old reviews matched one destination"
        orphaned[old_id] = {
            "status": "orphaned",
            "note": str(review.get("note", "")) if isinstance(review, dict) else "",
            "updated_at": str(review.get("updated_at", _now())) if isinstance(review, dict) else _now(),
            "reason": reason,
            "original_unit_id": old_id,
        }
    payload["unit_reviews"] = migrated
    payload["orphaned_unit_reviews"] = orphaned
    return payload


def migrate_manifest_session(
    payload: dict[str, Any],
    old_manifest: dict[str, Any],
    new_manifest: dict[str, Any],
    queue_id: str,
) -> dict[str, Any]:
    """Migrate one queue session using the old and rebuilt manifest entries."""
    def entry_units(manifest: dict[str, Any]) -> list[dict[str, Any]]:
        for entry in manifest.get("entries", []) or []:
            if isinstance(entry, dict) and str(entry.get("queue_id")) == queue_id:
                return [unit for unit in entry.get("units", []) or [] if isinstance(unit, dict)]
        raise ValueError(f"manifest has no queue entry: {queue_id}")

    return migrate_session_reviews(payload, entry_units(old_manifest), entry_units(new_manifest))


def _now() -> str:
    """Return a UTC timestamp suitable for a review record."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_session(
    year: int,
    queue_id: str,
    manifest_hash: str,
    units: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Create an in-memory default without claiming that review occurred."""
    unit_list = list(units)
    first = unit_list[0] if unit_list else None
    location = first.get("official_location") if isinstance(first, dict) else None
    return {
        "tax_year": year,
        "queue_id": queue_id,
        "manifest_hash": manifest_hash,
        "current_unit_id": first.get("unit_id") if isinstance(first, dict) else None,
        "page": int(location.get("page", 1)) if isinstance(location, dict) else 1,
        "selection": None,
        "zoom": 1.0,
        "notes": "",
        "elapsed_active_seconds": 0,
        "visited_unit_ids": [],
        "unit_reviews": {},
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def load_session(path: str | Path) -> dict[str, Any] | None:
    """Load and validate one saved session, or return None when absent."""
    session_path = Path(path)
    if not session_path.is_file():
        return None
    try:
        payload = json.loads(session_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read session state: {exc}") from exc
    validate_session_state(payload)
    payload.setdefault("unit_reviews", {})
    return payload


def save_session(path: str | Path, payload: dict[str, Any]) -> Path:
    """Validate and atomically replace one non-authoritative session file."""
    payload = dict(payload)
    payload.setdefault("unit_reviews", {})
    validate_session_state(payload)
    session_path = Path(path)
    session_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = session_path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(session_path)
    return session_path
