"""Focused M16-S4 tests for fail-closed structural validators."""

from __future__ import annotations

from tax_graph.output.structural_checks import check_document_structure


def _schedule_2_fragment() -> dict:
    fields = [
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
            "field_name": "form1[0].Page1[0].f1_15[0]",
            "line_anchor": "1",
            "page": 1,
            "y0": 468.0,
        },
    ]
    return {
        "fields": fields,
        "field_map": {
            "mappings": [
                {
                    "field_name": fields[3]["field_name"],
                    "node_id": "schedule_2_2025_part_i_line_1",
                    "address_id": "2025/document=schedule_2/line=1/control=amount",
                }
            ],
            "field_dispositions": [
                {
                    "field_name": fields[0]["field_name"],
                    "population_policy": "unsupported",
                },
                {
                    "field_name": fields[1]["field_name"],
                    "population_policy": "unsupported",
                },
                {
                    "field_name": fields[2]["field_name"],
                    "population_policy": "unsupported",
                },
            ],
        },
        "nodes": [
            {
                "node_id": "schedule_2_2025_part_i_line_1",
                "label": "Line 1: Additions to tax:",
                "node_type": "form_line",
                "value_type": "currency",
            },
            {
                "node_id": "schedule_2_2025_part_i_line_3",
                "label": "Line 3: Add lines 1z and 2.",
                "node_type": "form_line",
                "value_type": "currency",
            }
        ],
        "widget_bindings": [
            {
                "field_name": fields[0]["field_name"],
                "address_id": "2025/document=schedule_2/line=1z/control=amount",
            },
            {
                "field_name": fields[1]["field_name"],
                "address_id": "2025/document=schedule_2/line=1z/control=amount",
            },
            {
                "field_name": fields[2]["field_name"],
                "address_id": "2025/document=schedule_2/line=1/control=checkbox",
            },
            {
                "field_name": fields[3]["field_name"],
                "address_id": "2025/document=schedule_2/line=1/control=amount",
            },
        ],
        "node_bindings": [
            {
                "node_id": "schedule_2_2025_part_i_line_1",
                "address_id": "2025/document=schedule_2/line=1/control=amount",
            }
        ],
        "rendered_text": "\n".join(
            (
                "- 1: Additions to tax:",
                "- 3: Add lines 1z and 2.",
                "- 4: Self-employment tax. Check if any exemption:",
                "- z: Add lines 1a through 1y 1z",
            )
        ),
    }


def _run(fragment: dict, **overrides):
    values = {key: value for key, value in fragment.items() if key != "field_map"}
    values["field_map"] = fragment["field_map"]
    values.update(overrides)
    return check_document_structure("schedule_2_2025", **values)


def test_schedule_2_flags_heading_total_and_triangle_defects() -> None:
    findings = _run(_schedule_2_fragment())

    heading = [item for item in findings if item.validator == "heading_integrity"]
    totals = [item for item in findings if item.validator == "total_presence"]
    triangle = [item for item in findings if item.validator == "line_identity_triangle"]

    assert [item.control for item in heading] == ["form1[0].Page1[0].f1_15[0]"]
    assert [item.control for item in totals] == ["line=1z"]
    assert {item.control for item in triangle} >= {
        "form1[0].Page1[0].f1_13[0]",
        "form1[0].Page1[0].Line4_ReadOrder[0].c1_3[0]",
        "form1[0].Page1[0].f1_15[0]",
    }
    assert all(item.document == "schedule_2_2025" for item in findings)
    assert all(item.evidence for item in findings)


def test_line_coverage_accepts_one_node_or_explicit_out_of_profile() -> None:
    fragment = _schedule_2_fragment()
    fragment["field_map"]["field_dispositions"] = []
    fragment["field_map"]["mappings"] = [
        {
            "field_name": fragment["fields"][0]["field_name"],
            "node_id": "schedule_2_2025_part_i_line_1z",
        },
        {
            "field_name": fragment["fields"][1]["field_name"],
            "node_id": "schedule_2_2025_part_i_line_3",
        },
    ]
    findings = _run(fragment, total_lines=(), out_of_profile=("4",))

    assert not [item for item in findings if item.validator == "line_coverage"]


def test_findings_are_serializable_review_queue_records() -> None:
    finding = _run(_schedule_2_fragment())[0]
    record = finding.as_record()

    assert set(record) == {"document", "control", "validator", "observed", "expected", "evidence"}
    assert isinstance(record["evidence"], list)
