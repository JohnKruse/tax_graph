from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tax_graph.acquire.citation_check import CitationIntegrityReport
from tax_graph.cli import acquire_command


ROOT = Path(__file__).resolve().parents[1]


def _copy_acquire_root(tmp_path):
    root = tmp_path / "project"
    shutil.copytree(ROOT / "config", root / "config")
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
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "form_1040_2025_line_7_capital_gain_loss = 2000" in result.stdout


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
    assert len(rendered) == 7
    assert not (root / ".cache" / "raw" / "2025" / "_state.json").exists()
