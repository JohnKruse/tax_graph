"""Local-only Flask server for the artifact review workbench."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import getpass
import platform
import secrets
import socket
import uuid
from typing import Any, Callable, Mapping

from flask import Flask, jsonify, request, send_file

from workbench.artifacts import ArtifactBundle, load_artifact_bundle
from workbench.cell_inventory import build_document_cells, build_documents_index
from workbench.generated_review import GENERATED_REVIEW_DOCUMENTS, build_generated_document_cells
from workbench.manifest import build_manifest
from workbench.navigation import build_document_navigation
from workbench.preflight import preflight_manifest
from workbench.render import PageImageCache, PageRenderError, PageRenderer
from workbench.schema import SchemaValidationError, validate_session_state
from workbench.sessions import (
    default_session,
    load_session,
    save_session,
    session_progress,
    validate_unit_review_scope,
)
from workbench.verdicts import LEGACY_REVIEW_VERDICTS, REVIEW_VERDICTS, emit_verdict
from workbench.address_verdicts import append_address_verdict


REJECTION_REASON_CODES = frozenset({"pipeline_defect", "source_pathology"})


def create_app(
    root: str | Path,
    year: str | int,
    *,
    write_token: str | None = None,
    manifest: dict[str, Any] | None = None,
    bundle: ArtifactBundle | None = None,
    page_renderer: PageRenderer | None = None,
    cache_dir: str | Path | None = None,
    state_dir: str | Path | None = None,
    verdict_dir: str | Path | None = None,
    rederive_cell: Callable[[str, str, str | None], Mapping[str, Any]] | None = None,
) -> Flask:
    """Create a preflighted, local review API application."""
    root_path = Path(root).resolve()
    artifact_bundle = bundle or load_artifact_bundle(root_path, year)
    review_manifest = manifest or build_manifest(root_path, year)
    coverage = preflight_manifest(review_manifest, artifact_bundle)
    page_cache = PageImageCache(
        cache_dir or root_path / ".workbench_state" / str(year) / "page_cache",
        renderer=page_renderer,
    )
    session_root = (
        Path(state_dir)
        if state_dir is not None
        else root_path / ".workbench_state" / str(year) / "sessions"
    )
    verdict_root = (
        Path(verdict_dir)
        if verdict_dir is not None
        else root_path / "review_verdicts" / str(year)
    )

    app = Flask(__name__)
    app.config.update(
        WORKBENCH_ROOT=root_path,
        WORKBENCH_YEAR=int(year),
        WORKBENCH_WRITE_TOKEN=write_token or secrets.token_urlsafe(32),
        WORKBENCH_MANIFEST=review_manifest,
        WORKBENCH_BUNDLE=artifact_bundle,
        WORKBENCH_COVERAGE=coverage,
        WORKBENCH_PAGE_CACHE=page_cache,
        WORKBENCH_SESSION_ROOT=session_root,
        WORKBENCH_VERDICT_ROOT=verdict_root,
        WORKBENCH_REVIEWER_ID=_machine_reviewer_id(),
        WORKBENCH_REDERIVE_CELL=rederive_cell,
    )
    entries = {
        str(entry["queue_id"]): entry
        for entry in review_manifest.get("entries", [])
        if isinstance(entry, dict) and entry.get("queue_id")
    }

    @app.get("/")
    def get_shell() -> Any:
        """Serve the no-build review workbench shell."""
        if app.static_folder is None:
            return jsonify({"error": "workbench static assets are unavailable"}), 500
        shell = (Path(app.static_folder) / "index.html").read_text(encoding="utf-8")
        token = str(app.config["WORKBENCH_WRITE_TOKEN"])
        shell = shell.replace(
            '<meta name="workbench-write-token" content="">',
            f'<meta name="workbench-write-token" content="{token}">',
        )
        return shell, 200, {"Content-Type": "text/html; charset=utf-8"}

    @app.get("/api/queue")
    def get_queue() -> Any:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        total_units = 0
        for entry in entries.values():
            units = entry.get("units", []) or []
            total_units += len(units)
            documents = sorted({
                str(unit["official_location"]["document_id"])
                for unit in units
                if isinstance(unit.get("official_location"), dict)
            })
            groups[str(entry.get("review_kind", "object"))].append({
                "queue_id": entry["queue_id"],
                "review_kind": entry.get("review_kind", "object"),
                "status": entry.get("status", "pending"),
                "summary": entry.get("summary", ""),
                "unit_count": len(units),
                "required_units": sum(bool(unit.get("required")) for unit in units),
                "located_units": sum(isinstance(unit.get("official_location"), dict) for unit in units),
                "document_ids": documents,
            })
        grouped = [
            {"review_kind": kind, "entries": sorted(items, key=lambda item: item["queue_id"])}
            for kind, items in sorted(groups.items())
        ]
        navigation = build_document_navigation(entries.values(), artifact_bundle.graph.objects("documents"))
        return jsonify({
            "tax_year": int(year),
            "manifest_hash": review_manifest["manifest_hash"],
            "progress": {
                "total_entries": len(entries),
                "reviewed_entries": 0,
                "remaining_entries": len(entries),
                "total_units": total_units,
            },
            "groups": grouped,
            "documents": navigation,
            "coverage": coverage,
        })

    @app.get("/api/entries/<queue_id>")
    def get_entry(queue_id: str) -> Any:
        entry = entries.get(queue_id)
        if entry is None:
            return jsonify({"error": "unknown queue_id", "queue_id": queue_id}), 404
        return jsonify({
            "tax_year": int(year),
            "manifest_hash": review_manifest["manifest_hash"],
            "entry": entry,
        })

    @app.get("/api/documents/<document_id>/pages/<int:page>.png")
    def get_page(document_id: str, page: int) -> Any:
        pdf = next((item for item in artifact_bundle.pdfs if item.path.stem == document_id), None)
        if pdf is None:
            return jsonify({"error": "unknown document_id", "document_id": document_id}), 404
        try:
            scale = float(request.args.get("scale", "2.0"))
            path = page_cache.get(pdf.path, pdf.sha256, page, scale)
        except (ValueError, PageRenderError) as exc:
            return jsonify({"error": str(exc)}), 400
        return send_file(path, mimetype="image/png", conditional=True)

    @app.get("/api/evidence/<object_type>/<path:object_id>")
    def get_evidence(object_type: str, object_id: str) -> Any:
        matches = _evidence_matches(artifact_bundle, object_type, object_id)
        if not matches:
            return jsonify({
                "error": "unknown evidence object", "object_type": object_type, "object_id": object_id,
            }), 404
        if len(matches) > 1:
            return jsonify({
                "error": "ambiguous evidence object", "object_type": object_type,
                "object_id": object_id, "sources": [source for source, _ in matches],
            }), 409
        source, raw = matches[0]
        geometry = [
            item for item in artifact_bundle.geometry.get("entries", [])
            if object_type in {"node", "node_instance"}
            and item.get("node_id") == object_id.split("#", 1)[0]
        ]
        queue_units = [
            {"queue_id": entry["queue_id"], "unit_id": unit["unit_id"]}
            for entry in entries.values()
            for unit in entry.get("units", []) or []
            if any(
                ref.get("object_type") == object_type and ref.get("object_id") == object_id
                for ref in unit.get("object_refs", []) or []
                if isinstance(ref, dict)
            )
        ]
        return jsonify({
            "object_type": object_type,
            "object_id": object_id,
            "source_artifact": source,
            "raw": raw,
            "geometry": geometry,
            "queue_units": queue_units,
            "citation_refs": sorted(str(value) for value in raw.get("citation_refs", []) or []),
        })

    @app.get("/api/sessions/<queue_id>")
    def get_session(queue_id: str) -> Any:
        entry = entries.get(queue_id)
        if entry is None:
            return jsonify({"error": "unknown queue_id", "queue_id": queue_id}), 404
        try:
            payload = load_session(session_root / f"{queue_id}.json")
        except (ValueError, SchemaValidationError) as exc:
            return jsonify({"error": str(exc), "queue_id": queue_id}), 409
        if payload is not None and payload.get("manifest_hash") != review_manifest["manifest_hash"]:
            return jsonify({"error": "saved session belongs to a stale review manifest", "queue_id": queue_id}), 409
        session = payload or default_session(
            int(year), queue_id, review_manifest["manifest_hash"], entry.get("units", [])
        )
        try:
            validate_unit_review_scope(session, entry.get("units", []))
            response = dict(session)
            response["progress"] = session_progress(session, entry.get("units", []))
        except ValueError as exc:
            return jsonify({"error": str(exc), "queue_id": queue_id}), 409
        return jsonify(response)

    @app.put("/api/sessions/<queue_id>")
    def put_session(queue_id: str) -> Any:
        denied = _require_write_token(app)
        if denied is not None:
            return denied
        entry = entries.get(queue_id)
        if entry is None:
            return jsonify({"error": "unknown queue_id", "queue_id": queue_id}), 404
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "session body must be a JSON object"}), 400
        if (
            payload.get("queue_id") != queue_id
            or payload.get("tax_year") != int(year)
            or payload.get("manifest_hash") != review_manifest["manifest_hash"]
        ):
            return jsonify({"error": "session queue_id, tax_year, and manifest_hash must match"}), 400
        session_payload = dict(payload)
        session_payload.pop("progress", None)
        unit_ids = {str(unit.get("unit_id")) for unit in entry.get("units", []) or []}
        referenced = set(str(value) for value in session_payload.get("visited_unit_ids", []) or [])
        if session_payload.get("current_unit_id") is not None:
            referenced.add(str(session_payload["current_unit_id"]))
        selection = session_payload.get("selection")
        if isinstance(selection, dict) and selection.get("unit_id") is not None:
            referenced.add(str(selection["unit_id"]))
        unknown = sorted(referenced - unit_ids)
        if unknown:
            return jsonify({"error": "session references units outside the queue entry", "unit_ids": unknown}), 400
        try:
            validate_unit_review_scope(session_payload, entry.get("units", []))
            validate_session_state(session_payload)
            save_session(session_root / f"{queue_id}.json", session_payload)
        except (ValueError, SchemaValidationError) as exc:
            return jsonify({"error": str(exc)}), 400
        response = dict(session_payload)
        response["progress"] = session_progress(session_payload, entry.get("units", []))
        return jsonify(response)

    # Resolved lazily and cached: only the document-centric routes need the artifact
    # bundle, so constructing the app must not read it. The session-API tests build an
    # app with a stub bundle to exercise the queue routes in isolation, and an eager read
    # here turned CI red on `AttributeError: 'object' object has no attribute 'graph'`.
    _documents: dict[str, Any] = {}

    def _document_context() -> dict[str, Any]:
        if not _documents:
            entries = artifact_bundle.geometry.get("entries", []) or []
            _documents.update(
                titles={
                    str(document["document_id"]): str(document.get("title") or document["document_id"])
                    for document in artifact_bundle.graph.objects("documents")
                    if isinstance(document, dict) and document.get("document_id")
                },
                geometry_entries=entries,
                page_geometry=artifact_bundle.geometry.get("pages", []) or [],
                valid_document_ids=frozenset(
                    str(entry["document_id"])
                    for entry in entries
                    if isinstance(entry, dict) and entry.get("document_id")
                ),
            )
        return _documents

    def _document_cells(document_id: str) -> list[dict[str, Any]]:
        builder = build_generated_document_cells if document_id in GENERATED_REVIEW_DOCUMENTS else build_document_cells
        return builder(
            root_path,
            year,
            document_id,
            geometry_entries=_document_context()["geometry_entries"],
            page_geometry=_document_context()["page_geometry"],
        ).cells

    def _pseudo_units(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # The session helpers only read ``unit_id`` and the first page, so the
        # cell list projects cleanly onto them without a manifest entry.
        return [
            {"unit_id": cell["cell_id"], "official_location": {"page": cell["page"]}}
            for cell in cells
        ]

    @app.get("/api/documents")
    def get_documents() -> Any:
        return jsonify({
            "tax_year": int(year),
            "manifest_hash": review_manifest["manifest_hash"],
            "documents": build_documents_index(
                root_path,
                year,
                sorted(_document_context()["valid_document_ids"]),
                geometry_entries=_document_context()["geometry_entries"],
                page_geometry=_document_context()["page_geometry"],
                titles=_document_context()["titles"],
                generated_documents=GENERATED_REVIEW_DOCUMENTS,
            ),
        })

    @app.get("/api/documents/<document_id>/cells")
    def get_document_cells(document_id: str) -> Any:
        if document_id not in _document_context()["valid_document_ids"]:
            return jsonify({"error": "unknown document_id", "document_id": document_id}), 404
        cells = _document_cells(document_id)
        return jsonify({
            "tax_year": int(year),
            "manifest_hash": review_manifest["manifest_hash"],
            "document_id": document_id,
            "title": _document_context()["titles"].get(document_id, document_id),
            "pages": sorted({cell["page"] for cell in cells}),
            "page_geometry": build_document_cells(
                root_path,
                year,
                document_id,
                geometry_entries=_document_context()["geometry_entries"],
                page_geometry=_document_context()["page_geometry"],
                include_inputs=False,
            ).page_geometry,
            "cells": cells,
        })

    @app.get("/api/documents/<document_id>/session")
    def get_document_session(document_id: str) -> Any:
        if document_id not in _document_context()["valid_document_ids"]:
            return jsonify({"error": "unknown document_id", "document_id": document_id}), 404
        units = _pseudo_units(_document_cells(document_id))
        path = session_root / "documents" / f"{document_id}.json"
        try:
            payload = load_session(path)
        except (ValueError, SchemaValidationError) as exc:
            return jsonify({"error": str(exc), "document_id": document_id}), 409
        if payload is not None and payload.get("manifest_hash") != review_manifest["manifest_hash"]:
            return jsonify({"error": "saved session belongs to a stale review manifest", "document_id": document_id}), 409
        session = payload or default_session(
            int(year), document_id, review_manifest["manifest_hash"], units
        )
        try:
            validate_unit_review_scope(session, units)
            response = dict(session)
            response["progress"] = session_progress(session, units)
        except ValueError as exc:
            return jsonify({"error": str(exc), "document_id": document_id}), 409
        return jsonify(response)

    @app.put("/api/documents/<document_id>/session")
    def put_document_session(document_id: str) -> Any:
        denied = _require_write_token(app)
        if denied is not None:
            return denied
        if document_id not in _document_context()["valid_document_ids"]:
            return jsonify({"error": "unknown document_id", "document_id": document_id}), 404
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "session body must be a JSON object"}), 400
        if (
            payload.get("queue_id") != document_id
            or payload.get("tax_year") != int(year)
            or payload.get("manifest_hash") != review_manifest["manifest_hash"]
        ):
            return jsonify({"error": "session queue_id, tax_year, and manifest_hash must match"}), 400
        session_payload = dict(payload)
        session_payload.pop("progress", None)
        units = _pseudo_units(_document_cells(document_id))
        cell_ids = {str(unit["unit_id"]) for unit in units}
        referenced = set(str(value) for value in session_payload.get("visited_unit_ids", []) or [])
        if session_payload.get("current_unit_id") is not None:
            referenced.add(str(session_payload["current_unit_id"]))
        selection = session_payload.get("selection")
        if isinstance(selection, dict) and selection.get("unit_id") is not None:
            referenced.add(str(selection["unit_id"]))
        unknown = sorted(referenced - cell_ids)
        if unknown:
            return jsonify({"error": "session references cells outside the document", "unit_ids": unknown}), 400
        try:
            validate_unit_review_scope(session_payload, units)
            validate_session_state(session_payload)
            save_session(session_root / "documents" / f"{document_id}.json", session_payload)
        except (ValueError, SchemaValidationError) as exc:
            return jsonify({"error": str(exc)}), 400
        response = dict(session_payload)
        response["progress"] = session_progress(session_payload, units)
        return jsonify(response)

    @app.post("/api/rederive")
    def post_rederive() -> Any:
        """Try one cell again with an optional comment and persist nothing."""
        denied = _require_write_token(app)
        if denied is not None:
            return denied
        handler = app.config.get("WORKBENCH_REDERIVE_CELL")
        if handler is None:
            return jsonify({"error": "cell re-derive is not configured"}), 501
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "re-derive body must be a JSON object"}), 400
        unexpected = sorted(set(payload) - {"document_id", "line", "draft_comment"})
        if unexpected:
            return jsonify({"error": "unexpected re-derive fields", "fields": unexpected}), 400
        document_id = str(payload.get("document_id") or "").strip()
        line = str(payload.get("line") or "").strip()
        draft_comment = payload.get("draft_comment")
        if not document_id or not line:
            return jsonify({"error": "document_id and line are required"}), 400
        if draft_comment is not None and not isinstance(draft_comment, str):
            return jsonify({"error": "draft_comment must be a string or null"}), 400
        if isinstance(draft_comment, str) and len(draft_comment) > 10000:
            return jsonify({"error": "draft_comment is too long"}), 400
        try:
            result = handler(document_id, line, draft_comment)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:  # noqa: BLE001 - local provider failures become one request error.
            return jsonify({"error": f"re-derive failed: {type(exc).__name__}: {exc}"}), 502
        if not isinstance(result, Mapping):
            return jsonify({"error": "re-derive handler returned a non-object result"}), 502
        return jsonify(dict(result))

    @app.post("/api/verdicts")
    def post_verdict() -> Any:
        denied = _require_write_token(app)
        if denied is not None:
            return denied
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "verdict body must be a JSON object"}), 400
        allowed = {
            "queue_id", "verdict_id", "reviewer_id", "human_minutes", "verdict",
            "reviewed_at", "reason", "object_ref", "source_override", "comment",
            "origin", "reviewer_tag",
        }
        unexpected = sorted(set(payload) - allowed)
        if unexpected:
            return jsonify({"error": "unexpected verdict fields", "fields": unexpected}), 400
        queue_id = str(payload.get("queue_id", ""))
        if queue_id not in entries:
            return jsonify({"error": "unknown queue_id", "queue_id": queue_id}), 404
        required = ("verdict_id", "human_minutes", "verdict")
        missing = [key for key in required if payload.get(key) is None]
        if missing:
            return jsonify({"error": "missing verdict fields", "fields": missing}), 400
        verdict = str(payload.get("verdict") or "")
        reason = str(payload.get("reason") or "").strip()
        comment = str(payload.get("comment") or "").strip()
        if verdict in {"questioned", "rejected"}:
            if not comment:
                return jsonify({"error": "a questioned or rejected verdict requires a non-empty comment"}), 400
        elif verdict in LEGACY_REVIEW_VERDICTS:
            if reason not in REJECTION_REASON_CODES:
                return jsonify({"error": "a rejection requires reason pipeline_defect or source_pathology"}), 400
            if not comment:
                return jsonify({"error": "a rejection requires a non-empty comment"}), 400
        elif verdict not in REVIEW_VERDICTS:
            return jsonify({"error": "verdict must be confirmed, questioned, or rejected"}), 400
        try:
            object_ref = _scoped_verdict_ref(entries[queue_id], payload.get("object_ref"))
            result = emit_verdict(
                root=root_path,
                year=year,
                queue_id=queue_id,
                manifest_hash=str(review_manifest["manifest_hash"]),
                verdict_id=str(payload["verdict_id"]),
                reviewer_id=str(app.config["WORKBENCH_REVIEWER_ID"]),
                human_minutes=float(payload["human_minutes"]),
                verdict=verdict,
                reviewed_at=payload.get("reviewed_at"),
                reason=payload.get("reason"),
                object_ref=object_ref,
                source_override=payload.get("source_override"),
                comment=payload.get("comment"),
                reviewer_tag=payload.get("reviewer_tag"),
                output_path=verdict_root / f"{payload['verdict_id']}.yaml",
            )
            _append_address_review_if_applicable(
                root=root_path,
                year=year,
                queue_id=queue_id,
                object_ref=object_ref,
                verdict_payload=payload,
                reviewer_id=str(app.config["WORKBENCH_REVIEWER_ID"]),
                cells=_document_cells(queue_id) if queue_id in GENERATED_REVIEW_DOCUMENTS else [],
                store_path=verdict_root / "address_verdicts.jsonl",
            )
        except FileExistsError as exc:
            return jsonify({"error": str(exc)}), 409
        except (TypeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"verdict": result.payload, "path": result.path.name}), 201

    return app


def _require_write_token(app: Flask) -> Any | None:
    supplied = request.headers.get("X-Workbench-Token", "")
    expected = str(app.config["WORKBENCH_WRITE_TOKEN"])
    if not supplied or not secrets.compare_digest(supplied, expected):
        return jsonify({"error": "missing or invalid write token"}), 403
    return None


def _machine_reviewer_id() -> str:
    """Identify the local review session without asking a human to type a name."""
    host = socket.gethostname() or "unknown-host"
    user = getpass.getuser() or "unknown-user"
    session = uuid.uuid4().hex
    safe_host = "".join(char if char.isalnum() or char in "._-" else "_" for char in host)
    safe_user = "".join(char if char.isalnum() or char in "._-" else "_" for char in user)
    operating_system = platform.system() or "unknown-os"
    safe_os = "".join(char if char.isalnum() or char in "._-" else "_" for char in operating_system)
    return f"workbench/{safe_os}/{safe_host}/{safe_user}/{session}"


def _scoped_verdict_ref(entry: dict[str, Any], supplied: Any) -> dict[str, str] | None:
    """Return a normalized target only when it belongs to the reviewed entry."""
    if supplied is None:
        return None
    if not isinstance(supplied, dict) or not supplied.get("object_id"):
        raise ValueError("object_ref must identify one scoped object")
    object_id = str(supplied["object_id"])
    artifact_path = str(supplied.get("artifact_path") or "")
    candidates = []
    for unit in entry.get("units", []) or []:
        for ref in unit.get("object_refs", []) or []:
            if not isinstance(ref, dict) or str(ref.get("object_id")) != object_id:
                continue
            if artifact_path and str(ref.get("artifact_path") or "") != artifact_path:
                continue
            candidates.append(ref)
    unique = {
        (str(ref.get("object_id")), str(ref.get("artifact_path") or ""), str(ref.get("object_type") or ""))
        for ref in candidates
    }
    if len(unique) != 1:
        raise ValueError("object_ref does not resolve to exactly one object in the queue entry")
    matched_id, matched_path, object_type = next(iter(unique))
    expected_kind = Path(matched_path).parent.name if matched_path else f"{object_type}s"
    supplied_kind = str(supplied.get("object_kind") or "")
    if supplied_kind and supplied_kind != expected_kind:
        raise ValueError("object_ref object_kind does not match the scoped artifact")
    result = {"object_id": matched_id, "object_kind": expected_kind}
    if matched_path:
        result["artifact_path"] = matched_path
    return result


def _append_address_review_if_applicable(
    *,
    root: str | Path,
    year: str | int,
    queue_id: str,
    object_ref: dict[str, str] | None,
    verdict_payload: dict[str, Any],
    reviewer_id: str,
    cells: list[dict[str, Any]],
    store_path: str | Path,
) -> None:
    """Mirror generated-cell verdicts into the durable address ledger."""
    if not object_ref or not cells:
        return
    address = str(object_ref.get("object_id") or "")
    cell = next((item for item in cells if str(item.get("address_id") or "") == address), None)
    if cell is None:
        return
    judgement = str(verdict_payload.get("verdict") or "")
    comment = verdict_payload.get("comment")
    append_address_verdict(
        root=root,
        year=year,
        address=address,
        label=str(cell.get("display_name") or cell.get("official_ref") or address),
        expression=cell.get("expression"),
        form_citations=[item.get("quoted_text") for item in cell.get("form_citations", []) or []],
        instruction_citations=[item.get("quoted_text") for item in cell.get("instruction_citations", []) or []],
        judgement=judgement,
        reviewer_id=reviewer_id,
        reviewed_at=verdict_payload.get("reviewed_at"),
        verdict_id=str(verdict_payload.get("verdict_id") or ""),
        store_path=store_path,
        provenance={
            "queue_id": queue_id,
            "generated_model": cell.get("generated_model"),
            "generated_provider": cell.get("generated_provider"),
            "review_source": cell.get("review_source"),
        },
        comment=str(comment) if comment is not None else None,
        origin=str(verdict_payload.get("origin") or "") or None,
        reviewer_tag=str(verdict_payload.get("reviewer_tag") or "") or None,
    )


def _evidence_matches(
    bundle: ArtifactBundle, object_type: str, object_id: str,
) -> list[tuple[str, dict[str, Any]]]:
    lookup_type = "node" if object_type == "node_instance" else object_type
    lookup_id = object_id.split("#", 1)[0] if object_type == "node_instance" else object_id
    key = {
        "document": "document_id", "node": "node_id", "table": "table_id",
        "edge": "edge_id", "rule": "rule_id", "citation": "citation_id",
        "decision": "decision_id", "decision_option": "option_id",
        "routing_edge": "routing_id", "trigger": "trigger_id", "expectation": "expectation_id",
    }.get(lookup_type)
    if key is None:
        return []
    if lookup_type == "decision_option":
        compiled = [
            (bundle.graph.path.as_posix(), option)
            for decision in bundle.graph.objects("decisions")
            for option in decision.get("options", []) or []
            if isinstance(option, dict) and str(option.get(key)) == lookup_id
        ]
    else:
        plural = f"{lookup_type}s"
        if plural not in bundle.graph.objects_by_kind:
            compiled = []
        else:
            compiled = [
                (bundle.graph.path.as_posix(), item)
                for item in bundle.graph.objects(plural)
                if str(item.get(key)) == lookup_id
            ]
    if compiled:
        return compiled
    filename = f"{lookup_type}s.yaml"
    draft_matches: list[tuple[str, dict[str, Any]]] = []
    for directory, files in bundle.drafts.items():
        payload = files.get(filename, [])
        if not isinstance(payload, list):
            continue
        draft_matches.extend(
            (f"{directory}/{filename}", item)
            for item in payload
            if isinstance(item, dict) and str(item.get(key)) == lookup_id
        )
    return draft_matches


def serve(root: str | Path, year: str | int, *, port: int = 0) -> None:
    """Run the workbench on loopback with an ephemeral port by default."""
    from workbench.manifest import write_manifest

    root_path = Path(root).resolve()
    result = write_manifest(
        root_path,
        year,
        output_path=root_path / ".workbench_state" / str(year) / "review_manifest.json",
    )
    app = create_app(root_path, year, manifest=result.payload)
    print(f"write token: {app.config['WORKBENCH_WRITE_TOKEN']}", flush=True)
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
