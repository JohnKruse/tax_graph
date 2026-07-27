"""Document role classification shared by authored and draft records."""

from __future__ import annotations


DOCUMENT_CLASSES = ("return", "information_return", "instructions", "intake")


def document_class_for(*, document_id: str, document_type: str) -> str:
    """Return the role-axis class for a document type and known intake form."""
    if document_id.startswith("form_13614_c_"):
        return "intake"
    if document_type in {"tax_form", "schedule", "worksheet"}:
        return "return"
    if document_type == "source_document":
        return "information_return"
    if document_type in {"instructions", "publication"}:
        return "instructions"
    raise ValueError(
        f"cannot derive document_class for {document_id}: unsupported document_type {document_type}"
    )
