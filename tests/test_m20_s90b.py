"""M20-S90b regression tests for honest external-reference outcomes."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tax_graph.extract.candidate import build_candidate_from_run, write_candidate_from_run
from tax_graph.extract.cells import CellFrame, derive_cells, validate_cell_output


pytestmark = pytest.mark.m20


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def structured_completion(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def _external_row() -> dict:
    return {
        "form": "schedule_a_2025",
        "line": "15",
        "label": "Loss from casualty or theft",
        "form_face_text": "Attach Form 4684 and enter the amount from line 18 of that form.",
        "instruction_text": "Attach Form 4684 and enter the amount from line 18 of that form.",
        "instruction_locator": "face_15",
        "metadata": {
            "printed_lines": ["15"],
            "evidence_spans": [{
                "span_id": "face_15",
                "text": "Attach Form 4684 and enter the amount from line 18 of that form.",
            }],
        },
    }


def test_evidence_backed_external_reference_is_nonfatal_and_does_not_repair() -> None:
    client = FakeClient({
        "expression": {"op": "COPY", "args": [{"form": "form_4684_2025", "line": "18"}]},
        "quote": "Attach Form 4684 and enter the amount from line 18 of that form.",
    })

    result = derive_cells(
        CellFrame.from_rows([_external_row()]),
        "line <<line>>",
        "secret",
        client=client,
        reference_inventory={
            "document_ids": ["schedule_a_2025"],
            "printed_lines": {"schedule_a_2025": ["15"]},
            "node_ids": [],
            "graph_nodes": [],
        },
    )

    row = result.rows[0]
    assert row.status == "derived"
    assert len(client.calls) == 1
    assert result.validation_report["validator_failures_by_kind"] == {}
    assert result.validation_report["validator_warnings_by_kind"] == {
        "unresolved_external_reference": 1,
    }
    assert row.metadata["unresolved_external_nodes"][0]["document_id"] == "form_4684_2025"
    assert row.metadata["unresolved_external_nodes"][0]["line"] == "18"


def test_document_only_external_evidence_is_enough_to_mint_a_stub() -> None:
    row = _external_row()
    row["form_face_text"] = "Attach Form 4684 and enter the amount from that form."
    row["instruction_text"] = row["form_face_text"]
    row["metadata"]["evidence_spans"] = [{
        "span_id": "face_15",
        "text": row["form_face_text"],
    }]
    client = FakeClient({
        "expression": {"op": "COPY", "args": [{"form": "form_4684_2025", "line": "18"}]},
        "quote": row["form_face_text"],
    })

    result = derive_cells(
        CellFrame.from_rows([row]),
        "line <<line>>",
        "secret",
        client=client,
        reference_inventory={
            "document_ids": ["schedule_a_2025"],
            "printed_lines": {"schedule_a_2025": ["15"]},
            "node_ids": [],
            "graph_nodes": [],
        },
    )

    assert result.rows[0].status == "derived"
    assert result.validation_report["validator_failures_by_kind"] == {}
    assert result.validation_report["validator_warnings_by_kind"][
        "unresolved_external_reference"
    ] == 1
    assert result.validation_report["validator_warnings_by_kind"][
        "operand_not_in_quote"
    ] == 1
    assert result.rows[0].metadata["unresolved_external_nodes"][0]["line"] == "18"


def test_unsourced_unknown_document_is_still_a_hard_failure() -> None:
    row = CellFrame.from_rows([{
        "form": "form_1040_2025",
        "line": "22",
        "label": "Amount",
        "form_face_text": "Enter the amount from line 21.",
        "instruction_text": "Enter the amount from line 21.",
        "instruction_locator": "face_22",
    }]).rows[0]

    hard, warnings = validate_cell_output(
        row,
        {"op": "COPY", "args": [{"form": "form_1040_nr_2025", "line": "15"}]},
        row.form_face_text,
        reference_inventory={
            "document_ids": ["form_1040_2025"],
            "printed_lines": {"form_1040_2025": ["22"]},
            "node_ids": [],
        },
    )

    assert [issue.kind for issue in hard] == ["operand_document_not_found"]
    assert all(issue.kind != "unresolved_external_reference" for issue in warnings)


@pytest.mark.parametrize(
    "face",
    (
        "Amount from Form W-2, box 1",
        "Amount from Form(s) 1099-NEC, box 1",
        "Amount from Schedule K-1 (Form 1041), box 12, code A",
    ),
)
def test_information_returns_are_filer_inputs(face: str) -> None:
    row = CellFrame.from_rows([{
        "form": "form_6251_2025",
        "line": "2j",
        "label": "Information return amount",
        "form_face_text": face,
        "instruction_text": "",
        "instruction_locator": "face_2j",
    }]).rows[0]

    hard, warnings = validate_cell_output(
        row,
        {"op": "REQUIRE_INPUT", "args": [{"line": "2j"}]},
        face,
    )

    assert hard == ()
    assert warnings == ()


def test_candidate_review_row_exposes_external_reference_as_finding(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    run = tmp_path / "run"
    root.mkdir()
    run.mkdir()
    report = {
        "document_id": "schedule_a_2025",
        "year": "2025",
        "rows": 1,
        "rows_attempted": 1,
        "line_anchor_count": 1,
        "row_status_counts": {"derived": 1, "repaired": 0, "gapped": 0, "errored": 0},
        "rows_detail": [{
            "line": "15",
            "label_after": "Loss from casualty or theft",
            "form_face_after": _external_row()["form_face_text"],
            "status": "derived",
            "expression": {"op": "COPY", "args": [{"form": "form_4684_2025", "line": "18"}]},
            "quote": _external_row()["form_face_text"],
            "quote_span_id": "face_15",
            "validation_failures": [],
            "validation_warnings": [{
                "kind": "unresolved_external_reference",
                "message": "cross-form operand names document form_4684_2025 line 18 outside the document inventory",
                "hard": False,
            }],
            "unresolved_external_nodes": [{
                "node_id": "form_4684_2025_root_line_18",
                "document_id": "form_4684_2025",
                "line": "18",
                "status": "unresolved",
            }],
        }],
        "denominator": {"line_anchor_count": 1, "skipped": 0, "anchors": [{"anchor": "15"}]},
        "validation": {"attempted": 1, "repaired": 0, "gapped": 0, "errored": 0},
    }
    (run / "schedule_a_2025_derive_cells_report.yaml").write_text(
        yaml.safe_dump(report, sort_keys=False, allow_unicode=False),
        encoding="ascii",
    )

    candidate = build_candidate_from_run(
        run,
        root=root,
        expected_documents=["schedule_a_2025"],
    )

    assert candidate["documents"] == ["schedule_a_2025", "form_4684_2025"]
    assert candidate["source_documents"] == ["schedule_a_2025"]
    assert candidate["stub_documents"] == ["form_4684_2025"]
    output = tmp_path / "candidate"
    write_candidate_from_run(
        run,
        output,
        root=root,
        expected_documents=["schedule_a_2025"],
    )
    rows = yaml.safe_load(
        (output / "graph" / "2025" / "_drafts" / "schedule_a_2025" / "rows.yaml").read_text(
            encoding="ascii"
        )
    )
    row = rows[0]
    assert row["candidate_status"] == "derived"
    assert row["unresolved_external_nodes"][0]["document_id"] == "form_4684_2025"
    assert any(
        item["kind"] == "unresolved_external_reference"
        for item in row["findings"]
    )
    assert row["warnings"][0]["kind"] == "unresolved_external_reference"
