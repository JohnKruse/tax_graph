"""Stable flow-spine concepts for structured form addresses.

Concepts are the durable meaning layer between a form's annual placement and its
physical AcroForm widgets. This module mints only structured forms whose semantic
groups already exist in the promoted address paths. Printed line and box tokens
stay in placement metadata and never enter a concept id.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
from typing import Any, Iterable

import yaml


STRUCTURED_DOCUMENTS = (
    "form_1040_2025",
    "form_8949_2025",
    "form_w2_2025",
    "form_1099_div_2025",
    "form_1099_int_2025",
    "form_1099b_2025",
    "schedule_1a_2025",
)

_CONCEPT_PATTERN = re.compile(r"^[a-z0-9_]+(?:/[a-z0-9_]+)+$")
_YEAR_PATTERN = re.compile(r"(?:19|20)\d{2}")
_PLACEMENT_PATTERN = re.compile(r"(?:^|/)(?:line|box)(?:/|=)|(?:^|/)(?:line|box)_")

_FORM_1040_IDENTITY = {
    "address_line_1": ("filer", "address_line_1"),
    "apartment": ("filer", "apartment"),
    "city": ("filer", "city"),
    "foreign_country": ("filer", "foreign_country"),
    "foreign_postal_code": ("filer", "foreign_postal_code"),
    "foreign_province": ("filer", "foreign_province"),
    "spouse_first_name": ("spouse", "first_name"),
    "spouse_last_name": ("spouse", "last_name"),
    "spouse_ssn": ("spouse", "ssn"),
    "state": ("filer", "state"),
    "taxpayer_first_name": ("taxpayer", "first_name"),
    "taxpayer_last_name": ("taxpayer", "last_name"),
    "taxpayer_ssn": ("taxpayer", "ssn"),
    "zip_code": ("filer", "zip_code"),
    "main_home_joint_return": ("residence", "main_home_joint_return"),
    "presidential_election_spouse": ("presidential_election", "spouse"),
    "presidential_election_you": ("presidential_election", "taxpayer"),
}

_FORM_W2_BOXES = {
    "a": ("employee", "ssn"),
    "b": ("employer", "ein"),
    "c": ("employer", "name_address"),
    "d": ("employer", "control_number"),
    "e": ("employee", "name"),
    "f": ("employee", "address"),
    "1": ("employee", "wages"),
    "2": ("employee", "federal_income_tax_withheld"),
    "3": ("employee", "social_security_wages"),
    "4": ("employee", "social_security_tax_withheld"),
    "5": ("employee", "medicare_wages"),
    "6": ("employee", "medicare_tax_withheld"),
    "7": ("employee", "social_security_tips"),
    "8": ("employee", "allocated_tips"),
    "10": ("employee", "dependent_care_benefits"),
    "11": ("employee", "nonqualified_plans"),
    "14": ("employee", "other_compensation"),
}

_FORM_1099_BOXES = {
    "form_1099b": {
        "1a": ("transaction", "description"),
        "1b": ("transaction", "date_acquired"),
        "1c": ("transaction", "date_disposed"),
        "1d": ("transaction", "proceeds"),
        "1e": ("transaction", "cost_basis"),
        "1f": ("transaction", "accrued_market_discount"),
        "1g": ("transaction", "wash_sale_loss_disallowed"),
        "4": ("transaction", "federal_income_tax_withheld"),
        "8": ("contract", "realized_profit_loss"),
        "9": ("contract", "unrealized_profit_loss_prior"),
        "10": ("contract", "unrealized_profit_loss_current"),
        "11": ("contract", "aggregate_profit_loss"),
        "13": ("transaction", "bartering"),
    },
    "form_1099_div": {
        "1a": ("dividends", "ordinary"),
        "1b": ("dividends", "qualified"),
        "2a": ("capital_gain_distribution", "total"),
        "2b": ("capital_gain_distribution", "unrecaptured_section_1250"),
        "2c": ("capital_gain_distribution", "section_1202"),
        "2d": ("capital_gain_distribution", "collectibles"),
        "2e": ("dividends", "section_897_ordinary"),
        "2f": ("capital_gain_distribution", "section_897"),
        "3": ("dividends", "nondividend_distribution"),
        "4": ("payer", "federal_income_tax_withheld"),
        "5": ("dividends", "section_199a"),
        "6": ("dividends", "investment_expenses"),
        "7": ("foreign_tax", "paid"),
        "8": ("foreign_tax", "country"),
        "9": ("liquidation", "cash"),
        "10": ("liquidation", "noncash"),
        "12": ("dividends", "exempt_interest"),
        "13": ("dividends", "specified_private_activity_bond"),
    },
    "form_1099_int": {
        "1": ("interest", "income"),
        "2": ("interest", "early_withdrawal_penalty"),
        "3": ("interest", "us_savings_bonds"),
        "4": ("payer", "federal_income_tax_withheld"),
        "5": ("interest", "investment_expenses"),
        "6": ("foreign_tax", "paid"),
        "7": ("foreign_tax", "country"),
        "8": ("interest", "tax_exempt"),
        "9": ("interest", "specified_private_activity_bond"),
        "10": ("interest", "market_discount"),
        "11": ("interest", "bond_premium"),
        "12": ("interest", "bond_premium_treasury"),
        "13": ("interest", "bond_premium_tax_exempt"),
        "14": ("interest", "cusip"),
    },
}

_FORM_8949_COLUMNS = {
    "a": "description",
    "b": "date_acquired",
    "c": "date_disposed",
    "d": "proceeds",
    "e": "cost_basis",
    "f": "adjustment_code",
    "g": "adjustment_amount",
    "h": "gain_or_loss",
}


class ConceptError(ValueError):
    """Raised when a structured address cannot receive a safe concept id."""


def validate_concept_id(concept_id: str) -> None:
    """Enforce the flow-spine and owner/role rules for a concept id."""
    value = str(concept_id)
    if not _CONCEPT_PATTERN.fullmatch(value):
        raise ConceptError(f"concept id is not path-style ASCII: {value}")
    if _YEAR_PATTERN.search(value):
        raise ConceptError(f"concept id contains a year: {value}")
    if _PLACEMENT_PATTERN.search(value):
        raise ConceptError(f"concept id contains a line or box placement token: {value}")
    parts = value.split("/")
    if len(parts) < 3 or parts[-1] in {"amount", "value", "control", "option"}:
        raise ConceptError(f"concept id lacks an owner-qualified role: {value}")
    if parts[-1] == "ssn" and (len(parts) < 3 or parts[-2] in {"identity", "document"}):
        raise ConceptError(f"bare ssn concept is not owner-qualified: {value}")


def _document_token(document_id: str) -> str:
    return str(document_id).removesuffix("_2025")


def _components(address: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        (str(item.get("kind")), str(item.get("token")))
        for item in address.get("path", []) or []
        if isinstance(item, dict)
    ]


def _component(path: list[tuple[str, str]], kind: str) -> str | None:
    return next((token for item_kind, token in path if item_kind == kind), None)


def _is_minting_candidate(address: dict[str, Any]) -> bool:
    """Return whether a leaf is inside the S3a structured-form scope."""
    document = _document_token(str(address.get("document_id") or ""))
    path = _components(address)
    kind = str(address.get("kind") or "")
    if kind not in {"control", "option", "column"}:
        return False
    section = _component(path, "section")
    table = _component(path, "table")
    box = _component(path, "box")
    if document == "form_1040":
        return section == "identity" or table == "dependents"
    if document == "form_8949":
        return table in {"part_i_line_1", "part_i_line_2", "part_ii_line_1", "part_ii_line_2"}
    if document == "schedule_1a":
        return section == "identity" or table == "line_22"
    if document == "form_w2":
        return box is not None or table == "state_local"
    return document in {"form_1099b", "form_1099_div", "form_1099_int"} and (
        box is not None or section in {"header", "recipient"} or table == "state"
    )


def mint_concept_id(address: dict[str, Any]) -> str:
    """Mint one concept id from authored flow structure, or fail closed."""
    document_id = str(address.get("document_id") or "")
    if document_id not in STRUCTURED_DOCUMENTS:
        raise ConceptError(f"document is outside M19-S3a: {document_id}")
    path = _components(address)
    document = _document_token(document_id)
    section = _component(path, "section")
    table = _component(path, "table")
    box = _component(path, "box")
    terminal = path[-1][1] if path else ""

    if document == "form_1040" and section == "identity":
        mapping = _FORM_1040_IDENTITY.get(terminal)
        if mapping is None:
            raise ConceptError(f"unmapped Form 1040 identity role: {terminal}")
        owner, role = mapping
        concept_id = f"{document}/identity/{owner}/{role}"
    elif document == "form_1040" and table == "dependents":
        column = _component(path, "column")
        if not column:
            option = _component(path, "option")
            if option != "more_than_four":
                raise ConceptError("dependent address has no column")
            concept_id = f"{document}/dependents/{option}"
        else:
            concept_id = f"{document}/dependents/dependent/{column.removesuffix('_2025')}"
    elif document == "form_8949" and table in {"part_i_line_1", "part_i_line_2", "part_ii_line_1", "part_ii_line_2"}:
        column = _component(path, "column")
        row_template = _component(path, "row_template")
        if not column or not row_template or column not in _FORM_8949_COLUMNS:
            raise ConceptError("Form 8949 table address lacks a known row column")
        part = "short_term" if table.startswith("part_i_") else "long_term"
        suffix = _FORM_8949_COLUMNS[column]
        if row_template == "total":
            suffix = f"{suffix}_total"
        concept_id = f"{document}/{part}_transactions/{row_template}/{suffix}"
    elif document == "schedule_1a" and section == "identity":
        role = "ssn" if terminal == "social_security_number" else terminal
        concept_id = f"{document}/identity/filer/{role}"
    elif document == "schedule_1a" and table == "line_22":
        column = _component(path, "column")
        if not column:
            raise ConceptError("Schedule 1-A vehicle address has no column")
        concept_id = f"{document}/vehicles/vehicle/{column}"
    elif document == "form_w2" and table == "state_local":
        column = _component(path, "column")
        if not column:
            raise ConceptError("W-2 state/local address has no column")
        concept_id = f"{document}/state_local/jurisdiction/{column}"
    elif document == "form_w2" and box == "12":
        column = _component(path, "column")
        if not column:
            raise ConceptError("W-2 Box 12 address has no column")
        amount_role = "compensation_amount" if column == "amount" else column
        concept_id = f"{document}/other_compensation/entry/{amount_role}"
    elif document == "form_w2" and box is not None:
        option = _component(path, "option")
        if option == "void":
            concept_id = f"{document}/header/void"
        elif option:
            concept_id = f"{document}/employee/benefit_election/{option}"
        else:
            mapping = _FORM_W2_BOXES.get(box)
            if mapping is None:
                raise ConceptError(f"unmapped W-2 box: {box}")
            owner, role = mapping
            control = _component(path, "control")
            if box == "e" and control in {"first_name_initial", "last_name", "suffix"}:
                role = control
            concept_id = f"{document}/{owner}/{role}"
    elif document in _FORM_1099_BOXES and box is not None:
        option = _component(path, "option")
        if option:
            owner, role = "classification", option
        else:
            try:
                owner, role = _FORM_1099_BOXES[document][box]
            except KeyError as exc:
                raise ConceptError(f"unmapped {document} box: {box}") from exc
        concept_id = f"{document}/{owner}/{role}"
    elif document in _FORM_1099_BOXES and section in {"header", "recipient"}:
        owner = "recipient" if section == "recipient" else "header"
        concept_id = f"{document}/{owner}/{terminal}"
    elif document in _FORM_1099_BOXES and table == "state":
        column = _component(path, "column")
        if not column:
            raise ConceptError(f"{document} state address has no column")
        concept_id = f"{document}/state_local/jurisdiction/{column}"
    else:
        raise ConceptError(f"structured address has no S3a minting rule: {address.get('address_id')}")

    validate_concept_id(concept_id)
    return concept_id


def _placement(address: dict[str, Any], concept_id: str) -> dict[str, str]:
    path = _components(address)
    box = _component(path, "box")
    line = _component(path, "line")
    table = _component(path, "table")
    if box:
        printed_kind, printed_token = "box", box
    elif line:
        printed_kind, printed_token = "line", line
    elif table and "line_" in table:
        printed_kind, printed_token = "line", table.split("line_", 1)[1]
    elif table:
        printed_kind, printed_token = "table", table
    else:
        printed_kind, printed_token = "section", _component(path, "section") or "section"
    return {
        "concept_id": concept_id,
        "printed_kind": printed_kind,
        "printed_token": printed_token,
        "printed_ref": str(address.get("official_ref") or printed_token),
    }


def _occurrence(address: dict[str, Any]) -> dict[str, Any]:
    """Describe the physical axes that distinguish a concept's slots.

    The promoted artifact is authored before a return record exists. Its row
    positions are therefore slots, not entities; runtime code may bind a slot
    to an entity later.
    """
    path = _components(address)
    document = _document_token(str(address.get("document_id") or ""))
    row_template = _component(path, "row_template")
    axes: list[str] = []
    if document in {"form_w2", "form_1099_div", "form_1099_int", "form_1099b"}:
        axes.append("copy")
    if row_template:
        axes.append("row_slot")
    if not axes:
        return {"kind": "singleton", "review_granularity": "concept", "row_policy": "none"}
    return {
        "kind": "slot",
        "slot_key": row_template or "copy",
        "axes": axes,
        "review_granularity": "concept",
        "row_policy": "slot_keyed",
    }


_COPY_RE = re.compile(r"(?:^|\.)Copy(?P<copy>[A-Za-z0-9]+)\[")
def _copy_axis(field_name: str) -> str | None:
    match = _COPY_RE.search(str(field_name))
    return match.group("copy") if match else None


def _field_occurrences(
    dispositions: list[dict[str, Any]],
    addresses: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any] | None]:
    """Build concrete slot keys from stable field structure and row order."""
    counters: dict[tuple[str, str | None], int] = defaultdict(int)
    result: dict[str, dict[str, Any] | None] = {}
    for disposition in dispositions:
        field_name = str(disposition.get("field_name") or "")
        address = addresses.get(str(disposition.get("address_id") or ""), {})
        contract = address.get("occurrence") or {}
        if contract.get("kind") != "slot":
            result[field_name] = None
            continue
        axes: dict[str, Any] = {}
        if "copy" in contract.get("axes", []):
            copy = _copy_axis(field_name)
            if copy is None:
                raise ConceptError(f"repeatable field has no copy axis: {field_name}")
            axes["copy"] = copy
        if "row_slot" in contract.get("axes", []):
            repeatable = disposition.get("repeatable") or {}
            row_slot = repeatable.get("row_slot")
            if row_slot is None:
                counter_key = (str(disposition.get("address_id") or ""), axes.get("copy"))
                counters[counter_key] += 1
                row_slot = counters[counter_key]
            axes["row_slot"] = int(row_slot)
        key = "/".join(f"{name}={axes[name]}" for name in sorted(axes))
        result[field_name] = {
            "kind": "slot",
            "axes": axes,
            "review_granularity": "concept",
            "row_policy": "slot_keyed",
            "key": key,
        }
    return result


def _repeatable_projection(
    address: dict[str, Any], concept_id: str, old: dict[str, Any] | None, occurrence: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Normalize row metadata without claiming entity binding at authoring time."""
    if not occurrence or "row_slot" not in occurrence.get("axes", {}):
        return None
    path = _components(address)
    row_template = _component(path, "row_template") or "repeatable_fields"
    if concept_id.startswith("form_8949/"):
        # Form 8949 uses the normalized concept group as its table contract.
        group = concept_id.split("/")[1]
    elif _component(path, "document") == "form_1040":
        # ``group`` names the table, while ``row_template`` names its row shape.
        # The filler and workbench both consume the table token.
        group = _component(path, "table") or row_template
    else:
        group = row_template
    return {
        "group": group,
        "row_slot": int(occurrence["axes"]["row_slot"]),
        "column": concept_id.rsplit("/", 1)[-1],
        "role": str((old or {}).get("role") or "value"),
    }


