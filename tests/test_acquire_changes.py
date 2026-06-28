from __future__ import annotations

import json

import pytest

from tax_graph.acquire.changes import detect_changes, load_state, state_path, write_state
from tax_graph.acquire.changes import DocumentState
from tax_graph.acquire.fetch import FetchedDocument


def _fetched(document_id: str, content_hash: str) -> FetchedDocument:
    return FetchedDocument(
        document_id=document_id,
        url=f"https://www.irs.gov/pub/irs-pdf/{document_id}.pdf",
        content_hash=content_hash,
        retrieved_date="2026-06-28",
        raw_path=f"{document_id}.pdf",
        metadata_path=f"{document_id}.json",
    )


@pytest.mark.m3
def test_detect_changes_reports_new_and_writes_state(tmp_path):
    report = detect_changes([_fetched("f8949", "hash-a")], raw_store=tmp_path, year=2025)

    assert report.new == ["f8949"]
    assert report.changed == []
    assert report.unchanged == []
    assert load_state(tmp_path, 2025)["f8949"].content_hash == "hash-a"


@pytest.mark.m3
def test_detect_changes_reports_changed_and_unchanged(tmp_path):
    write_state(
        tmp_path,
        2025,
        {
            "f8949": DocumentState(
                content_hash="old-hash",
                retrieved_date="2026-06-27",
                url="https://www.irs.gov/pub/irs-pdf/f8949.pdf",
            ),
            "i8949": DocumentState(
                content_hash="same-hash",
                retrieved_date="2026-06-27",
                url="https://www.irs.gov/pub/irs-pdf/i8949.pdf",
            ),
        },
    )

    report = detect_changes(
        [_fetched("f8949", "new-hash"), _fetched("i8949", "same-hash")],
        raw_store=tmp_path,
        year=2025,
    )

    assert report.changed == ["f8949"]
    assert report.unchanged == ["i8949"]
    state = load_state(tmp_path, 2025)
    assert state["f8949"].content_hash == "new-hash"


@pytest.mark.m3
def test_check_mode_does_not_write_state(tmp_path):
    write_state(
        tmp_path,
        2025,
        {
            "f8949": DocumentState(
                content_hash="old-hash",
                retrieved_date="2026-06-27",
                url="https://www.irs.gov/pub/irs-pdf/f8949.pdf",
            )
        },
    )
    before = json.loads(state_path(tmp_path, 2025).read_text(encoding="utf-8"))

    report = detect_changes([_fetched("f8949", "new-hash")], raw_store=tmp_path, year=2025, check=True)

    after = json.loads(state_path(tmp_path, 2025).read_text(encoding="utf-8"))
    assert report.changed == ["f8949"]
    assert after == before
