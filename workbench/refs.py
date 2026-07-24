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

from tax_graph.addressing import parse_address_id
from tax_graph.addressing.registry import AddressError


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
    try:
        _year, components = parse_address_id(address_id)
    except AddressError:
        return None
    parts = [
        abbreviate_document(component.token)
        if component.kind == "document"
        else component.token
        for component in components
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
