"""M20-S106 guards for acquired core citation ranges and packet reachability."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest
import yaml

from tax_graph.extract.cells import build_cell_frame_from_document
from tax_graph.extract.inputs import load_document_input
from pilot.source_extents import measure_source_extents
from tax_graph.acquire.manifest import load_manifest
from tax_graph.acquire.source_ranges import normalize_source_quote
from tax_graph.ingest.core_source_ranges import (
    COMPUTED_TABLE_CITATION_IDS,
    COMPUTED_TABLE_KIND,
    LEGACY_RANGE_EXEMPTION,
    PARAPHRASE_CITATION_IDS,
)
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


def _citation_records() -> dict[str, dict]:
    return {
        str(item["citation_id"]): item
        for path in sorted((ROOT / "graph" / YEAR / "citations").glob("*.yaml"))
        for item in (yaml.safe_load(path.read_text(encoding="ascii")) or [])
        if item.get("citation_id")
    }


def _baseline_quote_text() -> dict[str, object]:
    baseline: dict[str, object] = {}
    for path in sorted((ROOT / "graph" / YEAR / "citations").glob("*.yaml")):
        result = subprocess.run(
            ["git", "show", f"82962eb:{path.relative_to(ROOT).as_posix()}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            continue
        for item in yaml.safe_load(result.stdout) or []:
            if item.get("citation_id"):
                baseline[str(item["citation_id"])] = item.get("quoted_text")

    return baseline


def test_s107_reextracts_exactly_the_named_paraphrases() -> None:
    """Only the 30 named A9 paraphrases may change their quote text."""
    baseline = _baseline_quote_text()
    current = _citation_records()
    changed = {
        citation_id
        for citation_id, item in current.items()
        if citation_id in baseline
        and citation_id not in COMPUTED_TABLE_CITATION_IDS
        and item.get("quoted_text") != baseline[citation_id]
    }
    assert changed == set(PARAPHRASE_CITATION_IDS)
    assert len(changed) == 30
    assert all(
        citation_id in current and current[citation_id].get("quoted_text")
        for citation_id in PARAPHRASE_CITATION_IDS
    )


def test_s107_types_computed_bracket_citations_without_quote_text() -> None:
    """Bracket results carry typed table provenance rather than synthetic prose."""
    current = _citation_records()
    assert set(COMPUTED_TABLE_CITATION_IDS) <= set(current)
    for citation_id in COMPUTED_TABLE_CITATION_IDS:
        citation = current[citation_id]
        assert citation["kind"] == COMPUTED_TABLE_KIND
        assert citation["ranges"]
        assert citation["derivation"]
        assert "quoted_text" not in citation


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
        if citation.get("kind") == COMPUTED_TABLE_KIND:
            assert citation.get("derivation")
            continue
        assert _source_slice(citation, source) == normalize_source_quote(
            str(citation["quoted_text"])
        ), citation["citation_id"]
    # The rework removes the 74 unreferenced source-gap records. The invariant
    # applies to every citation that remains, rather than to the old artifact's
    # record count.
    assert checked > 0


def test_unclaimed_core_gaps_are_not_promoted_without_a_reachable_consumer() -> None:
    """The measurement aid cannot become a graph citation by itself."""
    graph = load_graph(YEAR, root=ROOT, include_extensions=False)
    path = ROOT / "graph" / YEAR / "citations" / "source-extents-m106.yaml"
    assert not path.exists()
    assert not any(
        str(item.get("citation_id") or "").startswith("cite_")
        and "_source_" in str(item.get("citation_id") or "")
        for item in graph.items("citations")
    )


def test_source_gap_measurement_remains_nonzero_after_range_rebinding() -> None:
    """Range binding must not claim source gaps merely by relabeling them."""
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
    assert remaining > 0


@pytest.mark.parametrize(
    ("document_id", "line", "required_text"),
    (
        ("simplified_method_worksheet_2025", "4", "last year's worksheet on line 4"),
        ("state_and_local_income_tax_refund_worksheet_2025", "8", "married filing separately"),
        ("state_and_local_income_tax_refund_worksheet_2025", "9", "married filing separately"),
    ),
)
def test_existing_governed_chunks_reach_row_derivation_packets(
    document_id: str,
    line: str,
    required_text: str,
) -> None:
    """A governed source chunk is useful only when the row packet receives it."""
    document = load_document_input(document_id, year=YEAR, root=ROOT)
    frame = build_cell_frame_from_document(document)
    row = next(item for item in frame.rows if item.line == line)
    provenance = row.metadata.get("governed_note_provenance") or []
    assert provenance
    packet = " ".join(
        (
            row.form_face_text,
            row.instruction_text,
            " ".join(str(item.get("text") or "") for item in provenance),
        )
    ).casefold()
    assert required_text.casefold() in packet
    assert any(
        required_text.casefold() in str(item.get("text") or "").casefold()
        for item in provenance
    )
