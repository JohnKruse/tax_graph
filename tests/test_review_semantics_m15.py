"""Golden tests for M15 Step 4 simple semantic formatters."""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench.manifest import build_manifest
from workbench.schema import validate_review_expression
from workbench.semantics import format_computation


ROOT = Path(__file__).resolve().parents[1]


def _node(node_id: str, document_id: str, label: str | None = None) -> dict[str, str]:
    return {"node_id": node_id, "document_id": document_id, "label": label or node_id}


def _edge(source: str, role: str = "") -> dict[str, object]:
    edge: dict[str, object] = {"source": source, "citation_refs": ["cite_test"]}
    if role:
        edge["role"] = role
    return edge


@pytest.mark.m15
def test_sum_formatter_golden() -> None:
    document_id = "schedule_2_2025"
    sources = [
        "schedule_2_2025_part_i_line_z",
        "schedule_2_2025_part_ii_line_b",
        "schedule_2_2025_part_iii_line_b",
    ]
    nodes = {
        node_id: _node(node_id, document_id, f"Line {node_id.rsplit('_', 1)[-1]}: source {line}")
        for node_id, line in zip(sources, ["1z", "2b", "3b"], strict=True)
    }

    formatted = format_computation(
        target=_node("schedule_2_2025_root_line_4", document_id),
        rule={"operation": "SUM"},
        operand_edges=[_edge(node_id, "addend") for node_id in sources],
        nodes=nodes,
    )

    assert formatted.summary == "Add lines 1z + 2b + 3b"
    assert formatted.expression == {
        "kind": "sum",
        "operation": "SUM",
        "text": "Add lines 1z + 2b + 3b",
        "operands": [
            {
                "kind": "reference",
                "ref": {"object_type": "node", "object_id": node_id, "display_label": f"line {line}"},
            }
            for node_id, line in zip(sources, ["1z", "2b", "3b"], strict=True)
        ],
        "citation_refs": ["cite_test"],
    }
    validate_review_expression(formatted.expression)


@pytest.mark.m15
def test_subtract_formatter_golden() -> None:
    document_id = "form_1040_2025"
    line_14 = "form_1040_2025_root_line_14"
    line_15 = "form_1040_2025_root_line_15"

    formatted = format_computation(
        target=_node("form_1040_2025_root_line_16", document_id),
        rule={"operation": "SUBTRACT"},
        operand_edges=[_edge(line_14, "minuend"), _edge(line_15, "subtrahend")],
        nodes={line_14: _node(line_14, document_id), line_15: _node(line_15, document_id)},
    )

    assert formatted.summary == "Subtract line 15 from line 14"
    assert formatted.expression["left"]["ref"]["object_id"] == line_14
    assert formatted.expression["right"]["ref"]["object_id"] == line_15
    validate_review_expression(formatted.expression)


@pytest.mark.m15
def test_copy_formatter_golden() -> None:
    source_id = "schedule_1_2025_part_i_line_10"

    formatted = format_computation(
        target=_node("form_1040_2025_root_line_8", "form_1040_2025"),
        rule={"operation": "COPY"},
        operand_edges=[_edge(source_id)],
        nodes={source_id: _node(source_id, "schedule_1_2025")},
    )

    assert formatted.summary == "Copied from Schedule 1 line 10"
    assert formatted.expression["source"]["ref"]["display_label"] == "Schedule 1 line 10"
    validate_review_expression(formatted.expression)


@pytest.mark.m15
def test_negate_formatter_has_structured_source() -> None:
    source_id = "schedule_d_2025_root_line_21_limit_positive"
    formatted = format_computation(
        target=_node("schedule_d_2025_root_line_21_limit_negative", "schedule_d_2025"),
        rule={"operation": "NEGATE"},
        operand_edges=[_edge(source_id)],
        nodes={source_id: _node(source_id, "schedule_d_2025")},
    )

    assert formatted.summary == "Negate line 21"
    assert formatted.expression["kind"] == "negate"
    validate_review_expression(formatted.expression)


@pytest.mark.m15
def test_live_manifest_uses_simple_semantics_without_formatting_later_ops() -> None:
    manifest = build_manifest(ROOT, 2025)
    units = [unit for entry in manifest["entries"] for unit in entry["units"]]
    formatted = [unit for unit in units if unit["expression"]["kind"] in {"copy", "sum", "subtract", "negate"}]

    assert formatted
    assert any(unit["summary"].startswith("Copied from ") for unit in formatted)
    assert any(unit["summary"] == "Add lines 5a + 5b + 5c" for unit in formatted)
    assert all(unit["expression"].get("text") == unit["summary"] for unit in formatted)
