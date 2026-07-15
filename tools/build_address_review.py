"""Build the Form 1040 M15R Gate A candidate and focused review page."""

from __future__ import annotations

import argparse
from pathlib import Path

from tax_graph.addressing import build_form_1040_review, render_form_1040_review_html, write_candidate_registry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    payload = build_form_1040_review(root)
    draft = write_candidate_registry(payload["registry"], root)
    output = args.output or root / "workbench_output" / "m15r_form_1040_address_review.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_form_1040_review_html(payload), encoding="utf-8")
    print(f"candidate: {draft}")
    print(f"review: {output}")
    print(f"coverage: {payload['coverage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
