"""Short, quotable, ASCII references for review units.

A review unit's canonical address is unambiguous but long
(``2025/document=schedule_2/line=4/control=amount``). Reviewers need a short handle
they can type into one cell's note to cite another cell exactly. This module derives
that handle deterministically from the canonical address, so it is stable across runs
and unique within a document. It is projection-only: it reads addresses and writes
nothing.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping
from urllib.parse import unquote


def _parse_address(address_id: str) -> list[tuple[str, str]] | None:
    """Parse a canonical year-scoped address into (kind, token) pairs, or None.

    This is a read-only, stdlib-only reader of the canonical serialization
    (``year/kind=token/...`` with urllib-quoted tokens). The workbench must not
    import the pipeline package, so it does not reuse the addressing parser; it only
    needs to split a string it never round-trips. Non-canonical input returns None.
    """
    parts = address_id.split("/")
    if len(parts) < 2 or not parts[0].isdigit():
        return None
    components: list[tuple[str, str]] = []
    for part in parts[1:]:
        kind, separator, encoded = part.partition("=")
        if not separator or not kind:
            return None
        components.append((kind, unquote(encoded)))
    return components


def abbreviate_document(token: str) -> str:
    """Return a short, injective abbreviation of a document token.

    ``form_`` is dropped, ``schedule_`` becomes ``sch``, and separators are removed:
    ``form_1040`` -> ``1040``, ``schedule_2`` -> ``sch2``, ``form_1099_div`` ->
    ``1099div``, ``form_13614_c`` -> ``13614c``.
    """
    lowered = token.lower()
    if lowered.startswith("schedule_"):
        return "sch" + lowered[len("schedule_"):].replace("_", "")
    if lowered.startswith("form_"):
        return lowered[len("form_"):].replace("_", "")
    return lowered.replace("_", "")


def unit_ref_from_address(address_id: str) -> str | None:
    """Derive a short ASCII ref from a canonical address, or None if not derivable.

    The document component is abbreviated; every other component keeps its token, so
    the ref preserves the address's distinguishing structure and stays unique within a
    document. Returns None for a non-canonical or empty address rather than guessing.
    """
    if not address_id:
        return None
    components = _parse_address(address_id)
    if not components:
        return None
    parts = [
        abbreviate_document(token) if kind == "document" else token
        for kind, token in components
    ]
    ref = "/".join(parts)
    if not ref or not ref.isascii():
        return None
    return ref


def ambiguous_refs(units: Iterable[Mapping[str, Any]]) -> dict[str, list[str]]:
    """Return refs that map to more than one distinct address (true collisions).

    The contract a quotable ref must keep is that it names exactly one cell. Several
    review units can legitimately point at the SAME address - the same cell reviewed
    under different review kinds - and they correctly share a ref; that is not a
    collision. Only a ref that resolves to two DIFFERENT addresses is ambiguous and
    must fail closed. An empty result means every ref names exactly one cell.
    """
    by_ref: dict[str, set[str]] = {}
    for unit in units:
        ref = unit.get("ref")
        if not ref:
            continue
        by_ref.setdefault(str(ref), set()).add(str(unit.get("address_id", "")))
    return {ref: sorted(addresses) for ref, addresses in by_ref.items() if len(addresses) > 1}
