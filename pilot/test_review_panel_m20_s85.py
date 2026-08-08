"""M20-S85 review-panel coverage for conditional tree presentation."""

from __future__ import annotations

from review_panel import _math_text, _tree_html


def _leaf(line: str) -> dict[str, object]:
    return {"kind": "reference", "line": line}


def _if_else(*, comparison: str | None = "le", checkbox: bool = False) -> dict[str, object]:
    tree: dict[str, object] = {
        "kind": "operation",
        "operation": "IF_ELSE",
        "comparison": comparison,
        "operands": [
            {"role": "condition", "tree": _leaf("22" if checkbox else "17")},
            {"role": "threshold", "tree": {"kind": "constant", "value": 239100}},
            {"role": "when_true", "tree": {"kind": "constant", "value": 26000}},
            {"role": "when_false", "tree": {"kind": "constant", "value": 79218}},
        ],
    }
    if checkbox:
        tree["condition_control_role"] = "checkbox"
    if comparison is None:
        tree["comparison_finding"] = "missing IF_ELSE comparison at rule.parameters.comparison"
    return tree


def test_if_else_uses_explicit_comparator_phrase_and_child_precedes_label() -> None:
    html = _tree_html(_if_else())

    assert "line 17 &lt;= threshold" in html
    assert html.index('class="tree-leaf"') < html.index('class="tree-role">line 17 &lt;= threshold</span>')


def test_checkbox_condition_uses_filer_language() -> None:
    tree = _if_else(checkbox=True)

    assert "Line 22 checked?" in _math_text(tree)
    assert "Line 22 checked?" in _tree_html(tree)


def test_missing_comparator_is_visible_in_tree_and_math() -> None:
    tree = _if_else(comparison=None)

    html = _tree_html(tree)
    assert "missing IF_ELSE comparison at rule.parameters.comparison" in html
    assert "comparison missing" in _math_text(tree)


def test_long_math_wraps_only_between_operands() -> None:
    tree = {
        "kind": "operation",
        "operation": "SUM",
        "operands": [
            {"role": "addend", "tree": {"kind": "reference", "label": f"operand_{index}_with_a_stable_token"}}
            for index in range(12)
        ],
    }

    rendered = _math_text(tree)
    lines = rendered.splitlines()

    assert rendered.startswith("SUM(\n")
    assert all(len(line) <= 120 for line in lines)
    assert all("operand_" in line or line.strip() in {"SUM(", ")"} for line in lines)


def test_nested_operation_edges_are_indented_by_the_panel_contract() -> None:
    tree = {
        "kind": "operation",
        "operation": "SUM",
        "operands": [
            {
                "role": "addend",
                "tree": {
                    "kind": "operation",
                    "operation": "MULTIPLY",
                    "operands": [
                        {"role": "multiplicand", "tree": _leaf("1")},
                        {"role": "multiplier", "tree": _leaf("2")},
                    ],
                },
            }
        ],
    }

    html = _tree_html(tree)

    assert 'class="tree-edge tree-edge-operation"' in html
