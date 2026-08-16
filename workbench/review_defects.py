"""Append-only local defect reports emitted by the review workbench."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from threading import RLock
from typing import Any, Iterable, Mapping


_WRITE_LOCK = RLock()


def defect_queue_path(root: str | Path, year: str | int) -> Path:
    """Return the local queue path for rejected generated cells."""
    return Path(root).resolve() / "review_queue" / str(year) / "workbench_defects.jsonl"


def append_defect_report(
    *,
    root: str | Path,
    year: str | int,
    report: Mapping[str, Any],
    path: str | Path | None = None,
) -> dict[str, Any]:
    """Append one ASCII JSON defect report and return the stored payload."""
    payload = dict(report)
    payload.setdefault(
        "reported_at",
        datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    )
    if not str(payload.get("report_id") or "").strip():
        raise ValueError("defect report requires report_id")
    if not str(payload.get("address") or "").strip():
        raise ValueError("defect report requires address")
    line = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    line.encode("ascii")
    queue_path = Path(path).resolve() if path is not None else defect_queue_path(root, year)
    with _WRITE_LOCK:
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        with queue_path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(line + "\n")
    return payload


def load_defect_reports(path: str | Path) -> list[dict[str, Any]]:
    """Load local defect reports without changing or deduplicating them."""
    report_path = Path(path)
    if not report_path.is_file():
        return []
    reports: list[dict[str, Any]] = []
    for line_number, line in enumerate(report_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid defect report JSON at {report_path}:{line_number}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"defect report must be an object at {report_path}:{line_number}")
        reports.append(value)
    return reports


def summarize_attempts(attempts: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Keep the model result history compact while retaining review evidence."""
    result: list[dict[str, Any]] = []
    for attempt in attempts:
        result.append({
            "attempt_id": str(attempt.get("attempt_id") or ""),
            "line": str(attempt.get("line") or ""),
            "comment": str(attempt.get("comment") or ""),
            "comment_source": str(attempt.get("comment_source") or "none"),
            "result": attempt.get("result"),
            "validation": attempt.get("validation"),
        })
    return result
