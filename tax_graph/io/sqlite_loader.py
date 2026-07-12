"""Load compiled SQLite graph artifacts behind the standard graph interface."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any

from tax_graph.config import get_config_value, load_config, project_root
from tax_graph.io.loader import GRAPH_KINDS, LoadedGraph, graph_content_hash


def compiled_db_path(year: str | int = "2025", root: str | Path | None = None) -> Path:
    """Return the configured compiled SQLite path for one tax year."""
    root_path = Path(root).resolve() if root is not None else project_root()
    settings = load_config(root=root_path)
    build_dir = Path(get_config_value(settings, "project.paths.build_dir", "build"))
    output_dir = build_dir if build_dir.is_absolute() else root_path / build_dir
    return output_dir / f"tax_graph_{year}.sqlite"


def load_sqlite_graph(
    year: str | int = "2025",
    root: str | Path | None = None,
    db_path: str | Path | None = None,
) -> LoadedGraph:
    """Load a compiled SQLite graph artifact as ``LoadedGraph``."""
    graph_year = str(year)
    root_path = Path(root).resolve() if root is not None else project_root()
    sqlite_path = Path(db_path).resolve() if db_path is not None else compiled_db_path(graph_year, root_path)
    if not sqlite_path.exists():
        raise FileNotFoundError(f"compiled graph not found: {sqlite_path}")

    with sqlite3.connect(sqlite_path) as conn:
        stored_year = conn.execute("SELECT value FROM metadata WHERE key = 'tax_year'").fetchone()
        if stored_year is None or str(stored_year[0]) != graph_year:
            raise ValueError(f"compiled graph {sqlite_path} is not for tax year {graph_year}")
        stored_hash = conn.execute("SELECT value FROM metadata WHERE key = 'content_hash'").fetchone()
        if stored_hash is None or not stored_hash[0]:
            raise ValueError(f"compiled graph {sqlite_path} has no content hash")
        source_dir = root_path / "graph" / graph_year
        actual_hash = graph_content_hash(source_dir)
        if str(stored_hash[0]) != actual_hash:
            raise ValueError(
                f"compiled graph {sqlite_path} content hash mismatch: "
                f"stamped {stored_hash[0]}, actual {actual_hash}"
            )
        objects = {kind: _load_kind(conn, kind) for kind in GRAPH_KINDS}
    return LoadedGraph(
        year=graph_year,
        root=root_path,
        graph_dir=root_path / "graph" / graph_year,
        objects=objects,
        base_content_hash=str(stored_hash[0]),
    )


def _load_kind(conn: sqlite3.Connection, kind: str) -> list[dict[str, Any]]:
    id_field = GRAPH_KINDS[kind][2]
    try:
        rows = conn.execute(f"SELECT object_json FROM {kind} ORDER BY {id_field}").fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower():
            return []
        raise
    return [json.loads(row[0]) for row in rows]
