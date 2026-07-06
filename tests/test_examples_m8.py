from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tax_graph.cli import verify_mine_examples_command, verify_replay_examples_command
from tax_graph.verify.examples import replay_irs_examples, segment_example_blocks


ROOT = Path(__file__).resolve().parents[1]


class FakeExampleClient:
    def __init__(self):
        self.calls: list[dict] = []

    def structured_completion(self, *, prompt, schema, model, max_tokens, temperature, purpose):
        self.calls.append(
            {
                "prompt": prompt,
                "schema": schema,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "purpose": purpose,
            }
        )
        return {
            "facts": {
                "facts": [],
                "tables": [
                    {
                        "table_id": "form_8949_2025_part_ii_line_1",
                        "rows": [
                            {
                                "row_key": "mock_example",
                                "columns": {"d": 6000, "e": 2000, "g": 0},
                            }
                        ],
                    }
                ],
            },
            "expected": {
                "form_8949_2025_part_ii_line_1_column_h#mock_example": 4000,
                "form_1040_2025_line_7_capital_gain_loss": 4000,
            },
            "notes": "mocked extraction",
        }


@pytest.mark.m8
def test_segment_example_blocks_finds_markdown_examples():
    text = "\n".join(
        [
            "Intro",
            "**Example 1Gain.** Column (d) is $6,000 and column (e) is $2,000.",
            "**Example 2Loss.** Column (d) is $6,000 and column (e) is $8,000.",
            "## Next Section",
        ]
    )

    blocks = segment_example_blocks(text, source_document_id="instructions_form_8949_2025")

    assert [block.example_id for block in blocks] == ["example_001", "example_002"]
    assert "Example 1Gain" in blocks[0].text
    assert "Example 2Loss" in blocks[1].text


@pytest.mark.m8
def test_mine_examples_command_with_mocked_client_freezes_confirmed_fixture(tmp_path, capsys):
    root = _make_project(tmp_path)
    client = FakeExampleClient()

    exit_code = verify_mine_examples_command(
        doc="instructions_form_8949_2025",
        year="2025",
        root=root,
        client=client,
        confirm=True,
        limit=1,
        source="yaml",
    )

    captured = capsys.readouterr()
    fixture_dir = root / "examples" / "irs_examples" / "instructions_form_8949_2025" / "example_001"
    assert exit_code == 0
    assert "agreed: 1" in captured.out
    assert client.calls[0]["purpose"] == "tax_graph_example_miner"
    assert (fixture_dir / "facts.yaml").exists()
    assert (fixture_dir / "expected.yaml").exists()
    assert (fixture_dir / "provenance.yaml").exists()


@pytest.mark.m8
def test_committed_irs_example_fixture_replays_offline():
    report = replay_irs_examples(year="2025", root=ROOT, source="yaml")

    assert report.ok, report.issues
    assert report.example_count >= 1


@pytest.mark.m8
def test_replay_examples_command_reports_ok(capsys):
    exit_code = verify_replay_examples_command(year="2025", root=ROOT, source="yaml")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "IRS example replay" in captured.out
    assert "result: OK" in captured.out


def _make_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "config", root / "config")
    shutil.copyfile(
        root / "config" / "tax-graph.config.example.yaml",
        root / "config" / "tax-graph.config.yaml",
    )  # hermetic: never inherit the developer's gitignored local config
    shutil.copytree(ROOT / "schemas", root / "schemas")
    shutil.copytree(ROOT / "graph", root / "graph")
    raw_dir = root / ".cache" / "raw" / "2025"
    raw_dir.mkdir(parents=True)
    (raw_dir / "instructions_form_8949_2025.txt").write_text(
        "**Example 1Gain.** Column (d) is $6,000 and column (e) is $2,000. Enter $4,000 in column (h).\n",
        encoding="utf-8",
    )
    pages_dir = raw_dir / "instructions_form_8949_2025.pages"
    pages_dir.mkdir()
    (pages_dir / "page-001.md").write_text("Example text\n", encoding="utf-8")
    (raw_dir / "instructions_form_8949_2025.links.json").write_text("[]\n", encoding="utf-8")
    return root
