"""Build the Form 1040 M15R Gate A candidate and focused review page."""

from __future__ import annotations

import argparse
from pathlib import Path

from tax_graph.addressing import build_form_1040_review, render_form_1040_review_html, write_candidate_registry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--promote", action="store_true", help="Write machine-valid pending-review artifacts to the live graph.")
    args = parser.parse_args()
    root = args.root.resolve()
    payload = build_form_1040_review(root)
    draft = write_candidate_registry(payload["registry"], root)
    output = args.output or root / "workbench_output" / "m15r_form_1040_address_review.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_form_1040_review_html(payload), encoding="utf-8")
    if args.promote:
        targets = {
            root / "graph/2025/addresses/form_1040_2025.yaml": payload["registry"],
            root / "graph/2025/bindings/widgets/form_1040_2025.yaml": payload["widget_bindings"],
            root / "graph/2025/bindings/nodes/form_1040_2025.yaml": payload["node_bindings"],
            root / "graph/2025/references/form_1040_2025.yaml": payload["references"],
        }
        for target, artifact in targets.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(__import__("yaml").safe_dump(artifact, sort_keys=False), encoding="utf-8")
        field_map_path = root / "graph/2025/field_maps/form_1040_2025.yaml"
        field_map = __import__("yaml").safe_load(field_map_path.read_text(encoding="utf-8"))
        by_field = {item["field_name"]: item["address_id"] for item in payload["controls"] if item["address_id"]}
        for group in (field_map.get("mappings", []), field_map.get("field_dispositions", [])):
            for item in group:
                if item["field_name"] in by_field:
                    item["address_id"] = by_field[item["field_name"]]
        field_map_path.write_text(__import__("yaml").safe_dump(field_map, sort_keys=False), encoding="utf-8")
    print(f"candidate: {draft}")
    print(f"review: {output}")
    print(f"coverage: {payload['coverage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
