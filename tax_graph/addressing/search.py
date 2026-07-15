"""Constrained candidate retrieval for canonical-address review."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from typing import Any, Protocol, Sequence

from tax_graph.addressing.registry import AddressArtifacts, CanonicalAddress


class EmbeddingRanker(Protocol):
    """Optional build-time ranker; implementations must expose reproducibility metadata."""
    metadata: dict[str, Any]
    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...


@dataclass(frozen=True)
class SearchQuery:
    """Hard address constraints plus optional text used only for ranking."""
    source_id: str
    document_id: str
    year: int
    text: str = ""
    official_ref: str | None = None
    parent_address_id: str | None = None
    target_kind: str | None = None
    control_role: str | None = None
    structure_complete: bool = True


def ranked_candidates(query: SearchQuery, artifacts: AddressArtifacts, *, ranker: EmbeddingRanker | None = None, top_k: int = 10) -> dict[str, Any]:
    """Rank only hard-valid candidates and resolve independently of ranking scores."""
    survivors = [item for item in artifacts.addresses if _hard_valid(query, item)]
    lexical = {item.address_id: _trigram_score(query.text, _candidate_text(item)) for item in survivors}
    embedding: dict[str, float] = {}
    metadata = None
    if ranker is not None and survivors:
        texts = [query.text, *[_candidate_text(item) for item in survivors]]
        vectors = ranker.embed(texts)
        if len(vectors) != len(texts):
            raise ValueError("embedding ranker returned the wrong vector count")
        embedding = {item.address_id: _cosine(vectors[0], vectors[index + 1]) for index, item in enumerate(survivors)}
        metadata = dict(ranker.metadata)
        metadata["vector_input_hash"] = hashlib.sha256("\n".join(texts).encode("utf-8")).hexdigest()
    ordered = sorted(survivors, key=lambda item: (-(embedding.get(item.address_id, lexical[item.address_id])), -lexical[item.address_id], item.address_id))
    state = "unresolved" if not survivors else "exact" if len(survivors) == 1 and query.structure_complete else "provisional" if len(survivors) == 1 else "ambiguous"
    resolved = survivors[0].address_id if state == "exact" else None
    return {
        "source_id": query.source_id, "state": state, "resolved_address_id": resolved,
        "semantic_ranking_available": ranker is not None,
        "ranker": metadata,
        "candidates": [
            {"address_id": item.address_id, "rank": index + 1, "lexical_score": lexical[item.address_id],
             "embedding_score": embedding.get(item.address_id), "hard_validators": _validator_record(query, item),
             "accepted": item.address_id == resolved}
            for index, item in enumerate(ordered[:top_k])
        ],
    }


def recall_at_k(reports: Sequence[dict[str, Any]], expected: dict[str, str], k: int) -> float:
    """Measure review candidate recall without treating rank as resolution accuracy."""
    if not expected:
        return 1.0
    hits = 0
    for report in reports:
        wanted = expected.get(report["source_id"])
        if wanted and wanted in [item["address_id"] for item in report["candidates"][:k]]:
            hits += 1
    return hits / len(expected)


def _hard_valid(query: SearchQuery, item: CanonicalAddress) -> bool:
    return all(_validator_record(query, item).values())


def _validator_record(query: SearchQuery, item: CanonicalAddress) -> dict[str, bool]:
    return {
        "year": item.year == query.year,
        "document": item.document_id == query.document_id,
        "official_ref": query.official_ref is None or item.official_ref == query.official_ref,
        "parent": query.parent_address_id is None or item.parent_address_id == query.parent_address_id,
        "kind": query.target_kind is None or item.kind == query.target_kind,
        "control_role": query.control_role is None or item.control_role == query.control_role,
    }


def _candidate_text(item: CanonicalAddress) -> str:
    return " ".join(filter(None, [item.official_ref or "", item.control_role, str(item.raw.get("printed_label", "")), *item.raw.get("aliases", [])])).lower()


def _trigram_score(left: str, right: str) -> float:
    a, b = _trigrams(left.lower()), _trigrams(right.lower())
    return len(a & b) / len(a | b) if a or b else 0.0


def _trigrams(value: str) -> set[str]:
    normalized = " ".join(value.split())
    return {normalized[index:index + 3] for index in range(max(0, len(normalized) - 2))}


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("embedding dimensions differ")
    denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(sum(value * value for value in right))
    return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0.0
