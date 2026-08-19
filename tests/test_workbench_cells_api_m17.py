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
def test_documents_api_reports_a_complete_recognized_policy_histogram(client) -> None:
    """Every generated form cell has one recognized population policy."""
    payload = client.get("/api/documents").get_json()
    assert payload["tax_year"] == 2025
    assert any(item["document_id"] == "form_1040_2025" for item in payload["documents"])
    assert all(item["cell_count"] > 0 for item in payload["documents"])
    form_1040 = next(item for item in payload["documents"] if item["document_id"] == "form_1040_2025")
    cells = client.get("/api/documents/form_1040_2025/cells").get_json()["cells"]
    allowed = {"computed", "copied", "decision_required", "unsupported", "user_entered"}
    policy_counts = form_1040["policy_counts"]

    assert len(cells) == form_1040["cell_count"]
    assert all(
        isinstance(cell.get("population_policy"), str)
        and cell["population_policy"] in allowed
        for cell in cells
    )
    assert set(policy_counts) <= allowed
    assert all(isinstance(count, int) and count > 0 for count in policy_counts.values())
    assert sum(policy_counts.values()) == len(cells)


@pytest.mark.m17
def test_generated_documents_open_and_report_unplaceable_rows(client) -> None:
    """A decision guard checks question shape, not regenerated IRS wording."""
    response = client.get("/api/documents")
    assert response.status_code == 200, response.get_data(as_text=True)
    payload = response.get_json()
    documents = {item["document_id"]: item for item in payload["documents"]}
    expected = {"form_1040_2025", "schedule_1_2025", "schedule_a_2025"}
    assert expected <= documents.keys()
    assert all("unplaceable_count" in documents[document_id] for document_id in expected)

    schedule_a = client.get("/api/documents/schedule_a_2025/cells")
    assert schedule_a.status_code == 200, schedule_a.get_data(as_text=True)
    schedule_a_payload = schedule_a.get_json()
    assert any(
        cell.get("control_role") == "checkbox"
        and isinstance(decision.get("question"), str)
        and decision["question"].strip().endswith("?")
        and decision["question"].strip().lower() not in {"", "?", "unknown", "n/a", "none", "placeholder"}
        and decision["anchor"] == "5a"
        for cell in schedule_a_payload["cells"]
        for decision in cell.get("decisions", [])
    )
    for document_id in expected:
        document_cells = client.get(f"/api/documents/{document_id}/cells")
        assert document_cells.status_code == 200, document_cells.get_data(as_text=True)
        assert all(
            row["label"] and row["kind"] and row["reason"]
            for row in document_cells.get_json().get("unplaceable", [])
        )


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
