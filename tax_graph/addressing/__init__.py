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

__all__ = [
    "AddressArtifacts", "AddressComponent", "AddressError", "CanonicalAddress",
    "Resolution", "compile_address_artifacts", "load_address_artifacts",
    "load_compiled_address_artifacts", "parse_address_id", "serialize_address_id",
]
