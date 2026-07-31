from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tax_graph.verify.form_completeness import (
    build_form_completeness_report,
    write_form_completeness_report,
)


pytestmark = pytest.mark.m20


def test_form_completeness_distinguishes_complete_expression_and_gap(tmp_path: Path, monkeypatch):
    draft = tmp_path / "graph" / "2025" / "_drafts" / "form_1040_2025"
    draft.mkdir(parents=True)
    (draft / "micro_extraction.yaml").write_text(
        yaml.safe_dump(
            {
                "formula_cells": [
                    {
                        "target_cell_id": "form_1040_2025_root_line_9",
                        "line_anchor": "9",
                        "status": "complete",
                        "has_expression": True,
                        "has_verbatim_citation": True,
                        "has_form_face_citation": True,
                        "has_instruction_citation": True,
                    },
                    {
                        "target_cell_id": "form_1040_2025_root_line_11a",
                        "line_anchor": "11a",
                        "status": "expression_without_citation",
                        "has_expression": True,
                        "has_verbatim_citation": False,
                        "review_gap": "expression produced without a matching verbatim citation",
                    },
                    {
                        "target_cell_id": "form_1040_2025_root_line_15",
                        "line_anchor": "15",
                        "status": "review_gap",
                        "has_expression": False,
                        "has_verbatim_citation": False,
                        "review_gap": "micro extraction failed: timeout",
                    },
                    {
                        "target_cell_id": "form_1040_2025_root_line_16",
                        "line_anchor": "16",
                        "status": "complete",
                        "has_expression": True,
                        "has_verbatim_citation": True,
                        "has_form_face_citation": True,
                        "has_instruction_citation": False,
                    },
                ],
                "wrong_owner_instruction_span_count": 1,
                "wrong_owner_instruction_addresses": ["form_1040_2025_root_line_1z"],
                "unresolved_line_refs": [{"code": "ambiguous_parent_source_line", "source_line": "11"}],
                "background_controls": [
                    {
                        "field_name": "control_a",
                        "address_id": "2025/document=form_1040/section=identity/control=a",
                        "label": "Control A",
                        "population_policy": "user_entered",
                        "has_policy": True,
                        "has_form_face_citation": True,
                    },
                    {
                        "field_name": "control_b",
                        "address_id": "2025/document=form_1040/section=identity/control=b",
                        "label": "Control B",
                        "population_policy": "unsupported",
                        "has_policy": False,
                        "review_gap": "policy extraction failed",
                    },
                ],
                "background_policy_before": {"unsupported": 1, "user_entered": 1},
                "background_policy_after": {"unsupported": 1, "user_entered": 1},
                "background_policy_progress": 0,
            },
            sort_keys=False,
        ),
        encoding="ascii",
    )
    (draft / "metrics.yaml").write_text(
        yaml.safe_dump(
            {
                "llm_calls": [
                    {
                        "resolved_model": "google/gemini-3.6-flash",
                        "resolved_provider": "Google AI Studio",
                        "prompt_tokens": 10,
                        "completion_tokens": 20,
                        "total_tokens": 30,
                        "cost": 0.01,
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="ascii",
    )
    monkeypatch.setattr(
        "tax_graph.verify.form_completeness.build_expression_agreement_report",
        lambda **_: {"rows": [{"document_id": "form_1040_2025", "category": "missing_in_draft"}]},
    )

    report = build_form_completeness_report(
        year="2025",
        root=tmp_path,
        documents=("form_1040_2025",),
    )
    item = report["by_document"]["form_1040_2025"]

    assert report["measurement"] == "m20_s19_form_completeness"
    assert report["totals"] == {
        "formula_cells": 4,
        "policy_controls": 2,
        "policy_controls_with_policy": 1,
        "policy_and_form_face_citation": 1,
        "policy_coverage_rate": pytest.approx(1 / 2),
        "policy_and_form_face_citation_rate": pytest.approx(1 / 2),
        "expression_and_verbatim_citation": 2,
        "expression_and_form_face_citation": 2,
        "expression_and_both_citations": 1,
        "completeness_rate": pytest.approx(1 / 2),
    }
    assert item["expression_and_form_face_citation"] == 2
    assert item["policy_controls"] == 2
    assert item["policy_controls_with_policy"] == 1
    assert item["policy_and_form_face_citation"] == 1
    assert item["background_policy_progress"] == 0
    assert item["background_policy_review_gaps"][0]["field_name"] == "control_b"
    assert item["expression_and_instruction_page_citation"] == 1
    assert item["expression_and_both_citations"] == 1
    assert item["instruction_review_cells"] == 4
    assert item["instruction_page_citation_before"] == 0
    assert item["instruction_page_citation"] == 1
    assert item["expression_without_citation"] == 1
    assert item["neither_expression_nor_citation"] == 1
    assert item["wrong_owner_instruction_spans"] == 1
    assert item["unresolved_line_refs"][0]["code"] == "ambiguous_parent_source_line"
    assert item["handcrafted_diff"]["flag_only"] is True

    path = write_form_completeness_report(report, root=tmp_path)
    assert path.name == "m20_s19_form_completeness.yaml"
    assert "handcrafted expression set" not in path.read_text(encoding="ascii").lower()
