"""Fetch IRS source documents into a reproducible raw store."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Callable
import unicodedata

from tax_graph.acquire.manifest import ManifestEntry
from tax_graph.config import get_config_value


FetchBytes = Callable[[str, dict[str, Any]], bytes]


_ASCII_REPLACEMENTS = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2026": "...",
        "\u00a0": " ",
    }
)


@dataclass(frozen=True)
class FetchedDocument:
    """Metadata recorded for one acquired document."""

    document_id: str
    url: str
    content_hash: str
    retrieved_date: str
    raw_path: str
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
    metadata_path = raw_root / f"{entry.document_id}.json"

    raw_path.write_bytes(content)

    metadata = FetchedDocument(
        document_id=entry.document_id,
        url=entry.url,
        content_hash=content_hash,
        retrieved_date=retrieved_date,
        raw_path=str(raw_path),
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


def fetch_instruction_html(
    entry: ManifestEntry,
    *,
    year: int | str,
    raw_store: str | Path,
    config: dict[str, Any] | None = None,
    fetch_bytes: FetchBytes | None = None,
    today: dt.date | None = None,
) -> FetchedDocument:
    """Fetch and store one manifest-backed HTML instruction page.

    The stored bytes are ASCII-normalized once at acquisition time. Later parsers and
    citation checks read this file rather than fetching a live page.
    """
    if not entry.instruction_url:
        raise ValueError(f"manifest entry {entry.document_id} has no instruction_url")
    settings = config or {}
    raw_root = Path(raw_store) / str(year)
    raw_root.mkdir(parents=True, exist_ok=True)
    source = (fetch_bytes or _httpx_fetch_bytes)(entry.instruction_url, settings)
    normalized = transliterate_ascii(source.decode("utf-8"))
    content = normalized.encode("ascii")
    content_hash = hashlib.sha256(content).hexdigest()
    retrieved_date = (today or dt.date.today()).isoformat()
    raw_path = raw_root / f"{entry.document_id}.html"
    metadata_path = raw_root / f"{entry.document_id}.html.json"
    raw_path.write_bytes(content)
    metadata = FetchedDocument(
        document_id=entry.document_id,
        url=entry.instruction_url,
        content_hash=content_hash,
        retrieved_date=retrieved_date,
        raw_path=str(raw_path),
        metadata_path=str(metadata_path),
    )
    metadata_path.write_text(json.dumps(asdict(metadata), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return metadata


def fetch_instruction_html_documents(
    entries: list[ManifestEntry] | tuple[ManifestEntry, ...],
    *,
    year: int | str,
    raw_store: str | Path,
    config: dict[str, Any] | None = None,
    fetch_bytes: FetchBytes | None = None,
    today: dt.date | None = None,
) -> list[FetchedDocument]:
    """Fetch instruction pages sequentially for entries that declare instruction_url."""
    return [
        fetch_instruction_html(
            entry,
            year=year,
            raw_store=raw_store,
            config=config,
            fetch_bytes=fetch_bytes,
            today=today,
        )
        for entry in entries
        if entry.instruction_url
    ]


def transliterate_ascii(text: str) -> str:
    """Convert common IRS typography to ASCII without changing structural markup."""
    translated = unicodedata.normalize("NFKD", text.translate(_ASCII_REPLACEMENTS))
    return translated.encode("ascii", "ignore").decode("ascii")


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
