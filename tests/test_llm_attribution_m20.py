from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tax_graph.extract.generator import parse_generator_response
from tax_graph.extract.llm_client import StructuredCompletionResult
from tax_graph.extract.models import DraftObject, ExtractionBatch, LlmCallTelemetry, RoutedDrafts, SourceDocumentInput
from tax_graph.extract.route import write_routed_drafts


pytestmark = pytest.mark.m20


def _document(tmp_path: Path) -> SourceDocumentInput:
    text_path = tmp_path / "form_1040_2025.txt"
    text_path.write_text("# Page 1\n- 1: Wages\n", encoding="ascii")
    return SourceDocumentInput(
        document_id="form_1040_2025",
        kind="tax_form",
        year="2025",
        url="https://example.test/form-1040.pdf",
        text=text_path.read_text(encoding="ascii"),
        text_path=text_path,
    )


def _response() -> StructuredCompletionResult:
    payload = {
        "nodes": [
            {
                "node_id": "form_1040_2025_line_1",
                "document_id": "form_1040_2025",
                "label": "Wages",
                "node_type": "form_line",
            }
        ],
        "edges": [],
        "rules": [],
        "citations": [],
        "decisions": [],
        "tables": [],
        "provenance": [],
    }
    return StructuredCompletionResult(
        payload,
        LlmCallTelemetry(
            provider="OpenRouter",
            requested_model="~google/gemini-flash-latest",
            resolved_model="z-ai/glm-5.2",
            prompt_tokens=13,
            completion_tokens=5,
            total_tokens=18,
            cost=0.01,
        ),
    )


def test_generator_provenance_uses_resolved_model_and_records_call(tmp_path: Path):
    document = _document(tmp_path)
    batch = parse_generator_response(
        _response(),
        document=document,
        model="~google/gemini-flash-latest",
    )

    assert batch.items("nodes")[0].extracted_by == "z-ai/glm-5.2"
    assert batch.items("nodes")[0].requested_model == "~google/gemini-flash-latest"
    assert batch.items("nodes")[0].resolved_model == "z-ai/glm-5.2"
    assert batch.llm_calls[0].total_tokens == 18


def test_draft_metrics_and_provenance_record_resolved_call(tmp_path: Path):
    batch = ExtractionBatch(
        document_id="form_1040_2025",
        year="2025",
        objects=[
            DraftObject(
                "nodes",
                {"node_id": "form_1040_2025_line_1", "document_id": "form_1040_2025"},
                "Wages",
                "z-ai/glm-5.2",
                1.0,
                requested_model="~google/gemini-flash-latest",
                resolved_model="z-ai/glm-5.2",
            )
        ],
        llm_calls=[_response().metadata],
    )
    routed = RoutedDrafts(accepted=batch.objects, review=[], issues=[])

    written = write_routed_drafts(batch, routed, root=tmp_path)
    metrics = yaml.safe_load((written.output_dir / "metrics.yaml").read_text(encoding="ascii"))
    provenance = yaml.safe_load((written.output_dir / "provenance.yaml").read_text(encoding="ascii"))

    assert metrics["worker_tokens"] == 18
    assert metrics["worker_cost"] == 0.01
    assert metrics["llm_calls"][0]["resolved_model"] == "z-ai/glm-5.2"
    assert provenance[0]["requested_model"] == "~google/gemini-flash-latest"
    assert provenance[0]["resolved_model"] == "z-ai/glm-5.2"
