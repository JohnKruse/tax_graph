"""Local-only Flask server for the artifact review workbench."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import secrets
from typing import Any

from flask import Flask, jsonify

from workbench.artifacts import ArtifactBundle, load_artifact_bundle
from workbench.manifest import build_manifest
from workbench.preflight import preflight_manifest


def create_app(
    root: str | Path,
    year: str | int,
    *,
    write_token: str | None = None,
    manifest: dict[str, Any] | None = None,
    bundle: ArtifactBundle | None = None,
) -> Flask:
    """Create a preflighted, local review API application."""
    root_path = Path(root).resolve()
    artifact_bundle = bundle or load_artifact_bundle(root_path, year)
    review_manifest = manifest or build_manifest(root_path, year)
    coverage = preflight_manifest(review_manifest, artifact_bundle)

    app = Flask(__name__)
    app.config.update(
        WORKBENCH_ROOT=root_path,
        WORKBENCH_YEAR=int(year),
        WORKBENCH_WRITE_TOKEN=write_token or secrets.token_urlsafe(32),
        WORKBENCH_MANIFEST=review_manifest,
        WORKBENCH_BUNDLE=artifact_bundle,
        WORKBENCH_COVERAGE=coverage,
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

    return app


def serve(root: str | Path, year: str | int, *, port: int = 0) -> None:
    """Run the workbench on loopback with an ephemeral port by default."""
    app = create_app(root, year)
    print(f"write token: {app.config['WORKBENCH_WRITE_TOKEN']}", flush=True)
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
