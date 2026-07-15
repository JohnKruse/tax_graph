from __future__ import annotations

from pathlib import Path

import jsonschema
import pytest

from tax_graph.addressing import build_form_1040_review, render_form_1040_review_html


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def review():
    return build_form_1040_review(ROOT)


@pytest.mark.m15r
def test_real_1040_inventory_is_fully_reconciled(review) -> None:
    coverage = review["coverage"]
    assert coverage["inventory"] == 199
    assert coverage["addressed"] + coverage["exempt"] == coverage["inventory"]
    assert len(review["controls"]) == coverage["inventory"]
    assert {item["status"] for item in review["controls"]} <= {"pending_review", "provisional", "ambiguous", "unresolved", "exempt"}
    assert all(item["address_id"] or item["status"] == "exempt" for item in review["controls"])


@pytest.mark.m15r
def test_real_1040_tree_has_1a_through_1h_1z_and_distinct_1h_controls(review) -> None:
    addresses = {item["address_id"] for item in review["registry"]["addresses"]}
    for ref in ["1a", "1b", "1c", "1d", "1e", "1f", "1g", "1h", "1z"]:
        assert f"2025/document=form_1040/line={ref}/control=amount" in addresses
    assert "2025/document=form_1040/line=1h/control=description" in addresses
    schema = __import__("json").loads((ROOT / "schemas/address_registry.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(review["registry"], schema)


@pytest.mark.m15r
def test_filing_status_dependents_and_special_distribution_controls_are_visible(review) -> None:
    addresses = {item["address_id"] for item in review["registry"]["addresses"]}
    assert any("section=filing_status/option=single" in item for item in addresses)
    assert any("table=dependents/row_template=dependent/column=first_name" in item for item in addresses)
    special = [item for item in review["controls"] if any(term in item["label"] for term in ("Rollover", "QCD", "PSO"))]
    assert special and all(item["status"] == "exempt" for item in special)
    assert all("no authored graph" in item["reason"] for item in special)


@pytest.mark.m15r
def test_gate_a_review_html_contains_stable_addresses_and_evidence(review) -> None:
    html = render_form_1040_review_html(review)
    assert "Form 1040 canonical address review" in html
    assert "2025/document=form_1040/line=1z/control=amount" in html
    assert "Explicit form structure or authored slot evidence" in html
    assert "formula" not in html.lower()
