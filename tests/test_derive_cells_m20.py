"""M20-S24 tests for the pure typed cell derivation boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.extract.cells import (
    CellFrame,
    build_cell_frame_from_document,
    derive_cells,
    expression_schema,
    expression_to_graph,
    load_cell_prompt,
    render,
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

    result = derive_cells(_frame(), "line {line}: {form_face_text}", "secret", client=client)

    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    assert before == after
    assert [row["status"] for row in result] == ["derived", "error"]
    assert result[0]["rendered"] == "max(line 11b - line 14, 0)"
    assert result[0]["quote_span_id"] == "span_line_15"
    assert "provider unavailable" in result[1]["error"]
    assert client.calls[0]["purpose"] == "tax_graph_cell_derivation"
    assert "line 15" in client.calls[0]["prompt"]


def test_cell_frame_round_trip_and_missing_client_fail_closed() -> None:
    frame = CellFrame.from_rows(_frame())
    result = derive_cells(frame, "{form} {line}", None)

    assert isinstance(result, CellFrame)
    assert result.coverage == {"total": 2, "error": 2}
    assert all("no configured cell provider client" in (row.error or "") for row in result.rows)


def test_model_cannot_invent_quote_span_id() -> None:
    client = FakeClient([
        {
            "expression": {"op": "REQUIRE_INPUT", "args": [{"line": "15"}]},
            "quote": "Subtract line 14 from line 11b. If zero or less, enter -0-.",
            "quote_span_id": "model_invented_span",
        }
    ])

    result = derive_cells(_frame()[:1], "{line}", "secret", client=client)

    assert result[0]["status"] == "error"
    assert "known input evidence span" in result[0]["error"]


def test_expression_schema_is_bounded_and_contains_no_recursive_ref() -> None:
    schema = expression_schema(["MAX", "SUBTRACT"], depth=2)
    serialized = repr(schema)
    assert "$ref" not in serialized
    assert schema["properties"]["expression"]["properties"]["op"]["enum"] == ["MAX", "SUBTRACT"]


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
    prompt_path.write_text("{form} / {line}", encoding="ascii")

    assert load_cell_prompt(
        {"extraction": {"prompts": {"cells": "cells.md"}}},
        root=tmp_path,
    ) == "{form} / {line}"


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

    result = derive_cells(frame, "{form} {line}", "secret", client=client)

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

    result = derive_cells(CellFrame.from_rows([row]), "{line}", "secret", client=client)

    assert result.rows[0].status == "derived"
    assert result.validation_report["gapped"] == 0
    assert result.validation_report["validator_warnings_by_kind"] == {}


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

    result = derive_cells(CellFrame.from_rows([row]), "{line}", "secret", client=client)

    assert result.rows[0].status == "derived"
    assert result.validation_report["gapped"] == 0
    assert result.validation_report["validator_warnings_by_kind"] == {"operand_not_in_quote": 1}


def test_input_owner_failure_is_row_local_and_does_not_call_provider() -> None:
    row = {
        **_frame()[0],
        "metadata": {
            "instruction_owner_document_id": "schedule_2_2025",
            "instruction_lines": ["15"],
        },
    }
    client = FakeClient([])

    result = derive_cells(CellFrame.from_rows([row]), "{line}", "secret", client=client)

    assert result.rows[0].status == "error"
    assert "instruction_wrong_owner" in result.rows[0].error
    assert client.calls == []
    assert result.validation_report["errored"] == 1


def test_second_property_failure_becomes_a_named_gap() -> None:
    invalid = {
        "expression": {"op": "SUBTRACT", "args": [{"line": "15"}, {"line": "14"}]},
        "quote": "Subtract line 14 from line 11b. If zero or less, enter -0-.",
    }
    client = FakeClient([invalid, invalid])

    result = derive_cells(CellFrame.from_rows(_frame()[:1]), "{line}", "secret", client=client)

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
    assert all(row.metadata["evidence_spans"] for row in frame.rows)
