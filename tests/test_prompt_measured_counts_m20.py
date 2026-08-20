"""Guards against measured answers leaking into model prompt contracts."""

from __future__ import annotations

from pathlib import Path

from tools.check_prompt_measured_counts import find_prompt_measured_counts


ROOT = Path(__file__).resolve().parents[1]


def test_repository_prompts_contain_no_document_specific_measured_counts() -> None:
    assert find_prompt_measured_counts(ROOT) == []


def test_guard_detects_document_specific_measured_count(tmp_path: Path) -> None:
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    (prompt_root / "bad.md").write_text(
        "For Schedule 1-A, the measured expectation is 50 empty labels out of 69 spans.\n",
        encoding="ascii",
    )

    violations = find_prompt_measured_counts(tmp_path)

    assert len(violations) == 1
    assert violations[0]["document"].lower() == "schedule 1-a"