def _validate_field_occurrences(dispositions: list[dict[str, Any]]) -> None:
    """Fail closed when repeated physical fields lack a discriminator."""
    by_concept: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in dispositions:
        concept_id = str(item.get("concept_id") or "")
        if concept_id:
            by_concept[concept_id].append(item)
    for concept_id, items in by_concept.items():
        if len(items) <= 1:
            continue
        occurrences = [item.get("occurrence") for item in items]
        if any(not isinstance(value, dict) or value.get("kind") != "slot" or not value.get("axes") for value in occurrences):
            raise ConceptError(f"concept maps to repeated fields without slot occurrence data: {concept_id}")
        keys = [str(value.get("key")) for value in occurrences]
        if len(set(keys)) != len(keys):
            raise ConceptError(f"concept has duplicate occurrence keys: {concept_id}")


def validate_occurrence_contract(dispositions: Iterable[dict[str, Any]]) -> None:
    """Validate the fail-closed repeated-concept occurrence invariant."""
    _validate_field_occurrences([item for item in dispositions if isinstance(item, dict)])


def _apply_field_occurrences(
    field_map: dict[str, Any],
    addresses: dict[str, dict[str, Any]],
    projections: dict[str, dict[str, Any]],
) -> int:
    dispositions = [item for item in field_map.get("field_dispositions", []) or [] if isinstance(item, dict)]
    occurrences = _field_occurrences(dispositions, addresses)
    updated = 0
    for item in dispositions:
        address_id = str(item.get("address_id") or "")
        projection = projections.get(address_id)
        if projection is None:
            continue
        occurrence = occurrences.get(str(item.get("field_name") or ""))
        if occurrence is None:
            item.pop("occurrence", None)
            item.pop("repeatable", None)
            continue
        item["occurrence"] = occurrence
        item["repeatable"] = _repeatable_projection(
            addresses[address_id], str(projection["concept_id"]), item.get("repeatable"), occurrence
        )
        if item["repeatable"] is None:
            item.pop("repeatable", None)
        updated += 1
    _validate_field_occurrences(dispositions)
    return updated


