"""Compile authored YAML graph objects into a deterministic SQLite artifact."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any

from tax_graph.config import get_config_value, load_config, project_root
from tax_graph.io.loader import GRAPH_KINDS, LoadedGraph, load_graph


DB_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class BuildResult:
    """SQLite artifact emitted for one tax year."""

    year: str
    path: Path
    counts: dict[str, int]


def build_sqlite(
    year: str | int = "2025",
    *,
    root: str | Path | None = None,
    build_dir: str | Path | None = None,
) -> BuildResult:
    """Build ``tax_graph_<year>.sqlite`` from authored YAML graph data."""
    root_path = Path(root).resolve() if root is not None else project_root()
    settings = load_config(root=root_path)
    graph = load_graph(year, root_path)
    output_dir = _build_dir(root_path, settings, build_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / f"tax_graph_{graph.year}.sqlite"
    temp_path = db_path.with_suffix(".sqlite.tmp")
    if temp_path.exists():
        temp_path.unlink()

    conn = sqlite3.connect(temp_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        _create_schema(conn)
        _insert_graph(conn, graph)
        conn.commit()
    finally:
        conn.close()

    if db_path.exists():
        db_path.unlink()
    temp_path.replace(db_path)
    return BuildResult(year=graph.year, path=db_path, counts=graph.counts())


def _build_dir(root: Path, config: dict[str, Any], build_dir: str | Path | None) -> Path:
    if build_dir is not None:
        candidate = Path(build_dir)
    else:
        candidate = Path(get_config_value(config, "project.paths.build_dir", "build"))
    return candidate if candidate.is_absolute() else root / candidate


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY,
            tax_year INTEGER,
            kind TEXT,
            title TEXT,
            object_json TEXT NOT NULL
        );

        CREATE TABLE nodes (
            node_id TEXT PRIMARY KEY,
            document_id TEXT,
            label TEXT,
            node_type TEXT,
            value_type TEXT,
            required TEXT,
            object_json TEXT NOT NULL
        );

        CREATE TABLE tables (
            table_id TEXT PRIMARY KEY,
            document_id TEXT,
            line_anchor TEXT,
            object_json TEXT NOT NULL
        );

        CREATE TABLE edges (
            edge_id TEXT PRIMARY KEY,
            source TEXT,
            target TEXT,
            rule_id TEXT,
            role TEXT,
            object_json TEXT NOT NULL
        );

        CREATE TABLE rules (
            rule_id TEXT PRIMARY KEY,
            operation TEXT,
            target_node_id TEXT,
            object_json TEXT NOT NULL
        );

        CREATE TABLE citations (
            citation_id TEXT PRIMARY KEY,
            document_id TEXT,
            locator TEXT,
            quoted_text TEXT,
            url TEXT,
            object_json TEXT NOT NULL
        );

        CREATE TABLE decisions (
            decision_id TEXT PRIMARY KEY,
            node_id TEXT,
            prompt TEXT,
            object_json TEXT NOT NULL
        );

        CREATE TABLE tax_table (
            income_min INTEGER,
            income_max INTEGER,
            single INTEGER,
            married_filing_jointly INTEGER,
            married_filing_separately INTEGER,
            head_of_household INTEGER,
            qualifying_surviving_spouse INTEGER,
            PRIMARY KEY (income_min, income_max)
        );

        CREATE VIRTUAL TABLE graph_fts USING fts5(
            kind UNINDEXED,
            object_id UNINDEXED,
            title,
            body
        );
        """
    )


def _insert_graph(conn: sqlite3.Connection, graph: LoadedGraph) -> None:
    conn.executemany(
        "INSERT INTO metadata(key, value) VALUES (?, ?)",
        [
            ("schema_version", str(DB_SCHEMA_VERSION)),
            ("tax_year", graph.year),
        ],
    )
    _insert_documents(conn, graph.items("documents"))
    _insert_nodes(conn, graph.items("nodes"))
    _insert_tables(conn, graph.items("tables"))
    _insert_edges(conn, graph.items("edges"))
    _insert_rules(conn, graph.items("rules"))
    _insert_citations(conn, graph.items("citations"))
    _insert_decisions(conn, graph.items("decisions"))
    _insert_tax_table(conn, graph.graph_dir)
    _insert_fts(conn, graph)


def _insert_documents(conn: sqlite3.Connection, objects: list[dict[str, Any]]) -> None:
    rows = [
        (
            obj.get("document_id"),
            obj.get("tax_year"),
            obj.get("kind"),
            obj.get("title"),
            _json(obj),
        )
        for obj in _stable_objects("documents", objects)
    ]
    conn.executemany(
        "INSERT INTO documents(document_id, tax_year, kind, title, object_json) VALUES (?, ?, ?, ?, ?)",
        rows,
    )


