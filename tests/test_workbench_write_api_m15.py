"""Session and append-only verdict API tests for M15 S9."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from workbench.server import create_app
from workbench.verdicts import load_verdict


ROOT = Path(__file__).resolve().parents[1]
TOKEN = "s9-test-token"


@pytest.fixture(scope="module")
def api(tmp_path_factory: pytest.TempPathFactory):
    temporary = tmp_path_factory.mktemp("s9-api")
    app = create_app(
        ROOT,
        2025,
        write_token=TOKEN,
        state_dir=temporary / "sessions",
        verdict_dir=temporary / "verdicts",
        cache_dir=temporary / "pages",
    )
    app.config.update(TESTING=True)
    return app, app.test_client()


@pytest.mark.m15
def test_session_get_put_requires_token_and_round_trips_schema_valid_state(api) -> None:
    app, client = api
    queue_id = next(iter(app.config["WORKBENCH_MANIFEST"]["entries"]))["queue_id"]
    initial = client.get(f"/api/sessions/{queue_id}")
    state = initial.get_json()
    state.update(notes="Check the official line.", elapsed_active_seconds=12.5, visited_unit_ids=[state["current_unit_id"]])

    denied = client.put(f"/api/sessions/{queue_id}", json=state)
    saved = client.put(f"/api/sessions/{queue_id}", json=state, headers=_headers())
    loaded = client.get(f"/api/sessions/{queue_id}")

    assert initial.status_code == 200
    assert denied.status_code == 403
    assert saved.status_code == 200
    assert loaded.get_json() == state
    session_path = app.config["WORKBENCH_SESSION_ROOT"] / f"{queue_id}.json"
    assert json.loads(session_path.read_text(encoding="utf-8")) == state


@pytest.mark.m15
def test_verdict_api_rejects_missing_token_tampering_and_duplicates(api) -> None:
    app, client = api
    queue_id = app.config["WORKBENCH_MANIFEST"]["entries"][0]["queue_id"]
    payload = {
        "queue_id": queue_id,
        "verdict_id": "s9_api_verdict_1",
        "reviewer_id": "john",
        "human_minutes": 1.5,
        "verdict": "confirmed",
        "reviewed_at": "2026-07-14T12:00:00Z",
    }

    assert client.post("/api/verdicts", json=payload).status_code == 403
    tampered = {**payload, "content_hash": "0" * 64}
    assert client.post("/api/verdicts", json=tampered, headers=_headers()).status_code == 400
    created = client.post("/api/verdicts", json=payload, headers=_headers())
    duplicate = client.post("/api/verdicts", json=payload, headers=_headers())

    assert created.status_code == 201
    assert duplicate.status_code == 409
    path = app.config["WORKBENCH_VERDICT_ROOT"] / created.get_json()["path"]
    loaded = load_verdict(path, schema_path=ROOT / "schemas" / "review_verdict.schema.json")
    assert loaded.payload == created.get_json()["verdict"]


@pytest.mark.m15
def test_write_apis_never_mutate_graph_queue_tier_or_provenance(api) -> None:
    app, client = api
    paths = [
        ROOT / "build" / "tax_graph_2025.sqlite",
        ROOT / "review_queue" / "2025" / "deferred_review.yaml",
        ROOT / "graph" / "2025" / "node_geometry.json",
    ]
    provenance = sorted((ROOT / "review_provenance").rglob("*")) if (ROOT / "review_provenance").exists() else []
    files = paths + [path for path in provenance if path.is_file()]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    queue_id = app.config["WORKBENCH_MANIFEST"]["entries"][1]["queue_id"]
    state = client.get(f"/api/sessions/{queue_id}").get_json()

    assert client.put(f"/api/sessions/{queue_id}", json=state, headers=_headers()).status_code == 200
    verdict = {
        "queue_id": queue_id,
        "verdict_id": "s9_api_verdict_2",
        "reviewer_id": "john",
        "human_minutes": 0.5,
        "verdict": "pipeline_defect",
        "reason": "The scoped artifact needs correction.",
        "reviewed_at": "2026-07-14T12:01:00Z",
    }
    assert client.post("/api/verdicts", json=verdict, headers=_headers()).status_code == 201

    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    assert after == before


def _headers() -> dict[str, str]:
    return {"X-Workbench-Token": TOKEN}
