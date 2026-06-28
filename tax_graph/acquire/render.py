"""Dispatch source rendering by manifest document kind."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tax_graph.acquire.manifest import ManifestEntry
from tax_graph.acquire.render_form import render_form_pdf
from tax_graph.acquire.render_ocr import OcrClient, render_instructions_ocr


FORM_KINDS = {"tax_form", "schedule", "source_document"}
OCR_KINDS = {"instructions", "publication"}


def render_source(
    entry: ManifestEntry,
    *,
    pdf_path: str | Path,
    output_dir: str | Path,
    content_hash: str,
    config: dict[str, Any] | None = None,
    ocr_client: OcrClient | None = None,
):
    """Render one acquired source document based on its manifest kind."""
    if entry.kind in FORM_KINDS:
        return render_form_pdf(pdf_path, document_id=entry.document_id, output_dir=output_dir)
    if entry.kind in OCR_KINDS:
        return render_instructions_ocr(
            pdf_path,
            document_id=entry.document_id,
            output_dir=output_dir,
            content_hash=content_hash,
            config=config,
            client=ocr_client,
        )
    raise ValueError(f"unsupported render kind: {entry.kind}")
