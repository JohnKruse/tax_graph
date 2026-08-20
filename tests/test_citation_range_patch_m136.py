"""M20-S136 guards for the citation range proposal and its applied result.

The proposal was applied to `graph/2025/citations/` on 2026-08-19 with John's
approval, taking unverifiable citations from 114 to 36.  The 22 that remain
rangeable are held by the content-hash gated `graph_ext/` overlay and are
deferred, not written; the other 14 are locatable only in acquired HTML.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tax_graph.acquire.citation_check import check_citation_integrity
from tax_graph.acquire.citation_range_patch import apply_citation_range_patch
from tax_graph.acquire.citation_range_patch import apply_citation_range_patch_to_files
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


def test_only_the_overlay_22_and_the_html_only_14_remain(real_patch) -> None:
    assert real_patch["unverifiable_count"] == 36
    assert real_patch["proposed_range_count"] == 22
    assert real_patch["html_only_count"] == 14
    assert real_patch["unverifiable_after_apply"] == 14
    assert real_patch["accounting"] == {
        "ranged_before": 589,
        "unverifiable": 36,
        "computed_table": 4,
        "total": 629,
    }

    proposals = {item["citation_id"]: item for item in real_patch["proposed_ranges"]}
    html_only = {item["citation_id"]: item for item in real_patch["html_only"]}
    assert all(
        item["source_document_id"] == "form_2441_2025"
        for item in proposals.values()
    ), "the only rangeable backlog left is the 2441 overlay"
    assert "cite_span_form_2441_2025_0012" in proposals
    assert (
        "cite_instruction_schedule_1_2025_en_us_2025_publink1000151499"
        in html_only
    )
    assert all(
        item["reason"] == "quoted text is locatable only in acquired HTML"
        for item in html_only.values()
    )


def test_applied_ranges_are_in_the_graph_and_verify_exactly() -> None:
    graph = load_graph("2025", ROOT)
    citations = {
        str(item["citation_id"]): item for item in graph.items("citations")
    }

    # Rebound by M20-S160 into the acquired HTML byte coordinate space, plus
    # the single-range intake record.
    emphasis = citations["cite_instruction_form_1040_2025_en_us_2025_publink1000106118"]
    assert emphasis["ranges"] == [
        {"start": 330268, "end": 330654},
    ]
    assert citations["cite_intake_13614c_quality"].get("ranges")

    # Deferred, never written: the overlay is content-hash gated and gitignored.
    assert not citations["cite_span_form_2441_2025_0012"].get("ranges")

    report = check_citation_integrity(
        list(citations.values()),
        text_dir=RAW_ROOT / "2025",
        require_ranges=False,
    )
    assert report.ok
    assert not report.mismatches
    assert report.checked == 593
    assert len(report.unverifiable_citations) == 36
    assert report.checked + len(report.unverifiable_citations) == 629


def test_remaining_proposal_still_self_verifies_without_editing_graph(
    real_patch,
) -> None:
    original = load_graph("2025", ROOT).items("citations")
    patched = apply_citation_range_patch(original, real_patch)

    report = check_citation_integrity(
        patched,
        text_dir=RAW_ROOT / "2025",
        require_ranges=False,
    )

    assert report.ok
    assert report.checked == 615
    assert len(report.unverifiable_citations) == 14
    html_only_ids = {entry["citation_id"] for entry in real_patch["html_only"]}
    assert all(
        "ranges" not in item
        for item in original
        if item.get("citation_id") in html_only_ids
    )


def test_applier_appends_to_the_owning_record_and_leaves_the_rest_alone(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "graph" / "2025" / "citations" / "sample.yaml"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(
        "- citation_id: cite_one\n"
        "  document_id: form_1040_2025\n"
        "  quoted_text: first\n"
        "- citation_id: cite_two\n"
        "  document_id: form_1040_2025\n"
        "  quoted_text: second\n",
        encoding="utf-8",
    )
    patch = {
        "year": "2025",
        "proposed_ranges": [
            {"citation_id": "cite_two", "ranges": [{"start": 7, "end": 13}]},
        ],
    }

    result = apply_citation_range_patch_to_files(patch, root=tmp_path)

    assert result["citations_written"] == 1
    assert result["deferred"] == []
    assert artifact.read_text(encoding="utf-8") == (
        "- citation_id: cite_one\n"
        "  document_id: form_1040_2025\n"
        "  quoted_text: first\n"
        "- citation_id: cite_two\n"
        "  document_id: form_1040_2025\n"
        "  quoted_text: second\n"
        "  ranges:\n"
        "  - start: 7\n"
        "    end: 13\n"
    )


def test_applier_refuses_to_overwrite_an_existing_range(tmp_path: Path) -> None:
    artifact = tmp_path / "graph" / "2025" / "citations" / "sample.yaml"
    artifact.parent.mkdir(parents=True)
    before = (
        "- citation_id: cite_one\n"
        "  quoted_text: first\n"
        "  ranges:\n"
        "  - start: 1\n"
        "    end: 2\n"
    )
    artifact.write_text(before, encoding="utf-8")
    patch = {
        "year": "2025",
        "proposed_ranges": [
            {"citation_id": "cite_one", "ranges": [{"start": 9, "end": 9}]},
        ],
    }

    with pytest.raises(ValueError, match="already carries ranges"):
        apply_citation_range_patch_to_files(patch, root=tmp_path)
    assert artifact.read_text(encoding="utf-8") == before


def test_applier_raises_when_no_artifact_holds_the_citation(tmp_path: Path) -> None:
    artifact = tmp_path / "graph" / "2025" / "citations" / "sample.yaml"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("- citation_id: cite_one\n  quoted_text: first\n", encoding="utf-8")

    with pytest.raises(ValueError, match="no citation artifact holds"):
        apply_citation_range_patch_to_files(
            {
                "year": "2025",
                "proposed_ranges": [
                    {"citation_id": "cite_absent", "ranges": [{"start": 1, "end": 2}]},
                ],
            },
            root=tmp_path,
        )


def test_patch_writer_is_ascii_and_reproducible(real_patch, tmp_path: Path) -> None:
    output = write_citation_range_patch(real_patch, tmp_path / "ranges.json")
    loaded = json.loads(output.read_text(encoding="ascii"))

    assert loaded == real_patch
    assert all(ord(character) < 128 for character in output.read_text(encoding="ascii"))
