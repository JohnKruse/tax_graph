"""M20-S65 tests for the provider-free pipeline doctor."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
import yaml

import tax_graph.doctor as doctor


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.m20


def _write_manifest_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    (root / "schemas").mkdir()
    (root / ".cache" / "raw" / "2025").mkdir(parents=True)
    (root / "graph" / "2025" / "_drafts" / "worksheet_2025").mkdir(parents=True)
    (root / "schemas" / "manifest.schema.json").write_text(
        (ROOT / "schemas" / "manifest.schema.json").read_text(encoding="ascii"),
        encoding="ascii",
    )
    manifest = {
        "tax_year": 2025,
        "documents": [
            {
                "document_id": "instructions_form_1040_2025",
                "kind": "instructions",
                "url": "https://www.irs.gov/pub/irs-prior/i1040gi--2025.pdf",
            },
            {
                "document_id": "worksheet_2025",
                "kind": "worksheet",
                "region": {
                    "source_document_id": "instructions_form_1040_2025",
                    "title": "Toy Worksheet",
                    "parent_sha256": "a" * 64,
                },
            },
        ],
    }
    (root / "config" / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=False),
        encoding="ascii",
    )
    (root / ".cache" / "raw" / "2025" / "instructions_form_1040_2025.pdf").write_bytes(b"pdf")
    (root / "graph" / "2025" / "_drafts" / "worksheet_2025" / "harvest.yaml").write_text(
        "document_id: worksheet_2025\nstatus: ready\n",
        encoding="ascii",
    )
    return root


def test_operation_report_keeps_lookup_bracket_as_a_real_disagreement() -> None:
    rows = doctor._check_operations(ROOT)

    lookup = next(row for row in rows if row.operation == "LOOKUP_BRACKET")
    assert lookup.prompt is False
    assert lookup.validator is True
    assert lookup.projection is False
    assert lookup.engine is True
    assert lookup.status == "DISAGREES"


def test_declared_region_harvest_is_checked_and_missing_output_is_unknown(tmp_path: Path) -> None:
    root = _write_manifest_project(tmp_path)

    checks = doctor._check_declared_artifacts(root, "2025")
    assert {item.status for item in checks} == {"HOLDS"}
    assert any(item.check_id == "harvest:worksheet_2025" for item in checks)

    (root / "graph" / "2025" / "_drafts" / "worksheet_2025" / "harvest.yaml").unlink()
    checks = doctor._check_declared_artifacts(root, "2025")
    missing = next(item for item in checks if item.check_id == "harvest:worksheet_2025")
    assert missing.status == "UNKNOWN"
    assert "missing" in missing.message


def test_outline_claim_fails_closed_when_the_predicate_cannot_read_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    claim = doctor.CHECKABLE_CLAIMS[0]

    def fail(*args, **kwargs):
        raise FileNotFoundError("source missing")

    monkeypatch.setattr(doctor, "load_document_input", fail)
    result = doctor._run_claim(claim, tmp_path, "2025")

    assert result.status == "UNKNOWN"
    assert "FileNotFoundError" in result.message


def test_open_item_age_uses_commits_touching_handoff_and_flags_threshold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    handoff = tmp_path / "plans" / "AGENT_HANDOFF.md"
    handoff.parent.mkdir()
    handoff.write_text(
        "## Open for Architect\n"
        "- **old question** (raised 2026-08-01).\n"
        "\n"
        "## From Architect\n",
        encoding="ascii",
    )
    monkeypatch.setattr(
        doctor,
        "_handoff_commit_dates",
        lambda root: ((dt.date(2026, 8, 1),) * 21, None),
    )

    items = doctor._check_open_item_age(tmp_path, max_commits=20)

    assert len(items) == 1
    assert items[0].status == "STALE"
    assert items[0].commits == 21


def test_report_exit_contract_mentions_nonzero_attention() -> None:
    report = doctor.DoctorReport(
        year="2025",
        claims=(doctor.DoctorCheck("claim", "CLEARED", "assertion", "done"),),
        artifacts=(),
        operations=(doctor.OperationRow("LOOKUP_BRACKET", False, True, False, True),),
        open_items=(),
    )

    rendered = doctor.render_doctor_report(report)
    assert not report.ok
    assert "result: NEEDS ATTENTION" in rendered
    assert "exit code: 1" in rendered
