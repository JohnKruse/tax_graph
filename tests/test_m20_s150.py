from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tax_graph.cli import explain_cell_command
from tax_graph.extract.assembly import FormulaAssemblyFinding, assemble_formula_plan
from tax_graph.extract.models import SourceDocumentInput
from tax_graph.extract.outline import CandidateSpan, OutlineNode


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m20
def test_assembly_resolves_recorded_spelled_form_operand(tmp_path: Path) -> None:
    document = SourceDocumentInput(
        document_id="form_1040_2025",
        kind="tax_form",
        year="2025",
        url="",
        text="",
        text_path=tmp_path / "form.txt",
    )
    node = OutlineNode(
        "root_line_1e",
        "line",
        "Taxable dependent care benefits from Form 2441, line 26",
        line_anchor="1e",
    )
    span = CandidateSpan(
        "span_form_1040_2025_1e",
        document.document_id,
        "source",
        "page 1, line 62",
        "Taxable dependent care benefits from Form 2441, line 26",
    )
    plan = {
        "operation": "SUM",
        "source_lines": [{"form": "Form 2441", "line": "26", "role": None}],
        "quote": "Taxable dependent care benefits from Form 2441, line 26",
    }
    line_index = {
        ("form_2441_2025", "26"): "form_2441_2025_root_line_26",
    }

    batch = assemble_formula_plan(
        document,
        node,
        plan,
        [span],
        root=ROOT,
        line_index=line_index,
    )

    assert batch.items("edges")[0].data["source"] == "form_2441_2025_root_line_26"
    assert batch.items("edges")[0].data["target"] == "form_1040_2025_root_line_1e"

    with pytest.raises(FormulaAssemblyFinding) as exc_info:
        assemble_formula_plan(
            document,
            node,
            plan,
            [span],
            root=ROOT,
            line_index={},
        )
    assert exc_info.value.finding["reason"] == (
        'unresolved_source_line: form="Form 2441" line="26" '
        "-> key ('form_2441_2025', '26') not in outline index; "
        "source line is not present in the deterministic outline index"
    )


@pytest.mark.m20
def test_explain_cell_reads_the_persisted_stack_without_extraction(tmp_path: Path, capsys) -> None:
    draft = tmp_path / "graph" / "2025" / "_drafts" / "form_1040_2025"
    draft.mkdir(parents=True)
    (draft / "outline.yaml").write_text(
        yaml.safe_dump(
            {
                "document_id": "form_1040_2025",
                "children": [
                    {
                        "outline_id": "root_line_1e",
                        "kind": "line",
                        "label": "Taxable dependent care benefits from Form 2441, line 26",
                        "line_anchor": "1e",
                        "page": 1,
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="ascii",
    )
    (draft / "micro_extraction.yaml").write_text(
        yaml.safe_dump(
            {
                "formula_cells": [
                    {
                        "target_cell_id": "form_1040_2025_root_line_1e",
                        "line_anchor": "1e",
                        "label": "Taxable dependent care benefits from Form 2441, line 26",
                        "status": "review_gap",
                        "review_gap": "source line is not present in the deterministic outline index",
                        "instruction_span_ids": ["span_instructions_1e"],
                        "response_kind": "computation",
                    }
                ],
                "findings": [
                    {
                        "code": "unresolved_source_line",
                        "target_cell_id": "form_1040_2025_root_line_1e",
                        "source_line": {"form": "Form 2441", "line": "26", "role": None},
                        "candidates": [],
                        "reason": "source line is not present in the deterministic outline index",
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="ascii",
    )
    (draft / "candidate_spans.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "span_id": "span_instructions_1e",
                    "document_id": "instructions_form_1040_2025",
                    "relationship": "instructions",
                    "locator": "page 24, lines 1128-1133",
                    "owner_document_id": "form_1040_2025",
                    "owner_lines": ["1e"],
                    "text": "## Line 1e\n\nEnter the total from Form 2441, line 26.",
                }
            ],
            sort_keys=False,
        ),
        encoding="ascii",
    )

    assert explain_cell_command(doc="form_1040_2025", line="1e", root=tmp_path) == 0
    output = capsys.readouterr().out
    assert "=== form-face ===" in output
    assert "=== instruction ===" in output
    assert "Enter the total from Form 2441, line 26." in output
    assert "=== model plan or outcome ===" in output
    assert "=== finding ===" in output
    assert "=== resolver ===" in output
    assert '"computed_key_text": "(\'form_2441_2025\', \'26\')"' in output
    assert '"found": false' in output
