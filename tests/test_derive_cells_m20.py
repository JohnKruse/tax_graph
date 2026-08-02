"""M20-S24 tests for the pure typed cell derivation boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.extract.cells import (
    CellFrame,
    derive_cells,
    expression_schema,
    expression_to_graph,
    load_cell_prompt,
    render,
)


pytestmark = pytest.mark.m20


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
