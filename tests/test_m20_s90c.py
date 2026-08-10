"""M20-S90c regression tests for candidate graph stubs."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from tax_graph.extract.candidate import (
    _assert_candidate_operand_resolution,
    write_candidate_from_run,
)
from tax_graph.extract.cells import derive_cells


pytestmark = pytest.mark.m20


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)

    def structured_completion(self, **kwargs):
        del kwargs
        return self.responses.pop(0)


def _write_report(
    run: Path,
    document_id: str,
    rows: list[dict],
    *,
    line_anchor_count: int,
) -> None:
    payload = {
        "document_id": document_id,
        "year": "2025",
        "rows": len(rows),
        "rows_attempted": len(rows),
        "line_anchor_count": line_anchor_count,
        "row_status_counts": {
            "derived": len(rows),
            "repaired": 0,
            "gapped": 0,
            "errored": 0,
        },
        "rows_detail": rows,
        "denominator": {
            "line_anchor_count": line_anchor_count,
            "skipped": 0,
            "anchors": [{"anchor": row["line"]} for row in rows],
        },
        "validation": {
            "attempted": len(rows),
            "derived": len(rows),
            "repaired": 0,
            "gapped": 0,
            "errored": 0,
        },
    }
    path = run / f"m20_s90c_{document_id}_derive_cells_report.yaml"
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="ascii",
    )


def _external_row() -> dict:
    quote = "Attach Form 4684 and enter the amount from line 18 of that form."
    return {
        "line": "15",
        "label_after": "Loss from casualty or theft",
        "form_face_after": quote,
        "instruction_text": quote,
        "status": "derived",
        "expression": {
            "op": "COPY",
            "args": [{"form": "form_4684_2025", "line": "18"}],
        },
        "quote": quote,
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
            "label": quote,
            "node_type": "fact",
            "value_type": "currency",
            "required": "required",
            "status": "unresolved",
            "citation_refs": ["face_15"],
        }],
    }


def test_external_reference_writes_document_and_line_stubs_with_canonical_join(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    run = tmp_path / "run"
    output = tmp_path / "candidate"
    root.mkdir()
    run.mkdir()
    _write_report(run, "schedule_a_2025", [_external_row()], line_anchor_count=1)

    written = write_candidate_from_run(
        run,
        output,
        root=root,
        expected_documents=["schedule_a_2025"],
    )

    assert written == output
    stub_dir = output / "graph" / "2025" / "_drafts" / "form_4684_2025"
    stub_document = yaml.safe_load((stub_dir / "documents.yaml").read_text(encoding="ascii"))[0]
    stub_node = yaml.safe_load((stub_dir / "nodes.yaml").read_text(encoding="ascii"))[0]
    assert stub_document["document_id"] == "form_4684_2025"
    assert stub_document["status"] == "unresolved"
    assert "must be ingested or" in stub_document["stub_message"]
    assert stub_node["node_id"] == "form_4684_2025_root_line_18"
    assert stub_node["status"] == "unresolved"
    assert "line 18" in stub_node["stub_message"]

    source_edges = yaml.safe_load(
        (output / "graph" / "2025" / "_drafts" / "schedule_a_2025" / "edges.yaml").read_text(
            encoding="ascii"
        )
    )
    assert source_edges[0]["source"] == "form_4684_2025_root_line_18"
    lifecycle = yaml.safe_load((output / "stub_lifecycle.yaml").read_text(encoding="ascii"))
    assert lifecycle == [{
        "document_id": "form_4684_2025",
        "line": "18",
        "node_id": "form_4684_2025_root_line_18",
        "status": "unresolved",
        "message": "Form 4684, line 18 must be ingested or supplied by the caller before this value can be computed.",
    }]
    candidate = yaml.safe_load((output / "candidate.yaml").read_text(encoding="ascii"))
    assert candidate["graph_integrity"]["status"] == "ok"
    assert candidate["stub_documents"] == ["form_4684_2025"]

    node_schema = json.loads((Path(__file__).parents[1] / "schemas" / "node.schema.json").read_text(encoding="ascii"))
    document_schema = json.loads((Path(__file__).parents[1] / "schemas" / "document.schema.json").read_text(encoding="ascii"))
    jsonschema.Draft202012Validator(node_schema).validate(stub_node)
    jsonschema.Draft202012Validator(document_schema).validate(stub_document)


def test_column_external_reference_writes_column_stub_with_canonical_join(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    run = tmp_path / "run"
    output = tmp_path / "candidate"
    root.mkdir()
    run.mkdir()
    row = _external_row()
    row["expression"] = {
        "op": "COPY",
        "args": [{
            "form": "form_4255_2025",
            "line": "2a",
            "column": "l",
        }],
    }
    row["validation_warnings"] = [{
        "kind": "unresolved_external_reference",
        "message": "cross-form operand names document form_4255_2025 line 2a column l outside the document inventory",
        "hard": False,
    }]
    row["unresolved_external_nodes"] = [{
        "node_id": "form_4255_2025_root_line_2a_column_l",
        "document_id": "form_4255_2025",
        "line": "2a",
        "column": "l",
        "label": row["form_face_after"],
        "node_type": "fact",
        "value_type": "currency",
        "required": "required",
        "status": "unresolved",
        "citation_refs": ["face_15"],
    }]
    _write_report(run, "schedule_a_2025", [row], line_anchor_count=1)

    write_candidate_from_run(
        run,
        output,
        root=root,
        expected_documents=["schedule_a_2025"],
    )

    stub_dir = output / "graph" / "2025" / "_drafts" / "form_4255_2025"
    stub_document = yaml.safe_load((stub_dir / "documents.yaml").read_text(encoding="ascii"))[0]
    stub_node = yaml.safe_load((stub_dir / "nodes.yaml").read_text(encoding="ascii"))[0]
    assert stub_node["node_id"] == "form_4255_2025_root_line_2a_column_l"
    assert stub_node["line"] == "2a"
    assert stub_node["column"] == "l"
    assert "line 2a, column (l)" in stub_node["stub_message"]
    assert "line 2a, column (l)" in stub_document["stub_message"]
    lifecycle = yaml.safe_load((output / "stub_lifecycle.yaml").read_text(encoding="ascii"))
    assert lifecycle[0]["node_id"] == "form_4255_2025_root_line_2a_column_l"
    assert lifecycle[0]["column"] == "l"
    source_edges = yaml.safe_load(
        (output / "graph" / "2025" / "_drafts" / "schedule_a_2025" / "edges.yaml").read_text(
            encoding="ascii"
        )
    )
    assert source_edges[0]["source"] == "form_4255_2025_root_line_2a_column_l"
    candidate = yaml.safe_load((output / "candidate.yaml").read_text(encoding="ascii"))
    assert candidate["graph_integrity"]["dangling_node_ids"] == []


def test_inducted_document_marks_stub_ingested_and_writes_no_stub(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    run = tmp_path / "run"
    output = tmp_path / "candidate"
    root.mkdir()
    run.mkdir()
    _write_report(run, "schedule_a_2025", [_external_row()], line_anchor_count=1)
    _write_report(
        run,
        "form_4684_2025",
        [{
            "line": "18",
            "label_after": "Net casualty loss",
            "form_face_after": "Enter an amount.",
            "instruction_text": "Enter an amount.",
            "status": "derived",
            "expression": {"op": "COPY", "args": [{"const": 0}]},
            "quote": "Enter an amount.",
            "quote_span_id": "face_18",
            "validation_failures": [],
            "validation_warnings": [],
        }],
        line_anchor_count=1,
    )

    write_candidate_from_run(
        run,
        output,
        root=root,
        expected_documents=["schedule_a_2025", "form_4684_2025"],
    )

    assert not (output / "graph" / "2025" / "_drafts" / "form_4684_2025" / "documents.yaml").exists()
    lifecycle = yaml.safe_load((output / "stub_lifecycle.yaml").read_text(encoding="ascii"))
    assert lifecycle[0]["status"] == "ingested"
    assert lifecycle[0]["node_id"] == "form_4684_2025_root_line_18"
    candidate = yaml.safe_load((output / "candidate.yaml").read_text(encoding="ascii"))
    assert candidate["stub_documents"] == []
    assert candidate["graph_integrity"]["dangling_node_ids"] == []


def test_instructions_document_operand_is_named_and_never_becomes_stub() -> None:
    face = "See instructions Schedule D, line 13."
    row = {
        "form": "form_1040_2025",
        "line": "6b",
        "label": "Amount",
        "form_face_text": face,
        "instruction_text": face,
        "instruction_locator": "face_6b",
        "metadata": {
            "printed_lines": ["6b"],
            "evidence_spans": [{"span_id": "face_6b", "text": face}],
        },
    }
    response = {
        "expression": {
            "op": "COPY",
            "args": [{"form": "instructions_schedule_d_2025", "line": "13"}],
        },
        "quote": face,
    }
    result = derive_cells(
        [row],
        "line <<line>>",
        "secret",
        client=FakeClient([response, response]),
        reference_inventory={
            "document_ids": ["form_1040_2025"],
            "printed_lines": {"form_1040_2025": ["6b"]},
            "node_ids": [],
            "graph_nodes": [],
        },
    )

    assert result[0]["status"] == "error"
    assert result[0].get("unresolved_external_nodes") is None
    assert result[0]["validation_failures"][0]["kind"] == "instructions_document_operand"


def test_shared_node_id_allows_identical_identity_payloads_with_distinct_citations(tmp_path: Path) -> None:
    graph_root = tmp_path / "graph"
    shared = {
        "node_id": "taxpayer_2025_filing_status",
        "document_id": "taxpayer_2025_filing_status",
        "label": "Filing status",
        "node_type": "fact",
        "value_type": "enum",
        "required": "optional",
    }
    for document_id, citation in (("form_1040_2025", "face_1040"), ("form_6251_2025", "face_6251")):
        document_root = graph_root / document_id
        document_root.mkdir(parents=True)
        payload = {**shared, "citation_refs": [citation]}
        (document_root / "nodes.yaml").write_text(
            yaml.safe_dump([payload], sort_keys=False, allow_unicode=False),
            encoding="ascii",
        )
        (document_root / "edges.yaml").write_text("[]\n", encoding="ascii")

    result = _assert_candidate_operand_resolution(graph_root)

    assert result["status"] == "ok"
    assert result["node_count"] == 1


def test_shared_node_id_rejects_conflicting_identity_payloads(tmp_path: Path) -> None:
    graph_root = tmp_path / "graph"
    for document_id, label in (("form_1040_2025", "Filing status"), ("form_6251_2025", "Wrong fact")):
        document_root = graph_root / document_id
        document_root.mkdir(parents=True)
        (document_root / "nodes.yaml").write_text(
            yaml.safe_dump([{
                "node_id": "taxpayer_2025_filing_status",
                "document_id": "taxpayer_2025_filing_status",
                "label": label,
                "node_type": "fact",
                "value_type": "enum",
                "required": "optional",
            }], sort_keys=False, allow_unicode=False),
            encoding="ascii",
        )
        (document_root / "edges.yaml").write_text("[]\n", encoding="ascii")

    with pytest.raises(ValueError, match="conflicting node payloads: taxpayer_2025_filing_status"):
        _assert_candidate_operand_resolution(graph_root)


def test_missing_canonical_operand_becomes_a_line_stub_in_the_candidate(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    run = tmp_path / "run"
    output = tmp_path / "candidate"
    root.mkdir()
    run.mkdir()
    row = _external_row()
    row.pop("unresolved_external_nodes")
    _write_report(run, "schedule_a_2025", [row], line_anchor_count=1)

    write_candidate_from_run(
        run,
        output,
        root=root,
        expected_documents=["schedule_a_2025"],
    )

    stub_dir = output / "graph" / "2025" / "_drafts" / "form_4684_2025"
    stub_node = yaml.safe_load((stub_dir / "nodes.yaml").read_text(encoding="ascii"))[0]
    assert stub_node["node_id"] == "form_4684_2025_root_line_18"
    assert stub_node["status"] == "unresolved"
    candidate = yaml.safe_load((output / "candidate.yaml").read_text(encoding="ascii"))
    assert candidate["graph_integrity"]["status"] == "ok"
    assert candidate["stub_documents"] == ["form_4684_2025"]
