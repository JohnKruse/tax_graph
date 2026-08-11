"""M20-S97 tests for HTML-structured worksheet discovery."""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from tax_graph.ingest.worksheet_harvest import (
    QDCGT_WORKSHEET_TARGET,
    WorksheetTarget,
    classify_worksheet_tables,
    harvest_worksheet,
    harvest_worksheet_file,
    harvest_worksheets,
    harvest_worksheets_file,
)


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / ".cache" / "raw" / "2025"


def _fixture_classifier(table, source_text):
    heading = table.heading.text if table.heading is not None else ""
    lines = []
    for row in table.rows:
        for cell in row.cells:
            match = re.match(r"\s*[\"']?([0-9]+[a-z]?)\s*[.)]\s+", cell, re.IGNORECASE)
            if match:
                lines.append(match.group(1).lower())
                break
    return {
        "kind": "worksheet" if "Worksheet" in heading else "layout",
        "lines": list(dict.fromkeys(lines)),
    }


def test_schedule_d_discovery_uses_all_five_html_tables_and_oracle() -> None:
    result = harvest_worksheets_file(
        RAW / "instructions_schedule_d_2025.html",
        source_document_id="instructions_schedule_d_2025",
        classifier=_fixture_classifier,
    )

    assert len(result.classifications) == 5
    assert len(result.windows) == 5
    assert len(result.worksheets) == 4
    assert [len(item.line_nodes) for item in result.worksheets] == [13, 7, 18, 47]
    assert all(item.ok for item in result.worksheets), result.as_dict()
    assert all(item.as_dict()["oracle"]["status"] == "agree" for item in result.worksheets)
    assert result.classifications[0].heading.startswith("Capital Loss Carryover Worksheet")
    assert result.classifications[0].anchor_id == "en_US_2024_publink1000291473"
    assert result.classifications[0].lines == ("6", "14")
    assert result.classifications[1].lines == ("18",)
    assert result.classifications[2].lines == ("19",)
    assert result.classifications[3].lines == ()
    assert result.classifications[4].lines == ()
    assert result.windows[0].title.startswith("Capital Loss Carryover Worksheet")
    assert result.windows[0].anchor_table_id == 1
    assert result.windows[0].table_ids == (1,)
    assert result.windows[1].serves_lines == ("Schedule D, line 18",)
    assert result.windows[2].serves_lines == ()
    assert result.windows[3].starts_a_worksheet
    assert not result.windows[4].starts_a_worksheet


def test_title_filter_returns_one_logical_worksheet_across_continuation() -> None:
    result = harvest_worksheets_file(
        RAW / "instructions_schedule_d_2025.html",
        source_document_id="instructions_schedule_d_2025",
        title="Schedule D Tax Worksheet",
        classifier=_fixture_classifier,
    )

    assert len(result.worksheets) == 1
    assert len(result.worksheets[0].line_nodes) == 47
    assert result.worksheets[0].document["document_id"] == "schedule_d_tax_worksheet_2025"


def test_schedule_b_zero_tables_is_a_valid_empty_answer() -> None:
    result = harvest_worksheets_file(
        RAW / "instructions_schedule_b_2025.html",
        source_document_id="instructions_schedule_b_2025",
    )

    assert result.classifications == ()
    assert result.windows == ()
    assert result.worksheets == ()
    assert result.findings == ()


def test_six_registered_extents_are_recovered_without_a_registry() -> None:
    cases = (
        ("instructions_form_2441_2025", "Credit Limit Worksheet", 3),
        ("instructions_form_6251_2025", "Exemption Worksheet", 6),
        ("instructions_schedule_d_2025", "Schedule D Tax Worksheet", 47),
        ("instructions_form_1040_2025", "Simplified Method Worksheet", 11),
        ("instructions_schedule_d_2025", "28% Rate Gain Worksheet", 7),
        ("instructions_form_1040_2025", "Social Security Benefits Worksheet", 18),
    )

    for source_id, title, expected in cases:
        result = harvest_worksheet_file(
            RAW / f"{source_id}.html",
            WorksheetTarget(document_id="probe", title=title, start_anchor="stale"),
        )
        assert result.ok, (title, result.findings)
        assert len(result.line_nodes) == expected
        assert result.as_dict()["oracle"]["status"] == "agree"


