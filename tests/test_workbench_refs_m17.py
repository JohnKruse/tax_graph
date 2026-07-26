"""M17-S2 tests for short, quotable review-unit refs."""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench.refs import abbreviate_document, ambiguous_refs, unit_ref_from_address


ROOT = Path(__file__).resolve().parents[1]


def test_abbreviation_is_short_and_injective_over_the_2025_documents() -> None:
    documents = [
        "form_1040", "schedule_1", "schedule_1a", "schedule_2", "schedule_3",
        "schedule_a", "schedule_b", "schedule_d", "form_8949", "form_w2",
        "form_1099_b", "form_1099_div", "form_1099_int", "form_6251", "form_2441",
        "form_13614_c",
    ]
    abbreviations = [abbreviate_document(document) for document in documents]
    assert abbreviations == [
        "1040", "sch1", "sch1a", "sch2", "sch3", "scha", "schb", "schd", "8949",
        "w2", "1099b", "1099div", "1099int", "6251", "2441", "13614c",
    ]
    assert len(set(abbreviations)) == len(abbreviations)
    assert all(ref.isascii() and " " not in ref for ref in abbreviations)


def test_ref_derives_from_the_address_and_is_deterministic() -> None:
    amount = "2025/document=schedule_2/line=4/control=amount"
    assert unit_ref_from_address(amount) == "sch2/4/amount"
    assert unit_ref_from_address(amount) == unit_ref_from_address(amount)

    # The role distinguishes two controls that share a line - exactly what a note
    # needs to cite one without ambiguity.
    assert unit_ref_from_address(
        "2025/document=schedule_2/line=4/option=form_4361"
    ) == "sch2/4/form_4361"
    assert unit_ref_from_address(
        "2025/document=form_1040/section=identity/control=address_line_1"
    ) == "1040/identity/address_line_1"


def test_ref_is_none_for_a_non_canonical_or_empty_address() -> None:
    assert unit_ref_from_address("") is None
    assert unit_ref_from_address("schedule_2/line=4/control=amount") is None  # no year
    assert unit_ref_from_address("2025/schedule_2/line/4") is None  # not key=value


def test_ambiguous_refs_flags_only_a_ref_that_spans_two_addresses() -> None:
    same_address = "2025/document=schedule_2/line=4/control=amount"
    units = [
        # Same cell reviewed two ways: shares a ref legitimately, not a collision.
        {"unit_id": "a", "ref": "sch2/4/amount", "address_id": same_address},
        {"unit_id": "b", "ref": "sch2/4/amount", "address_id": same_address},
        # A ref that resolves to two different addresses IS ambiguous.
        {"unit_id": "c", "ref": "x/1/amount", "address_id": "2025/document=x/line=1/control=amount"},
        {"unit_id": "d", "ref": "x/1/amount", "address_id": "2025/document=y/line=1/control=amount"},
        {"unit_id": "e"},  # no ref - ignored
    ]
    assert ambiguous_refs(units) == {
        "x/1/amount": [
            "2025/document=x/line=1/control=amount",
            "2025/document=y/line=1/control=amount",
        ]
    }
    assert ambiguous_refs(units[:2]) == {}


@pytest.mark.m15
@pytest.mark.skipif(
    not (ROOT / "graph" / "2025" / "_drafts").exists(),
    reason="live review drafts are required: fresh checkouts (CI) carry no _drafts",
)
def test_live_2025_manifest_refs_are_unique_ascii_and_cover_addressed_units() -> None:
    from workbench.manifest import build_manifest

    manifest = build_manifest(ROOT, 2025)
    units = [unit for entry in manifest["entries"] for unit in entry["units"]]

    assert units, "the live manifest must contain review units"
    assert ambiguous_refs(units) == {}, "each ref must name exactly one address"
    for unit in units:
        if unit.get("address_id"):
            ref = unit.get("ref")
            assert ref, f"addressed unit {unit['unit_id']} is missing a ref"
            assert ref.isascii() and " " not in ref
        if unit.get("ref"):
            assert unit["ref"] == unit_ref_from_address(unit["address_id"], unit.get("occurrence"))
