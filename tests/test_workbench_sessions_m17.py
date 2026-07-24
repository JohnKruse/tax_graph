"""Focused M17-S1 tests for mutable per-unit session review state."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import workbench.server as server
from workbench.schema import SchemaValidationError, validate_session_state
from workbench.server import create_app
from workbench.sessions import (
    clear_unit_review,
    default_session,
    load_session,
    session_progress,
    set_unit_approval,
    set_unit_note,
    set_unit_review,
)


UNITS = [
    {"unit_id": "queue_1_line_1", "official_location": {"page": 1}},
    {"unit_id": "queue_1_line_2", "official_location": {"page": 1}},
]
MANIFEST = {
    "tax_year": 2025,
    "manifest_hash": "a" * 64,
    "entries": [{"queue_id": "queue_1", "units": UNITS}],
}


def _session() -> dict[str, object]:
    return default_session(2025, "queue_1", MANIFEST["manifest_hash"], UNITS)


@pytest.fixture
def api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(server, "preflight_manifest", lambda _manifest, _bundle: {})
    app = create_app(
        tmp_path,
        2025,
        write_token="m17-token",
        manifest=MANIFEST,
        bundle=object(),
        state_dir=tmp_path / "sessions",
    )
    app.config.update(TESTING=True)
    return app, app.test_client()


@pytest.mark.m15
def test_review_helpers_approve_reopen_note_progress_and_clear() -> None:
    state = _session()
    set_unit_review(
        state,
        "queue_1_line_1",
        UNITS,
        approved=True,
        note="Checked the cited line.",
        updated_at="2026-07-24T10:00:00+00:00",
    )
    assert session_progress(state, UNITS) == {"approved": 1, "total": 2}
    set_unit_approval(
        state,
        "queue_1_line_1",
        UNITS,
        False,
        updated_at="2026-07-24T10:01:00+00:00",
    )
    assert state["unit_reviews"]["queue_1_line_1"] == {
        "status": "open",
        "note": "Checked the cited line.",
        "updated_at": "2026-07-24T10:01:00+00:00",
    }
    set_unit_note(
        state,
        "queue_1_line_1",
        UNITS,
        "Reopened for a second look.",
        updated_at="2026-07-24T10:02:00+00:00",
    )
    assert state["unit_reviews"]["queue_1_line_1"]["note"] == "Reopened for a second look."
    clear_unit_review(state, "queue_1_line_1", UNITS)
    assert session_progress(state, UNITS) == {"approved": 0, "total": 2}


@pytest.mark.m15
def test_schema_accepts_reviews_and_rejects_non_ascii_note() -> None:
    state = _session()
    state["unit_reviews"] = {
        "queue_1_line_1": {
            "status": "open",
            "note": "ASCII only",
            "updated_at": "2026-07-24T10:00:00+00:00",
        }
    }
    validate_session_state(state)
    state["unit_reviews"]["queue_1_line_1"]["note"] = "non-ascii: cafe\u00e9"
    with pytest.raises(SchemaValidationError):
        validate_session_state(state)


@pytest.mark.m15
def test_existing_saved_session_without_reviews_remains_loadable(tmp_path: Path) -> None:
    state = _session()
    state.pop("unit_reviews")
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(state), encoding="utf-8")

    loaded = load_session(path)

    assert loaded is not None
    assert loaded["unit_reviews"] == {}


@pytest.mark.m15
def test_session_api_round_trips_reviews_derives_progress_and_rejects_unknown(api) -> None:
    app, client = api
    initial = client.get("/api/sessions/queue_1")
    state = initial.get_json()
    state["unit_reviews"] = {
        "queue_1_line_1": {
            "status": "approved",
            "note": "Approved after checking the source.",
            "updated_at": "2026-07-24T10:00:00+00:00",
        }
    }

    saved = client.put(
        "/api/sessions/queue_1",
        json=state,
        headers={"X-Workbench-Token": "m17-token"},
    )
    loaded = client.get("/api/sessions/queue_1")

    assert initial.status_code == 200
    assert initial.get_json()["progress"] == {"approved": 0, "total": 2}
    assert saved.status_code == 200
    assert saved.get_json()["progress"] == {"approved": 1, "total": 2}
    assert loaded.get_json()["unit_reviews"] == state["unit_reviews"]
    assert loaded.get_json()["progress"] == {"approved": 1, "total": 2}
    persisted = json.loads(
        (app.config["WORKBENCH_SESSION_ROOT"] / "queue_1.json").read_text(encoding="utf-8")
    )
    assert "progress" not in persisted

    state["unit_reviews"]["queue_1_line_1"]["status"] = "open"
    reopened = client.put(
        "/api/sessions/queue_1",
        json=state,
        headers={"X-Workbench-Token": "m17-token"},
    )
    assert reopened.get_json()["progress"] == {"approved": 0, "total": 2}
    assert reopened.get_json()["unit_reviews"]["queue_1_line_1"]["note"] == (
        "Approved after checking the source."
    )

    state["unit_reviews"]["not_in_manifest"] = {
        "status": "approved",
        "note": "Must fail closed.",
        "updated_at": "2026-07-24T10:00:00+00:00",
    }
    rejected = client.put(
        "/api/sessions/queue_1",
        json=state,
        headers={"X-Workbench-Token": "m17-token"},
    )
    assert rejected.status_code == 400
    assert "not_in_manifest" in rejected.get_json()["error"]
