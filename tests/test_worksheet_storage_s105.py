"""M20-S105 tests for source-owned worksheet citation ranges."""

from __future__ import annotations

from pathlib import Path

from jsonschema import validate
import yaml

from tax_graph.ingest.worksheet_harvest import WorksheetTarget, harvest_worksheet


ROOT = Path(__file__).resolve().parents[1]
CITATION_SCHEMA = ROOT / "schemas" / "citation.schema.json"


def _real_harvest(title: str, source_document_id: str):
    html = (ROOT / ".cache" / "raw" / "2025" / f"{source_document_id}.html").read_text(
        encoding="ascii"
    )
    source = (ROOT / ".cache" / "raw" / "2025" / f"{source_document_id}.txt").read_text(
        encoding="ascii"
    )
    target = WorksheetTarget(
        document_id=title.casefold().replace(" ", "_") + "_2025",
        title=title,
        start_anchor="",
    )
    return harvest_worksheet(
        html,
        target,
        source_document_id=source_document_id,
        year="2025",
        oracle_source_text=source,
        _advisories_enabled=True,
    )


def _source_text(source_document_id: str) -> str:
    return (ROOT / ".cache" / "raw" / "2025" / f"{source_document_id}.txt").read_text(
        encoding="ascii"
    )


def test_real_worksheet_citations_store_non_overlapping_source_ranges() -> None:
    schema = yaml.safe_load(CITATION_SCHEMA.read_text(encoding="ascii"))
    for title, source_document_id in (
        ("Simplified Method Worksheet", "instructions_form_1040_2025"),
        ("Standard Deduction Worksheet for Dependents", "instructions_form_1040_2025"),
        ("IRA Deduction Worksheet", "instructions_form_1040_2025"),
        ("Capital Loss Carryover Worksheet", "instructions_schedule_d_2025"),
    ):
        result = _real_harvest(title, source_document_id)
        assert result.ok
        source = _source_text(source_document_id)
        ranges: list[tuple[int, int, str]] = []
        for citation in result.citations:
            value = citation.as_dict()
            validate(value, schema)
            assert value["ranges"]
            reconstructed = " ".join(
                source[item["start"] : item["end"]] for item in value["ranges"]
            )
            assert " ".join(value["quoted_text"].split()) == " ".join(reconstructed.split())
            ranges.extend(
                (item["start"], item["end"], str(value["citation_id"]))
                for item in value["ranges"]
            )
        ranges.sort()
        assert all(current[0] >= previous[1] for previous, current in zip(ranges, ranges[1:]))


def test_simplified_method_note_is_its_own_governed_citation() -> None:
    result = _real_harvest("Simplified Method Worksheet", "instructions_form_1040_2025")
    line_two = next(
        citation for citation in result.citations if citation["citation_id"].endswith("_lines_2")
    )
    note = next(citation for citation in result.citations if citation["kind"] == "note")

    assert "last year" not in line_two["quoted_text"].casefold()
    assert note["governs"] == ["3", "4"]
    assert "last year" in note["quoted_text"].casefold()
    assert note["ranges"] == [{"start": 118266, "end": 118490}]


def test_capital_loss_routing_rows_are_not_claimed_by_line_citations() -> None:
    result = _real_harvest("Capital Loss Carryover Worksheet", "instructions_schedule_d_2025")
    rows = {
        citation["citation_id"].rsplit("_lines_", 1)[-1]: citation
        for citation in result.citations
        if citation["kind"] == "row"
    }
    routing = [citation for citation in result.citations if citation["kind"] == "routing_sentence"]

    assert "go to line 5" not in rows["4"]["quoted_text"].casefold()
    assert "go to line 9" not in rows["8"]["quoted_text"].casefold()
    assert len(routing) == 2
    assert all(citation["ranges"] for citation in routing)
