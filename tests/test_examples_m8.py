from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tax_graph.cli import verify_mine_examples_command, verify_replay_examples_command
from tax_graph.verify.examples import mine_examples, replay_irs_examples, segment_example_blocks


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
                "filing_status": "single",
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


class FailingExampleClient:
    def structured_completion(self, *, prompt, schema, model, max_tokens, temperature, purpose):
        raise RuntimeError("provider down")


class UnsupportedStructuredOutputClient:
    def structured_completion(self, *, prompt, schema, model, max_tokens, temperature, purpose):
        raise RuntimeError("OpenRouter endpoint does not support JSON-schema structured outputs; choose a structured-output-capable endpoint or adjust llm.require_parameters")


class RuntimeRowShorthandClient:
    def structured_completion(self, *, prompt, schema, model, max_tokens, temperature, purpose):
        return {
            "facts": {
                "filing_status": "single",
                "row_key": "example_1_gain",
                "inputs": {"column_d": 6000, "column_e": 2000},
            },
            "expected": {
                "form_8949_2025_part_ii_line_1_column_d#example_1_gain": 6000,
                "form_8949_2025_part_ii_line_1_column_e#example_1_gain": 2000,
                "form_8949_2025_part_ii_line_1_column_d_minus_e#example_1_gain": 4000,
                "form_8949_2025_part_ii_line_1_column_h#example_1_gain": 4000,
                "form_1040_2025_line_7_capital_gain_loss": 4000,
            },
        }


class StaticRowTemplateIdClient:
    def structured_completion(self, *, prompt, schema, model, max_tokens, temperature, purpose):
        return {
            "facts": {
                "filing_status": "single",
                "form": "8949",
                "part": "II",
                "line": "1",
                "scenario": "gain",
                "column_d": 6000,
                "column_e": 2000,
            },
            "expected": {
                "form_8949_2025_part_ii_line_1_column_d_minus_e": 4000,
                "form_8949_2025_part_ii_line_1_column_h": 4000,
                "form_1040_2025_line_7_capital_gain_loss": 4000,
            },
        }


