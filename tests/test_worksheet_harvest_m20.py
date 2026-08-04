"""M20-S42 tests for the source-anchored worksheet harvester."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from jsonschema import validate

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
    )
    target = WorksheetTarget(document_id="gap_worksheet", title="Gap Worksheet", start_anchor="gap")

    result = harvest_worksheet(source, target)

    assert not result.ok
    assert not result.nodes
    assert any(finding.kind == "line_sequence_gap" for finding in result.findings)


def test_harvester_requires_the_declared_start_anchor() -> None:
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

    assert not result.ok
    assert not result.nodes
    assert any(finding.kind == "missing_start_anchor" for finding in result.findings)


def test_harvester_fails_closed_when_a_footnote_marker_is_unresolved() -> None:
    source = _worksheet_html(
        """
        <tr><td>1.</td><td>Enter an amount*.</td></tr>
        <tr><td>2.</td><td>Also include this amount on the entry space on Form 1040, line 16.</td></tr>
        """,
        anchor="footnote",
    )
    target = WorksheetTarget(document_id="footnote_worksheet", title="Footnote Worksheet", start_anchor="footnote")

    result = harvest_worksheet(source, target)

    assert not result.ok
    assert any(finding.kind == "unresolved_footnote_marker" for finding in result.findings)


def test_harvester_requires_terminal_destination_even_when_rows_are_contiguous() -> None:
    source = _worksheet_html(
        """
        <tr><td>1.</td><td>Enter an amount.</td></tr>
        <tr><td>2.</td><td>Enter another amount.</td></tr>
        """,
        anchor="terminal",
    )
    target = WorksheetTarget(document_id="terminal_worksheet", title="Terminal Worksheet", start_anchor="terminal")

    result = harvest_worksheet(source, target)

    assert not result.ok
    assert any(finding.kind == "missing_terminal_line" for finding in result.findings)


def _worksheet_html(rows: str, *, anchor: str) -> str:
    return f"""
    <html><body>
      <h3><a name="{anchor}"></a>Test Worksheet</h3>
      <table><tbody>{rows}</tbody></table>
    </body></html>
    """
