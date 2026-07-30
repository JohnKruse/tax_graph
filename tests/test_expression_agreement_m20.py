from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.verify.expressions import build_expression_agreement_report, write_expression_agreement_report


pytestmark = pytest.mark.m20


def _write_graph(root: Path) -> None:
    year_root = root / "graph" / "2025"
    for kind in ("documents", "nodes", "edges", "rules", "citations", "decisions", "tables"):
        (year_root / kind).mkdir(parents=True)
    (year_root / "documents" / "documents.yaml").write_text(
        "- document_id: form_1040_2025\n  title: Form 1040\n",
        encoding="ascii",
    )
    (year_root / "nodes" / "nodes.yaml").write_text(
        "\n".join(
            [
                "- node_id: form_1040_2025_sum_target",
                "  document_id: form_1040_2025",
                "  node_type: computed",
                "- node_id: form_1040_2025_subtract_target",
                "  document_id: form_1040_2025",
                "  node_type: computed",
                "",
            ]
        ),
        encoding="ascii",
    )
    (year_root / "rules" / "rules.yaml").write_text(
        "\n".join(
            [
                "- rule_id: rule_sum",
                "  operation: SUM",
                "  description: Add values.",
                "- rule_id: rule_subtract",
                "  operation: SUBTRACT",
                "  description: Subtract values.",
                "",
            ]
        ),
        encoding="ascii",
    )
    (year_root / "edges" / "edges.yaml").write_text(
        "\n".join(
            [
                "- edge_id: live_sum_a",
                "  source: form_1040_2025_a",
                "  target: form_1040_2025_sum_target",
                "  relationship: CALCULATES",
                "  rule_id: rule_sum",
                "  role: addend",
                "- edge_id: live_sum_b",
                "  source: form_1040_2025_b",
                "  target: form_1040_2025_sum_target",
                "  relationship: CALCULATES",
                "  rule_id: rule_sum",
                "  role: addend",
                "- edge_id: live_subtract_a",
                "  source: form_1040_2025_a",
                "  target: form_1040_2025_subtract_target",
                "  relationship: CALCULATES",
                "  rule_id: rule_subtract",
                "  role: minuend",
                "- edge_id: live_subtract_b",
                "  source: form_1040_2025_b",
                "  target: form_1040_2025_subtract_target",
                "  relationship: CALCULATES",
                "  rule_id: rule_subtract",
                "  role: subtrahend",
                "",
            ]
        ),
        encoding="ascii",
    )
    draft_root = year_root / "_drafts" / "form_1040_2025"
    draft_root.mkdir(parents=True)
    (draft_root / "nodes.yaml").write_text(
        "- node_id: form_1040_2025_sum_target\n  document_id: form_1040_2025\n",
        encoding="ascii",
    )
    (draft_root / "rules.yaml").write_text(
        "- rule_id: draft_sum\n  operation: SUM\n  description: Add values.\n",
        encoding="ascii",
    )
    (draft_root / "edges.yaml").write_text(
        "\n".join(
            [
                "- edge_id: draft_sum_b",
                "  source: form_1040_2025_b",
                "  target: form_1040_2025_sum_target",
                "  relationship: CALCULATES",
                "  rule_id: draft_sum",
                "  role: addend",
                "- edge_id: draft_sum_a",
                "  source: form_1040_2025_a",
                "  target: form_1040_2025_sum_target",
                "  relationship: CALCULATES",
                "  rule_id: draft_sum",
                "  role: addend",
                "",
            ]
        ),
        encoding="ascii",
    )


def test_expression_agreement_normalizes_commutative_operands_and_reports_missing(tmp_path: Path):
    _write_graph(tmp_path)

    report = build_expression_agreement_report(root=tmp_path)

    assert report["totals"]["expression_agreement"] == 1
    assert report["totals"]["missing_in_draft"] == 1
    assert report["totals"]["operation_agreement_operands_differ"] == 0
    assert report["by_document"]["form_1040_2025"]["expression_agreement"] == 1


def test_expression_agreement_distinguishes_wrong_operation_and_extra_target(tmp_path: Path):
    _write_graph(tmp_path)
    draft_root = tmp_path / "graph" / "2025" / "_drafts" / "form_1040_2025"
    (draft_root / "nodes.yaml").write_text(
        "\n".join(
            [
                "- node_id: form_1040_2025_sum_target",
                "  document_id: form_1040_2025",
                "  node_type: computed",
                "- node_id: form_1040_2025_subtract_target",
                "  document_id: form_1040_2025",
                "  node_type: computed",
                "- node_id: form_1040_2025_extra_target",
                "  document_id: form_1040_2025",
                "  node_type: computed",
                "",
            ]
        ),
        encoding="ascii",
    )
    (draft_root / "rules.yaml").write_text(
        "\n".join(
            [
                "- rule_id: draft_sum",
                "  operation: SUM",
                "  description: Add values.",
                "- rule_id: draft_wrong",
                "  operation: MAX",
                "  description: Pick a value.",
                "- rule_id: draft_extra",
                "  operation: COPY",
                "  description: Copy a value.",
                "",
            ]
        ),
        encoding="ascii",
    )
    (draft_root / "edges.yaml").write_text(
        "\n".join(
            [
                "- edge_id: draft_sum_b",
                "  source: form_1040_2025_b",
                "  target: form_1040_2025_sum_target",
                "  relationship: CALCULATES",
                "  rule_id: draft_sum",
                "  role: addend",
                "- edge_id: draft_sum_a",
                "  source: form_1040_2025_a",
                "  target: form_1040_2025_sum_target",
                "  relationship: CALCULATES",
                "  rule_id: draft_sum",
                "  role: addend",
                "- edge_id: draft_wrong_subtract",
                "  source: form_1040_2025_a",
                "  target: form_1040_2025_subtract_target",
                "  relationship: CALCULATES",
                "  rule_id: draft_wrong",
                "  role: minuend",
                "- edge_id: draft_extra",
                "  source: form_1040_2025_a",
                "  target: form_1040_2025_extra_target",
                "  relationship: CALCULATES",
                "  rule_id: draft_extra",
                "",
            ]
        ),
        encoding="ascii",
    )

    report = build_expression_agreement_report(root=tmp_path)

    assert report["totals"]["operation_disagreement"] == 1
    assert report["totals"]["extra_in_draft"] == 1


def test_expression_agreement_report_is_ascii_and_reproducible(tmp_path: Path):
    _write_graph(tmp_path)
    report = build_expression_agreement_report(root=tmp_path)

    first = write_expression_agreement_report(report, root=tmp_path)
    first_text = first.read_text(encoding="ascii")
    second = write_expression_agreement_report(report, root=tmp_path)

    assert first == second
    assert first_text == second.read_text(encoding="ascii")
