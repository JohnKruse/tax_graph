"""Load, validate, resolve, and compile canonical form-address artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable
from urllib.parse import quote, unquote

import jsonschema
import yaml


KINDS = frozenset({"document", "part", "section", "line", "item", "box", "control", "option", "table", "row_template", "column", "worksheet_step"})
ROLE_KINDS = {
    "amount": frozenset({"control", "column"}), "text": frozenset({"control", "column"}),
    "description": frozenset({"control", "column"}), "checkbox": frozenset({"control", "option", "column"}),
    "radio": frozenset({"control", "option", "column"}), "choice": frozenset({"control", "option", "column"}),
    "date": frozenset({"control", "column"}), "identifier": frozenset({"control", "column"}),
    "signature": frozenset({"control"}), "attachment_indicator": frozenset({"control", "option"}),
    "other": frozenset({"control", "option", "column"}),
}


class AddressError(ValueError):
    """Raised when canonical address artifacts violate an invariant."""


@dataclass(frozen=True, order=True)
class AddressComponent:
    """One typed, escaped component in a canonical address path."""
    kind: str
    token: str


@dataclass(frozen=True)
class CanonicalAddress:
    """Validated canonical address record."""
    address_id: str
    logical_key: str
    year: int
    document_id: str
    parent_address_id: str | None
    kind: str
    path: tuple[AddressComponent, ...]
    official_ref: str | None
    control_role: str
    status: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class Resolution:
    """Exact, missing, or ambiguous address lookup result."""
    state: str
    matches: tuple[CanonicalAddress, ...]

    @property
    def address(self) -> CanonicalAddress | None:
        return self.matches[0] if self.state == "exact" else None


@dataclass(frozen=True)
class AddressArtifacts:
    """Validated registries and their separate binding/reference artifacts."""
    addresses: tuple[CanonicalAddress, ...]
    widget_bindings: tuple[dict[str, Any], ...] = ()
    node_bindings: tuple[dict[str, Any], ...] = ()
    references: tuple[dict[str, Any], ...] = ()

    def resolve(self, *, address_id: str | None = None, document_id: str | None = None,
                official_ref: str | None = None, control_role: str | None = None,
                alias: str | None = None) -> Resolution:
        """Resolve only exact structured/scoped queries; never choose a best match."""
        matches = list(self.addresses)
        if address_id is not None:
            matches = [item for item in matches if item.address_id == address_id]
        if document_id is not None:
            matches = [item for item in matches if item.document_id == document_id]
        if official_ref is not None:
            matches = [item for item in matches if item.official_ref == official_ref]
        if control_role is not None:
            matches = [item for item in matches if item.control_role == control_role]
        if alias is not None:
            matches = [item for item in matches if alias in item.raw.get("aliases", [])]
        ordered = tuple(sorted(matches, key=lambda item: item.address_id))
        return Resolution("missing" if not ordered else "exact" if len(ordered) == 1 else "ambiguous", ordered)


def serialize_address_id(year: int | None, components: Iterable[AddressComponent]) -> str:
    """Serialize typed components with stable percent escaping."""
    parts = []
    for component in components:
        if component.kind not in KINDS or not component.token:
            raise AddressError(f"invalid address component: {component!r}")
        parts.append(f"{component.kind}={quote(component.token, safe='._-')}")
    logical = "/".join(parts)
    if not logical:
        raise AddressError("address path cannot be empty")
    return f"{year}/{logical}" if year is not None else logical


def parse_address_id(value: str, *, year_scoped: bool = True) -> tuple[int | None, tuple[AddressComponent, ...]]:
    """Parse only canonical strings and prove byte-for-byte round-trip stability."""
    parts = value.split("/")
    year = None
    if year_scoped:
        try:
            year = int(parts.pop(0))
        except (ValueError, IndexError) as exc:
            raise AddressError(f"address lacks numeric year: {value}") from exc
    components = []
    for part in parts:
        if "=" not in part:
            raise AddressError(f"address component lacks kind: {part}")
        kind, encoded = part.split("=", 1)
        components.append(AddressComponent(kind, unquote(encoded)))
    result = tuple(components)
    if serialize_address_id(year if year_scoped else None, result) != value:
        raise AddressError(f"address is not in canonical serialized form: {value}")
    return year, result


def load_address_artifacts(year: str | int, root: str | Path) -> AddressArtifacts:
    """Load and validate committed YAML address artifacts for one year."""
    root_path = Path(root)
    graph = root_path / "graph" / str(year)
    addresses = []
    for path in sorted((graph / "addresses").glob("*.yaml")):
        payload = _load_and_schema(path, root_path / "schemas" / "address_registry.schema.json")
        _header(payload, int(year), path)
        for raw in payload["addresses"]:
            addresses.append(_address(raw, int(year), str(payload["document_id"])))
    widgets = _binding_files(graph / "bindings" / "widgets", "widget", root_path, int(year))
    nodes = _binding_files(graph / "bindings" / "nodes", "node", root_path, int(year))
    references = []
    for path in sorted((graph / "references").glob("*.yaml")):
        payload = _load_and_schema(path, root_path / "schemas" / "address_reference.schema.json")
        _header(payload, int(year), path)
        references.extend(payload["references"])
    artifacts = AddressArtifacts(tuple(addresses), tuple(widgets), tuple(nodes), tuple(references))
    _validate_artifacts(artifacts)
    return artifacts


def compile_address_artifacts(conn: sqlite3.Connection, artifacts: AddressArtifacts) -> None:
    """Create deterministic additive indexes in an existing graph database."""
    conn.executescript("""
    CREATE TABLE addresses (address_id TEXT PRIMARY KEY, logical_key TEXT NOT NULL, year INTEGER NOT NULL, document_id TEXT NOT NULL, parent_address_id TEXT, kind TEXT NOT NULL, official_ref TEXT, control_role TEXT NOT NULL, status TEXT NOT NULL, object_json TEXT NOT NULL);
    CREATE TABLE address_aliases (address_id TEXT NOT NULL, alias TEXT NOT NULL, PRIMARY KEY(address_id, alias), FOREIGN KEY(address_id) REFERENCES addresses(address_id));
    CREATE TABLE widget_bindings (document_id TEXT NOT NULL, field_name TEXT NOT NULL, address_id TEXT NOT NULL, object_json TEXT NOT NULL, PRIMARY KEY(document_id, field_name), FOREIGN KEY(address_id) REFERENCES addresses(address_id));
    CREATE TABLE node_bindings (document_id TEXT NOT NULL, node_id TEXT NOT NULL, address_id TEXT NOT NULL, role TEXT NOT NULL, object_json TEXT NOT NULL, PRIMARY KEY(document_id, node_id, address_id, role), FOREIGN KEY(address_id) REFERENCES addresses(address_id));
    CREATE TABLE address_references (reference_id TEXT PRIMARY KEY, source_address_id TEXT NOT NULL, resolved_address_id TEXT, object_json TEXT NOT NULL, FOREIGN KEY(source_address_id) REFERENCES addresses(address_id), FOREIGN KEY(resolved_address_id) REFERENCES addresses(address_id));
    """)
    for item in sorted(artifacts.addresses, key=lambda value: value.address_id):
        conn.execute("INSERT INTO addresses VALUES (?,?,?,?,?,?,?,?,?,?)", (item.address_id, item.logical_key, item.year, item.document_id, item.parent_address_id, item.kind, item.official_ref, item.control_role, item.status, _json(item.raw)))
        conn.executemany("INSERT INTO address_aliases VALUES (?,?)", [(item.address_id, alias) for alias in sorted(item.raw.get("aliases", []))])
    for item in sorted(artifacts.widget_bindings, key=lambda x: (x["document_id"], x["field_name"])):
        conn.execute("INSERT INTO widget_bindings VALUES (?,?,?,?)", (item["document_id"], item["field_name"], item["address_id"], _json(item)))
    for item in sorted(artifacts.node_bindings, key=lambda x: (x["document_id"], x["node_id"], x["address_id"], x["role"])):
        conn.execute("INSERT INTO node_bindings VALUES (?,?,?,?,?)", (item["document_id"], item["node_id"], item["address_id"], item["role"], _json(item)))
    for item in sorted(artifacts.references, key=lambda x: x["reference_id"]):
        conn.execute("INSERT INTO address_references VALUES (?,?,?,?)", (item["reference_id"], item["source_address_id"], item.get("resolved_address_id"), _json(item)))


def load_compiled_address_artifacts(db_path: str | Path) -> AddressArtifacts:
    """Read canonical address artifacts from compiled SQLite indexes."""
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT object_json FROM addresses ORDER BY address_id").fetchall()
        widgets = _json_rows(conn, "widget_bindings", "document_id, field_name")
        nodes = _json_rows(conn, "node_bindings", "document_id, node_id, address_id, role")
        refs = _json_rows(conn, "address_references", "reference_id")
    addresses = tuple(_address(json.loads(row[0]), int(json.loads(row[0])["year"]), str(json.loads(row[0])["document_id"])) for row in rows)
    artifacts = AddressArtifacts(addresses, tuple(widgets), tuple(nodes), tuple(refs))
    _validate_artifacts(artifacts)
    return artifacts


def _address(raw: dict[str, Any], year: int, document_id: str) -> CanonicalAddress:
    if int(raw["year"]) != year or raw["document_id"] != document_id:
        raise AddressError(f"address year/document mismatch: {raw['address_id']}")
    parsed_year, components = parse_address_id(raw["address_id"])
    logical_year, logical_components = parse_address_id(raw["logical_key"], year_scoped=False)
    del logical_year
    declared = tuple(AddressComponent(item["kind"], item["token"]) for item in raw["path"])
    if parsed_year != year or components != declared or logical_components != declared:
        raise AddressError(f"address path does not match identifiers: {raw['address_id']}")
    return CanonicalAddress(raw["address_id"], raw["logical_key"], year, document_id, raw["parent_address_id"], raw["kind"], components, raw.get("official_ref"), raw["control_role"], raw["status"], raw)


def _validate_artifacts(artifacts: AddressArtifacts) -> None:
    by_id = {item.address_id: item for item in artifacts.addresses}
    if len(by_id) != len(artifacts.addresses):
        raise AddressError("duplicate address_id")
    logical = {(item.year, item.logical_key) for item in artifacts.addresses}
    if len(logical) != len(artifacts.addresses):
        raise AddressError("duplicate logical_key within year")
    for item in artifacts.addresses:
        if item.kind != item.path[-1].kind:
            raise AddressError(f"terminal path kind mismatch: {item.address_id}")
        if item.control_role != "none" and item.kind not in ROLE_KINDS.get(item.control_role, frozenset()):
            raise AddressError(f"incompatible control role: {item.address_id}")
        if item.parent_address_id is not None:
            parent = by_id.get(item.parent_address_id)
            if parent is None or parent.document_id != item.document_id or item.path[:-1] != parent.path:
                raise AddressError(f"invalid parent: {item.address_id}")
        seen = set()
        cursor = item
        while cursor.parent_address_id is not None:
            if cursor.address_id in seen:
                raise AddressError(f"address parent cycle: {item.address_id}")
            seen.add(cursor.address_id)
            cursor = by_id[cursor.parent_address_id]
    for binding in (*artifacts.widget_bindings, *artifacts.node_bindings):
        target = by_id.get(binding["address_id"])
        if target is None or target.document_id != binding["document_id"]:
            raise AddressError(f"dangling or cross-document binding: {binding['address_id']}")
    for binding in artifacts.node_bindings:
        target = by_id[binding["address_id"]]
        expected_ref = binding.get("expected_official_ref")
        if expected_ref and target.official_ref != expected_ref:
            raise AddressError(f"node binding official reference mismatch: {binding['node_id']}")
        if binding.get("role") == "value" and target.control_role in {"checkbox", "radio", "choice", "signature", "attachment_indicator"}:
            raise AddressError(f"node value binding has incompatible control role: {binding['node_id']}")
    for ref in artifacts.references:
        if ref["source_address_id"] not in by_id:
            raise AddressError(f"dangling reference source: {ref['reference_id']}")
        resolved = ref.get("resolved_address_id")
        if resolved and resolved not in by_id:
            raise AddressError(f"dangling resolved reference: {ref['reference_id']}")
    aliases: dict[tuple[str, str], int] = {}
    for item in artifacts.addresses:
        for alias in item.raw.get("aliases", []):
            key = (item.document_id, alias)
            aliases[key] = aliases.get(key, 0) + 1
    if any(count > 1 for count in aliases.values()):
        raise AddressError("alias is ambiguous within document")


def _binding_files(directory: Path, kind: str, root: Path, year: int) -> list[dict[str, Any]]:
    result = []
    for path in sorted(directory.glob("*.yaml")):
        payload = _load_and_schema(path, root / "schemas" / "address_binding.schema.json")
        _header(payload, year, path)
        if payload["binding_kind"] != kind:
            raise AddressError(f"wrong binding kind in {path}")
        result.extend(dict(item, document_id=payload["document_id"]) for item in payload["bindings"])
    return result


def _header(payload: dict[str, Any], year: int, path: Path) -> None:
    if int(payload["year"]) != year:
        raise AddressError(f"artifact year mismatch: {path}")


def _load_and_schema(path: Path, schema_path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(payload)
    return payload


def _json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _json_rows(conn: sqlite3.Connection, table: str, order: str) -> list[dict[str, Any]]:
    return [json.loads(row[0]) for row in conn.execute(f"SELECT object_json FROM {table} ORDER BY {order}")]
