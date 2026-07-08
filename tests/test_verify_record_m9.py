from __future__ import annotations

from pathlib import Path

import pytest

from tax_graph.cli import verify_record_command
from tax_graph.verify.record import build_verification_bundle


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m9
def test_verify_record_matches_committed_goldens(tmp_path, capsys):
    rollup_path = tmp_path / "VERIFICATION.md"
    pages_dir = tmp_path / "docs" / "verification"

    exit_code = verify_record_command(year="2025", root=ROOT, rollup_path=rollup_path, pages_dir=pages_dir)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "verification record" in captured.out
    assert rollup_path.read_text(encoding="utf-8") == (ROOT / "VERIFICATION.md").read_text(encoding="utf-8")
    assert (pages_dir / "form_8949_2025.md").read_text(encoding="utf-8") == (
        ROOT / "docs" / "verification" / "form_8949_2025.md"
    ).read_text(encoding="utf-8")
    assert (pages_dir / "schedule_d_2025.md").read_text(encoding="utf-8") == (
        ROOT / "docs" / "verification" / "schedule_d_2025.md"
    ).read_text(encoding="utf-8")


@pytest.mark.m9
def test_verify_record_is_byte_stable_on_regeneration(tmp_path):
    rollup_path = tmp_path / "VERIFICATION.md"
    pages_dir = tmp_path / "docs" / "verification"

    first = verify_record_command(year="2025", root=ROOT, rollup_path=rollup_path, pages_dir=pages_dir)
    before_rollup = rollup_path.read_bytes()
    before_page = (pages_dir / "form_8949_2025.md").read_bytes()

    second = verify_record_command(year="2025", root=ROOT, rollup_path=rollup_path, pages_dir=pages_dir)

    assert first == 0
    assert second == 0
    assert before_rollup == rollup_path.read_bytes()
    assert before_page == (pages_dir / "form_8949_2025.md").read_bytes()


@pytest.mark.m9
def test_verify_record_states_witness_absence_plainly():
    bundle = build_verification_bundle(year="2025", root=ROOT)

    schedule_d = bundle.page_texts["schedule_d_2025"]
    form_1099b = bundle.page_texts["form_1099b_2025"]

    assert "1 committed IRS worked-example fixture(s); 1 pending human review." in schedule_d
    assert "No committed calibration metrics artifact covers this document." in form_1099b
