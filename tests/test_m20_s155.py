"""M20-S155 guards for cross-document line resolution."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tax_graph.extract.assembly import FormulaAssemblyFinding, assemble_formula_plan
from tax_graph.extract.models import SourceDocumentInput
from tax_graph.extract.outline import CandidateSpan, OutlineNode
from tax_graph.extract.references import (
    build_form_alias_resolver,
    build_modelled_line_index,
)


ROOT = Path(__file__).resolve().parents[1]


def _write_project(root: Path) -> None:
    (root / "config").mkdir(parents=True)
    (root / "schemas").mkdir()
    (root / "data" / "soi").mkdir(parents=True)
    (root / "graph" / "2025" / "addresses").mkdir(parents=True)
    (root / "graph" / "2025" / "_drafts" / "schedule_3_2025").mkdir(parents=True)
    (root / "schemas" / "manifest.schema.json").write_text(
        (ROOT / "schemas" / "manifest.schema.json").read_text(encoding="ascii"),
        encoding="ascii",
    )
    manifest = {
        "tax_year": 2025,
        "documents": [
            {
                "document_id": document_id,
                "kind": kind,
                "ownership": "project-maintained",
                "url": "https://www.irs.gov/pub/irs-prior/f1040--2025.pdf",
            }
            for document_id, kind in [
                ("form_1040_2025", "tax_form"),
                ("schedule_1a_2025", "schedule"),
                ("schedule_3_2025", "schedule"),
                ("form_6251_2025", "tax_form"),
                ("form_2441_2025", "tax_form"),
            ]
        ],
    }
    (root / "config" / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=False),
        encoding="ascii",
    )
    (root / "data" / "soi" / "form_id_map.yaml").write_text(
        yaml.safe_dump(
            {
                "labels": {
                    "Form 1040": {"document_id": "form_1040_2025"},
                    "Schedule 3": {"document_id": "schedule_3_2025"},
                    "Form 6251": {"document_id": "form_6251_2025"},
                    "Form 2441": {"document_id": "form_2441_2025"},
                }
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="ascii",
    )
    (root / "graph" / "2025" / "addresses" / "schedule_1a_2025.yaml").write_text(
        yaml.safe_dump(
            {
                "addresses": [
                    {
                        "kind": "document",
                        "printed_label": "Schedule 1-A (Form 1040)",
                        "aliases": [],
                    }
                ]
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="ascii",
    )
    (root / "graph" / "2025" / "addresses" / "schedule_3_2025.yaml").write_text(
        yaml.safe_dump(
            {
                "addresses": [
                    {
                        "kind": "document",
                        "printed_label": "Schedule 3 (Form 1040)",
                        "aliases": [],
                    }
                ]
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="ascii",
    )
    (root / "graph" / "2025" / "_drafts" / "schedule_3_2025" / "outline.yaml").write_text(
        yaml.safe_dump(
            {
                "children": [
                    {
                        "outline_id": "line_15",
                        "line_anchor": "15",
                        "children": [],
                    }
                ]
            },
            sort_keys=False,
            allow_unicode=False,
        ),
        encoding="ascii",
    )


def test_aliases_are_derived_and_unknown_spelling_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _write_project(root)
    resolver = build_form_alias_resolver(root, year="2025")

    assert resolver.resolve("Schedule 1-A (Form 1040) (2025)") == "schedule_1a_2025"
    assert resolver.resolve("6251") == "form_6251_2025"
    assert resolver.resolve("Form 2441") == "form_2441_2025"
    assert resolver.resolve("Schedule 1-A (Wrong Form) (2025)") is None


def test_line_index_includes_a_promoted_modelled_document(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _write_project(root)
    current = SourceDocumentInput(
        document_id="form_1040_2025",
        kind="tax_form",
        year="2025",
        url="",
        text="",
        text_path=root / "form_1040.txt",
    )
    index = build_modelled_line_index(
        root,
        year="2025",
        current_document_id=current.document_id,
        current_nodes=[OutlineNode("root_line_31", "line", "31", line_anchor="31")],
    )

    assert index[("form_1040_2025", "31")] == "form_1040_2025_root_line_31"
    assert (
        index[("schedule_3_2025", "15")]
        == "schedule_3_2025_line_15"
    )


def test_assembly_uses_source_derived_aliases_and_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _write_project(root)
    document = SourceDocumentInput(
        document_id="form_1040_2025",
        kind="tax_form",
        year="2025",
        url="",
        text="",
        text_path=root / "form_1040.txt",
    )
    outline_node = OutlineNode(
        "root_line_31",
        "line",
        "Amount from Schedule 1-A, line 37",
        line_anchor="31",
    )
    span = CandidateSpan(
        "span_form_1040_2025_31",
        document.document_id,
        "source",
        "page 2, line 31",
        "Amount from Schedule 1-A, line 37",
    )
    plan = {
        "operation": "SUM",
        "source_lines": [
            {"form": "Schedule 1-A (Form 1040) (2025)", "line": "37", "role": None}
        ],
        "quote": "Amount from Schedule 1-A, line 37",
    }
    resolver = build_form_alias_resolver(root, year="2025")
    batch = assemble_formula_plan(
        document,
        outline_node,
        plan,
        [span],
        root=root,
        line_index={("schedule_1a_2025", "37"): "schedule_1a_2025_line_37"},
        form_aliases=resolver,
    )

    assert batch.items("edges")[0].data["source"] == "schedule_1a_2025_line_37"

    unknown_plan = {
        **plan,
        "source_lines": [{"form": "Schedule 1-Z (Form 1040)", "line": "37"}],
    }
    with pytest.raises(FormulaAssemblyFinding) as exc_info:
        assemble_formula_plan(
            document,
            outline_node,
            unknown_plan,
            [span],
            root=root,
            line_index={("schedule_1a_2025", "37"): "schedule_1a_2025_line_37"},
            form_aliases=resolver,
        )
    assert "key None not in outline index" in exc_info.value.finding["reason"]
