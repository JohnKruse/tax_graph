"""Explicit legacy-address migration diagnostics; never a production fallback."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

import yaml

from tax_graph.addressing.registry import AddressArtifacts


@dataclass(frozen=True)
class MigrationCandidate:
    """One legacy identity claim presented to canonical resolution."""
    source_id: str
    document_id: str
    official_ref: str | None = None
    control_role: str | None = None
    alias: str | None = None
    evidence_complete: bool = True


def migration_report(candidates: Iterable[MigrationCandidate], artifacts: AddressArtifacts) -> dict[str, Any]:
    """Return a byte-stable exact/provisional/ambiguous/unresolved report."""
    rows = []
    for item in sorted(candidates, key=lambda value: value.source_id):
        result = artifacts.resolve(document_id=item.document_id, official_ref=item.official_ref,
                                   control_role=item.control_role, alias=item.alias)
        state = result.state
        if state == "missing":
            state = "unresolved"
        elif state == "exact" and not item.evidence_complete:
            state = "provisional"
        rows.append({
            "source_id": item.source_id, "state": state,
            "candidate_address_ids": [match.address_id for match in result.matches],
            "query": {"document_id": item.document_id, "official_ref": item.official_ref,
                      "control_role": item.control_role, "alias": item.alias},
        })
    payload = {"schema_version": 1, "results": rows}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
    payload["report_hash"] = hashlib.sha256(canonical).hexdigest()
    return payload


def semantic_join_inventory(root: str | Path) -> tuple[dict[str, str], ...]:
    """Verify the pinned legacy semantic-join inventory and reject new join sites."""
    root_path = Path(root)
    manifest = yaml.safe_load((root_path / "docs" / "legacy-semantic-joins.yaml").read_text(encoding="utf-8"))
    declared = {item["path"]: item for item in manifest["joins"]}
    signatures = {
        "workbench/semantics.py": r"def _line_number\(",
        "tax_graph/validate/graph_validator.py": r"re\.search\(r\"_line_",
        "tax_graph/verify/completeness.py": r"def _node_mentions_line\(",
        "tax_graph/extract/tables.py": r"ROW_COLUMN_RE\.search\(node_id\)",
    }
    if set(declared) != set(signatures):
        raise ValueError("legacy semantic-join manifest does not match the enforced inventory")
    result = []
    for relative, signature in sorted(signatures.items()):
        text = (root_path / relative).read_text(encoding="utf-8")
        if not re.search(signature, text):
            raise ValueError(f"declared semantic join signature is missing: {relative}")
        result.append({"path": relative, "category": declared[relative]["category"], "disposition": declared[relative]["disposition"]})
    return tuple(result)
