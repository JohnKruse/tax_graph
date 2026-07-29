"""Golden tests for the M15 Step 5 semantic formatter set."""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench.manifest import build_manifest
from workbench.schema import validate_review_expression
from workbench.semantics import (
    SemanticFormatError,
    format_computation,
    format_scope_semantics,
)


ROOT = Path(__file__).resolve().parents[1]


def _node(node_id: str, label: str, *, node_type: str = "computed", document_id: str = "form_1040_2025") -> dict[str, object]:
    return {
        "node_id": node_id,
        "document_id": document_id,
        "label": label,
        "node_type": node_type,
    }


def _edge(source: str, role: str) -> dict[str, str]:
    return {"source": source, "role": role}


def _format(operation: str, roles: list[tuple[str, str]], *, parameters: dict[str, str] | None = None):
    nodes = {
        node_id: _node(node_id, label, node_type="parameter" if "rate" in node_id else "computed")
        for node_id, label in (
            ("amount", "Taxable amount"),
            ("other", "Other amount"),
            ("rate", "15 percent cited rate"),
            ("status", "Filing status"),
            ("brackets", "2025 tax brackets"),
            ("yes", "Worksheet result"),
            ("no", "Regular tax"),
        )
    }
    return format_computation(
        target=_node("target", "Target"),
        rule={"operation": operation, "parameters": parameters or {}},
        operand_edges=[_edge(source, role) for source, role in roles],
        nodes=nodes,
    )


@pytest.mark.m15
@pytest.mark.parametrize(
    ("operation", "word"),
    [("MIN", "smaller"), ("MAX", "larger")],
)
def test_min_max_formatters(operation: str, word: str) -> None:
    formatted = _format(operation, [("amount", "candidate"), ("other", "candidate")])

    assert formatted.summary == f"Use the {word} of Taxable amount and Other amount"
    assert formatted.semantic_class == "branch"
    validate_review_expression(formatted.expression)


@pytest.mark.m15
def test_multiply_names_the_parameter_and_bracket_names_the_resource() -> None:
    multiply = _format("MULTIPLY", [("amount", "multiplicand"), ("rate", "multiplier")])
    bracket = _format("LOOKUP_BRACKET", [("amount", "amount"), ("brackets", "brackets")])

    assert multiply.summary == "Multiply Taxable amount by 15 percent cited rate"
    assert multiply.expression["parameter_ref"] == "rate"
    assert bracket.summary == "Calculate tax on Taxable amount using 2025 tax brackets"
    assert bracket.expression["lookup_ref"] == "brackets"
    validate_review_expression(multiply.expression)
    validate_review_expression(bracket.expression)


@pytest.mark.m15
def test_lookup_table_formats_resource_and_keyed_selection() -> None:
    resource = _format(
        "LOOKUP_TABLE",
        [("amount", "amount"), ("status", "status")],
        parameters={"resource": "tax_table"},
    )
    keyed = _format("LOOKUP_TABLE", [("status", "key"), ("amount", "single"), ("other", "joint")])

    assert resource.summary == "Look up tax for Taxable amount using Filing status"
    assert resource.expression["lookup_ref"] == "tax_table"
    assert keyed.summary == "Select the value matching Filing status"
    assert keyed.expression["lookup_ref"] == "status"
    validate_review_expression(resource.expression)
    validate_review_expression(keyed.expression)


@pytest.mark.m15
def test_if_else_formatter_names_condition_branches_and_escape() -> None:
    formatted = _format(
        "IF_ELSE",
        [("amount", "condition"), ("other", "threshold"), ("yes", "when_true"), ("no", "when_false")],
        parameters={"comparison": "lt"},
    )

    assert formatted.summary == (
        "If Taxable amount is less than Other amount, use Worksheet result; otherwise use Regular tax"
    )
    assert formatted.expression["branches"][0]["then"]["ref"]["object_id"] == "yes"
    assert formatted.expression["else"]["ref"]["object_id"] == "no"
    validate_review_expression(formatted.expression)


@pytest.mark.m15
def test_table_frontier_gap_parameter_input_and_imported_classes() -> None:
    table = {
        "table_id": "table_a",
        "line_anchor": "Form 8949 Part I line 1",
    }
    graph_index = {
        ("table", "table_a"): table,
        ("node", "parameter_a"): {
            **_node("parameter_a", "Capital loss limit", node_type="parameter"),
            "constant_value": 3000,
            "citation_refs": ["cite_limit"],
        },
        ("node", "input_a"): _node("input_a", "Filing status", node_type="fact"),
        ("node", "imported_a"): _node(
            "imported_a",
            "1099-B proceeds",
            node_type="box",
            document_id="form_1099b_2025",
        ),
    }
    cases = [
        ({"object_type": "table", "object_id": "table_a"}, "repeatable_table"),
        ({"object_type": "frontier", "object_id": "frontier_a"}, "frontier"),
        ({"object_type": "node", "object_id": "gap_a", "role": "excluded"}, "review_gap"),
        ({"object_type": "node", "object_id": "parameter_a"}, "parameter"),
        ({"object_type": "node", "object_id": "input_a"}, "input"),
        ({"object_type": "node", "object_id": "imported_a"}, "imported"),
    ]

    for scope_ref, expected_kind in cases:
        formatted = format_scope_semantics(scope_ref, graph_index)
        assert formatted is not None
        assert formatted.expression["kind"] == expected_kind
        validate_review_expression(formatted.expression)


@pytest.mark.m15
def test_unknown_operation_fails_instead_of_exposing_raw_json() -> None:
    with pytest.raises(SemanticFormatError, match="no formatter for operation DIVIDE"):
        _format("DIVIDE", [("amount", "numerator"), ("other", "denominator")])


@pytest.mark.m15
@pytest.mark.skipif(
    not (Path(__file__).resolve().parents[1] / "graph" / "2025" / "_drafts").exists(),
    reason="live review drafts are required: fresh checkouts (CI) carry no _drafts",
)
def test_live_derived_manifest_uses_review_expressions_without_raw_fallback() -> None:
    manifest = build_manifest(ROOT, 2025)
    units = [unit for entry in manifest["entries"] for unit in entry["units"]]
    kinds = {unit["expression"]["kind"] for unit in units}

    # The derived manifest contains physical cells only; graph operations without a
    # physical cell are covered by the formatter tests above, not projected here.
    assert {"lookup_table", "if_else", "max"} <= kinds
    assert {"input", "review_gap"} <= kinds
    assert all(unit["summary"] and "{" not in unit["summary"] for unit in units)
    assert all("use line 22; otherwise use line 22" not in unit["summary"] for unit in units)
    assert all("d_minus_e" not in unit["summary"] for unit in units)
    for unit in units:
        expression_citations = set(unit["expression"].get("citation_refs", []))
        assert expression_citations <= set(unit.get("citation_refs", []))
