"""Render IRS instructions and publications through Mistral OCR."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Protocol

from tax_graph.config import get_config_value, resolve_secret


class RendererUnavailable(RuntimeError):
    """Raised when the configured renderer cannot run."""


class OcrClient(Protocol):
    """Small OCR client protocol used by deterministic tests."""

    def render_pdf(self, pdf_path: Path, *, model: str) -> dict[str, Any]:
        """Return OCR output with pages containing markdown and links."""


@dataclass(frozen=True)
class OcrRenderResult:
    """Artifacts emitted by the OCR renderer."""

    document_id: str
    markdown_path: str
    pages_dir: str
    links_path: str
    cached: bool = False


def render_instructions_ocr(
    pdf_path: str | Path,
    *,
    document_id: str,
    output_dir: str | Path,
    content_hash: str,
    config: dict[str, Any] | None = None,
    client: OcrClient | None = None,
) -> OcrRenderResult:
    """Render an instructions/publication PDF to markdown artifacts."""
    settings = config or {}
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    markdown_path = output_root / f"{document_id}.txt"
    pages_dir = output_root / f"{document_id}.pages"
    links_path = output_root / f"{document_id}.links.json"
    metadata_path = output_root / f"{document_id}.ocr.json"

    if _cache_hit(metadata_path, content_hash, markdown_path, links_path):
        return OcrRenderResult(
            document_id=document_id,
            markdown_path=str(markdown_path),
            pages_dir=str(pages_dir),
            links_path=str(links_path),
            cached=True,
        )

    ocr_client = client or _build_mistral_client(settings)
    model = get_config_value(settings, "ocr.model", "mistral-ocr-latest")
    rendered = ocr_client.render_pdf(Path(pdf_path), model=model)
    pages = rendered.get("pages", [])
    pages_dir.mkdir(parents=True, exist_ok=True)

    all_markdown: list[str] = []
    all_links: list[dict[str, Any]] = []
    for index, page in enumerate(pages, 1):
        page_markdown = _ascii_normalize(str(page.get("markdown", ""))).strip()
        page_path = pages_dir / f"page-{index:03}.md"
        page_path.write_text(page_markdown + "\n", encoding="utf-8")
        all_markdown.append(f"# Page {index}\n{page_markdown}".rstrip())
        for link in page.get("links", []):
            all_links.append(
                {
                    "page": index,
                    "text": _ascii_normalize(str(link.get("text", ""))),
                    "url": str(link.get("url", "")),
                }
            )

    markdown_path.write_text("\n\n".join(all_markdown) + ("\n" if all_markdown else ""), encoding="utf-8")
    links_path.write_text(json.dumps(all_links, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    metadata_path.write_text(
        json.dumps({"content_hash": content_hash, "model": model}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return OcrRenderResult(
        document_id=document_id,
        markdown_path=str(markdown_path),
        pages_dir=str(pages_dir),
        links_path=str(links_path),
        cached=False,
    )


def _cache_hit(metadata_path: Path, content_hash: str, markdown_path: Path, links_path: Path) -> bool:
    if not metadata_path.exists() or not markdown_path.exists() or not links_path.exists():
        return False
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return metadata.get("content_hash") == content_hash


def _build_mistral_client(config: dict[str, Any]) -> OcrClient:
    api_key = resolve_secret(
        config,
        "ocr.api_key",
        keyring_path="ocr.api_key_keyring",
        env_path="ocr.api_key_env",
    )
    if not api_key:
        raise RendererUnavailable("Mistral OCR requires an API key")

    try:
        from mistralai import Mistral
    except ImportError as exc:  # pragma: no cover - dependency is declared for synced envs.
        raise RendererUnavailable("mistralai package is not installed") from exc

    return _MistralOcrClient(Mistral(api_key=api_key))


class _MistralOcrClient:
    def __init__(self, client: Any):
        self.client = client

    def render_pdf(self, pdf_path: Path, *, model: str) -> dict[str, Any]:
        with pdf_path.open("rb") as handle:
            uploaded = self.client.files.upload(
                file={"file_name": pdf_path.name, "content": handle},
                purpose="ocr",
            )
        signed_url = self.client.files.get_signed_url(file_id=uploaded.id)
        response = self.client.ocr.process(
            model=model,
            document={"type": "document_url", "document_url": signed_url.url},
        )
        pages = []
        for page in getattr(response, "pages", []):
            page_data = _object_to_dict(page)
            pages.append(
                {
                    "markdown": page_data.get("markdown", ""),
                    "links": page_data.get("links", []),
                }
            )
        return {"pages": pages}


def _object_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return dict(getattr(value, "__dict__", {}))


def _ascii_normalize(value: str) -> str:
    return value.encode("ascii", errors="ignore").decode("ascii")
