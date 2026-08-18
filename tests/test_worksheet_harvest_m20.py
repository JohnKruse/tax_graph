"""M20-S43 tests for title-anchored worksheet harvesting."""

from __future__ import annotations

from pathlib import Path
import re

import pytest
import yaml
from jsonschema import validate

from tax_graph.acquire.citation_check import check_citation_integrity
from tax_graph.ingest.worksheet_harvest import (
    QDCGT_WORKSHEET_TARGET,
    WorksheetTarget,
    harvest_worksheet,
    harvest_worksheet_file,
    write_worksheet_draft,
)


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]
QDCGT_HTML = ROOT / ".cache" / "raw" / "2025" / "instructions_form_1040_2025.html"


def test_qdcgt_canary_discovers_lines_constants_citations_and_form_2555_routes() -> None:
    result = harvest_worksheet_file(QDCGT_HTML, QDCGT_WORKSHEET_TARGET)

    assert result.ok
    assert len(result.line_nodes) == 25
    assert len(result.parameter_nodes) == 13
    assert len(result.citations) == 13
    assert [node["node_id"].rsplit("_", 1)[-1] for node in result.line_nodes] == [str(i) for i in range(1, 26)]
    assert {condition.line for condition in result.conditions} == {"1", "25"}
    assert all(condition.referenced_document == "form_2555" for condition in result.conditions)
    assert all(node.source_quote for node in result.nodes)
    assert all(citation.source_quote for citation in result.citations)
    assert any("Form 2555" in condition.source_quote for condition in result.conditions)
    assert result.observed_start_anchor == QDCGT_WORKSHEET_TARGET.start_anchor
    assert all("publink" not in citation["locator"] for citation in result.citations)
    assert all(QDCGT_WORKSHEET_TARGET.title in citation["locator"] for citation in result.citations)

    values = [node["constant_value"] for node in result.parameter_nodes]
    assert sum(value == 48350 for value in values) == 2
    assert sum(value == 96700 for value in values) == 2
    assert sum(value == 64750 for value in values) == 1
    assert sum(value == 533400 for value in values) == 1
    assert sum(value == 300000 for value in values) == 1
    assert sum(value == 600050 for value in values) == 2
    assert sum(value == 566700 for value in values) == 1
    assert 0.15 in values
    assert 0.2 in values
    assert 100000 in values


def test_qdcgt_canary_survives_rewritten_publink_ids_and_keeps_citations_verbatim() -> None:
    source = QDCGT_HTML.read_text(encoding="ascii")
    rewritten = re.sub(
        r"en_US_2025_publink[0-9]+",
        lambda match: f"future_anchor_{match.group(0)[-4:]}",
        source,
    )
    assert QDCGT_WORKSHEET_TARGET.start_anchor not in rewritten

    result = harvest_worksheet(
        rewritten,
        QDCGT_WORKSHEET_TARGET,
        source_document_id="instructions_form_1040_2025",
        oracle_source_text=(ROOT / ".cache" / "raw" / "2025" / "instructions_form_1040_2025.txt").read_text(
            encoding="ascii"
        ),
    )

    assert result.ok
    assert result.start_anchor.startswith("future_anchor_")
    assert len(result.line_nodes) == 25
    assert len(result.parameter_nodes) == 13
    assert len(result.citations) == 13
    assert {condition.line for condition in result.conditions} == {"1", "25"}
    report = check_citation_integrity(
        [citation.as_dict() for citation in result.citations],
        text_dir=ROOT / ".cache" / "raw" / "2025",
    )
    assert report.checked == 13
    assert report.ok
    assert all("publink" not in citation["locator"] for citation in result.citations)


def test_harvester_fails_closed_when_worksheet_title_is_absent() -> None:
    source = QDCGT_HTML.read_text(encoding="ascii").replace(
        "Qualified Dividends and Capital Gain Tax Worksheet-Line 16",
        "Different Worksheet-Line 16",
    )

    result = harvest_worksheet(source, QDCGT_WORKSHEET_TARGET)

    assert not result.ok
    finding = next(finding for finding in result.findings if finding.kind == "missing_start_title")
    assert "matched 0 headings" in finding.message
    assert "candidate_count=0" in finding.evidence


def test_harvester_fails_closed_when_worksheet_title_is_ambiguous() -> None:
    source = """
    <h3><a name="first-anchor"></a>Test Worksheet</h3>
    <h3><a name="second-anchor"></a>Test Worksheet</h3>
    <table><tr><td>1.</td><td>Enter an amount.</td></tr>
    <tr><td>2.</td><td>Also include this amount on the entry space on Form 1040, line 16.</td></tr></table>
    """
    target = WorksheetTarget(
        document_id="ambiguous_worksheet",
        title="Test Worksheet",
        start_anchor="stale-anchor",
    )

    result = harvest_worksheet(source, target)

    assert not result.ok
    finding = next(finding for finding in result.findings if finding.kind == "ambiguous_start_title")
    assert "matched 2 headings" in finding.message
    assert "candidate[0]=Test Worksheet;anchor=first-anchor" in finding.evidence
    assert "candidate[1]=Test Worksheet;anchor=second-anchor" in finding.evidence


