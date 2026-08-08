"""Local, user-gated graph extensions.

The extension harness deliberately reuses the existing acquire, render, and
extract stages. It owns the boundary around those stages: a separate overlay,
an explicit user gate, a review queue entry, and a content-hashed package.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import json
from pathlib import Path
import shutil
from typing import Any, Callable
import urllib.request
import zipfile

import jsonschema
import yaml

from tax_graph.acquire.fetch import fetch_manifest_documents
from tax_graph.acquire.manifest import AcquisitionManifest, ManifestEntry, load_manifest
from tax_graph.acquire.render import render_source
from tax_graph.config import get_config_value, load_config, resolve_llm_model, resolve_secret
from tax_graph.documents import document_class_for
from tax_graph.extract import extract_document
from tax_graph.io.loader import (
    GRAPH_KINDS,
    extension_content_hash,
    load_graph,
)
from tax_graph.review_queue import upsert_deferred_review_entry
from tax_graph.validate.graph_validator import validate_loaded_graph
from tax_graph.addressing import build_document_addresses


EXTENSION_GATE = "user"
EXTENSION_TIER = "T1"
EXTENSION_METADATA = "extension.json"
@dataclass(frozen=True)
class DoctorCheck:
    """One prerequisite result from ``extend doctor``."""

    name: str
    ok: bool
    detail: str
    fix: str = ""


@dataclass(frozen=True)
class DoctorReport:
    """All local extension prerequisite checks."""

    checks: tuple[DoctorCheck, ...]

    @property
    def ok(self) -> bool:
        """Whether every required check passed."""
        return all(check.ok for check in self.checks)

    def format_report(self) -> str:
        """Render a stable, actionable doctor report."""
        lines = ["=== extension doctor ==="]
        for check in self.checks:
            status = "OK" if check.ok else "MISSING"
            lines.append(f"  {status}: {check.name} - {check.detail}")
            if not check.ok and check.fix:
                lines.append(f"    fix: {check.fix}")
        return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class ExtensionRunResult:
    """Artifacts produced before the user makes the local promotion decision."""

    document_id: str
    year: str
    draft_dir: Path
    source_hash: str
    review_queue_path: Path
    routed_ok: bool
    verification_tier: str


@dataclass(frozen=True)
class ExtensionAcceptResult:
    """Result of explicitly accepting a local extension."""

    document_id: str
    year: str
    extension_dir: Path
    content_hash: str
    validation_errors: tuple[str, ...]


@dataclass(frozen=True)
class ExtensionPackageResult:
    """Result of packaging an accepted extension for contribution review."""

    document_id: str
    year: str
    path: Path
    content_hash: str


def build_address_contribution(
    document_id: str,
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> Path:
    """Build a machine-validated, pending-review address package outside the live corpus."""
    _validate_document_id(document_id)
    root_path = Path(root).resolve() if root is not None else Path.cwd().resolve()
    settings = config if config is not None else load_config(root=root_path)
    payload = build_document_addresses(root_path, document_id)
    schemas = {
        "addresses.yaml": "address_registry.schema.json",
        "widget_bindings.yaml": "address_binding.schema.json",
        "node_bindings.yaml": "address_binding.schema.json",
        "references.yaml": "address_reference.schema.json",
    }
    artifacts = {
        "addresses.yaml": payload["registry"],
        "widget_bindings.yaml": payload["widget_bindings"],
        "node_bindings.yaml": payload["node_bindings"],
        "references.yaml": payload["references"],
    }
    for name, schema_name in schemas.items():
        schema = json.loads((root_path / "schemas" / schema_name).read_text(encoding="utf-8"))
        jsonschema.validate(artifacts[name], schema)
    output = extension_root(root_path, settings) / str(year) / "_drafts" / document_id / "addressing"
    output.mkdir(parents=True, exist_ok=True)
    for name, artifact in artifacts.items():
        (output / name).write_text(yaml.safe_dump(artifact, sort_keys=False), encoding="utf-8")
    unresolved = sorted(
        set(_field_disposition_names(root_path, str(year), document_id)) - set(payload["field_addresses"])
    )
    report = {
        "schema_version": 1,
        "document_id": document_id,
        "tax_year": int(year),
        "gate": EXTENSION_GATE,
        "project_corpus": False,
        "human_confirmed": False,
        "review_status": "pending",
        "coverage": payload["coverage"],
        "unresolved_field_names": unresolved,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="ascii")
    return output


def extension_root(root: str | Path, config: dict[str, Any] | None = None) -> Path:
    """Resolve the configured local extension overlay directory."""
    root_path = Path(root).resolve()
    configured = get_config_value(config or {}, "project.paths.graph_ext_dir", "graph_ext")
    candidate = Path(configured)
    return candidate if candidate.is_absolute() else root_path / candidate


def doctor_extension(
    *,
    root: str | Path,
    config: dict[str, Any] | None = None,
    check_network: bool = False,
    network_url: str | None = None,
) -> DoctorReport:
    """Check configuration, credentials, network reachability, and layout.

    Network probing is opt-in so the normal doctor command remains hermetic and
    does not unexpectedly contact an external service.
    """
    root_path = Path(root).resolve()
    settings = config if config is not None else load_config(root=root_path)
    checks: list[DoctorCheck] = []

    provider = get_config_value(settings, "llm.provider")
    try:
        model = resolve_llm_model(settings)
    except ValueError:
        model = None
    if provider and model:
        checks.append(DoctorCheck("llm configuration", True, f"provider={provider}, model={model}"))
    else:
        missing = "provider" if not provider else "model"
        checks.append(
            DoctorCheck(
                "llm configuration",
                False,
                f"missing llm.{missing}; no vendor default is selected",
                "set llm.provider and llm.model in the local config",
            )
        )

    llm_key = resolve_secret(
        settings,
        "llm.api_key",
        keyring_path="llm.api_key_keyring",
        env_path="llm.api_key_env",
    )
    checks.append(
        DoctorCheck(
            "llm credentials",
            bool(llm_key),
            "configured through config, keyring, or environment" if llm_key else "no LLM API key resolved",
            "set the configured environment variable or keyring entry; never commit the key",
        )
    )

    ocr_key = resolve_secret(
        settings,
        "ocr.api_key",
        keyring_path="ocr.api_key_keyring",
        env_path="ocr.api_key_env",
    )
    checks.append(
        DoctorCheck(
            "ocr credentials",
            bool(ocr_key),
            "Mistral OCR key resolved" if ocr_key else "Mistral OCR key not resolved",
            "set the configured OCR environment variable or keyring entry for instruction PDFs",
        )
    )

    if check_network:
        url = network_url or "https://www.irs.gov"
        try:
            request = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(request, timeout=10) as response:
                status = int(getattr(response, "status", 200))
            checks.append(DoctorCheck("network", 200 <= status < 400, f"HEAD {url} -> {status}"))
        except Exception as exc:  # pragma: no cover - platform/network dependent.
            checks.append(DoctorCheck("network", False, f"could not reach {url}: {exc}", "check network access and retry"))
    else:
        checks.append(DoctorCheck("network", True, "not checked (use --network to probe IRS reachability)"))

    configured_years = get_config_value(settings, "project.tax_years", [2025])
    doctor_year = configured_years[0] if isinstance(configured_years, list) and configured_years else 2025
    graph_dir = root_path / "graph" / str(doctor_year)
    ext_dir = extension_root(root_path, settings)
    layout_ok = root_path.is_dir() and graph_dir.is_dir()
    if layout_ok:
        try:
            ext_dir.mkdir(parents=True, exist_ok=True)
            layout_detail = f"graph={graph_dir}; extension overlay={ext_dir}"
        except OSError as exc:
            layout_ok = False
            layout_detail = f"extension overlay is not writable: {exc}"
    else:
        layout_detail = f"missing source graph directory: {graph_dir}"
    checks.append(
        DoctorCheck(
            "disk layout",
            layout_ok,
            layout_detail,
            "run from the project root or provide --root pointing at a Tax Graph checkout",
        )
    )
    return DoctorReport(checks=tuple(checks))


def run_extension(
    document_id: str,
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    url: str | None = None,
    kind: str | None = None,
    title: str | None = None,
    instructions_url: str | None = None,
    instructions_document_id: str | None = None,
    config: dict[str, Any] | None = None,
    fetch_bytes: Callable[[str, dict[str, Any]], bytes] | None = None,
    renderer: Callable[..., Any] | None = None,
    ocr_client: object | None = None,
    client: object | None = None,
    extractor: Callable[..., Any] | None = None,
    today: dt.date | None = None,
) -> ExtensionRunResult:
    """Acquire, render, extract, verify, and queue one user extension.

    This function intentionally stops before promotion. The separate
    :func:`accept_extension` call is the local user gate.
    """
    _validate_document_id(document_id)
    root_path = Path(root).resolve() if root is not None else Path.cwd().resolve()
    settings = config if config is not None else load_config(root=root_path)
    graph_year = str(year)
    if _extension_document_exists(document_id, graph_year, root_path, settings):
        raise ValueError(f"extension already accepted for {document_id}; re-extraction needs a new local review")

    primary, instruction = _resolve_entries(
        document_id,
        year=graph_year,
        root=root_path,
        url=url,
        kind=kind,
        instructions_url=instructions_url,
        instructions_document_id=instructions_document_id,
    )
    entries = [primary]
    if instruction is not None:
        entries.append(instruction)
    manifest = AcquisitionManifest(tax_year=int(graph_year), documents=tuple(entries))

    raw_store = _raw_store(root_path, settings)
    fetched = fetch_manifest_documents(
        entries,
        year=graph_year,
        raw_store=raw_store,
        config=settings,
        fetch_bytes=fetch_bytes,
        today=today,
    )
    fetched_by_id = {item.document_id: item for item in fetched}
    render = renderer or render_source
    render_dir = raw_store / graph_year
    for entry in entries:
        item = fetched_by_id[entry.document_id]
        if renderer is None:
            render(
                entry,
                pdf_path=item.raw_path,
                output_dir=render_dir,
                content_hash=item.content_hash,
                config=settings,
                ocr_client=ocr_client,
            )
        else:
            render(
                entry,
                pdf_path=item.raw_path,
                output_dir=render_dir,
                content_hash=item.content_hash,
                config=settings,
            )

    extension_settings = _extension_config(settings, extension_root(root_path, settings))
    extract = extractor or extract_document
    routed = extract(
        document_id,
        year=graph_year,
        root=root_path,
        client=client,
        config=extension_settings,
        manifest=manifest,
        raw_store=raw_store,
        gate=EXTENSION_GATE,
    )
    draft_dir = Path(routed.output_dir)
    _ensure_document_draft(
        draft_dir,
        document_id=document_id,
        year=graph_year,
        kind=primary.kind,
        url=primary.url,
        title=title,
        source_hash=fetched_by_id[document_id].content_hash,
    )
    input_payload = {
        "document_id": document_id,
        "tax_year": int(graph_year),
        "url": primary.url,
        "kind": primary.kind,
        "source_hash": fetched_by_id[document_id].content_hash,
        "gate": EXTENSION_GATE,
    }
    _write_json(draft_dir / "extension-input.json", input_payload)
    tier = _extension_tier(routed)
    queue_path = upsert_deferred_review_entry(
        root=root_path,
        year=graph_year,
        entry={
            "queue_id": f"extension_review_{document_id}",
            "kind": "extension_promotion",
            "status": "pending",
            "priority": "high" if not routed.ok else "medium",
            "document_id": document_id,
            "created_date": (today or dt.date.today()).isoformat(),
            "created_by": "tax_graph.extension",
            "summary": "User-gated extension awaiting explicit local accept; human review remains pending.",
            "artifact_dir": str(draft_dir.relative_to(root_path)),
            "artifact_paths": [
                str(path.relative_to(root_path))
                for path in (draft_dir / "review.md", draft_dir / "review.html", draft_dir / "metrics.yaml")
                if path.exists()
            ],
            "machine_agreed": bool(routed.ok),
            "human_confirmed": False,
            "review_status": "pending",
            "gate": EXTENSION_GATE,
            "verification_tier": tier,
            "source_hash": fetched_by_id[document_id].content_hash,
        },
    )
    return ExtensionRunResult(
        document_id=document_id,
        year=graph_year,
        draft_dir=draft_dir,
        source_hash=fetched_by_id[document_id].content_hash,
        review_queue_path=queue_path,
        routed_ok=bool(routed.ok),
        verification_tier=tier,
    )


def accept_extension(
    document_id: str,
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    config: dict[str, Any] | None = None,
    today: dt.date | None = None,
) -> ExtensionAcceptResult:
    """Promote a reviewed draft into the user-only YAML overlay."""
    _validate_document_id(document_id)
    root_path = Path(root).resolve() if root is not None else Path.cwd().resolve()
    settings = config if config is not None else load_config(root=root_path)
    graph_year = str(year)
    overlay = extension_root(root_path, settings)
    draft_dir = overlay / graph_year / "_drafts" / document_id
    extension_dir = overlay / graph_year / document_id
    if not draft_dir.is_dir():
        raise FileNotFoundError(f"extension draft not found: {draft_dir}")
    if extension_dir.exists():
        raise ValueError(f"extension already accepted: {extension_dir}")

    base = load_graph(graph_year, root_path, include_extensions=False)
    existing = load_graph(graph_year, root_path, include_extensions=True)
    occupied = _object_ids(existing.objects)
    del base  # Loading the base separately documents that collisions include shipped objects.
    payloads: dict[str, Any] = {}
    for kind, (_, is_list, id_field) in GRAPH_KINDS.items():
        path = draft_dir / f"{kind}.yaml"
        if not path.exists():
            continue
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        items = payload if (is_list or kind == "documents") else [payload]
        if not isinstance(items, list):
            raise ValueError(f"extension draft {path} has the wrong shape")
        for item in items:
            if not isinstance(item, dict) or item.get("gate") != EXTENSION_GATE:
                raise ValueError(f"extension draft {path} contains an object without gate: user")
            identity = (kind, str(item.get(id_field) or ""))
            if not identity[1]:
                raise ValueError(f"extension draft {path} is missing {id_field}")
            if identity in occupied:
                raise ValueError(f"extension object collision: {kind}/{identity[1]}")
            occupied.add(identity)
        payloads[kind] = payload
    if "documents" not in payloads:
        raise ValueError(f"extension draft has no documents.yaml: {draft_dir}")

    extension_dir.mkdir(parents=True, exist_ok=False)
    try:
        for kind, payload in payloads.items():
            _write_yaml(extension_dir / f"{kind}.yaml", payload)
        content_hash = extension_content_hash(extension_dir)
        input_payload = _load_json(draft_dir / "extension-input.json")
        metadata = {
            "document_id": document_id,
            "tax_year": int(graph_year),
            "gate": EXTENSION_GATE,
            "content_hash": content_hash,
            "source_hash": input_payload.get("source_hash"),
            "verification_tier": _load_queue_tier(root_path, graph_year, document_id),
            "accepted_date": (today or dt.date.today()).isoformat(),
            "human_review": "pending",
        }
        _write_json(extension_dir / EXTENSION_METADATA, metadata)
        loaded = load_graph(graph_year, root_path, include_extensions=True)
        validation = validate_loaded_graph(loaded)
        if not validation.ok:
            raise ValueError("accepted extension failed validation: " + "; ".join(validation.errors))
    except Exception:
        shutil.rmtree(extension_dir, ignore_errors=True)
        raise

    _update_queue_after_accept(
        root_path,
        graph_year,
        document_id,
        extension_dir=extension_dir,
        content_hash=content_hash,
    )
    return ExtensionAcceptResult(
        document_id=document_id,
        year=graph_year,
        extension_dir=extension_dir,
        content_hash=content_hash,
        validation_errors=tuple(),
    )


def package_extension(
    document_id: str,
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    config: dict[str, Any] | None = None,
    output_dir: str | Path | None = None,
) -> ExtensionPackageResult:
    """Bundle an accepted extension and its review artifacts deterministically."""
    _validate_document_id(document_id)
    root_path = Path(root).resolve() if root is not None else Path.cwd().resolve()
    settings = config if config is not None else load_config(root=root_path)
    graph_year = str(year)
    extension_dir = extension_root(root_path, settings) / graph_year / document_id
    if not extension_dir.is_dir():
        raise FileNotFoundError(f"accepted extension not found: {extension_dir}")
    metadata = _load_json(extension_dir / EXTENSION_METADATA)
    content_hash = extension_content_hash(extension_dir)
    if str(metadata.get("content_hash")) != content_hash:
        raise ValueError(f"extension content hash mismatch before package: {document_id}")

    destination = Path(output_dir).resolve() if output_dir is not None else root_path / "dist"
    destination.mkdir(parents=True, exist_ok=True)
    package_path = destination / f"{document_id}_{graph_year}.tax-graph-extension.zip"
    files: dict[str, bytes] = {}
    for path in sorted(extension_dir.iterdir(), key=lambda item: item.name):
        if path.is_file():
            files[f"graph/{path.name}"] = path.read_bytes()
    draft_dir = extension_root(root_path, settings) / graph_year / "_drafts" / document_id
    address_dir = build_address_contribution(
        document_id, year=graph_year, root=root_path, config=settings,
    ) if (root_path / "graph" / graph_year / "field_maps" / f"{document_id}.yaml").exists() else None
    for name in ("metrics.yaml", "review.md", "review.html", "nversion.yaml", "example_mining.yaml"):
        path = draft_dir / name
        if path.exists():
            files[f"review/{name}"] = path.read_bytes()
    if address_dir is not None:
        for path in sorted(address_dir.iterdir(), key=lambda item: item.name):
            if path.is_file():
                files[f"review/addressing/{path.name}"] = path.read_bytes()

    from tax_graph.verify.record import verification_summary_for_document

    summary = verification_summary_for_document(document_id, year=graph_year, root=root_path)
    files["verification.md"] = str(summary.get("page_markdown") or "").encode("ascii")
    manifest = {
        "document_id": document_id,
        "tax_year": int(graph_year),
        "gate": EXTENSION_GATE,
        "content_hash": content_hash,
        "address_review_status": "pending" if address_dir is not None else None,
        "project_corpus": False,
        "human_confirmed": False,
        "files": sorted(files),
    }
    files["package.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("ascii")
    _write_deterministic_zip(package_path, files)
    return ExtensionPackageResult(
        document_id=document_id,
        year=graph_year,
        path=package_path,
        content_hash=content_hash,
    )


def _field_disposition_names(root: Path, year: str, document_id: str) -> list[str]:
    path = root / "graph" / year / "field_maps" / f"{document_id}.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [str(item["field_name"]) for item in payload.get("field_dispositions", [])]


def _resolve_entries(
    document_id: str,
    *,
    year: str,
    root: Path,
    url: str | None,
    kind: str | None,
    instructions_url: str | None,
    instructions_document_id: str | None,
) -> tuple[ManifestEntry, ManifestEntry | None]:
    source_entry: ManifestEntry | None = None
    manifest_path = root / "config" / "manifest.yaml"
    if manifest_path.exists():
        try:
            source_entry = load_manifest(root=root).by_document_id().get(document_id)
        except Exception:
            source_entry = None
    if source_entry is None and url is None:
        from tax_graph.frontier import load_frontier_registry

        for entry in load_frontier_registry(year, root).get("frontiers", []) or []:
            target = entry.get("target") or {}
            if target.get("document_id") == document_id and entry.get("target_url"):
                source_entry = ManifestEntry(
                    document_id=document_id,
                    kind=_infer_kind(document_id, kind),
                    url=str(entry["target_url"]),
                )
                break
    if source_entry is None:
        if not url:
            raise ValueError(f"no URL known for {document_id}; provide --url")
        source_entry = ManifestEntry(document_id=document_id, kind=_infer_kind(document_id, kind), url=url)
    elif url or kind:
        source_entry = ManifestEntry(
            document_id=document_id,
            kind=kind or source_entry.kind,
            url=url or source_entry.url,
            instructions_document_id=source_entry.instructions_document_id,
            expected_sha256=source_entry.expected_sha256,
        )
    if source_entry.instructions_document_id and instructions_url is None:
        try:
            entries = load_manifest(root=root).by_document_id()
            instruction = entries.get(source_entry.instructions_document_id)
        except Exception:
            instruction = None
    else:
        instruction = None
    if instructions_url:
        instruction_id = instructions_document_id or f"instructions_{document_id}"
        instruction = ManifestEntry(document_id=instruction_id, kind="instructions", url=instructions_url)
    elif instruction is not None and instructions_document_id and instruction.document_id != instructions_document_id:
        instruction = ManifestEntry(
            document_id=instructions_document_id,
            kind=instruction.kind,
            url=instruction.url,
        )
    return source_entry, instruction


def _infer_kind(document_id: str, kind: str | None) -> str:
    if kind:
        return kind
    if document_id.startswith("schedule_"):
        return "schedule"
    if document_id.startswith("form_"):
        return "tax_form"
    return "source_document"


def _extension_config(config: dict[str, Any], graph_ext: Path) -> dict[str, Any]:
    import copy

    settings = copy.deepcopy(config)
    settings.setdefault("project", {}).setdefault("paths", {})["graph_dir"] = str(graph_ext)
    return settings


def _raw_store(root: Path, config: dict[str, Any]) -> Path:
    configured = Path(get_config_value(config, "project.paths.raw_store", ".cache/raw"))
    return configured if configured.is_absolute() else root / configured


def _ensure_document_draft(
    draft_dir: Path,
    *,
    document_id: str,
    year: str,
    kind: str,
    url: str,
    title: str | None,
    source_hash: str,
) -> None:
    path = draft_dir / "documents.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else []
    documents = payload if isinstance(payload, list) else [payload]
    documents = [item for item in documents if isinstance(item, dict)]
    document = next((item for item in documents if item.get("document_id") == document_id), None)
    if document is None:
        document = {
            "document_id": document_id,
            "title": title or document_id,
            "tax_year": int(year),
            "document_type": kind,
            "document_class": document_class_for(document_id=document_id, document_type=kind),
            "source_url": url,
            "status": "partial",
            "not_modeled_fields": [],
        }
        documents.append(document)
    document["gate"] = EXTENSION_GATE
    document["content_hash"] = source_hash
    _write_yaml(path, documents)


def _extension_tier(routed: Any) -> str:
    if not routed.ok or routed.review or routed.issues:
        return "T0"
    return EXTENSION_TIER


def _extension_document_exists(document_id: str, year: str, root: Path, config: dict[str, Any]) -> bool:
    return (extension_root(root, config) / year / document_id).is_dir()


def _object_ids(objects: dict[str, list[dict[str, Any]]]) -> set[tuple[str, str]]:
    return {
        (kind, str(obj.get(id_field)))
        for kind, (_, _, id_field) in GRAPH_KINDS.items()
        for obj in objects.get(kind, [])
        if obj.get(id_field)
    }


def _load_queue_tier(root: Path, year: str, document_id: str) -> str:
    path = root / "review_queue" / year / "deferred_review.yaml"
    if not path.exists():
        return EXTENSION_TIER
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for entry in payload.get("entries", []) or []:
        if entry.get("document_id") == document_id and entry.get("kind") == "extension_promotion":
            return str(entry.get("verification_tier") or EXTENSION_TIER)
    return EXTENSION_TIER


def _update_queue_after_accept(root: Path, year: str, document_id: str, *, extension_dir: Path, content_hash: str) -> None:
    path = root / "review_queue" / year / "deferred_review.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    entries = payload.get("entries", []) if isinstance(payload, dict) else []
    existing = next(
        (dict(item) for item in entries if isinstance(item, dict) and item.get("document_id") == document_id),
        None,
    )
    if existing is None:
        existing = {
            "queue_id": f"extension_review_{document_id}",
            "kind": "extension_promotion",
            "priority": "medium",
            "document_id": document_id,
            "created_date": dt.date.today().isoformat(),
            "created_by": "tax_graph.extension",
            "summary": "User-gated extension accepted locally; human review remains pending.",
        }
    existing.update(
        {
            "status": "accepted_local",
            "review_status": "pending",
            "human_confirmed": False,
            "gate": EXTENSION_GATE,
            "artifact_dir": str(extension_dir.relative_to(root)),
            "extension_hash": content_hash,
        }
    )
    upsert_deferred_review_entry(root=root, year=year, entry=existing)


def _validate_document_id(document_id: str) -> None:
    if not document_id or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_" for ch in document_id):
        raise ValueError(f"document_id must be lowercase snake_case: {document_id!r}")


def _write_yaml(path: Path, payload: Any) -> None:
    text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)
    text.encode("ascii")
    path.write_text(text, encoding="utf-8", newline="\n")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object in {path}")
    return payload


def _write_deterministic_zip(path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, files[name])
