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

INFORMATION_RETURN_DOCUMENTS = (
    "form_w2_2025",
    "form_1099b_2025",
    "form_1099_int_2025",
    "form_1099_div_2025",
    "form_13614_c_2025",
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
        evidence = _control_evidence(
            item, mappings.get(field_name), dispositions[field_name], document_id=document_id,
        )
        if evidence is None:
            exemption = {"field_name": field_name, "population_policy": dispositions[field_name]["population_policy"]}
            if document_id == "form_w2_2025" and re.fullmatch(r".*\.f[1-6]_17\[0\]", field_name):
                exemption.update({
                    "display_name": "Shaded no-entry box 9",
                    "population_policy": "intentionally_blank",
                    "reason": "The official Form W-2 shades captionless box 9 while the AcroForm includes a text widget.",
                    "downstream_effect": "None - no node maps to this widget and the fill pipeline never writes it.",
                    "missing_capability": "None - this is official shading, not a capability gap.",
                })
            exemptions.append(exemption)
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
        "exemptions": exemptions,
        "coverage": {
            "inventory": len(inventory), "addressed_widgets": len(controls), "exempt_widgets": len(exemptions),
            "node_bindings": len(node_bindings), "references": len(references),
        },
    }


def _control_evidence(item: dict[str, Any], mapping: dict[str, Any] | None,
                      disposition: dict[str, Any], *, document_id: str) -> dict[str, Any] | None:
    if document_id == "form_8949_2025":
        return _form_8949_control_evidence(item, mapping, disposition)
    if document_id == "form_w2_2025":
        return _form_w2_control_evidence(item)
    if document_id in {"form_1099b_2025", "form_1099_div_2025", "form_1099_int_2025"}:
        return _form_1099_control_evidence(item, document_id)
    line = item.get("line_anchor")
    role = _role(item, mapping)
    total = re.fullmatch(
        r"form_8949_2025_part_(i|ii)_line_2_line_2_column_([degh])_total",
        str(mapping.get("slot", "")) if mapping else "",
    )
    runtime_ref = str(disposition.get("runtime_fact_ref", ""))
    box = _box_token(str(item["field_name"])) if document_id in INFORMATION_RETURN_DOCUMENTS else None
    if document_id == "form_13614_c_2025" and runtime_ref:
        token = runtime_ref.rsplit(".", 1)[-1]
        terminal = "option" if role in {"checkbox", "radio", "choice"} else "control"
        path = [{"kind": "section", "token": "intake"}, {"kind": terminal, "token": token}]
        official_ref = token
    elif box:
        terminal = "option" if role in {"checkbox", "radio", "choice"} else "control"
        path = [{"kind": "box", "token": box}, {"kind": terminal, "token": _box_control_token(item, role)}]
        official_ref = f"Box {box}"
    elif document_id in INFORMATION_RETURN_DOCUMENTS:
        return None
    elif total:
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


