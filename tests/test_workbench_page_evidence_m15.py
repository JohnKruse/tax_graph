"""Lazy page rendering and evidence API tests for M15 S8."""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench.server import create_app


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m15
def test_page_api_renders_only_requested_page_and_reuses_cache(tmp_path: Path) -> None:
    calls: list[tuple[str, int, float]] = []

    def renderer(pdf_path: Path, page: int, scale: float) -> bytes:
        calls.append((pdf_path.stem, page, scale))
        return b"\x89PNG\r\n\x1a\n" + f"{pdf_path.stem}:{page}:{scale}".encode("ascii")

    app = create_app(ROOT, 2025, page_renderer=renderer, cache_dir=tmp_path / "cache")
    app.config.update(TESTING=True)
    client = app.test_client()
    document_id = app.config["WORKBENCH_BUNDLE"].pdfs[0].path.stem

    first = client.get(f"/api/documents/{document_id}/pages/1.png?scale=1.5")
    repeated = client.get(f"/api/documents/{document_id}/pages/1.png?scale=1.5")
    second_page = client.get(f"/api/documents/{document_id}/pages/2.png?scale=1.5")

    assert first.status_code == repeated.status_code == second_page.status_code == 200
    assert first.mimetype == "image/png"
    assert first.data == repeated.data
    assert calls == [(document_id, 1, 1.5), (document_id, 2, 1.5)]
    assert len(list((tmp_path / "cache").glob("*.png"))) == 2


@pytest.mark.m15
def test_page_api_rejects_unknown_documents_and_bad_scale(tmp_path: Path) -> None:
    app = create_app(ROOT, 2025, page_renderer=lambda *_: b"png", cache_dir=tmp_path)
    app.config.update(TESTING=True)
    client = app.test_client()
    document_id = app.config["WORKBENCH_BUNDLE"].pdfs[0].path.stem

    assert client.get("/api/documents/not_a_document/pages/1.png").status_code == 404
    assert client.get(f"/api/documents/{document_id}/pages/1.png?scale=99").status_code == 400


@pytest.mark.m15
def test_evidence_api_returns_compiled_and_draft_objects() -> None:
    app = create_app(ROOT, 2025)
    app.config.update(TESTING=True)
    client = app.test_client()

    compiled = client.get("/api/evidence/decision/decision_1040_deduction_method")
    draft = client.get("/api/evidence/node/form_1040_2025_root_line_12a")
    missing = client.get("/api/evidence/node/not_a_node")

    assert compiled.status_code == 200
    assert compiled.get_json()["raw"]["decision_id"] == "decision_1040_deduction_method"
    assert compiled.get_json()["queue_units"]
    assert draft.status_code == 200
    assert draft.get_json()["raw"]["node_id"] == "form_1040_2025_root_line_12a"
    assert "/_drafts/" in draft.get_json()["source_artifact"]
    assert missing.status_code == 404
