"""M15 A8 document-navigation projection tests."""

from __future__ import annotations

import pytest

from workbench.navigation import build_document_navigation


pytestmark = pytest.mark.m15


def test_document_projection_is_independent_of_queue_order() -> None:
    entries = [
        _entry("queue_b", "computed", "unit_b", 2),
        _entry("queue_a", "user_entered", "unit_a", 1),
    ]
    documents = [{"document_id": "form_x", "title": "Form X"}]

    forward = build_document_navigation(entries, documents)
    reverse = build_document_navigation(reversed(entries), documents)

    assert forward == reverse
    assert forward[0]["title"] == "Form X"
    assert [group["label"] for group in forward[0]["check_groups"]] == [
        "Identity and filer inputs", "Calculations",
    ]
    assert forward[0]["pages"] == [1, 2]


def _entry(queue_id: str, policy: str, unit_id: str, page: int) -> dict:
    return {
        "queue_id": queue_id,
        "review_kind": "field_map_review",
        "units": [{
            "queue_id": queue_id,
            "unit_id": unit_id,
            "required": True,
            "field_policy": policy,
            "semantic_class": "input" if policy == "user_entered" else "calculation",
            "official_location": {"document_id": "form_x", "page": page},
            "object_refs": [],
        }],
    }
