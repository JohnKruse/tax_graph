"""Cross-year canonical-address deltas keyed by yearless logical identity."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import hashlib
import json
from typing import Any, Iterable

from tax_graph.addressing.registry import CanonicalAddress


DELTA_STATES = frozenset({"unchanged", "added", "removed", "renumbered", "split", "merged", "unresolved"})


@dataclass(frozen=True)
class DeltaHint:
    """Explicit reviewed relationship between old and new logical keys."""

    state: str
    old_logical_keys: tuple[str, ...]
    new_logical_keys: tuple[str, ...]


def address_delta(
    previous: Iterable[CanonicalAddress],
    current: Iterable[CanonicalAddress],
    *,
    hints: Iterable[DeltaHint] = (),
    suggestion_limit: int = 3,
) -> dict[str, Any]:
    """Return a byte-stable cross-year delta without fuzzy trust inheritance."""
    old = _by_logical_key(previous, "previous")
    new = _by_logical_key(current, "current")
    remaining_old = set(old)
    remaining_new = set(new)
    rows: list[dict[str, Any]] = []
    for logical_key in sorted(remaining_old & remaining_new):
        rows.append(_row("unchanged", (logical_key,), (logical_key,), inherited_trust=True))
        remaining_old.remove(logical_key)
        remaining_new.remove(logical_key)
    for hint in sorted(hints, key=lambda item: (item.state, item.old_logical_keys, item.new_logical_keys)):
        _validate_hint(hint, remaining_old, remaining_new)
        rows.append(_row(hint.state, hint.old_logical_keys, hint.new_logical_keys, inherited_trust=False))
        remaining_old.difference_update(hint.old_logical_keys)
        remaining_new.difference_update(hint.new_logical_keys)
    for logical_key in sorted(remaining_old):
        suggestions = _suggest(logical_key, remaining_new, suggestion_limit)
        rows.append(_row("removed", (logical_key,), (), inherited_trust=False, suggestions=suggestions))
    for logical_key in sorted(remaining_new):
        rows.append(_row("added", (), (logical_key,), inherited_trust=False))
    rows.sort(key=lambda item: (item["state"], item["old_logical_keys"], item["new_logical_keys"]))
    payload = {"schema_version": 1, "results": rows}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
    payload["report_hash"] = hashlib.sha256(canonical).hexdigest()
    return payload


def _by_logical_key(addresses: Iterable[CanonicalAddress], label: str) -> dict[str, CanonicalAddress]:
    result: dict[str, CanonicalAddress] = {}
    for address in addresses:
        if address.logical_key in result:
            raise ValueError(f"duplicate {label} logical key: {address.logical_key}")
        result[address.logical_key] = address
    return result


def _validate_hint(hint: DeltaHint, old: set[str], new: set[str]) -> None:
    if hint.state not in {"renumbered", "split", "merged", "unresolved"}:
        raise ValueError(f"invalid explicit delta state: {hint.state}")
    if not set(hint.old_logical_keys) <= old or not set(hint.new_logical_keys) <= new:
        raise ValueError(f"delta hint refers to missing or already-consumed keys: {hint}")
    cardinality = (len(hint.old_logical_keys), len(hint.new_logical_keys))
    valid = {
        "renumbered": cardinality == (1, 1),
        "split": cardinality[0] == 1 and cardinality[1] > 1,
        "merged": cardinality[0] > 1 and cardinality[1] == 1,
        "unresolved": cardinality[0] > 0 or cardinality[1] > 0,
    }
    if not valid[hint.state]:
        raise ValueError(f"invalid {hint.state} cardinality: {cardinality}")


def _suggest(logical_key: str, candidates: set[str], limit: int) -> list[dict[str, Any]]:
    ranked = sorted(
        ((SequenceMatcher(None, logical_key, candidate).ratio(), candidate) for candidate in candidates),
        key=lambda item: (-item[0], item[1]),
    )
    return [
        {"logical_key": candidate, "score": round(score, 6), "authoritative": False}
        for score, candidate in ranked[:limit]
    ]


def _row(state: str, old: tuple[str, ...], new: tuple[str, ...], *, inherited_trust: bool,
         suggestions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "state": state,
        "old_logical_keys": list(old),
        "new_logical_keys": list(new),
        "inherited_trust": inherited_trust,
    }
    if suggestions:
        result["suggestions"] = suggestions
    return result
