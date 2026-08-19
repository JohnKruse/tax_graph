"""M20-S136 guards for the non-destructive citation range proposal."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tax_graph.acquire.citation_check import check_citation_integrity
from tax_graph.acquire.citation_range_patch import apply_citation_range_patch
from tax_graph.acquire.citation_range_patch import build_citation_range_patch
from tax_graph.acquire.citation_range_patch import write_citation_range_patch
from tax_graph.io.loader import load_graph


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / ".cache" / "raw"


@pytest.fixture(scope="module")
def real_patch() -> dict:
    """Build the proposal from the local 2025 graph and acquired sources."""
    return build_citation_range_patch(
        year="2025",
        root=ROOT,
        raw_store=RAW_ROOT,
    )


def test_real_patch_accounts_for_the_100_rangeable_and_14_html_only(real_patch) -> None:
    assert real_patch["unverifiable_count"] == 114
    assert real_patch["proposed_range_count"] == 100
    assert real_patch["html_only_count"] == 14
    assert real_patch["unverifiable_after_apply"] == 14
    assert real_patch["accounting"] == {
        "ranged_before": 511,
        "unverifiable": 114,
        "computed_table": 4,
        "total": 629,
    }

    proposals = {item["citation_id"]: item for item in real_patch["proposed_ranges"]}
    html_only = {item["citation_id"]: item for item in real_patch["html_only"]}
    assert "cite_intake_13614c_quality" in proposals
    assert "cite_span_form_2441_2025_0012" in proposals
    emphasis = proposals[
        "cite_instruction_form_1040_2025_en_us_2025_publink1000106118"
    ]
    assert emphasis["method"] == "txt_format_normalized"
    assert len(emphasis["ranges"]) == 3
    assert (
        "cite_instruction_schedule_1_2025_en_us_2025_publink1000151499"
        in html_only
    )
    assert (
        "cite_instruction_form_1040_2025_en_us_2025_publink1000106118"
        not in html_only
    )
    assert all(
        item["reason"] == "quoted text is locatable only in acquired HTML"
        for item in html_only.values()
    )


def test_every_proposed_range_self_verifies_without_editing_graph(real_patch) -> None:
    graph = load_graph("2025", ROOT)
    original = graph.items("citations")
    patched = apply_citation_range_patch(original, real_patch)

    report = check_citation_integrity(
        patched,
        text_dir=RAW_ROOT / "2025",
        require_ranges=False,
    )

    assert report.ok
    assert report.checked == 615
    assert len(report.unverifiable_citations) == 14
    assert report.checked + len(report.unverifiable_citations) == 629
    html_only_ids = {entry["citation_id"] for entry in real_patch["html_only"]}
    assert all(
        "ranges" not in item
        for item in original
        if item.get("citation_id") in html_only_ids
    )


def test_patch_writer_is_ascii_and_reproducible(real_patch, tmp_path: Path) -> None:
    output = write_citation_range_patch(real_patch, tmp_path / "ranges.json")
    loaded = json.loads(output.read_text(encoding="ascii"))

    assert loaded == real_patch
    assert all(ord(character) < 128 for character in output.read_text(encoding="ascii"))
