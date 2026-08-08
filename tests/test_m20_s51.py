"""M20-S51 tests for honest derivation denominators and structural skips."""

from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.models import SourceDocumentInput
from tax_graph.extract.outline import OutlineNode, OutlineTree
from tax_graph.extract.outline import build_outline_tree
from tax_graph.extract.outline_pipeline import (
    _flatten_nodes,
    build_derivation_denominator,
)


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
    assert report["admitted"] == 3
    assert report["skipped"] == 0
    assert report["status"] == "complete"
    by_anchor = {item["anchor"]: item for item in report["anchors"]}
    assert by_anchor["6"]["before"]["legacy_selector_admits"] is False
    assert by_anchor["6"]["after"]["legacy_selector_cue"] == "smallest_of_line"
    assert by_anchor["8"]["after"]["legacy_selector_cue"] == "amount_shown_below"
    assert by_anchor["9"]["skip_reason"] == ""
    assert by_anchor["9"]["derivation_admitted"] is True
    assert by_anchor["9"]["legacy_selector_admits"] is False


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
    assert report["legacy_admitted"] == 13
    assert report["admitted"] == 32
    assert report["skipped"] == 3
    assert report["status"] == "complete"
    assert set(report["skipped_by_reason"]) <= {
        "structure_duplicate_anchor",
        "structure_header_anchor",
        "structure_non_cell_anchor",
    }
    by_anchor = {item["anchor"]: item for item in report["anchors"]}
    assert by_anchor["8"]["legacy_selector_cue"] == "amount_shown_below"
    assert by_anchor["6"]["legacy_selector_cue"] == "smallest_of_line"
    assert by_anchor["19"]["legacy_selector_cue"] == "amount_from_line"
    assert by_anchor["21"]["legacy_selector_cue"] == "dollar_constant"
    assert by_anchor["27"]["legacy_selector_cue"] == "dollar_constant"
    assert by_anchor["12"]["skip_reason"] == "structure_duplicate_anchor"
    assert by_anchor["1"]["skip_reason"] == ""
    assert by_anchor["1"]["derivation_admitted"] is True
    assert by_anchor["1"]["legacy_selector_admits"] is False


@pytest.mark.parametrize(
    ("document_id", "anchor"),
    (("form_2441_2025", "21"), ("form_6251_2025", "32")),
)
def test_root_header_duplicate_does_not_consume_real_cell(
    document_id: str,
    anchor: str,
) -> None:
    required = [
        ROOT / ".cache" / "raw" / "2025" / f"{document_id}.txt",
        ROOT / ".cache" / "raw" / "2025" / f"{document_id}.fields.json",
        ROOT / ".cache" / "raw" / "2025" / f"{document_id}.pdf",
    ]
    if not all(path.exists() for path in required):
        pytest.skip(f"local acquired {document_id} structure artifacts are not present")

    document = load_document_input(document_id, year="2025", root=ROOT)
    outline = build_outline_tree(document)
    nodes = [
        node
        for node in _flatten_nodes(outline.children)
        if str(node.line_anchor).lower() == anchor
    ]
    assert any(node.outline_id == f"root_line_{anchor}" for node in nodes)

    report = build_derivation_denominator(document, outline=outline)
    entries = [item for item in report["anchors"] if item["anchor"] == anchor]
    assert any(item["skip_reason"] == "structure_header_anchor" for item in entries)
    assert any(
        item["derivation_admitted"] is True and item["skip_reason"] == ""
        for item in entries
    )


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
