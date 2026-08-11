"""M20-S98 tests for isolated worksheet discovery and title grouping."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tax_graph.cli import harvest_worksheet_command
from tax_graph.ingest.worksheet_harvest import (
    classify_worksheet_tables,
    harvest_worksheets,
    harvest_worksheets_file,
)


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / ".cache" / "raw" / "2025"


def test_2441_merges_caption_and_body_and_accounts_for_layout() -> None:
    result = harvest_worksheets_file(
        RAW / "instructions_form_2441_2025.html",
        source_document_id="instructions_form_2441_2025",
        cache_path=RAW / "instructions_form_2441_2025.worksheet_tables.yaml",
    )

    assert len(result.classifications) == 4
    assert len(result.windows) == 3
    assert len(result.worksheets) == 2
    assert all(item.ok for item in result.worksheets), result.as_dict()
    assert len({item.target.document_id for item in result.worksheets}) == 2
    worksheet_a = next(item for item in result.worksheets if item.target.document_id.startswith("worksheet_a_"))
    assert worksheet_a.source_table_ids == (3, 4)
    assert len(worksheet_a.line_nodes) == 17
    assert any(item.kind == "classified_not_emitted" and "table 2" in item.message for item in result.inventory)
    assert any(item.kind == "table_merged" and "table 4" in item.message for item in result.inventory)


def test_1040_groups_repeated_titles_and_refuses_step_blocks() -> None:
    result = harvest_worksheets_file(
        RAW / "instructions_form_1040_2025.html",
        source_document_id="instructions_form_1040_2025",
        cache_path=RAW / "instructions_form_1040_2025.worksheet_tables.yaml",
    )

    assert len(result.classifications) == 200
    assert len(result.windows) == 28
    assert len(result.worksheets) == 14
    simplified = next(item for item in result.worksheets if item.target.document_id.startswith("simplified_method_"))
    assert simplified.source_table_ids == (43, 44, 45, 46)
    assert simplified.ok
    assert len(simplified.line_nodes) == 11
    assert set(simplified.window.parameter_table_ids) == {45, 46}
    assert any(item.kind == "window_claim_overlap" for item in result.findings)


def test_later_overlapping_window_claim_is_reported_and_first_anchor_wins() -> None:
    source = """
    <h3><a name="first"></a>Repeated Worksheet</h3>
    <table><tr><td>1.</td><td>First table.</td></tr><tr><td>2.</td><td>Done.</td></tr></table>
    <h3><a name="second"></a>Repeated Worksheet</h3>
    <table><tr><td>1.</td><td>Second table.</td></tr><tr><td>2.</td><td>Done.</td></tr></table>
    """

    result = harvest_worksheets(
        source,
        source_document_id="instructions_repeated_2025",
        classifier=lambda table, source_text: {"kind": "worksheet"},
        window_classifier=lambda table, source_text, lookahead, chunk: {
            "starts_a_worksheet": True,
            "title": "Repeated Worksheet",
            "table_ids": [1, 2] if table.table_id == 1 else [2],
            "parameter_table_ids": [],
            "serves_lines": [],
        },
    )

    assert len(result.worksheets) == 1
    assert result.worksheets[0].source_table_ids == (1, 2)
    finding = next(item for item in result.findings if item.kind == "window_claim_overlap")
    assert "overlap_table_id=2" in finding.evidence


def test_window_provider_failure_isolated(tmp_path: Path) -> None:
    source = """
    <h3><a name="good"></a>Good Worksheet</h3>
    <table><tr><td>1.</td><td>First.</td></tr></table>
    <h3><a name="bad"></a>Bad Worksheet</h3>
    <table><tr><td>1.</td><td>Second.</td></tr></table>
    """
    calls: list[int] = []

    def classifier(table, source_text, lookahead, chunk):
        calls.append(table.table_id)
        if table.table_id == 2:
            raise RuntimeError("table provider failed")
        return {
            "starts_a_worksheet": True,
            "title": "Good Worksheet",
            "table_ids": [1],
            "parameter_table_ids": [],
            "serves_lines": [],
        }

    result = harvest_worksheets(
        source,
        source_document_id="instructions_toy_2025",
        classifier=lambda table, source_text: {"kind": "worksheet"},
        window_classifier=classifier,
    )

    assert len(result.windows) == 2
    assert result.windows[1].finding is not None
    assert result.windows[1].finding.kind == "window_provider_failed"
    assert calls == [1, 2]


def test_table_classification_failure_isolated_and_cache_is_incremental(tmp_path: Path) -> None:
    source = """
    <h3><a name="good"></a>Good Worksheet</h3>
    <table><tr><td>1.</td><td>First.</td></tr></table>
    <h3><a name="bad"></a>Bad Worksheet</h3>
    <table><tr><td>1.</td><td>Second.</td></tr></table>
    """
    cache = tmp_path / "worksheet_tables.yaml"
    calls: list[int] = []

    def classifier(table, source_text):
        calls.append(table.table_id)
        if table.table_id == 2:
            raise RuntimeError("table provider failed")
        return {"kind": "worksheet"}

    result = classify_worksheet_tables(source, classifier=classifier, cache_path=cache)

    assert [item.kind for item in result] == ["worksheet", "classification_error"]
    assert result[1].finding is not None
    assert result[1].finding.kind == "table_classification_failed"
    assert calls == [1, 2]
    assert list(yaml.safe_load(cache.read_text(encoding="ascii"))["tables"]) != []

    calls.clear()
    classify_worksheet_tables(source, classifier=classifier, cache_path=cache)
    assert calls == [2]


def test_provider_classifier_budget_defaults_to_six_thousand() -> None:
    class FakeClient:
        def __init__(self):
            self.calls = []

        def structured_completion(self, **kwargs):
            self.calls.append(kwargs)
            return {"kind": "layout"}

    client = FakeClient()
    classify_worksheet_tables(
        "<h3><a name=\"one\"></a>One</h3><table><tr><td>1.</td></tr></table>",
        classifier=client,
        config={"llm": {"model": "test/model"}},
    )

    assert client.calls[0]["max_tokens"] == 6000


def test_provider_window_budget_defaults_to_six_thousand() -> None:
    class FakeClient:
        def __init__(self):
            self.calls = []

        def structured_completion(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "starts_a_worksheet": False,
                "title": "",
                "table_ids": [],
                "parameter_table_ids": [],
                "serves_lines": [],
            }

    client = FakeClient()
    harvest_worksheets(
        "<h3><a name=\"one\"></a>One</h3><table><tr><td>1.</td></tr></table>",
        source_document_id="instructions_toy_2025",
        classifier=lambda table, source_text: {"kind": "worksheet"},
        window_classifier=client,
        config={"llm": {"model": "test/model"}},
    )

    assert client.calls[0]["max_tokens"] == 6000


def test_cli_attempts_all_worksheets_and_writes_successes(tmp_path: Path, capsys) -> None:
    html_path = tmp_path / "instructions.html"
    html_path.write_text(
        """
        <h3><a name="good"></a>Good Worksheet</h3>
        <table><tr><td>1.</td><td>First.</td></tr><tr><td>2.</td><td>Done.</td></tr></table>
        <h3><a name="bad"></a>Bad Worksheet</h3>
        <table><tr><td>1.</td><td>First.</td></tr><tr><td>3.</td><td>Gap.</td></tr></table>
        """,
        encoding="ascii",
    )
    draft_dir = tmp_path / "project" / "graph" / "2025" / "_drafts"

    def classifier(table, source_text):
        return {"kind": "worksheet"}

    def window_classifier(table, source_text, lookahead, chunk):
        return {
            "starts_a_worksheet": True,
            "title": "Good Worksheet" if table.table_id == 1 else "Bad Worksheet",
            "table_ids": [table.table_id],
            "parameter_table_ids": [],
            "serves_lines": [],
        }

    exit_code = harvest_worksheet_command(
        root=tmp_path / "project",
        html_path=html_path,
        source_document_id="instructions_toy_2025",
        draft_dir=draft_dir,
        classifier=classifier,
        window_classifier=window_classifier,
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert (draft_dir / "good_worksheet_2025" / "documents.yaml").exists()
    report = yaml.safe_load((draft_dir / "worksheet-discovery.yaml").read_text(encoding="ascii"))
    assert report["source_document_id"] == "instructions_toy_2025"
    assert report["worksheets"][1]["findings"][0]["kind"] == "line_sequence_gap"
    assert "harvested good_worksheet_2025" in output
    assert "refused bad_worksheet_2025" in output
    assert "worksheet attempts: discovered=2; written=1; refused=1; sum=2" in output
