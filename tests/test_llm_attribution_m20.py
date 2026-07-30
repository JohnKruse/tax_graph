from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from tax_graph.extract.generator import parse_generator_response
from tax_graph.extract.llm_client import (
    ImplausiblePromptTokens,
    LlmResponseTruncated,
    OpenAILlmClient,
    StructuredCompletionResult,
)
from tax_graph.extract.models import DraftObject, ExtractionBatch, LlmCallTelemetry, RoutedDrafts, SourceDocumentInput
from tax_graph.extract.observability import extraction_run, llm_call_target
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
            resolved_provider="Decart",
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
    assert batch.llm_calls[0].resolved_provider == "Decart"


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
                    resolved_provider="Decart",
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
    assert metrics["llm_calls"][0]["resolved_provider"] == "Decart"
    assert provenance[0]["requested_model"] == "~google/gemini-flash-latest"
    assert provenance[0]["resolved_model"] == "z-ai/glm-5.2"
    assert provenance[0]["resolved_provider"] == "Decart"


def test_review_gaps_are_persisted_as_draft_sidecar(tmp_path: Path):
    batch = ExtractionBatch(
        document_id="form_1040_2025",
        year="2025",
        objects=[],
        micro_stats={
            "formula_cells": [
                {
                    "target_cell_id": "form_1040_2025_root_line_9",
                    "line_anchor": "9",
                    "status": "review_gap",
                    "review_gap": "unresolved source line",
                }
            ],
            "review_gaps": [
                {
                    "target_cell_id": "form_1040_2025_root_line_9",
                    "line_anchor": "9",
                    "status": "review_gap",
                    "review_gap": "unresolved source line",
                }
            ],
        },
    )
    routed = RoutedDrafts(accepted=[], review=[], issues=[])

    written = write_routed_drafts(batch, routed, root=tmp_path)

    assert yaml.safe_load((written.output_dir / "review_gaps.yaml").read_text(encoding="ascii"))[0]["line_anchor"] == "9"


def _provider_response(*, prompt_tokens: int, finish_reason: str = "stop") -> dict:
    return {
        "model": "z-ai/glm-5.2",
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": 4,
            "total_tokens": prompt_tokens + 4,
            "cost": 0.0001,
        },
        "choices": [
            {
                "finish_reason": finish_reason,
                "message": {"content": json.dumps({"ok": True})},
            }
        ],
        "openrouter_metadata": {
            "endpoints": {
                "available": [
                    {"provider": "Decart", "model": "z-ai/glm-5.2", "selected": True}
                ]
            }
        },
    }


def _live_client(response: dict) -> OpenAILlmClient:
    completions = SimpleNamespace(create=lambda **kwargs: response)
    return OpenAILlmClient(
        SimpleNamespace(chat=SimpleNamespace(completions=completions)),
        provider_name="OpenRouter",
    )


def _run_config(level: str = "INFO") -> dict:
    return {
        "project": {"paths": {"output_dir": "output"}},
        "llm": {"provider": "openrouter", "model": "z-ai/glm-5.2"},
        "extraction": {"mode": "one_pass", "expression_mode": "generator", "concurrency": 1},
        "logging": {"level": level},
    }


def _log_records(root: Path) -> list[dict]:
    paths = sorted((root / "output" / "logs").glob("*.jsonl"))
    assert len(paths) == 1
    return [json.loads(line) for line in paths[0].read_text(encoding="ascii").splitlines()]


def test_implausible_prompt_tokens_fail_fast_and_retain_failure_bodies(tmp_path: Path):
    client = _live_client(_provider_response(prompt_tokens=1))

    with pytest.raises(ImplausiblePromptTokens, match="implausible prompt token count"):
        with extraction_run(
            root=tmp_path,
            document_id="form_1040_2025",
            year="2025",
            config=_run_config("WARNING"),
        ):
            client.structured_completion(
                prompt="extract the form",
                schema={"type": "object"},
                model="z-ai/glm-5.2",
                max_tokens=24000,
                temperature=0,
                purpose="tax_graph_draft",
            )

    records = _log_records(tmp_path)
    call = next(record for record in records if record["event"] == "llm_call")
    assert call["document_id"] == "form_1040_2025"
    assert call["outcome"] == "implausible_prompt"
    assert call["prompt_tokens"] == 1
    assert call["resolved_provider"] == "Decart"
    assert call["request_body"]
    assert call["response_body"]
    assert records[-1]["event"] == "run_end"
    assert records[-1]["outcome"] == "failed"


def test_finish_reason_length_is_named_and_logged_at_info(tmp_path: Path):
    client = _live_client(_provider_response(prompt_tokens=12, finish_reason="length"))

    with pytest.raises(LlmResponseTruncated, match="finish_reason=length"):
        with extraction_run(
            root=tmp_path,
            document_id="form_1040_2025",
            year="2025",
            config=_run_config(),
        ):
            client.structured_completion(
                prompt="extract the form",
                schema={"type": "object"},
                model="z-ai/glm-5.2",
                max_tokens=24000,
                temperature=0,
                purpose="tax_graph_draft",
            )

    call = next(record for record in _log_records(tmp_path) if record["event"] == "llm_call")
    assert call["finish_reason"] == "length"
    assert call["outcome"] == "truncated"
    assert call["response_body"]


def test_micro_call_logs_target_and_bodies_at_info(tmp_path: Path):
    client = _live_client(_provider_response(prompt_tokens=12))

    with extraction_run(
        root=tmp_path,
        document_id="form_1040_2025",
        year="2025",
        config=_run_config(),
    ):
        with llm_call_target("form_1040_2025_root_line_1z"):
            client.structured_completion(
                prompt="human question",
                schema={"type": "object"},
                model="z-ai/glm-5.2",
                max_tokens=4000,
                temperature=0,
                purpose="tax_graph_micro_formula",
            )

    call = next(record for record in _log_records(tmp_path) if record["event"] == "llm_call")
    assert call["target_cell_id"] == "form_1040_2025_root_line_1z"
    assert call["request_body"]
    assert call["response_body"]
