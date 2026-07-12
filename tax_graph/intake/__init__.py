"""Document-drop intake and graph relevance helpers."""

from tax_graph.intake.classifier import (
    Classification,
    DocumentCandidate,
    classify_document,
    classify_documents,
    crawl_documents,
)
from tax_graph.intake.consent import ConsentReceipt, ConsentRequiredError, require_consent
from tax_graph.intake.engine import (
    IntakeResult,
    build_gap_list,
    check_completeness,
    load_relevance_layer,
    route_documents,
    run_intake,
)

__all__ = [
    "Classification",
    "DocumentCandidate",
    "ConsentReceipt",
    "ConsentRequiredError",
    "IntakeResult",
    "build_gap_list",
    "check_completeness",
    "classify_document",
    "classify_documents",
    "crawl_documents",
    "load_relevance_layer",
    "require_consent",
    "route_documents",
    "run_intake",
]
