from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from tax_graph.config import (
    ModelConfigurationError,
    derive_vendor_family,
    resolve_llm_model,
    resolve_llm_seed,
)
from tax_graph.doctor import DoctorReport, render_doctor_report
from tax_graph.extract.llm_client import OpenAILlmClient
from tax_graph.extract.observability import extraction_run


pytestmark = pytest.mark.m20


@pytest.mark.parametrize("role", ["primary", "micro", "example", "nversion"])
def test_model_accessor_fails_closed_for_missing_role(role: str) -> None:
    with pytest.raises(ModelConfigurationError, match="required"):
        resolve_llm_model({"llm": {}}, role)


def test_model_accessor_does_not_select_a_placeholder_or_fallback() -> None:
    with pytest.raises(ModelConfigurationError, match="llm.model is required"):
        resolve_llm_model({"llm": {}})
    assert resolve_llm_model({"llm": {"model": "openai/gpt-test"}}) == "openai/gpt-test"


def test_seed_accessor_preserves_zero_and_rejects_non_integer() -> None:
    assert resolve_llm_seed({"llm": {"seed": 0}}) == 0
    assert resolve_llm_seed({"llm": {"seed": None}}) is None
    with pytest.raises(ModelConfigurationError, match="llm.seed"):
        resolve_llm_seed({"llm": {"seed": "not-an-integer"}})


def test_vendor_family_is_derived_from_model_id() -> None:
    assert derive_vendor_family("~google/gemini-test") == "google"
    assert derive_vendor_family("family-a/model") == "family-a"


def test_openai_adapter_sends_explicit_zero_seed() -> None:
    calls: list[dict] = []

    def create(**kwargs):
        calls.append(kwargs)
        return {
            "model": "openai/gpt-test",
            "choices": [{"message": {"content": json.dumps({"ok": True})}}],
        }

    client = OpenAILlmClient(
        SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))),
        provider_name="OpenAI",
    )

    result = client.structured_completion(
        prompt="test",
        schema={"type": "object"},
        model="openai/gpt-test",
        max_tokens=10,
        temperature=None,
        seed=0,
        purpose="s86_seed",
    )

    assert result["ok"] is True
    assert calls[0]["seed"] == 0


def test_run_report_records_requested_resolved_and_endpoint(tmp_path) -> None:
    response = {
        "model": "z-ai/glm-5.2",
        "usage": {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16},
        "choices": [{"finish_reason": "stop", "message": {"content": '{"ok": true}'}}],
        "openrouter_metadata": {
            "endpoints": {"available": [{"provider": "Decart", "selected": True}]}
        },
    }
    client = OpenAILlmClient(
        SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=lambda **kwargs: response)
            )
        ),
        provider_name="OpenRouter",
    )
    config = {
        "project": {"paths": {"output_dir": "output"}},
        "llm": {"model": "openai/gpt-test", "seed": 0},
    }

    with extraction_run(
        root=tmp_path,
        document_id="form_1040_2025",
        year="2025",
        config=config,
    ):
        client.structured_completion(
            prompt="test",
            schema={"type": "object"},
            model="openai/gpt-test",
            max_tokens=10,
            temperature=None,
            seed=0,
            purpose="s86_attribution",
        )

    records = [
        json.loads(line)
        for line in next((tmp_path / "output" / "logs").glob("*.jsonl")).read_text(
            encoding="ascii"
        ).splitlines()
    ]
    start = next(record for record in records if record["event"] == "run_start")
    call = next(record for record in records if record["event"] == "llm_call")
    end = next(record for record in records if record["event"] == "run_end")
    assert start["requested_model"] == "openai/gpt-test"
    assert start["seed"] == 0
    assert call["resolved_endpoint"] == "Decart"
    assert end["requested_models"] == ["openai/gpt-test"]
    assert end["resolved_models"] == ["z-ai/glm-5.2"]
    assert end["resolved_endpoints"] == ["Decart"]


def test_doctor_report_names_the_requested_model() -> None:
    report = DoctorReport(
        year="2025",
        claims=(),
        artifacts=(),
        operations=(),
        open_items=(),
        configured_model="openai/gpt-test",
    )

    assert "configured model (requested): openai/gpt-test" in render_doctor_report(report)
