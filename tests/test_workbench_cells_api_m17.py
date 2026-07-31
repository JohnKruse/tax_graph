"""M17 document-centric review API tests.

These tests are intentionally separate from the pure cell-inventory projection tests:
creating the Flask app runs the live review preflight and is too slow for the Worker
launcher budget. The fixture also redirects all writable workbench state to pytest's
temporary directory so API round trips cannot pollute the developer's live session.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench.server import create_app


ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    not (ROOT / "graph" / "2025" / "_drafts").exists(),
    reason="live review drafts are required: fresh checkouts (CI) carry no _drafts",
)


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory):
    state = tmp_path_factory.mktemp("m17-workbench-state")
    app = create_app(
        ROOT,
        2025,
        write_token="test-write-token",
        state_dir=state / "sessions",
        cache_dir=state / "pages",
        verdict_dir=state / "verdicts",
    )
    app.config.update(TESTING=True)
    return app.test_client()


@pytest.mark.m17
def test_documents_api_lists_forms(client) -> None:
    payload = client.get("/api/documents").get_json()
    assert payload["tax_year"] == 2025
    assert any(item["document_id"] == "form_1040_2025" for item in payload["documents"])
    assert all(item["cell_count"] > 0 for item in payload["documents"])
    form_1040 = next(item for item in payload["documents"] if item["document_id"] == "form_1040_2025")
    assert form_1040["policy_counts"] == {
        "computed": 14,
        "copied": 2,
        "review_gap": 40,
        "user_entered": 1,
    }


@pytest.mark.m17
def test_document_cells_api_returns_ordered_cells(client) -> None:
    response = client.get("/api/documents/form_1040_2025/cells")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["document_id"] == "form_1040_2025"
    assert payload["pages"] == sorted(payload["pages"])
    assert payload["cells"], "the 1040 has cells"
    assert client.get("/api/documents/not_a_form/cells").status_code == 404


@pytest.mark.m17
def test_document_session_round_trip_and_scope(client) -> None:
    session = client.get("/api/documents/form_1040_2025/session").get_json()
    assert session["queue_id"] == "form_1040_2025"
    assert session["progress"]["total"] > 0
    cells = client.get("/api/documents/form_1040_2025/cells").get_json()["cells"]
    target = cells[0]["cell_id"]
    session["unit_reviews"] = {
        target: {"status": "approved", "note": "ok", "updated_at": "2026-07-24T00:00:00+00:00"}
    }
    session["current_unit_id"] = target
    session.pop("progress", None)
    saved = client.put(
        "/api/documents/form_1040_2025/session",
        json=session,
        headers={"X-Workbench-Token": "test-write-token"},
    )
    assert saved.status_code == 200, saved.get_json()
    assert saved.get_json()["progress"]["approved"] == 1
    # A review keyed to a cell outside the document is rejected.
    session["unit_reviews"]["not_a_cell_here"] = {
        "status": "approved", "note": "", "updated_at": "2026-07-24T00:00:00+00:00"
    }
    bad = client.put(
        "/api/documents/form_1040_2025/session",
        json=session,
        headers={"X-Workbench-Token": "test-write-token"},
    )
    assert bad.status_code == 400


@pytest.mark.m17
def test_document_session_requires_write_token(client) -> None:
    session = client.get("/api/documents/form_1040_2025/session").get_json()
    session.pop("progress", None)
    denied = client.put("/api/documents/form_1040_2025/session", json=session)
    assert denied.status_code == 403
