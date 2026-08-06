"""M20-S71 regression tests for clean text across the full anchor set."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pytest
import yaml

from tax_graph.extract.candidate import write_candidate_from_run
from tax_graph.extract.cells import (
    CellFrame,
    _table_anchor_boundary_finding,
    build_cell_frame_from_document,
    derive_cells,
)
from tax_graph.extract.inputs import load_document_input


ROOT = Path(__file__).resolve().parents[1]
REAL_RUN = Path(r"C:\tmp\m20_s68_live")
pytestmark = pytest.mark.m20


class _UnexpectedClient:
    def __init__(self) -> None:
        self.calls = 0

    def structured_completion(self, **_kwargs: Any) -> Any:
        self.calls += 1
        raise AssertionError("selector-skipped cells must not call the provider")


def test_selector_skips_provider_but_retains_clean_cell_text() -> None:
    frame = CellFrame.from_rows(
        [
            {
                "form": "form_test_2025",
                "line": "1",
                "label": "",
                "form_face_text": "Enter an amount.",
                "instruction_text": "",
                "instruction_locator": "",
                "metadata": {
                    "selector_admitted": False,
                    "selector_skip_reason": "selector_no_formula_cue",
                },
            }
        ]
    )

    client = _UnexpectedClient()
    result = derive_cells(frame, "line <<line>>", "unused", client=client)

    assert result.rows[0].status == "skipped"
    assert result.rows[0].form_face_text == "Enter an amount."
    assert result.rows[0].metadata["selector_skip_reason"] == "selector_no_formula_cue"
    assert client.calls == 0
    assert result.validation_report["attempted"] == 0


def test_table_anchor_boundary_is_a_named_finding() -> None:
    text = (
        "8 Enter the decimal amount shown below. Over amount is $0-15,000 .35 "
        "8 X 15,000-17,000 .34"
    )

    finding = _table_anchor_boundary_finding(text, cleaned_text=text, line="8")

    assert finding is not None
    assert finding["code"] == "table_anchor_boundary"
    assert "boundary is unresolved" in finding["detail"]


def test_real_frame_cleans_all_printed_anchors_and_reports_line_8_table() -> None:
    required = [
        ROOT / ".cache" / "raw" / "2025" / "form_2441_2025.txt",
        ROOT / ".cache" / "raw" / "2025" / "form_2441_2025.fields.json",
        ROOT / ".cache" / "raw" / "2025" / "form_2441_2025.pdf",
    ]
    if not all(path.is_file() for path in required):
        pytest.skip("local acquired Form 2441 artifacts are not present")

    document = load_document_input("form_2441_2025", year="2025", root=ROOT)
    frame = build_cell_frame_from_document(document)

    assert len(frame.rows) == 35
    assert all(row.form_face_text for row in frame.rows)
    assert all("selector_admitted" in row.metadata for row in frame.rows)
    line_8 = next(row for row in frame.rows if row.line == "8")
    assert line_8.metadata["evidence_findings"][0]["code"] == "table_anchor_boundary"


def test_real_candidate_node_labels_use_clean_text(tmp_path: Path) -> None:
    if not REAL_RUN.is_dir():
        pytest.skip("the S68 real derivation run is not available")

    candidate = write_candidate_from_run(
        REAL_RUN,
        tmp_path / "candidate",
        root=ROOT,
        expected_documents=["form_1040_2025", "form_2441_2025", "form_6251_2025"],
    )
    for rows_path in sorted((candidate / "graph" / "2025" / "_drafts").glob("*/rows.yaml")):
        rows = {
            str(row["line"]): row
            for row in yaml.safe_load(rows_path.read_text(encoding="ascii")) or []
            if row.get("candidate_status") in {"derived", "repaired"}
        }
        nodes = yaml.safe_load(
            (rows_path.parent / "nodes.yaml").read_text(encoding="ascii")
        ) or []
        for node in nodes:
            node_id = str(node.get("node_id") or "")
            match = re.search(r"_root_line_(.+)$", node_id)
            if match is None or match.group(1) not in rows:
                continue
            line = match.group(1)
            label = str(node.get("label") or "")
            assert not re.search(rf"^Line\s+{re.escape(line)}:\s+{re.escape(line)}(?:\s|$)", label, re.I)
            assert not re.search(rf"\s{re.escape(line)}$", label, re.I)
            assert label != str(rows[line].get("label_before") or "")
