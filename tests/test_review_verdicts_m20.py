"""M20 S5-1 tests for address-keyed verdict history and derived coverage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from workbench.address_verdicts import (
    address_without_year,
    append_address_verdict,
    derive_cell_coverage,
    load_address_verdicts,
    report_blast_radius,
    review_content_fingerprint,
    rollover_candidates,
)
from workbench.derived_reviews import build_derived_coverage


ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.m20


def _unit(address: str, label: str, cited_text: list[str]) -> dict[str, object]:
    return {
        "unit_id": "unit_" + address.replace("/", "_"),
        "address_id": address,
        "display_name": label,
        "review_content": {"label": label, "cited_text": cited_text},
        "content_fingerprint": review_content_fingerprint(label, cited_text),
    }


def test_fingerprint_survives_whitespace_dashes_and_quotes() -> None:
    first = review_content_fingerprint("Line 1 - Taxpayer's amount", ["Enter the amount from line 2."])
    second = review_content_fingerprint(" Line 1 - Taxpayer\u2019s   amount ", ["Enter the amount from line 2."])
    assert first == second


def test_ledger_is_append_only_and_coverage_has_three_states(tmp_path: Path) -> None:
    address = "2025/document=form_a/section=income/control=amount"
    changed_address = "2025/document=form_a/section=income/control=changed_amount"
    unit_a = _unit(address, "Amount", ["Enter amount."])
    path = tmp_path / "address_verdicts.jsonl"
    record = append_address_verdict(
        root=tmp_path,
        year=2025,
        address=address,
        label="Amount",
        cited_text=["Enter amount."],
        reviewer_id="john",
        reviewed_at="2026-07-29T10:00:00+00:00",
        verdict_id="verdict_amount_1",
        store_path=path,
    )
    assert load_address_verdicts(path) == [record]
    with pytest.raises(FileExistsError):
        append_address_verdict(
            root=tmp_path,
            year=2025,
            address=address,
            label="Amount",
            cited_text=["Enter amount."],
            reviewer_id="john",
            reviewed_at="2026-07-29T10:00:00+00:00",
            verdict_id="verdict_amount_1",
            store_path=path,
        )

    append_address_verdict(
        root=tmp_path,
        year=2025,
        address=changed_address,
        label="Amount",
        cited_text=["Enter amount."],
        reviewer_id="john",
        reviewed_at="2026-07-29T10:00:00+00:00",
        verdict_id="verdict_changed_amount_1",
        store_path=path,
    )
    changed = _unit(changed_address, "Changed amount", ["Enter amount."])
    other = _unit("2025/document=form_a/section=income/control=other", "Other", [])
    coverage = derive_cell_coverage([unit_a, changed, other], load_address_verdicts(path))
    assert coverage["states"] == {"unreviewed": 1, "approved": 1, "needs_recheck": 1}
    assert next(item for item in coverage["cells"] if item["unit_id"] == changed["unit_id"])["needs_recheck"] is True

    blast = report_blast_radius([unit_a, changed, other], load_address_verdicts(path))
    assert blast["approved_total"] == 2
    assert blast["invalidated"] == 1
    assert blast["items"][0]["address"] == changed_address


def test_content_flip_back_revalidates_original_approval(tmp_path: Path) -> None:
    address = "2025/document=form_a/section=income/control=amount"
    unit_a = _unit(address, "Amount", ["Enter amount."])
    unit_b = _unit(address, "Changed amount", ["Enter amount."])
    path = tmp_path / "address_verdicts.jsonl"
    append_address_verdict(
        root=tmp_path,
        year=2025,
        address=address,
        label="Amount",
        cited_text=["Enter amount."],
        reviewer_id="john",
        reviewed_at="2026-07-29T10:00:00+00:00",
        verdict_id="verdict_amount_1",
        store_path=path,
    )
    assert derive_cell_coverage([unit_b], load_address_verdicts(path))["needs_recheck"] == 1
    assert derive_cell_coverage([unit_a], load_address_verdicts(path))["approved"] == 1


def test_latest_verdict_orders_by_utc_epoch_and_file_order(tmp_path: Path) -> None:
    address = "2025/document=form_a/section=income/control=amount"
    path = tmp_path / "address_verdicts.jsonl"
    append_address_verdict(
        root=tmp_path, year=2025, address=address, label="Amount", cited_text=["Enter amount."],
        reviewer_id="john", judgement="approved", reviewed_at="2026-07-29T12:00:00+02:00",
        verdict_id="verdict_early", store_path=path,
    )
    append_address_verdict(
        root=tmp_path, year=2025, address=address, label="Amount", cited_text=["Enter amount."],
        reviewer_id="john", judgement="rejected", reviewed_at="2026-07-29T11:00:00+00:00",
        verdict_id="verdict_late", store_path=path,
    )
    records = load_address_verdicts(path)
    assert records[0]["reviewed_at"] == "2026-07-29T10:00:00+00:00"
    assert records[0]["reviewed_at_epoch"] == 1785319200
    from jsonschema import validate

    validate(records[0], json.loads((ROOT / "schemas" / "review_address_verdict.schema.json").read_text()))
    coverage = derive_cell_coverage([_unit(address, "Amount", ["Enter amount."])], records)
    assert coverage["cells"][0]["judgement"] == "rejected"


def test_verdict_rejects_missing_or_tampered_reviewed_content(tmp_path: Path) -> None:
    address = "2025/document=form_a/section=income/control=amount"
    path = tmp_path / "address_verdicts.jsonl"
    record = append_address_verdict(
        root=tmp_path, year=2025, address=address, label="Amount", cited_text=["Enter amount."],
        reviewer_id="john", reviewed_at="2026-07-29T10:00:00+00:00", verdict_id="verdict_amount_1",
        store_path=path,
    )
    record.pop("reviewed_content")
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="reviewed_content"):
        load_address_verdicts(path)


def test_rollover_returns_explicit_candidates_without_copying(tmp_path: Path) -> None:
    old = _unit("2025/document=form_a/section=income/control=amount", "Amount", ["Enter amount."])
    current = _unit("2026/document=form_a/section=income/control=amount", "Amount", ["Enter amount."])
    path = tmp_path / "address_verdicts.jsonl"
    append_address_verdict(
        root=tmp_path,
        year=2025,
        address=old["address_id"],
        label="Amount",
        cited_text=["Enter amount."],
        reviewer_id="john",
        reviewed_at="2026-07-29T10:00:00+00:00",
        verdict_id="verdict_amount_1",
        store_path=path,
    )
    candidates = rollover_candidates([old], load_address_verdicts(path), [current], previous_year=2025)
    assert len(candidates) == 1
    assert candidates[0]["state"] == "carried"
    assert candidates[0]["source_year"] == 2025
    assert "per-cell confirmation required" in candidates[0]["provenance"]


def test_rollover_year_stripping_does_not_corrupt_form_numbers() -> None:
    assert address_without_year("2025/document=form_1040/section=identity/control=taxpayer_ssn") == (
        "document=form_1040/section=identity/control=taxpayer_ssn"
    )
    assert address_without_year(
        "2025/document=form_1040/table=dependents/row_template=dependent/column=lived_with_you_more_than_half_2025"
    ) == "document=form_1040/table=dependents/row_template=dependent/column=lived_with_you_more_than_half"


def test_real_derived_projection_covers_all_1921_controls() -> None:
    coverage = build_derived_coverage(ROOT, 2025, [])
    assert coverage["denominator"] == 1921
    assert coverage["states"] == {"unreviewed": 1921, "approved": 0, "needs_recheck": 0}
    assert sum(coverage["identity_sources"].values()) == 1921


def test_derived_projection_replaces_queue_matching_and_orphan_persistence() -> None:
    """Generated-id matching is replaced by a pure address/content projection.

    This covers the retired reconciler's unique-match, changed-content, and
    idempotence behaviors without persisting aliases or orphan records.
    """
    address = "2025/document=form_a/section=income/control=amount"
    current = _unit(address, "Amount", ["Enter amount."])
    changed = _unit(address, "Amount", ["Enter the amount."])
    history = [{
        "verdict_id": "verdict_amount_1",
        "tax_year": 2025,
        "address": address,
        "content_fingerprint": review_content_fingerprint("Amount", ["Enter amount."]),
        "reviewed_content": {"label": "Amount", "cited_text": ["Enter amount."]},
        "judgement": "approved",
        "reviewer_id": "john",
        "reviewed_at": "2026-07-29T10:00:00+00:00",
        "reviewed_at_epoch": 1785319200,
    }]
    first = derive_cell_coverage([changed], history)
    second = derive_cell_coverage([changed], history)
    assert first == second
    assert first["states"] == {"unreviewed": 0, "approved": 0, "needs_recheck": 1}
    assert "orphaned" not in first
    assert derive_cell_coverage([current], history)["approved"] == 1


def test_authored_review_context_preserves_all_four_curated_records() -> None:
    import yaml

    payload = yaml.safe_load(
        (ROOT / "review_context" / "2025" / "authored_reviews.yaml").read_text(encoding="utf-8")
    )
    assert len(payload["entries"]) == 4
    assert {entry["queue_id"] for entry in payload["entries"]} == {
        "authored_review_qdcgt_worksheet_2025",
        "authored_review_schedule_d_2025_tax_worksheet",
        "routing_review_schedule_d_2025_line_20_decision",
        "decision_review_1040_deduction_method",
    }
    assert all(entry.get("summary") and entry.get("machine_witnesses") for entry in payload["entries"])
