"""Deterministic, form-first canonical-address candidate generation."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable

import yaml

from tax_graph.addressing.registry import AddressComponent, serialize_address_id


def generate_candidate_registry(*, year: int, document_id: str, document_token: str,
                                source_path: str, source_hash: str,
                                controls: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Generate a byte-stable pending-review hierarchy from explicit form evidence."""
    root_path = (AddressComponent("document", document_token),)
    records: dict[str, dict[str, Any]] = {}
    root = _record(year, document_id, root_path, None, "document", "none", source_path, source_hash,
                   printed_label=document_token, status="pending_review")
    records[root["address_id"]] = root
    normalized = sorted((dict(item) for item in controls), key=_structural_sort_key)
    for control in normalized:
        path = root_path
        parent = root["address_id"]
        for component in _semantic_components(control):
            path = path + (component,)
            address_id = serialize_address_id(year, path)
            terminal = component == _semantic_components(control)[-1]
            if address_id not in records:
                kind = component.kind
                role = str(control.get("control_role", "other")) if terminal else "none"
                status = "provisional" if control.get("semantic_status") == "provisional" or (terminal and not control.get("official_ref")) else "pending_review"
                records[address_id] = _record(
                    year, document_id, path, parent, kind, role, source_path, source_hash,
                    official_ref=str(control["official_ref"]) if terminal and control.get("official_ref") else None,
                    printed_label=str(control.get("printed_label", "")) if terminal else str(component.token),
                    status=status,
                    evidence={key: control[key] for key in ("page", "rect", "field_name", "widget_type", "accessibility_label") if key in control},
                )
            parent = address_id
    return {"schema_version": 1, "year": year, "document_id": document_id,
            "addresses": [records[key] for key in sorted(records)]}


def write_candidate_registry(payload: dict[str, Any], root: str | Path) -> Path:
    """Write a candidate only inside the gitignored draft boundary."""
    path = Path(root) / "graph" / str(payload["year"]) / "_drafts" / "addresses" / f"{payload['document_id']}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False), encoding="utf-8", newline="\n"
    )
    return path


def _semantic_components(control: dict[str, Any]) -> tuple[AddressComponent, ...]:
    explicit = control.get("semantic_path")
    if explicit:
        return tuple(AddressComponent(str(item["kind"]), str(item["token"])) for item in explicit)
    official_ref = control.get("official_ref")
    role = str(control.get("control_role", "other"))
    if official_ref:
        return (AddressComponent("line", str(official_ref).lower()), AddressComponent("control", role))
    neutral = control.get("neutral_token")
    if neutral is None:
        stable = str(control.get("structural_key") or control.get("accessibility_label") or "unlabeled")
        neutral = hashlib.sha256(stable.encode("utf-8")).hexdigest()[:12]
    return (AddressComponent("section", str(control.get("section_token", "unlabeled"))), AddressComponent("option", str(neutral)))


def _structural_sort_key(item: dict[str, Any]) -> tuple[str, ...]:
    return tuple(f"{component.kind}={component.token}" for component in _semantic_components(item))


def _record(year: int, document_id: str, path: tuple[AddressComponent, ...], parent: str | None,
            kind: str, role: str, source_path: str, source_hash: str, *, official_ref: str | None = None,
            printed_label: str = "", status: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    source = {"source_path": source_path, "source_hash": source_hash}
    physical = evidence or {}
    if "page" in physical:
        source["page"] = physical["page"]
    if physical.get("accessibility_label"):
        source["quoted_text"] = str(physical["accessibility_label"])
    result = {
        "address_id": serialize_address_id(year, path), "logical_key": serialize_address_id(None, path),
        "year": year, "document_id": document_id, "parent_address_id": parent, "kind": kind,
        "path": [{"kind": item.kind, "token": item.token} for item in path],
        "printed_label": printed_label, "aliases": [], "control_role": role,
        "status": status, "evidence": [source],
    }
    if official_ref:
        result["official_ref"] = official_ref
    return result
