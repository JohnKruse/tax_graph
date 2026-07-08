from __future__ import annotations

import json
from pathlib import Path
import re
import shutil

import jsonschema
import pytest
import yaml

from tax_graph.extract.pipeline import extract_year


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_RAW = ROOT / "tests" / "fixtures" / "m10_batch_bundle" / "raw"


class ScheduleBFormulaClient:
    def __init__(self):
        self.calls: list[dict[str, str]] = []

    def structured_completion(self, *, prompt, schema, model, max_tokens, temperature, purpose):
        self.calls.append({"model": model, "purpose": purpose, "prompt": prompt})
        outline_id = re.search(r"outline_id: ([^\n]+)", prompt).group(1)
        line_anchor = re.search(r"line_([0-9]+[a-z]?)$", outline_id).group(1)
        columns = re.findall(r"'([a-z])'", re.search(r"columns: \[(.*?)\]", prompt).group(1))
        span_ids = re.findall(r"- (span_[a-z0-9_]+):", prompt)
        span_id = span_ids[0] if span_ids else ""
        return {
            "operation_plan": [
                {
                    "output": f"line_{line_anchor}_column_{column}_total",
                    "operation": "SUM",
                    "inputs": [{"name": f"line_{int(line_anchor) - 1}_column_{column}", "role": "addend"}],
                    "citation_span_ids": [span_id] if span_id else [],
                }
                for column in columns
            ]
        }


@pytest.mark.m10
def test_extract_year_writes_batch_sidecars_and_schedule_b_table_fixture(tmp_path):
    root = _make_batch_project(tmp_path)
    primary = ScheduleBFormulaClient()
    secondary = ScheduleBFormulaClient()

    routed = extract_year(
        year="2025",
        root=root,
        client=primary,
        secondary_client=secondary,
        config={
            "project": {"paths": {"graph_dir": "graph", "raw_store": ".cache/raw"}},
            "extraction": {
                "mode": "outline_first",
                "max_docs_per_run": 1,
                "example_mining_limit": 10,
                "require_critic_agreement": False,
            },
            "llm": {
                "model": "family-a/mock",
                "micro_model": "family-a/mock-micro",
                "nversion_model": "family-b/mock-micro",
                "vendor_family": "family-a",
                "nversion_vendor_family": "family-b",
                "temperature": 0,
            },
        },
    )

    assert len(routed) == 1
    draft_dir = root / "graph" / "2025" / "_drafts" / "schedule_b_2025"
    metrics = yaml.safe_load((draft_dir / "metrics.yaml").read_text(encoding="utf-8"))
    nversion = yaml.safe_load((draft_dir / "nversion.yaml").read_text(encoding="utf-8"))
    example_mining = yaml.safe_load((draft_dir / "example_mining.yaml").read_text(encoding="utf-8"))
    tables = yaml.safe_load((draft_dir / "tables.yaml").read_text(encoding="utf-8"))
    table_schema = json.loads((root / "schemas" / "table.schema.json").read_text(encoding="utf-8"))

    assert nversion["ran"] is True
    assert nversion["status"] == "agreed"
    assert nversion["diffs"] == 0
    assert metrics["nversion"]["status"] == "agreed"
    assert metrics["example_mining"] == {
        "ran": True,
        "examples": 0,
        "agreed": 0,
        "disagreed": 0,
        "unmappable": 0,
    }
    assert example_mining["document_id"] == "schedule_b_2025"
    assert example_mining["examples"] == 0
    assert example_mining["items"] == []
    assert {table["table_id"] for table in tables} == {
        "schedule_b_2025_part_i_line_1",
        "schedule_b_2025_part_ii_line_5",
    }
    for table in tables:
        jsonschema.validate(table, table_schema)
    assert any(total["column_id"] == "b" for total in tables[0]["totals"])
    assert primary.calls
    assert secondary.calls


def _make_batch_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "config", root / "config")
    shutil.copyfile(
        root / "config" / "tax-graph.config.example.yaml",
        root / "config" / "tax-graph.config.yaml",
    )
    shutil.copytree(ROOT / "schemas", root / "schemas")
    shutil.copytree(ROOT / "graph", root / "graph", ignore=shutil.ignore_patterns("_drafts"))
    raw_dir = root / ".cache" / "raw" / "2025"
    raw_dir.mkdir(parents=True)
    for path in (FIXTURE_RAW / "2025").iterdir():
        target = raw_dir / path.name
        if path.is_dir():
            shutil.copytree(path, target)
        else:
            shutil.copyfile(path, target)
    (root / "config" / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "tax_year": 2025,
                "documents": [
                    {
                        "document_id": "schedule_b_2025",
                        "kind": "schedule",
                        "url": "https://www.irs.gov/pub/irs-prior/f1040sb--2025.pdf",
                        "instructions_document_id": "instructions_schedule_b_2025",
                    },
                    {
                        "document_id": "instructions_schedule_b_2025",
                        "kind": "instructions",
                        "url": "https://www.irs.gov/pub/irs-prior/i1040sb--2025.pdf",
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
        newline="\n",
    )
    return root
