"""M20-S152 tests for the single core source and refusal gate."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pilot.core_refusal_gate import CANDIDATE_RULES, evaluate_core_refusals
from tax_graph.acquire.corpus import load_core_document_ids


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.m20


def test_manifest_has_no_second_core_definition() -> None:
    manifest = yaml.safe_load((ROOT / "config" / "manifest.yaml").read_text(encoding="ascii"))

    assert all("core" not in entry for entry in manifest["documents"])
    assert len(load_core_document_ids(root=ROOT)) == 22


def _write_project(root: Path) -> None:
    (root / "config").mkdir(parents=True)
    (root / "schemas").mkdir()
    (root / "output").mkdir()
    (root / "graph" / "2025" / "_drafts" / "form_core_2025").mkdir(parents=True)
    (root / "graph" / "2025" / "_drafts" / "form_other_2025").mkdir(parents=True)
    (root / "graph" / "2025").mkdir(exist_ok=True)
    (root / "schemas" / "manifest.schema.json").write_text(
        (ROOT / "schemas" / "manifest.schema.json").read_text(encoding="ascii"),
        encoding="ascii",
    )
    manifest = {
        "tax_year": 2025,
        "documents": [
            {
                "document_id": "form_core_2025",
                "kind": "tax_form",
                "ownership": "project-maintained",
                "url": "https://www.irs.gov/pub/irs-prior/fcore--2025.pdf",
            },
            {
                "document_id": "form_other_2025",
                "kind": "tax_form",
                "ownership": "review-cycle",
                "url": "https://www.irs.gov/pub/irs-prior/fother--2025.pdf",
            },
        ],
    }
    (root / "config" / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=False),
        encoding="ascii",
    )
    (root / "config" / "document_tiers.yaml").write_text(
        yaml.safe_dump(
            {
                "tax_year": 2025,
                "core_documents": ["form_core_2025"],
                "tiers": {
                    "T1": ["form_core_2025"],
                    "review-cycle": ["form_other_2025"],
                },
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="ascii",
    )


def test_written_rules_cover_each_candidate_and_name_the_surface() -> None:
    assert {rule.kind for rule in CANDIDATE_RULES} == {
        "derive_cell_status",
        "formula_review_gap",
        "not_derivable_outcome",
        "worksheet_refusal",
        "frontier_refusal",
    }
    assert all(rule.refusal and rule.surface for rule in CANDIDATE_RULES)


def test_gate_accounts_for_all_candidates_and_only_core_unsurfaced_blocks(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _write_project(root)

    (root / "output" / "m20_s26_form_core_2025_derive_cells_report.yaml").write_text(
        yaml.safe_dump(
            {
                "document_id": "form_core_2025",
                "rows_detail": [
                    {"line": "1", "status": "errored", "error": "missing operand"},
                    {"line": "2", "status": "skipped", "structural_skip_reason": "not a cell"},
                ],
            },
            sort_keys=False,
        ),
        encoding="ascii",
    )
    (root / "graph" / "2025" / "_drafts" / "form_core_2025" / "review_gaps.yaml").write_text(
        yaml.safe_dump(
            [{"line_anchor": "3", "status": "review_gap", "review_gap": "needs review"}],
            sort_keys=False,
        ),
        encoding="ascii",
    )
    (root / "graph" / "2025" / "_drafts" / "form_core_2025" / "micro_extraction.yaml").write_text(
        yaml.safe_dump(
            {"outcomes": [{"line_anchor": "4", "kind": "not_derivable", "reason": "packet is incomplete"}]},
            sort_keys=False,
        ),
        encoding="ascii",
    )
    (root / "graph" / "2025" / "_drafts" / "worksheet-discovery-core.yaml").write_text(
        yaml.safe_dump(
            {
                "source_document_id": "form_core_2025",
                "worksheets": [{"document_id": "form_other_2025", "status": "refused", "findings": [{"message": "blocked"}]}],
                "findings": [{"kind": "window_response_invalid", "message": "invalid window"}],
            },
            sort_keys=False,
        ),
        encoding="ascii",
    )
    (root / "graph" / "2025" / "frontier.yaml").write_text(
        yaml.safe_dump(
            {
                "frontiers": [
                    {"status": "unmodeled", "source": {"document_id": "form_core_2025"}, "target": {"line": "5"}},
                    {"status": "declared", "source": {"document_id": "form_core_2025"}, "target": {"line": "6"}},
                ],
            },
            sort_keys=False,
        ),
        encoding="ascii",
    )

    report = evaluate_core_refusals(root=root)

    assert report.ok
    assert len(report.candidates) == 8
    assert {item.kind for item in report.candidates} == {
        "derive_cell_status",
        "formula_review_gap",
        "not_derivable_outcome",
        "worksheet_refusal",
        "frontier_refusal",
    }
    assert report.core_unsurfaced == ()
    assert all(item.surfaced for item in report.candidates)


def test_core_unsurfaced_refusal_is_not_silenced(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _write_project(root)
    (root / "output" / "m20_s26_form_core_2025_derive_cells_report.yaml").write_text(
        "document_id: form_core_2025\nrows_detail:\n- line: 1\n  status: errored\n",
        encoding="ascii",
    )

    report = evaluate_core_refusals(root=root)

    assert report.ok is False
    assert len(report.core_unsurfaced) == 1
    assert report.core_unsurfaced[0].artifact.endswith("m20_s26_form_core_2025_derive_cells_report.yaml")
    assert "UNSURFACED" in report.format_report()
