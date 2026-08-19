"""M20-S135 guards for unverifiable citations and repair evidence."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from tax_graph.acquire.citation_check import CitationIntegrityReport
from tax_graph.acquire.citation_check import CitationUnverifiable
from tax_graph.acquire.citation_check import check_citation_integrity
from tax_graph.acquire.citation_check import check_graph_citations
from tax_graph.cli import _print_acquire_summary
from tax_graph.io.loader import load_graph


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / ".cache" / "raw"


def _citation(citation_id: str) -> dict:
    graph = load_graph("2025", ROOT)
    return next(item for item in graph.items("citations") if item["citation_id"] == citation_id)


def test_real_graph_accounts_for_unverifiable_citations_without_failing() -> None:
    graph = load_graph("2025", ROOT)
    report = check_graph_citations(year="2025", raw_store=RAW_ROOT, root=ROOT)

    assert report.checked == 593
    assert len(report.unverifiable_citations) == 36
    assert report.checked + len(report.unverifiable_citations) == len(graph.items("citations")) == 629
    assert report.ok
    assert all(item.reason == "missing source ranges" for item in report.unverifiable_citations)
    ids = {item.citation_id for item in report.unverifiable_citations}
    # Both were in the 114 and were ranged by the S136 apply on 2026-08-19.
    assert "cite_instruction_form_1040_2025_en_us_2025_publink1000106118" not in ids
    assert "cite_intake_13614c_quality" not in ids
    # The 36 that remain are the 22 held by the content-hash gated graph_ext
    # overlay and the 14 whose quote exists only in acquired HTML.
    assert "cite_span_form_2441_2025_0012" in ids
    assert "cite_instruction_schedule_1_2025_en_us_2025_publink1000151499" in ids


def test_provenance_findings_self_verify_after_their_proposed_repairs() -> None:
    report = check_graph_citations(year="2025", raw_store=RAW_ROOT, root=ROOT)

    assert {item.citation_id for item in report.provenance_findings} == {
        "cite_schedule_d_carryover_line_13",
        "cite_1040_qdcgt_line_4",
    }
    qdcgt = next(
        item for item in report.provenance_findings if item.citation_id == "cite_1040_qdcgt_line_4"
    )
    assert qdcgt.correct_ranges == (
        {"start": 157403, "end": 157405},
        {"start": 157407, "end": 157425},
    )

    for finding in report.provenance_findings:
        repaired = deepcopy(_citation(finding.citation_id))
        assert finding.repair_quote is not None
        assert finding.repair_blocker
        repaired["ranges"] = [dict(item) for item in finding.correct_ranges]
        repaired["quoted_text"] = finding.repair_quote
        repaired_report = check_citation_integrity(
            [repaired],
            text_dir=RAW_ROOT / "2025",
        )
        assert repaired_report.ok, finding.citation_id


def test_acquire_summary_prints_unverifiable_count_and_ids(capsys) -> None:
    report = SimpleNamespace(new=[], changed=[], unchanged=[])
    citation_report = CitationIntegrityReport(
        checked=515,
        mismatches=[],
        unverifiable_citations=[
            CitationUnverifiable(
                citation_id="cite_legacy_one",
                document_id="instructions_form_1040_2025",
                source_document_id="instructions_form_1040_2025",
                reason="missing source ranges",
            ),
            CitationUnverifiable(
                citation_id="cite_legacy_two",
                document_id="intake_13614c_2025",
                source_document_id="intake_13614c_2025",
                reason="missing source ranges",
            ),
        ],
    )

    _print_acquire_summary(report, citation_report)

    output = capsys.readouterr().out
    assert "checked: 515 (unverifiable: 2)" in output
    assert "cite_legacy_one: missing source ranges" in output
    assert "cite_legacy_two: missing source ranges" in output
