"""M20-S49 tests for the non-persisting review retry loop."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from workbench.address_verdicts import append_address_verdict
from workbench.server import create_app


ROOT = Path(__file__).resolve().parents[1]


def test_application_host_injects_pipeline_callback(monkeypatch, tmp_path: Path) -> None:
    built: list[tuple[Path, str | int]] = []
    served: list[tuple[Path, str | int, int, object]] = []
    callback = object()

    def fake_build(root: Path, year: str | int):
        built.append((root, year))
        return callback

    def fake_serve(root: Path, year: str | int, *, port: int, rederive_cell: object):
        served.append((root, year, port, rederive_cell))

    monkeypatch.setattr("tax_graph.extract.rederive.build_rederive_handler", fake_build)
    monkeypatch.setattr("workbench.server.serve", fake_serve)

    from tax_graph.workbench_host import serve_workbench

    serve_workbench(tmp_path, "2025", port=9123)

    assert built == [(tmp_path.resolve(), "2025")]
    assert served == [(tmp_path.resolve(), "2025", 9123, callback)]


def test_generated_cells_display_history_but_retry_sends_only_explicit_draft(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cell = {
        "cell_id": "cell_1",
        "address_id": "2025/document=form_1040/section=income/control=amount",
        "page": 1,
        "display_name": "33 - Total",
        "official_ref": "33",
        "generated": True,
        "expression": {"kind": "input"},
        "form_citations": [],
        "instruction_citations": [],
    }

    def fake_cells(*_args, **_kwargs):
        return SimpleNamespace(cells=[dict(cell)], page_geometry=[])

    monkeypatch.setattr("workbench.server.build_generated_document_cells", fake_cells)
    monkeypatch.setattr("workbench.server.build_document_cells", fake_cells)
    monkeypatch.setattr("workbench.server.preflight_manifest", lambda _manifest, _bundle: {})

    ledger = tmp_path / "address_verdicts.jsonl"
    common = {
        "root": tmp_path,
        "year": "2025",
        "address": cell["address_id"],
        "label": "33 - Total",
        "expression": {"kind": "input"},
        "reviewer_id": "test-reviewer",
        "store_path": ledger,
    }
    append_address_verdict(
        **common,
        verdict_id="contributed-1",
        comment="This observation is retained for the reviewer.",
        origin="contributed",
    )
    append_address_verdict(
        **common,
        verdict_id="curated-1",
        comment="Use the form-face operand order.",
        origin="curated",
    )
    before = ledger.read_bytes()
    calls: list[tuple[str, str, str | None]] = []

    def handler(document_id: str, line: str, draft_comment: str | None):
        calls.append((document_id, line, draft_comment))
        return {"result": {"rendered": "trial"}}

    bundle = SimpleNamespace(
        geometry={"entries": [{"document_id": "form_1040_2025"}], "pages": []},
        graph=SimpleNamespace(
            objects=lambda kind: (
                [{"document_id": "form_1040_2025", "title": "Form 1040"}]
                if kind == "documents" else []
            ),
        ),
        pdfs=[],
    )
    app = create_app(
        ROOT,
        2025,
        manifest={"entries": [], "manifest_hash": "a" * 64},
        bundle=bundle,
        write_token="test-write-token",
        state_dir=tmp_path / "sessions",
        cache_dir=tmp_path / "pages",
        verdict_dir=tmp_path,
        rederive_cell=handler,
    )
    app.config.update(TESTING=True)
    client = app.test_client()
    headers = {"X-Workbench-Token": "test-write-token"}

    response = client.get("/api/documents/form_1040_2025/cells")
    comments = response.get_json()["cells"][0]["review_comments"]
    assert response.status_code == 200
    assert [item["origin"] for item in comments] == ["contributed", "curated"]
    assert "not sent" not in comments[0]["comment"]

    assert client.post(
        "/api/rederive",
        json={"document_id": "form_1040_2025", "line": "33"},
        headers=headers,
    ).status_code == 200
    assert client.post(
        "/api/rederive",
        json={
            "document_id": "form_1040_2025",
            "line": "33",
            "draft_comment": "Use the current form face.",
        },
        headers=headers,
    ).status_code == 200
    assert calls == [
        ("form_1040_2025", "33", None),
        ("form_1040_2025", "33", "Use the current form face."),
    ]
    assert ledger.read_bytes() == before
    assert not list((tmp_path / "sessions").rglob("*"))
