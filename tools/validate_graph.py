#!/usr/bin/env python3
"""Validate the authored graph YAML for a tax year.

Two layers:
  1. JSON Schema validation of every object (schemas/*.schema.json).
  2. Graph-integrity cross-references (requirements doc §10.3): every edge
     source/target/rule, every node document, every citation_ref must resolve.

Usage:  python tools/validate_graph.py [tax_year]   (default 2025)
Deps:   pyyaml, jsonschema
"""
from __future__ import annotations
import sys, glob, json, pathlib, datetime

import yaml
try:
    import jsonschema
    HAVE_JSONSCHEMA = True
except ImportError:
    HAVE_JSONSCHEMA = False

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"

# dir -> (schema name, is the file a list of objects or a single object)
KINDS = {
    "documents": ("document", False),
    "nodes": ("node", True),
    "edges": ("edge", True),
    "rules": ("rule", True),
    "citations": ("citation", True),
    "decisions": ("decision", True),
}


def _normalize(x):
    """Tame YAML implicit typing: ISO dates parse to date objects, but our
    schemas expect strings. Normalize date/datetime -> ISO string at load time
    so authors never have to remember to quote them."""
    if isinstance(x, dict):
        return {k: _normalize(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_normalize(v) for v in x]
    if isinstance(x, (datetime.date, datetime.datetime)):
        return x.isoformat()
    return x


def load_kind(graph_dir: pathlib.Path, sub: str, is_list: bool):
    objs = []
    for f in sorted((graph_dir / sub).glob("*.yaml")):
        data = _normalize(yaml.safe_load(f.read_text(encoding="utf-8")))
        if data is None:
            continue
        objs.extend(data if is_list else [data])
    return objs


def main(year: str = "2025") -> int:
    graph_dir = ROOT / "graph" / year
    if not graph_dir.is_dir():
        print(f"no graph dir for {year}")
        return 1

    schemas = {
        name: json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))
        for name, _ in KINDS.values()
    }
    loaded = {sub: load_kind(graph_dir, sub, is_list) for sub, (_, is_list) in KINDS.items()}
    errors: list[str] = []

    # 1. schema validation
    if HAVE_JSONSCHEMA:
        for sub, (schema_name, _) in KINDS.items():
            for o in loaded[sub]:
                try:
                    jsonschema.validate(o, schemas[schema_name])
                except jsonschema.ValidationError as e:
                    errors.append(f"[schema/{sub}] {e.message} :: {json.dumps(o, default=str)[:120]}")

    # 2. cross-reference integrity
    doc_ids = {d["document_id"] for d in loaded["documents"]}
    node_ids = {n["node_id"] for n in loaded["nodes"]}
    rule_ids = {r["rule_id"] for r in loaded["rules"]}
    cite_ids = {c["citation_id"] for c in loaded["citations"]}

    for n in loaded["nodes"]:
        if n["document_id"] not in doc_ids:
            errors.append(f"node {n['node_id']} -> missing document {n['document_id']}")
        for c in n.get("citation_refs", []):
            if c not in cite_ids:
                errors.append(f"node {n['node_id']} -> missing citation {c}")
    for e in loaded["edges"]:
        if e["source"] not in node_ids:
            errors.append(f"edge {e['edge_id']} -> missing source {e['source']}")
        if e["target"] not in node_ids:
            errors.append(f"edge {e['edge_id']} -> missing target {e['target']}")
        if e.get("rule_id") and e["rule_id"] not in rule_ids:
            errors.append(f"edge {e['edge_id']} -> missing rule {e['rule_id']}")
        for c in e.get("citation_refs", []):
            if c not in cite_ids:
                errors.append(f"edge {e['edge_id']} -> missing citation {c}")
    for c in loaded["citations"]:
        if c["document_id"] not in doc_ids:
            errors.append(f"citation {c['citation_id']} -> missing document {c['document_id']}")
    for d in loaded["decisions"]:
        for c in d.get("citation_refs", []):
            if c not in cite_ids:
                errors.append(f"decision {d['decision_id']} -> missing citation {c}")

    counts = " ".join(f"{k}={len(v)}" for k, v in loaded.items())
    print(f"tax year {year}: {counts}")
    print("jsonschema:", "ON" if HAVE_JSONSCHEMA else "SKIPPED (not installed)")
    if errors:
        print(f"\n{len(errors)} INTEGRITY ERROR(S):")
        for e in errors:
            print("  -", e)
        return 1
    print("graph integrity OK — all references resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "2025"))
