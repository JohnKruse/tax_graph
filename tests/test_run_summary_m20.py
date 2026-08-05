"""M20-S63 tests for the provider-free derivation run summary."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tax_graph.extract.run_summary import (
    build_run_summary,
    render_run_summary_markdown,
    write_run_summary,
)
from tax_graph.cli import summarize_runs_command as cli_summarize_runs_command


pytestmark = pytest.mark.m20


def _row(line: str, *, status: str = "derived", expression: dict | None = None, error: str | None = None) -> dict:
    row = {
        "line": line,
        "status": status,
        "expression": expression or {"op": "COPY", "args": [{"line": "1"}]},
        "rendered": "line 1",
        "validation_failures": [],
        "validation_warnings": [],
        "dropped_instruction_sections": [],
        "unresolved_external_nodes": [],
    }
    if error:
        row["error"] = error
        row["expression"] = None
        row["rendered"] = None
    return row


def _write_report(
    run_dir: Path,
    document_id: str,
    *,
    derived: int,
    attempted: int,
    expression_text: str = "line 1",
    empty: bool = False,
    error_lines: tuple[str, ...] = (),
    warning_line: str | None = None,
) -> None:
    rows = []
    for index in range(1, attempted + 1):
        line = str(index)
        if line in error_lines:
            rows.append(_row(line, status="error", error="ProviderError: failed"))
        else:
            rows.append(
                _row(
                    line,
                    expression={"op": "COPY", "args": [{"line": expression_text}]}
                    if line == "1"
                    else {"op": "COPY", "args": [{"line": "1"}]},
                )
            )
            rows[-1]["rendered"] = expression_text if line == "1" else "line 1"
            if line == warning_line:
                rows[-1]["validation_warnings"] = [
                    {"kind": "unmapped_operation", "message": "operation needs projection"}
                ]
    if empty:
        rows = []
        attempted = 0
        derived = 0
    error_count = len(error_lines)
    payload = {
        "document_id": document_id,
        "year": "2025",
        "rows": len(rows),
        "rows_attempted": attempted,
        "outline_node_count": len(rows),
        "line_anchor_count": len(rows),
        "row_status_counts": {
            "derived": derived,
            "repaired": 0,
            "gapped": 0,
            "errored": error_count,
        },
        "rows_detail": rows,
        "validation": {
            "attempted": attempted,
            "repaired": 0,
            "gapped": 0,
            "errored": error_count,
        },
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"{document_id}_derive_cells_report.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="ascii")


def test_summary_uses_three_run_band_and_shows_expression_renderings(tmp_path: Path) -> None:
    runs = [tmp_path / name for name in ("r1", "r2", "r3", "r4")]
    _write_report(runs[0], "form_2441_2025", derived=18, attempted=20, expression_text="line 2", error_lines=("19", "20"))
    _write_report(runs[1], "form_2441_2025", derived=20, attempted=20, expression_text="line 2")
    _write_report(runs[2], "form_2441_2025", derived=18, attempted=20, expression_text="line 2", error_lines=("19", "20"))
    _write_report(
        runs[3],
        "form_2441_2025",
        derived=19,
        attempted=20,
        expression_text="line 2 + line 3",
        error_lines=("19",),
        warning_line="1",
    )

    summary = build_run_summary(runs)
    item = summary["documents"]["form_2441_2025"]

    assert item["movement"] == "in_band_noise"
    assert item["band"]["derived"]["min"] == 18
    assert item["band"]["derived"]["max"] == 20
    assert item["delta"]["derived"]["delta"] == 1
    assert item["derived_over_attempted"]["current"] == pytest.approx(0.95)
    changes = {change["line"]: change for change in item["expression_changes"]}
    assert changes["1"] == {
        "line": "1",
        "attention": False,
        "previous": "line 2",
        "current": "line 2 + line 3",
        "previous_status": "derived",
        "current_status": "derived",
    }
    assert changes["20"]["previous"] is None
    assert changes["20"]["current"] == "line 1"
    assert [finding["line"] for finding in item["findings"]["appeared"]] == ["1"]
    assert [finding["line"] for finding in item["findings"]["cleared"]] == ["20"]

    markdown = render_run_summary_markdown(summary)
    assert "in_band_noise" in markdown
    assert "line 2 + line 3" in markdown
    assert "This is an evidence diff, not a tax-correctness verdict." in markdown


def test_summary_flags_movement_outside_band(tmp_path: Path) -> None:
    runs = [tmp_path / name for name in ("r1", "r2", "r3", "r4")]
    for run, derived in zip(runs, (18, 20, 18, 22)):
        _write_report(run, "form_2441_2025", derived=derived, attempted=derived)

    summary = build_run_summary(runs)
    item = summary["documents"]["form_2441_2025"]

    assert item["movement"] == "outside_band"
    assert item["outside_band_metrics"] == ["derived", "attempted", "resolved"]
    assert summary["attention_documents"] == ["form_2441_2025"]


def test_empty_and_missing_expected_documents_are_explicit(tmp_path: Path) -> None:
    run = tmp_path / "run"
    _write_report(run, "empty_doc_2025", derived=0, attempted=0, empty=True)

    summary = build_run_summary(
        [run],
        expected_documents=["empty_doc_2025", "missing_doc_2025"],
    )

    empty = summary["documents"]["empty_doc_2025"]["current"]
    missing = summary["documents"]["missing_doc_2025"]["current"]
    assert empty["status"] == "empty"
    assert empty["reason"] == "no derivation rows were produced"
    assert missing["status"] == "missing"
    assert missing["reason"] == "expected report was not produced in the current run"
    assert summary["attention_documents"] == ["missing_doc_2025"]


def test_summary_output_must_be_outside_repository(tmp_path: Path) -> None:
    run = tmp_path / "run"
    _write_report(run, "toy_2025", derived=1, attempted=1)
    summary = build_run_summary([run])

    output = tmp_path.parent / "summary.md"
    assert write_run_summary(summary, output, root=tmp_path) == output.resolve()
    assert output.read_text(encoding="ascii").startswith("# Derivation run summary")

    with pytest.raises(ValueError, match="outside repository root"):
        write_run_summary(summary, tmp_path / "inside.md", root=tmp_path)


def test_cli_wrapper_writes_the_same_provider_free_artifact(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = tmp_path / "run"
    _write_report(run, "toy_2025", derived=1, attempted=1)
    output = tmp_path.parent / "cli-summary.md"

    assert cli_summarize_runs_command(run_paths=[run], output=output, root=tmp_path) == 0
    assert output.is_file()
    assert "summary:" in capsys.readouterr().out
