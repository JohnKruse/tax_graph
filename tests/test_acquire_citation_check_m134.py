"""M20-S134 guards for exact citation range-list provenance."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from tax_graph.acquire.citation_check import check_citation_integrity
from tax_graph.acquire.citation_check import check_graph_citations
from tax_graph.io.loader import load_graph


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / ".cache" / "raw"


def _citation(citation_id: str) -> dict:
    graph = load_graph("2025", ROOT)
    return next(item for item in graph.items("citations") if item["citation_id"] == citation_id)


def test_real_citation_check_concatenates_ranges_and_emits_two_bad_provenance_findings() -> None:
    """The real corpus passes exact range containment and names the stitched records."""
    report = check_graph_citations(year="2025", raw_store=RAW_ROOT, root=ROOT)

    assert report.checked == 515
    assert report.ok
    assert report.mismatches == []
    assert len(report.range_telltales) == 511
    assert sum(item.short_fragment_count for item in report.range_telltales) == 40
    assert sum(item.large_gap_count for item in report.range_telltales) == 4

    findings = {item.citation_id: item for item in report.provenance_findings}
    assert set(findings) == {
        "cite_schedule_d_carryover_line_13",
        "cite_1040_qdcgt_line_4",
    }
    carryover = findings["cite_schedule_d_carryover_line_13"]
    assert carryover.gaps == (5273,)
    assert carryover.correct_ranges == ({"start": 62388, "end": 62452},)
    qdcgt = findings["cite_1040_qdcgt_line_4"]
    assert qdcgt.gaps == (3068, 1394, 1717, 13)
    assert qdcgt.correct_ranges == ({"start": 157403, "end": 157425},)


def test_real_range_perturbation_is_rejected_by_exact_containment() -> None:
    """Shifting a real stored range cannot pass through a whole-file fallback."""
    citation = deepcopy(_citation("cite_schedule_d_carryover_line_9_13"))
    for item in citation["ranges"]:
        item["start"] += 200
        item["end"] += 200

    report = check_citation_integrity(
        [citation],
        text_dir=RAW_ROOT / "2025",
    )

    assert not report.ok
    assert report.mismatches[0].citation_id == citation["citation_id"]
    assert report.mismatches[0].reason == "quote not found in cited range"


def test_missing_ranges_are_unverifiable_in_strict_mode(tmp_path):
    text_dir = tmp_path / "2025"
    text_dir.mkdir()
    (text_dir / "form_8949_2025.txt").write_text("Proceeds", encoding="utf-8")

    report = check_citation_integrity(
        [
            {
                "citation_id": "cite_without_ranges",
                "document_id": "form_8949_2025",
                "quoted_text": "Proceeds",
            }
        ],
        text_dir=text_dir,
    )

    assert report.checked == 1
    assert not report.ok
    assert report.mismatches[0].reason == "missing source ranges"