def build_document_concepts(
    root: str | Path, year: str | int, document_id: str
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Build a schema-shaped concept inventory and address projections."""
    path = Path(root) / "graph" / str(year) / "addresses" / f"{document_id}.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    concepts: dict[str, dict[str, Any]] = {}
    projections: dict[str, dict[str, Any]] = {}
    for address in payload.get("addresses", []) or []:
        if not _is_minting_candidate(address):
            continue
        try:
            concept_id = mint_concept_id(address)
        except ConceptError as exc:
            raise ConceptError(
                f"cannot mint in-scope structured address {address.get('address_id')}: {exc}"
            ) from exc
        placement = _placement(address, concept_id)
        concept = concepts.setdefault(
            concept_id,
            {
                "concept_id": concept_id,
                "document_id": document_id,
                "status": "active",
                "flow_path": concept_id.split("/"),
                "owner": concept_id.split("/")[-2],
                "role": concept_id.split("/")[-1],
                "review_granularity": "concept",
                "occurrence": _occurrence(address),
                "aliases": [],
                "placements": [],
                "same_fact_as": [],
            },
        )
        logical_key = str(address.get("logical_key") or "")
        if logical_key and logical_key not in concept["aliases"]:
            concept["aliases"].append(logical_key)
        concept["placements"].append({"address_id": str(address["address_id"]), **placement})
        projections[str(address["address_id"])] = {
            "concept_id": concept_id,
            "placement": placement,
            "occurrence": _occurrence(address),
        }
    for concept in concepts.values():
        concept["aliases"].sort()
        concept["placements"].sort(key=lambda item: item["address_id"])
    return {
        "schema_version": 1,
        "year": int(year),
        "document_id": document_id,
        "concepts": [concepts[key] for key in sorted(concepts)],
    }, projections


def promote_structured_concepts(
    root: str | Path, year: str | int = 2025, document_ids: Iterable[str] = STRUCTURED_DOCUMENTS
) -> dict[str, dict[str, int]]:
    """Promote deterministic structured concepts and their placement projections."""
    root_path = Path(root)
    summary: dict[str, dict[str, int]] = {}
    for document_id in document_ids:
        inventory, projections = build_document_concepts(root_path, year, document_id)
        address_path = root_path / "graph" / str(year) / "addresses" / f"{document_id}.yaml"
        addresses = yaml.safe_load(address_path.read_text(encoding="utf-8")) or {}
        for address in addresses.get("addresses", []) or []:
            projection = projections.get(str(address.get("address_id")))
            if projection is None:
                if address.get("concept_id"):
                    address.pop("concept_id", None)
                    address.pop("placement", None)
                    address.pop("occurrence", None)
                    logical_key = str(address.get("logical_key") or "")
                    address["aliases"] = sorted(
                        set(str(value) for value in address.get("aliases", []) or []) - {logical_key}
                    )
                continue
            address["concept_id"] = projection["concept_id"]
            address["placement"] = projection["placement"]
            address["occurrence"] = projection["occurrence"]
            aliases = set(str(value) for value in address.get("aliases", []) or [])
            logical_key = str(address.get("logical_key") or "")
            if logical_key:
                aliases.add(logical_key)
            address["aliases"] = sorted(aliases)
        address_path.write_text(yaml.safe_dump(addresses, sort_keys=False, allow_unicode=False), encoding="utf-8", newline="\n")
        concepts_path = root_path / "graph" / str(year) / "concepts" / f"{document_id}.yaml"
        concepts_path.parent.mkdir(parents=True, exist_ok=True)
        concepts_path.write_text(yaml.safe_dump(inventory, sort_keys=False, allow_unicode=False), encoding="utf-8", newline="\n")
        field_map_path = root_path / "graph" / str(year) / "field_maps" / f"{document_id}.yaml"
        field_map = yaml.safe_load(field_map_path.read_text(encoding="utf-8")) or {}
        address_by_id = {
            str(address.get("address_id")): address
            for address in addresses.get("addresses", []) or []
            if isinstance(address, dict) and address.get("address_id")
        }
        address_to_concept = {address_id: item["concept_id"] for address_id, item in projections.items()}
        updated_fields = 0
        for item in field_map.get("field_dispositions", []) or []:
            concept_id = address_to_concept.get(str(item.get("address_id") or ""))
            if concept_id:
                item["concept_id"] = concept_id
                updated_fields += 1
        for item in field_map.get("mappings", []) or []:
            concept_id = address_to_concept.get(str(item.get("address_id") or ""))
            if concept_id:
                item["concept_id"] = concept_id
        occurrence_fields = _apply_field_occurrences(field_map, address_by_id, projections)
        field_map_path.write_text(yaml.safe_dump(field_map, sort_keys=False, allow_unicode=False), encoding="utf-8", newline="\n")
        summary[document_id] = {
            "concepts": len(inventory["concepts"]),
            "placements": len(projections),
            "field_dispositions": updated_fields,
            "occurrence_fields": occurrence_fields,
        }
    return summary


def retrieve_occurrences(
    root: str | Path,
    year: str | int,
    document_id: str,
    concept_id: str,
    *,
    axes: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Retrieve physical fields for a concept from promoted graph metadata.

    ``axes`` filters concrete slot values such as ``{"row_slot": 3}`` or
    ``{"copy": "A", "row_slot": 2}``. The result retains the placement,
    field name, occurrence key, and quotable ref needed to pull a complete
    table row without consulting a PDF or a return record.
    """
    root_path = Path(root)
    address_path = root_path / "graph" / str(year) / "addresses" / f"{document_id}.yaml"
    field_map_path = root_path / "graph" / str(year) / "field_maps" / f"{document_id}.yaml"
    address_payload = yaml.safe_load(address_path.read_text(encoding="utf-8")) or {}
    field_map = yaml.safe_load(field_map_path.read_text(encoding="utf-8")) or {}
    addresses = {
        str(item.get("address_id")): item
        for item in address_payload.get("addresses", []) or []
        if isinstance(item, dict) and item.get("address_id")
    }
    result: list[dict[str, Any]] = []
    wanted = axes or {}
    for item in field_map.get("field_dispositions", []) or []:
        if not isinstance(item, dict) or str(item.get("concept_id") or "") != concept_id:
            continue
        occurrence = item.get("occurrence") or {}
        actual_axes = occurrence.get("axes", {}) if isinstance(occurrence, dict) else {}
        if any(actual_axes.get(key) != value for key, value in wanted.items()):
            continue
        address_id = str(item.get("address_id") or "")
        address = addresses.get(address_id, {})
        result.append(
            {
                "concept_id": concept_id,
                "address_id": address_id,
                "field_name": str(item.get("field_name") or ""),
                "display_name": str(item.get("label") or address.get("printed_label") or ""),
                "occurrence": occurrence,
                "repeatable": item.get("repeatable"),
                "placement": address.get("placement"),
                "ref": _occurrence_ref(address_id, occurrence),
            }
        )
    return sorted(result, key=lambda item: (str(item.get("ref") or ""), str(item.get("field_name") or "")))


def retrieve_table_occurrence(
    root: str | Path,
    year: str | int,
    document_id: str,
    concept_prefix: str,
    *,
    row_slot: int,
    copy: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve one complete row across all concept columns in a table."""
    inventory_path = Path(root) / "graph" / str(year) / "concepts" / f"{document_id}.yaml"
    inventory = yaml.safe_load(inventory_path.read_text(encoding="utf-8")) or {}
    axes: dict[str, Any] = {"row_slot": int(row_slot)}
    if copy is not None:
        axes["copy"] = copy
    result: list[dict[str, Any]] = []
    for concept in inventory.get("concepts", []) or []:
        concept_id = str(concept.get("concept_id") or "")
        if concept_id.startswith(concept_prefix):
            result.extend(retrieve_occurrences(root, year, document_id, concept_id, axes=axes))
    return sorted(result, key=lambda item: (str(item.get("ref") or ""), str(item.get("field_name") or "")))


def _occurrence_ref(address_id: str, occurrence: dict[str, Any]) -> str | None:
    """Import the workbench ref projection without making it a pipeline dependency."""
    from workbench.refs import unit_ref_from_address

    return unit_ref_from_address(address_id, occurrence)


def structured_address_ids(root: str | Path, year: str | int = 2025) -> set[str]:
    """Return promoted address ids carrying an S3a concept."""
    result: set[str] = set()
    for document_id in STRUCTURED_DOCUMENTS:
        path = Path(root) / "graph" / str(year) / "addresses" / f"{document_id}.yaml"
        if not path.is_file():
            continue
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        result.update(str(item["address_id"]) for item in payload.get("addresses", []) or [] if isinstance(item, dict) and item.get("concept_id"))
    return result


__all__ = [
    "ConceptError", "STRUCTURED_DOCUMENTS", "build_document_concepts", "mint_concept_id",
    "promote_structured_concepts", "retrieve_occurrences", "retrieve_table_occurrence",
    "structured_address_ids", "validate_concept_id", "validate_occurrence_contract",
]