def _form_w2_control_evidence(item: dict[str, Any]) -> dict[str, Any] | None:
    """Collapse the six official W-2 copies onto one authored box template."""
    field_name = str(item["field_name"])
    leaf = field_name.rsplit(".", 1)[-1]
    text_match = re.fullmatch(r"f[1-6]_([0-9]{2})\[0\]", leaf)
    check_match = re.fullmatch(r"c[1-6]_([1-4])\[0\]", leaf)
    if check_match:
        choice = check_match.group(1)
        box, token, label = {
            "1": ("void", "void", "VOID"),
            "2": ("13", "statutory_employee", "Statutory employee"),
            "3": ("13", "retirement_plan", "Retirement plan"),
            "4": ("13", "third_party_sick_pay", "Third-party sick pay"),
        }[choice]
        path = [{"kind": "box", "token": box}, {"kind": "option", "token": token}]
        official_ref = "VOID" if box == "void" else f"Box {box}"
        role = "checkbox"
    elif text_match:
        number = int(text_match.group(1))
        scalar = {
            1: ("a", "employee_ssn", "Employee's social security number", "identifier"),
            2: ("b", "value", "Employer identification number (EIN)", "identifier"),
            3: ("c", "value", "Employer's name, address, and ZIP code", "text"),
            4: ("d", "value", "Control number", "identifier"),
            5: ("e", "first_name_initial", "Employee's first name and initial", "text"),
            6: ("e", "last_name", "Last name", "text"),
            7: ("e", "suffix", "Suffix", "text"),
            8: ("f", "value", "Employee's address and ZIP code", "text"),
            9: ("1", "value", "Wages, tips, other compensation", "amount"),
            10: ("2", "value", "Federal income tax withheld", "amount"),
            11: ("3", "value", "Social security wages", "amount"),
            12: ("4", "value", "Social security tax withheld", "amount"),
            13: ("5", "value", "Medicare wages and tips", "amount"),
            14: ("6", "value", "Medicare tax withheld", "amount"),
            15: ("7", "value", "Social security tips", "amount"),
            16: ("8", "value", "Allocated tips", "amount"),
            18: ("10", "value", "Dependent care benefits", "amount"),
            19: ("11", "value", "Nonqualified plans", "amount"),
            28: ("14", "value", "Other", "text"),
        }
        if number in scalar:
            box, token, label, role = scalar[number]
            path = [{"kind": "box", "token": box}, {"kind": "control", "token": token}]
            official_ref = f"Box {box}"
        elif 20 <= number <= 27:
            column = "code" if number % 2 == 0 else "amount"
            path = [{"kind": "box", "token": "12"}, {"kind": "row_template", "token": "entry"},
                    {"kind": "column", "token": column}]
            official_ref = f"Box 12 {column}"
            label = "Code" if column == "code" else "Amount"
            role = "text" if column == "code" else "amount"
        elif 29 <= number <= 42:
            box, token, label, role = {
                29: ("15", "state", "State", "text"),
                30: ("15", "employer_state_id", "Employer's state ID number", "text"),
                31: ("15", "state", "State", "text"),
                32: ("15", "employer_state_id", "Employer's state ID number", "text"),
                33: ("16", "state_wages", "State wages, tips, etc.", "amount"),
                34: ("16", "state_wages", "State wages, tips, etc.", "amount"),
                35: ("17", "state_income_tax", "State income tax", "amount"),
                36: ("17", "state_income_tax", "State income tax", "amount"),
                37: ("18", "local_wages", "Local wages, tips, etc.", "amount"),
                38: ("18", "local_wages", "Local wages, tips, etc.", "amount"),
                39: ("19", "local_income_tax", "Local income tax", "amount"),
                40: ("19", "local_income_tax", "Local income tax", "amount"),
                41: ("20", "locality_name", "Locality name", "text"),
                42: ("20", "locality_name", "Locality name", "text"),
            }[number]
            path = [{"kind": "table", "token": "state_local"},
                    {"kind": "row_template", "token": "jurisdiction"},
                    {"kind": "column", "token": token}]
            official_ref = f"Box {box}"
        else:
            return None
    else:
        return None
    return {
        "semantic_path": path, "official_ref": official_ref, "control_role": role,
        "printed_label": label, "field_name": field_name,
        "widget_type": item["field_type"], "page": item["page"],
        "rect": [item["x0"], item["y0"], item["x1"], item["y1"]],
        "semantic_status": "pending_review",
    }


