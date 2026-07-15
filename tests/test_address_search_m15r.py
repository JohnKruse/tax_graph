from __future__ import annotations

from dataclasses import replace

import pytest

from tax_graph.addressing import AddressArtifacts, AddressComponent, CanonicalAddress, SearchQuery, ranked_candidates, recall_at_k


def _address(form: str, year: int, ref: str, role: str, label: str) -> CanonicalAddress:
    address_id = f"{year}/document={form}/line={ref}/control={role}"
    path = (AddressComponent("document", form), AddressComponent("line", ref), AddressComponent("control", role))
    return CanonicalAddress(address_id, address_id.split("/", 1)[1], year, f"{form}_{year}", None, "control", path, ref, role, "pending_review", {"printed_label": label, "aliases": []})


class FrozenRanker:
    metadata = {"provider": "fixture", "model": "hostile-v1", "revision": "1", "dimensions": 2, "normalization": "cosine"}
    def __init__(self, vectors): self.vectors = vectors
    def embed(self, texts):
        assert len(texts) == len(self.vectors)
        return self.vectors


@pytest.mark.m15r
def test_hostile_embedding_rank_cannot_cross_hard_constraints() -> None:
    addresses = AddressArtifacts((
        _address("form_test", 2025, "24", "amount", "tax amount"),
        _address("form_test", 2025, "25", "amount", "tax amount"),
        _address("form_test", 2025, "24", "checkbox", "tax amount"),
        _address("other_form", 2025, "24", "amount", "tax amount"),
        _address("form_test", 2024, "24", "amount", "tax amount"),
    ))
    query = SearchQuery("claim", "form_test_2025", 2025, "tax amount", official_ref="24", target_kind="control", control_role="amount")
    report = ranked_candidates(query, addresses, ranker=FrozenRanker([[1, 0], [-1, 0]]))
    assert report["state"] == "exact"
    assert report["resolved_address_id"].endswith("line=24/control=amount")
    assert len(report["candidates"]) == 1
    assert all(report["candidates"][0]["hard_validators"].values())


@pytest.mark.m15r
def test_rank_and_margin_never_resolve_ambiguity_or_incomplete_structure() -> None:
    artifacts = AddressArtifacts((_address("form_test", 2025, "24", "amount", "alpha"), _address("form_test", 2025, "25", "amount", "beta")))
    broad = SearchQuery("broad", "form_test_2025", 2025, "alpha", control_role="amount")
    hostile = FrozenRanker([[1, 0], [1, 0], [-1, 0]])
    report = ranked_candidates(broad, artifacts, ranker=hostile)
    assert report["candidates"][0]["embedding_score"] == 1.0
    assert report["state"] == "ambiguous" and report["resolved_address_id"] is None
    provisional = ranked_candidates(replace(broad, official_ref="24", structure_complete=False), artifacts)
    assert provisional["state"] == "provisional" and provisional["resolved_address_id"] is None


@pytest.mark.m15r
def test_keyless_lexical_baseline_and_recall_metrics_are_deterministic() -> None:
    artifacts = AddressArtifacts((_address("form_test", 2025, "24", "amount", "qualified dividends"), _address("form_test", 2025, "25", "amount", "total tax")))
    query = SearchQuery("q1", "form_test_2025", 2025, "qualified dividends", control_role="amount")
    report = ranked_candidates(query, artifacts, top_k=2)
    assert report["semantic_ranking_available"] is False
    assert report["ranker"] is None
    assert report["candidates"][0]["address_id"].endswith("line=24/control=amount")
    assert recall_at_k([report], {"q1": report["candidates"][0]["address_id"]}, 1) == 1.0
