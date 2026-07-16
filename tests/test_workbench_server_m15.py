"""Local Flask API tests for M15 S7."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from workbench.server import create_app


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def client():
    app = create_app(ROOT, 2025, write_token="test-write-token")
    app.config.update(TESTING=True)
    return app.test_client()


@pytest.mark.m15
def test_queue_api_groups_pending_entries_and_reports_progress(client) -> None:
    response = client.get("/api/queue")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["tax_year"] == 2025
    assert len(payload["manifest_hash"]) == 64
    assert payload["progress"]["total_entries"] == 35
    assert payload["progress"]["remaining_entries"] == 35
    assert payload["progress"]["total_units"] == payload["coverage"]["units"]
    assert payload["groups"] == sorted(payload["groups"], key=lambda group: group["review_kind"])
    assert all(group["entries"] for group in payload["groups"])


@pytest.mark.m15
def test_entry_api_returns_only_the_requested_scoped_units(client) -> None:
    queue = client.get("/api/queue").get_json()
    selected = queue["groups"][0]["entries"][0]

    response = client.get(f"/api/entries/{selected['queue_id']}")
    missing = client.get("/api/entries/not_a_queue_id")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["entry"]["queue_id"] == selected["queue_id"]
    assert len(payload["entry"]["units"]) == selected["unit_count"]
    assert all(unit["queue_id"] == selected["queue_id"] for unit in payload["entry"]["units"])
    assert missing.status_code == 404
    assert missing.get_json()["error"] == "unknown queue_id"


@pytest.mark.m15
def test_read_apis_do_not_mutate_authoritative_artifacts(client) -> None:
    paths = [
        ROOT / "build" / "tax_graph_2025.sqlite",
        ROOT / "review_queue" / "2025" / "deferred_review.yaml",
        ROOT / "graph" / "2025" / "node_geometry.json",
    ]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}

    queue = client.get("/api/queue").get_json()
    for group in queue["groups"]:
        client.get(f"/api/entries/{group['entries'][0]['queue_id']}")

    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    assert after == before