def _insert_nodes(conn: sqlite3.Connection, objects: list[dict[str, Any]]) -> None:
    rows = [
        (
            obj.get("node_id"),
            obj.get("document_id"),
            obj.get("label"),
            obj.get("node_type"),
            obj.get("value_type"),
            obj.get("required"),
            _json(obj),
        )
        for obj in _stable_objects("nodes", objects)
    ]
    conn.executemany(
        """
        INSERT INTO nodes(node_id, document_id, label, node_type, value_type, required, object_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_tables(conn: sqlite3.Connection, objects: list[dict[str, Any]]) -> None:
    rows = [
        (
            obj.get("table_id"),
            obj.get("document_id"),
            obj.get("line_anchor"),
            _json(obj),
        )
        for obj in _stable_objects("tables", objects)
    ]
    conn.executemany(
        "INSERT INTO tables(table_id, document_id, line_anchor, object_json) VALUES (?, ?, ?, ?)",
        rows,
    )


def _insert_edges(conn: sqlite3.Connection, objects: list[dict[str, Any]]) -> None:
    rows = [
        (
            obj.get("edge_id"),
            obj.get("source"),
            obj.get("target"),
            obj.get("rule_id"),
            obj.get("role"),
            _json(obj),
        )
        for obj in _stable_objects("edges", objects)
    ]
    conn.executemany(
        "INSERT INTO edges(edge_id, source, target, rule_id, role, object_json) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )


def _insert_rules(conn: sqlite3.Connection, objects: list[dict[str, Any]]) -> None:
    rows = [
        (
            obj.get("rule_id"),
            obj.get("operation"),
            obj.get("target_node_id"),
            _json(obj),
        )
        for obj in _stable_objects("rules", objects)
    ]
    conn.executemany(
        "INSERT INTO rules(rule_id, operation, target_node_id, object_json) VALUES (?, ?, ?, ?)",
        rows,
    )


def _insert_citations(conn: sqlite3.Connection, objects: list[dict[str, Any]]) -> None:
    rows = [
        (
            obj.get("citation_id"),
            obj.get("document_id"),
            obj.get("locator"),
            obj.get("quoted_text"),
            obj.get("url"),
            _json(obj),
        )
        for obj in _stable_objects("citations", objects)
    ]
    conn.executemany(
        """
        INSERT INTO citations(citation_id, document_id, locator, quoted_text, url, object_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_decisions(conn: sqlite3.Connection, objects: list[dict[str, Any]]) -> None:
    rows = [
        (
            obj.get("decision_id"),
            obj.get("node_id"),
            obj.get("prompt"),
            _json(obj),
        )
        for obj in _stable_objects("decisions", objects)
    ]
    conn.executemany(
        "INSERT INTO decisions(decision_id, node_id, prompt, object_json) VALUES (?, ?, ?, ?)",
        rows,
    )


def _insert_fts(conn: sqlite3.Connection, graph: LoadedGraph) -> None:
    rows: list[tuple[str, str, str, str]] = []
    for node in _stable_objects("nodes", graph.items("nodes")):
        rows.append(
            (
                "nodes",
                str(node.get("node_id", "")),
                str(node.get("label", "")),
                " ".join(str(node.get(key, "")) for key in ("node_id", "label", "description")),
            )
        )
    for citation in _stable_objects("citations", graph.items("citations")):
        rows.append(
            (
                "citations",
                str(citation.get("citation_id", "")),
                str(citation.get("locator", "")),
                str(citation.get("quoted_text", "")),
            )
        )
    conn.executemany(
        "INSERT INTO graph_fts(kind, object_id, title, body) VALUES (?, ?, ?, ?)",
        rows,
    )


def _stable_objects(kind: str, objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    id_field = GRAPH_KINDS[kind][2]
    return sorted(objects, key=lambda obj: str(obj.get(id_field, "")))


def _json(obj: dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _insert_tax_table(conn: sqlite3.Connection, graph_dir: Path) -> None:
    path = graph_dir / "tax_table.json"
    if not path.exists():
        return
    import json
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for entry in data.get("entries", []):
        taxes = entry["taxes"]
        rows.append((
            entry["income_min"],
            entry["income_max"],
            taxes["single"],
            taxes["married_filing_jointly"],
            taxes["married_filing_separately"],
            taxes["head_of_household"],
            taxes["qualifying_surviving_spouse"],
        ))
    conn.executemany(
        """
        INSERT INTO tax_table(
            income_min, income_max, single, married_filing_jointly,
            married_filing_separately, head_of_household, qualifying_surviving_spouse
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

