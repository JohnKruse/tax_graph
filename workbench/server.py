"""Local-only Flask server for the artifact review workbench."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import secrets
from typing import Any

from flask import Flask, jsonify, request, send_file

from workbench.artifacts import ArtifactBundle, load_artifact_bundle
from workbench.manifest import build_manifest
from workbench.preflight import preflight_manifest
from workbench.render import PageImageCache, PageRenderError, PageRenderer
from workbench.schema import SchemaValidationError, validate_session_state
from workbench.sessions import default_session, load_session, save_session
from workbench.verdicts import emit_verdict


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
    )
    entries = {
        str(entry["queue_id"]): entry
        for entry in review_manifest.get("entries", [])
        if isinstance(entry, dict) and entry.get("queue_id")
    }

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
        return jsonify(payload or default_session(int(year), queue_id, entry.get("units", [])))

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
        if payload.get("queue_id") != queue_id or payload.get("tax_year") != int(year):
            return jsonify({"error": "session queue_id and tax_year must match the request"}), 400
        unit_ids = {str(unit.get("unit_id")) for unit in entry.get("units", []) or []}
        referenced = set(str(value) for value in payload.get("visited_unit_ids", []) or [])
        if payload.get("current_unit_id") is not None:
            referenced.add(str(payload["current_unit_id"]))
        selection = payload.get("selection")
        if isinstance(selection, dict) and selection.get("unit_id") is not None:
            referenced.add(str(selection["unit_id"]))
        unknown = sorted(referenced - unit_ids)
        if unknown:
            return jsonify({"error": "session references units outside the queue entry", "unit_ids": unknown}), 400
        try:
            validate_session_state(payload)
            save_session(session_root / f"{queue_id}.json", payload)
        except (ValueError, SchemaValidationError) as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(payload)

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
            "reviewed_at", "reason", "object_ref", "source_override",
        }
        unexpected = sorted(set(payload) - allowed)
        if unexpected:
            return jsonify({"error": "unexpected verdict fields", "fields": unexpected}), 400
        queue_id = str(payload.get("queue_id", ""))
        if queue_id not in entries:
            return jsonify({"error": "unknown queue_id", "queue_id": queue_id}), 404
        required = ("verdict_id", "reviewer_id", "human_minutes", "verdict")
        missing = [key for key in required if payload.get(key) is None]
        if missing:
            return jsonify({"error": "missing verdict fields", "fields": missing}), 400
        try:
            result = emit_verdict(
                root=root_path,
                year=year,
                queue_id=queue_id,
                verdict_id=str(payload["verdict_id"]),
                reviewer_id=str(payload["reviewer_id"]),
                human_minutes=float(payload["human_minutes"]),
                verdict=str(payload["verdict"]),
                reviewed_at=payload.get("reviewed_at"),
                reason=payload.get("reason"),
                object_ref=payload.get("object_ref"),
                source_override=payload.get("source_override"),
                output_path=verdict_root / f"{payload['verdict_id']}.yaml",
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
    app = create_app(root, year)
    print(f"write token: {app.config['WORKBENCH_WRITE_TOKEN']}", flush=True)
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
