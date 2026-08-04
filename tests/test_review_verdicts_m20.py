"""M20 S6-1 tests for expression-bound verdict history and derived coverage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from workbench.address_verdicts import (
    address_without_year,
    append_address_verdict,
    derive_cell_coverage,
    expression_kind_bucket,
    latest_curated_comment,
    latest_curated_comments,
    load_address_verdicts,
    make_review_content,
    report_blast_radius,
    review_content_fingerprint,
    rollover_candidates,
)
from workbench.derived_reviews import build_derived_coverage


ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.m20


def _unit(
    address: str,
    label: str,
    cited_text: list[str],
    *,
    expression: dict[str, object] | None = None,
) -> dict[str, object]:
    expression = expression or {
        "kind": "reference",
        "ref": {"object_type": "address", "object_id": address},
    }
    content = make_review_content(label, expression=expression, form_citations=cited_text)
    return {
        "unit_id": "unit_" + address.replace("/", "_"),
        "address_id": address,
        "display_name": label,
        "expression": expression,
        "review_content": content,
        "content_fingerprint": review_content_fingerprint(
            label, expression=expression, form_citations=cited_text,
        ),
    }


def test_fingerprint_survives_whitespace_dashes_and_quotes() -> None:
    first = review_content_fingerprint("Line 1 - Taxpayer's amount", ["Enter the amount from line 2."])
    second = review_content_fingerprint(" Line 1 - Taxpayer\u2019s   amount ", ["Enter the amount from line 2."])
    assert first == second


def test_comment_is_review_metadata_not_content_identity(tmp_path: Path) -> None:
    common = {
        "root": tmp_path,
        "year": 2025,
        "address": "2025/document=form_a/line=1/control=amount",
        "label": "Amount",
        "cited_text": ["Enter amount."],
        "reviewer_id": "john",
        "reviewed_at": "2026-07-29T10:00:00Z",
    }
    first = append_address_verdict(
        **common, verdict_id="comment_identity_without", store_path=tmp_path / "one.jsonl",
    )
    second = append_address_verdict(
        **common, verdict_id="comment_identity_with", comment="Needs a second look.",
        store_path=tmp_path / "two.jsonl",
    )
    assert first["content_fingerprint"] == second["content_fingerprint"]
    assert "comment" not in first
    assert second["comment"] == "Needs a second look."
    assert second["origin"] == "contributed"


def test_latest_curated_comment_wins_and_contributed_text_is_excluded(tmp_path: Path) -> None:
    address = "2025/document=form_a/section=income/control=amount"
    path = tmp_path / "address_verdicts.jsonl"
    append_address_verdict(
        root=tmp_path,
        year=2025,
        address=address,
        label="Amount",
        cited_text=["Enter amount."],
        reviewer_id="contributor",
        reviewed_at="2026-07-29T09:00:00+00:00",
        verdict_id="contributed_1",
        comment="This is broke.",
        origin="contributed",
        store_path=path,
    )
    append_address_verdict(
        root=tmp_path,
        year=2025,
        address=address,
        label="Amount",
        cited_text=["Enter amount."],
        reviewer_id="john",
        reviewed_at="2026-07-29T10:00:00+00:00",
        verdict_id="curated_1",
        comment="Use the amount from line 17 before applying the threshold.",
        origin="curated",
        store_path=path,
    )
    append_address_verdict(
        root=tmp_path,
        year=2025,
        address=address,
        label="Amount",
        cited_text=["Enter amount."],
        reviewer_id="john",
        reviewed_at="2026-07-29T11:00:00+00:00",
        verdict_id="curated_2",
        comment="Use the printed filing-status threshold and subtrahend.",
        origin="curated",
        store_path=path,
    )

    history = load_address_verdicts(path)
    assert latest_curated_comment(address, history) == (
        "Use the printed filing-status threshold and subtrahend."
    )
    assert latest_curated_comments(history) == {
        address: "Use the printed filing-status threshold and subtrahend."
    }


def test_comment_origin_requires_comment_and_known_value(tmp_path: Path) -> None:
    common = {
        "root": tmp_path,
        "year": 2025,
        "address": "2025/document=form_a/section=income/control=amount",
        "label": "Amount",
        "cited_text": ["Enter amount."],
        "reviewer_id": "john",
        "store_path": tmp_path / "address_verdicts.jsonl",
    }
    with pytest.raises(ValueError, match="comment origin requires"):
        append_address_verdict(**common, origin="curated")
    with pytest.raises(ValueError, match="comment origin must be"):
        append_address_verdict(**common, comment="Needs work.", origin="guess")


def test_three_state_judgement_requires_comment_for_non_confirming_observations(tmp_path: Path) -> None:
    common = {
        "root": tmp_path,
        "year": 2025,
        "address": "2025/document=form_a/section=income/control=amount",
        "label": "Amount",
        "cited_text": ["Enter amount."],
        "reviewer_id": "john",
        "store_path": tmp_path / "address_verdicts.jsonl",
    }
    for judgement in ("questioned", "rejected"):
        with pytest.raises(ValueError, match="requires a non-empty comment"):
            append_address_verdict(**common, judgement=judgement, verdict_id=f"missing_{judgement}")
    with pytest.raises(ValueError, match="judgement must be one of"):
        append_address_verdict(**common, judgement="invented", verdict_id="invented")

    record = append_address_verdict(
        **common,
        judgement="questioned",
        comment="The source and generated label do not agree.",
        verdict_id="questioned_1",
    )
    assert record["judgement"] == "questioned"


def test_fingerprint_binds_expression_and_normalizes_equivalent_operands() -> None:
    first_expression = {
        "kind": "sum",
        "operation": "SUM",
        "operands": [
            {"kind": "reference", "ref": {"object_type": "node", "object_id": "a"}},
            {"kind": "reference", "ref": {"object_type": "node", "object_id": "b"}},
        ],
    }
    equivalent_expression = {
        "operation": " SUM ",
        "kind": "sum",
        "operands": [
            {"ref": {"object_id": "b", "object_type": "node"}, "kind": "reference"},
            {"kind": "reference", "ref": {"object_type": "node", "object_id": "a"}},
        ],
    }
    changed_expression = {
        **first_expression,
        "operands": [*first_expression["operands"], {"kind": "literal", "value": 1}],
    }
    first = review_content_fingerprint(
        "Total", expression=first_expression, form_citations=["Line 1"],
    )
    assert first == review_content_fingerprint(
        " Total ", expression=equivalent_expression, form_citations=[" Line 1 "],
    )
    assert first != review_content_fingerprint(
        "Total", expression=changed_expression, form_citations=["Line 1"],
    )
    assert first != review_content_fingerprint(
        "Total",
        expression={**first_expression, "operation": "SUBTRACT"},
        form_citations=["Line 1"],
    )
    subtract = {
        "kind": "subtract",
        "operands": first_expression["operands"],
    }
    reversed_subtract = {
        "kind": "subtract",
        "operands": list(reversed(first_expression["operands"])),
    }
    assert review_content_fingerprint("Difference", expression=subtract) != review_content_fingerprint(
        "Difference", expression=reversed_subtract,
    )


def test_expression_kind_buckets_are_explicit_and_fail_closed() -> None:
    assert expression_kind_bucket("sum") == "ARITHMETIC"
    assert expression_kind_bucket("copy") == "COPY"
    assert expression_kind_bucket("input") == "USER_ENTRY"
    assert expression_kind_bucket("imported") == "IMPORTED"
    assert expression_kind_bucket("repeatable_table") == "PER_ROW"
    assert expression_kind_bucket("review_gap") == "NOT_REVIEWABLE"
    with pytest.raises(ValueError, match="unsupported review expression kind"):
        expression_kind_bucket("invented")


def test_ledger_is_append_only_and_coverage_has_four_states(tmp_path: Path) -> None:
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
    assert coverage["states"] == {"unreviewed": 1, "approved": 1, "needs_recheck": 1, "review_gap": 0}
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
        verdict_id="verdict_late", comment="The generated cell is not correct.", store_path=path,
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


def test_verdict_rejects_reviewed_content_without_expression_slot(tmp_path: Path) -> None:
    address = "2025/document=form_a/section=income/control=amount"
    path = tmp_path / "address_verdicts.jsonl"
    record = append_address_verdict(
        root=tmp_path, year=2025, address=address, label="Amount", cited_text=["Enter amount."],
        reviewer_id="john", reviewed_at="2026-07-29T10:00:00+00:00", verdict_id="verdict_amount_1",
        store_path=path,
    )
    record["reviewed_content"].pop("expression")
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expression"):
        load_address_verdicts(path)


def test_review_gap_is_explicitly_not_reviewable() -> None:
    address = "2025/document=form_a/section=income/control=unsupported"
    gap = _unit(address, "Unsupported", [], expression={"kind": "review_gap", "reason": "not modeled"})
    coverage = derive_cell_coverage([gap], [])
    assert coverage["states"] == {"unreviewed": 0, "approved": 0, "needs_recheck": 0, "review_gap": 1}
    assert coverage["cells"][0]["kind_bucket"] == "NOT_REVIEWABLE"


def test_rollover_returns_explicit_candidates_without_copying(tmp_path: Path) -> None:
    expression = {"kind": "input", "text": "amount"}
    old = _unit(
        "2025/document=form_a/section=income/control=amount", "Amount", ["Enter amount."],
        expression=expression,
    )
    current = _unit(
        "2026/document=form_a/section=income/control=amount", "Amount", ["Enter amount."],
        expression=expression,
    )
    path = tmp_path / "address_verdicts.jsonl"
    append_address_verdict(
        root=tmp_path,
        year=2025,
        address=old["address_id"],
        label="Amount",
        cited_text=["Enter amount."],
        expression=expression,
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


def test_real_derived_projection_covers_graph_cells_and_routing() -> None:
    coverage = build_derived_coverage(ROOT, 2025, [])
    assert coverage["denominator"] == 2120
    assert coverage["states"] == {
        "unreviewed": 1529, "approved": 0, "needs_recheck": 0, "review_gap": 591,
    }
    assert sum(coverage["identity_sources"].values()) == 2120
    assert coverage["kind_buckets"] == {
        "ARITHMETIC": 139,
        "COPY": 49,
        "USER_ENTRY": 547,
        "IMPORTED": 696,
        "PER_ROW": 98,
        "NOT_REVIEWABLE": 591,
    }


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
        "content_fingerprint": review_content_fingerprint(
            "Amount",
            expression={"kind": "reference", "ref": {"object_type": "address", "object_id": address}},
            form_citations=["Enter amount."],
        ),
        "reviewed_content": make_review_content(
            "Amount",
            expression={"kind": "reference", "ref": {"object_type": "address", "object_id": address}},
            form_citations=["Enter amount."],
        ),
        "judgement": "approved",
        "reviewer_id": "john",
        "reviewed_at": "2026-07-29T10:00:00+00:00",
        "reviewed_at_epoch": 1785319200,
    }]
    first = derive_cell_coverage([changed], history)
    second = derive_cell_coverage([changed], history)
    assert first == second
    assert first["states"] == {"unreviewed": 0, "approved": 0, "needs_recheck": 1, "review_gap": 0}
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
