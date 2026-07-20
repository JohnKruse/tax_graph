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
    if document_id == "form_1040_2025":
        return _form_1040_control_evidence(item, mapping)
    if document_id == "schedule_1_2025":
        return _schedule_1_control_evidence(item)
    if document_id == "schedule_1a_2025":
        return _schedule_1a_control_evidence(item)
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


def _schedule_1_control_evidence(item: dict[str, Any]) -> dict[str, Any] | None:
    """Project every Schedule 1 widget through its printed 2025 line identity."""
    leaf = str(item["field_name"]).rsplit(".", 1)[-1]
    header_specs = {
        "f1_01[0]": ("name", "Name(s) shown on Form 1040, 1040-SR, or 1040-NR", "text"),
        "f1_02[0]": ("social_security_number", "Your social security number", "identifier"),
    }
    if leaf in header_specs:
        token, label, role = header_specs[leaf]
        return _campaign_control(
            item,
            [{"kind": "section", "token": "identity"}, {"kind": "control", "token": token}],
            "Header",
            label,
            role,
        )

    line_specs = {
        "f1_03[0]": ("1a", "Form 1099-K amount included in error or for personal items", "amount"),
        "f1_04[0]": ("1", "Taxable refunds, credits, or offsets of state and local income taxes", "amount"),
        "f1_05[0]": ("2a", "Alimony received", "amount"),
        "f1_06[0]": ("2b", "Date of original divorce or separation agreement", "date"),
        "f1_07[0]": ("3", "Business income or (loss)", "amount"),
        "f1_08[0]": ("4", "Other gains or (losses)", "amount"),
        "f1_09[0]": ("5", "Rental real estate, royalties, partnerships, S corporations, trusts, etc.", "amount"),
        "f1_10[0]": ("6", "Farm income or (loss)", "amount"),
        "f1_12[0]": ("7", "Unemployment compensation", "amount"),
        "f1_13[0]": ("8a", "Net operating loss", "amount"),
        "f1_14[0]": ("8b", "Gambling", "amount"),
        "f1_15[0]": ("8c", "Cancellation of debt", "amount"),
        "f1_16[0]": ("8d", "Foreign earned income exclusion from Form 2555", "amount"),
        "f1_17[0]": ("8e", "Income from Form 8853", "amount"),
        "f1_18[0]": ("8f", "Income from Form 8889", "amount"),
        "f1_19[0]": ("8g", "Alaska Permanent Fund dividends", "amount"),
        "f1_20[0]": ("8h", "Jury duty pay", "amount"),
        "f1_21[0]": ("8i", "Prizes and awards", "amount"),
        "f1_22[0]": ("8j", "Activity not engaged in for profit income", "amount"),
        "f1_23[0]": ("8k", "Stock options", "amount"),
        "f1_24[0]": ("8l", "Income from the rental of personal property", "amount"),
        "f1_25[0]": ("8m", "Olympic and Paralympic medals and USOC prize money", "amount"),
        "f1_26[0]": ("8n", "Section 951(a) inclusion", "amount"),
        "f1_27[0]": ("8o", "Section 951A(a) inclusion", "amount"),
        "f1_28[0]": ("8p", "Section 461(l) excess business loss adjustment", "amount"),
        "f1_29[0]": ("8q", "Taxable distributions from an ABLE account", "amount"),
        "f1_30[0]": ("8r", "Scholarship and fellowship grants not reported on Form W-2", "amount"),
        "f1_31[0]": ("8s", "Nontaxable Medicaid waiver payments included on Form 1040, line 1a or 1d", "amount"),
        "f1_32[0]": ("8t", "Pension or annuity from a nonqualified deferred compensation plan", "amount"),
        "f1_33[0]": ("8u", "Wages earned while incarcerated", "amount"),
        "f1_34[0]": ("8v", "Digital assets received as ordinary income not reported elsewhere", "amount"),
        "f1_35[0]": ("8z", "Other income - type", "description"),
        "f1_36[0]": ("8z", "Other income - amount", "amount"),
        "f1_37[0]": ("9", "Total other income", "amount"),
        "f1_38[0]": ("10", "Additional income", "amount"),
        "f2_01[0]": ("11", "Educator expenses", "amount"),
        "f2_02[0]": ("12", "Certain business expenses of reservists, performing artists, and fee-basis government officials", "amount"),
        "f2_03[0]": ("13", "Health savings account deduction", "amount"),
        "f2_04[0]": ("14", "Moving expenses for members of the Armed Forces", "amount"),
        "f2_05[0]": ("15", "Deductible part of self-employment tax", "amount"),
        "f2_06[0]": ("16", "Self-employed SEP, SIMPLE, and qualified plans", "amount"),
        "f2_07[0]": ("17", "Self-employed health insurance deduction", "amount"),
        "f2_08[0]": ("18", "Penalty on early withdrawal of savings", "amount"),
        "f2_09[0]": ("19a", "Alimony paid", "amount"),
        "f2_10[0]": ("19b", "Recipient's social security number", "identifier"),
        "f2_11[0]": ("19c", "Date of original divorce or separation agreement", "date"),
        "f2_12[0]": ("20", "IRA deduction", "amount"),
        "f2_13[0]": ("21", "Student loan interest deduction", "amount"),
        "f2_14[0]": ("22", "Reserved for future use", "amount"),
        "f2_15[0]": ("23", "Archer MSA deduction", "amount"),
        "f2_16[0]": ("24a", "Jury duty pay", "amount"),
        "f2_17[0]": ("24b", "Deductible expenses related to income reported on line 8l", "amount"),
        "f2_18[0]": ("24c", "Nontaxable value of Olympic and Paralympic medals and USOC prize money", "amount"),
        "f2_19[0]": ("24d", "Reforestation amortization and expenses", "amount"),
        "f2_20[0]": ("24e", "Repayment of supplemental unemployment benefits under the Trade Act of 1974", "amount"),
        "f2_21[0]": ("24f", "Contributions to section 501(c)(18)(D) pension plans", "amount"),
        "f2_22[0]": ("24g", "Contributions by certain chaplains to section 403(b) plans", "amount"),
        "f2_23[0]": ("24h", "Attorney fees and court costs for actions involving certain unlawful discrimination claims", "amount"),
        "f2_24[0]": ("24i", "Attorney fees and court costs paid in connection with an IRS award", "amount"),
        "f2_25[0]": ("24j", "Housing deduction from Form 2555", "amount"),
        "f2_26[0]": ("24k", "Excess deductions of section 67(e) expenses from Schedule K-1 (Form 1041)", "amount"),
        "f2_27[0]": ("24z", "Other adjustments - type", "description"),
        "f2_28[0]": ("24z", "Other adjustments - amount", "amount"),
        "f2_29[0]": ("25", "Total other adjustments", "amount"),
        "f2_30[0]": ("26", "Adjustments to income", "amount"),
    }
    if leaf == "f1_11[0]":
        return _campaign_control(
            item,
            [{"kind": "line", "token": "7"}, {"kind": "control", "token": "repaid_amount"}],
            "7",
            "Amount of repaid unemployment compensation",
            "amount",
        )
    if leaf in line_specs:
        line, label, role = line_specs[leaf]
        return _campaign_control(
            item,
            [{"kind": "line", "token": line}, {"kind": "control", "token": role}],
            line,
            label,
            role,
        )

    choice_specs = {
        "c1_1[0]": ("4", "form_4797", "Other gains or (losses) from Form 4797"),
        "c1_2[0]": ("4", "form_4684", "Other gains or (losses) from Form 4684"),
        "c1_3[0]": ("7", "repaid_overpayment", "Repaid 2025 unemployment compensation overpayment"),
        "c2_1[0]": ("14", "storage_fees_only", "Claiming only storage fees for a move to a foreign country"),
        "c2_2[0]": ("21", "mfs_lived_apart", "Married filing separately and lived apart from spouse for the entire year"),
    }
    if leaf in choice_specs:
        line, token, label = choice_specs[leaf]
        return _campaign_control(
            item,
            [{"kind": "line", "token": line}, {"kind": "option", "token": token}],
            line,
            label,
            "checkbox",
        )
    return None