def _form_1099_control_evidence(item: dict[str, Any], document_id: str) -> dict[str, Any] | None:
    """Collapse official 1099 copy pages onto one authored control template."""
    field_name = str(item["field_name"])
    leaf = field_name.rsplit(".", 1)[-1]
    check = re.fullmatch(r"c[12]_([0-9]+)\[([0-9]+)\]", leaf)
    if check:
        key = (int(check.group(1)), int(check.group(2)), int(float(item["y0"]) + 0.5))
        header_choices = {
            (1, 0, 25): ("void", "VOID"),
            (1, 1, 25): ("corrected", "CORRECTED"),
        }
        if key in header_choices:
            token, label = header_choices[key]
            return _campaign_control(item, [{"kind": "section", "token": "header"},
                                            {"kind": "option", "token": token}],
                                     label, label, "checkbox")
        choice = _form_1099_choice(document_id, key)
        if choice is None:
            return None
        box, token, label = choice
        if box is None:
            path = [{"kind": "section", "token": "recipient"}, {"kind": "option", "token": token}]
            return _campaign_control(item, path, label, label, "checkbox")
        path = [{"kind": "box", "token": box}, {"kind": "option", "token": token}]
        return _campaign_control(item, path, f"Box {box}", label, "checkbox")

    text = re.fullmatch(r"(?:CalendarYear[12]_)?f?([12])?_?([0-9]+)\[0\]", leaf)
    if not text:
        return None
    number = int(text.group(2))
    spec = _form_1099_text_spec(document_id, number, leaf.startswith("CalendarYear"))
    if spec is None:
        return None
    box, token, label, role = spec
    if box is None:
        path = [{"kind": "section", "token": "header" if token == "calendar_year" else "recipient"},
                {"kind": "control", "token": token}]
        return _campaign_control(item, path, label, label, role)
    if token in {"state", "state_id", "state_tax"}:
        path = [{"kind": "table", "token": "state"}, {"kind": "row_template", "token": "jurisdiction"},
                {"kind": "column", "token": token}]
    else:
        path = [{"kind": "box", "token": box}, {"kind": "control", "token": token}]
    return _campaign_control(item, path, f"Box {box}", label, role)


def _form_1099_choice(document_id: str, key: tuple[int, int, int]) -> tuple[str | None, str, str] | None:
    common = {
        (2, 0, 310): (None, "fatca_filing_requirement", "FATCA filing requirement"),
        (3, 0, 310): (None, "fatca_filing_requirement", "FATCA filing requirement"),
        (3, 0, 338): (None, "second_tin_notice", "2nd TIN not."),
        (4, 0, 338): (None, "second_tin_notice", "2nd TIN not."),
    }
    if document_id == "form_1099b_2025":
        return {
            (2, 0, 302): (None, "second_tin_notice", "2nd TIN not."),
            (3, 0, 326): (None, "fatca_filing_requirement", "FATCA filing requirement"),
            (4, 0, 182): ("2", "short_term", "Short-term gain or loss"),
            (4, 1, 194): ("2", "long_term", "Long-term gain or loss"),
            (4, 2, 206): ("2", "ordinary", "Ordinary"),
            (5, 0, 194): ("3", "collectibles", "Collectibles"),
            (5, 1, 206): ("3", "qof", "QOF"),
            (6, 0, 230): ("5", "noncovered_security", "Check if noncovered security"),
            (7, 0, 254): ("6", "gross_proceeds", "Gross proceeds"),
            (7, 1, 266): ("6", "net_proceeds", "Net proceeds"),
            (8, 0, 266): ("7", "loss_not_allowed", "Check if loss is not allowed based on amount in 1d"),
            (9, 0, 362): ("12", "basis_reported", "Check if basis reported to IRS"),
        }.get(key)
    return common.get(key)


