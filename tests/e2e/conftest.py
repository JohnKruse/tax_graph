"""Browser fixtures for the local M15 review workbench."""

from __future__ import annotations

from pathlib import Path
from threading import Thread
from types import SimpleNamespace

import pytest
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

from workbench.server import create_app


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def page():
    """Own the browser lifecycle per test so no event loop leaks into MCP tests."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        browser_page = browser.new_page()
        try:
            yield browser_page
        finally:
            browser.close()


@pytest.fixture(scope="session")
def workbench_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Serve the real 2025 artifact projection on an ephemeral loopback port."""
    if not (ROOT / "graph" / "2025" / "_drafts").exists():
        pytest.skip("live review drafts are required: fresh checkouts (CI) carry no _drafts")
    state = tmp_path_factory.mktemp("workbench-e2e-state")
    app = create_app(
        ROOT,
        2025,
        write_token="e2e-write-token",
        cache_dir=state / "page_cache",
        state_dir=state / "sessions",
        verdict_dir=state / "verdicts",
        rederive_cell=lambda document_id, line, draft_comment: {
            "document_id": document_id,
            "line": line,
            "comment_source": "draft" if draft_comment else "curated",
            "result": {
                "status": "derived",
                "rendered": f"trial expression for line {line}: {draft_comment or 'curated guidance'}",
                "expression": {"kind": "copy", "source": "form face"},
            },
            "validation": {
                "validator_failures_by_kind": {"quote_not_verbatim": 1},
            },
        },
    )
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


@pytest.fixture
def retry_workbench_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> str:
    """Serve one generated cell so the retry UI can run without provider drafts."""
    cell = {
        "cell_id": "cell_retry_1",
        "document_id": "form_1040_2025",
        "address_id": "2025/document=form_1040/section=income/control=amount",
        "ref": "form_1040_2025/section=income/control=amount",
        "page": 1,
        "rect": [10, 10, 100, 20],
        "display_name": "33 - Total",
        "official_ref": "33",
        "section": "income",
        "control_role": "amount",
        "generated": True,
        "generated_status": "derived",
        "generated_model": "fixture-model",
        "generated_provider": "fixture-provider",
        "policy_origin": "derived",
        "population_policy": "computed",
        "expression": {"text": "line 33 = line 25d + line 26 + line 32", "kind": "sum"},
        "form_citations": [],
        "instruction_citations": [],
        "inputs": [],
    }

    def fake_cells(*_args, **_kwargs):
        return SimpleNamespace(cells=[dict(cell)], page_geometry=[])

    monkeypatch.setattr("workbench.server.build_generated_document_cells", fake_cells)
    monkeypatch.setattr("workbench.server.build_document_cells", fake_cells)
    monkeypatch.setattr("workbench.server.preflight_manifest", lambda _manifest, _bundle: {})
    monkeypatch.setattr(
        "workbench.server.build_documents_index",
        lambda *_args, **_kwargs: [{
            "document_id": "form_1040_2025",
            "title": "Form 1040",
            "cell_count": 1,
            "pages": [1],
            "page_geometry": [],
            "policy_counts": {"computed": 1},
            "citation_counts": {"cited": 0, "uncited": 1},
        }],
    )
    app = create_app(
        ROOT,
        2025,
        write_token="e2e-write-token",
        manifest={"entries": [], "manifest_hash": "a" * 64},
        bundle=SimpleNamespace(
            geometry={"entries": [{"document_id": "form_1040_2025"}], "pages": []},
            graph=SimpleNamespace(
                objects=lambda kind: (
                    [{"document_id": "form_1040_2025", "title": "Form 1040"}]
                    if kind == "documents" else []
                ),
            ),
            pdfs=[],
        ),
        cache_dir=tmp_path / "page_cache",
        state_dir=tmp_path / "sessions",
        verdict_dir=tmp_path / "verdicts",
        rederive_cell=lambda document_id, line, draft_comment: {
            "document_id": document_id,
            "line": line,
            "result": {
                "status": "derived",
                "rendered": f"trial expression for line {line}: {draft_comment or 'curated guidance'}",
            },
            "validation": {"validator_failures_by_kind": {"quote_not_verbatim": 1}},
        },
    )
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
