"""Scenario model and renderers for M6 oracle comparisons."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


SUPPORTED_FILING_STATUSES = {"single": "Single"}


@dataclass(frozen=True)
class CapitalGainScenario:
    """A fenced single-lot capital-gains scenario."""

    scenario_id: str
    tax_year: str
    filing_status: str
    description: str
    date_acquired: str
    date_sold: str
    proceeds: int | float
    cost: int | float
    adjustment: int | float = 0

    @property
    def gain_loss(self) -> int | float:
        """Return proceeds minus cost plus adjustment."""

        return _clean_number(self.proceeds) - _clean_number(self.cost) + _clean_number(self.adjustment)


def render_tax_graph_facts_document(scenario: CapitalGainScenario) -> dict[str, Any]:
    """Render a scenario to Tax Graph taxpayer facts."""

    _require_supported_tax_graph_scenario(scenario)
    return {
        "tax_year": int(scenario.tax_year),
        "filing_status": scenario.filing_status,
        "scenario_id": scenario.scenario_id,
        "facts": [
            {
                "node_id": "schedule_d_2025_line_7_net_st",
                "value": 0,
                "source": {
                    "document_label": f"Generated scenario {scenario.scenario_id}",
                    "extracted_by": "m6_scenario_renderer",
                },
            },
        ],
        "tables": [
            {
                "table_id": "form_8949_2025_part_ii_line_1",
                "rows": [
                    {
                        "row_key": "lot_1",
                        "columns": {
                            "d": _clean_number(scenario.proceeds),
                            "e": _clean_number(scenario.cost),
                            "g": _clean_number(scenario.adjustment),
                        },
                        "source": _source(scenario),
                    }
                ],
            }
        ],
    }


def render_tax_graph_facts_yaml(scenario: CapitalGainScenario) -> str:
    """Render Tax Graph facts YAML for a scenario."""

    return yaml.safe_dump(
        render_tax_graph_facts_document(scenario),
        sort_keys=False,
        allow_unicode=False,
    )


def render_ots_input_text(
    scenario: CapitalGainScenario,
    *,
    spreadsheet_name: str | None = None,
    template_text: str | None = None,
) -> str:
    """Render the OTS 1040 input text that points at an 8949 CSV."""

    _require_supported_ots_scenario(scenario)
    csv_name = spreadsheet_name or f"{_safe_id(scenario.scenario_id)}_f8949.csv"
    status = SUPPORTED_FILING_STATUSES[scenario.filing_status]
    template = template_text or _fallback_ots_template(scenario.tax_year)
    rendered = _fill_ots_template(
        template,
        {
            "Title": f"US Federal 1040 Tax Form - {scenario.tax_year} - Tax Graph scenario {scenario.scenario_id}",
            "Status": status,
            "You_65+Over?": "N",
            "You_Blind?": "N",
            "Spouse_65+Over?": "N",
            "Spouse_Blind?": "N",
            "Dependents": "0",
            "CkHomeInUS": "Y",
            "VirtCurr?": "N",
            "CkSepLivedApart": "N",
            "f8949_spreadsheet-A/D": csv_name,
        },
    )
    return rendered if rendered.endswith("\n") else f"{rendered}\n"


def render_ots_8949_csv(scenario: CapitalGainScenario) -> str:
    """Render the OTS Form 8949 spreadsheet CSV for one lot."""

    _require_supported_ots_scenario(scenario)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "Description",
            "Date_Acquired",
            "Date_Sold",
            "Proceeds",
            "Cost",
            "Code",
            "Adjustment",
        ]
    )
    writer.writerow(
        [
            scenario.description,
            scenario.date_acquired,
            scenario.date_sold,
            _format_number(scenario.proceeds),
            _format_number(scenario.cost),
            "",
            _format_adjustment(scenario.adjustment),
        ]
    )
    return buffer.getvalue()


def write_ots_input_bundle(
    scenario: CapitalGainScenario,
    output_dir: str | Path,
    *,
    template_path: str | Path | None = None,
) -> dict[str, Path]:
    """Write OTS input text and 8949 CSV for a scenario."""

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stem = _safe_id(scenario.scenario_id)
    csv_path = directory / f"{stem}_f8949.csv"
    input_path = directory / f"{stem}.txt"
    template_text = Path(template_path).read_text(encoding="utf-8") if template_path else None
    csv_path.write_text(render_ots_8949_csv(scenario), encoding="utf-8", newline="\n")
    input_path.write_text(
        render_ots_input_text(scenario, spreadsheet_name=csv_path.name, template_text=template_text),
        encoding="utf-8",
        newline="\n",
    )
    return {"input": input_path, "csv": csv_path}


def _require_supported_tax_graph_scenario(scenario: CapitalGainScenario) -> None:
    _require_supported_ots_scenario(scenario)
    if _clean_number(scenario.adjustment) != 0:
        raise ValueError("Tax Graph v0 capital-gains slice does not model 8949 adjustments")


def _require_supported_ots_scenario(scenario: CapitalGainScenario) -> None:
    if str(scenario.tax_year) != "2025":
        raise ValueError(f"unsupported tax year for M6 scenario: {scenario.tax_year}")
    if scenario.filing_status not in SUPPORTED_FILING_STATUSES:
        raise ValueError(f"unsupported filing status for M6 scenario: {scenario.filing_status}")


def _source(scenario: CapitalGainScenario) -> dict[str, str]:
    return {
        "document_label": f"Generated broker 1099-B for scenario {scenario.scenario_id}",
        "extracted_by": "m6_scenario_renderer",
    }


def _clean_number(value: int | float) -> int | float:
    number = float(value)
    return int(number) if number.is_integer() else number


def _format_number(value: int | float) -> str:
    number = _clean_number(value)
    return str(number)


def _format_adjustment(value: int | float) -> str:
    return "" if _clean_number(value) == 0 else _format_number(value)


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return cleaned.strip("_") or "scenario"


def _fallback_ots_template(tax_year: str) -> str:
    return "\n".join(
        [
            f"Title:  US Federal 1040 Tax Form - {tax_year}",
            "Status        Single",
            "You_65+Over?  N",
            "You_Blind?  N",
            "Spouse_65+Over?  N",
            "Spouse_Blind?  N",
            "Dependents  0",
            "CkHomeInUS  Y",
            "VirtCurr?  N",
            "CkSepLivedApart  N",
            "f8949_spreadsheet-A/D:",
            "",
        ]
    )


def _fill_ots_template(template: str, values: dict[str, str]) -> str:
    rendered = template.replace("\r\n", "\n").replace("\r", "\n")
    colon_labels = {"Title", "f8949_spreadsheet-A/D"}
    for label, value in values.items():
        rendered = _replace_template_value(
            rendered,
            label=label,
            value=value,
            use_colon=label in colon_labels,
        )
    return rendered


def _replace_template_value(text: str, *, label: str, value: str, use_colon: bool) -> str:
    pattern = re.compile(
        rf"^(?P<indent>\s*){re.escape(label)}(?P<colon>:?)(?P<body>[^\n]*)$",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        raise ValueError(f"OTS template is missing required field {label}")

    def replace(found: re.Match[str]) -> str:
        comment = _inline_comment(found.group("body"))
        colon = ":" if use_colon else ""
        return f"{found.group('indent')}{label}{colon}  {value}{comment}"

    return pattern.sub(replace, text, count=1)


def _inline_comment(text: str) -> str:
    comment_start = text.find("{")
    if comment_start < 0:
        return ""
    return f"  {text[comment_start:].strip()}"
