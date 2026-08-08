"""Fast tests for the standalone construction measurement pilot."""

from __future__ import annotations

from pathlib import Path

import yaml

from measure import main, measure


def _candidate(tmp_path: Path) -> Path:
    root = tmp_path / "candidate"
    source = root / "source_reports"
    source.mkdir(parents=True)
    (root / "candidate.yaml").write_text(
        yaml.safe_dump(
            {
                "kind": "candidate_graph",
                "documents": ["toy_2025"],
            },
            sort_keys=False,
        ),
        encoding="ascii",
    )
    report = {
        "document_id": "toy_2025",
        "year": "2025",
        "rows": 2,
        "rows_attempted": 2,
        "line_anchor_count": 3,
        "rows_detail": [
            {
                "line": "1",
                "label_after": "Enter the smaller of line 2 or $500.",
                "form_face_after": "Enter the smaller of line 2 or $500.",
                "status": "derived",
                "quote": "Enter the smaller of line 2 or $500.",
            },
            {
                "line": "2",
                "label_after": "If line 1 is $10 or less, enter line 1. Otherwise, enter zero.",
                "form_face_after": "If zero or less, enter -0-.",
                "status": "error",
                "error": "provider error",
            },
        ],
        "denominator": {
            "line_anchor_count": 3,
            "skipped": 1,
            "skipped_by_reason": {"structure_non_cell_anchor": 1},
            "anchors": [
                {"anchor": "1"},
                {"anchor": "2"},
                {"anchor": "3", "label": "Check the box if required.", "skip_reason": "structure_non_cell_anchor"},
            ],
        },
    }
    (source / "m20_s68_toy_2025_derive_cells_report.yaml").write_text(
        yaml.safe_dump(report, sort_keys=False),
        encoding="ascii",
    )
    return root


def test_measure_uses_printed_anchors_and_reports_outcomes(tmp_path: Path) -> None:
    inventory = measure(_candidate(tmp_path))

    assert inventory["denominator"]["printed_anchors"] == 3
    assert inventory["denominator"]["outcomes"] == {
        "derived": 1,
        "repaired": 0,
        "errored": 1,
        "skipped": 1,
    }
    construction = {item["id"]: item for item in inventory["constructions"]}
    assert construction["smaller_or_smallest_of"]["count"] == 1
    assert construction["smaller_or_smallest_of"]["outcomes"]["derived"] == 1
    assert construction["if_otherwise"]["count"] == 1
    assert construction["if_otherwise"]["example_anchor_ids"] == ["toy_2025#line=2"]
    assert construction["checkbox_line"]["count"] == 1
    assert inventory["comparator_gap"]["inclusive_or_exclusive_anchor_count"] == 1


def test_vocabulary_is_derived_from_source_text(tmp_path: Path) -> None:
    inventory = measure(_candidate(tmp_path))
    tokens = inventory["vocabulary"]["token_counts"]

    assert tokens["smaller"] == 1
    assert tokens["otherwise"] == 1
    assert "authored_operation_name" not in tokens


def test_cli_writes_report_to_requested_path(tmp_path: Path) -> None:
    candidate = _candidate(tmp_path)
    output = tmp_path / "inventory.yaml"

    assert main([str(candidate), "--output", str(output)]) == 0
    loaded = yaml.safe_load(output.read_text(encoding="ascii"))
    assert loaded["kind"] == "construction_inventory"
    assert loaded["denominator"]["printed_anchors"] == 3


def test_measure_preserves_duplicate_printed_anchor_instances(tmp_path: Path) -> None:
    root = tmp_path / "candidate"
    source = root / "source_reports"
    source.mkdir(parents=True)
    (root / "candidate.yaml").write_text(
        yaml.safe_dump({"kind": "candidate_graph", "documents": ["toy_2025"]}, sort_keys=False),
        encoding="ascii",
    )
    report = {
        "document_id": "toy_2025",
        "year": "2025",
        "rows": 1,
        "rows_attempted": 1,
        "line_anchor_count": 2,
        "rows_detail": [
            {
                "line": "2",
                "label_after": "Enter the smaller of line 1 or $500.",
                "status": "derived",
            }
        ],
        "denominator": {
            "line_anchor_count": 2,
            "anchors": [
                {"anchor": "2", "label": "Header anchor", "skip_reason": "structure_header_anchor"},
                {"anchor": "2", "label": "Enter the smaller of line 1 or $500."},
            ],
        },
    }
    (source / "m20_s68_toy_2025_derive_cells_report.yaml").write_text(
        yaml.safe_dump(report, sort_keys=False),
        encoding="ascii",
    )

    inventory = measure(root)

    assert inventory["denominator"]["printed_anchors"] == 2
    assert inventory["denominator"]["outcomes"] == {
        "derived": 1,
        "repaired": 0,
        "errored": 0,
        "skipped": 1,
    }
    smaller = next(item for item in inventory["constructions"] if item["id"] == "smaller_or_smallest_of")
    assert smaller["example_anchor_ids"] == ["toy_2025#anchor=2:line=2"]


def test_measure_keeps_candidate_text_for_skipped_anchor(tmp_path: Path) -> None:
    root = _candidate(tmp_path)
    draft = root / "graph" / "2025" / "_drafts" / "toy_2025"
    draft.mkdir(parents=True)
    (draft / "rows.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "line": "3",
                    "instruction_text": "If zero or less, enter -0-.",
                    "status": "skipped",
                }
            ],
            sort_keys=False,
        ),
        encoding="ascii",
    )

    inventory = measure(root)

    floor = next(item for item in inventory["constructions"] if item["id"] == "zero_or_less_floor")
    assert floor["count"] == 2
    assert floor["outcomes"]["skipped"] == 1
