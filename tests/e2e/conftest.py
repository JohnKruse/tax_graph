"""Browser fixtures for the local M15 review workbench."""

from __future__ import annotations

from pathlib import Path
from threading import Thread

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
def workbench_url() -> str:
    """Serve the real 2025 artifact projection on an ephemeral loopback port."""
    app = create_app(ROOT, 2025, write_token="e2e-write-token")
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
