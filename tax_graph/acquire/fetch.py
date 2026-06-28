"""Fetch IRS source documents into a reproducible raw store."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from tax_graph.acquire.manifest import ManifestEntry
from tax_graph.config import get_config_value


FetchBytes = Callable[[str, dict[str, Any]], bytes]


@dataclass(frozen=True)
class FetchedDocument:
    """Metadata recorded for one acquired document."""

    document_id: str
    url: str
    content_hash: str
    retrieved_date: str
    raw_path: str
    text_path: str
    metadata_path: str


def fetch_document(
    entry: ManifestEntry,
    *,
    year: int | str,
    raw_store: str | Path,
    config: dict[str, Any] | None = None,
    fetch_bytes: FetchBytes | None = None,
    today: dt.date | None = None,
) -> FetchedDocument:
    """Fetch one manifest entry, store raw/text artifacts, and write metadata."""
    settings = config or {}
    raw_root = Path(raw_store) / str(year)
    raw_root.mkdir(parents=True, exist_ok=True)

    content = (fetch_bytes or _httpx_fetch_bytes)(entry.url, settings)
    content_hash = hashlib.sha256(content).hexdigest()
    retrieved_date = (today or dt.date.today()).isoformat()

    raw_path = raw_root / f"{entry.document_id}.pdf"
    text_path = raw_root / f"{entry.document_id}.txt"
    metadata_path = raw_root / f"{entry.document_id}.json"

    raw_path.write_bytes(content)
    text_path.write_text(render_pdf_text(content), encoding="utf-8")

    metadata = FetchedDocument(
        document_id=entry.document_id,
        url=entry.url,
        content_hash=content_hash,
        retrieved_date=retrieved_date,
        raw_path=str(raw_path),
        text_path=str(text_path),
        metadata_path=str(metadata_path),
    )
    metadata_path.write_text(json.dumps(asdict(metadata), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def fetch_manifest_documents(
    entries: list[ManifestEntry] | tuple[ManifestEntry, ...],
    *,
    year: int | str,
    raw_store: str | Path,
    config: dict[str, Any] | None = None,
    fetch_bytes: FetchBytes | None = None,
    today: dt.date | None = None,
) -> list[FetchedDocument]:
    """Fetch all manifest entries into the raw store."""
    return [
        fetch_document(
            entry,
            year=year,
            raw_store=raw_store,
            config=config,
            fetch_bytes=fetch_bytes,
            today=today,
        )
        for entry in entries
    ]


def render_pdf_text(content: bytes) -> str:
    """Extract text from PDF bytes, falling back to UTF-8 for test fixtures."""
    try:
        from io import BytesIO

        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return content.decode("utf-8", errors="ignore")


def _httpx_fetch_bytes(url: str, config: dict[str, Any]) -> bytes:
    import httpx

    timeout = get_config_value(config, "acquire.timeout_sec", 30)
    retries = get_config_value(config, "acquire.retries", 3)
    user_agent = get_config_value(config, "acquire.user_agent", "tax-graph-bot/0.1")
    headers = {"User-Agent": user_agent}

    last_error: Exception | None = None
    for _ in range(int(retries) + 1):
        try:
            response = httpx.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()
            return response.content
        except httpx.HTTPError as exc:
            last_error = exc
    assert last_error is not None
    raise last_error
