from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.extract.models import DraftObject, ExtractionBatch, RoutedDrafts
from tax_graph.extract.route import write_routed_drafts


@pytest.mark.m20
def test_empty_regenerated_kind_removes_stale_draft_file(tmp_path: Path):
    draft_dir = tmp_path / "graph" / "2025" / "_drafts" / "schedule_a_2025"
    draft_dir.mkdir(parents=True)
    stale = draft_dir / "nodes.yaml"
    stale.write_text("- node_id: stale\n", encoding="ascii")

    batch = ExtractionBatch(
        document_id="schedule_a_2025",
        year="2025",
        objects=[],
    )
    routed = RoutedDrafts(
        accepted=[],
        review=[],
        issues=[],
        output_dir=None,
        calibration=[],
    )

    written = write_routed_drafts(batch, routed, root=tmp_path)

    assert written.output_dir == draft_dir
    assert not stale.exists()


@pytest.mark.m20
def test_route_writer_emits_expression_kinds(tmp_path: Path):
    batch = ExtractionBatch(
        document_id="form_1040_2025",
        year="2025",
        objects=[
            DraftObject(
                "rules",
                {"rule_id": "rule_sum", "operation": "SUM", "description": "Add values."},
                "",
                "generator",
                1.0,
            ),
            DraftObject(
                "edges",
                {
                    "edge_id": "edge_sum",
                    "source": "form_1040_2025_a",
                    "target": "form_1040_2025_b",
                    "relationship": "CALCULATES",
                    "rule_id": "rule_sum",
                    "role": "addend",
                },
                "",
                "generator",
                1.0,
            ),
        ],
    )
    routed = RoutedDrafts(accepted=[], review=[], issues=[], output_dir=None, calibration=[])

    written = write_routed_drafts(batch, routed, root=tmp_path)

    assert written.output_dir == tmp_path / "graph" / "2025" / "_drafts" / "form_1040_2025"
    assert (written.output_dir / "edges.yaml").exists()
    assert (written.output_dir / "rules.yaml").exists()
