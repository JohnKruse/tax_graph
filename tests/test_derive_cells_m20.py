"""M20-S26 tests for the pure typed cell derivation boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.extract.cells import (
    CellFrame,
    build_reference_inventory,
    build_cell_frame_from_document,
    clean_form_face_text,
    derive_cells,
    expression_schema,
    expression_to_graph,
    load_cell_prompt,
    render,
    validate_cell_output,
    validate_expression_tree,
    _line_mentioned,
)


pytestmark = pytest.mark.m20

ROOT = Path(__file__).resolve().parents[1]


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def structured_completion(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _frame() -> list[dict[str, str]]:
    return [
        {
            "form": "form_1040_2025",
            "line": "15",
            "label": "Taxable income",
            "form_face_text": "Subtract line 14 from line 11b. If zero or less, enter -0-.",
            "instruction_text": "Subtract line 14 from line 11b.",
            "instruction_locator": "span_line_15",
        },
        {
            "form": "form_1040_2025",
            "line": "22",
            "label": "Excess advance premium tax credit repayment",
            "form_face_text": "Enter the amount from line 21.",
            "instruction_text": "Enter the amount from line 21.",
            "instruction_locator": "span_line_22",
        },
    ]


def test_derive_cells_returns_row_level_results_and_writes_nothing(tmp_path: Path) -> None:
    client = FakeClient([
        {
            "expression": {
                "op": "MAX",
                "args": [
                    {
                        "op": "SUBTRACT",
                        "args": [{"line": "11b"}, {"line": "14"}],
                    },
                    {"const": 0},
                ],
            },
            "quote": "Subtract line 14 from line 11b. If zero or less, enter -0-.",
        },
        RuntimeError("provider unavailable"),
    ])
    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))

    result = derive_cells(_frame(), "line <<line>>: <<form_face_text>>", "secret", client=client)

    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    assert before == after
    assert [row["status"] for row in result] == ["derived", "error"]
    assert result[0]["rendered"] == "max(line 11b - line 14, 0)"
    assert result[0]["quote_span_id"] == "span_line_15"
    assert "provider unavailable" in result[1]["error"]
    assert client.calls[0]["purpose"] == "tax_graph_cell_derivation"
    assert "line 15" in client.calls[0]["prompt"]


def test_prompt_includes_sorted_untruncated_printed_line_inventory() -> None:
    row = {
        **_frame()[1],
        "metadata": {"printed_lines": ["25d", "8z", "8a", "1", "8b", "21"]},
    }
    client = FakeClient([
        {
            "expression": {"op": "COPY", "args": [{"line": "8a"}]},
            "quote": row["form_face_text"],
        }
    ])

    result = derive_cells(CellFrame.from_rows([row]), "printed: <<printed_lines>>", "secret", client=client)

    assert result.rows[0].status == "derived"
    assert client.calls[0]["prompt"] == "printed: 1, 8a, 8b, 8z, 21, 25d"


def test_prompt_includes_relevant_graph_node_inventory_and_handles_absence() -> None:
    row = {**_frame()[1], "metadata": {"printed_lines": ["21", "22"]}}
    client = FakeClient([
        {"expression": {"op": "COPY", "args": [{"line": "21"}]}, "quote": row["form_face_text"]},
        {"expression": {"op": "COPY", "args": [{"line": "21"}]}, "quote": row["form_face_text"]},
    ])

    result = derive_cells(
        CellFrame.from_rows([row, row]),
        "nodes:\n<<graph_nodes>>",
        "secret",
        client=client,
        reference_inventory={
            "node_ids": [],
            "graph_nodes": [
                {"node_id": "form_1040_2025_standard_deduction_single", "label": "Standard deduction, Single"},
            ],
        },
    )

    assert result.coverage == {"total": 2, "derived": 2}
    assert client.calls[0]["prompt"] == (
        "nodes:\n- form_1040_2025_standard_deduction_single: Standard deduction, Single"
    )

    absent_client = FakeClient([
        {"expression": {"op": "COPY", "args": [{"line": "21"}]}, "quote": row["form_face_text"]},
    ])
    absent = derive_cells(
        CellFrame.from_rows([row]),
        "nodes:\n<<graph_nodes>>",
        "secret",
        client=absent_client,
    )
    assert absent.rows[0].status == "derived"
    assert absent_client.calls[0]["prompt"] == "nodes:\nnone available"


def test_reference_inventory_lists_only_parameter_and_fact_nodes() -> None:
    class FakeGraph:
        def items(self, kind):
            return {
                "documents": [{"document_id": "form_1040_2025"}],
                "nodes": [
                    {"node_id": "fact_b", "node_type": "fact", "label": "Fact B", "document_id": "form_1040_2025"},
                    {"node_id": "computed_a", "node_type": "computed", "label": "Computed A", "document_id": "form_1040_2025"},
                    {"node_id": "parameter_a", "node_type": "parameter", "label": "Parameter A", "document_id": "form_1040_2025"},
                ],
            }.get(kind, [])

    inventory = build_reference_inventory(FakeGraph())

    assert inventory["node_ids"] == ["computed_a", "fact_b", "parameter_a"]
    assert inventory["graph_nodes"] == [
        {"node_id": "fact_b", "label": "Fact B"},
        {"node_id": "parameter_a", "label": "Parameter A"},
    ]
    assert inventory["graph_node_details"]["parameter_a"] == {
        "node_type": "parameter",
        "document_id": "form_1040_2025",
        "label": "Parameter A",
    }


def test_prompt_scopes_graph_nodes_to_document_and_global_filer_facts() -> None:
    row = {**_frame()[1], "metadata": {"printed_lines": ["21", "22"]}}
    client = FakeClient([
        {"expression": {"op": "COPY", "args": [{"line": "21"}]}, "quote": row["form_face_text"]},
    ])
    inventory = {
        "node_ids": [],
        "graph_nodes": [
            {"node_id": "form_1040_2025_zero_floor", "label": "Zero floor"},
            {"node_id": "schedule_d_2025_capital_loss_limit_default", "label": "Capital loss limit"},
            {"node_id": "taxpayer_2025_filing_status", "label": "Filing status"},
            {"node_id": "global_fact", "label": "Global fact"},
        ],
        "graph_node_details": {
            "form_1040_2025_zero_floor": {
                "node_type": "parameter", "document_id": "form_1040_2025",
            },
            "schedule_d_2025_capital_loss_limit_default": {
                "node_type": "parameter", "document_id": "schedule_d_2025",
            },
            "taxpayer_2025_filing_status": {
                "node_type": "fact", "document_id": "form_1040_2025",
            },
            "global_fact": {"node_type": "fact", "document_id": ""},
        },
    }

    result = derive_cells(
        CellFrame.from_rows([row]),
        "nodes:\n<<graph_nodes>>",
        "secret",
        client=client,
        reference_inventory=inventory,
    )

    assert result.rows[0].status == "derived"
    assert client.calls[0]["prompt"] == (
        "nodes:\n"
        "- form_1040_2025_zero_floor: Zero floor\n"
        "- global_fact: Global fact\n"
        "- taxpayer_2025_filing_status: Filing status"
    )


def test_missing_floor_accepts_cited_zero_parameter_and_rejects_nonzero_parameter() -> None:
    row = CellFrame.from_rows([_frame()[0]]).rows[0]
    expression = {
        "op": "MAX",
        "args": [
            {"op": "SUBTRACT", "args": [{"line": "11b"}, {"line": "14"}]},
            {"node": "form_1040_2025_zero_floor"},
        ],
    }
    inventory = {
        "node_ids": ["form_1040_2025_zero_floor"],
        "graph_node_details": {
            "form_1040_2025_zero_floor": {
                "node_type": "parameter",
                "constant_value": 0,
            },
        },
    }

    hard, _warnings = validate_cell_output(
        row, expression, row.form_face_text, reference_inventory=inventory,
    )
    assert hard == ()

    nonzero_inventory = {
        **inventory,
        "graph_node_details": {
            "form_1040_2025_zero_floor": {
                "node_type": "parameter",
                "constant_value": 1,
            },
        },
    }
    hard, _warnings = validate_cell_output(
        row, expression, row.form_face_text, reference_inventory=nonzero_inventory,
    )
    assert [issue.kind for issue in hard] == ["missing_floor"]


def test_curated_human_comment_is_rendered_for_one_address_only() -> None:
    address = "2025/document=form_1040/line=15/control=amount"
    row = {**_frame()[0], "canonical_address": address}
    client = FakeClient([
        {
            "expression": {
                "op": "MAX",
                "args": [
                    {"op": "SUBTRACT", "args": [{"line": "11b"}, {"line": "14"}]},
                    {"const": 0},
                ],
            },
            "quote": row["form_face_text"],
        }
    ])

    result = derive_cells(
        CellFrame.from_rows([row]),
        "comment: <<human_comment>>",
        "secret",
        client=client,
        human_comments={address: "Use the printed line 14 rule."},
    )

    assert result.rows[0].status == "derived"
    assert client.calls[0]["prompt"] == "comment: Use the printed line 14 rule."
    assert result.rows[0].human_comment == "Use the printed line 14 rule."


def test_empty_human_comment_keeps_the_prompt_value_empty() -> None:
    client = FakeClient([
        {
            "expression": {"op": "COPY", "args": [{"line": "21"}]},
            "quote": _frame()[1]["form_face_text"],
        }
    ])

    result = derive_cells(
        CellFrame.from_rows(_frame()[1:]),
        "before\n<<human_comment>>\nafter",
        "secret",
        client=client,
        human_comments={},
    )

    assert result.rows[0].status == "derived"
    assert client.calls[0]["prompt"] == "before\n\nafter"


def test_cell_frame_round_trip_and_missing_client_fail_closed() -> None:
    frame = CellFrame.from_rows(_frame())
    result = derive_cells(frame, "<<form>> <<line>>", None)

    assert isinstance(result, CellFrame)
    assert result.coverage == {"total": 2, "error": 2}
    assert all("no configured cell provider client" in (row.error or "") for row in result.rows)


def test_quote_span_id_is_resolved_from_verbatim_match() -> None:
    client = FakeClient([
        {
            "expression": {
                "op": "MAX",
                "args": [
                    {"op": "SUBTRACT", "args": [{"line": "11b"}, {"line": "14"}]},
                    {"const": 0},
                ],
            },
            "quote": "Subtract line 14 from line 11b. If zero or less, enter -0-.",
            "quote_span_id": "model_invented_span",
        }
    ])

    result = derive_cells(_frame()[:1], "<<line>>", "secret", client=client)

    assert result[0]["status"] == "derived"
    assert result[0]["quote_span_id"] == "span_line_15"


def test_expression_schema_is_bounded_and_contains_no_recursive_ref() -> None:
    schema = expression_schema(["MAX", "SUBTRACT"], depth=2)
    serialized = repr(schema)
    assert "$ref" not in serialized
    assert schema["properties"]["expression"]["properties"]["op"]["enum"] == ["MAX", "SUBTRACT"]


def test_quote_span_schema_does_not_expose_source_identity() -> None:
    rows = [
        {
            **_frame()[0],
            "metadata": {
                "evidence_spans": [
                    {"span_id": "face_15", "text": _frame()[0]["form_face_text"]},
                    {"span_id": "instruction_15", "text": _frame()[0]["instruction_text"]},
                ]
            },
        },
        {
            **_frame()[1],
            "metadata": {
                "evidence_spans": [
                    {"span_id": "face_22", "text": _frame()[1]["form_face_text"]},
                ]
            },
        },
    ]
    client = FakeClient([
        {
            "expression": {
                "op": "MAX",
                "args": [
                    {"op": "SUBTRACT", "args": [{"line": "11b"}, {"line": "14"}]},
                    {"const": 0},
                ],
            },
            "quote": _frame()[0]["form_face_text"],
        },
        {
            "expression": {"op": "COPY", "args": [{"line": "21"}]},
            "quote": _frame()[1]["form_face_text"],
        },
    ])

    result = derive_cells(CellFrame.from_rows(rows), "<<line>>", "secret", client=client)

    assert result.coverage == {"total": 2, "derived": 2}
    assert client.calls[0]["schema"]["required"] == ["expression", "quote"]
    assert "quote_span_id" not in client.calls[0]["schema"]["properties"]
    assert client.calls[1]["schema"] == client.calls[0]["schema"]


def test_quote_span_schema_keeps_strict_required_contract() -> None:
    schema = expression_schema()

    assert schema["required"] == ["expression", "quote"]
    assert set(schema["properties"]) == {"expression", "quote"}


def test_require_input_may_reference_its_own_line() -> None:
    row = {
        "form": "form_1040_2025",
        "line": "35a",
        "label": "Amount of line 34 you want refunded to you.",
        "form_face_text": "Amount of refund requested.",
        "instruction_text": "",
        "instruction_locator": "face_35a",
    }
    client = FakeClient([
        {
            "expression": {"op": "REQUIRE_INPUT", "args": [{"line": "35a"}]},
            "quote": "Amount of refund requested.",
        }
    ])

    result = derive_cells(CellFrame.from_rows([row]), "<<line>>", "secret", client=client)

    assert result.coverage == {"total": 1, "derived": 1}
    assert result.validation["validator_warnings_by_kind"] == {"unmapped_operation": 1}


def test_require_input_non_self_operand_still_warns_when_quote_omits_it() -> None:
    row = {
        "form": "form_1040_2025",
        "line": "35a",
        "label": "Amount of line 34 you want refunded to you.",
        "form_face_text": "Amount of refund requested.",
        "instruction_text": "",
        "instruction_locator": "face_35a",
    }
    client = FakeClient([
        {
            "expression": {"op": "REQUIRE_INPUT", "args": [{"line": "34"}]},
            "quote": "Amount of refund requested.",
        }
    ])

    result = derive_cells(CellFrame.from_rows([row]), "<<line>>", "secret", client=client)

    assert result.coverage == {"total": 1, "derived": 1}
    assert result.validation["validator_warnings_by_kind"] == {
        "operand_not_in_quote": 1,
        "unmapped_operation": 1,
    }


def test_tree_to_graph_preserves_floor_shape_and_subtraction_roles() -> None:
    projection = expression_to_graph(
        form="form_1040_2025",
        line="15",
        expression={
            "op": "MAX",
            "args": [
                {"op": "SUBTRACT", "args": [{"line": "11b"}, {"line": "14"}]},
                {"const": 0},
            ],
        },
        quote_span_id="cite_line_15",
    )

    assert any(node["node_id"] == "form_1040_2025_root_line_15_pre_floor" for node in projection.nodes)
    subtract_edges = [edge for edge in projection.edges if edge["rule_id"] == "subtract_currency"]
    assert [(edge["source"], edge["role"]) for edge in subtract_edges] == [
        ("form_1040_2025_root_line_11b", "minuend"),
        ("form_1040_2025_root_line_14", "subtrahend"),
    ]
    max_edges = [edge for edge in projection.edges if edge["rule_id"] == "max_currency"]
    assert {edge["source"] for edge in max_edges} == {
        "form_1040_2025_root_line_15_pre_floor",
        "form_1040_2025_zero_floor",
    }
    assert all(edge["citation_refs"] == ["cite_line_15"] for edge in projection.edges)
    assert render({"op": "MAX", "args": [{"line": "15"}, {"const": 0}]}) == "max(line 15, 0)"


def test_prompt_is_loaded_from_config(tmp_path: Path) -> None:
    prompt_path = tmp_path / "cells.md"
    prompt_path.write_text("<<form>> / <<line>>", encoding="ascii")

    assert load_cell_prompt(
        {"extraction": {"prompts": {"cells": "cells.md"}}},
        root=tmp_path,
    ) == "<<form>> / <<line>>"


def test_property_failure_is_repaired_once_and_reported() -> None:
    bad = {
        "expression": {"op": "SUBTRACT", "args": [{"line": "15"}, {"line": "14"}]},
        "quote": "Subtract line 14 from line 11b. If zero or less, enter -0-.",
    }
    good = {
        "expression": {
            "op": "MAX",
            "args": [
                {"op": "SUBTRACT", "args": [{"line": "11b"}, {"line": "14"}]},
                {"const": 0},
            ],
        },
        "quote": "Subtract line 14 from line 11b. If zero or less, enter -0-.",
    }
    client = FakeClient([bad, good])
    frame = CellFrame.from_rows(_frame()[:1])

    result = derive_cells(frame, "<<form>> <<line>>", "secret", client=client)

    assert result.rows[0].status == "repaired"
    assert result.rows[0].rendered == "max(line 11b - line 14, 0)"
    assert result.validation_report["attempted"] == 1
    assert result.validation_report["repaired"] == 1
    assert result.validation_report["gapped"] == 0
    assert result.validation_report["validator_failures_by_kind"] == {
        "self_reference": 1,
        "subtract_direction": 1,
        "missing_floor": 1,
    }
    assert "self_reference" in client.calls[1]["prompt"]


def test_properties_allow_explicit_cross_form_and_warn_on_quote_omission() -> None:
    row = {
        **_frame()[0],
        "line": "22",
        "label": "Taxable income",
        "form_face_text": "Enter the amount from Form 2441 line 26.",
        "instruction_text": "Enter the amount from Form 2441 line 26.",
        "metadata": {"printed_lines": ["22", "21"]},
    }
    client = FakeClient([
        {
            "expression": {"op": "COPY", "args": [{"form": "form_2441_2025", "line": "26"}]},
            "quote": "Enter the amount from Form 2441 line 26.",
        }
    ])

    result = derive_cells(
        CellFrame.from_rows([row]),
        "<<line>>",
        "secret",
        client=client,
        reference_inventory={
            "document_ids": ["form_1040_2025", "form_2441_2025"],
            "printed_lines": {"form_2441_2025": ["26"]},
            "node_ids": [],
        },
    )

    assert result.rows[0].status == "derived"
    assert result.validation_report["gapped"] == 0
    assert result.validation_report["validator_warnings_by_kind"] == {}


def test_named_unseen_form_reference_mints_unresolved_external_node() -> None:
    row = {
        "form": "schedule_a_2025",
        "line": "15",
        "label": "Loss from casualty or theft",
        "form_face_text": "Attach Form 4684 and enter the amount from line 18 of that form.",
        "instruction_text": "Attach Form 4684 and enter the amount from line 18 of that form.",
        "instruction_locator": "face_15",
        "metadata": {
            "printed_lines": ["15"],
            "evidence_spans": [
                {
                    "span_id": "face_15",
                    "text": "Attach Form 4684 and enter the amount from line 18 of that form.",
                },
            ],
        },
    }
    client = FakeClient([
        {
            "expression": {"op": "COPY", "args": [{"form": "form_4684_2025", "line": "18"}]},
            "quote": row["form_face_text"],
        },
    ])

    result = derive_cells(
        CellFrame.from_rows([row]),
        "<<graph_nodes>>",
        "secret",
        client=client,
        reference_inventory={
            "document_ids": ["schedule_a_2025"],
            "printed_lines": {"schedule_a_2025": ["15"]},
            "node_ids": [],
            "graph_nodes": [],
        },
    )

    assert result.rows[0].status == "derived"
    assert result.validation_report["gapped"] == 0
    assert result.rows[0].metadata["unresolved_external_nodes"] == [{
        "node_id": "form_4684_2025_root_line_18",
        "document_id": "form_4684_2025",
        "line": "18",
        "label": "Attach Form 4684 and enter the amount from line 18 of that form.",
        "node_type": "fact",
        "value_type": "currency",
        "required": "required",
        "status": "unresolved",
        "citation_refs": ["face_15"],
    }]


def test_cross_form_operands_fail_closed_against_document_and_line_inventory() -> None:
    row = {
        **_frame()[0],
        "line": "22",
        "form_face_text": "Enter the amount from another form line 26.",
        "instruction_text": "Enter the amount from another form line 26.",
        "metadata": {"printed_lines": ["22"]},
    }
    inventory = {
        "document_ids": ["form_1040_2025", "form_2441_2025"],
        "printed_lines": {"form_2441_2025": ["26"]},
        "node_ids": [],
    }
    unknown_document = {"form": "form_1040_nr_2025", "line": "filing_status"}
    hard, _warnings = validate_cell_output(
        CellFrame.from_rows([row]).rows[0],
        {"op": "COPY", "args": [unknown_document]},
        row["form_face_text"],
        reference_inventory=inventory,
    )
    assert [(issue.kind, issue.message) for issue in hard] == [
        ("operand_document_not_found", "cross-form operand names unknown document form_1040_nr_2025")
    ]

    missing_line = {"form": "form_2441_2025", "line": "27"}
    hard, _warnings = validate_cell_output(
        CellFrame.from_rows([row]).rows[0],
        {"op": "COPY", "args": [missing_line]},
        row["form_face_text"],
        reference_inventory=inventory,
    )
    assert [(issue.kind, issue.message) for issue in hard] == [
        ("operand_not_printed", "line 27 is not a printed line on form_2441_2025")
    ]


def test_graph_node_operand_is_schema_validated_resolved_and_projected() -> None:
    expression = {"op": "COPY", "args": [{"node": "taxpayer_2025_filing_status"}]}
    validate_expression_tree(expression)
    schema = expression_schema()
    node_alternatives = schema["properties"]["expression"]["properties"]["args"]["items"]["anyOf"]
    assert {"node"} in [set(item["required"]) for item in node_alternatives]

    row = CellFrame.from_rows([{
        **_frame()[1],
        "metadata": {
            "printed_lines": ["21", "22"],
            "evidence_spans": [{"span_id": "face_22", "text": _frame()[1]["form_face_text"]}],
        },
    }]).rows[0]
    hard, _warnings = validate_cell_output(
        row,
        expression,
        row.form_face_text,
        reference_inventory={"node_ids": ["taxpayer_2025_filing_status"]},
    )
    assert hard == ()
    projection = expression_to_graph(
        form=row.form,
        line=row.line,
        expression=expression,
    )
    assert projection.edges[0]["source"] == "taxpayer_2025_filing_status"


def test_unknown_graph_node_operand_fails_closed() -> None:
    row = CellFrame.from_rows([_frame()[1]]).rows[0]
    hard, _warnings = validate_cell_output(
        row,
        {"op": "COPY", "args": [{"node": "invented_filer_fact"}]},
        row.form_face_text,
        reference_inventory={"node_ids": ["taxpayer_2025_filing_status"]},
    )
    assert [issue.kind for issue in hard] == ["operand_node_not_found"]


def test_conditional_argument_roles_and_shapes_are_explicit() -> None:
    valid = {
        "op": "IF_ELSE",
        "args": [{"line": "17"}, {"const": 239100}, {"const": 1}, {"const": 2}],
    }
    validate_expression_tree(valid)
    with pytest.raises(ValueError, match=r"IF_ELSE argument 1 \(condition\)"):
        validate_expression_tree({
            "op": "IF_ELSE",
            "args": [
                {"op": "COMPARE", "args": [{"line": "17"}, {"const": 239100}]},
                {"const": 1},
                {"const": 2},
                {"const": 3},
            ],
        })
    validate_expression_tree({
        "op": "AND",
        "args": [
            {"op": "COMPARE", "args": [{"line": "1"}, {"const": 0}]},
            {"op": "NOT", "args": [{"op": "COMPARE", "args": [{"line": "2"}, {"const": 0}]}]},
        ],
    })
    with pytest.raises(ValueError, match="AND arguments"):
        validate_expression_tree({"op": "AND", "args": [{"line": "1"}, {"line": "2"}]})


def test_unmapped_projection_operation_is_a_warning_not_a_clean_success() -> None:
    row = _frame()[1]
    client = FakeClient([
        {
            "expression": {
                "op": "IF_ELSE",
                "args": [
                    {"line": "21"},
                    {"const": 100000},
                    {"const": 1},
                    {"const": 2},
                ],
            },
            "quote": row["form_face_text"],
        },
    ])

    result = derive_cells(CellFrame.from_rows([row]), "<<line>>", "secret", client=client)

    assert result.rows[0].status == "derived"
    assert result.rows[0].metadata["validation_warnings"] == [{
        "kind": "unmapped_operation",
        "message": "graph projection: no reusable rule for operation IF_ELSE",
        "hard": False,
    }]
    assert result.validation_report["validator_warnings_by_kind"] == {
        "unmapped_operation": 1,
    }


def test_operand_absent_from_quote_is_warning_not_failure() -> None:
    row = {
        **_frame()[1],
        "metadata": {"printed_lines": ["22", "21", "20"]},
    }
    client = FakeClient([
        {
            "expression": {"op": "SUM", "args": [{"line": "21"}, {"line": "20"}]},
            "quote": "Enter the amount from line 21.",
        }
    ])

    result = derive_cells(CellFrame.from_rows([row]), "<<line>>", "secret", client=client)

    assert result.rows[0].status == "derived"
    assert result.validation_report["gapped"] == 0
    assert result.validation_report["validator_warnings_by_kind"] == {"operand_not_in_quote": 1}


def test_input_line_operands_are_valid_when_inventory_contains_all_printed_lines() -> None:
    row = {
        "form": "form_1040_2025",
        "line": "33",
        "label": "Total payments",
        "form_face_text": "Add lines 25d, 26, and 32. These are your total payments.",
        "instruction_text": "",
        "instruction_locator": "",
        "metadata": {
            "printed_lines": ["25d", "26", "32", "33"],
            "evidence_spans": [
                {
                    "span_id": "face_33",
                    "text": "Add lines 25d, 26, and 32. These are your total payments.",
                }
            ],
        },
    }
    client = FakeClient([
        {
            "expression": {
                "op": "SUM",
                "args": [{"line": "25d"}, {"line": "26"}, {"line": "32"}],
            },
            "quote": row["form_face_text"],
        }
    ])

    result = derive_cells(CellFrame.from_rows([row]), "<<line>>", "secret", client=client)

    assert result.rows[0].status == "derived"
    assert result.validation_report["validator_failures_by_kind"] == {}


def test_form_face_evidence_is_sufficient_without_instruction_text() -> None:
    row = {
        **_frame()[1],
        "instruction_text": "",
        "instruction_locator": "",
        "metadata": {
            "evidence_spans": [{"span_id": "face_22", "text": "Enter the amount from line 21."}],
            "form_face_span_id": "face_22",
            "printed_lines": ["21", "22"],
        },
    }
    client = FakeClient([
        {
            "expression": {"op": "COPY", "args": [{"line": "21"}]},
            "quote": "Enter the amount from line 21.",
        }
    ])

    result = derive_cells(CellFrame.from_rows([row]), "<<line>>", "secret", client=client)

    assert result.rows[0].status == "derived"
    assert result.validation_report["errored"] == 0


def test_wrong_instruction_owner_drops_section_but_keeps_form_face() -> None:
    row = {
        **_frame()[0],
        "metadata": {
            "instruction_owner_document_id": "schedule_2_2025",
            "instruction_lines": ["15"],
            "instruction_span_ids": ["instruction_15"],
            "form_face_span_id": "face_15",
            "evidence_spans": [
                {"span_id": "face_15", "text": _frame()[0]["form_face_text"]},
                {"span_id": "instruction_15", "text": _frame()[0]["instruction_text"]},
            ],
        },
    }
    client = FakeClient([
        {
            "expression": {
                "op": "MAX",
                "args": [
                    {"op": "SUBTRACT", "args": [{"line": "11b"}, {"line": "14"}]},
                    {"const": 0},
                ],
            },
            "quote": _frame()[0]["form_face_text"],
        }
    ])

    result = derive_cells(CellFrame.from_rows([row]), "<<line>>", "secret", client=client)

    assert result.rows[0].status == "derived"
    assert result.rows[0].instruction_text == ""
    assert result.rows[0].metadata["dropped_instruction_sections"][0]["kind"] == "instruction_wrong_owner"
    assert result.validation_report["instruction_sections_dropped"] == 1
    assert result.validation_report["instruction_drops_by_kind"] == {"instruction_wrong_owner": 1}
    assert len(client.calls) == 1


def test_wrong_instruction_line_drops_section_but_keeps_form_face() -> None:
    row = {
        **_frame()[0],
        "metadata": {
            "instruction_owner_document_id": "form_1040_2025",
            "instruction_lines": ["14"],
            "instruction_span_ids": ["instruction_15"],
            "form_face_span_id": "face_15",
            "evidence_spans": [
                {"span_id": "face_15", "text": _frame()[0]["form_face_text"]},
                {"span_id": "instruction_15", "text": _frame()[0]["instruction_text"]},
            ],
        },
    }
    client = FakeClient([
        {
            "expression": {
                "op": "MAX",
                "args": [
                    {"op": "SUBTRACT", "args": [{"line": "11b"}, {"line": "14"}]},
                    {"const": 0},
                ],
            },
            "quote": _frame()[0]["form_face_text"],
        }
    ])

    result = derive_cells(CellFrame.from_rows([row]), "{line}", "secret", client=client)

    assert result.rows[0].status == "derived"
    assert result.validation_report["instruction_drops_by_kind"] == {"instruction_wrong_line": 1}


def test_missing_both_evidence_sources_is_row_local_error() -> None:
    row = {**_frame()[0], "form_face_text": "", "instruction_text": "", "instruction_locator": ""}

    result = derive_cells(CellFrame.from_rows([row]), "<<line>>", "secret", client=FakeClient([]))

    assert result.rows[0].status == "error"
    assert "missing_evidence" in result.rows[0].error
    assert result.validation_report["errored"] == 1


@pytest.mark.parametrize(
    ("line", "raw", "expected"),
    [
        ("14", "$15,750 14 Add lines 12e, 13a, and 13b 14", "14 Add lines 12e, 13a, and 13b"),
        ("15", "jointly or 15 Subtract line 14 from line 11b. 15", "15 Subtract line 14 from line 11b."),
        ("21", "a box on line 21 Add lines 19 and 20 21", "21 Add lines 19 and 20"),
        ("22", "12a, 12b, 12c, 22 Subtract line 21 from line 18. 22", "22 Subtract line 21 from line 18."),
        ("1z", "z Add lines 1a through 1h 1z", "Add lines 1a through 1h"),
        ("25d", "d Add lines 25a through 25c 25d", "Add lines 25a through 25c"),
        ("8e", "e Add lines 8a through 8c 8e", "Add lines 8a through 8c"),
        ("14c", "c Add lines 14a and 14b 14c", "Add lines 14a and 14b"),
        (
            "36b",
            "your spouse was born before January 2, 1961, enter the amount from line 35 36b",
            "your spouse was born before January 2, 1961, enter the amount from line 35",
        ),
        (
            "34",
            "Refund 34 If line 33 is more than...",
            "34 If line 33 is more than...",
        ),
    ],
)
def test_clean_form_face_text_starts_at_its_own_line(line: str, raw: str, expected: str) -> None:
    assert clean_form_face_text(raw, line) == expected


@pytest.mark.parametrize(
    ("quote", "line", "expected"),
    [
        ("Subtract line 10 from line 9", "10", True),
        ("Subtract line 10 from line 9", "9", True),
        ("Add lines 1z, 2b, and 8", "1z", True),
        ("Add lines 1z, 2b, and 8", "2b", True),
        ("Add lines 1z, 2b, and 8", "8", True),
        ("Add lines 1z, 2b, and 8", "1", False),
        ("Add lines 25a through 25c", "25b", True),
        ("Add lines 25a through 25c", "25d", False),
    ],
)
def test_line_mentioned_supports_singular_lists_ranges_and_exact_tokens(
    quote: str, line: str, expected: bool
) -> None:
    assert _line_mentioned(quote, line) is expected


def test_second_property_failure_becomes_a_named_gap() -> None:
    invalid = {
        "expression": {"op": "SUBTRACT", "args": [{"line": "15"}, {"line": "14"}]},
        "quote": "Subtract line 14 from line 11b. If zero or less, enter -0-.",
    }
    client = FakeClient([invalid, invalid])

    result = derive_cells(CellFrame.from_rows(_frame()[:1]), "<<line>>", "secret", client=client)

    assert result.rows[0].status == "error"
    assert "validation gap after one repair" in result.rows[0].error
    assert result.validation_report["repaired"] == 0
    assert result.validation_report["gapped"] == 1
    assert len(client.calls) == 2


def test_real_1040_frame_carries_join_ownership_and_printed_line_inventory() -> None:
    pytest.importorskip("yaml")
    from tax_graph.extract.inputs import load_document_input

    raw = ROOT / ".cache" / "raw" / "2025" / "form_1040_2025.txt"
    fields = ROOT / ".cache" / "raw" / "2025" / "form_1040_2025.fields.json"
    if not raw.is_file() or not fields.is_file():
        pytest.skip("real 1040 acquisition artifacts are not available")
    document = load_document_input("form_1040_2025", year="2025", root=ROOT)

    frame = build_cell_frame_from_document(document)

    assert len(frame.rows) == 17
    assert all(row.metadata["instruction_owner_document_id"] == "form_1040_2025" for row in frame.rows)
    assert all(row.line in row.metadata["printed_lines"] for row in frame.rows)
    assert {"1a", "16", "23", "26"}.issubset(frame.rows[0].metadata["printed_lines"])
    assert all(row.metadata["evidence_spans"] for row in frame.rows)
    assert frame.rows[0].metadata["evidence_spans"][0]["text"] == frame.rows[0].form_face_text
    source_texts = {document.text}
    source_texts.update(source.text for source in document.related_sources)
    # Assembled physical rows join source lines with one space; compare spans
    # after whitespace normalization, which preserves the acquired text order.
    normalized = lambda value: " ".join(value.split())
    assert all(
        any(normalized(span["text"]) in normalized(source_text) for source_text in source_texts)
        for row in frame.rows
        for span in row.metadata["evidence_spans"]
    )
    normalized_sources = {" ".join(source.split()) for source in source_texts}
    assert all(
        any(" ".join(row.form_face_text.split()) in source_text for source_text in normalized_sources)
        for row in frame.rows
    )
    rows_by_line = {row.line: row for row in frame.rows}
    assert rows_by_line["1z"].form_face_text == "Add lines 1a through 1h"
    assert rows_by_line["25d"].form_face_text == "Add lines 25a through 25c"
    assert frame.rows[5].label == "15 Subtract line 14 from line 11b. If zero or less, enter -0-. This is your taxable income"
    assert frame.rows[8].label == "22 Subtract line 21 from line 18. If zero or less, enter -0-"
