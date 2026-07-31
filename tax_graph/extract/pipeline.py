"""End-to-end extraction pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tax_graph.acquire.manifest import AcquisitionManifest, load_manifest
from tax_graph.config import get_config_value
from tax_graph.config import load_config, project_root
from tax_graph.extract.checks import run_deterministic_checks
from tax_graph.extract.critic import critique_drafts
from tax_graph.extract.generator import generate_drafts
from tax_graph.extract.inputs import FORM_KINDS, load_document_input
from tax_graph.extract.llm_client import LlmClient, build_llm_client
from tax_graph.extract.observability import extraction_run
from tax_graph.extract.outline_pipeline import generate_outline_first_drafts
from tax_graph.extract.outline import write_outline_artifacts
from tax_graph.extract.route import route_drafts, write_routed_drafts
from tax_graph.extract.models import RoutedDrafts
from tax_graph.verify.properties import check_draft_batch_properties
from tax_graph.verify.tiers import TierInputs, collect_covered_nodes


def _extract_document_impl(
    document_id: str,
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    client: LlmClient | None = None,
    config: dict[str, Any] | None = None,
    manifest: AcquisitionManifest | None = None,
    raw_store: str | Path | None = None,
    gate: str | None = None,
) -> RoutedDrafts:
    """Run rendered input -> generator -> critic -> checks -> draft writeout."""
    root_path = Path(root).resolve() if root is not None else project_root()
    settings = config if config is not None else load_config(root=root_path)
    llm_client = client or build_llm_client(settings)
    document = load_document_input(
        document_id,
        year=year,
        root=root_path,
        config=settings,
        raw_store=raw_store,
        manifest=manifest,
    )
    write_outline_artifacts(document, root=root_path, config=settings)
    mode = str(get_config_value(settings, "extraction.mode", "one_pass"))
    if mode == "one_pass":
        batch = generate_drafts(document, client=llm_client, config=settings, root=root_path)
        critique_drafts(document, batch, client=llm_client, config=settings, root=root_path)
    elif mode == "outline_first":
        batch = generate_outline_first_drafts(document, client=llm_client, config=settings, root=root_path)
        expression_mode = str(get_config_value(settings, "extraction.expression_mode", "generator"))
        if expression_mode == "generator":
            expression_batch = generate_drafts(document, client=llm_client, config=settings, root=root_path)
            critique_drafts(document, expression_batch, client=llm_client, config=settings, root=root_path)
            batch = _merge_expression_batch(batch, expression_batch)
        elif expression_mode not in {"none", ""}:
            raise ValueError(f"unsupported extraction.expression_mode: {expression_mode}")
    else:
        raise ValueError(f"unsupported extraction.mode: {mode}")
    if gate is not None:
        if gate not in {"project", "user"}:
            raise ValueError(f"unsupported graph provenance gate: {gate}")
        for obj in batch.objects:
            obj.data["gate"] = gate
    checks = run_deterministic_checks(document, batch, root=root_path)
    tier_inputs = TierInputs(
        nversion_agreed=None,
        properties_ok=check_draft_batch_properties(batch, root=root_path).ok,
        covered_nodes=collect_covered_nodes(root_path),
    )
    routed = route_drafts(batch, checks, config=settings, tier_inputs=tier_inputs)
    return write_routed_drafts(batch, routed, root=root_path, config=settings, document=document)


def extract_document(
    document_id: str,
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    client: LlmClient | None = None,
    config: dict[str, Any] | None = None,
    manifest: AcquisitionManifest | None = None,
    raw_store: str | Path | None = None,
    gate: str | None = None,
) -> RoutedDrafts:
    """Run one document inside an inspectable provider-call run context."""
    root_path = Path(root).resolve() if root is not None else project_root()
    settings = config if config is not None else load_config(root=root_path)
    with extraction_run(
        root=root_path,
        document_id=document_id,
        year=year,
        config=settings,
    ):
        return _extract_document_impl(
            document_id,
            year=year,
            root=root_path,
            client=client,
            config=settings,
            manifest=manifest,
            raw_store=raw_store,
            gate=gate,
        )


def _merge_expression_batch(base: Any, expression_batch: Any) -> Any:
    """Add generator-backed expressions to an outline-first cell projection.

    The outline pass remains the source of the broad form-cell inventory.  The
    generator pass contributes only expression objects and the citations they
    reference, so a second model response cannot replace or hand-edit the
    deterministic cell spine.  If a generator returns no expression objects,
    the outline result is preserved and the missing layer remains measurable.
    """
    expression_objects = [
        obj for obj in expression_batch.objects if obj.kind in {"edges", "rules"}
    ]
    if not expression_objects:
        return base

    expression_citation_ids = {
        str(citation_id)
        for obj in expression_objects
        for citation_id in obj.data.get("citation_refs", []) or []
    }
    generated_citations = [
        obj
        for obj in expression_batch.items("citations")
        if obj.object_id in expression_citation_ids
    ]
    replaced = {(obj.kind, obj.object_id) for obj in expression_objects}
    replaced.update((obj.kind, obj.object_id) for obj in generated_citations)
    merged = [
        obj
        for obj in base.objects
        if (obj.kind, obj.object_id) not in replaced
    ]
    merged.extend(generated_citations)
    merged.extend(expression_objects)
    return type(base)(
        document_id=base.document_id,
        year=base.year,
        objects=merged,
        llm_calls=[*base.llm_calls, *expression_batch.llm_calls],
        micro_stats=base.micro_stats,
    )


def extract_year(
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    client: LlmClient | None = None,
    secondary_client: LlmClient | None = None,
    example_client: LlmClient | None = None,
    config: dict[str, Any] | None = None,
) -> list[RoutedDrafts]:
    """Run extraction for manifest documents in one tax year."""
    root_path = Path(root).resolve() if root is not None else project_root()
    settings = config if config is not None else load_config(root=root_path)
    llm_client = client or build_llm_client(settings)
    manifest = load_manifest(root=root_path)
    if str(manifest.tax_year) != str(year):
        raise ValueError(f"manifest tax_year {manifest.tax_year} does not match requested {year}")
    extract_entries = [entry for entry in manifest.documents if entry.kind in FORM_KINDS]
    max_docs = int(get_config_value(settings, "extraction.max_docs_per_run", len(extract_entries)))
    routed: list[RoutedDrafts] = []
    for entry in extract_entries[:max_docs]:
        routed_batch = extract_document(
            entry.document_id,
            year=year,
            root=root_path,
            client=llm_client,
            config=settings,
        )
        _write_batch_verification_sidecars(
            document_id=entry.document_id,
            year=year,
            root=root_path,
            draft_dir=routed_batch.output_dir,
            config=settings,
            primary_client=llm_client,
            secondary_client=secondary_client,
            example_client=example_client or llm_client,
        )
        routed.append(routed_batch)
    return routed


def _write_batch_verification_sidecars(
    *,
    document_id: str,
    year: str | int,
    root: Path,
    draft_dir: Path | None,
    config: dict[str, Any],
    primary_client: LlmClient,
    secondary_client: LlmClient | None,
    example_client: LlmClient,
) -> None:
    from tax_graph.verify.examples import mine_examples
    from tax_graph.verify.nversion import run_nversion_extraction

    if draft_dir is None:
        return
    metrics_path = draft_dir / "metrics.yaml"
    metrics = _load_yaml(metrics_path)
    document = load_document_input(document_id, year=year, root=root, config=config)

    nversion_payload = {"ran": False, "status": "not_configured", "diffs": 0}
    if secondary_client is not None or get_config_value(config, "llm.nversion_model"):
        nversion_report = run_nversion_extraction(
            document,
            primary_client=primary_client,
            secondary_client=secondary_client or build_llm_client(_secondary_llm_config(config)),
            config=config,
            root=root,
        )
        nversion_payload = {
            "ran": True,
            "status": nversion_report.status,
            "diffs": len(nversion_report.diffs),
            "primary_model": nversion_report.primary_model,
            "secondary_model": nversion_report.secondary_model,
            "primary_family": nversion_report.primary_family,
            "secondary_family": nversion_report.secondary_family,
            "review_entries": [
                {
                    "kind": entry.kind,
                    "object_id": entry.object_id,
                    "reason": entry.reason,
                }
                for entry in nversion_report.review_entries
            ],
        }
    _write_yaml(draft_dir / "nversion.yaml", nversion_payload)

    example_limit = int(get_config_value(config, "extraction.example_mining_limit", 10))
    example_report = mine_examples(
        document_id=document_id,
        year=year,
        root=root,
        client=example_client,
        config=config,
        limit=example_limit,
        source="yaml",
    )
    example_payload = {
        "ran": True,
        "document_id": document_id,
        "examples": len(example_report.examples),
        "agreed": example_report.agreed,
        "disagreed": example_report.disagreed,
        "unmappable": example_report.unmappable,
        "items": [
            {
                "example_id": example.block.example_id,
                "source_document_id": example.block.source_document_id,
                "status": example.status,
                "mismatches": list(example.mismatches),
            }
            for example in example_report.examples
        ],
    }
    _write_yaml(draft_dir / "example_mining.yaml", example_payload)

    metrics["nversion"] = nversion_payload
    metrics["example_mining"] = {
        key: example_payload[key]
        for key in ("ran", "examples", "agreed", "disagreed", "unmappable")
    }
    _write_yaml(metrics_path, metrics)


def _secondary_llm_config(config: dict[str, Any]) -> dict[str, Any]:
    secondary = yaml.safe_load(yaml.safe_dump(config, sort_keys=False)) or {}
    nversion_model = get_config_value(config, "llm.nversion_model")
    if nversion_model:
        secondary.setdefault("llm", {})["micro_model"] = nversion_model
        secondary.setdefault("llm", {})["model"] = nversion_model
    return secondary


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"expected mapping in {path}")
    return payload


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False), encoding="utf-8", newline="\n")
