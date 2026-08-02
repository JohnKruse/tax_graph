#!/usr/bin/env python3
"""Deterministic conversion: model expression tree -> the objects the graph stores.

Answers "what would actually land in the graph?" The graph has no nested
expressions. A tree is flattened into intermediate computed nodes plus edges
that carry rule_id and role, matching the live convention for Form 1040 line 15
(`..._pre_floor` node, subtract_currency edges, then max_currency edges).

Usage:
  python experiments/to_graph.py --form form_1040_2025 --lines 1z,11a,15,22,1e
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import yaml  # noqa: E402

from prompt_experiment import (  # noqa: E402
    build_prompt,
    expression_schema,
    render,
    rows_with_instruction_sections,
)
from tax_graph.extract.cells import expression_to_graph  # noqa: E402
from tax_graph.config import load_config  # noqa: E402
from tax_graph.extract.llm_client import build_llm_client  # noqa: E402

# operation -> the reusable rule already in graph/2025/rules/core.yaml
RULE_FOR_OP = {
    "SUM": "sum_currency",
    "SUBTRACT": "subtract_currency",
    "MULTIPLY": "multiply_currency",
    "NEGATE": "negate_currency",
    "MAX": "max_currency",
    "MIN": "min_currency",
    "COPY": "copy_currency_value",
}

ROLE_FOR_OP = {
    "SUM": ["addend"],
    "SUBTRACT": ["minuend", "subtrahend"],
    "MULTIPLY": ["factor"],
    "MAX": ["candidate"],
    "MIN": ["candidate"],
    "COPY": ["source"],
    "NEGATE": ["value"],
}


def role_for(op: str, index: int) -> str:
    roles = ROLE_FOR_OP.get(op, ["operand"])
    return roles[index] if index < len(roles) else roles[-1]


class Converter:
    """Compatibility facade over the pipeline's shared graph projection."""

    def __init__(self, doc: str, line: str, citation: str):
        self.doc = doc
        self.line = line
        self.base = f"{doc}_root_line_{line}"
        self.citation = citation
        self.nodes: list[dict] = []
        self.edges: list[dict] = []
        self.rules: list[dict] = []
        self.findings: list[str] = []

    def walk(self, node: dict, target: str) -> str:
        projection = expression_to_graph(
            form=self.doc,
            line=self.line,
            expression=node,
            quote_span_id=self.citation,
        )
        self.nodes = projection.nodes
        self.edges = projection.edges
        self.rules = projection.rules
        self.findings = projection.findings
        return target


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--form", required=True)
    p.add_argument("--lines", required=True)
    p.add_argument("--year", default="2025")
    p.add_argument("--model", default=None)
    args = p.parse_args()

    data = json.loads((ROOT / "experiments" / "data" / f"lines_{args.year}.json").read_text(encoding="utf-8"))
    entry = data["forms"][args.form]
    wanted = [x.strip().lower() for x in args.lines.split(",") if x.strip()]
    rows = rows_with_instruction_sections(
        args.form,
        entry,
        entry["lines"],
        year=str(args.year),
    )
    rows = [r for r in rows if r["line"] in wanted]

    settings = load_config(root=str(ROOT))
    client = build_llm_client(settings)
    model = args.model or str(settings.get("llm", {}).get("model") or "google/gemini-3.6-flash")
    schema = expression_schema(data["operations"])

    for row in rows:
        res = client.structured_completion(
            prompt=build_prompt(args.form, row, hints=True, mode="expr"),
            schema=schema,
            model=model,
            max_tokens=4000,
            temperature=None,
            purpose="experiment_to_graph",
        )
        payload = getattr(res, "payload", res)
        tree = payload["expression"]

        print("=" * 78)
        print(f"{args.form}  line {row['line']}")
        print(f"  label   : {row['label'][:90]}")
        print(f"  model   : {render(tree)}")
        print(f"  raw tree: {json.dumps(tree)}")
        print("-" * 78)

        conv = Converter(args.form, row["line"], "cite_span_PLACEHOLDER")
        conv.walk(tree, conv.base)
        out = {}
        if conv.nodes:
            out["nodes (new)"] = conv.nodes
        out["edges"] = conv.edges
        print(yaml.safe_dump(out, sort_keys=False, width=100).rstrip())
        if conv.findings:
            print("FINDINGS:")
            for f in conv.findings:
                print(f"  - {f}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