def _schedule_1a_control_evidence(item: dict[str, Any]) -> dict[str, Any] | None:
    """Project every Schedule 1-A widget through its printed 2025 identity."""
    field_name = str(item["field_name"])
    leaf = field_name.rsplit(".", 1)[-1]
    header_specs = {
        "f1_01[0]": ("name", "Name(s) shown on Form 1040, 1040-SR, or 1040-NR", "text"),
        "f1_02[0]": ("social_security_number", "Your social security number", "identifier"),
    }
    if leaf in header_specs:
        token, label, role = header_specs[leaf]
        return _campaign_control(
            item,
            [{"kind": "section", "token": "identity"}, {"kind": "control", "token": token}],
            "Header",
            label,
            role,
        )

    table_match = re.search(r"Line22([ab])\[0\]", field_name)
    if table_match:
        row = table_match.group(1)
        column, label, role = {
            "f2_01[0]": ("vin", "Vehicle identification number (VIN)", "identifier"),
            "f2_02[0]": ("deducted_elsewhere", "Deducted on Schedule C, Schedule E, or Schedule F", "amount"),
            "f2_03[0]": ("schedule_1a", "Schedule 1-A", "amount"),
            "f2_04[0]": ("vin", "Vehicle identification number (VIN)", "identifier"),
            "f2_05[0]": ("deducted_elsewhere", "Deducted on Schedule C, Schedule E, or Schedule F", "amount"),
            "f2_06[0]": ("schedule_1a", "Schedule 1-A", "amount"),
        }[leaf]
        return _campaign_control(
            item,
            [
                {"kind": "table", "token": "line_22"},
                {"kind": "row_template", "token": "vehicle"},
                {"kind": "column", "token": column},
            ],
            f"Line 22{row} column ({'i' if column == 'vin' else 'ii' if column == 'deducted_elsewhere' else 'iii'})",
            label,
            role,
        )

    line_specs = {
        "f1_03[0]": ("1", "Amount from Form 1040, 1040-SR, or 1040-NR, line 11b"),
        "f1_04[0]": ("2a", "Income from Puerto Rico that you excluded"),
        "f1_05[0]": ("2b", "Amount from Form 2555, line 45"),
        "f1_06[0]": ("2c", "Amount from Form 2555, line 50"),
        "f1_07[0]": ("2d", "Amount from Form 4563, line 15"),
        "f1_08[0]": ("2e", "Add lines 2a, 2b, 2c, and 2d"),
        "f1_09[0]": ("3", "Add lines 1 and 2e"),
        "f1_10[0]": ("4a", "Enter qualified tips included on Form W-2, box 7"),
        "f1_11[0]": ("4b", "Qualified tips included on Form 4137, line 1, row A, column (c)"),
        "f1_12[0]": ("4c", "If you only received qualified tips as an employee"),
        "f1_13[0]": ("5", "Qualified tips received in the course of a trade or business"),
        "f1_14[0]": ("6", "Add lines 4c and 5"),
        "f1_15[0]": ("7", "Enter the smaller of the amount on line 6 or $25,000"),
        "f1_16[0]": ("8", "Amount from line 3"),
        "f1_17[0]": ("9", "$150,000 ($300,000 if married filing jointly)"),
        "f1_18[0]": ("10", "Subtract line 9 from line 8"),
        "f1_19[0]": ("11", "Divide line 10 by $1,000"),
        "f1_20[0]": ("12", "Multiply line 11 by $100"),
        "f1_21[0]": ("13", "Qualified tips deduction"),
        "f1_22[0]": ("14a", "Qualified overtime compensation included in Form W-2, box 1"),
        "f1_23[0]": ("14b", "Qualified overtime compensation included in Form 1099-NEC, box 1, or Form 1099-MISC, box 3"),
        "f1_24[0]": ("14c", "Add lines 14a and 14b"),
        "f1_25[0]": ("15", "Enter the smaller of the amount on line 14c or $12,500"),
        "f1_26[0]": ("16", "Amount from line 3"),
        "f1_27[0]": ("17", "$150,000 ($300,000 if married filing jointly)"),
        "f1_28[0]": ("18", "Subtract line 17 from line 16"),
        "f1_29[0]": ("19", "Divide line 18 by $1,000"),
        "f1_30[0]": ("20", "Multiply line 19 by $100"),
        "f1_31[0]": ("21", "Qualified overtime compensation deduction"),
        "f2_07[0]": ("23", "Add lines 22a and 22b, column (iii)"),
        "f2_08[0]": ("24", "Enter the smaller of the amount on line 23 or $10,000"),
        "f2_09[0]": ("25", "Amount from line 3"),
        "f2_10[0]": ("26", "$100,000 ($200,000 if married filing jointly)"),
        "f2_11[0]": ("27", "Subtract line 26 from line 25"),
        "f2_12[0]": ("28", "Divide line 27 by $1,000"),
        "f2_13[0]": ("29", "Multiply line 28 by $200"),
        "f2_14[0]": ("30", "Qualified passenger vehicle loan interest deduction"),
        "f2_15[0]": ("31", "Amount from line 3"),
        "f2_16[0]": ("32", "$75,000 ($150,000 if married filing jointly)"),
        "f2_17[0]": ("33", "Subtract line 32 from line 31"),
        "f2_18[0]": ("34", "Multiply line 33 by 6% (0.06)"),
        "f2_19[0]": ("35", "Subtract line 34 from $6,000"),
        "f2_20[0]": ("36a", "If you have a valid social security number"),
        "f2_21[0]": ("36b", "If you are married filing jointly"),
        "f2_22[0]": ("37", "Enhanced deduction for seniors"),
        "f2_23[0]": ("38", "Add lines 13, 21, 30, and 37"),
    }
    if leaf not in line_specs:
        return None
    line, label = line_specs[leaf]
    return _campaign_control(
        item,
        [{"kind": "line", "token": line}, {"kind": "control", "token": "amount"}],
        line,
        label,
        "amount",
    )


