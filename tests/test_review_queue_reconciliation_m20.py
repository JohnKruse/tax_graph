"""Fail-closed generated-review queue reconciliation for M20 S3a-2."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from tax_graph.review_queue import reconcile_generated_review_queue


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.m20


def _write_yaml(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
        newline="\n",
    )


def _queue(refs: list[dict[str, object]]) -> dict[str, object]:
    return {
        "tax_year": 2025,
        "entries": [
            {
                "queue_id": "promotion_review_form_test_2025",
                "kind": "promotion_review",
                "status": "pending",
                "priority": "high",
                "document_id": "form_test_2025",
                "created_date": "2026-07-29",
                "created_by": "tax_graph.test",
                "summary": "Review regenerated form extraction.",
                "review_scope": {
                    "scope_version": 1,
                    "scope_type": "promotion",
                    "object_refs": refs,
                },
            }
        ],
    }


def _ref(object_type: str, object_id: str) -> dict[str, object]:
    return {
        "object_type": object_type,
        "object_id": object_id,
        "source_path": "graph/2025/_drafts/form_test_2025/review.md",
        "role": "primary",
    }


def _write_root(
    root: Path,
    *,
    queue_refs: list[dict[str, object]],
    live_nodes: list[dict[str, object]],
    live_citations: list[dict[str, object]],
    draft_nodes: list[dict[str, object]],
    draft_citations: list[dict[str, object]],
) -> Path:
    queue_path = root / "review_queue" / "2025" / "deferred_review.yaml"
    _write_yaml(queue_path, _queue(queue_refs))
    _write_yaml(root / "graph" / "2025" / "nodes" / "form-test.yaml", live_nodes)
    _write_yaml(root / "graph" / "2025" / "citations" / "form-test.yaml", live_citations)
    draft_dir = root / "graph" / "2025" / "_drafts" / "form_test_2025"
    _write_yaml(draft_dir / "nodes.yaml", draft_nodes)
    _write_yaml(draft_dir / "citations.yaml", draft_citations)
    (draft_dir / "review.md").write_text("# Test review\n", encoding="utf-8", newline="\n")
    return queue_path


def test_unique_evidence_match_moves_refs_records_aliases_and_is_idempotent(tmp_path: Path) -> None:
    evidence = "Alpha beta amount from the official source"
    queue_path = _write_root(
        tmp_path,
        queue_refs=[_ref("citation", "cite_old"), _ref("node", "node_old")],
        live_nodes=[
            {
                "node_id": "node_old",
                "document_id": "form_test_2025",
                "label": f"Line 1a: {evidence}",
                "citation_refs": ["cite_old"],
            }
        ],
        live_citations=[
            {
                "citation_id": "cite_old",
                "document_id": "form_test_2025",
                "source_document_id": "form_test_2025",
                "locator": "page 1, line 4",
                "quoted_text": evidence,
            }
        ],
        draft_nodes=[
            {
                "node_id": "node_new",
                "document_id": "form_test_2025",
                "label": f"Line 1a: 1a {evidence} 1a",
                "citation_refs": ["cite_new"],
            }
        ],
        draft_citations=[
            {
                "citation_id": "cite_new",
                "document_id": "form_test_2025",
                "locator": "page 1, line 10",
                "quoted_text": f"1a {evidence} 1a",
            }
        ],
    )

    first = reconcile_generated_review_queue(root=tmp_path, year=2025)
    payload = yaml.safe_load(queue_path.read_text(encoding="utf-8"))
    refs = payload["entries"][0]["review_scope"]["object_refs"]

    assert first.migrated == 2
    assert first.orphaned == 0
    assert [(ref["object_type"], ref["object_id"]) for ref in refs] == [
        ("citation", "cite_new"),
        ("node", "node_new"),
    ]
    assert refs[0]["aliases"] == ["cite_old"]
    assert refs[1]["aliases"] == ["node_old"]
    assert payload["orphaned"] == []

    before = queue_path.read_bytes()
    second = reconcile_generated_review_queue(root=tmp_path, year=2025)
    assert second.migrated == 2
    assert second.orphaned == 0
    assert queue_path.read_bytes() == before


def test_changed_ambiguous_and_missing_evidence_stays_orphaned(tmp_path: Path) -> None:
    document_ref = {
        "object_type": "document",
        "object_id": "form_test_2025",
        "source_path": "graph/2025/documents.yaml",
        "role": "primary",
    }
    queue_path = _write_root(
        tmp_path,
        queue_refs=[
            document_ref,
            _ref("citation", "cite_changed"),
            _ref("node", "node_changed"),
            _ref("citation", "cite_ambiguous"),
            _ref("citation", "cite_missing_source"),
            _ref("citation", "cite_no_match"),
            _ref("citation", "cite_short"),
            _ref("citation", "cite_wrong_anchor"),
        ],
        live_nodes=[
            {
                "node_id": "node_changed",
                "document_id": "form_test_2025",
                "label": "Line 1a: Changed evidence node",
                "citation_refs": ["cite_changed"],
            }
        ],
        live_citations=[
            {
                "citation_id": "cite_changed",
                "document_id": "form_test_2025",
                "source_document_id": "form_test_2025",
                "locator": "page 1, line 4",
                "quoted_text": "Original changed evidence text",
            },
            {
                "citation_id": "cite_ambiguous",
                "document_id": "form_test_2025",
                "locator": "page 1, line 5",
                "quoted_text": "Common long evidence phrase for matching",
            },
            {
                "citation_id": "cite_no_match",
                "document_id": "form_test_2025",
                "locator": "page 1, line 6",
                "quoted_text": "Evidence that disappeared from the settled draft",
            },
            {
                "citation_id": "cite_short",
                "document_id": "form_test_2025",
                "locator": "page 1, line 7",
                "quoted_text": "1a",
            },
            {
                "citation_id": "cite_wrong_anchor",
                "document_id": "form_test_2025",
                "locator": "page 1, line 8",
                "quoted_text": "Other taxes. List type and amount:",
            },
        ],
        draft_nodes=[
            {
                "node_id": "node_changed",
                "document_id": "form_test_2025",
                "label": "Line 1a: Changed evidence node",
                "citation_refs": ["cite_changed"],
            }
        ],
        draft_citations=[
            {
                "citation_id": "cite_changed",
                "document_id": "form_test_2025",
                "locator": "page 1, line 44",
                "quoted_text": "Different evidence now occupies this id",
            },
            {
                "citation_id": "candidate_a",
                "document_id": "form_test_2025",
                "locator": "page 1, line 9",
                "quoted_text": "A Common long evidence phrase for matching",
            },
            {
                "citation_id": "candidate_b",
                "document_id": "form_test_2025",
                "locator": "page 1, line 10",
                "quoted_text": "B Common long evidence phrase for matching",
            },
            {
                "citation_id": "cite_replacement",
                "document_id": "form_test_2025",
                "locator": "page 1, line 83",
                "quoted_text": "Other-from list in instructions. List type and amount:",
            },
        ],
    )

    result = reconcile_generated_review_queue(root=tmp_path, year=2025)
    payload = yaml.safe_load(queue_path.read_text(encoding="utf-8"))
    reasons = {item["original_ref"]["object_id"]: item["reason"] for item in payload["orphaned"]}

    assert result.migrated == 0
    assert result.orphaned == 7
    assert reasons == {
        "cite_changed": "same_id_reused_with_changed_citation_evidence",
        "node_changed": "supporting_citation_changed",
        "cite_ambiguous": "ambiguous_content_match",
        "cite_missing_source": "missing_old_source",
        "cite_no_match": "no_certain_content_match",
        "cite_short": "insufficient_evidence_for_unique_match",
        "cite_wrong_anchor": "no_certain_content_match",
    }
    assert payload["entries"][0]["review_scope"]["object_refs"] == [document_ref]
    assert all(item["status"] == "orphaned" for item in payload["orphaned"])
    assert not any(
        ref.get("aliases") == ["cite_wrong_anchor"]
        for ref in payload["entries"][0]["review_scope"]["object_refs"]
    )

    schema = json.loads(
        (ROOT / "schemas" / "deferred_review_queue.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(payload, schema)
