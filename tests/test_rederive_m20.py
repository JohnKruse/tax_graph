"""M20-S37 tests for the non-persisting single-cell review loop."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tax_graph.extract.cells import CellFrame
from tax_graph.extract import rederive
from workbench.address_verdicts import append_address_verdict


pytestmark = pytest.mark.m20


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def structured_completion(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def _frame() -> CellFrame:
    return CellFrame.from_rows([
        {
            "form": "form_a_2025",
            "line": "18",
            "label": "Tax amount",
            "form_face_text": "Multiply line 17 by the rate.",
            "instruction_text": "Multiply line 17 by the rate.",
            "instruction_locator": "face_18",
            "metadata": {
                "evidence_spans": [
                    {"span_id": "face_18", "text": "Multiply line 17 by the rate."},
                ],
            },
        },
    ])


def _config(tmp_path: Path) -> dict:
    prompt = tmp_path / "cells.md"
    prompt.write_text("human: <<human_comment>>\nline: <<line>>", encoding="ascii")
    return {
        "llm": {"model": "mock-model", "micro_model": "mock-model", "temperature": 0},
        "extraction": {"prompts": {"cells": str(prompt)}},
    }


def test_rederive_cell_returns_result_and_does_not_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rederive, "load_document_input", lambda *args, **kwargs: object())
    monkeypatch.setattr(rederive, "build_cell_frame_from_document", lambda document: _frame())
    config = _config(tmp_path)
    client = FakeClient({
        "expression": {"op": "COPY", "args": [{"line": "17"}]},
        "quote": "Multiply line 17 by the rate.",
    })
    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))

    result = rederive.rederive_cell(
        "form_a_2025",
        "18",
        "Use the threshold printed on the form.",
        year=2025,
        root=tmp_path,
        config=config,
        client=client,
    )

    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    assert before == after
    assert result["comment_source"] == "draft"
    assert result["comment"] == "Use the threshold printed on the form."
    assert result["result"]["status"] == "derived"
    assert result["validation"]["attempted"] == 1
    assert "Use the threshold printed on the form." in client.calls[0]["prompt"]
    assert client.calls[0]["temperature"] is None


def test_rederive_cell_uses_latest_curated_comment_when_no_draft(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rederive, "load_document_input", lambda *args, **kwargs: object())
    monkeypatch.setattr(rederive, "build_cell_frame_from_document", lambda document: _frame())
    address = "2025/document=form_a/line=18/control=amount"
    ledger = tmp_path / "address_verdicts.jsonl"
    append_address_verdict(
        root=tmp_path,
        year=2025,
        address=address,
        label="Tax amount",
        cited_text=["Multiply line 17 by the rate."],
        reviewer_id="john",
        reviewed_at="2026-07-29T10:00:00+00:00",
        verdict_id="curated_rederive_1",
        comment="Use the printed threshold.",
        origin="curated",
        store_path=ledger,
    )
    client = FakeClient({
        "expression": {"op": "COPY", "args": [{"line": "17"}]},
        "quote": "Multiply line 17 by the rate.",
    })

    result = rederive.rederive_cell(
        "form_a_2025",
        "18",
        year=2025,
        root=tmp_path,
        config=_config(tmp_path),
        client=client,
        comment_history=[json.loads(ledger.read_text(encoding="utf-8"))],
    )

    assert result["comment_source"] == "curated"
    assert result["comment"] == "Use the printed threshold."
    assert "Use the printed threshold." in client.calls[0]["prompt"]
