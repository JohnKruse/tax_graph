from __future__ import annotations

import datetime as dt
import hashlib
import json
import os

import pytest

from tax_graph.acquire.fetch import fetch_document, fetch_instruction_html
from tax_graph.acquire.manifest import ManifestEntry


@pytest.mark.m3
def test_fetch_document_stores_raw_text_hash_and_metadata(tmp_path):
    content = b"Fake IRS PDF text for deterministic tests."
    entry = ManifestEntry(
        document_id="form_8949_2025",
        kind="tax_form",
        url="https://www.irs.gov/pub/irs-pdf/f8949.pdf",
    )

    metadata = fetch_document(
        entry,
        year=2025,
        raw_store=tmp_path,
        fetch_bytes=lambda url, config: content,
        today=dt.date(2026, 6, 28),
    )

    raw_path = tmp_path / "2025" / "form_8949_2025.pdf"
    metadata_path = tmp_path / "2025" / "form_8949_2025.json"

    assert raw_path.read_bytes() == content
    assert metadata.content_hash == hashlib.sha256(content).hexdigest()
    assert metadata.retrieved_date == "2026-06-28"

    recorded = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert recorded["document_id"] == "form_8949_2025"
    assert recorded["url"] == entry.url
    assert recorded["content_hash"] == metadata.content_hash


@pytest.mark.m18
def test_fetch_instruction_html_stores_ascii_content_and_provenance(tmp_path):
    source = "<html><h2 id=\"id1\">Line 1 - Taxable \u201cIncome\u201d \u2014 2025</h2></html>".encode("utf-8")
    entry = ManifestEntry(
        document_id="instructions_form_1040_2025",
        kind="instructions",
        url="https://www.irs.gov/pub/irs-prior/i1040gi--2025.pdf",
        instruction_url="https://www.irs.gov/instructions/i1040gi",
    )

    metadata = fetch_instruction_html(
        entry,
        year=2025,
        raw_store=tmp_path,
        fetch_bytes=lambda url, config: source,
        today=dt.date(2026, 7, 27),
    )

    raw_path = tmp_path / "2025" / "instructions_form_1040_2025.html"
    metadata_path = tmp_path / "2025" / "instructions_form_1040_2025.html.json"
    stored = raw_path.read_bytes()
    assert stored == b'<html><h2 id="id1">Line 1 - Taxable "Income" - 2025</h2></html>'
    assert stored.decode("ascii")
    assert metadata.content_hash == hashlib.sha256(stored).hexdigest()
    assert json.loads(metadata_path.read_text(encoding="utf-8"))["url"] == entry.instruction_url


@pytest.mark.network
@pytest.mark.skipif(
    os.environ.get("TAX_GRAPH_RUN_NETWORK_TESTS") != "1",
    reason="live network tests are opt-in",
)
def test_network_fetch_one_small_irs_doc(tmp_path):
    pytest.importorskip("httpx")
    entry = ManifestEntry(
        document_id="form_8949_2025",
        kind="tax_form",
        url="https://www.irs.gov/pub/irs-pdf/f8949.pdf",
    )

    metadata = fetch_document(entry, year=2025, raw_store=tmp_path)

    assert metadata.content_hash