def test_qdcgt_draft_writer_stays_under_drafts_and_strips_witness_fields(tmp_path: Path) -> None:
    result = harvest_worksheet_file(QDCGT_HTML, QDCGT_WORKSHEET_TARGET)
    draft_dir = tmp_path / "graph" / "2025" / "_drafts" / result.target.document_id

    written = write_worksheet_draft(result, draft_dir)

    assert written == draft_dir.resolve()
    assert yaml.safe_load((draft_dir / "documents.yaml").read_text(encoding="ascii"))[0]["document_type"] == "worksheet"
    nodes = yaml.safe_load((draft_dir / "nodes.yaml").read_text(encoding="ascii"))
    assert len(nodes) == 38
    assert all("source_quote" not in node for node in nodes)
    validate(
        yaml.safe_load((draft_dir / "documents.yaml").read_text(encoding="ascii"))[0],
        yaml.safe_load((ROOT / "schemas" / "document.schema.json").read_text(encoding="ascii")),
    )
    node_schema = yaml.safe_load((ROOT / "schemas" / "node.schema.json").read_text(encoding="ascii"))
    edge_schema = yaml.safe_load((ROOT / "schemas" / "edge.schema.json").read_text(encoding="ascii"))
    citation_schema = yaml.safe_load((ROOT / "schemas" / "citation.schema.json").read_text(encoding="ascii"))
    for node in nodes:
        validate(node, node_schema)
    for edge in yaml.safe_load((draft_dir / "edges.yaml").read_text(encoding="ascii")):
        validate(edge, edge_schema)
    for citation in yaml.safe_load((draft_dir / "citations.yaml").read_text(encoding="ascii")):
        validate(citation, citation_schema)
    report = yaml.safe_load((draft_dir / "harvest.yaml").read_text(encoding="ascii"))
    assert report["status"] == "ready"
    assert report["counts"]["lines"] == 25

    with pytest.raises(ValueError, match="_drafts"):
        write_worksheet_draft(result, tmp_path / "graph" / "2025" / "nodes")


def test_harvester_fails_closed_on_a_line_gap() -> None:
    source = _worksheet_html(
        """
        <tr><td>1.</td><td>Enter an amount.</td></tr>
        <tr><td>3.</td><td>Also include this amount on the entry space on Form 1040, line 16.</td></tr>
        """,
        anchor="gap",
        title="Gap Worksheet",
    )
    target = WorksheetTarget(document_id="gap_worksheet", title="Gap Worksheet", start_anchor="gap")

    result = harvest_worksheet(source, target)

    assert not result.ok
    assert not result.nodes
    assert any(finding.kind == "line_sequence_gap" for finding in result.findings)


def test_harvester_uses_title_when_declared_start_anchor_is_stale() -> None:
    source = _worksheet_html(
        """
        <tr><td>1.</td><td>Enter an amount.</td></tr>
        <tr><td>2.</td><td>Also include this amount on the entry space on Form 1040, line 16.</td></tr>
        """,
        anchor="different-anchor",
    )
    target = WorksheetTarget(
        document_id="anchored_worksheet",
        title="Test Worksheet",
        start_anchor="required-anchor",
    )

    result = harvest_worksheet(source, target)

    assert result.ok
    assert result.start_anchor == "different-anchor"
    assert all("publink" not in citation["locator"] for citation in result.citations)


def test_harvester_normalizes_title_case_whitespace_and_punctuation() -> None:
    source = _worksheet_html(
        """
        <tr><td>1.</td><td>Enter an amount.</td></tr>
        <tr><td>2.</td><td>Also include this amount on the entry space on Form 1040, line 16.</td></tr>
        """,
        anchor="normalized-title",
        title="  TEST-WORKSHEET.  ",
    )
    target = WorksheetTarget(
        document_id="normalized_worksheet",
        title="Test Worksheet",
        start_anchor="stale-anchor",
    )

    result = harvest_worksheet(source, target)

    assert result.ok


def test_harvester_fails_closed_when_a_footnote_marker_is_unresolved() -> None:
    source = _worksheet_html(
        """
        <tr><td>1.</td><td>Enter an amount*.</td></tr>
        <tr><td>2.</td><td>Also include this amount on the entry space on Form 1040, line 16.</td></tr>
        """,
        anchor="footnote",
        title="Footnote Worksheet",
    )
    target = WorksheetTarget(document_id="footnote_worksheet", title="Footnote Worksheet", start_anchor="footnote")

    result = harvest_worksheet(source, target)

    assert not result.ok
    assert any(finding.kind == "unresolved_footnote_marker" for finding in result.findings)


def _worksheet_html(rows: str, *, anchor: str, title: str = "Test Worksheet") -> str:
    return f"""
    <html><body>
      <h3><a name="{anchor}"></a>{title}</h3>
      <table><tbody>{rows}</tbody></table>
    </body></html>
    """
