"""M20-S106 guards for acquired core citation ranges and source-owned gaps."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from pilot.source_extents import measure_source_extents
from tax_graph.acquire.manifest import load_manifest
from tax_graph.acquire.source_ranges import normalize_source_quote
from tax_graph.ingest.core_source_ranges import LEGACY_RANGE_EXEMPTION
from tax_graph.io.loader import load_graph


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]
YEAR = "2025"


def _core_ids() -> set[str]:
    manifest = load_manifest(root=ROOT)
    configured = set(
        yaml.safe_load(
            (ROOT / "config" / "document_tiers.yaml").read_text(encoding="ascii")
        )["core_documents"]
    )
    return {entry.document_id for entry in manifest.documents if entry.document_id in configured}


def _source_slice(citation: dict, source: str) -> str:
    return normalize_source_quote(
        " ".join(
            source[int(item["start"]) : int(item["end"])]
            for item in citation.get("ranges") or ()
        )
    )


def test_core_citations_reconstruct_from_acquired_ranges() -> None:
    """Every non-HTML core citation is a projection of acquired source ranges."""
    core_ids = _core_ids()
    graph = load_graph(YEAR, root=ROOT, include_extensions=False)
    raw_root = ROOT / ".cache" / "raw" / YEAR
    checked = 0
    for citation in graph.items("citations"):
        source_id = str(citation.get("source_document_id") or "")
        locator = str(citation.get("locator") or "")
        if source_id not in core_ids:
            continue
        if locator.casefold().startswith("html#"):
            # HTML is the structural authority; it has its own stable locator.
            continue
        if citation.get("document_id") == LEGACY_RANGE_EXEMPTION:
            continue
        checked += 1
        source = (raw_root / f"{source_id}.txt").read_text(encoding="ascii")
        ranges = citation.get("ranges") or []
        assert ranges, citation["citation_id"]
        assert all(
            0 <= int(item["start"]) < int(item["end"]) <= len(source)
            for item in ranges
        )
        assert _source_slice(citation, source) == normalize_source_quote(
            str(citation["quoted_text"])
        ), citation["citation_id"]
    assert checked >= 500


def test_core_gap_citations_enumerate_the_external_contract() -> None:
    """Promoted rule gaps use only the citation schema's typed vocabulary."""
    core_ids = _core_ids()
    path = ROOT / "graph" / YEAR / "citations" / "source-extents-m106.yaml"
    citations = yaml.safe_load(path.read_text(encoding="ascii")) or []
    schema = json.loads(
        (ROOT / "schemas" / "citation.schema.json").read_text(encoding="ascii")
    )
    validator = jsonschema.Draft202012Validator(schema)
    raw_root = ROOT / ".cache" / "raw" / YEAR

    assert citations
    assert all(item["source_document_id"] in core_ids for item in citations)
    assert all(item["document_id"] == item["source_document_id"] for item in citations)
    assert all(item["kind"] in {"note", "routing_sentence", "table_header"} for item in citations)
    assert all(item["governs"] for item in citations)
    assert len({item["citation_id"] for item in citations}) == len(citations)
    for citation in citations:
        validator.validate(citation)
        source = (raw_root / f"{citation['source_document_id']}.txt").read_text(encoding="ascii")
        assert _source_slice(citation, source) == citation["quoted_text"]


def test_promoted_measurement_preserves_rows_and_clears_core_rule_gaps() -> None:
    """Promotion reduces core rule-bearing source text without changing row coverage."""
    report = measure_source_extents(
        root=ROOT,
        year=YEAR,
        include_promoted_citations=True,
    )
    core_ids = _core_ids()
    remaining = sum(
        item["end"] - item["start"]
        for item in report["unclaimed_runs"]
        if item["partition"] == "rule_bearing"
        and item["source_document_id"] in core_ids
    )
    assert report["counts"]["rows"] == 731
    assert report["counts"]["overlaps"] == 0
    assert remaining == 0
