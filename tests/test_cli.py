from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tax_graph.acquire.citation_check import CitationIntegrityReport
from tax_graph.cli import (
    acquire_command,
    harvest_worksheet_command,
    promote_instruction_command,
    verify_expression_agreement_command,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m20
def test_expression_agreement_command_writes_report(tmp_path, capsys):
    root = tmp_path / "project"
    (root / "graph" / "2025").mkdir(parents=True)
    for kind in ("documents", "nodes", "edges", "rules", "citations", "decisions", "tables"):
        (root / "graph" / "2025" / kind).mkdir()
    (root / "graph" / "2025" / "nodes" / "nodes.yaml").write_text(
        "- node_id: form_1040_2025_target\n  document_id: form_1040_2025\n  node_type: computed\n",
        encoding="ascii",
    )
    (root / "graph" / "2025" / "rules" / "rules.yaml").write_text(
        "- rule_id: rule_sum\n  operation: SUM\n  description: Add values.\n",
        encoding="ascii",
    )
    (root / "graph" / "2025" / "edges" / "edges.yaml").write_text(
        "- edge_id: edge_a\n  source: form_1040_2025_a\n  target: form_1040_2025_target\n  relationship: CALCULATES\n  rule_id: rule_sum\n  role: addend\n",
        encoding="ascii",
    )

    assert verify_expression_agreement_command(root=root) == 0
    output = capsys.readouterr().out
    assert "expression agreement report:" in output
    assert "coverage:" in output
    assert "accuracy:" in output
    assert (root / "output" / "m20_s8_expression_agreement.yaml").exists()
    report_text = (root / "output" / "m20_s8_expression_agreement.yaml").read_text(encoding="ascii")
    assert "measurement: m20_s8" in report_text
    assert "coverage:" in report_text
    assert "accuracy:" in report_text


def _copy_acquire_root(tmp_path):
    root = tmp_path / "project"
    shutil.copytree(
        ROOT / "config",
        root / "config",
        ignore=shutil.ignore_patterns("tax-graph.config.yaml"),
    )
    shutil.copyfile(
        root / "config" / "tax-graph.config.example.yaml",
        root / "tax-graph.config.yaml",
    )  # hermetic: never inherit the developer's gitignored local config
    shutil.copytree(ROOT / "schemas", root / "schemas")
    return root


@pytest.mark.m0
def test_cli_validate_succeeds():
    result = subprocess.run(
        [sys.executable, "-m", "tax_graph.cli", "validate", "2025"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "graph integrity OK" in result.stdout


@pytest.mark.m0
def test_cli_run_reports_line_7_value():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "tax_graph.cli",
            "run",
            "--facts",
            "examples/capital_gains_basic/facts.yaml",
            "--no-record",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "form_1040_2025_line_7_capital_gain_loss = 2000" in result.stdout


@pytest.mark.m18
def test_promote_instruction_command_has_reproducible_defaults(tmp_path, monkeypatch, capsys):
    called = {}

    def fake_promote(root, **kwargs):
        called["root"] = root
        called.update(kwargs)
        return SimpleNamespace(joins=(object(),), findings=(object(),), coverage_before={}, coverage_after={})

    monkeypatch.setattr("tax_graph.ingest.instruction_promotion.promote_instruction_html", fake_promote)

    exit_code = promote_instruction_command(root=tmp_path, year="2025")

    assert exit_code == 0
    assert called["root"] == tmp_path.resolve()
    assert called["source_document_id"] == "instructions_form_1040_2025"
    assert called["html_path"] == tmp_path / ".cache" / "raw" / "2025" / "instructions_form_1040_2025.html"
    assert "findings persisted: 1" in capsys.readouterr().out


@pytest.mark.m20
def test_harvest_worksheet_command_writes_only_a_draft(tmp_path, capsys):
    html_path = tmp_path / "instructions.html"
    html_path.write_text(
        """
        <h3><a name="toy-anchor"></a>Toy Worksheet</h3>
        <table><tr><td>1.</td><td>Enter an amount.</td></tr>
        <tr><td>2.</td><td>Also include this amount on the entry space on Form 1040, line 16.</td></tr></table>
        """,
        encoding="ascii",
    )
    root = tmp_path / "project"

    exit_code = harvest_worksheet_command(
        root=root,
        html_path=html_path,
        source_document_id="instructions_toy_2025",
        document_id="toy_worksheet_2025",
        title="Toy Worksheet",
        start_anchor="toy-anchor",
    )

    assert exit_code == 0
    draft_dir = root / "graph" / "2025" / "_drafts" / "toy_worksheet_2025"
    assert (draft_dir / "documents.yaml").exists()
    assert (draft_dir / "nodes.yaml").exists()
    assert "promoted: no" in capsys.readouterr().out


@pytest.mark.m3
def test_acquire_command_smoke_with_mocked_components(tmp_path, capsys):
    root = _copy_acquire_root(tmp_path)
    rendered = []

    def fake_render(entry, *, pdf_path, output_dir, content_hash, config):
        rendered.append(entry.document_id)
        Path(output_dir, f"{entry.document_id}.txt").write_text("rendered", encoding="utf-8")

    def fake_citation_checker(**kwargs):
        return CitationIntegrityReport(checked=4, mismatches=[])

    exit_code = acquire_command(
        "2025",
        check=True,
        root=root,
        fetch_bytes=lambda url, config: b"fake public IRS pdf",
        renderer=fake_render,
        citation_checker=fake_citation_checker,
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "acquisition change report" in captured.out
    assert "citation integrity" in captured.out
    assert "result: OK" in captured.out
    assert len(rendered) == 26
    assert not (root / ".cache" / "raw" / "2025" / "_state.json").exists()


@pytest.mark.m3
def test_acquire_summary_prints_per_issue_document_and_source(tmp_path, capsys):
    root = _copy_acquire_root(tmp_path)

    def fake_render(entry, *, pdf_path, output_dir, content_hash, config):
        Path(output_dir, f"{entry.document_id}.txt").write_text("rendered", encoding="utf-8")

    def fake_citation_checker(**kwargs):
        return CitationIntegrityReport(
            checked=1,
            mismatches=[
                type("Mismatch", (), {
                    "citation_id": "source_drift_form_8949_2025",
                    "document_id": "form_8949_2025",
                    "source_document_id": "form_8949_2025",
                    "reason": "source drift: expected sha256 aaa, got bbb",
                })()
            ],
        )

    exit_code = acquire_command(
        "2025",
        check=True,
        root=root,
        fetch_bytes=lambda url, config: b"fake public IRS pdf",
        renderer=fake_render,
        citation_checker=fake_citation_checker,
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "source_drift_form_8949_2025: source drift:" in captured.out
    assert "(doc=form_8949_2025, source=form_8949_2025)" in captured.out
