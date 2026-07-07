from __future__ import annotations

import shutil
from pathlib import Path
import re

import pytest
import yaml
from jsonschema import validate

from tax_graph.extract.checks import run_deterministic_checks
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.models import CheckIssue, DeterministicReport
from tax_graph.extract.outline_pipeline import generate_outline_first_drafts
from tax_graph.extract.route import route_drafts, write_routed_drafts
from tax_graph.verify.metrics import build_metrics


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_RAW = ROOT / "tests" / "fixtures" / "schedule_d_bundle" / "raw"


class ScheduleDMicroClient:
    def __init__(self):
        self.prompts: list[str] = []

    def structured_completion(self, *, prompt, schema, model, max_tokens, temperature, purpose):
        self.prompts.append(prompt)
        span_id = re.search(r"- (span_[a-z0-9_]+):", prompt).group(1)
        return {
            "operation_plan": [
                {
                    "output": "column_h",
                    "operation": "SUM",
                    "inputs": [
                        {"name": "column_d", "role": "addend"},
                        {"name": "column_e", "role": "addend"},
                        {"name": "column_g", "role": "addend"},
                    ],
                    "citation_span_ids": [span_id],
                }
            ]
        }


@pytest.mark.m9
def test_schedule_d_outline_first_fixture_routes_and_writes_metrics(tmp_path):
    root = _copy_project(tmp_path)
    document = load_document_input("schedule_d_2025", year="2025", root=root, raw_store=FIXTURE_RAW)
    batch = generate_outline_first_drafts(
        document,
        client=ScheduleDMicroClient(),
        config={"llm": {"model": "mock-schedule-d"}},
        root=root,
    )
    batch.objects[0].flag("field grid: unmapped Schedule D line 18")
    report = run_deterministic_checks(document, batch, root=root)
    routed = route_drafts(batch, report, config={"extraction": {"require_critic_agreement": False}})
    written = write_routed_drafts(batch, routed, root=root, document=document)
    metrics = yaml.safe_load((written.output_dir / "metrics.yaml").read_text(encoding="utf-8"))

    assert report.issues == []
    assert written.output_dir.name == "schedule_d_2025"
    assert metrics["document_id"] == "schedule_d_2025"
    assert metrics["routing"]["review"] > 0
    assert metrics["human_minutes"] is None
    assert metrics["objects_by_kind"]["documents"] == 1
    assert metrics["objects_by_kind"]["tables"] == 2
    assert metrics["flags_by_layer"]["field_grid"] == 1
    assert (written.output_dir / "documents.yaml").exists()
    assert (written.output_dir / "review.html").exists()


@pytest.mark.m9
def test_schedule_d_fixture_drafts_include_schema_valid_band_tables(tmp_path):
    root = _copy_project(tmp_path)
    document = load_document_input("schedule_d_2025", year="2025", root=root, raw_store=FIXTURE_RAW)
    client = ScheduleDMicroClient()
    batch = generate_outline_first_drafts(
        document,
        client=client,
        config={"llm": {"model": "mock-schedule-d"}},
        root=root,
    )
    table_schema = yaml.safe_load((ROOT / "schemas" / "table.schema.json").read_text(encoding="utf-8"))
    tables = [obj.data for obj in batch.items("tables")]
    table_ids = {table["table_id"] for table in tables}

    assert table_ids == {
        "schedule_d_2025_part_i_lines_1b_3",
        "schedule_d_2025_part_ii_lines_8b_10",
    }
    for table in tables:
        validate(table, table_schema)
        assert [column["column_id"] for column in table["columns"]] == ["d", "e", "g", "h"]
        assert table["totals"][0]["column_id"] == "h"
    assert client.prompts == []


@pytest.mark.m9
def test_schedule_d_unmapped_field_flags_review(tmp_path):
    root = _copy_project(tmp_path)
    document = load_document_input("schedule_d_2025", year="2025", root=root, raw_store=FIXTURE_RAW)
    batch = generate_outline_first_drafts(
        document,
        client=ScheduleDMicroClient(),
        config={"llm": {"model": "mock-schedule-d"}},
        root=root,
    )
    batch.objects[0].flag("field grid: unmapped Schedule D line 18")
    routed = route_drafts(
        batch,
        DeterministicReport(
            issues=[CheckIssue("document", "schedule_d_2025", "field grid: unmapped Schedule D line 18")]
        ),
        config={"extraction": {"require_critic_agreement": False}},
    )
    metrics = build_metrics(batch, routed)

    assert routed.review
    assert metrics["flags_by_layer"]["field_grid"] == 2


def _copy_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "config", root / "config")
    shutil.copyfile(
        root / "config" / "tax-graph.config.example.yaml",
        root / "config" / "tax-graph.config.yaml",
    )
    shutil.copytree(ROOT / "schemas", root / "schemas")
    shutil.copytree(ROOT / "graph", root / "graph", ignore=shutil.ignore_patterns("_drafts"))
    return root
