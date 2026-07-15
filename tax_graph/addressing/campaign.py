"""Deterministic canonical-address campaigns for authored field-map documents."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

import yaml

from tax_graph.addressing.candidates import generate_candidate_registry


CORE_RETURN_DOCUMENTS = (
    "schedule_1_2025",
    "schedule_1a_2025",
    "schedule_2_2025",
    "schedule_3_2025",
    "schedule_a_2025",
    "schedule_b_2025",
    "schedule_d_2025",
    "form_6251_2025",
    "form_8949_2025",
)


def build_address_campaign(root: str | Path, document_ids: Iterable[str]) -> dict[str, dict[str, Any]]:
    """Build machine-valid pending-review artifacts for authored field maps."""
    root_path = Path(root)
    return {document_id: build_document_addresses(root_path, document_id) for document_id in document_ids}


def build_document_addresses(root: str | Path, document_id: str) -> dict[str, Any]:
    """Reconcile one field inventory to addressed widgets and explicit exemptions."""
    root_path = Path(root)
    map_path = root_path / "graph" / "2025" / "field_maps" / f"{document_id}.yaml"
    field_map = yaml.safe_load(map_path.read_text(encoding="utf-8"))
    inventory = json.loads((root_path / field_map["inventory"]).read_text(encoding="utf-8"))["fields"]
    mappings = {item["field_name"]: item for item in field_map.get("mappings", [])}
    dispositions = {item["field_name"]: item for item in field_map["field_dispositions"]}
    source_hash = _source_hash(root_path, document_id)
    controls: list[dict[str, Any]] = []
    exemptions: list[dict[str, str]] = []
    for item in inventory:
        field_name = item["field_name"]
        evidence = _control_evidence(item, mappings.get(field_name), dispositions[field_name])
        if evidence is None:
            exemptions.append({"field_name": field_name, "population_policy": dispositions[field_name]["population_policy"]})
        else:
            controls.append(evidence)
    worksheet_nodes = _schedule_d_worksheet_controls(root_path) if document_id == "schedule_d_2025" else []
    registry = generate_candidate_registry(
        year=2025,
        document_id=document_id,
        document_token=document_id.removesuffix("_2025"),
        source_path=f"config/manifest.yaml#{document_id}",
        source_hash=source_hash,
        controls=[*controls, *worksheet_nodes],
    )
    by_path = {
        tuple((part["kind"], part["token"]) for part in item["path"][1:]): item
        for item in registry["addresses"]
    }
    widget_bindings: list[dict[str, Any]] = []
    addressed_by_field: dict[str, dict[str, Any]] = {}
    for control in controls:
        key = tuple((part["kind"], part["token"]) for part in control["semantic_path"])
        address = by_path[key]
        addressed_by_field[control["field_name"]] = address
        widget_bindings.append({
            "field_name": control["field_name"],
            "address_id": address["address_id"],
            "widget_type": _widget_type(control["widget_type"]),
            "page": control["page"],
            "rect": control["rect"],
            "status": "exact" if mappings.get(control["field_name"]) else "provisional",
        })
    node_bindings: dict[str, dict[str, Any]] = {}
    for field_name, mapping in sorted(mappings.items()):
        address = addressed_by_field.get(field_name)
        node_id = mapping.get("node_id")
        if not node_id or address is None:
            continue
        candidate = {
            "node_id": node_id,
            "address_id": address["address_id"],
            "expected_official_ref": address.get("official_ref"),
            "role": "value",
            "status": "exact",
        }
        previous = node_bindings.get(node_id)
        if previous and previous["address_id"] != candidate["address_id"]:
            raise ValueError(f"node {node_id} maps to multiple addresses")
        node_bindings[node_id] = candidate
    for control in worksheet_nodes:
        key = tuple((part["kind"], part["token"]) for part in control["semantic_path"])
        address = by_path[key]
        node_bindings[control["node_id"]] = {
            "node_id": control["node_id"], "address_id": address["address_id"],
            "expected_official_ref": control["official_ref"], "role": "value", "status": "exact",
        }
    references = _form_8949_references(registry, source_hash) if document_id == "form_8949_2025" else []
    return {
        "registry": registry,
        "widget_bindings": _binding_artifact(document_id, "widget", widget_bindings),
        "node_bindings": _binding_artifact(document_id, "node", list(node_bindings.values())),
        "references": {"schema_version": 1, "year": 2025, "document_id": document_id, "references": references},
        "field_addresses": {field: address["address_id"] for field, address in addressed_by_field.items()},
        "coverage": {
            "inventory": len(inventory), "addressed_widgets": len(controls), "exempt_widgets": len(exemptions),
            "node_bindings": len(node_bindings), "references": len(references),
        },
    }


def _control_evidence(item: dict[str, Any], mapping: dict[str, Any] | None,
                      disposition: dict[str, Any]) -> dict[str, Any] | None:
    line = item.get("line_anchor")
    role = _role(item, mapping)
    total = re.fullmatch(
        r"form_8949_2025_part_(i|ii)_line_2_line_2_column_([degh])_total",
        str(mapping.get("slot", "")) if mapping else "",
    )
    if total:
        part, column = total.groups()
        path = [
            {"kind": "table", "token": f"part_{part}_line_2"},
            {"kind": "row_template", "token": "total"},
            {"kind": "column", "token": column},
        ]
        official_ref = f"Line 2 column ({column})"
    elif mapping and str(mapping.get("slot", "")).startswith("table:"):
        _, table_id, _row, column = str(mapping["slot"]).split(":", 3)
        path = [
            {"kind": "table", "token": table_id.removeprefix("form_8949_2025_")},
            {"kind": "row_template", "token": "transaction"},
            {"kind": "column", "token": column},
        ]
        official_ref = f"Column ({column})"
    elif line and str(line)[0].isdigit():
        path = [{"kind": "line", "token": str(line).lower()}, {"kind": "control", "token": role}]
        official_ref = str(line)
    else:
        return None
    return {
        "semantic_path": path, "official_ref": official_ref, "control_role": role,
        "printed_label": disposition.get("label", ""), "field_name": item["field_name"],
        "widget_type": item["field_type"], "page": item["page"],
        "rect": [item["x0"], item["y0"], item["x1"], item["y1"]],
        "semantic_status": "pending_review",
    }


def _schedule_d_worksheet_controls(root: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load((root / "graph/2025/nodes/capital-gains.yaml").read_text(encoding="utf-8"))
    nodes = {item["node_id"]: item for item in payload if isinstance(item, dict) and item.get("node_id")}
    controls: list[dict[str, Any]] = []
    for worksheet, steps in (("carryover", range(1, 14)), ("tax", range(1, 48))):
        for step in steps:
            node_id = f"schedule_d_2025_{worksheet}_worksheet_line_{step}"
            node = nodes.get(node_id)
            if not node or node.get("node_type") != "worksheet_field":
                continue
            controls.append({
                "semantic_path": [{"kind": "section", "token": f"{worksheet}_worksheet"},
                                  {"kind": "worksheet_step", "token": str(step)}],
                "official_ref": str(step), "control_role": "none", "printed_label": node.get("label", ""),
                "node_id": node_id, "semantic_status": "pending_review",
            })
    return controls


def _form_8949_references(registry: dict[str, Any], evidence_hash: str) -> list[dict[str, Any]]:
    by_path = {
        tuple((part["kind"], part["token"]) for part in item["path"][1:]): item["address_id"]
        for item in registry["addresses"]
    }
    references: list[dict[str, Any]] = []
    for part, targets in (("i", ("1b", "2", "3")), ("ii", ("8b", "9", "10"))):
        source = by_path[(("table", f"part_{part}_line_2"), ("row_template", "total"), ("column", "h"))]
        for target in targets:
            references.append({
                "reference_id": f"flow_form_8949_2025_part_{part}_line_2_column_h_to_schedule_d_2025_line_{target}",
                "source_address_id": source,
                "target_document_id": "schedule_d_2025",
                "target_official_ref": target,
                "control_role": "amount",
                "resolved_address_id": f"2025/document=schedule_d/line={target}/control=amount",
                "status": "exact",
                "evidence_hash": evidence_hash,
            })
    return references


def _source_hash(root: Path, document_id: str) -> str:
    manifest = yaml.safe_load((root / "config/manifest.yaml").read_text(encoding="utf-8"))
    declared = next(item for item in manifest["documents"] if item["document_id"] == document_id)
    if declared.get("expected_sha256"):
        return str(declared["expected_sha256"])
    pdf = root / ".cache" / "raw" / "2025" / f"{document_id}.pdf"
    return hashlib.sha256(pdf.read_bytes()).hexdigest()


def _role(item: dict[str, Any], mapping: dict[str, Any] | None) -> str:
    if mapping and mapping.get("format") == "checkbox" or item["field_type"] == "CheckBox":
        return "checkbox"
    if mapping and mapping.get("format") == "date":
        return "date"
    return "amount" if item.get("line_anchor") or mapping else "text"


def _widget_type(value: str) -> str:
    return {"Text": "text", "CheckBox": "checkbox", "RadioButton": "radio", "Choice": "choice",
            "Signature": "signature"}.get(value, "other")


def _binding_artifact(document_id: str, kind: str, bindings: list[dict[str, Any]]) -> dict[str, Any]:
    return {"schema_version": 1, "year": 2025, "document_id": document_id,
            "binding_kind": kind, "bindings": sorted(bindings, key=lambda item: next(iter(item.values())))}
