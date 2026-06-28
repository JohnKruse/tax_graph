from __future__ import annotations

import json
import os

import pytest

from tax_graph.acquire.manifest import ManifestEntry
from tax_graph.acquire.render import render_source
from tax_graph.acquire.render_ocr import RendererUnavailable, render_instructions_ocr


class FakeOcrClient:
    def __init__(self):
        self.calls = 0

    def render_pdf(self, pdf_path, *, model):
        self.calls += 1
        return {
            "pages": [
                {
                    "markdown": "Line 2. Combine the amounts listed here.",
                    "links": [{"text": "Form 1116", "url": "https://www.irs.gov/forms-pubs/about-form-1116"}],
                },
                {
                    "markdown": "Worksheet A step text",
                    "links": [],
                },
            ]
        }


@pytest.mark.m3
def test_ocr_renderer_stores_markdown_pages_links_and_cache(tmp_path):
    pdf_path = tmp_path / "i1116.pdf"
    pdf_path.write_bytes(b"fake pdf")
    client = FakeOcrClient()

    result = render_instructions_ocr(
        pdf_path,
        document_id="instructions_form_1116_2025",
        output_dir=tmp_path,
        content_hash="hash-one",
        config={"ocr": {"model": "mistral-ocr-latest"}},
        client=client,
    )

    assert not result.cached
    assert client.calls == 1
    assert "Line 2. Combine" in (tmp_path / "instructions_form_1116_2025.txt").read_text(encoding="utf-8")
    assert (tmp_path / "instructions_form_1116_2025.pages" / "page-001.md").exists()
    links = json.loads((tmp_path / "instructions_form_1116_2025.links.json").read_text(encoding="utf-8"))
    assert links[0]["text"] == "Form 1116"

    cached = render_instructions_ocr(
        pdf_path,
        document_id="instructions_form_1116_2025",
        output_dir=tmp_path,
        content_hash="hash-one",
        config={"ocr": {"model": "mistral-ocr-latest"}},
        client=client,
    )

    assert cached.cached
    assert client.calls == 1


@pytest.mark.m3
def test_ocr_renderer_fails_loudly_without_key_or_client(tmp_path):
    pdf_path = tmp_path / "i1116.pdf"
    pdf_path.write_bytes(b"fake pdf")

    with pytest.raises(RendererUnavailable, match="API key"):
        render_instructions_ocr(
            pdf_path,
            document_id="instructions_form_1116_2025",
            output_dir=tmp_path,
            content_hash="hash-one",
            config={"ocr": {"api_key": None, "api_key_env": "MISSING_MISTRAL_KEY"}},
        )


@pytest.mark.m3
def test_render_dispatcher_routes_instructions_to_ocr(tmp_path):
    pdf_path = tmp_path / "i8949.pdf"
    pdf_path.write_bytes(b"fake pdf")
    entry = ManifestEntry(
        document_id="instructions_form_8949_2025",
        kind="instructions",
        url="https://www.irs.gov/pub/irs-pdf/i8949.pdf",
    )
    client = FakeOcrClient()

    render_source(entry, pdf_path=pdf_path, output_dir=tmp_path, content_hash="hash-one", ocr_client=client)

    assert client.calls == 1


@pytest.mark.network
@pytest.mark.skipif(
    os.environ.get("TAX_GRAPH_RUN_NETWORK_TESTS") != "1",
    reason="live OCR tests are opt-in",
)
def test_network_ocr_one_public_irs_doc(tmp_path):
    pytest.skip("Live Mistral OCR contract is finalized in integration docs before enabling")
