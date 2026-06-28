"""Change detection for acquired source documents."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from tax_graph.acquire.fetch import FetchedDocument


@dataclass(frozen=True)
class DocumentState:
    """Persisted acquisition state for one document."""

    content_hash: str
    retrieved_date: str
    url: str


@dataclass(frozen=True)
class ChangeReport:
    """Classification of fetched documents against previous state."""

    new: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)

    def has_changes(self) -> bool:
        """Return whether any document is new or changed."""
        return bool(self.new or self.changed)


def state_path(raw_store: str | Path, year: str | int) -> Path:
    """Return the persisted state path for a raw store and tax year."""
    return Path(raw_store) / str(year) / "_state.json"


def load_state(raw_store: str | Path, year: str | int) -> dict[str, DocumentState]:
    """Load acquisition state, returning an empty mapping if absent."""
    path = state_path(raw_store, year)
    if not path.exists():
        return {}

    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        document_id: DocumentState(
            content_hash=entry["content_hash"],
            retrieved_date=entry["retrieved_date"],
            url=entry["url"],
        )
        for document_id, entry in data.items()
    }


def write_state(raw_store: str | Path, year: str | int, state: dict[str, DocumentState]) -> None:
    """Persist acquisition state."""
    path = state_path(raw_store, year)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        document_id: {
            "content_hash": entry.content_hash,
            "retrieved_date": entry.retrieved_date,
            "url": entry.url,
        }
        for document_id, entry in sorted(state.items())
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def detect_changes(
    fetched: list[FetchedDocument] | tuple[FetchedDocument, ...],
    *,
    raw_store: str | Path,
    year: str | int,
    check: bool = False,
) -> ChangeReport:
    """Compare fetched documents to persisted state and optionally update it."""
    previous = load_state(raw_store, year)
    next_state = dict(previous)
    new: list[str] = []
    changed: list[str] = []
    unchanged: list[str] = []

    for document in fetched:
        prior = previous.get(document.document_id)
        current = DocumentState(
            content_hash=document.content_hash,
            retrieved_date=document.retrieved_date,
            url=document.url,
        )
        if prior is None:
            new.append(document.document_id)
        elif prior.content_hash != document.content_hash:
            changed.append(document.document_id)
        else:
            unchanged.append(document.document_id)
        next_state[document.document_id] = current

    report = ChangeReport(
        new=sorted(new),
        changed=sorted(changed),
        unchanged=sorted(unchanged),
    )
    if not check:
        write_state(raw_store, year, next_state)
    return report
