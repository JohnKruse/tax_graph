from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tax_graph.addressing import AddressComponent, CanonicalAddress, DeltaHint, address_delta


ROOT = Path(__file__).resolve().parents[1]


def _fixture(year: int) -> list[CanonicalAddress]:
    payload = yaml.safe_load(
        (ROOT / "tests/fixtures/m15r" / f"address_delta_{year}.yaml").read_text(encoding="utf-8")
    )
    return [
        CanonicalAddress(
            f"{year}/{key}", key, year, f"form_test_{year}", None, "control",
            (AddressComponent("document", "form_test"), AddressComponent("control", "amount")),
            None, "amount", "pending_review", {},
        )
        for key in payload["logical_keys"]
    ]


def _hints() -> tuple[DeltaHint, ...]:
    prefix = "document=form_test/line="
    suffix = "/control=amount"
    key = lambda line: f"{prefix}{line}{suffix}"
    return (
        DeltaHint("renumbered", (key("2"),), (key("2a"),)),
        DeltaHint("split", (key("3"),), (key("3a"), key("3b"))),
        DeltaHint("merged", (key("4a"), key("4b")), (key("4"),)),
        DeltaHint("unresolved", (key("6"),), (key("60"),)),
    )


@pytest.mark.m15r
def test_cross_year_delta_proves_every_state_and_is_stable() -> None:
    first = address_delta(_fixture(2025), _fixture(2026), hints=_hints())
    second = address_delta(reversed(_fixture(2025)), reversed(_fixture(2026)), hints=reversed(_hints()))

    assert first == second
    assert {item["state"] for item in first["results"]} == {
        "unchanged", "added", "removed", "renumbered", "split", "merged", "unresolved",
    }
    assert len(first["report_hash"]) == 64
    assert json.dumps(first, sort_keys=True).isascii()
    assert all(item["inherited_trust"] is (item["state"] == "unchanged") for item in first["results"])


@pytest.mark.m15r
def test_fuzzy_suggestions_never_inherit_trust_or_change_state() -> None:
    report = address_delta(_fixture(2025), _fixture(2026))
    removed = next(
        item for item in report["results"]
        if item["old_logical_keys"] == ["document=form_test/line=2/control=amount"]
    )
    assert removed["state"] == "removed"
    assert removed["inherited_trust"] is False
    assert removed["suggestions"]
    assert all(item["authoritative"] is False for item in removed["suggestions"])


@pytest.mark.m15r
def test_invalid_delta_hint_fails_closed() -> None:
    with pytest.raises(ValueError, match="cardinality"):
        address_delta(
            _fixture(2025), _fixture(2026),
            hints=(DeltaHint(
                "split",
                ("document=form_test/line=2/control=amount",),
                ("document=form_test/line=2a/control=amount",),
            ),),
        )
