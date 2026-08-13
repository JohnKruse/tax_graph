"""M20-S105 regression coverage for source-owned worksheet citation ranges."""

from __future__ import annotations

import json
from pathlib import Path
import re

import jsonschema
import pytest

from pilot.source_extents import measure_source_extents
from tax_graph.acquire.manifest import load_manifest
from tax_graph.io.loader import load_graph


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]


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
