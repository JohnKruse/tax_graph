"""Return-scoped filing output helpers."""

from tax_graph.output.field_maps import load_field_maps, validate_field_maps
from tax_graph.output.fill import DependentAttachmentRequired, FilledForm, PdfExtraRequired, build_field_values, fill_official_pdf
from tax_graph.output.geometry import load_node_geometry, resolve_node_geometry, validate_node_geometry
from tax_graph.output.sidecar import scenario_from_facts_document, write_ots_sidecar
from tax_graph.output.session import export_filing_bundle, resolve_return_root, used_form_ids, validate_direct_return_root
from tax_graph.output.concepts import ConceptError, build_document_concepts, mint_concept_id, promote_structured_concepts, validate_concept_id

__all__ = [
    "FilledForm",
    "DependentAttachmentRequired",
    "PdfExtraRequired",
    "build_field_values",
    "fill_official_pdf",
    "export_filing_bundle",
    "load_field_maps",
    "load_node_geometry",
    "scenario_from_facts_document",
    "resolve_return_root",
    "resolve_node_geometry",
    "used_form_ids",
    "validate_field_maps",
    "validate_direct_return_root",
    "validate_node_geometry",
    "write_ots_sidecar",
    "ConceptError",
    "build_document_concepts",
    "mint_concept_id",
    "promote_structured_concepts",
    "validate_concept_id",
]
