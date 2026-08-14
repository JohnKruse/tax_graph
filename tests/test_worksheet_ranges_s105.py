"""M20-S105 regression coverage for source-owned worksheet citation ranges."""

from __future__ import annotations

import json
from pathlib import Path
import re

import jsonschema
import pytest
import yaml

from pilot.source_extents import measure_source_extents
from tax_graph.acquire.manifest import load_manifest
from tax_graph.io.loader import load_graph


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]
LEGACY_RANGE_EXEMPTION = "negative_form_8978_adjustment_worksheet_schedule_2_2025"


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def test_promoted_worksheet_citations_reconstruct_from_source_ranges() -> None:
    """Every promoted worksheet quote is regenerated from its acquired bytes."""
    manifest = load_manifest(root=ROOT)
    region_ids = {entry.document_id for entry in manifest.documents if entry.is_region}
    graph = load_graph("2025", root=ROOT, include_extensions=False)
    schema = json.loads((ROOT / "schemas" / "citation.schema.json").read_text(encoding="ascii"))
    validator = jsonschema.Draft202012Validator(schema)
    raw_root = ROOT / ".cache" / "raw" / "2025"
    citations = [item for item in graph.items("citations") if item.get("document_id") in region_ids]

    assert citations
    for citation in citations:
        validator.validate({key: value for key, value in citation.items() if key != "gate"})
        if citation["document_id"] == LEGACY_RANGE_EXEMPTION:
            # This legacy region has no reliable HTML heading and remains on
            # its pre-S105 citation path until that source defect is decided.
            continue
        source_id = str(citation["source_document_id"])
        source = (raw_root / f"{source_id}.txt").read_text(encoding="ascii")
        ranges = citation["ranges"]
        assert all(0 <= item["start"] < item["end"] <= len(source) for item in ranges)
        reconstructed = _normalize(
            " ".join(source[item["start"] : item["end"]] for item in ranges)
        )
        assert citation["quoted_text"] == reconstructed, citation["citation_id"]


def test_source_extents_preserves_the_worksheet_corpus_partition() -> None:
    """The range migration keeps all 731 form-face rows and no overlaps."""
    report = measure_source_extents(root=ROOT, year="2025")
    assert report["counts"]["rows"] == 731
    assert report["counts"]["overlaps"] == 0


def test_promoted_core_citations_reconstruct_from_source_ranges() -> None:
    """Every Markdown-backed core citation is reconstructed from acquired bytes."""
    tiers = yaml.safe_load(
        (ROOT / "config" / "document_tiers.yaml").read_text(encoding="ascii")
    )
    core_ids = set(tiers["core_documents"])
    graph = load_graph("2025", root=ROOT, include_extensions=False)
    schema = json.loads(
        (ROOT / "schemas" / "citation.schema.json").read_text(encoding="ascii")
    )
    validator = jsonschema.Draft202012Validator(schema)
    raw_root = ROOT / ".cache" / "raw" / "2025"
    citations = [
        item
        for item in graph.items("citations")
        if item.get("source_document_id") in core_ids
        and not str(item.get("locator") or "").casefold().startswith("html#")
        and item.get("document_id") != LEGACY_RANGE_EXEMPTION
    ]

    assert citations
    for citation in citations:
        validator.validate({key: value for key, value in citation.items() if key != "gate"})
        source_id = str(citation["source_document_id"])
        source = (raw_root / f"{source_id}.txt").read_text(encoding="utf-8")
        ranges = citation.get("ranges") or []
        assert ranges, citation["citation_id"]
        assert all(0 <= item["start"] < item["end"] <= len(source) for item in ranges)
        reconstructed = _normalize(
            " ".join(source[item["start"] : item["end"]] for item in ranges)
        )
        assert _normalize(citation["quoted_text"]) == reconstructed, citation["citation_id"]


def test_core_source_gap_citations_are_typed_and_governed() -> None:
    """Rule-bearing promoted gaps retain their source range and line ownership."""
    tiers = yaml.safe_load(
        (ROOT / "config" / "document_tiers.yaml").read_text(encoding="ascii")
    )
    core_ids = set(tiers["core_documents"])
    citations = yaml.safe_load(
        (ROOT / "graph" / "2025" / "citations" / "source-extents-m106.yaml").read_text(
            encoding="ascii"
        )
    )

    assert citations
    assert all(item["source_document_id"] in core_ids for item in citations)
    assert all(item["document_id"] == item["source_document_id"] for item in citations)
    assert all(item["kind"] in {"note", "routing_sentence", "table_header"} for item in citations)
    assert all(item["governs"] for item in citations)
    assert len({item["citation_id"] for item in citations}) == len(citations)