def _form_1099_text_spec(
    document_id: str, number: int, calendar_year: bool,
) -> tuple[str | None, str, str, str] | None:
    if calendar_year:
        return None, "calendar_year", "For calendar year", "text"
    common = {
        1: (None, "payer_name_address", "Payer's name, street address, city or town, state or province, country, ZIP or foreign postal code, and telephone number", "text"),
        2: (None, "payer_tin", "Payer's TIN", "identifier"),
        3: (None, "recipient_tin", "Recipient's TIN", "identifier"),
        4: (None, "recipient_name", "Recipient's name", "text"),
        5: (None, "recipient_street", "Street address (including apt. no.)", "text"),
        6: (None, "recipient_city", "City or town, state or province, country, and ZIP or foreign postal code", "text"),
        7: (None, "account_number", "Account number (see instructions)", "identifier"),
    }
    if document_id == "form_1099b_2025":
        specs = {
            **common,
            8: (None, "cusip_number", "CUSIP number", "identifier"),
            9: ("14", "state", "State name", "text"), 10: ("14", "state", "State name", "text"),
            11: ("15", "state_id", "State identification no.", "identifier"),
            12: ("15", "state_id", "State identification no.", "identifier"),
            13: ("16", "state_tax", "State tax withheld", "amount"),
            14: ("16", "state_tax", "State tax withheld", "amount"),
            15: (None, "form_8949_checkbox", "Applicable checkbox on Form 8949", "text"),
            16: ("1a", "value", "Description of property (Example: 100 sh. XYZ Co.)", "description"),
            17: ("1b", "value", "Date acquired", "date"), 18: ("1c", "value", "Date sold or disposed", "date"),
            19: ("1d", "value", "Proceeds", "amount"), 20: ("1e", "value", "Cost or other basis", "amount"),
            21: ("1f", "value", "Accrued market discount", "amount"),
            22: ("1g", "value", "Wash sale loss disallowed", "amount"),
            23: ("4", "value", "Federal income tax withheld", "amount"),
            24: ("8", "value", "Profit or (loss) realized in 2025 on closed contracts", "amount"),
            25: ("9", "value", "Unrealized profit or (loss) on open contracts - 12/31/2024", "amount"),
            26: ("10", "value", "Unrealized profit or (loss) on open contracts - 12/31/2025", "amount"),
            27: ("11", "value", "Aggregate profit or (loss) on contracts", "amount"),
            28: ("13", "value", "Bartering", "amount"),
        }
        return specs.get(number)
    if document_id == "form_1099_div_2025":
        if number == 1:
            return None, "calendar_year", "For calendar year", "text"
        div_common = {
            number + 1: value for number, value in common.items()
        }
        boxes = {
            9: ("1a", "Total ordinary dividends"), 10: ("1b", "Qualified dividends"),
            11: ("2a", "Total capital gain distr."), 12: ("2b", "Unrecap. Sec. 1250 gain"),
            13: ("2c", "Section 1202 gain"), 14: ("2d", "Collectibles (28%) gain"),
            15: ("2e", "Section 897 ordinary dividends"), 16: ("2f", "Section 897 capital gain"),
            17: ("3", "Nondividend distributions"), 18: ("4", "Federal income tax withheld"),
            19: ("5", "Section 199A dividends"), 20: ("6", "Investment expenses"),
            21: ("7", "Foreign tax paid"), 22: ("8", "Foreign country or U.S. possession"),
            23: ("9", "Cash liquidation distributions"), 24: ("10", "Noncash liquidation distributions"),
            25: ("12", "Exempt-interest dividends"), 26: ("13", "Specified private activity bond interest dividends"),
        }
        if number in boxes:
            box, label = boxes[number]
            return box, "value", label, "text" if box == "8" else "amount"
        state = {27: ("14", "state", "State"), 28: ("14", "state", "State"),
                 29: ("15", "state_id", "State identification no."), 30: ("15", "state_id", "State identification no."),
                 31: ("16", "state_tax", "State tax withheld"), 32: ("16", "state_tax", "State tax withheld")}
        if number in state:
            box, token, label = state[number]
            return box, token, label, "amount" if token == "state_tax" else "text"
        return div_common.get(number)
    specs = {
        **common,
        8: (None, "payer_rtn", "Payer's RTN (optional)", "identifier"),
        9: ("1", "value", "Interest income", "amount"), 10: ("2", "value", "Early withdrawal penalty", "amount"),
        11: ("3", "value", "Interest on U.S. Savings Bonds and Treasury obligations", "amount"),
        12: ("4", "value", "Federal income tax withheld", "amount"), 13: ("5", "value", "Investment expenses", "amount"),
        14: ("6", "value", "Foreign tax paid", "amount"), 15: ("7", "value", "Foreign country or U.S. territory", "text"),
        16: ("8", "value", "Tax-exempt interest", "amount"), 17: ("9", "value", "Specified private activity bond interest", "amount"),
        18: ("10", "value", "Market discount", "amount"), 19: ("11", "value", "Bond premium", "amount"),
        20: ("12", "value", "Bond premium on Treasury obligations", "amount"),
        21: ("13", "value", "Bond premium on tax-exempt bond", "amount"),
        22: ("14", "value", "Tax-exempt and tax credit bond CUSIP no.", "identifier"),
        23: ("15", "state", "State", "text"), 24: ("15", "state", "State", "text"),
        25: ("16", "state_id", "State identification no.", "identifier"),
        26: ("16", "state_id", "State identification no.", "identifier"),
        27: ("17", "state_tax", "State tax withheld", "amount"),
        28: ("17", "state_tax", "State tax withheld", "amount"),
    }
    return specs.get(number)


