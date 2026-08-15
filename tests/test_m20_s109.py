"""M20-S109 regressions for role-aware micro operand validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tax_graph.extract.assembly import assemble_formula_plan
from tax_graph.extract.models import SourceDocumentInput
from tax_graph.extract.micro import MicroExtractionError, formula_micro_schema, validate_formula_plan
from tax_graph.extract.outline import CandidateSpan, OutlineNode
from tax_graph.operation_registry import assign_operation_roles, operation_repeatable_roles


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.m20


def _span() -> CandidateSpan:
    return CandidateSpan(
        "span_s109",
        "form_6251_2025",
        "source",
        "page 1",
        "Printed formula evidence for S109.",
    )


def _validate(operation: str, source_lines: list[object]) -> None:
    validate_formula_plan(
        {
            "operation": operation,
            "source_lines": source_lines,
            "quote": "Printed formula evidence for S109.",
        },
        spans=[_span()],
        root=ROOT,
    )


def _constant(value: int | float, role: str, branch: str) -> dict[str, object]:
    return {
        "constant": value,
        "role": role,
        "branch": branch,
        "value_type": "percentage" if isinstance(value, float) and value < 1 else "currency",
    }


def test_formula_schema_separates_operand_role_from_branch_selection() -> None:
    schema = formula_micro_schema(root=ROOT)
    alternatives = schema["properties"]["source_lines"]["items"]["anyOf"]
    same_form_schema = next(
        item
        for item in alternatives
        if "line" in item.get("properties", {}) and "form" not in item.get("properties", {})
    )
    cross_form_schema = next(item for item in alternatives if "form" in item.get("properties", {}))
    constant_schema = next(item for item in alternatives if "constant" in item.get("properties", {}))

    for item in (same_form_schema, cross_form_schema, constant_schema):
        assert "role" in item["required"]
        assert "branch" in item["required"]
        assert item["properties"]["role"]["type"] == ["string", "null"]
        assert item["properties"]["branch"]["type"] == ["string", "null"]

    edge_schema = json.loads((ROOT / "schemas" / "edge.schema.json").read_text(encoding="ascii"))
    assert edge_schema["properties"]["branch"]["type"] == "string"


def test_same_form_role_bearing_line_resolves_in_current_document() -> None:
    document = SourceDocumentInput(
        document_id="form_1040_2025",
        kind="tax_form",
        year="2025",
        url="https://example.test/form-1040.pdf",
        text="",
        text_path=Path("unused-form-1040.txt"),
    )
    node = OutlineNode("line_11a", "line", "formula", line_anchor="11a")
    span = _span()
    plan = {
        "operation": "SUBTRACT",
        "source_lines": [
            {"line": "9", "role": "minuend", "branch": None},
            {"line": "10", "role": "subtrahend", "branch": None},
        ],
        "quote": span.text,
    }

    _validate("SUBTRACT", plan["source_lines"])
    batch = assemble_formula_plan(
        document,
        node,
        plan,
        [span],
        root=ROOT,
        line_index={
            ("form_1040_2025", "9"): "form_1040_2025_line_9",
            ("form_1040_2025", "10"): "form_1040_2025_line_10",
        },
    )
    edges = [item.data for item in batch.items("edges")]
    assert [(edge["source"], edge["role"]) for edge in edges] == [
        ("form_1040_2025_line_9", "minuend"),
        ("form_1040_2025_line_10", "subtrahend"),
    ]


def test_threshold_conditional_accepts_repeated_role_with_distinct_branches() -> None:
    source_lines = [
        "17",
        _constant(239100, "threshold", "default"),
        _constant(119550, "threshold", "married filing separately"),
        _constant(0.26, "when_true", "default"),
        _constant(0.26, "when_true", "married filing separately"),
        _constant(0.28, "when_false", "default"),
        _constant(0.28, "when_false", "married filing separately"),
    ]

    _validate("IF_ELSE", source_lines)
    assert operation_repeatable_roles("IF_ELSE") == ("threshold", "when_true", "when_false")


def test_threshold_conditional_can_have_repeated_false_branch_operands() -> None:
    source_lines = [
        "12",
        _constant(239100, "threshold", "default"),
        _constant(119550, "threshold", "married filing separately"),
        _constant(0.26, "when_true", "default"),
        _constant(0.26, "when_true", "married filing separately"),
        _constant(0.28, "when_false", "default"),
        _constant(0.28, "when_false", "married filing separately"),
        _constant(4782, "when_false", "default"),
        _constant(2391, "when_false", "married filing separately"),
    ]

    _validate("IF_ELSE", source_lines)


def test_bracket_table_accepts_repeated_brackets_role() -> None:
    source_lines = ["7"] + [
        _constant(index / 100, "brackets", f"band_{index}")
        for index in range(47)
    ]

    _validate("LOOKUP_BRACKET", source_lines)
    assert assign_operation_roles("LOOKUP_BRACKET", [None] + ["brackets"] * 47) == (
        ("amount",) + ("brackets",) * 47
    )


def test_two_branch_if_else_accepts_cross_form_inputs() -> None:
    _validate(
        "IF_ELSE",
        [
            {
                "form": "form_2441",
                "line": "XFORM",
                "role": "when_true",
                "branch": "married filing jointly",
            },
            {
                "form": "form_2441",
                "line": "4",
                "role": "when_false",
                "branch": "default",
            },
        ],
    )


def test_unknown_or_missing_roles_remain_findings() -> None:
    with pytest.raises(MicroExtractionError, match="operand roles"):
        _validate(
            "IF_ELSE",
            [
                "17",
                _constant(239100, "threshold", "default"),
                _constant(0.26, "when_true", "default"),
            ],
        )

    with pytest.raises(MicroExtractionError, match="operand roles"):
        _validate(
            "IF_ELSE",
            [
                {"constant": 1, "role": "unknown", "branch": None, "value_type": "integer"},
                {"constant": 2, "role": "threshold", "branch": None, "value_type": "integer"},
                {"constant": 3, "role": "when_true", "branch": None, "value_type": "integer"},
                {"constant": 4, "role": "when_false", "branch": None, "value_type": "integer"},
            ],
        )


def test_fixed_arity_guard_is_not_widened() -> None:
    with pytest.raises(MicroExtractionError, match="MULTIPLY requires exactly 2"):
        _validate("MULTIPLY", ["2"])


def test_assembly_keeps_branch_separate_from_edge_role() -> None:
    document = SourceDocumentInput(
        document_id="form_6251_2025",
        kind="tax_form",
        year="2025",
        url="https://example.test/form-6251.pdf",
        text="",
        text_path=Path("unused-form-6251.txt"),
    )
    node = OutlineNode("line_18", "line", "formula", line_anchor="18")
    span = _span()
    plan = {
        "operation": "IF_ELSE",
        "source_lines": [
            "17",
            _constant(239100, "threshold", "default"),
            _constant(0.26, "when_true", "default"),
            _constant(0.28, "when_false", "default"),
        ],
        "quote": span.text,
    }

    batch = assemble_formula_plan(document, node, plan, [span], root=ROOT)
    edges = [item.data for item in batch.items("edges")]
    assert [(edge["role"], edge.get("branch")) for edge in edges] == [
        ("condition", None),
        ("threshold", "default"),
        ("when_true", "default"),
        ("when_false", "default"),
    ]
