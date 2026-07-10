"""Emit a user-runnable OpenTaxSolver second-opinion sidecar."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

from tax_graph.oracles.scenario import CapitalGainLot, CapitalGainScenario, write_ots_input_bundle


README_TEXT = """# OpenTaxSolver second-opinion input

This directory contains an OpenTaxSolver US 1040 input and its Form 8949 CSV.
Install the pinned OTS release described in the Tax Graph configuration, then run:

    taxsolve_US_1040_2025 <input-file.txt>

Broker descriptions and dates are deterministic OTS-only placeholders because the
Tax Graph facts contract retains amounts and holding-period tables, not those display
fields. Review the files before using them outside this second-opinion calculation.
"""


def scenario_from_facts_document(facts_document: Mapping[str, Any], *, root: str | Path) -> CapitalGainScenario:
    """Translate one supported return facts document into the existing OTS model."""
    values = {item["node_id"]: item.get("value", 0) for item in facts_document.get("facts", [])}
    lots: list[CapitalGainLot] = []
    for table in facts_document.get("tables", []) or []:
        table_id = str(table.get("table_id", ""))
        if table_id == "form_8949_2025_part_i_line_1":
            holding_period = "short_term"
            acquired = "01/15/2025"
        elif table_id == "form_8949_2025_part_ii_line_1":
            holding_period = "long_term"
            acquired = "01/15/2024"
        else:
            continue
        for index, row in enumerate(table.get("rows", []) or [], start=1):
            columns = row.get("columns") or {}
            row_key = str(row.get("row_key") or f"lot_{index}")
            lots.append(
                CapitalGainLot(
                    row_key=row_key,
                    description=f"Tax Graph row {row_key}",
                    date_acquired=acquired,
                    date_sold="06/01/2025",
                    proceeds=columns.get("d", 0),
                    cost=columns.get("e", 0),
                    adjustment=columns.get("g", 0),
                    holding_period=holding_period,
                )
            )
    if not lots:
        raise ValueError("OTS sidecar export currently requires at least one Form 8949 table row")
    supplemental = _supplemental_ots_inputs(values, root)
    first = lots[0]
    return CapitalGainScenario(
        scenario_id=str(facts_document.get("return_id") or facts_document.get("scenario_id") or "tax_graph_return"),
        tax_year=str(facts_document.get("tax_year") or 2025),
        filing_status=str(facts_document.get("filing_status")),
        description=first.description,
        date_acquired=first.date_acquired,
        date_sold=first.date_sold,
        proceeds=first.proceeds,
        cost=first.cost,
        adjustment=first.adjustment,
        holding_period=first.holding_period,
        wages=values.get("form_1040_2025_root_line_1a", 0),
        taxable_interest=values.get("schedule_b_2025_root_line_4", 0),
        qualified_dividends=values.get("form_1040_2025_root_line_3a", 0),
        ordinary_dividends=values.get("schedule_b_2025_root_line_6", 0),
        deduction_method=values.get("form_1040_2025_deduction_method", "standard"),
        itemized_deductions=values.get("schedule_a_2025_root_line_17", 0),
        lots=tuple(lots),
        extra_ots_inputs=supplemental,
    )


def write_ots_sidecar(
    facts_document: Mapping[str, Any],
    output_dir: str | Path,
    *,
    root: str | Path,
    template_path: str | Path | None = None,
) -> dict[str, Path]:
    """Write the existing OTS bundle plus concise user instructions."""
    directory = Path(output_dir)
    paths = write_ots_input_bundle(
        scenario_from_facts_document(facts_document, root=root),
        directory,
        template_path=template_path,
    )
    readme = directory / "README.md"
    readme.write_text(README_TEXT, encoding="utf-8", newline="\n")
    return {**paths, "readme": readme}


def _supplemental_ots_inputs(values: Mapping[str, Any], root: str | Path) -> dict[str, Any]:
    domain_path = Path(root) / "oracles" / "domain_2025.yaml"
    if not domain_path.exists():
        return {}
    domain = yaml.safe_load(domain_path.read_text(encoding="utf-8")) or {}
    return {
        item["ots_input"]: values[item["node_id"]]
        for item in domain.get("supplemental_inputs", [])
        if item.get("node_id") in values
    }
