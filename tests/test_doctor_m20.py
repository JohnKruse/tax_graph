"""M20-S67 tests for the provider-free pipeline doctor."""

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


def test_operation_report_uses_registry_for_every_layer() -> None:
    rows = doctor._check_operations(ROOT)

    lookup = next(row for row in rows if row.operation == "LOOKUP_BRACKET")
    assert lookup.prompt is True
    assert lookup.validator is True
    assert lookup.projection is True
    assert lookup.engine is True
    assert lookup.category == "value"
    assert lookup.projection_expected is True
    assert lookup.status == "HOLDS"
    assert all(row.status == "HOLDS" for row in rows)


def test_doctor_accepts_predicate_and_disposition_rows_without_projection() -> None:
    rows = doctor._check_operations(ROOT)

    predicate = next(row for row in rows if row.operation == "COMPARE")
    assert predicate.category == "predicate"
    assert predicate.projection is False
    assert predicate.projection_expected is False
    assert predicate.status == "HOLDS"

    disposition = next(row for row in rows if row.operation == "REQUIRE_INPUT")
    assert disposition.category == "disposition"
    assert disposition.projection is False
    assert disposition.projection_expected is False
    assert disposition.status == "HOLDS"


def test_doctor_catches_prompt_roles_validator_does_not_accept(monkeypatch: pytest.MonkeyPatch) -> None:
    original = doctor.prompt_operation_documentation()
    broken = original.replace(
        "- SUM: Add one or more values. category=value; args=1+",
        "- SUM: Add one or more values. category=value; args=1+; roles=addend",
    )
    monkeypatch.setattr(doctor, "prompt_operation_documentation", lambda: broken)

    rows = doctor._check_operations(ROOT)
    sum_row = next(row for row in rows if row.operation == "SUM")

    assert sum_row.prompt_roles == ("addend",)
    assert sum_row.validator_roles == ()
    assert sum_row.projection_roles == ("addend",)
    assert sum_row.role_agreement is False
    assert sum_row.status == "DISAGREES"
    assert "prompt=addend" in sum_row.detail


def test_doctor_catches_validator_role_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    import tax_graph.extract.cells as cells

    monkeypatch.setattr(cells, "validate_expression_tree", lambda expression, max_depth=2: None)

    rows = doctor._check_operations(ROOT)
    sum_row = next(row for row in rows if row.operation == "SUM")

    assert sum_row.validator_roles == ("probe",)
    assert sum_row.role_agreement is False
    assert sum_row.status == "DISAGREES"
    assert "validator=probe" in sum_row.detail


def test_doctor_catches_projection_role_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    import tax_graph.extract.cells as cells

    monkeypatch.setattr(cells, "_role_for", lambda operation, index, operand=None: "wrong")

    rows = doctor._check_operations(ROOT)
    sum_row = next(row for row in rows if row.operation == "SUM")

    assert sum_row.projection_roles == ("wrong",)
    assert sum_row.role_agreement is False
    assert sum_row.status == "DISAGREES"
    assert "projection=wrong" in sum_row.detail


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


def test_operation_report_fails_when_a_runtime_handler_disappears(monkeypatch: pytest.MonkeyPatch) -> None:
    import tax_graph.engine.operations as operations

    monkeypatch.setattr(operations, "registered_operations", lambda: frozenset())

    rows = doctor._check_operations(ROOT)

    assert all(row.engine is False for row in rows)
    assert all(row.status == "DISAGREES" for row in rows)
