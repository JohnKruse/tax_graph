"""Canonical form-address contracts and storage adapters."""

from tax_graph.addressing.registry import (
    AddressArtifacts,
    AddressComponent,
    AddressError,
    CanonicalAddress,
    Resolution,
    compile_address_artifacts,
    load_address_artifacts,
    load_compiled_address_artifacts,
    parse_address_id,
    serialize_address_id,
)
from tax_graph.addressing.migration import MigrationCandidate, migration_report, semantic_join_inventory
from tax_graph.addressing.search import SearchQuery, ranked_candidates, recall_at_k
from tax_graph.addressing.candidates import generate_candidate_registry, write_candidate_registry
from tax_graph.addressing.form1040 import build_form_1040_review, render_form_1040_review_html
from tax_graph.addressing.campaign import CORE_RETURN_DOCUMENTS, build_address_campaign, build_document_addresses

__all__ = [
    "AddressArtifacts", "AddressComponent", "AddressError", "CanonicalAddress",
    "Resolution", "compile_address_artifacts", "load_address_artifacts",
    "load_compiled_address_artifacts", "parse_address_id", "serialize_address_id",
    "MigrationCandidate", "migration_report", "semantic_join_inventory",
    "SearchQuery", "ranked_candidates", "recall_at_k",
    "generate_candidate_registry", "write_candidate_registry",
    "build_form_1040_review", "render_form_1040_review_html",
    "CORE_RETURN_DOCUMENTS", "build_address_campaign", "build_document_addresses",
]
