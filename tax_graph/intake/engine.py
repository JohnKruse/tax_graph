"""Deterministic routing, reconciliation, and completeness for intake v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from tax_graph.config import get_config_value, load_config, project_root
from tax_graph.intake.classifier import Classification
from tax_graph.intake.consent import ConsentReceipt, require_consent
from tax_graph.io.loader import LoadedGraph, load_graph, load_yaml


@dataclass(frozen=True)
class RelevanceLayer:
    """The three additive intake object kinds loaded from the same graph."""

    graph: LoadedGraph
    routing_edges: tuple[dict[str, Any], ...]
    triggers: tuple[dict[str, Any], ...]
    expectations: tuple[dict[str, Any], ...]
    inventory: dict[str, Any]


@dataclass(frozen=True)
class RouteMatch:
    """One document box routed to a graph entry point."""

    path: str
    document_type: str
    source_box: str
    target: str
    status: str
    citation_refs: tuple[str, ...]
    reason: str | None = None


@dataclass(frozen=True)
class IntakeResult:
    """Complete, serializable result of one intake pass."""

    classifications: list[Classification]
    routes: list[RouteMatch]
    gaps: list[dict[str, Any]]
    complete: bool
    consent: ConsentReceipt | None = None
    resolutions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe intake output."""
        return {
            "classifications": [
                {
                    "path": str(item.path),
                    "document_type": item.document_type,
                    "confidence": item.confidence,
                    "evidence": list(item.evidence),
                    "boxes": dict(item.boxes),
                    "provider": item.provider,
                }
                for item in self.classifications
            ],
            "routes": [
                {
                    "path": item.path,
                    "document_type": item.document_type,
                    "source_box": item.source_box,
                    "target": item.target,
                    "status": item.status,
                    "citation_refs": list(item.citation_refs),
                    "reason": item.reason,
                }
                for item in self.routes
            ],
            "gaps": self.gaps,
            "complete": self.complete,
            "consent": None if self.consent is None else self.consent.__dict__,
            "resolutions": self.resolutions,
        }


def load_relevance_layer(year: str | int = "2025", root: str | Path | None = None) -> RelevanceLayer:
    """Load intake objects from authored YAML, never from drafts."""
    graph = load_graph(year, root)
    inventory_path = graph.graph_dir / "intake-inventory.yaml"
    inventory = load_yaml(inventory_path) if inventory_path.exists() else {}
    return RelevanceLayer(
        graph=graph,
        routing_edges=tuple(graph.items("routing_edges")),
        triggers=tuple(graph.items("triggers")),
        expectations=tuple(graph.items("expectations")),
        inventory=inventory or {},
    )


def route_documents(
    classifications: Iterable[Classification],
    layer: RelevanceLayer,
) -> list[RouteMatch]:
    """Map classified boxes to cited targets without LLM judgment."""
    by_key = {
        (edge.get("source_document_type"), edge.get("source_box")): edge
        for edge in layer.routing_edges
    }
    routes: list[RouteMatch] = []
    for classification in classifications:
        for source_box in sorted(classification.boxes):
            edge = by_key.get((classification.document_type, source_box))
            if edge is None:
                routes.append(
                    RouteMatch(
                        str(classification.path), classification.document_type, source_box,
                        "", "not_modeled", (), "No cited routing edge exists for this box.",
                    )
                )
                continue
            routes.append(
                RouteMatch(
                    str(classification.path),
                    classification.document_type,
                    source_box,
                    str(edge.get("target", "")),
                    str(edge.get("status", "not_modeled")),
                    tuple(sorted(edge.get("citation_refs", []))),
                    edge.get("reason"),
                )
            )
    return routes


