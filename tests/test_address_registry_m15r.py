from __future__ import annotations

import copy
import json
from pathlib import Path
import sqlite3

import pytest
import yaml

from tax_graph.addressing import (
    AddressComponent, AddressError, compile_address_artifacts,
    load_address_artifacts, load_compiled_address_artifacts,
    parse_address_id, serialize_address_id,
)


ROOT = Path(__file__).resolve().parents[1]
HASH = "a" * 64


def _record(path, *, kind, parent, role="none", aliases=None, official_ref=None):
    address_id = serialize_address_id(2025, path)
    result = {
        "address_id": address_id, "logical_key": serialize_address_id(None, path),
        "year": 2025, "document_id": "form_test_2025", "parent_address_id": parent,
        "kind": kind, "path": [{"kind": item.kind, "token": item.token} for item in path],
        "printed_label": official_ref or kind, "aliases": aliases or [], "control_role": role,
        "status": "pending_review", "evidence": [{"source_path": "raw/test.pdf", "source_hash": HASH}],
    }
    if official_ref:
        result["official_ref"] = official_ref
    return result


def _root(tmp_path: Path) -> tuple[Path, list[dict]]:
    (tmp_path / "schemas").mkdir()
    for name in ("address_registry.schema.json", "address_binding.schema.json", "address_reference.schema.json"):
        (tmp_path / "schemas" / name).write_text((ROOT / "schemas" / name).read_text(encoding="utf-8"), encoding="utf-8")
    base = (AddressComponent("document", "form_test"),)
    document = _record(base, kind="document", parent=None)
    line_path = base + (AddressComponent("line", "1"),)
    line = _record(line_path, kind="line", parent=document["address_id"], official_ref="1")
    control_path = line_path + (AddressComponent("control", "amount"),)
    control = _record(control_path, kind="control", parent=line["address_id"], role="amount", aliases=["total"], official_ref="1")
    records = [document, line, control]
    address_dir = tmp_path / "graph" / "2025" / "addresses"
    address_dir.mkdir(parents=True)
    (address_dir / "form_test_2025.yaml").write_text(yaml.safe_dump({"schema_version": 1, "year": 2025, "document_id": "form_test_2025", "addresses": records}, sort_keys=False), encoding="utf-8")
    return tmp_path, records


@pytest.mark.m15r
def test_serializer_escapes_and_round_trips() -> None:
    components = (AddressComponent("document", "form/x"), AddressComponent("line", "1 a"))
    value = serialize_address_id(2025, components)
    assert value == "2025/document=form%2Fx/line=1%20a"
    assert parse_address_id(value) == (2025, components)
    with pytest.raises(AddressError, match="canonical"):
        parse_address_id("2025/document=form%2fx")


@pytest.mark.m15r
def test_load_resolve_compile_and_sqlite_parity(tmp_path: Path) -> None:
    root, records = _root(tmp_path)
    node_dir = root / "graph" / "2025" / "bindings" / "nodes"
    node_dir.mkdir(parents=True)
    node_dir.joinpath("form_test_2025.yaml").write_text(yaml.safe_dump({"schema_version": 1, "year": 2025, "document_id": "form_test_2025", "binding_kind": "node", "bindings": [{"node_id": "form_test_2025_line_1", "address_id": records[-1]["address_id"], "role": "value", "status": "exact"}]}, sort_keys=False), encoding="utf-8")
    artifacts = load_address_artifacts(2025, root)
    assert artifacts.resolve(document_id="form_test_2025", official_ref="1", control_role="amount").address.address_id == records[-1]["address_id"]
    assert artifacts.resolve(document_id="form_test_2025", official_ref="1").state == "ambiguous"
    assert artifacts.resolve(alias="missing").state == "missing"
    db = tmp_path / "addresses.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        compile_address_artifacts(conn, artifacts)
    compiled = load_compiled_address_artifacts(db)
    assert compiled == artifacts


@pytest.mark.m15r
@pytest.mark.parametrize("defect", ["duplicate", "cycle", "path", "alias", "role"])
def test_validator_fails_closed_on_registry_defects(tmp_path: Path, defect: str) -> None:
    root, records = _root(tmp_path)
    payload = {"schema_version": 1, "year": 2025, "document_id": "form_test_2025", "addresses": records}
    if defect == "duplicate": payload["addresses"].append(copy.deepcopy(records[-1]))
    elif defect == "cycle": records[0]["parent_address_id"] = records[-1]["address_id"]
    elif defect == "path": records[-1]["logical_key"] += "/item=x"
    elif defect == "alias": records[1]["aliases"] = ["total"]
    elif defect == "role": records[-1]["kind"] = "line"; records[-1]["path"][-1]["kind"] = "line"; records[-1]["address_id"] = records[-1]["address_id"].replace("control=", "line="); records[-1]["logical_key"] = records[-1]["logical_key"].replace("control=", "line=")
    path = root / "graph" / "2025" / "addresses" / "form_test_2025.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    with pytest.raises((AddressError, Exception)):
        load_address_artifacts(2025, root)
