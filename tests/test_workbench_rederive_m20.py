"""M20-S37 tests for the workbench's injected re-derive HTTP seam."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from workbench.server import create_app


ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    not (ROOT / "graph" / "2025" / "_drafts").exists(),
    reason="live review drafts are required: fresh checkouts (CI) carry no _drafts",
)


@pytest.fixture
def rederive_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, str, str | None]] = []

    def handler(document_id: str, line: str, draft_comment: str | None):
        calls.append((document_id, line, draft_comment))
        return {
            "document_id": document_id,
            "line": line,
            "comment_source": "draft",
            "result": {"status": "derived", "rendered": "copy(line 17)"},
            "validation": {"attempted": 1, "errored": 0},
        }

    state = tmp_path / "workbench-state"
    monkeypatch.setattr("workbench.server.preflight_manifest", lambda _manifest, _bundle: {})
    bundle = SimpleNamespace(
        geometry={"entries": [], "pages": []},
        graph=SimpleNamespace(objects=lambda _kind: ()),
        pdfs=[],
    )
    manifest = {"entries": [], "manifest_hash": "a" * 64}
    app = create_app(
        ROOT,
        2025,
        manifest=manifest,
        bundle=bundle,
        write_token="test-write-token",
        state_dir=state / "sessions",
        cache_dir=state / "pages",
        verdict_dir=state / "verdicts",
        rederive_cell=handler,
    )
    app.config.update(TESTING=True)
    return app.test_client(), calls, app


def test_rederive_requires_token_and_passes_one_trial_to_handler(rederive_api) -> None:
    client, calls, _app = rederive_api
    payload = {
        "document_id": "form_6251_2025",
        "line": "18",
        "draft_comment": "Use the printed threshold.",
    }

    assert client.post("/api/rederive", json=payload).status_code == 403
    response = client.post(
        "/api/rederive",
        json=payload,
        headers={"X-Workbench-Token": "test-write-token"},
    )

    assert response.status_code == 200
    assert response.get_json()["result"]["status"] == "derived"
    assert calls == [("form_6251_2025", "18", "Use the printed threshold.")]


def test_rederive_validates_payload_and_reports_unconfigured_handler(rederive_api) -> None:
    client, _calls, app = rederive_api
    headers = {"X-Workbench-Token": "test-write-token"}

    assert client.post("/api/rederive", json={"document_id": "form_a"}, headers=headers).status_code == 400
    unexpected = client.post(
        "/api/rederive",
        json={"document_id": "form_a", "line": "18", "extra": "no"},
        headers=headers,
    )
    assert unexpected.status_code == 400
    app.config["WORKBENCH_REDERIVE_CELL"] = None
    unavailable = client.post(
        "/api/rederive",
        json={"document_id": "form_a", "line": "18"},
        headers=headers,
    )
    assert unavailable.status_code == 501


def test_rederive_maps_callback_failures_without_writing_state(rederive_api) -> None:
    client, _calls, app = rederive_api
    headers = {"X-Workbench-Token": "test-write-token"}

    app.config["WORKBENCH_REDERIVE_CELL"] = lambda *_args: (_ for _ in ()).throw(
        ValueError("unknown document line")
    )
    bad = client.post(
        "/api/rederive",
        json={"document_id": "form_a", "line": "18"},
        headers=headers,
    )
    assert bad.status_code == 400
    assert bad.get_json()["error"] == "unknown document line"
