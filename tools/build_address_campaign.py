"""Build or promote a deterministic canonical-address document campaign."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from tax_graph.addressing import CORE_RETURN_DOCUMENTS, build_address_campaign, write_candidate_registry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("document_ids", nargs="*", default=list(CORE_RETURN_DOCUMENTS))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    campaign = build_address_campaign(root, args.document_ids)
    for document_id, payload in campaign.items():
        write_candidate_registry(payload["registry"], root)
        if not args.promote:
            continue
        targets = {
            root / "graph/2025/addresses" / f"{document_id}.yaml": payload["registry"],
            root / "graph/2025/bindings/widgets" / f"{document_id}.yaml": payload["widget_bindings"],
            root / "graph/2025/bindings/nodes" / f"{document_id}.yaml": payload["node_bindings"],
            root / "graph/2025/references" / f"{document_id}.yaml": payload["references"],
        }
        for target, artifact in targets.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(yaml.safe_dump(artifact, sort_keys=False), encoding="utf-8")
        map_path = root / "graph/2025/field_maps" / f"{document_id}.yaml"
        field_map = yaml.safe_load(map_path.read_text(encoding="utf-8"))
        for group in (field_map.get("mappings", []), field_map.get("field_dispositions", [])):
            for item in group:
                address_id = payload["field_addresses"].get(item["field_name"])
                if address_id:
                    item["address_id"] = address_id
        map_path.write_text(yaml.safe_dump(field_map, sort_keys=False), encoding="utf-8")
    report = {document_id: payload["coverage"] for document_id, payload in campaign.items()}
    report_path = args.report or root / "workbench_output" / "m15r_core_address_campaign.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