def _campaign_control(
    item: dict[str, Any], path: list[dict[str, str]], official_ref: str, label: str, role: str,
) -> dict[str, Any]:
    return {
        "semantic_path": path, "official_ref": official_ref, "control_role": role,
        "printed_label": label, "field_name": item["field_name"], "widget_type": item["field_type"],
        "page": item["page"], "rect": [item["x0"], item["y0"], item["x1"], item["y1"]],
        "semantic_status": "pending_review",
    }


def _form_8949_control_evidence(
    item: dict[str, Any], mapping: dict[str, Any] | None, disposition: dict[str, Any]
) -> dict[str, Any] | None:
    """Project every meaningful Form 8949 widget through authored templates."""
    field_name = str(item["field_name"])
    page = int(item["page"])
    part = "i" if page == 1 else "ii"
    header = re.fullmatch(r".*\.f[12]_0([12])\[0\]", field_name)
    choice = re.fullmatch(r".*\.c[12]_1\[([0-5])\]", field_name)
    row = re.fullmatch(r".*\.Row([0-9]+)\[0\]\.f[12]_([0-9]+)\[0\]", field_name)
    total = re.fullmatch(r".*\.f[12]_9([1-5])\[0\]", field_name)
    if header:
        token, label = {
            "1": ("name", "Name(s) shown on return"),
            "2": ("taxpayer_identification_number", "Social security number or taxpayer identification number"),
        }[header.group(1)]
        path = [{"kind": "section", "token": "header"}, {"kind": "control", "token": token}]
        official_ref = "Header"
        role = "identifier" if header.group(1) == "2" else "text"
    elif choice:
        labels = {
            "i": (
                ("a", "Short-term transactions reported on Form(s) 1099-B showing basis was reported to the IRS"),
                ("b", "Short-term transactions reported on Form(s) 1099-B showing basis was not reported to the IRS"),
                ("c", "Short-term transactions, other than digital asset transactions, not reported to you on Form 1099-B or Form 1099-DA"),
                ("g", "Short-term transactions reported on Form(s) 1099-DA showing basis was reported to the IRS"),
                ("h", "Short-term transactions reported on Form(s) 1099-DA showing basis was not reported to the IRS"),
                ("i", "Short-term digital asset transactions not reported to you on Form 1099-DA or Form 1099-B"),
            ),
            "ii": (
                ("d", "Long-term transactions reported on Form(s) 1099-B showing basis was reported to the IRS"),
                ("e", "Long-term transactions reported on Form(s) 1099-B showing basis was not reported to the IRS"),
                ("f", "Long-term transactions, other than digital asset transactions, not reported to you on Form 1099-B or Form 1099-DA"),
                ("j", "Long-term transactions reported on Form(s) 1099-DA showing basis was reported to the IRS"),
                ("k", "Long-term transactions reported on Form(s) 1099-DA showing basis was not reported to the IRS"),
                ("l", "Long-term digital asset transactions not reported to you on Form 1099-DA or Form 1099-B"),
            ),
        }
        token, label = labels[part][int(choice.group(1))]
        path = [{"kind": "section", "token": f"part_{part}_transaction_type"},
                {"kind": "option", "token": token}]
        official_ref = f"Box {token.upper()}"
        role = "checkbox"
    elif row:
        index = int(row.group(2))
        column = "abcdefgh"[(index - 3) % 8]
        labels = {
            "a": "Description of property",
            "b": "Date acquired",
            "c": "Date sold or disposed of",
            "d": "Proceeds (sales price)",
            "e": "Cost or other basis",
            "f": "Code(s) from instructions",
            "g": "Amount of adjustment",
            "h": "Gain or (loss)",
        }
        path = [{"kind": "table", "token": f"part_{part}_line_1"},
                {"kind": "row_template", "token": "transaction"},
                {"kind": "column", "token": column}]
        official_ref = f"Line 1 column ({column})"
        label = labels[column]
        role = "description" if column in {"a", "f"} else "date" if column in {"b", "c"} else "amount"
    elif total:
        column = "defgh"[int(total.group(1)) - 1]
        if column == "f":
            return None
        labels = {
            "d": "Total proceeds",
            "e": "Total cost or other basis",
            "g": "Total adjustments",
            "h": "Total gain or (loss)",
        }
        path = [{"kind": "table", "token": f"part_{part}_line_2"},
                {"kind": "row_template", "token": "total"},
                {"kind": "column", "token": column}]
        official_ref = f"Line 2 column ({column})"
        label = labels[column]
        role = "amount"
    else:
        return None
    return {
        "semantic_path": path, "official_ref": official_ref, "control_role": role,
        "printed_label": label, "field_name": field_name,
        "widget_type": item["field_type"], "page": page,
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
    declared = next((item for item in manifest["documents"] if item["document_id"] == document_id), None)
    if declared and declared.get("expected_sha256"):
        return str(declared["expected_sha256"])
    pdf = root / ".cache" / "raw" / "2025" / f"{document_id}.pdf"
    return hashlib.sha256(pdf.read_bytes()).hexdigest()


def _role(item: dict[str, Any], mapping: dict[str, Any] | None) -> str:
    if mapping and mapping.get("format") == "checkbox" or item["field_type"] == "CheckBox":
        return "checkbox"
    if item["field_type"] == "RadioButton":
        return "radio"
    if item["field_type"] == "Choice":
        return "choice"
    if mapping and mapping.get("format") == "date":
        return "date"
    return "amount" if item.get("line_anchor") or mapping else "text"


def _box_token(field_name: str) -> str | None:
    matches = re.findall(r"(?:^|\.)Box(?!es)([A-Za-z0-9]+?)(?:_+ReadOrder)?\[", field_name)
    return matches[-1].lower() if matches else None


def _box_control_token(item: dict[str, Any], role: str) -> str:
    leaf = str(item["field_name"]).rsplit(".", 1)[-1]
    match = re.fullmatch(r"([A-Za-z]+)\d*(_[0-9]+)?\[([0-9]+)\]", leaf)
    if match:
        stem = f"{match.group(1).lower()}{match.group(2) or ''}"
        return f"choice_{stem}_{match.group(3)}" if role in {"checkbox", "radio", "choice"} else stem
    digest = hashlib.sha256(leaf.encode("utf-8")).hexdigest()[:12]
    return f"choice_{digest}" if role in {"checkbox", "radio", "choice"} else f"field_{digest}"


def _widget_type(value: str) -> str:
    return {"Text": "text", "CheckBox": "checkbox", "RadioButton": "radio", "Choice": "choice",
            "Signature": "signature"}.get(value, "other")


def _binding_artifact(document_id: str, kind: str, bindings: list[dict[str, Any]]) -> dict[str, Any]:
    return {"schema_version": 1, "year": 2025, "document_id": document_id,
            "binding_kind": kind, "bindings": sorted(bindings, key=lambda item: next(iter(item.values())))}
