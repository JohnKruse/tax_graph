"""M20-S94 tests for broken-only derivation and complete merged reports."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import yaml

import pytest

from experiments.derive_cells_s25 import (
    _frame_for_process,
    _merge_row_details,
    _report_status_counts,
    run_documents,
    run_real_document,
)
from tax_graph.extract.cells import CellFrame, CellRecord


pytestmark = pytest.mark.m20


def _frame() -> CellFrame:
    return CellFrame([
        CellRecord(form="form_test_2025", line="1", label="one", form_face_text="One"),
        CellRecord(form="form_test_2025", line="2", label="two", form_face_text="Two"),
        CellRecord(form="form_test_2025", line="3", label="three", form_face_text="Three"),
        CellRecord(form="form_test_2025", line="4", label="four", form_face_text="Four"),
    ])


def _prior() -> dict[str, object]:
    return {
        "document_id": "form_test_2025",
        "rows_detail": [
            {
                "line": "1",
                "status": "derived",
                "label_before": "one",
                "form_face_before": "One",
                "instruction_text": "",
                "instruction_locator": "",
                "expression": {"op": "COPY"},
            },
            {
                "line": "2",
                "status": "repaired",
                "label_before": "two",
                "form_face_before": "Two",
                "instruction_text": "",
                "instruction_locator": "",
                "expression": {"op": "COPY"},
            },
            {
                "line": "3",
                "status": "error",
                "label_before": "three",
                "form_face_before": "Three",
                "instruction_text": "",
                "instruction_locator": "",
                "error": "payload",
            },
        ],
    }


def _duplicate_frame() -> CellFrame:
    return CellFrame([
        CellRecord(form="form_test_2025", line="1", label="first", form_face_text="First"),
        CellRecord(form="form_test_2025", line="1", label="second", form_face_text="Second"),
    ])


def test_all_is_the_default_and_processes_every_row() -> None:
    frame = _frame()

    work, prior_rows = _frame_for_process(frame, process="all", prior_report=None)

    assert [row.line for row in work.rows] == ["1", "2", "3", "4"]
    assert prior_rows == {}


def test_broken_process_selects_only_rows_without_a_successful_prior_answer() -> None:
    work, prior_rows = _frame_for_process(frame := _frame(), process="broken", prior_report=_prior())

    assert [row.line for row in work.rows] == ["3", "4"]
    assert sorted(prior_rows) == ["1", "2", "3"]
    assert frame.rows[0].line == "1"


def test_broken_process_requires_a_prior_report() -> None:
    with pytest.raises(ValueError, match="prior derivation report"):
        _frame_for_process(_frame(), process="broken", prior_report=None)


def test_broken_process_rederives_a_success_when_source_packet_changed() -> None:
    prior = _prior()
    prior["rows_detail"][0]["form_face_before"] = "Changed"

    work, _ = _frame_for_process(_frame(), process="broken", prior_report=prior)

    assert [row.line for row in work.rows] == ["1", "3", "4"]


def test_broken_process_rejects_malformed_prior_rows() -> None:
    with pytest.raises(ValueError, match="non-object row"):
        _frame_for_process(
            _frame(),
            process="broken",
            prior_report={"document_id": "form_test_2025", "rows_detail": ["bad"]},
        )


def test_repeated_printed_lines_are_rederived_as_one_flow_group() -> None:
    prior = {
        "document_id": "form_test_2025",
        "rows_detail": [
            {
                "line": "1",
                "status": "derived",
                "label_before": "first",
                "form_face_before": "First",
                "instruction_text": "",
                "instruction_locator": "",
            },
            {
                "line": "1",
                "status": "derived",
                "label_before": "second",
                "form_face_before": "Second",
                "instruction_text": "",
                "instruction_locator": "",
            },
        ],
    }

    work, prior_rows = _frame_for_process(
        _duplicate_frame(), process="broken", prior_report=prior
    )
    merged = _merge_row_details(
        _duplicate_frame(),
        [{"line": "1", "status": "error"}, {"line": "1", "status": "error"}],
        prior_rows,
    )

    assert [row.line for row in work.rows] == ["1", "1"]
    assert [row["status"] for row in merged] == ["error", "error"]


def test_merge_keeps_all_current_rows_and_carries_only_prior_successes() -> None:
    current = [
        {"line": "3", "status": "repaired", "expression": {"op": "COPY"}},
        {"line": "4", "status": "error", "error": "payload"},
    ]

    merged = _merge_row_details(
        _frame(),
        current,
        {
            "1": {
                "line": "1",
                "status": "derived",
                "label_before": "one",
                "form_face_before": "One",
                "instruction_text": "",
                "instruction_locator": "",
                "expression": {"op": "OLD"},
            },
            "2": {
                "line": "2",
                "status": "repaired",
                "label_before": "two",
                "form_face_before": "Two",
                "instruction_text": "",
                "instruction_locator": "",
                "expression": {"op": "OLD"},
            },
            "3": {"line": "3", "status": "error"},
        },
    )

    assert [row["line"] for row in merged] == ["1", "2", "3", "4"]
    assert [row["status"] for row in merged] == ["derived", "repaired", "repaired", "error"]
    assert merged[0]["expression"] == {"op": "OLD"}


def test_merge_fails_closed_when_a_broken_result_drops_a_row() -> None:
    with pytest.raises(ValueError, match="missing row for line 4"):
        _merge_row_details(
            _frame(),
            [
                {"line": "1", "status": "error"},
                {"line": "2", "status": "error"},
                {"line": "3", "status": "error"},
            ],
            {},
        )


def test_status_counts_normalize_error_without_losing_raw_status() -> None:
    normalized, raw = _report_status_counts([
        {"status": "derived"},
        {"status": "repaired"},
        {"status": "gapped"},
        {"status": "error"},
        {"status": "skipped"},
    ])

    assert normalized == {
        "derived": 1,
        "repaired": 1,
        "gapped": 1,
        "errored": 1,
        "skipped": 1,
    }
    assert raw == {
        "derived": 1,
        "error": 1,
        "gapped": 1,
        "repaired": 1,
        "skipped": 1,
    }


def test_run_documents_default_records_all_mode(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output = tmp_path / "output"
    monkeypatch.setattr(
        "experiments.derive_cells_s25.persist_instruction_frame",
        lambda **_: (tmp_path / "frame.yaml", tmp_path / "coverage.yaml"),
    )
    seen: list[dict[str, object]] = []

    def fake_run(**kwargs: object) -> dict[str, object]:
        seen.append(kwargs)
        return {
            "document_id": "form_test_2025",
            "process_mode": kwargs["process"],
            "rows_attempted": 1,
            "row_status_counts": {"derived": 1, "repaired": 0, "gapped": 0, "errored": 0, "skipped": 0},
            "outline_node_count": 1,
            "line_anchor_count": 1,
            "reference_inventory": {},
            "unresolved_external_node_count": 0,
            "unresolved_external_nodes": [],
            "validation": {"validator_failures_by_kind": {}},
            "denominator": {"status": "complete"},
        }

    monkeypatch.setattr("experiments.derive_cells_s25.run_real_document", fake_run)
    reports = run_documents(
        root=tmp_path / "repo",
        year="2025",
        document_ids=["form_test_2025"],
        output_dir=output,
    )

    assert seen[0]["process"] == "all"
    assert seen[0]["prior_run_dir"] is None
    assert reports[0]["status"] == "complete"


def test_real_broken_run_writes_a_complete_merged_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    prior_dir = tmp_path / "prior"
    output_dir = tmp_path / "output"
    prior_dir.mkdir()
    (prior_dir / "m20_s26_form_test_2025_derive_cells_report.yaml").write_text(
        yaml.safe_dump(_prior()),
        encoding="ascii",
    )
    frame = _frame()
    seen_lines: list[str] = []

    monkeypatch.setattr(
        "experiments.derive_cells_s25.load_config",
        lambda **_: {},
    )
    monkeypatch.setattr(
        "experiments.derive_cells_s25.load_document_input",
        lambda *args, **kwargs: SimpleNamespace(document_id="form_test_2025"),
    )
    monkeypatch.setattr(
        "experiments.derive_cells_s25.build_outline_tree",
        lambda *_: SimpleNamespace(children=[]),
    )
    monkeypatch.setattr(
        "experiments.derive_cells_s25._flatten_outline_nodes",
        lambda *_: [],
    )
    monkeypatch.setattr(
        "experiments.derive_cells_s25.build_derivation_denominator",
        lambda *_args, **_kwargs: {"skipped": 0},
    )
    monkeypatch.setattr(
        "experiments.derive_cells_s25.build_cell_frame_from_document",
        lambda *_: frame,
    )
    monkeypatch.setattr("experiments.derive_cells_s25.build_llm_client", lambda *_: object())
    monkeypatch.setattr("experiments.derive_cells_s25.load_cell_prompt", lambda *_args, **_kwargs: "prompt")
    monkeypatch.setattr("experiments.derive_cells_s25.load_graph", lambda *_: object())
    monkeypatch.setattr("experiments.derive_cells_s25.load_manifest", lambda **_: object())
    monkeypatch.setattr(
        "experiments.derive_cells_s25.build_reference_inventory",
        lambda *_args, **_kwargs: {"graph_nodes": []},
    )
    monkeypatch.setattr("experiments.derive_cells_s25.resolve_llm_model", lambda *_: "model")
    monkeypatch.setattr("experiments.derive_cells_s25.resolve_llm_seed", lambda *_: None)
    monkeypatch.setattr("experiments.derive_cells_s25._config_temperature", lambda *_: None)

    def fake_derive(work: CellFrame, *args: object, **kwargs: object) -> CellFrame:
        seen_lines.extend(row.line for row in work.rows)
        return CellFrame([
            CellRecord(
                form="form_test_2025",
                line="3",
                label="three",
                form_face_text="Three",
                status="repaired",
                expression={"op": "COPY"},
            ),
            CellRecord(
                form="form_test_2025",
                line="4",
                label="four",
                form_face_text="Four",
                status="error",
                error="payload",
            ),
        ], validation={"attempted": 2, "validator_failures_by_kind": {}})

    monkeypatch.setattr("experiments.derive_cells_s25.derive_cells", fake_derive)
    report = run_real_document(
        root=root,
        year="2025",
        document_id="form_test_2025",
        output_dir=output_dir,
        process="broken",
        prior_run_dir=prior_dir,
    )

    assert seen_lines == ["3", "4"]
    assert report["process_mode"] == "broken"
    assert report["rows"] == 4
    assert [row["status"] for row in report["rows_detail"]] == [
        "derived", "repaired", "repaired", "error",
    ]
    assert all(row["source_fingerprint"] for row in report["rows_detail"])
    assert report["row_status_counts"] == {
        "derived": 1,
        "repaired": 2,
        "gapped": 0,
        "errored": 1,
        "skipped": 0,
    }
    persisted = yaml.safe_load(
        (output_dir / "m20_s26_form_test_2025_derive_cells_report.yaml").read_text(encoding="ascii")
    )
    assert persisted["process_mode"] == "broken"
