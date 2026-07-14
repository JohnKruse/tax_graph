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


def create_app(
    root: str | Path,
    year: str | int,
    *,
    write_token: str | None = None,
    manifest: dict[str, Any] | None = None,
    bundle: ArtifactBundle | None = None,
    page_renderer: PageRenderer | None = None,
    cache_dir: str | Path | None = None,
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

    app = Flask(__name__)
    app.config.update(
        WORKBENCH_ROOT=root_path,
        WORKBENCH_YEAR=int(year),
        WORKBENCH_WRITE_TOKEN=write_token or secrets.token_urlsafe(32),
        WORKBENCH_MANIFEST=review_manifest,
        WORKBENCH_BUNDLE=artifact_bundle,
        WORKBENCH_COVERAGE=coverage,
        WORKBENCH_PAGE_CACHE=page_cache,
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

    return app


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
