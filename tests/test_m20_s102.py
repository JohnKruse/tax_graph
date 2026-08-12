"""M20-S102 regression coverage for prior-year source references."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import jsonschema
import yaml

from pilot.maintenance_report import build_refusal_report
from tax_graph.extract.candidate import (
    _stub_document,
    build_prior_year_target_report,
    write_candidate_from_run,
)
from tax_graph.extract.cells import (
    CellFrame,
    _external_form_is_named,
    derive_cells,
    validate_cell_output,
)


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def structured_completion(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def _row(*, line: str, face: str, instruction: str = "") -> dict:
    return {
        "form": "simplified_method_worksheet_2025",
        "line": line,
        "label": "Worksheet amount",
        "form_face_text": face,
        "instruction_text": instruction,
        "instruction_locator": "face_" + line,
        "metadata": {
            "printed_lines": [line],
            "evidence_spans": [
                {"span_id": "face_" + line, "text": face},
                *([{"span_id": "instruction_" + line, "text": instruction}] if instruction else []),
            ],
        },
    }


def _inventory() -> dict:
    return {
        "document_ids": ["simplified_method_worksheet_2025"],
        "printed_lines": {"simplified_method_worksheet_2025": ["2", "6"]},
        "node_ids": [],
        "graph_nodes": [],
    }


def test_prior_year_reference_is_a_nonfatal_source_backed_warning() -> None:
    row = _row(
        line="6",
        face="Enter the amount recovered tax free in years after 1986.",
        instruction=(
            "If you completed this worksheet last year, enter the amount from line 10 "
            "of last year's worksheet."
        ),
    )
    result = derive_cells(
        CellFrame.from_rows([row]),
        "line <<line>>",
        "secret",
        client=FakeClient([{
            "expression": {
                "op": "COPY",
                "args": [{"form": "simplified_method_worksheet_2024", "line": "10"}],
            },
            "quote": row["instruction_text"],
        }]),
        reference_inventory=_inventory(),
    )

    assert result.rows[0].status == "derived"
    assert len(result.rows[0].metadata["unresolved_external_nodes"]) == 1
    warning_kinds = [item["kind"] for item in result.rows[0].metadata["validation_warnings"]]
    assert "prior_year_reference" in warning_kinds
    assert result.validation_report["repaired"] == 0


def test_line_2_year_shift_without_prior_year_cue_stays_hard_missing_document() -> None:
    row = _row(
        line="2",
        face="Enter your cost in the plan at the annuity starting date.",
    )
    hard, warnings = validate_cell_output(
        CellFrame.from_rows([row]).rows[0],
        {
            "op": "COPY",
            "args": [{"form": "simplified_method_worksheet_2024", "line": "10"}],
        },
        row["form_face_text"],
        reference_inventory=_inventory(),
    )

    assert [issue.kind for issue in hard] == ["operand_document_not_found"]
    assert all(issue.kind != "prior_year_reference" for issue in warnings)


def test_year_shift_is_not_hidden_by_form_name_matching() -> None:
    assert not _external_form_is_named("Enter the amount from Form 1040, line 15.", "form_1040_2024")
    assert _external_form_is_named("Enter the amount from 2024 Form 1040, line 15.", "form_1040_2024")


def _prior_year_row(line: str, referenced_line: str) -> dict:
    return {
        "line": line,
        "label_after": "Carryforward",
        "form_face_after": "Carryover from prior year.",
        "instruction_text": "Carryover from prior year.",
        "status": "derived",
        "expression": {
            "op": "COPY",
            "args": [{"form": "schedule_d_2024", "line": referenced_line}],
        },
        "quote": "Carryover from prior year.",
        "quote_span_id": "face_" + line,
        "validation_failures": [],
        "validation_warnings": [{
            "kind": "prior_year_reference",
            "message": "schedule_d_2024 is the prior-year document for this source row",
            "hard": False,
        }],
        "unresolved_external_nodes": [{
            "node_id": "schedule_d_2024_root_line_" + referenced_line,
            "document_id": "schedule_d_2024",
            "line": referenced_line,
            "label": "Carryover from prior year.",
            "node_type": "fact",
            "value_type": "currency",
            "required": "required",
            "status": "unresolved",
            "citation_refs": ["face_" + line],
        }],
    }


def _write_run(run: Path) -> None:
    run.mkdir()
    rows = [_prior_year_row("6", "7"), _prior_year_row("14", "15")]
    payload = {
        "document_id": "schedule_d_2025",
        "year": "2025",
        "rows": len(rows),
        "rows_attempted": len(rows),
        "line_anchor_count": len(rows),
        "row_status_counts": {"derived": len(rows), "repaired": 0, "gapped": 0, "errored": 0},
        "rows_detail": rows,
        "denominator": {"anchors": [{"anchor": row["line"]} for row in rows]},
        "validation": {"attempted": len(rows), "derived": len(rows), "repaired": 0, "gapped": 0, "errored": 0},
    }
    (run / "m20_s26_schedule_d_2025_derive_cells_report.yaml").write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="ascii",
    )


def test_prior_year_reference_is_partitioned_from_refusals_and_reported_per_document(tmp_path: Path) -> None:
    run = tmp_path / "run"
    _write_run(run)

    report = build_refusal_report(run, root=ROOT)

    assert report.records == ()
    assert report.prior_year_reference_counts == {"schedule_d_2025": 2}
    assert report.as_dict()["counts"]["prior_year_references"] == 2
    assert "prior-year references: 2" in report.format_report()
    assert "schedule_d_2025: 2" in report.format_report()


def test_prior_year_stub_uses_document_year_and_candidate_target_report(tmp_path: Path) -> None:
    stub = _stub_document(
        "form_1040_2024",
        "2025",
        [{"line": "15", "node_id": "form_1040_2024_root_line_15"}],
    )
    assert stub["tax_year"] == 2024
    assert "2024" in stub["title"]
    assert "2024" in stub["stub_message"]

    root = tmp_path / "repo"
    run = tmp_path / "run"
    output = tmp_path / "candidate"
    root.mkdir()
    _write_run(run)
    write_candidate_from_run(
        run,
        output,
        root=root,
        expected_documents=["schedule_d_2025"],
    )
    documents = yaml.safe_load(
        (output / "graph" / "2025" / "_drafts" / "schedule_d_2024" / "documents.yaml").read_text(
            encoding="ascii"
        )
    )
    assert documents[0]["tax_year"] == 2024
    assert "2024" in documents[0]["title"]
    document_schema = json.loads(
        (ROOT / "schemas" / "document.schema.json").read_text(encoding="ascii")
    )
    jsonschema.Draft202012Validator(document_schema).validate(documents[0])
    candidate = yaml.safe_load((output / "candidate.yaml").read_text(encoding="ascii"))
    assert candidate["prior_year_reference_report"]["count"] == 2
    assert (output / "prior_year_reference_report.yaml").is_file()

    target_report = build_prior_year_target_report(run)
    assert target_report["by_document"] == {"schedule_d_2025": 2}
    assert target_report["hardcoded_capital_loss_targets"] == [
        "schedule_d_2025_line_14_lt_carryover",
        "schedule_d_2025_line_6_st_carryover",
    ]
    assert target_report["implied_capital_loss_targets"] == [
        "schedule_d_2025_line_14_lt_carryover",
        "schedule_d_2025_line_6_st_carryover",
    ]
    assert target_report["capital_loss_targets_match"] is True
