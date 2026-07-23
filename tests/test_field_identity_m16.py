"""Focused M16-S3 tests for the structure-first field identity resolver."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tax_graph.output.field_identity import (
    compare_identities,
    parse_field_structure,
    resolve_field,
    resolve_fields,
)


ROOT = Path(__file__).resolve().parents[1]
RAW_FIELDS = ROOT / ".cache/raw/2025/schedule_2_2025.fields.json"


def _schedule_2_part_i_fields() -> list[dict[str, object]]:
    return [
        {
            "field_name": "form1[0].Page1[0].f1_11[0]",
            "line_anchor": "z",
            "page": 1,
            "y0": 390.0,
        },
        {
            "field_name": "form1[0].Page1[0].f1_13[0]",
            "line_anchor": "3",
            "page": 1,
            "y0": 426.0,
        },
        {
            "field_name": "form1[0].Page1[0].Line4_ReadOrder[0].c1_3[0]",
            "line_anchor": "1",
            "page": 1,
            "y0": 470.0,
            "field_type": "CheckBox",
        },
        {
            "field_name": "form1[0].Page1[0].Line4_ReadOrder[0].f1_14[0]",
            "line_anchor": "1",
            "page": 1,
            "y0": 468.0,
        },
        {
            "field_name": "form1[0].Page1[0].f1_15[0]",
            "line_anchor": "1",
            "page": 1,
            "y0": 468.0,
        },
    ]


def test_schedule_2_part_i_structure_resolves_target_identities() -> None:
    rendered = "\n".join(
        (
            "- 1: Additions to tax:",
            "- 3: Add lines 1z and 2.",
            "- 4: Self-employment tax. Check if any exemption from (see instructions):",
            "- 1z: Add lines 1a through 1y",
        )
    )
    results = {item.field_name: item for item in resolve_fields(_schedule_2_part_i_fields(), rendered_text=rendered)}

    assert results["form1[0].Page1[0].f1_15[0]"].identity == ("4", "amount")
    assert results["form1[0].Page1[0].f1_13[0]"].identity == ("3", "amount")
    assert results["form1[0].Page1[0].f1_11[0]"].identity == ("1z", "amount")
    assert results["form1[0].Page1[0].Line4_ReadOrder[0].c1_3[0]"].identity == ("4", "checkbox")
    assert "same-row qualified wrapper" in results["form1[0].Page1[0].f1_15[0]"].evidence


def test_structure_parser_keeps_table_and_box_wrappers() -> None:
    parsed = parse_field_structure(
        "topmostSubform[0].CopyA[0].Table_Line1_Part1[0].Row2[0].Box1d_ReadOrder[0].f1_19[0]"
    )

    assert parsed.explicit_line == "1"
    assert parsed.box == "1d"
    assert parsed.table == "Table_Line1_Part1"
    assert parsed.copy == "CopyA"


def test_resolver_does_not_guess_unstructured_identity() -> None:
    result = resolve_field({"field_name": "form1[0].mystery[0].value[0]", "page": 1, "y0": 10.0})

    assert result.status == "unresolved"
    assert result.identity == (None, None)
    assert "insufficient non-guessing evidence" in result.evidence


def test_caption_adjacency_supplies_role_without_label_mining() -> None:
    result = resolve_field(
        {
            "field_name": "form1[0].Page1[0].Line2_ReadOrder[0].f1_02[0]",
            "page": 1,
            "y0": 20.0,
        },
        rendered_text=["- 2: Date of original divorce or separation agreement (see instructions):"],
    )

    assert result.identity == ("2", "date")
    assert result.status == "resolved"


def test_corpus_comparison_preserves_disagreements_and_unresolved() -> None:
    fields = _schedule_2_part_i_fields()[:3]
    derived = resolve_fields(fields)
    comparison = compare_identities(
        "schedule_2_2025",
        derived,
        {
            fields[0]["field_name"]: ("1z", "amount"),
            fields[1]["field_name"]: ("4", "amount"),
        },
    )

    assert comparison.total == 3
    assert comparison.agreement == 1
    assert comparison.disagreement == 1
    assert comparison.unresolved == 1
    assert any("disagreement" in item for item in comparison.examples)


@pytest.mark.skipif(
    not RAW_FIELDS.is_file(),
    reason="official raw AcroForm cache is absent in a fresh checkout",
)
def test_schedule_2_raw_cache_reproduces_target_fields() -> None:
    payload = json.loads(RAW_FIELDS.read_text(encoding="utf-8"))
    results = {item.field_name: item for item in resolve_fields(payload["fields"])}

    assert results["form1[0].Page1[0].f1_15[0]"].line == "4"
    assert results["form1[0].Page1[0].f1_13[0]"].line == "3"
    assert results["form1[0].Page1[0].f1_11[0]"].line == "1z"
    assert results["form1[0].Page1[0].Line4_ReadOrder[0].c1_3[0]"].line == "4"
