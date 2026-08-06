"""M20-S64 tests for candidate regeneration and candidate review projection."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from tax_graph.extract.candidate import build_candidate_from_run, write_candidate_from_run
from tax_graph.extract.cells import CellFrame
from tax_graph.review_table import build_review_table


pytestmark = pytest.mark.m20


def _report(run_dir: Path) -> None:
    payload = {
        "document_id": "toy_2025",
        "year": "2025",
        "rows": 2,
        "rows_attempted": 2,
        "line_anchor_count": 3,
        "row_status_counts": {"derived": 1, "repaired": 0, "gapped": 0, "errored": 1, "skipped": 1},
        "rows_detail": [
            {
                "line": "1",
                "label_after": "Total amount",
                "form_face_after": "Add line 2.",
                "status": "derived",
                "expression": {"op": "COPY", "args": [{"line": "2"}]},
                "rendered": "copy(line 2)",
                "quote": "Add line 2.",
                "quote_span_id": "span_toy_line_1",
                "validation_failures": [],
                "validation_warnings": [],
            },
            {
                "line": "2",
                "label_after": "Input",
                "form_face_after": "Enter an amount.",
                "status": "error",
                "error": "ProviderError: unavailable",
                "expression": None,
                "validation_failures": [],
                "validation_warnings": [],
            },
        ],
        "denominator": {
            "line_anchor_count": 3,
            "skipped": 1,
            "skipped_by_reason": {"selector_no_formula_cue": 1},
            "anchors": [
                {"anchor": "1"},
                {"anchor": "2"},
                {"anchor": "3", "skip_reason": "selector_no_formula_cue"},
            ],
        },
        "validation": {"attempted": 2, "derived": 1, "repaired": 0, "gapped": 0, "errored": 1},
    }
    run_dir.mkdir(parents=True)
    (run_dir / "m20_s64_toy_2025_derive_cells_report.yaml").write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="ascii",
    )


def _graph(root: Path) -> None:
    graph = root / "graph" / "2025"
    (graph / "nodes").mkdir(parents=True)
    (graph / "edges").mkdir()
    (graph / "rules").mkdir()
    (graph / "citations").mkdir()
    (graph / "documents").mkdir()
    (graph / "field_maps").mkdir()
    (graph / "nodes" / "toy.yaml").write_text(
        yaml.safe_dump(
            [
                {"node_id": "toy_2025_root_line_1", "document_id": "toy_2025", "node_type": "computed"},
                {"node_id": "toy_2025_root_line_2", "document_id": "toy_2025", "node_type": "form_line"},
            ],
            sort_keys=False,
        ),
        encoding="ascii",
    )
    (graph / "rules" / "toy.yaml").write_text(
        "- rule_id: copy_currency_value\n  operation: COPY\n",
        encoding="ascii",
    )
    (graph / "edges" / "toy.yaml").write_text(
        "- edge_id: e_2_to_1\n  source: toy_2025_root_line_2\n  target: toy_2025_root_line_1\n  rule_id: copy_currency_value\n  role: source\n",
        encoding="ascii",
    )


def test_candidate_is_complete_evidence_and_diffs_live_graph(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    run = tmp_path / "run"
    output = tmp_path / "candidate"
    root.mkdir()
    _graph(root)
    _report(run)

    summary = build_candidate_from_run(run, root=root, expected_documents=["toy_2025"])

    assert summary["coverage"] == {
        "printed_anchors": 3,
        "selected": 2,
        "attempted": 2,
        "derived": 1,
        "repaired": 0,
        "gapped": 0,
        "errored": 1,
        "skipped": 1,
        "resolved": 1,
        "skipped_by_reason": {"selector_no_formula_cue": 1},
        "documents": 1,
    }
    diff = summary["diff"]
    assert diff["in_both"] == ["toy_2025_root_line_1"]
    assert diff["candidate_only"] == []
    assert diff["handcrafted_only"] == ["toy_2025_root_line_2"]
    assert diff["expression_disagreements"] == []

    written = write_candidate_from_run(
        run,
        output,
        root=root,
        expected_documents=["toy_2025"],
    )
    assert written == output
    assert (output / "candidate.yaml").is_file()
    assert (output / "graph" / "2025" / "_drafts" / "toy_2025" / "rows.yaml").is_file()
    rows = yaml.safe_load(
        (output / "graph" / "2025" / "_drafts" / "toy_2025" / "rows.yaml").read_text(encoding="ascii")
    )
    by_line = {row["line"]: row for row in rows}
    assert by_line["1"]["candidate_status"] == "derived"
    assert by_line["2"]["candidate_status"] == "review_gap"
    assert by_line["3"]["candidate_status"] == "skipped"
    assert by_line["2"]["findings"][0]["kind"] == "row_error"


def test_candidate_writer_rejects_published_graph_path(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    run = tmp_path / "run"
    root.mkdir()
    _report(run)

    with pytest.raises(ValueError, match="outside repository root"):
        write_candidate_from_run(
            run,
            root / "graph" / "2025" / "_drafts" / "candidate",
            root=root,
            expected_documents=["toy_2025"],
        )


def test_review_table_reads_candidate_rows_without_live_graph_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = tmp_path / "candidate"
    draft = candidate / "graph" / "2025" / "_drafts" / "toy_2025"
    draft.mkdir(parents=True)
    (draft / "rows.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "line": "1",
                    "candidate_status": "derived",
                    "expression": {"op": "COPY", "args": [{"line": "2"}]},
                    "findings": [],
                    "warnings": [],
                }
            ],
            sort_keys=False,
        ),
        encoding="ascii",
    )
    frame = CellFrame.from_rows(
        [
            {
                "form": "toy_2025",
                "line": "1",
                "label": "Total amount",
                "form_face_text": "Add line 2.",
                "instruction_text": "",
                "instruction_locator": "",
            }
        ]
    )
    monkeypatch.setattr(
        "tax_graph.review_table.load_document_input",
        lambda *args, **kwargs: SimpleNamespace(document_id="toy_2025", text=""),
    )
    monkeypatch.setattr("tax_graph.review_table.build_cell_frame_from_document", lambda document: frame)

    payload = build_review_table(tmp_path, 2025, "toy_2025", candidate_root=candidate, all_rows=True)

    assert payload["rows"][0].status == "derived"
    assert payload["rows"][0].expression["op"] == "COPY"
