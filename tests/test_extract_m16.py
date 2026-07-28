from __future__ import annotations

from pathlib import Path
import re

import pytest

from tax_graph.extract.assembly import assemble_formula_plan
from tax_graph.extract.models import SourceDocumentInput
from tax_graph.extract.outline import (
    CandidateSpan,
    OutlineNode,
    build_outline_tree,
    infer_value_type,
)
from tax_graph.extract.outline_pipeline import generate_outline_first_drafts


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.m4


class NoCallClient:
    def structured_completion(self, **kwargs):
        raise AssertionError("the M16 scalar fixture should not call formula extraction")


def _document(text: str, *, fields: dict | None = None) -> SourceDocumentInput:
    field_data = fields or {"fields": []}
    field_data.setdefault("line_anchors", _line_anchor_index(text))
    return SourceDocumentInput(
        document_id="schedule_2_2025",
        kind="schedule",
        year="2025",
        url="https://www.irs.gov/pub/irs-pdf/f1040s2.pdf",
        text=text,
        text_path=ROOT / ".cache" / "raw" / "2025" / "schedule_2_2025.txt",
        fields=field_data,
    )


def _line_anchor_index(text: str) -> list[dict[str, int | str]]:
    return [
        {
            "anchor": match.group(1).lower(),
            "page": 1,
            "text_offset": match.start(1),
            "text_length": len(match.group(1)),
        }
        for match in re.finditer(r"^[-]\s+([0-9]+[a-z]?|[a-z]):", text, re.IGNORECASE | re.MULTILINE)
    ]


def test_schedule_2_outline_preserves_heading_and_printed_total_anchor():
    document = _document(
        "\n".join(
            [
                "Header: Part I Tax",
                "- 1: Additions to tax:",
                "- z: Add lines 1a through 1y 1z",
            ]
        )
    )

    outline = build_outline_tree(document)
    part_i = outline.children[0]

    heading, total = part_i.children
    assert heading.kind == "heading"
    assert heading.line_anchor == "1"
    assert total.line_anchor == "1z"


def test_assembly_uses_outline_kind_for_inputs_and_keeps_computed_currency():
    document = _document("")
    outline_node = OutlineNode("part_i_line_1", "heading", "Additions to tax:")
    span = CandidateSpan(
        span_id="span_schedule_2_2025_0001",
        document_id=document.document_id,
        relationship="source",
        locator="page 1, line 1",
        text="- 1: Additions to tax:",
    )
    batch = assemble_formula_plan(
        document,
        outline_node,
        {
            "operation_plan": [
                {
                    "output": "heading_total",
                    "operation": "SUM",
                    "inputs": [{"name": "heading_input"}],
                    "citation_span_ids": [span.span_id],
                }
            ]
        },
        [span],
        root=ROOT,
    )

    nodes = {node.object_id: node.data for node in batch.items("nodes")}
    assert nodes["schedule_2_2025_part_i_line_1_heading_input"]["node_type"] == "concept"
    assert nodes["schedule_2_2025_part_i_line_1_heading_input"]["value_type"] == "string"
    assert nodes["schedule_2_2025_part_i_line_1_heading_total"]["node_type"] == "computed"
    assert nodes["schedule_2_2025_part_i_line_1_heading_total"]["value_type"] == "currency"


def test_value_type_inference_reads_printed_control_and_field_kind():
    checkbox_fields = {
        "fields": [
            {"field_name": "c1_1", "field_type": "CheckBox", "line_anchor": "4"},
            {"field_name": "c1_2", "field_type": "CheckBox", "line_anchor": "4"},
        ]
    }

    assert infer_value_type(OutlineNode("line_date", "line", "Date paid")) == "date"
    assert infer_value_type(OutlineNode("line_id", "line", "Social security number")) == "string"
    assert infer_value_type(OutlineNode("line_name", "line", "Name of payer")) == "string"
    assert infer_value_type(
        OutlineNode("line_check", "line", "Check one"),
        document=_document("", fields=checkbox_fields),
    ) == "boolean"
    assert infer_value_type(OutlineNode("line_total", "line", "Total additional tax")) == "currency"


def test_outline_first_emits_nonfillable_heading_and_printed_total_node():
    document = _document(
        "\n".join(
            [
                "Header: Part I Tax",
                "- 1: Additions to tax:",
                "- z: Add lines 1a through 1y 1z",
            ]
        )
    )

    batch = generate_outline_first_drafts(document, client=NoCallClient(), root=ROOT)
    nodes = {node.object_id: node.data for node in batch.items("nodes")}

    heading = nodes["schedule_2_2025_part_i_line_1"]
    total = nodes["schedule_2_2025_part_i_line_1z"]
    assert (heading["node_type"], heading["value_type"]) == ("concept", "string")
    assert (total["node_type"], total["value_type"]) == ("form_line", "currency")
    assert total["citation_refs"] == ["cite_span_schedule_2_2025_0003"]
