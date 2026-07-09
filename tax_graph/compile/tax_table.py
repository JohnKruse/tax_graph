"""Compile the 2025 under-$100k tax table from official bracket rules."""

from __future__ import annotations

import json
from pathlib import Path

from tax_graph.io.loader import load_graph

BRACKET_NODE_BY_STATUS = {
    "single": "form_1040_2025_brackets_single",
    "married_filing_jointly": "form_1040_2025_brackets_mfj",
    "married_filing_separately": "form_1040_2025_brackets_mfs",
    "head_of_household": "form_1040_2025_brackets_hoh",
    "qualifying_surviving_spouse": "form_1040_2025_brackets_qss",
}


def generate_tax_table_ranges() -> list[tuple[int, int]]:
    """Generate income ranges for the tax table under $100k."""
    ranges = []
    # 1. Under $25 split into $5 ranges
    for i in range(0, 25, 5):
        ranges.append((i, i + 5))
    # 2. $25 to $3,000 in $25 ranges
    for i in range(25, 3000, 25):
        ranges.append((i, i + 25))
    # 3. $3,000 to $100,000 in $50 ranges
    for i in range(3000, 100000, 50):
        ranges.append((i, i + 50))
    return ranges


def compute_tax_for_midpoint(midpoint: float, filing_status: str, brackets_by_status: dict[str, list[dict]]) -> int:
    """Compute progressive tax for a midpoint income and filing status."""
    tiers = brackets_by_status[filing_status]
    for tier in reversed(tiers):
        if midpoint >= tier["floor"]:
            tax_val = tier["cumulative"] + tier["rate"] * (midpoint - tier["floor"])
            # schoolbook rounding (0.5 rounds up)
            return int(tax_val + 0.5)
    return 0


def compile_tax_table(
    year: str = "2025",
    output_path: Path | None = None,
    *,
    root: Path | None = None,
) -> dict:
    """Compile the 2025 tax table to JSON format."""
    project_root = root if root is not None else Path(__file__).resolve().parents[2]
    brackets_by_status = load_brackets_from_graph(project_root, year)
    ranges = generate_tax_table_ranges()
    entries = []
    for r_min, r_max in ranges:
        midpoint = (r_min + r_max) / 2.0
        taxes = {}
        for status in BRACKET_NODE_BY_STATUS:
            taxes[status] = compute_tax_for_midpoint(midpoint, status, brackets_by_status)
        entries.append({
            "income_min": r_min,
            "income_max": r_max,
            "taxes": taxes
        })
    data = {
        "tax_year": int(year),
        "entries": entries
    }
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    return data


def load_brackets_from_graph(root: Path, year: str = "2025") -> dict[str, list[dict]]:
    """Read the ordinary bracket tables from the authored graph nodes."""
    graph = load_graph(year, root)
    nodes = {node["node_id"]: node for node in graph.items("nodes")}
    return {
        status: list(nodes[node_id]["constant_value"])
        for status, node_id in BRACKET_NODE_BY_STATUS.items()
    }


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    out_file = project_root / "graph" / "2025" / "tax_table.json"
    compile_tax_table("2025", out_file, root=project_root)
    print(f"Compiled tax table data resource to: {out_file}")
