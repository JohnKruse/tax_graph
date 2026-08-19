"""M20-S145 guards for projection of instruction evidence on background cells."""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from workbench.generated_review import (
    GENERATED_REVIEW_DOCUMENTS,
    build_generated_document_cells,
)


ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    not (ROOT / "graph" / "2025" / "_drafts").exists(),
    reason="live review drafts are required: fresh checkouts carry no _drafts",
)


@pytest.mark.m20
def test_live_generated_review_has_no_line_label_only_instruction_citation() -> None:
    """Every live generated cell must carry explanatory instruction evidence."""
    label_only = re.compile(
        r"\s*Line\s+[0-9]+[a-z]?\.\s*",
        re.IGNORECASE,
    )

    for document_id in sorted(GENERATED_REVIEW_DOCUMENTS):
        cells = build_generated_document_cells(ROOT, 2025, document_id).cells
        for cell in cells:
            for citation in cell.get("instruction_citations") or []:
                quoted_text = citation.get("quoted_text")
                assert not label_only.fullmatch(str(quoted_text or "")), (
                    f"{document_id} {cell.get('field_name')}: "
                    f"line-label-only instruction citation "
                    f"{citation.get('citation_id')}"
                )
