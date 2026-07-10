"""Return-scoped filing output helpers."""

from tax_graph.output.field_maps import load_field_maps, validate_field_maps
from tax_graph.output.fill import FilledForm, PdfExtraRequired, build_field_values, fill_official_pdf
from tax_graph.output.sidecar import scenario_from_facts_document, write_ots_sidecar

__all__ = [
    "FilledForm",
    "PdfExtraRequired",
    "build_field_values",
    "fill_official_pdf",
    "load_field_maps",
    "scenario_from_facts_document",
    "validate_field_maps",
    "write_ots_sidecar",
]
