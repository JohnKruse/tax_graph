"""M20-S99 tests for cache-backed worksheet windows."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tax_graph.ingest.worksheet_harvest import (
    _source_tables,
    classify_worksheet_tables,
    harvest_worksheets,
    window_fingerprint,
)


pytestmark = pytest.mark.m20


def _source() -> str:
    return """
    <h3><a name="one"></a>Window Worksheet</h3>
    <table><tr><td>1.</td><td>Enter an amount.</td></tr>
      <tr><td>2.</td><td>Carry the amount forward.</td></tr></table>
    <table><tr><td>Lookup band</td><td>300</td></tr></table>
    <h3><a name="other"></a>Other Worksheet</h3>
    <table><tr><td>1.</td><td>Another amount.</td></tr></table>
    """


def _response(table, _source_text, _lookahead, _chunk):
    if table.table_id == 1:
        return {
            "starts_a_worksheet": True,
            "title": "Window Worksheet",
            "table_ids": [1, 2],
            "parameter_table_ids": [2],
            "serves_lines": ["1", "2"],
        }
    if table.table_id == 2:
        return {
            "starts_a_worksheet": True,
            "title": "Window Worksheet",
            "table_ids": [2],
            "parameter_table_ids": [],
            "serves_lines": [],
        }
    return {
        "starts_a_worksheet": True,
        "title": "Other Worksheet",
        "table_ids": [3],
        "parameter_table_ids": [],
        "serves_lines": ["1"],
    }


def test_first_anchor_wins_and_parameter_tables_do_not_extend_rows() -> None:
    result = harvest_worksheets(
        _source(),
        source_document_id="instructions_fixture_2025",
        classifier=lambda table, source_text: {"kind": "worksheet"},
        window_classifier=_response,
        lookahead=1,
    )

    first = result.worksheets[0]
    assert first.ok
    assert first.source_table_ids == (1, 2)
    assert first.window is not None
    assert first.window.parameter_table_ids == (2,)
    assert [node["node_id"].rsplit("_", 1)[-1] for node in first.line_nodes] == ["1", "2"]
    assert any(finding.kind == "window_claim_overlap" for finding in result.findings)
    assert any(finding.kind == "worksheet_window_reached_edge" for finding in first.findings)


def test_window_cache_uses_the_seeded_fingerprint_and_reports_misalignment(tmp_path: Path) -> None:
    source = _source()
    tables = _source_tables(source)
    cache = tmp_path / "instructions_fixture.worksheet_windows.yaml"
    entries = {}
    for index, table in enumerate(tables):
        entries[window_fingerprint(source, tables, index, 1)] = {
            "anchor_table_id": table.table_id,
            "starts_a_worksheet": False,
            "title": "",
            "table_ids": [],
            "parameter_table_ids": [],
            "serves_lines": [],
        }
    first_key = window_fingerprint(source, tables, 0, 1)
    entries[first_key]["anchor_table_id"] = 99
    cache.write_text(
        yaml.safe_dump(
            {"schema_version": 1, "lookahead": 1, "windows": entries},
            sort_keys=True,
            allow_unicode=False,
        ),
        encoding="ascii",
    )

    result = harvest_worksheets(
        source,
        source_document_id="instructions_fixture_2025",
        classifier=lambda table, source_text: {"kind": "worksheet"},
        window_cache_path=cache,
    )

    assert not result.worksheets
    assert any(finding.kind == "window_cache_entry_misaligned" for finding in result.findings)


def test_missing_window_is_a_persisted_finding_not_a_silent_empty() -> None:
    result = harvest_worksheets(
        _source(),
        source_document_id="instructions_fixture_2025",
        classifier=lambda table, source_text: {"kind": "worksheet"},
        window_classifier=lambda *_args: {
            "starts_a_worksheet": False,
            "title": "",
            "table_ids": [],
            "parameter_table_ids": [],
            "serves_lines": [],
        },
    )

    assert len(result.windows) == 3
    assert result.worksheets == ()
    assert result.inventory


def test_classifier_cache_is_reused_and_remains_the_window_gate(tmp_path: Path) -> None:
    source = _source()
    cache = tmp_path / "instructions_fixture.worksheet_tables.yaml"
    calls: list[int] = []

    def classifier(table, _source_text):
        calls.append(table.table_id)
        return {"kind": "worksheet" if table.table_id == 1 else "layout"}

    first = classify_worksheet_tables(source, classifier=classifier, cache_path=cache)
    calls.clear()
    second = classify_worksheet_tables(source, classifier=classifier, cache_path=cache)

    assert first == second
    assert calls == []
    assert cache.exists()

    result = harvest_worksheets(
        source,
        source_document_id="instructions_fixture_2025",
        classifier=classifier,
        cache_path=cache,
        window_classifier=lambda *_args: {
            "starts_a_worksheet": True,
            "title": "Window Worksheet",
            "table_ids": [1, 2],
            "parameter_table_ids": [2],
            "serves_lines": ["1", "2"],
        },
    )

    assert [window.anchor_table_id for window in result.windows] == [1]
    assert any("table 2" in item.message and item.kind == "classified_not_emitted" for item in result.inventory)
