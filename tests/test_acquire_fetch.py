from __future__ import annotations

import datetime as dt
import hashlib
import json
import os

import pytest

from tax_graph.acquire.fetch import fetch_document
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
    text_path = tmp_path / "2025" / "form_8949_2025.txt"
    metadata_path = tmp_path / "2025" / "form_8949_2025.json"

    assert raw_path.read_bytes() == content
    assert text_path.read_text(encoding="utf-8") == content.decode("utf-8")
    assert metadata.content_hash == hashlib.sha256(content).hexdigest()
    assert metadata.retrieved_date == "2026-06-28"

    recorded = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert recorded["document_id"] == "form_8949_2025"
    assert recorded["url"] == entry.url
    assert recorded["content_hash"] == metadata.content_hash


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