def test_html_table_boundary_replaces_destination_phrase() -> None:
    source = """
    <html><body>
      <h3><a name="model-end"></a>Model End Worksheet</h3>
      <table><tr><td>1.</td><td>Enter an amount.</td></tr>
      <tr><td>2.</td><td>Finish the worksheet here.</td></tr></table>
    </body></html>
    """

    result = harvest_worksheet(
        source,
        WorksheetTarget(document_id="model_end", title="Model End Worksheet", start_anchor="model-end"),
    )

    assert result.ok
    assert len(result.line_nodes) == 2
    assert not any(item.kind == "terminal_destination_missing" for item in result.findings)


def test_window_cache_is_used_without_a_per_table_classifier() -> None:
    result = harvest_worksheets_file(
        RAW / "instructions_schedule_d_2025.html",
        source_document_id="instructions_schedule_d_2025",
    )

    assert len(result.windows) == 5
    assert all(window.finding is None for window in result.windows)


def test_classification_cache_is_keyed_by_table_bytes(tmp_path: Path) -> None:
    source = (RAW / "instructions_schedule_d_2025.html").read_text(encoding="ascii")
    cache = tmp_path / "worksheet_tables.yaml"
    calls: list[int] = []

    def classifier(table, source_text):
        calls.append(table.table_id)
        return {"kind": "worksheet", "lines": []}

    first = classify_worksheet_tables(source, classifier=classifier, cache_path=cache)
    second = classify_worksheet_tables(source, classifier=classifier, cache_path=cache)

    assert first == second
    assert len(calls) == len(first)
    assert cache.exists()


def test_provider_classifier_receives_every_table_with_strict_schema() -> None:
    class FakeClient:
        def __init__(self):
            self.calls = []

        def structured_completion(self, **kwargs):
            self.calls.append(kwargs)
            return {"kind": "layout"}

    source = """
    <h3><a name="one"></a>One</h3><table><tr><td>1.</td></tr></table>
    <h3><a name="two"></a>Two</h3><table><tr><td>2.</td></tr></table>
    """
    client = FakeClient()
    result = classify_worksheet_tables(
        source,
        classifier=client,
        config={"llm": {"model": "test/model"}},
    )

    assert len(result) == 2
    assert len(client.calls) == 2
    request = client.calls[0]
    assert request["purpose"] == "tax_graph_worksheet_table_classifier"
    assert request["schema"]["type"] == "object"
    assert set(request["schema"]["required"]) == {"kind"}


def test_provider_window_receives_every_anchor_with_strict_schema() -> None:
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

    source = """
    <h3><a name="one"></a>One</h3><table><tr><td>1.</td></tr></table>
    <h3><a name="two"></a>Two</h3><table><tr><td>2.</td></tr></table>
    """
    client = FakeClient()
    result = harvest_worksheets(
        source,
        source_document_id="instructions_toy_2025",
        classifier=lambda table, source_text: {"kind": "worksheet"},
        window_classifier=client,
        config={"llm": {"model": "test/model"}},
    )

    assert len(result.windows) == 2
    assert len(client.calls) == 2
    request = client.calls[0]
    assert request["purpose"] == "tax_graph_worksheet_window"
    assert request["schema"]["type"] == "object"
    assert set(request["schema"]["required"]) == {
        "starts_a_worksheet",
        "title",
        "table_ids",
        "parameter_table_ids",
        "serves_lines",
    }


def test_qdcgt_canary_still_has_its_source_derived_constant_projection() -> None:
    result = harvest_worksheet_file(RAW / "instructions_form_1040_2025.html", QDCGT_WORKSHEET_TARGET)

    assert result.ok
    assert len(result.line_nodes) == 25
    assert len(result.parameter_nodes) == 13
    assert result.as_dict()["oracle"]["status"] == "agree"
