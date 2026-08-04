"""M20-S51 tests for honest derivation denominators and skipped anchors."""

from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.models import SourceDocumentInput
from tax_graph.extract.outline import OutlineNode, OutlineTree
from tax_graph.extract.outline import build_outline_tree
from tax_graph.extract.outline_pipeline import build_derivation_denominator


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]


def _synthetic_document() -> SourceDocumentInput:
    return SourceDocumentInput(
        document_id="form_test_2025",
        kind="tax_form",
        year="2025",
        url="https://example.test/form.pdf",
        text="",
        text_path=Path("form_test.txt"),
        fields={"fields": [], "line_anchors": []},
    )


def test_denominator_reports_legacy_and_widened_selector_decisions() -> None:
    document = _synthetic_document()
    outline = OutlineTree(
        document_id=document.document_id,
        kind=document.kind,
        children=[
            OutlineNode(
                outline_id="line_6",
                kind="line",
                line_anchor="6",
                label="Enter the smallest of line 3, 4, or 5.",
            ),
            OutlineNode(
                outline_id="line_8",
                kind="line",
                line_anchor="8",
                label="Enter the amount shown below that applies to line 7.",
            ),
            OutlineNode(
                outline_id="line_9",
                kind="line",
                line_anchor="9",
                label="Enter the name and identifying number.",
            ),
        ],
    )

    report = build_derivation_denominator(document, outline=outline)

    assert report["line_anchor_count"] == 3
    assert report["legacy_admitted"] == 0
    assert report["admitted"] == 2
    assert report["skipped"] == 1
    assert report["status"] == "complete"
    by_anchor = {item["anchor"]: item for item in report["anchors"]}
    assert by_anchor["6"]["before"]["selector_admits"] is False
    assert by_anchor["6"]["after"]["selector_cue"] == "smallest_of_line"
    assert by_anchor["8"]["after"]["selector_cue"] == "amount_shown_below"
    assert by_anchor["9"]["skip_reason"] == "selector_no_formula_cue"


def test_denominator_classifies_duplicate_and_header_structure_findings() -> None:
    document = _synthetic_document()
    outline = OutlineTree(
        document_id=document.document_id,
        kind=document.kind,
        children=[
            OutlineNode(
                outline_id="header_21",
                kind="line",
                line_anchor="21",
                label="Internal Revenue Service 21 Sequence No.",
            ),
            OutlineNode(
                outline_id="line_12_a",
                kind="line",
                line_anchor="12",
                label="Name of qualifying person.",
            ),
            OutlineNode(
                outline_id="line_12_b",
                kind="line",
                line_anchor="12",
                label="Name of qualifying person.",
            ),
        ],
    )

    report = build_derivation_denominator(document, outline=outline)

    assert report["status"] == "complete"
    assert report["skipped_by_reason"] == {
        "structure_duplicate_anchor": 2,
        "structure_header_anchor": 1,
    }
    assert report["accounted"] == report["line_anchor_count"]


def test_form_2441_denominator_names_the_newly_visible_rows() -> None:
    required = [
        ROOT / ".cache" / "raw" / "2025" / "form_2441_2025.txt",
        ROOT / ".cache" / "raw" / "2025" / "form_2441_2025.fields.json",
        ROOT / ".cache" / "raw" / "2025" / "form_2441_2025.pdf",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("local acquired 2441 structure artifacts are not present")

    document = load_document_input("form_2441_2025", year="2025", root=ROOT)
    report = build_derivation_denominator(
        document,
        outline=build_outline_tree(document),
    )

    assert report["line_anchor_count"] == 35
    assert report["legacy_admitted"] == 12
    assert report["admitted"] == 21
    assert report["skipped"] == 14
    assert report["status"] == "complete"
    assert report["newly_admitted_by_cue"] == {
        "add_the_amount": 2,
        "amount_shown_below": 2,
        "dollar_constant": 2,
        "smallest_of_line": 3,
    }
    by_anchor = {item["anchor"]: item for item in report["anchors"]}
    assert by_anchor["8"]["selector_cue"] == "amount_shown_below"
    assert by_anchor["6"]["selector_cue"] == "smallest_of_line"
    assert by_anchor["19"]["selector_cue"] == "amount_shown_below"
    assert by_anchor["21"]["selector_cue"] == "dollar_constant"
    assert by_anchor["27"]["selector_cue"] == "dollar_constant"
    assert by_anchor["12"]["skip_reason"] == "structure_duplicate_anchor"
    assert by_anchor["1"]["skip_reason"] == "selector_no_formula_cue"


def test_denominator_reports_total_classification() -> None:
    report = build_derivation_denominator(
        _synthetic_document(),
        outline=OutlineTree(
            document_id="form_test_2025",
            kind="tax_form",
            children=[
                OutlineNode(
                    outline_id="line_1",
                    kind="line",
                    line_anchor="1",
                    label="Enter an amount.",
                )
            ],
        ),
    )

    assert report["status"] == "complete"
    assert report["classification"] == "total"
    assert report["unaccounted"] == 0
