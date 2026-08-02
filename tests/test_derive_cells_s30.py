"""M20-S30 tests for the multi-document derivation harness."""

from pathlib import Path

import pytest

from experiments.derive_cells_s25 import _output_destination, _top_three_counts, run_documents


pytestmark = pytest.mark.m20


def test_harness_rejects_output_inside_repository(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    with pytest.raises(ValueError, match="outside repository root"):
        _output_destination(root, root / "output")


def test_harness_reports_only_top_three_validator_counts() -> None:
    assert _top_three_counts({"zeta": 1, "alpha": 3, "beta": 3, "gamma": 2}) == {
        "alpha": 3,
        "beta": 3,
        "gamma": 2,
    }


def test_harness_reports_unloadable_document_without_skipping(monkeypatch, tmp_path: Path) -> None:
    output = tmp_path / "output"

    def fail_to_load(**kwargs):
        raise FileNotFoundError(f"missing rendered text for {kwargs['document_id']}")

    monkeypatch.setattr("experiments.derive_cells_s25.persist_instruction_frame", fail_to_load)

    reports = run_documents(
        root=tmp_path / "repo",
        year="2025",
        document_ids=["missing_document"],
        output_dir=output,
        no_provider=True,
    )

    assert reports == [
        {
            "document_id": "missing_document",
            "status": "reported",
            "reason": "FileNotFoundError: missing rendered text for missing_document",
            "rows_attempted": 0,
            "derived": 0,
            "repaired": 0,
            "gapped": 0,
            "errored": 0,
        }
    ]