def build_gap_list(
    classifications: Iterable[Classification],
    layer: RelevanceLayer,
    *,
    claims: Mapping[str, Any] | None = None,
    resolutions: Mapping[str, Any] | None = None,
    routes: Iterable[RouteMatch] | None = None,
) -> list[dict[str, Any]]:
    """Build cited gaps in both directions for the current document drop."""
    classifications = list(classifications)
    claims = dict(claims or {})
    resolutions = dict(resolutions or {})
    routes = list(routes or route_documents(classifications, layer))
    types = {item.document_type for item in classifications}
    gaps: list[dict[str, Any]] = []

    for trigger in layer.triggers:
        if trigger.get("status") == "not_modeled":
            # Still resolve the question, but label its destination honestly.
            pass
        activation = set(trigger.get("activation", []))
        active = trigger.get("obligation_class") == "universal_gate" or bool(
            activation & (types | set(claims))
        )
        derived_resolution = any(_truthy(claims.get(key)) for key in activation if key in claims)
        if active and _unresolved(trigger["trigger_id"], resolutions) and not derived_resolution:
            gaps.append(_gap(
                "trigger",
                trigger["trigger_id"],
                trigger.get("label", trigger["trigger_id"]),
                trigger.get("citation_refs", []),
                status="not_modeled" if trigger.get("status") == "not_modeled" else "open",
            ))

    for expectation in layer.expectations:
        claim = expectation["claim"]
        has_claim = _truthy(claims.get(claim))
        has_document = expectation["expected_document_type"] in types
        if has_claim and not has_document:
            gaps.append(_gap(
                "claims_without_documents",
                expectation["expectation_id"],
                f"Claim {claim} has no {expectation['expected_document_type']} document.",
                expectation.get("citation_refs", []),
            ))
        if has_document and not has_claim:
            gaps.append(_gap(
                "documents_without_claims",
                expectation["expectation_id"],
                f"{expectation['expected_document_type']} document needs a {claim} resolution.",
                expectation.get("citation_refs", []),
            ))

    for classification in classifications:
        if not classification.supported:
            gaps.append(_gap(
                "unsupported_document",
                str(classification.path),
                f"Document type {classification.document_type} is outside intake v1.",
                [],
            ))
    for route in routes:
        if route.status == "not_modeled":
            gaps.append(_gap(
                "unrouted_box",
                f"{route.path}:{route.source_box}",
                route.reason or "This information-return box is not modeled.",
                route.citation_refs,
            ))
    return sorted(gaps, key=lambda item: (item["kind"], item["id"]))


def check_completeness(gaps: Iterable[dict[str, Any]]) -> bool:
    """Return true only when no trigger or reconciliation gap remains."""
    return not list(gaps)


def run_intake(
    drop_dir: str | Path,
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    claims: Mapping[str, Any] | None = None,
    resolutions: Mapping[str, Any] | None = None,
    provider: str | None = None,
    consent: bool | None = None,
    config: Mapping[str, Any] | None = None,
) -> IntakeResult:
    """Run crawl, classify, route, reconcile, and completeness gate."""
    from tax_graph.intake.classifier import classify_documents, crawl_documents

    settings = dict(config or load_config(root=root))
    provider_name = provider or str(get_config_value(settings, "intake.classifier_provider", "local_rules"))
    receipt = None
    if provider_name not in {"local", "local_rules"}:
        mode = get_config_value(settings, "intake.consent")
        receipt = require_consent(provider_name, configured_mode=mode, consent=consent)
    classifications = classify_documents(crawl_documents(drop_dir))
    layer = load_relevance_layer(year, root)
    routes = route_documents(classifications, layer)
    gaps = build_gap_list(
        classifications,
        layer,
        claims=claims,
        resolutions=resolutions,
        routes=routes,
    )
    resolution_entries = [
        {
            "trigger_id": trigger_id,
            "resolution": value,
            "provenance": "user asserted",
            "citation_refs": sorted(
                ref
                for trigger in layer.triggers
                if trigger.get("trigger_id") == trigger_id
                for ref in trigger.get("citation_refs", [])
            ),
        }
        for trigger_id, value in sorted((resolutions or {}).items())
    ]
    return IntakeResult(
        classifications=classifications,
        routes=routes,
        gaps=gaps,
        complete=check_completeness(gaps),
        consent=receipt,
        resolutions=resolution_entries,
    )


def _gap(kind: str, identifier: str, message: str, citation_refs: Iterable[str], **extra: Any) -> dict[str, Any]:
    return {
        "kind": kind,
        "id": identifier,
        "message": message,
        "citation_refs": sorted(set(citation_refs)),
        **extra,
    }


def _truthy(value: Any) -> bool:
    return value not in (None, False, "", "no", "false", 0)


def _unresolved(trigger_id: str, resolutions: Mapping[str, Any]) -> bool:
    value = resolutions.get(trigger_id)
    return value in (None, "", "unsure")
