from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from tax_graph.promote import promote_draft_document
from tax_graph.review_queue import upsert_deferred_review_entry


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.m10
def test_promote_draft_document_copies_live_yaml_with_document_override(tmp_path):
    root = tmp_path / "project"
    shutil.copytree(ROOT / "graph", root / "graph")

    result = promote_draft_document(
        "schedule_1_2025",
        root=root,
        documents_override={"title": "Schedule 1 (Form 1040)"},
    )

    document_path = root / "graph" / "2025" / "documents" / "schedule-1.yaml"
    nodes_path = root / "graph" / "2025" / "nodes" / "schedule-1.yaml"
    citations_path = root / "graph" / "2025" / "citations" / "schedule-1.yaml"

    assert result.paths["documents"] == document_path
    assert result.paths["nodes"] == nodes_path
    assert result.paths["citations"] == citations_path
    assert yaml.safe_load(document_path.read_text(encoding="utf-8"))["title"] == "Schedule 1 (Form 1040)"
    assert yaml.safe_load(nodes_path.read_text(encoding="utf-8"))[0]["document_id"] == "schedule_1_2025"
    assert yaml.safe_load(citations_path.read_text(encoding="utf-8"))[0]["document_id"] == "schedule_1_2025"


@pytest.mark.m10
def test_upsert_deferred_review_entry_replaces_same_queue_id(tmp_path):
    root = tmp_path / "project"

    first = upsert_deferred_review_entry(
        root=root,
        year="2025",
        entry={
            "queue_id": "promotion_review_schedule_1_2025",
            "kind": "promotion_review",
            "status": "pending",
            "priority": "medium",
            "document_id": "schedule_1_2025",
            "created_date": "2026-07-08",
            "created_by": "tax_graph.promote",
            "summary": "First summary",
        },
    )
    second = upsert_deferred_review_entry(
        root=root,
        year="2025",
        entry={
            "queue_id": "promotion_review_schedule_1_2025",
            "kind": "promotion_review",
            "status": "pending",
            "priority": "high",
            "document_id": "schedule_1_2025",
            "created_date": "2026-07-08",
            "created_by": "tax_graph.promote",
            "summary": "Updated summary",
            "artifact_paths": ["graph/2025/documents/schedule-1.yaml"],
        },
    )

    payload = yaml.safe_load(first.read_text(encoding="utf-8"))
    assert first == second
    assert payload["tax_year"] == 2025
    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["priority"] == "high"
    assert payload["entries"][0]["summary"] == "Updated summary"
