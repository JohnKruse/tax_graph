from __future__ import annotations

from pathlib import Path

import pytest
import shutil

from tax_graph.cli import verify_record_command
from tax_graph.verify.record import build_verification_bundle


ROOT = Path(__file__).resolve().parents[1]


def _copy_verification_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "graph", root / "graph", ignore=shutil.ignore_patterns("_drafts"))
    shutil.copytree(ROOT / "schemas", root / "schemas")
    shutil.copytree(ROOT / "config", root / "config")
    shutil.copytree(ROOT / "data", root / "data")
    shutil.copytree(ROOT / "examples", root / "examples")
    shutil.copytree(ROOT / "oracles", root / "oracles")
    shutil.copytree(ROOT / "review_queue", root / "review_queue")
    _copy_required_drafts(root)
    return root


def _copy_required_drafts(root: Path) -> None:
    drafts_root = root / "graph" / "2025" / "_drafts"
    drafts_root.mkdir(parents=True, exist_ok=True)
    for document_id in ("form_8949_2025", "schedule_d_2025"):
        shutil.copytree(ROOT / "graph" / "2025" / "_drafts" / document_id, drafts_root / document_id)


@pytest.mark.m9
def test_verify_record_matches_committed_goldens(tmp_path, capsys):
    root = _copy_verification_root(tmp_path)
    rollup_path = tmp_path / "VERIFICATION.md"
    pages_dir = tmp_path / "docs" / "verification"

    exit_code = verify_record_command(year="2025", root=root, rollup_path=rollup_path, pages_dir=pages_dir)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "verification record" in captured.out
    rollup_text = rollup_path.read_text(encoding="utf-8")
    form_8949_text = (pages_dir / "form_8949_2025.md").read_text(encoding="utf-8")
    schedule_d_text = (pages_dir / "schedule_d_2025.md").read_text(encoding="utf-8")

    assert rollup_text.startswith("# Verification Record (2025)\n")
    assert "### [Form 8949](docs/verification/form_8949_2025.md)" in rollup_text
    assert "### [Schedule D (Form 1040)](docs/verification/schedule_d_2025.md)" in rollup_text
    assert "- Verification tier: independently witnessed" in rollup_text
    assert "pending human review" in rollup_text
    assert form_8949_text.startswith("# Form 8949 Verification Record (form_8949_2025)\n")
    assert "- Oracle differential:" in form_8949_text
    assert "OpenTaxSolver" in form_8949_text
    assert schedule_d_text.startswith("# Schedule D (Form 1040) Verification Record (schedule_d_2025)\n")
    assert "- IRS worked examples: 1 committed IRS worked-example fixture(s); 1 pending human review." in schedule_d_text


@pytest.mark.m9
def test_verify_record_is_byte_stable_on_regeneration(tmp_path):
    root = _copy_verification_root(tmp_path)
    rollup_path = tmp_path / "VERIFICATION.md"
    pages_dir = tmp_path / "docs" / "verification"

    first = verify_record_command(year="2025", root=root, rollup_path=rollup_path, pages_dir=pages_dir)
    before_rollup = rollup_path.read_bytes()
    before_page = (pages_dir / "form_8949_2025.md").read_bytes()

    second = verify_record_command(year="2025", root=root, rollup_path=rollup_path, pages_dir=pages_dir)

    assert first == 0
    assert second == 0
    assert before_rollup == rollup_path.read_bytes()
    assert before_page == (pages_dir / "form_8949_2025.md").read_bytes()


@pytest.mark.m9
def test_verify_record_states_witness_absence_plainly(tmp_path):
    root = _copy_verification_root(tmp_path)
    bundle = build_verification_bundle(year="2025", root=root)

    schedule_d = bundle.page_texts["schedule_d_2025"]
    form_1099b = bundle.page_texts["form_1099b_2025"]

    assert "1 committed IRS worked-example fixture(s); 1 pending human review." in schedule_d
    assert "No committed calibration metrics artifact covers this document." in form_1099b
