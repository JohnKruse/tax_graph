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


class GenericBatchClient:
    def __init__(self):
        self.calls: list[dict[str, str]] = []

    def structured_completion(self, *, prompt, schema, model, max_tokens, temperature, purpose):
        self.calls.append({"model": model, "purpose": purpose, "prompt": prompt})
        outline_id_match = re.search(r"outline_id: ([^\n]+)", prompt)
        columns_match = re.search(r"columns: \[(.*?)\]", prompt)
        span_ids = re.findall(r"- (span_[a-z0-9_]+):", prompt)
        span_id = span_ids[0] if span_ids else ""
        if not outline_id_match or not columns_match:
            return {"operation_plan": [{"output": "column_a", "operation": "COPY", "inputs": [{"name": "column_a"}], "citation_span_ids": [span_id] if span_id else []}]}
        outline_id = outline_id_match.group(1)
        line_anchor = re.search(r"line_([0-9]+[a-z]?)$", outline_id).group(1)
        previous_line = str(max(int(re.sub(r"[^0-9]", "", line_anchor) or "1") - 1, 1))
        columns = re.findall(r"'([a-z])'", columns_match.group(1))
        if "kind: totals" in prompt:
            return {
                "operation_plan": [
                    {
                        "output": f"line_{line_anchor}_column_{column}_total",
                        "operation": "SUM",
                        "inputs": [{"name": f"line_{previous_line}_column_{column}", "role": "addend"}],
                        "citation_span_ids": [span_id] if span_id else [],
                    }
                    for column in columns
                ]
            }
        if {"d", "e", "g", "h"}.issubset(set(columns)):
            return {
                "operation_plan": [
                    {
                        "output": "column_d_minus_e",
                        "operation": "SUBTRACT",
                        "inputs": [
                            {"name": "column_d", "role": "minuend"},
                            {"name": "column_e", "role": "subtrahend"},
                        ],
                        "citation_span_ids": [span_id] if span_id else [],
                    },
                    {
                        "output": "column_h",
                        "operation": "SUM",
                        "inputs": [
                            {"name": "column_d_minus_e", "role": "addend"},
                            {"name": "column_g", "role": "addend"},
                        ],
                        "citation_span_ids": [span_id] if span_id else [],
                    },
                ]
            }
        first = columns[0] if columns else "a"
        return {
            "operation_plan": [
                {
                    "output": f"column_{first}",
                    "operation": "COPY",
                    "inputs": [{"name": f"column_{first}"}],
                    "citation_span_ids": [span_id] if span_id else [],
                }
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


@pytest.mark.m10
def test_extract_year_full_batch_writes_partial_document_records(tmp_path):
    root = _make_batch_project(tmp_path, manifest_docs=_default_manifest_docs())
    primary = GenericBatchClient()
    secondary = GenericBatchClient()

    routed = extract_year(
        year="2025",
        root=root,
        client=primary,
        secondary_client=secondary,
        config={
            "project": {"paths": {"graph_dir": "graph", "raw_store": ".cache/raw"}},
            "extraction": {
                "mode": "outline_first",
                "max_docs_per_run": 20,
                "example_mining_limit": 10,
                "require_critic_agreement": False,
            },
            "llm": {
                "model": "family-a/mock",
                "micro_model": "family-a/mock-micro",
                "nversion_model": "family-b/mock-micro",
                "temperature": 0,
            },
        },
    )

    assert [item.output_dir.name for item in routed] == [
        "schedule_1_2025",
        "schedule_1a_2025",
        "schedule_2_2025",
        "schedule_3_2025",
        "schedule_a_2025",
        "schedule_b_2025",
        "form_6251_2025",
    ]
    for document_id in [item.output_dir.name for item in routed]:
        draft_dir = root / "graph" / "2025" / "_drafts" / document_id
        metrics = yaml.safe_load((draft_dir / "metrics.yaml").read_text(encoding="utf-8"))
        nversion = yaml.safe_load((draft_dir / "nversion.yaml").read_text(encoding="utf-8"))
        example_mining = yaml.safe_load((draft_dir / "example_mining.yaml").read_text(encoding="utf-8"))
        documents = yaml.safe_load((draft_dir / "documents.yaml").read_text(encoding="utf-8"))

        assert metrics["nversion"]["ran"] is True
        assert nversion["status"] == "agreed"
        assert example_mining["ran"] is True
        assert documents[0]["document_id"] == document_id
        assert documents[0]["status"] == "partial"

    schedule_1_doc = yaml.safe_load(
        (root / "graph" / "2025" / "_drafts" / "schedule_1_2025" / "documents.yaml").read_text(encoding="utf-8")
    )[0]
    schedule_1_nodes = yaml.safe_load(
        (root / "graph" / "2025" / "_drafts" / "schedule_1_2025" / "nodes.yaml").read_text(encoding="utf-8")
    )
    schedule_2_doc = yaml.safe_load(
        (root / "graph" / "2025" / "_drafts" / "schedule_2_2025" / "documents.yaml").read_text(encoding="utf-8")
    )[0]
    schedule_2_nodes = yaml.safe_load(
        (root / "graph" / "2025" / "_drafts" / "schedule_2_2025" / "nodes.yaml").read_text(encoding="utf-8")
    )
    schedule_3_doc = yaml.safe_load(
        (root / "graph" / "2025" / "_drafts" / "schedule_3_2025" / "documents.yaml").read_text(encoding="utf-8")
    )[0]
    schedule_3_nodes = yaml.safe_load(
        (root / "graph" / "2025" / "_drafts" / "schedule_3_2025" / "nodes.yaml").read_text(encoding="utf-8")
    )
    schedule_b_doc = yaml.safe_load(
        (root / "graph" / "2025" / "_drafts" / "schedule_b_2025" / "documents.yaml").read_text(encoding="utf-8")
    )[0]
    schedule_b_nodes = yaml.safe_load(
        (root / "graph" / "2025" / "_drafts" / "schedule_b_2025" / "nodes.yaml").read_text(encoding="utf-8")
    )
    schedule_1_node_ids = {item["node_id"] for item in schedule_1_nodes}
    schedule_2_node_ids = {item["node_id"] for item in schedule_2_nodes}
    schedule_3_node_ids = {item["node_id"] for item in schedule_3_nodes}
    schedule_b_node_ids = {item["node_id"] for item in schedule_b_nodes}

    assert schedule_1_doc["not_modeled_fields"] == []
    assert "schedule_1_2025_part_i_line_1" in schedule_1_node_ids
    assert "schedule_1_2025_part_i_line_8z_amount" in schedule_1_node_ids
    assert "schedule_1_2025_part_i_line_8z_description" in schedule_1_node_ids
    assert "schedule_1_2025_part_i_line_9" in schedule_1_node_ids
    assert "schedule_1_2025_part_ii_line_11" in schedule_1_node_ids
    assert "schedule_1_2025_part_ii_line_24z_amount" in schedule_1_node_ids
    assert "schedule_1_2025_part_ii_line_24z_description" in schedule_1_node_ids
    assert "schedule_1_2025_part_ii_line_25" in schedule_1_node_ids
    assert schedule_2_doc["not_modeled_fields"] == []
    assert "schedule_2_2025_part_ii_line_17z_amount" in schedule_2_node_ids
    assert "schedule_2_2025_part_ii_line_17z_description" in schedule_2_node_ids
    assert schedule_3_doc["not_modeled_fields"] == []
    assert "schedule_3_2025_part_i_line_6z_amount" in schedule_3_node_ids
    assert "schedule_3_2025_part_i_line_6z_description" in schedule_3_node_ids
    assert "schedule_3_2025_part_ii_line_13z_amount" in schedule_3_node_ids
    assert "schedule_3_2025_part_ii_line_13z_description" in schedule_3_node_ids
    assert {item["line_anchor"] for item in schedule_b_doc["not_modeled_fields"]} == {"7", "8"}
    assert "schedule_b_2025_part_i_line_3" in schedule_b_node_ids
    assert "schedule_b_2025_part_i_line_4" in schedule_b_node_ids
    assert "schedule_b_2025_part_iii_line_9" in schedule_b_node_ids
    assert "schedule_b_2025_part_iii_line_10" in schedule_b_node_ids
    assert primary.calls
    assert secondary.calls


def _make_batch_project(tmp_path: Path, *, manifest_docs: list[dict[str, str]] | None = None) -> Path:
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
                "documents": manifest_docs
                or [
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


def _default_manifest_docs() -> list[dict[str, str]]:
    return [
        {
            "document_id": "schedule_1_2025",
            "kind": "schedule",
            "url": "https://www.irs.gov/pub/irs-prior/f1040s1--2025.pdf",
            "instructions_document_id": "instructions_form_1040_2025",
        },
        {
            "document_id": "schedule_1a_2025",
            "kind": "schedule",
            "url": "https://www.irs.gov/pub/irs-prior/f1040s1a--2025.pdf",
            "instructions_document_id": "instructions_form_1040_2025",
        },
        {
            "document_id": "schedule_2_2025",
            "kind": "schedule",
            "url": "https://www.irs.gov/pub/irs-prior/f1040s2--2025.pdf",
            "instructions_document_id": "instructions_form_1040_2025",
        },
        {
            "document_id": "schedule_3_2025",
            "kind": "schedule",
            "url": "https://www.irs.gov/pub/irs-prior/f1040s3--2025.pdf",
            "instructions_document_id": "instructions_form_1040_2025",
        },
        {
            "document_id": "schedule_a_2025",
            "kind": "schedule",
            "url": "https://www.irs.gov/pub/irs-prior/f1040sa--2025.pdf",
            "instructions_document_id": "instructions_schedule_a_2025",
        },
        {
            "document_id": "schedule_b_2025",
            "kind": "schedule",
            "url": "https://www.irs.gov/pub/irs-prior/f1040sb--2025.pdf",
            "instructions_document_id": "instructions_schedule_b_2025",
        },
        {
            "document_id": "form_6251_2025",
            "kind": "tax_form",
            "url": "https://www.irs.gov/pub/irs-prior/f6251--2025.pdf",
            "instructions_document_id": "instructions_form_6251_2025",
        },
        {
            "document_id": "instructions_form_1040_2025",
            "kind": "instructions",
            "url": "https://www.irs.gov/pub/irs-prior/i1040gi--2025.pdf",
        },
        {
            "document_id": "instructions_schedule_a_2025",
            "kind": "instructions",
            "url": "https://www.irs.gov/pub/irs-prior/i1040sca--2025.pdf",
        },
        {
            "document_id": "instructions_schedule_b_2025",
            "kind": "instructions",
            "url": "https://www.irs.gov/pub/irs-prior/i1040sb--2025.pdf",
        },
        {
            "document_id": "instructions_form_6251_2025",
            "kind": "instructions",
            "url": "https://www.irs.gov/pub/irs-prior/i6251--2025.pdf",
        },
    ]
