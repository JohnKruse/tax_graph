"""M20-S41 regression tests for manifest reconciliation and corpus selection."""

from __future__ import annotations

from pathlib import Path

import pytest

from experiments.derive_cells_s25 import manifest_document_ids, run_documents
from tax_graph.acquire.manifest import load_manifest
from tax_graph.acquire.reconcile import reconcile_document_lists
from tax_graph.cli import validate_command


pytestmark = pytest.mark.m20

ROOT = Path(__file__).resolve().parents[1]


def _baseline_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest_ids = set(load_manifest(root=ROOT).by_document_id())
    graph_ids = sorted(
        (manifest_ids - {
            "instructions_form_6251_2025",
            "instructions_form_8949_2025",
            "instructions_schedule_a_2025",
            "instructions_schedule_b_2025",
        })
        | {"form_2441_2025"}
    )
    original = __import__("tax_graph.acquire.reconcile", fromlist=["load_graph"])
    monkeypatch.setattr(
        original,
        "load_graph",
        lambda *_args, **_kwargs: type("Graph", (), {
            "items": lambda _self, kind: (
                [{"document_id": document_id} for document_id in graph_ids]
                if kind == "documents"
                else []
            )
        })(),
    )


def test_reconcile_names_graph_and_manifest_differences_without_raw_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _baseline_graph(monkeypatch)
    report = reconcile_document_lists(root=ROOT, year="2025", raw_store=tmp_path / "raw")

    assert report.raw_status == "skipped"
    assert report.difference("graph_not_in_manifest").document_ids == ()
    assert report.difference("manifest_not_in_graph").document_ids == (
        "instructions_form_6251_2025",
        "instructions_form_8949_2025",
        "instructions_schedule_a_2025",
        "instructions_schedule_b_2025",
    )
    assert report.difference("raw_not_in_manifest").status == "skipped"
    assert report.difference("manifest_not_in_raw").status == "skipped"
    assert "raw text directory is absent" in report.format_report()


def test_reconcile_reports_named_raw_orphans_and_missing_manifest_text(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _baseline_graph(monkeypatch)
    raw_year = tmp_path / "raw" / "2025"
    raw_year.mkdir(parents=True)
    (raw_year / "form_1040_2025.txt").write_text("form", encoding="ascii")
    (raw_year / "orphan_2025.txt").write_text("orphan", encoding="ascii")
    (raw_year / "not_text.html").write_text("ignored", encoding="ascii")

    report = reconcile_document_lists(root=ROOT, year="2025", raw_store=tmp_path / "raw")

    assert report.raw_status == "available"
    assert report.raw_documents == ("form_1040_2025", "orphan_2025")
    assert report.difference("raw_not_in_manifest").document_ids == ("orphan_2025",)
    # Region documents are backed by the parent HTML and therefore do not need
    # a child .txt artifact in the form-row reconciliation inventory.
    region_ids = {
        entry.document_id
        for entry in load_manifest(root=ROOT).documents
        if entry.is_region
    }
    assert report.difference("manifest_not_in_raw").document_ids == tuple(sorted(
        entry for entry in report.manifest_documents
        if entry not in {"form_1040_2025"} | region_ids
    ))


def test_validate_surfaces_reconcile_ids_without_failing_on_preexisting_differences(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class Result:
        ok = True

        @staticmethod
        def format_report() -> str:
            return "graph integrity OK\n"

    monkeypatch.setattr("tax_graph.cli.validate_graph", lambda *_args, **_kwargs: Result())
    _baseline_graph(monkeypatch)

    assert validate_command(year="2025", root=ROOT) == 0
    output = capsys.readouterr().out
    assert "document reconcile" in output
    assert "graph_not_in_manifest: -" in output
    assert "instructions_form_6251_2025" in output


def test_manifest_document_ids_are_declared_and_ordered() -> None:
    ids = manifest_document_ids(root=ROOT, year="2025")

    assert len(ids) == 23
    assert ids[0] == "form_8949_2025"
    assert ids[-2:] == ["form_2441_2025", "instructions_form_2441_2025"]
    assert ids == [
        entry.document_id
        for entry in load_manifest(root=ROOT).documents
        if not entry.is_region
    ]


def test_run_documents_defaults_to_manifest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen: list[str] = []

    def fake_persist(**kwargs):
        seen.append(kwargs["document_id"])
        return tmp_path / "frame.yaml", tmp_path / "coverage.yaml"

    monkeypatch.setattr("experiments.derive_cells_s25.persist_instruction_frame", fake_persist)
    monkeypatch.setattr(
        "experiments.derive_cells_s25._output_destination",
        lambda *_args, **_kwargs: tmp_path / "output",
    )

    reports = run_documents(
        root=ROOT,
        year="2025",
        document_ids=None,
        output_dir=tmp_path / "output",
        no_provider=True,
    )

    assert seen == manifest_document_ids(root=ROOT, year="2025")
    assert [report["document_id"] for report in reports] == seen
    assert all(report["status"] == "prepared" for report in reports)