class ScheduleDShorthandClient:
    def structured_completion(self, *, prompt, schema, model, max_tokens, temperature, purpose):
        return {
            "facts": {
                "filing_status": "single",
                "tax_form": "Form 8949",
                "part": "Part II (long-term)",
                "line": "line 1",
                "example_id": "section_1244",
                "proceeds": 1000,
                "basis": 60000,
                "ordinary_loss_claimed_on_form_4797": 50000,
            },
            "expected": {
                "form_8949_2025_part_ii_line_1_column_d": 1000,
                "form_8949_2025_part_ii_line_1_column_e": 60000,
                "form_8949_2025_part_ii_line_1_column_g": 50000,
                "form_8949_2025_part_ii_line_1_column_d_minus_e": -59000,
                "form_8949_2025_part_ii_line_1_column_h": -9000,
            },
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
    assert client.calls[0]["model"] == "configured-llm"
    assert (fixture_dir / "facts.yaml").exists()
    assert (fixture_dir / "expected.yaml").exists()
    assert (fixture_dir / "provenance.yaml").exists()
    expected = (fixture_dir / "expected.yaml").read_text(encoding="utf-8")
    provenance = (fixture_dir / "provenance.yaml").read_text(encoding="utf-8")
    assert "confirmed: true" in expected
    assert "human_confirmed: true" in provenance


@pytest.mark.m8
def test_mine_examples_command_freezes_machine_agreed_fixture_and_queue_entry(tmp_path, capsys):
    root = _make_project(tmp_path)
    client = FakeExampleClient()

    exit_code = verify_mine_examples_command(
        doc="instructions_form_8949_2025",
        year="2025",
        root=root,
        client=client,
        freeze_agreed=True,
        limit=1,
        source="yaml",
    )

    captured = capsys.readouterr()
    fixture_dir = root / "examples" / "irs_examples" / "instructions_form_8949_2025" / "example_001"
    queue_path = root / "review_queue" / "2025" / "deferred_review.yaml"
    assert exit_code == 0
    assert "review queue:" in captured.out
    assert queue_path.exists()
    expected = (fixture_dir / "expected.yaml").read_text(encoding="utf-8")
    provenance = (fixture_dir / "provenance.yaml").read_text(encoding="utf-8")
    queue = queue_path.read_text(encoding="utf-8")
    assert "confirmed: false" in expected
    assert "review_status: pending_human_review" in expected
    assert "human_confirmed: false" in provenance
    assert "machine_agreed: true" in provenance
    assert "kind: irs_example_review" in queue
    assert "status: pending" in queue


@pytest.mark.m8
def test_mine_examples_rejects_conflicting_freeze_modes(tmp_path):
    root = _make_project(tmp_path)

    with pytest.raises(ValueError, match="either confirm or freeze_agreed"):
        mine_examples(
            document_id="instructions_form_8949_2025",
            year="2025",
            root=root,
            client=FakeExampleClient(),
            config={"llm": {"model": "mock-model"}},
            confirm=True,
            freeze_agreed=True,
            limit=1,
            source="yaml",
        )


@pytest.mark.m8
def test_mine_examples_records_provider_failure_as_unmappable(tmp_path):
    root = _make_project(tmp_path)

    report = mine_examples(
        document_id="instructions_form_8949_2025",
        year="2025",
        root=root,
        client=FailingExampleClient(),
        config={"llm": {"model": "mock-model"}},
        limit=1,
        source="yaml",
    )

    assert report.agreed == 0
    assert report.unmappable == 1
    assert "example miner unavailable" in report.examples[0].mismatches[0]


@pytest.mark.m8
def test_mine_examples_records_actionable_structured_output_error(tmp_path):
    root = _make_project(tmp_path)

    report = mine_examples(
        document_id="instructions_form_8949_2025",
        year="2025",
        root=root,
        client=UnsupportedStructuredOutputClient(),
        config={"llm": {"provider": "openrouter", "require_parameters": "auto"}},
        limit=1,
        source="yaml",
    )

    assert report.unmappable == 1
    assert "structured-output-capable endpoint" in report.examples[0].mismatches[0]


@pytest.mark.m8
def test_mine_examples_normalizes_runtime_row_shorthand(tmp_path):
    root = _make_project(tmp_path)

    report = mine_examples(
        document_id="instructions_form_8949_2025",
        year="2025",
        root=root,
        client=RuntimeRowShorthandClient(),
        config={"llm": {"model": "mock-model"}},
        limit=1,
        source="yaml",
    )

    example = report.examples[0]
    assert report.agreed == 1, example.mismatches
    assert example.facts_document["tables"][0]["table_id"] == "form_8949_2025_part_ii_line_1"
    assert example.facts_document["tables"][0]["rows"][0]["row_key"] == "example_1_gain"
    assert example.facts_document["tables"][0]["rows"][0]["columns"] == {"d": 6000, "e": 2000, "g": 0}


@pytest.mark.m8
def test_mine_examples_rewrites_static_row_template_expected_ids(tmp_path):
    root = _make_project(tmp_path)

    report = mine_examples(
        document_id="instructions_form_8949_2025",
        year="2025",
        root=root,
        client=StaticRowTemplateIdClient(),
        config={"llm": {"model": "mock-model"}},
        limit=1,
        source="yaml",
    )

    example = report.examples[0]
    assert report.agreed == 1, example.mismatches
    assert "form_8949_2025_part_ii_line_1_column_h#example_001_gain" in example.expected
    assert "form_8949_2025_part_ii_line_1_column_h" not in example.expected


@pytest.mark.m8
def test_mine_examples_maps_schedule_d_shorthand_aliases_into_table_rows(tmp_path):
    root = _make_project(tmp_path)

    report = mine_examples(
        document_id="instructions_form_8949_2025",
        year="2025",
        root=root,
        client=ScheduleDShorthandClient(),
        config={"llm": {"model": "mock-model"}},
        limit=1,
        source="yaml",
    )

    example = report.examples[0]
    assert report.agreed == 1, example.mismatches
    assert example.facts_document["tables"][0]["rows"][0]["columns"] == {"d": 1000, "e": 60000, "g": 50000}
    assert "form_8949_2025_part_ii_line_1_column_h#section_1244" in example.expected


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
