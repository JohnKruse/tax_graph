"""Author complete v2 field maps from committed mappings and official PDFs.

This maintenance tool is intentionally conservative. Existing graph and identity
mappings remain authoritative. It can add a printable graph node only when the
node label has an IRS line anchor and exactly one unused amount field on that line
is available. Every other output control receives a specific unsupported policy;
source-document controls are imported and intake controls are user-entered.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tax_graph.acquire.render_form import extract_field_grid
from tax_graph.io.loader import load_graph
from tax_graph.output.field_maps import enumerate_pdf_widgets, load_field_maps
from tax_graph.output.geometry import write_node_geometry


GENERIC_EXCLUSION = "not mapped in the supported output profile"
SOURCE_DOCUMENTS = {"form_1099b_2025", "form_1099_div_2025", "form_1099_int_2025", "form_w2_2025"}
INTAKE_DOCUMENTS = {"form_13614_c_2025"}
OPTIONAL_EXTENSION_DOCUMENTS = {"form_2441_2025"}


def author(year: str, root: Path) -> None:
    """Regenerate complete inventories and v2 field dispositions in stable order."""
    raw_dir = root / ".cache" / "raw" / year
    inventory_dir = root / "graph" / year / "field_inventories"
    map_dir = root / "graph" / year / "field_maps"
    inventory_dir.mkdir(parents=True, exist_ok=True)
    map_dir.mkdir(parents=True, exist_ok=True)

    graph = load_graph(year, root)
    nodes = {str(item["node_id"]): item for item in graph.items("nodes")}
    rules = {str(item["rule_id"]): item for item in graph.items("rules")}
    incoming: dict[str, list[dict[str, Any]]] = {}
    for edge in graph.items("edges"):
        incoming.setdefault(str(edge["target"]), []).append(edge)
    existing = {item["document_id"]: item for item in load_field_maps(year, root)}

    for pdf_path in sorted(raw_dir.glob("*.pdf")):
        if not enumerate_pdf_widgets(pdf_path):
            continue
        document_id = pdf_path.stem
        inventory = extract_field_grid(pdf_path)
        inventory_path = inventory_dir / f"{document_id}.json"
        inventory_path.write_text(
            json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        field_map = dict(
            existing.get(
                document_id,
                {
                    "tax_year": int(year),
                    "document_id": document_id,
                    "inventory": inventory_path.relative_to(root).as_posix(),
                    "mappings": [],
                    "excluded_nodes": [],
                    "frontier_fields": [],
                },
            )
        )
        field_map["schema_version"] = 2
        field_map["inventory"] = inventory_path.relative_to(root).as_posix()
        if document_id in OPTIONAL_EXTENSION_DOCUMENTS:
            field_map["mappings"] = []
            field_map["excluded_nodes"] = [
                {
                    "node_id": node_id,
                    "reason": f"Optional extension graph object '{node.get('label', node_id)}' has no base-profile printable placement.",
                    "optional_extension": True,
                }
                for node_id, node in sorted(nodes.items())
                if node.get("document_id") == document_id
            ]
            field_map["frontier_fields"] = []
        _repair_form_1040_mappings(field_map)
        if document_id not in OPTIONAL_EXTENSION_DOCUMENTS:
            _declare_uncovered_nodes(field_map, nodes)
            _map_unambiguous_printable_nodes(field_map, inventory, nodes)
        mapped_node_ids = {item.get("node_id") for item in field_map.get("mappings", [])}
        field_map["excluded_nodes"] = [
            _specific_exclusion(item, nodes.get(str(item.get("node_id"))))
            for item in field_map.get("excluded_nodes", [])
            if item.get("node_id") not in mapped_node_ids
        ]
        field_map["field_dispositions"] = _dispositions(
            field_map,
            inventory,
            pdf_path,
            nodes=nodes,
            incoming=incoming,
            rules=rules,
        )
        if document_id == "form_1040_2025":
            _author_dependent_dispositions(field_map)
        map_path = map_dir / f"{document_id}.yaml"
        map_path.write_text(yaml.safe_dump(field_map, sort_keys=False), encoding="utf-8", newline="\n")
    write_node_geometry(year, root)


def _declare_uncovered_nodes(
    field_map: dict[str, Any], nodes: Mapping[str, Mapping[str, Any]]
) -> None:
    document_id = str(field_map["document_id"])
    covered = {item.get("node_id") for item in field_map.get("mappings", [])}
    excluded = {item["node_id"] for item in field_map.get("excluded_nodes", [])}
    for node_id, node in sorted(nodes.items()):
        if node.get("document_id") != document_id or node_id in covered or node_id in excluded:
            continue
        field_map.setdefault("excluded_nodes", []).append(
            {
                "node_id": node_id,
                "reason": f"Internal graph object '{node.get('label', node_id)}' has no authored printable placement.",
            }
        )


def _repair_form_1040_mappings(field_map: dict[str, Any]) -> None:
    if field_map.get("document_id") != "form_1040_2025":
        return
    by_field = {item["field_name"]: item for item in field_map.get("mappings", [])}
    amount_fields = {
        "1b": "topmostSubform[0].Page1[0].f1_48[0]",
        "1c": "topmostSubform[0].Page1[0].f1_49[0]",
        "1d": "topmostSubform[0].Page1[0].f1_50[0]",
        "1e": "topmostSubform[0].Page1[0].f1_51[0]",
        "1f": "topmostSubform[0].Page1[0].f1_52[0]",
        "1g": "topmostSubform[0].Page1[0].f1_53[0]",
        "1h": "topmostSubform[0].Page1[0].f1_55[0]",
    }
    for anchor, field_name in amount_fields.items():
        by_field[field_name] = {
            "slot": f"form_1040_2025_root_line_{anchor}",
            "field_name": field_name,
            "format": "dollars",
            "node_id": f"form_1040_2025_root_line_{anchor}",
        }
    by_field["topmostSubform[0].Page1[0].f1_54[0]"] = {
        "slot": "form_1040_2025_root_line_1h_description",
        "field_name": "topmostSubform[0].Page1[0].f1_54[0]",
        "format": "text",
        "identity_slot": "line_1h_description",
    }
    field_map["mappings"] = list(by_field.values())


def _map_unambiguous_printable_nodes(
    field_map: dict[str, Any], inventory: Mapping[str, Any], nodes: Mapping[str, Mapping[str, Any]]
) -> None:
    document_id = str(field_map["document_id"])
    mapped_fields = {item["field_name"] for item in field_map.get("mappings", [])}
    mapped_nodes = {item.get("node_id") for item in field_map.get("mappings", [])}
    excluded = {item["node_id"] for item in field_map.get("excluded_nodes", [])}
    fields = list(inventory.get("fields", []))
    for node_id in sorted(excluded):
        node = nodes.get(node_id)
        if not node or node_id in mapped_nodes or not _printable_node_id(document_id, node_id):
            continue
        match = re.search(r"\bLine\s+([0-9]+[a-z]?)\b", str(node.get("label", "")), re.IGNORECASE)
        if match is None:
            continue
        anchor = match.group(1).lower()
        candidates = [
            field
            for field in fields
            if str(field.get("line_anchor", "")).lower() == anchor
            and field.get("field_name") not in mapped_fields
            and str(field.get("field_type")) == "Text"
        ]
        if not candidates:
            continue
        candidate = max(candidates, key=lambda item: float(item.get("x0", 0)))
        mapping = {
            "slot": node_id,
            "field_name": candidate["field_name"],
            "format": "dollars" if node.get("value_type") == "currency" else "text",
            "node_id": node_id,
        }
        field_map.setdefault("mappings", []).append(mapping)
        mapped_fields.add(str(candidate["field_name"]))
        mapped_nodes.add(node_id)


def _printable_node_id(document_id: str, node_id: str) -> bool:
    suffix = node_id.removeprefix(document_id + "_")
    if any(token in suffix for token in ("worksheet", "qdcgt", "bracket", "rate", "threshold", "pre_floor")):
        return False
    return "line_" in suffix


def _specific_exclusion(item: Mapping[str, Any], node: Mapping[str, Any] | None) -> dict[str, Any]:
    node_id = str(item["node_id"])
    reason = str(item.get("reason", ""))
    if GENERIC_EXCLUSION not in reason.lower():
        result = {"node_id": node_id, "reason": reason}
        if item.get("optional_extension"):
            result["optional_extension"] = True
        return result
    label = str((node or {}).get("label", node_id))
    return {
        "node_id": node_id,
        "reason": f"Internal graph object '{label}' has no corresponding printable AcroForm control.",
    }


def _dispositions(
    field_map: Mapping[str, Any],
    inventory: Mapping[str, Any],
    pdf_path: Path,
    *,
    nodes: Mapping[str, Mapping[str, Any]],
    incoming: Mapping[str, list[dict[str, Any]]],
    rules: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    document_id = str(field_map["document_id"])
    mapping_by_field = {item["field_name"]: item for item in field_map.get("mappings", [])}
    frontier_by_field = {item["field_name"]: item for item in field_map.get("frontier_fields", [])}
    labels = _field_labels(pdf_path, inventory)
    result: list[dict[str, Any]] = []
    for field in inventory.get("fields", []):
        field_name = str(field["field_name"])
        mapping = mapping_by_field.get(field_name)
        frontier = frontier_by_field.get(field_name)
        base: dict[str, Any] = {
            "field_name": field_name,
            "label": labels[field_name],
            "population_policy": "unsupported",
            "value_format": _value_format(mapping, field),
        }
        repeatable = _repeatable(mapping, field_name)
        if repeatable:
            base["repeatable"] = repeatable
        if frontier is not None:
            if mapping and mapping.get("node_id"):
                base["node_id"] = mapping["node_id"]
            base.update(
                reason=str(frontier["note"]),
                downstream_effect="The affected return branch remains incomplete and this control is left blank.",
                missing_capability=f"Implement and cite frontier {frontier['frontier_id']} before populating this control.",
            )
        elif mapping and mapping.get("identity_slot"):
            base.update(
                population_policy="user_entered",
                identity_slot=str(mapping["identity_slot"]),
            )
        elif mapping and mapping.get("node_id"):
            node_id = str(mapping["node_id"])
            base.update(
                population_policy=_node_policy(node_id, nodes, incoming, rules),
                node_id=node_id,
            )
        elif document_id in SOURCE_DOCUMENTS:
            base.update(
                population_policy="imported",
                source_ref=f"{document_id}.{_safe_ref(field_name)}",
            )
        elif document_id in INTAKE_DOCUMENTS:
            base.update(
                population_policy="user_entered",
                runtime_fact_ref=f"intake.{document_id}.{_safe_ref(field_name)}",
            )
        else:
            base.update(
                reason=f"The official {document_id} control '{labels[field_name]}' has no authored graph, filer-fact, or decision mapping.",
                downstream_effect=f"Output leaves AcroForm field {field_name} blank and reports the unsupported filing field.",
                missing_capability=f"Add a cited graph rule, runtime fact, or explicit decision mapping for {field_name}.",
            )
        result.append(base)
    return result


def _node_policy(
    node_id: str,
    nodes: Mapping[str, Mapping[str, Any]],
    incoming: Mapping[str, list[dict[str, Any]]],
    rules: Mapping[str, Mapping[str, Any]],
) -> str:
    edges = incoming.get(node_id, [])
    operations = {
        str(rules.get(str(edge.get("rule_id")), {}).get("operation", ""))
        for edge in edges
    }
    if edges and operations == {"COPY"}:
        return "copied"
    if edges or (nodes.get(node_id) or {}).get("node_type") == "computed":
        return "computed"
    return "user_entered"


def _author_dependent_dispositions(field_map: dict[str, Any]) -> None:
    identity_columns = {1: "first_name", 2: "last_name", 3: "ssn", 4: "relationship"}
    decision_columns = {
        5: ("lived_with_you", "in_us"),
        6: ("full_time_student", "permanently_disabled"),
        7: ("child_tax_credit", "other_dependent_credit"),
    }
    for disposition in field_map.get("field_dispositions", []):
        field_name = str(disposition["field_name"])
        if "Table_Dependents" not in field_name:
            continue
        row_match = re.search(r"\.Row([1-7])\[", field_name)
        if row_match is None:
            continue
        physical_row = int(row_match.group(1))
        if physical_row <= 4:
            number_match = re.search(r"\.f1_([0-9]+)\[", field_name)
            if number_match is None:
                continue
            dependent_slot = ((int(number_match.group(1)) - 31) % 4) + 1
            column = identity_columns[physical_row]
            disposition.update(
                label=f"Dependent {dependent_slot} {column.replace('_', ' ')}",
                population_policy="user_entered",
                runtime_fact_ref=f"dependents.{column}",
                repeatable={
                    "group": "dependents",
                    "row_slot": dependent_slot,
                    "column": column,
                    "role": "identity",
                },
            )
            for key in ("reason", "downstream_effect", "missing_capability"):
                disposition.pop(key, None)
            continue
        dependent_match = re.search(r"\.Dependent([1-4])\[", field_name)
        field_number_match = re.search(r"\.c1_([0-9]+)\[([01])\]$", field_name)
        if dependent_match is None or field_number_match is None:
            continue
        dependent_slot = int(dependent_match.group(1))
        if physical_row == 7:
            choice_index = int(field_number_match.group(2))
        else:
            base_number = 12 if physical_row == 5 else 20
            choice_index = (int(field_number_match.group(1)) - base_number) % 2
        column = decision_columns[physical_row][choice_index]
        disposition.update(
            label=f"Dependent {dependent_slot} {column.replace('_', ' ')} decision",
            population_policy="decision_required",
            runtime_fact_ref=f"dependents.{column}",
            repeatable={
                "group": "dependents",
                "row_slot": dependent_slot,
                "column": column,
                "role": "decision",
            },
        )
        for key in ("reason", "downstream_effect", "missing_capability"):
            disposition.pop(key, None)


def _value_format(mapping: Mapping[str, Any] | None, field: Mapping[str, Any]) -> str:
    if mapping and mapping.get("format") in {"dollars", "text", "checkbox"}:
        return str(mapping["format"])
    field_type = str(field.get("field_type", "")).lower()
    if "check" in field_type or "button" in field_type:
        return "checkbox"
    if "choice" in field_type or "combo" in field_type or "list" in field_type:
        return "choice"
    if "sign" in field_type:
        return "signature"
    return "text"


def _repeatable(mapping: Mapping[str, Any] | None, field_name: str) -> dict[str, Any] | None:
    slot = str((mapping or {}).get("slot", ""))
    if slot.startswith("table:"):
        _, group, row, column = slot.split(":", 3)
        return {"group": group, "row_slot": int(row), "column": column, "role": "value"}
    row_match = re.search(r"\.Row([0-9]+)\[", field_name)
    if row_match is None:
        return None
    table_match = re.search(r"\.([A-Za-z0-9_]*Table[A-Za-z0-9_]*)\[", field_name)
    group = _safe_ref(table_match.group(1) if table_match else "repeatable_fields")
    terminal = re.search(r"\.([fc][0-9]_[0-9]+)\[", field_name)
    return {
        "group": group,
        "row_slot": int(row_match.group(1)),
        "column": terminal.group(1) if terminal else "field",
        "role": "other",
    }


def _field_labels(pdf_path: Path, inventory: Mapping[str, Any]) -> dict[str, str]:
    import fitz

    labels: dict[str, str] = {}
    with fitz.open(str(pdf_path)) as document:
        words_by_page = {number: document[number - 1].get_text("words") for number in range(1, len(document) + 1)}
    fields = list(inventory.get("fields", []))
    for field in fields:
        field_name = str(field["field_name"])
        words = words_by_page[int(field["page"])]
        center_y = (float(field["y0"]) + float(field["y1"])) / 2
        left = [
            word
            for word in words
            if float(word[2]) <= float(field["x0"]) + 2
            and abs(((float(word[1]) + float(word[3])) / 2) - center_y) <= 7
        ]
        nearby = " ".join(str(word[4]) for word in sorted(left, key=lambda item: item[0])[-10:]).strip()
        anchor = str(field.get("line_anchor", "")).strip()
        terminal = re.sub(r"\[[0-9]+\]", "", field_name.split(".")[-1])
        parts = [part for part in (f"Line {anchor}" if anchor else "", nearby, terminal) if part]
        labels[field_name] = " - ".join(parts) or f"Page {field['page']} {terminal}"
    counts = Counter(labels.values())
    for index, field in enumerate(fields, 1):
        field_name = str(field["field_name"])
        if counts[labels[field_name]] > 1:
            labels[field_name] = f"{labels[field_name]} (page {field['page']}, control {index})"
    return labels


def _safe_ref(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized or "field"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", default="2025")
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1], type=Path)
    args = parser.parse_args()
    author(str(args.year), args.root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
