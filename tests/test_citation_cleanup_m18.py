from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.acquire.citation_cleanup import derive_clean_quote, infer_source_document_id
from tax_graph.io.loader import load_graph


@pytest.mark.m18
@pytest.mark.parametrize(
    ("quoted_text", "expected"),
    [
        ("- z: Add lines 1a through 1h 1z", "Add lines 1a through 1h"),
        ("- g: Wages from Form 8919, line 6 1g", "Wages from Form 8919, line 6"),
        ("- 1: a Total amount from Form(s) W-2, box 1 (see instructions) 1a", "Total amount from Form(s) W-2, box 1 (see instructions)"),
        ("- 1b:", "1b"),
    ],
)
def test_derive_clean_quote_removes_extraction_scaffolding(quoted_text: str, expected: str):
    citation = {"quoted_text": quoted_text, "source_document_id": "form_1040_2025"}
    result = derive_clean_quote(citation, quoted_text)
    assert result.quoted_text == expected
    assert result.changed is True
    assert result.reason is None


@pytest.mark.m18
def test_derive_clean_quote_fails_closed_when_source_does_not_verify():
    citation = {"quoted_text": "- z: Add lines 1a through 1h 1z"}
    result = derive_clean_quote(citation, "a different acquired source")
    assert result.quoted_text == citation["quoted_text"]
    assert result.changed is False
    assert result.reason == "cleaned quote not found in acquired source"


@pytest.mark.m18
def test_infer_source_document_id_only_uses_exact_available_document():
    assert infer_source_document_id(
        {"document_id": "form_1040_2025"},
        available_source_ids={"form_1040_2025"},
    ) == "form_1040_2025"
    assert infer_source_document_id(
        {"document_id": "instructions_form_1040_2025"},
        available_source_ids={"form_1040_2025"},
    ) is None


@pytest.mark.m18
def test_real_citation_corpus_has_source_verified_cleanups():
    raw_root = Path(".cache/raw/2025")
    if not raw_root.exists():
        pytest.skip("acquired 2025 raw corpus is not present")
    graph = load_graph("2025")
    available = {path.stem for path in raw_root.glob("*.txt")}
    wrapped = 0
    cleaned = 0
    for citation in graph.items("citations"):
        source_id = infer_source_document_id(citation, available_source_ids=available)
        if not str(citation.get("quoted_text", "")).startswith("- "):
            continue
        wrapped += 1
        assert source_id is not None
        source_text = (raw_root / f"{source_id}.txt").read_text(encoding="utf-8")
        result = derive_clean_quote(citation, source_text)
        assert result.reason is None, citation["citation_id"]
        assert result.changed is True, citation["citation_id"]
        cleaned += 1
    assert wrapped == cleaned
