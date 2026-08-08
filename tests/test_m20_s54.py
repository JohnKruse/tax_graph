"""M20-S54 tests for lookup completeness and truthful selector outcomes."""

from __future__ import annotations

import pytest

from tax_graph.extract.cells import (
    CellRecord,
    expression_schema,
    validate_expression_tree,
    validate_cell_output,
    validate_lookup_table_completeness,
)


pytestmark = pytest.mark.m20


TABLE_TEXT = (
    "$0-15,000 .35 $25,000-27,000 .29 $37,000-39,000 .23\n"
    "15,000-17,000 .34 27,000-29,000 .28 39,000-41,000 .22\n"
    "17,000-19,000 .33 29,000-31,000 .27 41,000-43,000 .21\n"
    "19,000-21,000 .32 31,000-33,000 .26 43,000-No limit .20\n"
    "21,000-23,000 .31 33,000-35,000 .25\n"
    "23,000-25,000 .30 35,000-37,000 .24"
)

ALL_BANDS = [
    "band_0_15000",
    "band_15000_17000",
    "band_17000_19000",
    "band_19000_21000",
    "band_21000_23000",
    "band_23000_25000",
    "band_25000_27000",
    "band_27000_29000",
    "band_29000_31000",
    "band_31000_33000",
    "band_33000_35000",
    "band_35000_37000",
    "band_37000_39000",
    "band_39000_41000",
    "band_41000_43000",
    "band_43000_no_limit",
]


def _lookup(roles: list[str]) -> dict[str, object]:
    return {
        "op": "LOOKUP_TABLE",
        "args": [
            {"role": "key", "line": "7"},
            *(
                {"role": role, "const": index}
                for index, role in enumerate(roles, 1)
            ),
        ],
        # M20-S85: comparison is required on every node, null off IF_ELSE.
        "comparison": None,
    }


def test_lookup_table_accepts_all_source_bands_in_any_printed_column_order() -> None:
    assert validate_lookup_table_completeness(_lookup(ALL_BANDS), TABLE_TEXT) == ()


def test_lookup_table_rejects_the_2441_six_of_sixteen_truncation() -> None:
    issues = validate_lookup_table_completeness(_lookup(ALL_BANDS[:6]), TABLE_TEXT)

    kinds = {issue.kind for issue in issues}
    messages = " ".join(issue.message for issue in issues)
    assert "lookup_table_incomplete" in kinds
    assert "lookup_table_missing_bands" in kinds
    assert "25000-27000" in messages
    assert "no missing band may be inferred" in messages


def test_lookup_table_rejects_gaps_and_overlaps_in_source_or_expression() -> None:
    source_gap = "0-10 .1 12-20 .2"
    source_gap_issues = validate_lookup_table_completeness(
        _lookup(["band_0_10", "band_12_20"]),
        source_gap,
    )
    assert any(issue.kind == "lookup_table_band_gap" for issue in source_gap_issues)

    expression_overlap = validate_lookup_table_completeness(
        _lookup(["band_0_10", "band_9_20"]),
        "0-10 .1 10-20 .2",
    )
    assert any(issue.kind == "lookup_table_band_overlap" for issue in expression_overlap)

    open_ended_overlap = validate_lookup_table_completeness(
        _lookup(["band_0_10", "band_10_no_limit", "band_20_30"]),
        "0-10 .1 10-No limit .2 20-30 .3",
    )
    assert any(issue.kind == "lookup_table_band_overlap" for issue in open_ended_overlap)


def test_lookup_table_fails_closed_when_branch_roles_do_not_state_bounds() -> None:
    issues = validate_lookup_table_completeness(
        _lookup(["band_under_15000", "default"]),
        "0-15,000 .35 15,000-17,000 .34",
    )

    assert [issue.kind for issue in issues] == ["lookup_table_bounds_unverifiable"]


def test_schema_leaves_role_ownership_to_the_deterministic_validator() -> None:
    schema = expression_schema()
    # M20-S85 made comparison a required key on every expression node - null for
    # everything but IF_ELSE - so absence is typed rather than silently defaulted.
    ordinary = {"expression": {"op": "COPY", "args": [{"line": "1", "role": None}], "comparison": None}, "quote": "line 1"}
    ordinary_with_role = {"expression": {"op": "COPY", "args": [{"line": "1", "role": "source"}], "comparison": None}, "quote": "line 1"}
    lookup = {"expression": _lookup(["band_0_10", "band_10_no_limit"]), "quote": "0-10 10-No limit"}

    from jsonschema import Draft202012Validator

    Draft202012Validator(schema).validate(ordinary)
    Draft202012Validator(schema).validate(ordinary_with_role)
    Draft202012Validator(schema).validate(lookup)
    with pytest.raises(ValueError, match="only valid on LOOKUP_TABLE"):
        validate_expression_tree(ordinary_with_role["expression"])


def test_expression_schema_uses_only_the_supported_provider_keyword_class() -> None:
    """Keep unsupported JSON Schema composition out of every emitted depth."""
    supported = {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "anyOf",
        "enum",
        "description",
        "pattern",
        "format",
        "minLength",
        "maxLength",
        "multipleOf",
        "maximum",
        "exclusiveMaximum",
        "minimum",
        "exclusiveMinimum",
        "minItems",
        "maxItems",
    }

    def visit_schema(value: object, path: str, *, root: bool = False) -> None:
        assert isinstance(value, dict), path
        unexpected = set(value) - supported
        assert not unexpected, f"unsupported schema keywords at {path}: {sorted(unexpected)}"
        if root:
            assert "anyOf" not in value, "Structured Outputs root must remain an object"
        properties = value.get("properties")
        if isinstance(properties, dict):
            required = value.get("required")
            assert isinstance(required, list), f"missing required list at {path}"
            assert set(properties) == set(required), f"properties/required mismatch at {path}"
            for name, child in properties.items():
                visit_schema(child, f"{path}.properties.{name}")
        items = value.get("items")
        if isinstance(items, dict):
            visit_schema(items, f"{path}.items")
        alternatives = value.get("anyOf")
        if isinstance(alternatives, list):
            for index, child in enumerate(alternatives):
                visit_schema(child, f"{path}.anyOf[{index}]")

    visit_schema(expression_schema(depth=3), "schema", root=True)


def test_lookup_completeness_is_a_hard_cell_output_failure() -> None:
    row = CellRecord(
        form="form_test_2025",
        line="8",
        label="Lookup",
        form_face_text=TABLE_TEXT,
    )
    hard, _warnings = validate_cell_output(
        row,
        _lookup(ALL_BANDS[:6]),
        TABLE_TEXT,
    )
    assert any(issue.kind == "lookup_table_incomplete" for issue in hard)
