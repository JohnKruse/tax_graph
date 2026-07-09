"""Compile the 2025 under-$100k tax table from official bracket rules."""

from __future__ import annotations

import json
from pathlib import Path


BRACKETS_2025 = {
    "single": [
        {"rate": 0.10, "floor": 0, "cumulative": 0},
        {"rate": 0.12, "floor": 11925, "cumulative": 1192.50},
        {"rate": 0.22, "floor": 48475, "cumulative": 5578.50},
        {"rate": 0.24, "floor": 103350, "cumulative": 17651.00},
        {"rate": 0.32, "floor": 197300, "cumulative": 40199.00},
        {"rate": 0.35, "floor": 250525, "cumulative": 57231.00},
        {"rate": 0.37, "floor": 626350, "cumulative": 188769.75},
    ],
    "married_filing_jointly": [
        {"rate": 0.10, "floor": 0, "cumulative": 0},
        {"rate": 0.12, "floor": 23850, "cumulative": 2385.00},
        {"rate": 0.22, "floor": 96950, "cumulative": 11157.00},
        {"rate": 0.24, "floor": 206700, "cumulative": 35302.00},
        {"rate": 0.32, "floor": 394600, "cumulative": 80398.00},
        {"rate": 0.35, "floor": 501050, "cumulative": 114462.00},
        {"rate": 0.37, "floor": 751600, "cumulative": 202154.50},
    ],
    "married_filing_separately": [
        {"rate": 0.10, "floor": 0, "cumulative": 0},
        {"rate": 0.12, "floor": 11925, "cumulative": 1192.50},
        {"rate": 0.22, "floor": 48475, "cumulative": 5578.50},
        {"rate": 0.24, "floor": 103350, "cumulative": 17651.00},
        {"rate": 0.32, "floor": 197300, "cumulative": 40199.00},
        {"rate": 0.35, "floor": 250525, "cumulative": 57231.00},
        {"rate": 0.37, "floor": 375800, "cumulative": 101077.25},
    ],
    "head_of_household": [
        {"rate": 0.10, "floor": 0, "cumulative": 0},
        {"rate": 0.12, "floor": 17000, "cumulative": 1700.00},
        {"rate": 0.22, "floor": 64850, "cumulative": 7442.00},
        {"rate": 0.24, "floor": 103350, "cumulative": 15912.00},
        {"rate": 0.32, "floor": 197300, "cumulative": 38460.00},
        {"rate": 0.35, "floor": 250500, "cumulative": 55484.00},
        {"rate": 0.37, "floor": 626350, "cumulative": 187031.50},
    ],
    "qualifying_surviving_spouse": [
        {"rate": 0.10, "floor": 0, "cumulative": 0},
        {"rate": 0.12, "floor": 23850, "cumulative": 2385.00},
        {"rate": 0.22, "floor": 96950, "cumulative": 11157.00},
        {"rate": 0.24, "floor": 206700, "cumulative": 35302.00},
        {"rate": 0.32, "floor": 394600, "cumulative": 80398.00},
        {"rate": 0.35, "floor": 501050, "cumulative": 114462.00},
        {"rate": 0.37, "floor": 751600, "cumulative": 202154.50},
    ],
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


def compute_tax_for_midpoint(midpoint: float, filing_status: str) -> int:
    """Compute progressive tax for a midpoint income and filing status."""
    tiers = BRACKETS_2025[filing_status]
    for tier in reversed(tiers):
        if midpoint >= tier["floor"]:
            tax_val = tier["cumulative"] + tier["rate"] * (midpoint - tier["floor"])
            # schoolbook rounding (0.5 rounds up)
            return int(tax_val + 0.5)
    return 0


def compile_tax_table(year: str = "2025", output_path: Path | None = None) -> dict:
    """Compile the 2025 tax table to JSON format."""
    ranges = generate_tax_table_ranges()
    entries = []
    for r_min, r_max in ranges:
        midpoint = (r_min + r_max) / 2.0
        taxes = {}
        for status in BRACKETS_2025:
            taxes[status] = compute_tax_for_midpoint(midpoint, status)
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


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    out_file = project_root / "graph" / "2025" / "tax_table.json"
    compile_tax_table("2025", out_file)
    print(f"Compiled tax table data resource to: {out_file}")
