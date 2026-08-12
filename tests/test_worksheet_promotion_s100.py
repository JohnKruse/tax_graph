"""M20-S100 tests for worksheet regions becoming loadable review inputs."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pilot.review_panel import _worksheet_review, _worksheet_review_html
from tax_graph.acquire.manifest import load_manifest
from tax_graph.cli import harvest_worksheet_command, promote_worksheet_command
from tax_graph.extract.cells import build_cell_frame_from_document, derive_cells
from tax_graph.extract.inputs import load_document_input


pytestmark = pytest.mark.m20
ROOT = Path(__file__).resolve().parents[1]


def _project(tmp_path: Path, html_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    (root / "schemas").mkdir()
    (root / "schemas" / "manifest.schema.json").write_text(
        (Path(__file__).resolve().parents[1] / "schemas" / "manifest.schema.json").read_text(encoding="utf-8"),
        encoding="ascii",
    )
    (root / "config" / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "tax_year": 2025,
                "documents": [
                    {
                        "document_id": "instructions_toy_2025",
                        "kind": "instructions",
                        "ownership": "project-maintained",
                        "url": "https://www.irs.gov/pub/irs-prior/itoy--2025.pdf",
                    },
                    {
                        "document_id": "old_toy_worksheet",
                        "kind": "worksheet",
                        "region": {
                            "source_document_id": "instructions_toy_2025",
                            "title": "Toy Worksheet",
                            "parent_sha256": "0" * 64,
                        },
                    },
                ],
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="ascii",
    )
    for kind in ("documents", "nodes", "edges", "rules", "citations", "decisions", "tables"):
        (root / "graph" / "2025" / kind).mkdir(parents=True)
    return root


def _toy_html(tmp_path: Path) -> Path:
    path = tmp_path / "instructions_toy_2025.html"
    path.write_text(
        """
        <h3><a name="toy"></a>Toy Worksheet</h3>
        <table><tr><td>1.</td><td>Enter an amount.</td></tr>
        <tr><td>2.</td><td>Subtract line 1 from the amount.</td></tr></table>
        """,
        encoding="ascii",
    )
    return path


def test_harvest_mints_region_and_promote_loads_without_raw_text(tmp_path: Path) -> None:
    html = _toy_html(tmp_path)
    root = _project(tmp_path, html)

    def classifier(_table, _source_text):
        return {"kind": "worksheet"}

    def window_classifier(table, _source_text, _lookahead, _chunk):
        return {
            "starts_a_worksheet": True,
            "title": "Toy Worksheet",
            "table_ids": [table.table_id],
            "parameter_table_ids": [],
            "serves_lines": ["1", "2"],
        }

    assert harvest_worksheet_command(
        root=root,
        html_path=html,
        source_document_id="instructions_toy_2025",
        draft_dir=root / "graph" / "2025" / "_drafts",
        classifier=classifier,
        window_classifier=window_classifier,
    ) == 0

    manifest = load_manifest(root=root)
    entries = manifest.by_document_id()
    assert "old_toy_worksheet" not in entries
    assert "toy_worksheet_2025" in entries
    assert entries["toy_worksheet_2025"].region_of == "instructions_toy_2025"

    assert promote_worksheet_command(root=root) == 0
    document = load_document_input("toy_worksheet_2025", root=root, year="2025")
    assert document.source_document_id == "instructions_toy_2025"
    assert "- 1: Enter an amount." in document.text
    assert document.fields_path is None
    assert not (root / ".cache" / "raw" / "2025" / "toy_worksheet_2025.txt").exists()


class _WorksheetClient:
    """Return deterministic fixture rules for the offline S100 derivation seam."""

    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = list(responses)

    def structured_completion(self, **_kwargs: object) -> dict[str, object]:
        return self.responses.pop(0)


def test_self_serve_fixture_region_derives_all_its_cell_rows(tmp_path: Path) -> None:
    html = _toy_html(tmp_path)
    root = _project(tmp_path, html)
    harvest_worksheet_command(
        root=root,
        html_path=html,
        source_document_id="instructions_toy_2025",
        draft_dir=root / "graph" / "2025" / "_drafts",
        classifier=lambda _table, _source_text: {"kind": "worksheet"},
        window_classifier=lambda table, _source_text, _lookahead, _chunk: {
            "starts_a_worksheet": True,
            "title": "Toy Worksheet",
            "table_ids": [table.table_id],
            "parameter_table_ids": [],
            "serves_lines": ["1", "2"],
        },
    )
    promote_worksheet_command(root=root)

    document = load_document_input("toy_worksheet_2025", root=root, year="2025")
    frame = build_cell_frame_from_document(document)
    assert [row.line for row in frame.rows] == ["1", "2"]
    responses = [
        {
            "expression": {"op": "COPY", "args": [{"line": "1" if row.line == "2" else "2"}]},
            "quote": row.form_face_text,
        }
        for row in frame.rows
    ]
    result = derive_cells(frame, "line <<line>>: <<form_face_text>>", "offline-test", client=_WorksheetClient(responses))
    assert result.coverage == {"total": 2, "derived": 2}


def test_promoted_worksheet_corpus_loads_and_simplified_method_derives_all_lines() -> None:
    manifest = load_manifest(root=ROOT)
    regions = [entry for entry in manifest.documents if entry.is_region]
    assert len(regions) == 19
    for entry in regions:
        document = load_document_input(entry.document_id, year=2025, root=ROOT)
        assert document.source_document_id == entry.region_of
        assert document.fields_path is None
        assert document.fields["fields"]

    document = load_document_input("simplified_method_worksheet_2025", year=2025, root=ROOT)
    frame = build_cell_frame_from_document(document)
    assert [row.line for row in frame.rows] == [str(number) for number in range(1, 12)]
    expressions = [
        {"op": "REQUIRE_INPUT", "args": [{"line": "1"}]},
        {"op": "COPY", "args": [{"line": "1"}]},
        {"op": "REQUIRE_INPUT", "args": [{"line": "3"}]},
        {"op": "DIVIDE", "args": [{"line": "2"}, {"line": "3"}]},
        {"op": "MULTIPLY", "args": [{"line": "4"}, {"const": 12}]},
        {"op": "COPY", "args": [{"line": "1"}]},
        {"op": "SUBTRACT", "args": [{"line": "2"}, {"line": "6"}]},
        {"op": "MIN", "args": [{"line": "5"}, {"line": "7"}]},
        {"op": "SUBTRACT", "args": [{"line": "1"}, {"line": "8"}]},
        {"op": "REQUIRE_INPUT", "args": [{"line": "10"}]},
        {"op": "SUBTRACT", "args": [{"line": "2"}, {"line": "10"}]},
    ]
    responses = [
        {"expression": expression, "quote": row.form_face_text}
        for row, expression in zip(frame.rows, expressions)
    ]
    result = derive_cells(
        frame,
        "line <<line>>: <<form_face_text>>",
        "offline-test",
        client=_WorksheetClient(responses),
    )
    assert result.coverage == {"total": 11, "derived": 11}


def test_review_surface_renders_promoted_and_refused_worksheets(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "candidate.yaml").write_text(
        yaml.safe_dump(
            {
                "year": "2025",
                "documents": ["form_1040_2025"],
                "worksheet_drafts": {
                    "copied": ["toy_worksheet_2025"],
                    "promoted": ["toy_worksheet_2025"],
                    "missing": [],
                },
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="ascii",
    )
    (candidate / "worksheet-discovery-instructions_toy_2025.yaml").write_text(
        yaml.safe_dump(
            {
                "source_document_id": "instructions_toy_2025",
                "worksheets": [
                    {
                        "document_id": "toy_worksheet_2025",
                        "worksheet_title": "Toy Worksheet",
                        "status": "ready",
                        "findings": [],
                    },
                    {
                        "document_id": "blocked_worksheet_2025",
                        "worksheet_title": "Blocked Worksheet",
                        "status": "blocked",
                        "findings": [
                            {"kind": "line_sequence_gap", "message": "expected line 2, found 4"}
                        ],
                    },
                ],
                "findings": [],
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="ascii",
    )

    review = _worksheet_review(candidate, yaml.safe_load((candidate / "candidate.yaml").read_text(encoding="ascii")))
    assert [(item["document_id"], item["status"]) for item in review] == [
        ("blocked_worksheet_2025", "refused"),
        ("toy_worksheet_2025", "promoted"),
    ]
    html = _worksheet_review_html(review)
    assert 'data-worksheet-status="promoted"' in html
    assert 'data-worksheet-status="refused"' in html
    assert "expected line 2, found 4" in html
