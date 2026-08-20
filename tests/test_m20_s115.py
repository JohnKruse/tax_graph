"""M20-S115 guards for the review contract."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import workbench.server as server_module
from workbench.address_verdicts import (
    append_address_verdict,
    derive_cell_coverage,
    latest_curated_comment,
    load_address_verdicts,
    make_review_content,
    review_content_fingerprint,
)
from workbench.cell_inventory import DocumentCells
from workbench.generated_review import _outcome_expression
from workbench.generated_review import _source_label
from workbench.review_defects import append_defect_report, defect_queue_path, load_defect_reports
from workbench.server import create_app


ROOT = Path(__file__).resolve().parents[1]


def test_s113_outcomes_project_as_their_own_review_kinds() -> None:
    target = {"official_ref": "1a"}
    formula = {"line_anchor": "1a", "label": "Total amount from Form(s) W-2, box 1"}

    filer = _outcome_expression("filer_entry", formula, {}, "target", target, None)
    named_filer = _outcome_expression(
        "filer_entry",
        formula,
        {"form": "W-2", "line": "1a", "box": "1"},
        "target",
        target,
        None,
    )
    information = _outcome_expression(
        "information_return",
        formula,
        {"form": "W-2", "box": "1"},
        "target",
        target,
        None,
    )
    election = _outcome_expression(
        "election",
        formula,
        {"question": "Where should the overpayment go?"},
        "target",
        target,
        None,
    )
    not_derivable = _outcome_expression(
        "not_derivable",
        formula,
        {"reason": "The evidence packet omits filing status."},
        "target",
        target,
        None,
    )

    assert filer["kind"] == "input"
    assert named_filer["text"] == "line 1a = W-2 box 1"
    assert named_filer["source"]["text"] == "W-2 box 1"
    assert information["kind"] == "imported"
    assert election == {"kind": "reference", "text": "Where should the overpayment go?"}
    assert not_derivable["kind"] == "review_gap"
    assert not_derivable["reason"] == "The evidence packet omits filing status."


def test_source_label_normalizes_form_names_without_title_casing_punctuation() -> None:
    assert _source_label("information_return", "Form(s) W-2", "", "1") == "W-2 box 1"
    assert _source_label("information_return", "Form(s) 1099-NEC", "", "1") == "1099-NEC box 1"
    assert _source_label("form_line", "form_2441", "26", "") == "Form 2441, line 26"


def test_try_again_comment_is_curated_only_after_accept(tmp_path: Path) -> None:
    address = "2025/document=form_a/line=1/control=amount"
    path = tmp_path / "address_verdicts.jsonl"
    common = {
        "root": tmp_path,
        "year": 2025,
        "address": address,
        "label": "Amount",
        "cited_text": ["Enter amount."],
        "reviewer_id": "john",
        "store_path": path,
    }
    append_address_verdict(
        **common,
        judgement="questioned",
        verdict_id="try_again_only",
        comment="Use the printed W-2 instruction.",
    )
    assert latest_curated_comment(address, load_address_verdicts(path)) is None

    append_address_verdict(
        **common,
        judgement="confirmed",
        verdict_id="accepted_retry",
        comment="Use the printed W-2 instruction.",
        origin="curated",
    )
    assert latest_curated_comment(address, load_address_verdicts(path)) == (
        "Use the printed W-2 instruction."
    )


def test_demoted_review_cell_is_not_derived(tmp_path: Path) -> None:
    address = "2025/document=form_a/line=1/control=amount"
    expression = {"kind": "input", "text": "line 1 = entered by filer"}
    content = make_review_content("Amount", expression=expression, form_citations=["Enter amount."])
    unit = {
        "unit_id": "unit_amount",
        "address_id": address,
        "display_name": "Amount",
        "expression": expression,
        "review_content": content,
        "content_fingerprint": review_content_fingerprint(
            "Amount", expression=expression, form_citations=["Enter amount."],
        ),
    }
    history = [{
        "verdict_id": "demoted",
        "tax_year": 2025,
        "address": address,
        "content_fingerprint": unit["content_fingerprint"],
        "reviewed_content": content,
        "judgement": "rejected",
        "reviewer_id": "john",
        "reviewed_at": "2026-08-16T10:00:00+00:00",
        "reviewed_at_epoch": 1786874400,
        "comment": "Derivation failed; filer must supply this value.",
        "origin": "contributed",
        "provenance": {
            "demotion": {
                "kind": "REQUIRE_INPUT",
                "reason": "filer-supplied because derivation failed",
            }
        },
    }]
    coverage = derive_cell_coverage([unit], history)
    assert coverage["cells"][0]["demoted"] is True
    assert coverage["cells"][0]["derived"] is False
    assert coverage["cells"][0]["demotion_kind"] == "REQUIRE_INPUT"


def test_defect_queue_is_local_append_only_ascii(tmp_path: Path) -> None:
    path = defect_queue_path(tmp_path, 2025)
    append_defect_report(
        root=tmp_path,
        year=2025,
        report={
            "report_id": "reject_1",
            "address": "2025/document=form_a/line=1/control=amount",
            "attempts": [{"comment": "Use the printed line."}],
        },
    )
    reports = load_defect_reports(path)
    assert reports[0]["report_id"] == "reject_1"
    path.read_bytes().decode("ascii")


def test_workbench_retry_accept_curates_and_reject_gate_is_enforced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    defect_reports: list[dict] = []
    monkeypatch.setattr(
        server_module,
        "append_defect_report",
        lambda **kwargs: defect_reports.append(dict(kwargs["report"])),
    )
    app, client, address = _stub_generated_app(tmp_path, monkeypatch, gate="project")
    headers = {"X-Workbench-Token": "s115-token"}
    retry = client.post(
        "/api/rederive",
        json={"document_id": "form_test_2025", "line": "1", "draft_comment": "Use the printed line."},
        headers=headers,
    )
    assert retry.status_code == 200, retry.get_json()
    attempt_id = retry.get_json()["attempt_id"]
    assert not (tmp_path / "verdicts" / "address_verdicts.jsonl").exists()

    accepted = client.post(
        "/api/verdicts",
        json={
            "queue_id": "form_test_2025",
            "verdict_id": "s115_accept_retry",
            "human_minutes": 0,
            "verdict": "confirmed",
            "comment": "ignored by the earned-comment contract",
            "try_again_attempt_id": attempt_id,
            "object_ref": {"object_id": address},
        },
        headers=headers,
    )
    assert accepted.status_code == 201, accepted.get_json()
    history = load_address_verdicts(tmp_path / "verdicts" / "address_verdicts.jsonl")
    assert latest_curated_comment(address, history) == "Use the printed line."

    rejected = client.post(
        "/api/verdicts",
        json={
            "queue_id": "form_test_2025",
            "verdict_id": "s115_project_filer_hatch",
            "human_minutes": 0,
            "verdict": "rejected",
            "comment": "The generated result is not supported.",
            "reject_action": "filer_provided",
            "object_ref": {"object_id": address},
        },
        headers=headers,
    )
    assert rejected.status_code == 400
    assert "user-gated" in rejected.get_json()["error"]

    user_root = tmp_path / "user_gate"
    user_app, user_client, user_address = _stub_generated_app(
        user_root, monkeypatch, gate="user",
    )
    user_headers = {"X-Workbench-Token": "s115-token"}
    user_retry = user_client.post(
        "/api/rederive",
        json={
            "document_id": "form_test_2025",
            "line": "1",
            "draft_comment": "The printed line is still authoritative.",
        },
        headers=user_headers,
    )
    assert user_retry.status_code == 200
    user_rejected = user_client.post(
        "/api/verdicts",
        json={
            "queue_id": "form_test_2025",
            "verdict_id": "s115_user_filer_hatch",
            "human_minutes": 0,
            "verdict": "rejected",
            "comment": "The pipeline cannot derive this value.",
            "reject_action": "filer_provided",
            "object_ref": {"object_id": user_address},
        },
        headers=user_headers,
    )
    assert user_rejected.status_code == 201, user_rejected.get_json()
    user_cell = next(
        item
        for item in user_client.get("/api/documents/form_test_2025/cells").get_json()["cells"]
        if item["address_id"] == user_address
    )
    assert user_cell["demoted"] is True
    assert user_cell["operation"] == "REQUIRE_INPUT"
    assert user_cell["population_policy"] == "user_entered"
    assert user_cell["review_attempts"][0]["comment"] == (
        "The printed line is still authoritative."
    )
    assert defect_reports[0]["attempts"][0]["comment"] == (
        "The printed line is still authoritative."
    )


def _stub_generated_app(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    gate: str,
):
    document_id = "form_test_2025"
    address = "2025/document=form_test/line=1/control=amount"
    cell = {
        "cell_id": "cell_amount",
        "document_id": document_id,
        "address_id": address,
        "official_ref": "1",
        "display_name": "Amount",
        "page": 1,
        "rect": [1, 1, 20, 20],
        "generated": True,
        "generated_model": "test-model",
        "generated_provider": "test-provider",
        "review_source": "draft_only",
        "expression": {"kind": "input", "text": "line 1 = entered by filer"},
        "form_citations": [{"quoted_text": "Enter amount."}],
        "instruction_citations": [],
    }

    class Graph:
        def objects(self, kind):
            if kind == "documents":
                return [{"document_id": document_id, "title": "Test form", "gate": gate}]
            return []

    bundle = SimpleNamespace(
        geometry={
            "entries": [{"document_id": document_id, "field_name": "amount", "page": 1, "rect": [1, 1, 20, 20]}],
            "pages": [],
        },
        graph=Graph(),
        pdfs=[],
    )
    manifest = {
        "manifest_hash": "a" * 64,
        "entries": [{
            "queue_id": document_id,
            "review_kind": "form_cell",
            "status": "pending",
            "units": [{"object_refs": [{"object_id": address, "object_type": "address"}]}],
        }],
    }
    monkeypatch.setattr(server_module, "GENERATED_REVIEW_DOCUMENTS", frozenset({document_id}))
    monkeypatch.setattr(
        server_module,
        "build_generated_document_cells",
        lambda *_args, **_kwargs: DocumentCells(document_id, [dict(cell)], [1]),
    )
    monkeypatch.setattr(server_module, "preflight_manifest", lambda *_args: {})

    def handler(document_id, line, draft_comment):
        return {
            "document_id": document_id,
            "line": line,
            "comment_source": "draft",
            "result": {"rendered": "line 1 = entered by filer"},
            "validation": {"attempted": 1, "errored": 0},
        }

    app = create_app(
        ROOT,
        2025,
        manifest=manifest,
        bundle=bundle,
        write_token="s115-token",
        state_dir=tmp_path / "sessions",
        cache_dir=tmp_path / "pages",
        verdict_dir=tmp_path / "verdicts",
        rederive_cell=handler,
    )
    app.config.update(TESTING=True)
    return app, app.test_client(), address