def _form_1040_control_evidence(
    item: dict[str, Any], mapping: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Project every Form 1040 widget through its own printed 2025 form identity."""
    field_name = str(item["field_name"])
    leaf = field_name.rsplit(".", 1)[-1]

    identity = {
        "taxpayer_first_name": "First name and middle initial",
        "taxpayer_last_name": "Last name",
        "taxpayer_ssn": "Your social security number",
        "spouse_first_name": "Spouse's first name and middle initial",
        "spouse_last_name": "Spouse's last name",
        "spouse_ssn": "Spouse's social security number",
        "address_line_1": "Home address (number and street)",
        "apartment": "Apt. no.",
        "city": "City, town, or post office",
        "state": "State",
        "zip_code": "ZIP code",
    }
    if mapping and mapping.get("identity_slot") in identity:
        token = str(mapping["identity_slot"])
        return _campaign_control(
            item,
            [{"kind": "section", "token": "identity"}, {"kind": "control", "token": token}],
            "Identity",
            identity[token],
            "identifier" if token.endswith("ssn") else "text",
        )
    if mapping and mapping.get("identity_slot") == "filing_status":
        token = str(mapping["checkbox_value"])
        label = {
            "single": "Single",
            "married_filing_jointly": "Married filing jointly (even if only one had income)",
            "married_filing_separately": "Married filing separately (MFS)",
            "head_of_household": "Head of household (HOH)",
            "qualifying_surviving_spouse": "Qualifying surviving spouse (QSS)",
        }[token]
        return _campaign_control(
            item,
            [{"kind": "section", "token": "filing_status"}, {"kind": "option", "token": token}],
            "Filing Status",
            label,
            "checkbox",
        )

    header_specs = {
        "f1_01[0]": ("other_tax_year_beginning", "Other tax year beginning", "text"),
        "f1_02[0]": ("other_tax_year_ending", "Other tax year ending", "text"),
        "f1_03[0]": ("other_tax_year_ending_suffix", "Other tax year ending year suffix", "text"),
        "c1_1[0]": ("section_301_9100_2", "Filed pursuant to section 301.9100-2", "checkbox"),
        "c1_2[0]": ("combat_zone", "Combat zone", "checkbox"),
        "f1_04[0]": ("combat_zone_name", "Combat zone name", "text"),
        "c1_3[0]": ("taxpayer_deceased", "Deceased", "checkbox"),
        "f1_05[0]": ("taxpayer_deceased_month", "Deceased date - month", "text"),
        "f1_06[0]": ("taxpayer_deceased_day", "Deceased date - day", "text"),
        "f1_07[0]": ("taxpayer_deceased_year", "Deceased date - year", "text"),
        "f1_08[0]": ("spouse_deceased_month", "Spouse deceased date - month", "text"),
        "f1_09[0]": ("spouse_deceased_day", "Spouse deceased date - day", "text"),
        "f1_10[0]": ("spouse_deceased_year", "Spouse deceased date - year", "text"),
        "c1_4[0]": ("other_filing_designation", "Other", "checkbox"),
        "f1_11[0]": ("other_filing_designation_text", "Other filing designation", "text"),
        "f1_12[0]": ("other_filing_designation_text", "Other filing designation", "text"),
        "f1_13[0]": ("other_filing_designation_text", "Other filing designation", "text"),
    }
    if leaf in header_specs:
        token, label, role = header_specs[leaf]
        terminal = "option" if role == "checkbox" else "control"
        return _campaign_control(
            item,
            [{"kind": "section", "token": "return_header"}, {"kind": terminal, "token": token}],
            "Header",
            label,
            role,
        )

    identity_extras = {
        "f1_25[0]": ("foreign_country", "Foreign country name", "text"),
        "f1_26[0]": ("foreign_province", "Foreign province/state/county", "text"),
        "f1_27[0]": ("foreign_postal_code", "Foreign postal code", "text"),
        "c1_5[0]": (
            "main_home_joint_return",
            "Check here if your main home, and your spouse's if filing a joint return, was in the U.S. for more than half of 2025",
            "checkbox",
        ),
        "c1_6[0]": ("presidential_election_you", "Presidential Election Campaign - You", "checkbox"),
        "c1_7[0]": ("presidential_election_spouse", "Presidential Election Campaign - Spouse", "checkbox"),
    }
    if leaf in identity_extras:
        token, label, role = identity_extras[leaf]
        terminal = "option" if role == "checkbox" else "control"
        return _campaign_control(
            item,
            [{"kind": "section", "token": "identity"}, {"kind": terminal, "token": token}],
            "Identity",
            label,
            role,
        )

    filing_extras = {
        "f1_28[0]": ("mfs_spouse_full_name", "MFS spouse's full name", "text"),
        "f1_29[0]": ("hoh_qss_child_name", "HOH or QSS qualifying child's name", "text"),
        "c1_9[0]": (
            "nonresident_alien_spouse_election",
            "Treating a nonresident alien or dual-status alien spouse as a U.S. resident",
            "checkbox",
        ),
        "f1_30[0]": ("nonresident_alien_spouse_name", "Nonresident alien spouse's name", "text"),
    }
    if leaf in filing_extras:
        token, label, role = filing_extras[leaf]
        terminal = "option" if role == "checkbox" else "control"
        return _campaign_control(
            item,
            [{"kind": "section", "token": "filing_status"}, {"kind": terminal, "token": token}],
            "Filing Status",
            label,
            role,
        )

    if leaf.startswith("c1_10["):
        token, label = ("yes", "Yes") if leaf == "c1_10[0]" else ("no", "No")
        return _campaign_control(
            item,
            [{"kind": "section", "token": "digital_assets"}, {"kind": "option", "token": token}],
            "Digital Assets",
            label,
            "checkbox",
        )

    if leaf == "c1_11[0]":
        return _campaign_control(
            item,
            [{"kind": "table", "token": "dependents"}, {"kind": "option", "token": "more_than_four"}],
            "Dependents",
            "More than four dependents",
            "checkbox",
        )
    dependent_text = re.fullmatch(r"f1_([3-4][0-9])\[0\]", leaf)
    if dependent_text and 31 <= int(dependent_text.group(1)) <= 46:
        number = int(dependent_text.group(1))
        column = ("first_name", "last_name", "ssn", "relationship")[(number - 31) // 4]
        label = {
            "first_name": "First name",
            "last_name": "Last name",
            "ssn": "SSN",
            "relationship": "Relationship",
        }[column]
        return _campaign_control(
            item,
            [{"kind": "table", "token": "dependents"}, {"kind": "row_template", "token": "dependent"},
             {"kind": "column", "token": column}],
            f"Dependents column {label}",
            label,
            "identifier" if column == "ssn" else "text",
        )
    dependent_choice = re.fullmatch(r"c1_([12][0-9]|3[01])\[([01])\]", leaf)
    if dependent_choice and 12 <= int(dependent_choice.group(1)) <= 31:
        number = int(dependent_choice.group(1))
        index = int(dependent_choice.group(2))
        if number <= 19:
            token = "lived_with_you_more_than_half_2025" if number % 2 == 0 else "in_the_us"
            label = "Lived with you more than half of 2025" if number % 2 == 0 else "And in the U.S."
        elif number <= 27:
            token = "full_time_student" if number % 2 == 0 else "permanently_totally_disabled"
            label = "Full-time student" if number % 2 == 0 else "Permanently and totally disabled"
        else:
            token = "child_tax_credit" if index == 0 else "credit_for_other_dependents"
            label = "Child tax credit" if index == 0 else "Credit for other dependents"
        return _campaign_control(
            item,
            [{"kind": "table", "token": "dependents"}, {"kind": "row_template", "token": "dependent"},
             {"kind": "column", "token": token}],
            f"Dependents column {label}",
            label,
            "checkbox",
        )
    if leaf == "c1_32[0]":
        return _campaign_control(
            item,
            [{"kind": "section", "token": "filing_status"},
             {"kind": "option", "token": "mfs_hoh_lived_apart"}],
            "Filing Status",
            "MFS or HOH and lived apart from spouse for the last 6 months of 2025",
            "checkbox",
        )

    line_text_specs = {
        "f1_47[0]": ("1a", "Total amount from Form(s) W-2, box 1", "amount"),
        "f1_48[0]": ("1b", "Household employee wages not reported on Form(s) W-2", "amount"),
        "f1_49[0]": ("1c", "Tip income not reported on line 1a", "amount"),
        "f1_50[0]": ("1d", "Medicaid waiver payments not reported on Form(s) W-2", "amount"),
        "f1_51[0]": ("1e", "Taxable dependent care benefits from Form 2441, line 26", "amount"),
        "f1_52[0]": ("1f", "Employer-provided adoption benefits from Form 8839, line 31", "amount"),
        "f1_53[0]": ("1g", "Wages from Form 8919, line 6", "amount"),
        "f1_54[0]": ("1h", "Other earned income - type", "description"),
        "f1_55[0]": ("1h", "Other earned income - amount", "amount"),
        "f1_56[0]": ("1i", "Nontaxable combat pay election", "amount"),
        "f1_57[0]": ("1z", "Add lines 1a through 1h", "amount"),
        "f1_58[0]": ("2a", "Tax-exempt interest", "amount"),
        "f1_59[0]": ("2b", "Taxable interest", "amount"),
        "f1_60[0]": ("3a", "Qualified dividends", "amount"),
        "f1_61[0]": ("3b", "Ordinary dividends", "amount"),
        "f1_62[0]": ("4a", "IRA distributions", "amount"),
        "f1_63[0]": ("4b", "Taxable amount", "amount"),
        "f1_64[0]": ("4c", "Option 3 word or code", "text"),
        "f1_65[0]": ("5a", "Pensions and annuities", "amount"),
        "f1_66[0]": ("5b", "Taxable amount", "amount"),
        "f1_67[0]": ("5c", "Option 3 word or code", "text"),
        "f1_68[0]": ("6a", "Social security benefits", "amount"),
        "f1_69[0]": ("6b", "Taxable amount", "amount"),
        "f1_70[0]": ("7a", "Capital gain or (loss)", "amount"),
        "f1_71[0]": ("7b", "Child's capital gain or (loss) included in line 7a", "amount"),
        "f1_72[0]": ("8", "Additional income from Schedule 1, line 10", "amount"),
        "f1_73[0]": ("9", "Add lines 1z, 2b, 3b, 4b, 5b, 6b, 7a, and 8", "amount"),
        "f1_74[0]": ("10", "Adjustments to income from Schedule 1, line 26", "amount"),
        "f1_75[0]": ("11a", "Subtract line 10 from line 9", "amount"),
        "f2_01[0]": ("11b", "Amount from line 11a (adjusted gross income)", "amount"),
        "f2_02[0]": ("12e", "Standard deduction or itemized deductions (from Schedule A)", "amount"),
        "f2_03[0]": ("13a", "Qualified business income deduction from Form 8995 or Form 8995-A", "amount"),
        "f2_04[0]": ("13b", "Additional deductions from Schedule 1-A, line 38", "amount"),
        "f2_05[0]": ("14", "Add lines 12e, 13a, and 13b", "amount"),
        "f2_06[0]": ("15", "Subtract line 14 from line 11b", "amount"),
        "f2_07[0]": ("16", "Other tax form number", "text"),
        "f2_08[0]": ("16", "Tax", "amount"),
        "f2_09[0]": ("17", "Amount from Schedule 2, line 3", "amount"),
        "f2_10[0]": ("18", "Add lines 16 and 17", "amount"),
        "f2_11[0]": ("19", "Child tax credit or credit for other dependents from Schedule 8812", "amount"),
        "f2_12[0]": ("20", "Amount from Schedule 3, line 8", "amount"),
        "f2_13[0]": ("21", "Add lines 19 and 20", "amount"),
        "f2_14[0]": ("22", "Subtract line 21 from line 18", "amount"),
        "f2_15[0]": ("23", "Other taxes, including self-employment tax, from Schedule 2, line 21", "amount"),
        "f2_16[0]": ("24", "Add lines 22 and 23", "amount"),
        "f2_17[0]": ("25a", "Federal income tax withheld from Form(s) W-2", "amount"),
        "f2_18[0]": ("25b", "Federal income tax withheld from Form(s) 1099", "amount"),
        "f2_19[0]": ("25c", "Federal income tax withheld from other forms", "amount"),
        "f2_20[0]": ("25d", "Add lines 25a through 25c", "amount"),
        "f2_21[0]": ("26", "2025 estimated tax payments and amount applied from 2024 return", "amount"),
        "f2_22[0]": ("26", "Former spouse's SSN", "identifier"),
        "f2_23[0]": ("27a", "Earned income credit (EIC)", "amount"),
        "f2_24[0]": ("28", "Additional child tax credit (ACTC) from Schedule 8812", "amount"),
        "f2_25[0]": ("29", "American opportunity credit from Form 8863, line 8", "amount"),
        "f2_26[0]": ("30", "Refundable adoption credit from Form 8839, line 13", "amount"),
        "f2_27[0]": ("31", "Amount from Schedule 3, line 15", "amount"),
        "f2_28[0]": ("32", "Add lines 27a, 28, 29, 30, and 31", "amount"),
        "f2_29[0]": ("33", "Add lines 25d, 26, and 32", "amount"),
        "f2_30[0]": ("34", "Subtract line 24 from line 33", "amount"),
        "f2_31[0]": ("35a", "Amount of line 34 you want refunded to you", "amount"),
        "f2_32[0]": ("35b", "Routing number", "identifier"),
        "f2_33[0]": ("35d", "Account number", "identifier"),
        "f2_34[0]": ("36", "Amount of line 34 you want applied to your 2026 estimated tax", "amount"),
        "f2_35[0]": ("37", "Subtract line 33 from line 24", "amount"),
        "f2_36[0]": ("38", "Estimated tax penalty", "amount"),
    }
    if leaf in line_text_specs:
        line, label, role = line_text_specs[leaf]
        return _campaign_control(
            item,
            [{"kind": "line", "token": line}, {"kind": "control", "token": role}],
            line,
            label,
            role,
        )

    line_choice_specs = {
        "c1_33[0]": ("3c", "line_3a", "Child's dividends are included in line 1 - Line 3a"),
        "c1_34[0]": ("3c", "line_3b", "Child's dividends are included in line 1 - Line 3b"),
        "c1_35[0]": ("4c", "rollover", "Rollover"),
        "c1_36[0]": ("4c", "qcd", "QCD"),
        "c1_37[0]": ("4c", "other_word_or_code", "Use another word or code"),
        "c1_38[0]": ("5c", "rollover", "Rollover"),
        "c1_39[0]": ("5c", "pso", "PSO"),
        "c1_40[0]": ("5c", "other_word_or_code", "Use another word or code"),
        "c1_41[0]": ("6c", "lump_sum_election", "Lump-sum election method"),
        "c1_42[0]": ("6d", "mfs_lived_apart", "Married filing separately and lived apart from spouse the entire year"),
        "c1_43[0]": ("7b", "schedule_d_not_required", "Schedule D not required"),
        "c1_44[0]": ("7b", "child_capital_gain", "Includes child's capital gain or (loss)"),
        "c2_1[0]": ("12a", "you_as_dependent", "You as a dependent"),
        "c2_2[0]": ("12a", "spouse_as_dependent", "Your spouse as a dependent"),
        "c2_3[0]": ("12b", "spouse_itemizes", "Spouse itemizes on a separate return"),
        "c2_4[0]": ("12c", "dual_status_alien", "You were a dual-status alien"),
        "c2_5[0]": ("12d", "you_born_before_1961", "You were born before January 2, 1961"),
        "c2_6[0]": ("12d", "you_blind", "You are blind"),
        "c2_7[0]": ("12d", "spouse_born_before_1961", "Spouse was born before January 2, 1961"),
        "c2_8[0]": ("12d", "spouse_blind", "Spouse is blind"),
        "c2_9[0]": ("16", "form_8814", "Form 8814"),
        "c2_10[0]": ("16", "form_4972", "Form 4972"),
        "c2_11[0]": ("16", "other_form", "Other form"),
        "c2_12[0]": ("27b", "clergy_schedule_se", "Clergy filing Schedule SE"),
        "c2_13[0]": ("27c", "do_not_claim_eic", "Do not claim the EIC"),
        "c2_14[0]": ("28", "do_not_claim_actc", "Do not claim the ACTC"),
        "c2_15[0]": ("35a", "form_8888_attached", "Form 8888 is attached"),
        "c2_16[0]": ("35c", "checking", "Checking"),
        "c2_16[1]": ("35c", "savings", "Savings"),
    }
    if leaf in line_choice_specs:
        line, token, label = line_choice_specs[leaf]
        return _campaign_control(
            item,
            [{"kind": "line", "token": line}, {"kind": "option", "token": token}],
            line,
            label,
            "checkbox",
        )

    section_specs = {
        "c2_17[0]": ("third_party_designee", "yes", "Yes", "checkbox"),
        "c2_17[1]": ("third_party_designee", "no", "No", "checkbox"),
        "f2_37[0]": ("third_party_designee", "name", "Designee's name", "text"),
        "f2_38[0]": ("third_party_designee", "phone", "Phone no.", "text"),
        "f2_39[0]": ("third_party_designee", "pin", "Personal identification number (PIN)", "identifier"),
        "f2_40[0]": ("sign_here", "your_occupation", "Your occupation", "text"),
        "f2_41[0]": ("sign_here", "your_ip_pin", "Your Identity Protection PIN", "identifier"),
        "f2_42[0]": ("sign_here", "spouse_occupation", "Spouse's occupation", "text"),
        "f2_43[0]": ("sign_here", "spouse_ip_pin", "Spouse's Identity Protection PIN", "identifier"),
        "f2_44[0]": ("sign_here", "phone", "Phone no.", "text"),
        "f2_45[0]": ("sign_here", "email", "Email address", "text"),
        "f2_46[0]": ("paid_preparer", "name", "Preparer's name", "text"),
        "f2_47[0]": ("paid_preparer", "ptin", "PTIN", "identifier"),
        "c2_18[0]": ("paid_preparer", "self_employed", "Self-employed", "checkbox"),
        "f2_48[0]": ("paid_preparer", "firm_name", "Firm's name", "text"),
        "f2_49[0]": ("paid_preparer", "phone", "Phone no.", "text"),
        "f2_50[0]": ("paid_preparer", "firm_address", "Firm's address", "text"),
        "f2_51[0]": ("paid_preparer", "firm_ein", "Firm's EIN", "identifier"),
    }
    if leaf in section_specs:
        section, token, label, role = section_specs[leaf]
        terminal = "option" if role == "checkbox" else "control"
        return _campaign_control(
            item,
            [{"kind": "section", "token": section}, {"kind": terminal, "token": token}],
            section.replace("_", " ").title(),
            label,
            role,
        )
    return None


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
    # The 2021+ Form 1099-DIV revision numbers its FATCA checkbox as Box 11; on
    # 1099-INT and 1099-B the FATCA checkbox is printed without a box number.
    fatca_box = "11" if document_id == "form_1099_div_2025" else None
    common = {
        (2, 0, 310): (fatca_box, "fatca_filing_requirement", "FATCA filing requirement"),
        (3, 0, 310): (fatca_box, "fatca_filing_requirement", "FATCA filing requirement"),
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
