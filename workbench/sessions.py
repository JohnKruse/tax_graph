"""Non-authoritative, schema-validated review resume state."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable

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
