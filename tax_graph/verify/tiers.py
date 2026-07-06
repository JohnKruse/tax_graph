"""Trust-tier assignment for extraction drafts (design: docs/extraction-verification.md).

Tiers are deterministic functions of check outcomes - never of self-reported
confidence scores (confidence is telemetry only):

- T0: the object carries review flags (exception queue).
- T1: structural layers clean (deterministic checks + critic).
- T2: T1 plus cross-vendor N-version agreement.
- T3: T2 plus property checks pass and an executed example/differential covers
  a node the object references.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from tax_graph.extract.models import DraftObject


@dataclass(frozen=True)
class TierInputs:
    """Optional higher-layer evidence available at routing time.

    ``None`` means the layer has not run; the tier simply caps below the level
    that layer would unlock (it is never treated as a failure).
    """

    nversion_agreed: frozenset[tuple[str, str]] | None = None
    properties_ok: bool | None = None
    covered_nodes: frozenset[str] | None = None


def assign_tier(obj: DraftObject, inputs: TierInputs | None = None) -> str:
    """Assign a deterministic trust tier to one draft object."""
    if obj.flags:
        return "T0"
    evidence = inputs or TierInputs()
    if evidence.nversion_agreed is None or (obj.kind, obj.object_id) not in evidence.nversion_agreed:
        return "T1"
    if not evidence.properties_ok:
        return "T2"
    if evidence.covered_nodes and referenced_node_ids(obj) & evidence.covered_nodes:
        return "T3"
    return "T2"


def referenced_node_ids(obj: DraftObject) -> set[str]:
    """Collect every string value in the object payload (node-id candidates)."""
    found: set[str] = set()
    _collect_strings(obj.data, found)
    return found


def tier_distribution(objects: list[DraftObject]) -> dict[str, int]:
    """Count objects per assigned tier (unassigned objects count as T0)."""
    counts = {"T0": 0, "T1": 0, "T2": 0, "T3": 0}
    for obj in objects:
        counts[obj.tier or "T0"] += 1
    return counts


def collect_covered_nodes(root: str | Path) -> frozenset[str]:
    """Collect node ids exercised by frozen example/corpus expected values.

    Scans ``examples/**/expected.yaml``; both the flat mapping shape and the
    ``expected:`` wrapper shape contribute their node-id keys.
    """
    examples_dir = Path(root) / "examples"
    covered: set[str] = set()
    if not examples_dir.is_dir():
        return frozenset()
    for expected_path in sorted(examples_dir.rglob("expected.yaml")):
        payload = yaml.safe_load(expected_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        mapping = payload.get("expected") if isinstance(payload.get("expected"), dict) else payload
        covered.update(str(key) for key in mapping.keys() if isinstance(key, str))
    return frozenset(covered)


def _collect_strings(value: Any, found: set[str]) -> None:
    if isinstance(value, str):
        found.add(value)
    elif isinstance(value, dict):
        for item in value.values():
            _collect_strings(item, found)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _collect_strings(item, found)
