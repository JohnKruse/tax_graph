"""M20-S133 guards for the acquired source-range coordinate contract."""

from __future__ import annotations

import pytest

from tax_graph.acquire.source_ranges import (
    SourceDocumentNotFound,
    SourceRangeOutOfBounds,
    resolve_source_range,
)


def test_resolve_source_range_uses_universal_newline_character_offsets(tmp_path):
    text_dir = tmp_path / "2025"
    text_dir.mkdir()
    (text_dir / "crlf_source.txt").write_bytes(b"alpha\r\nbeta\r\n")
    (text_dir / "plain_source.txt").write_text("alpha\nbeta\n", encoding="utf-8")

    assert resolve_source_range("crlf_source", 6, 10, text_dir=text_dir) == "beta"
    assert resolve_source_range("plain_source", 6, 10, text_dir=text_dir) == "beta"


def test_resolve_source_range_reports_typed_absence(tmp_path):
    with pytest.raises(SourceDocumentNotFound):
        resolve_source_range("missing_source", 0, 1, text_dir=tmp_path)

    source_path = tmp_path / "source.txt"
    source_path.write_text("short", encoding="utf-8")
    with pytest.raises(SourceRangeOutOfBounds):
        resolve_source_range("source", 0, 6, text_dir=tmp_path)


def test_resolve_source_range_accepts_already_loaded_acquired_text():
    assert resolve_source_range("source", 1, 4, source_text="alpha") == "lph"
