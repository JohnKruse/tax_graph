"""M12 return-scoped CLI and MCP output contract tests."""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import pytest

from tax_graph.cli import run_command
from tax_graph.compile import build_sqlite
from tax_graph.io.loader import load_yaml
from tax_graph.mcp import build_mcp_server
from tax_graph.output import resolve_return_root


ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "examples/capital_gains_basic/facts.yaml"


@pytest.mark.m12
def test_two_cli_returns_do_not_collide(tmp_path: Path) -> None:
    for return_id in ("return_a", "return_b"):
        assert run_command(
            facts=FACTS,
            year="2025",
            root=ROOT,
            source="yaml",
            return_id=return_id,
            output_root=tmp_path,
            record_date="2026-07-10",
        ) == 0
    first = tmp_path / "returns/return_a"
    second = tmp_path / "returns/return_b"
    assert first != second
    for directory in (first, second):
        assert (directory / "return_record_2025.md").exists()
        assert (directory / "return_record_2025.carryforward.yaml").exists()
        assert (directory / "audit.txt").exists()
        assert json.loads((directory / "run.json").read_text())["return_id"] == directory.name
    assert not any(path.is_file() for path in tmp_path.iterdir())


@pytest.mark.m12
def test_return_id_cannot_escape_output_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="return_id"):
        resolve_return_root(
            project_root=ROOT,
            facts_document={},
            return_id="../graph/2025",
            output_root=tmp_path,
        )
    with pytest.raises(ValueError, match="may not be written under graph"):
        resolve_return_root(
            project_root=ROOT,
            facts_document={},
            return_id="bad",
            output_root=ROOT / "graph/2025",
        )


@pytest.mark.m12
@pytest.mark.parametrize("source", ["yaml", "sqlite"])
def test_mcp_audit_and_record_exports_are_return_scoped(tmp_path: Path, source: str) -> None:
    # The sqlite source builds its own throwaway artifact (the test_mcp_m2
    # pattern) instead of assuming build/tax_graph_2025.sqlite exists at ROOT.
    root = ROOT
    if source == "sqlite":
        root = _copy_graph_project(tmp_path)
        build_sqlite("2025", root=root)
    server = build_mcp_server(year="2025", root=root, source=source)
    facts = load_yaml(FACTS)
    audit = _call_tool(
        server,
        "export_audit_file",
        {"target": "form_1040_2025_line_7_capital_gain_loss", "facts": facts, "return_id": source, "output_root": str(tmp_path)},
    )
    record = _call_tool(
        server,
        "export_return_record",
        {"facts": facts, "return_id": source, "output_root": str(tmp_path), "generated_date": "2026-07-10"},
    )
    expected_root = tmp_path / "returns" / source
    assert Path(audit["path"]).parent == expected_root
    assert Path(record["paths"]["memo"]).parent == expected_root
    assert Path(record["paths"]["carryforward"]).parent == expected_root


@pytest.mark.m12
def test_supported_profile_exports_complete_bundle_when_cache_is_present(tmp_path: Path) -> None:
    if not (ROOT / ".cache/raw/2025/form_1040_2025.pdf").exists():
        pytest.skip("official cached PDFs are required for the gated bundle test")
    facts = ROOT / "examples/taxable_income_basic/facts.yaml"
    code = run_command(
        facts=facts,
        year="2025",
        target="form_1040_2025_root_line_16",
        root=ROOT,
        source="yaml",
        return_id="supported_profile",
        output_root=tmp_path,
        export_bundle=True,
        record_date="2026-07-10",
    )
    assert code == 0
    return_root = tmp_path / "returns/supported_profile"
    bundle = json.loads((return_root / "bundle.json").read_text())
    assert {Path(path).stem for path in bundle["forms"]} == {
        "form_1040_2025", "form_8949_2025", "schedule_1_2025", "schedule_1a_2025",
        "schedule_b_2025", "schedule_d_2025",
    }
    assert Path(bundle["sidecar"]["input"]).exists()
    memo = (return_root / "return_record_2025.md").read_text(encoding="utf-8")
    assert "## Blank Official-Form Lines" in memo
    assert "deferred_form_1040_2025_total_tax_chain" in memo


def _call_tool(server: object, name: str, arguments: dict) -> dict:
    _content, structured = asyncio.run(server.call_tool(name, arguments))
    return structured


def _copy_graph_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "graph", root / "graph", ignore=shutil.ignore_patterns("_drafts"))
    shutil.copytree(ROOT / "schemas", root / "schemas")
    (root / "config").mkdir()
    (root / "tax-graph.config.yaml").write_text(
        "project:\n  paths:\n    build_dir: compiled\n",
        encoding="utf-8",
    )
    return root
