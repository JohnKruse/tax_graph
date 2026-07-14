"""Non-authoritative, schema-validated review resume state."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable

from workbench.schema import validate_session_state


def default_session(year: int, queue_id: str, units: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Create an in-memory default without claiming that review occurred."""
    unit_list = list(units)
    first = unit_list[0] if unit_list else None
    location = first.get("official_location") if isinstance(first, dict) else None
    return {
        "tax_year": year,
        "queue_id": queue_id,
        "current_unit_id": first.get("unit_id") if isinstance(first, dict) else None,
        "page": int(location.get("page", 1)) if isinstance(location, dict) else 1,
        "selection": None,
        "zoom": 1.0,
        "notes": "",
        "elapsed_active_seconds": 0,
        "visited_unit_ids": [],
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
    return payload


def save_session(path: str | Path, payload: dict[str, Any]) -> Path:
    """Validate and atomically replace one non-authoritative session file."""
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
