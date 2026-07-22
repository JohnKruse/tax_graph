from __future__ import annotations

import json
from pathlib import Path
import zipfile

import pytest

from tax_graph.extension import build_address_contribution, package_extension


ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    not (ROOT / "graph_ext" / "2025" / "form_2441_2025").exists(),
    reason="form-2441 extension artifacts are not installed: parity checkouts cannot build its contribution",
)
DOCUMENT_ID = "form_2441_2025"


@pytest.mark.m15r
def test_form_2441_address_contribution_stays_outside_live_corpus() -> None:
    live_registry = ROOT / "graph/2025/addresses/form_2441_2025.yaml"
    assert not live_registry.exists()

    output = build_address_contribution(DOCUMENT_ID, root=ROOT)
    report = json.loads((output / "report.json").read_text(encoding="ascii"))

    assert output == ROOT / "graph_ext/2025/_drafts/form_2441_2025/addressing"
    assert not live_registry.exists()
    assert report["gate"] == "user"
    assert report["project_corpus"] is False
    assert report["human_confirmed"] is False
    assert report["review_status"] == "pending"
    assert report["coverage"]["inventory"] == 72
    assert report["coverage"]["inventory"] == (
        report["coverage"]["addressed_widgets"] + report["coverage"]["exempt_widgets"]
    )
    assert set(path.name for path in output.iterdir()) == {
        "addresses.yaml", "node_bindings.yaml", "references.yaml", "report.json", "widget_bindings.yaml",
    }


@pytest.mark.m15r
def test_form_2441_package_is_deterministic_and_truthful(tmp_path: Path) -> None:
    first = package_extension(DOCUMENT_ID, root=ROOT, output_dir=tmp_path)
    first_bytes = first.path.read_bytes()
    second = package_extension(DOCUMENT_ID, root=ROOT, output_dir=tmp_path)

    assert second.path.read_bytes() == first_bytes
    with zipfile.ZipFile(first.path) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("package.json"))
    assert "review/addressing/report.json" in names
    assert "review/addressing/addresses.yaml" in names
    assert manifest["gate"] == "user"
    assert manifest["address_review_status"] == "pending"
    assert manifest["project_corpus"] is False
    assert manifest["human_confirmed"] is False
