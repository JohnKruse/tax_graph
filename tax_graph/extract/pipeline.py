"""End-to-end extraction pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tax_graph.acquire.manifest import load_manifest
from tax_graph.config import get_config_value
from tax_graph.config import load_config, project_root
from tax_graph.extract.checks import run_deterministic_checks
from tax_graph.extract.critic import critique_drafts
from tax_graph.extract.generator import generate_drafts
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.llm_client import LlmClient, build_llm_client
from tax_graph.extract.route import route_drafts, write_routed_drafts
from tax_graph.extract.models import RoutedDrafts


def extract_document(
    document_id: str,
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    client: LlmClient | None = None,
    config: dict[str, Any] | None = None,
) -> RoutedDrafts:
    """Run rendered input -> generator -> critic -> checks -> draft writeout."""
    root_path = Path(root).resolve() if root is not None else project_root()
    settings = config if config is not None else load_config(root=root_path)
    llm_client = client or build_llm_client(settings)
    document = load_document_input(document_id, year=year, root=root_path, config=settings)
    batch = generate_drafts(document, client=llm_client, config=settings, root=root_path)
    critique_drafts(document, batch, client=llm_client, config=settings, root=root_path)
    checks = run_deterministic_checks(document, batch, root=root_path)
    routed = route_drafts(batch, checks, config=settings)
    return write_routed_drafts(batch, routed, root=root_path, config=settings)


def extract_year(
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    client: LlmClient | None = None,
    config: dict[str, Any] | None = None,
) -> list[RoutedDrafts]:
    """Run extraction for manifest documents in one tax year."""
    root_path = Path(root).resolve() if root is not None else project_root()
    settings = config if config is not None else load_config(root=root_path)
    llm_client = client or build_llm_client(settings)
    manifest = load_manifest(root=root_path)
    if str(manifest.tax_year) != str(year):
        raise ValueError(f"manifest tax_year {manifest.tax_year} does not match requested {year}")
    max_docs = int(get_config_value(settings, "extraction.max_docs_per_run", len(manifest.documents)))
    routed: list[RoutedDrafts] = []
    for entry in manifest.documents[:max_docs]:
        routed.append(
            extract_document(
                entry.document_id,
                year=year,
                root=root_path,
                client=llm_client,
                config=settings,
            )
        )
    return routed
