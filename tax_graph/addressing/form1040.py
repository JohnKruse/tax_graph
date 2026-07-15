"""Build the real Form 1040 address candidate and Gate A review payload."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
from typing import Any

import yaml

from tax_graph.addressing.candidates import generate_candidate_registry


FORM_1040_SHA256 = "3d31c226df0d189ced80e039d01cf0f8820c1019681a0f0ca6264de277b7e982"


def build_form_1040_review(root: str | Path) -> dict[str, Any]:
    """Reconcile all inventoried controls to a candidate address or explicit exemption."""
    root_path = Path(root)
    field_map = yaml.safe_load((root_path / "graph/2025/field_maps/form_1040_2025.yaml").read_text(encoding="utf-8"))
    inventory = json.loads((root_path / field_map["inventory"]).read_text(encoding="utf-8"))["fields"]
    mappings = {item["field_name"]: item for item in field_map.get("mappings", [])}
    dispositions = {item["field_name"]: item for item in field_map["field_dispositions"]}
    controls, review_controls = [], []
    for item in inventory:
        field_name = item["field_name"]
        mapping = mappings.get(field_name)
        disposition = dispositions[field_name]
        evidence = _control_evidence(item, mapping, disposition)
        if evidence is None:
            review_controls.append({"field_name": field_name, "status": "exempt", "address_id": None,
                                    "role": _role(item, mapping), "label": disposition.get("label", ""),
                                    "reason": disposition.get("reason") or f"Explicit {disposition['population_policy']} field disposition; semantic address unresolved.", "page": item["page"]})
            continue
        controls.append(evidence)
    registry = generate_candidate_registry(year=2025, document_id="form_1040_2025", document_token="form_1040",
                                           source_path="config/manifest.yaml#form_1040_2025", source_hash=FORM_1040_SHA256,
                                           controls=controls)
    by_key = {_candidate_key(item): item for item in registry["addresses"]}
    widget_bindings = []
    addressed_by_field = {}
    for evidence in controls:
        address = by_key[tuple((part["kind"], part["token"]) for part in evidence["semantic_path"])]
        addressed_by_field[evidence["field_name"]] = address
        widget_bindings.append({"field_name": evidence["field_name"], "address_id": address["address_id"],
                                "widget_type": _widget_type(evidence["widget_type"]), "page": evidence["page"],
                                "rect": evidence["rect"], "status": "exact" if mappings.get(evidence["field_name"]) else "provisional"})
        review_controls.append({"field_name": evidence["field_name"], "status": address["status"],
                                "address_id": address["address_id"], "role": evidence["control_role"],
                                "label": evidence["printed_label"], "reason": "Explicit form structure or authored slot evidence.",
                                "page": evidence["page"]})
    review_controls.sort(key=lambda item: (item["page"], item["field_name"]))
    node_bindings = []
    for field_name, mapping in sorted(mappings.items()):
        if mapping.get("node_id") and field_name in addressed_by_field:
            node_bindings.append({"node_id": mapping["node_id"], "address_id": addressed_by_field[field_name]["address_id"],
                                  "role": "value", "status": "exact"})
    return {"schema_version": 1, "document_id": "form_1040_2025", "registry": registry,
            "controls": review_controls, "coverage": {"inventory": len(inventory), "addressed": len(controls),
                                                       "exempt": len(inventory) - len(controls)},
            "widget_bindings": {"schema_version": 1, "year": 2025, "document_id": "form_1040_2025", "binding_kind": "widget", "bindings": widget_bindings},
            "node_bindings": {"schema_version": 1, "year": 2025, "document_id": "form_1040_2025", "binding_kind": "node", "bindings": node_bindings},
            "references": {"schema_version": 1, "year": 2025, "document_id": "form_1040_2025", "references": []}}


def render_form_1040_review_html(payload: dict[str, Any]) -> str:
    """Render a focused, artifact-only Gate A tree/control review table."""
    rows = []
    for item in payload["controls"]:
        rows.append("<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in
                    (item["page"], item["field_name"], item["address_id"] or "-", item["role"], item["status"], item["label"], item["reason"])) + "</tr>")
    coverage = payload["coverage"]
    return ("<!doctype html><html><head><meta charset=\"utf-8\"><title>Form 1040 address review</title></head><body>"
            f"<h1>Form 1040 canonical address review</h1><p>Inventory {coverage['inventory']}; addressed {coverage['addressed']}; explicit exemptions {coverage['exempt']}.</p>"
            "<table><thead><tr><th>Page</th><th>Official control</th><th>Stable address</th><th>Role</th><th>Status</th><th>Printed label</th><th>Evidence/rationale</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></body></html>")


def _control_evidence(item: dict[str, Any], mapping: dict[str, Any] | None, disposition: dict[str, Any]) -> dict[str, Any] | None:
    role = _role(item, mapping)
    line = item.get("line_anchor")
    if str(disposition.get("runtime_fact_ref", "")).startswith("dependents."):
        column = str(disposition["runtime_fact_ref"]).split(".", 1)[1]
        semantic_path = [{"kind": "table", "token": "dependents"}, {"kind": "row_template", "token": "dependent"}, {"kind": "column", "token": column}]
        status = "pending_review"
    elif line and str(line)[0].isdigit():
        semantic_path = [{"kind": "line", "token": str(line).lower()}, {"kind": "control", "token": role}]
        status = "pending_review"
    elif mapping and mapping.get("identity_slot"):
        slot = str(mapping["identity_slot"])
        if slot == "filing_status" and mapping.get("checkbox_value"):
            semantic_path = [{"kind": "section", "token": "filing_status"}, {"kind": "option", "token": str(mapping["checkbox_value"])}]
        else:
            semantic_path = [{"kind": "section", "token": "identity"}, {"kind": "control", "token": slot}]
        status = "pending_review"
    else:
        return None
    return {"semantic_path": semantic_path, "official_ref": str(line) if line else None,
            "control_role": role, "printed_label": disposition.get("label", ""),
            "field_name": item["field_name"], "widget_type": item["field_type"], "page": item["page"],
            "rect": [item["x0"], item["y0"], item["x1"], item["y1"]], "semantic_status": status}


def _role(item: dict[str, Any], mapping: dict[str, Any] | None) -> str:
    if mapping and mapping.get("identity_slot") == "line_1h_description":
        return "description"
    if mapping and mapping.get("format") == "checkbox" or item["field_type"] == "CheckBox":
        return "checkbox"
    if item.get("line_anchor"):
        return "amount"
    return "text"


def _candidate_key(item: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple((part["kind"], part["token"]) for part in item["path"][1:])


def _widget_type(value: str) -> str:
    return {"Text": "text", "CheckBox": "checkbox", "RadioButton": "radio", "Choice": "choice", "Signature": "signature"}.get(value, "other")
