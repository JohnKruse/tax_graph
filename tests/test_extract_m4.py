from __future__ import annotations

import json
import shutil
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest
import yaml

from tax_graph.cli import extract_command
from tax_graph.extract.checks import run_deterministic_checks
from tax_graph.extract.generator import ExtractionError, parse_generator_response
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.llm_client import LlmUnavailable, OpenAILlmClient, build_llm_client, supported_providers
from tax_graph.extract.models import SourceDocumentInput
from tax_graph.extract.prompts import _related_source_snippet, assemble_generator_prompt, closed_operations


ROOT = Path(__file__).resolve().parents[1]


class FakeLlmClient:
    def __init__(self, response: dict | None = None, critic_response: dict | None = None):
        self.response = response or _good_response(confidence=0.98)
        self.critic_response = critic_response or {
            "findings": [
                {"kind": "nodes", "object_id": "form_8949_2025_line_1_proceeds", "agrees": True, "reason": ""},
                {"kind": "citations", "object_id": "cite_8949_line_1", "agrees": True, "reason": ""},
            ]
        }
        self.calls: list[str] = []

    def structured_completion(self, *, prompt, schema, model, max_tokens, temperature, purpose):
        self.calls.append(purpose)
        if purpose == "tax_graph_critic":
            return self.critic_response
        return self.response


@pytest.mark.m4
def test_extract_input_loads_form_text_and_fields(tmp_path):
    root = _make_project(tmp_path)

    document = load_document_input("form_8949_2025", root=root, year="2025")

    assert document.document_id == "form_8949_2025"
    assert document.kind == "tax_form"
    assert "- 1: Proceeds" in document.text
    assert document.fields["fields"][0]["field_name"] == "f1"
    assert document.related_sources[0].document_id == "instructions_form_8949_2025"
    assert "Column h is column d minus column e" in document.related_sources[0].text


@pytest.mark.m4
def test_generator_prompt_includes_schema_ops_and_source(tmp_path):
    root = _make_project(tmp_path)
    document = load_document_input("form_8949_2025", root=root, year="2025")

    prompt = assemble_generator_prompt(document, root=root)

    assert "form_8949_2025" in prompt
    assert "COPY" in prompt
    assert "SUBTRACT" in closed_operations(root=root)
    assert "- 1: Proceeds" in prompt
    assert "instructions_form_8949_2025" in prompt
    assert "Column h is column d minus column e" in prompt
    assert "outbound FEEDS edge declaration" in prompt
    assert "lowercase snake_case" in prompt
    assert "node.schema.json" in prompt


@pytest.mark.m4
def test_critic_prompt_includes_draft_objects(tmp_path):
    from tax_graph.extract.generator import parse_generator_response
    from tax_graph.extract.prompts import assemble_critic_prompt

    root = _make_project(tmp_path)
    document = load_document_input("form_8949_2025", root=root, year="2025")
    batch = parse_generator_response(_good_response(confidence=0.98), document=document, model="mock-model", root=root)

    prompt = assemble_critic_prompt(document, batch=batch, root=root)

    assert "Draft objects to review:" in prompt
    assert "nodes/form_8949_2025_line_1_proceeds" in prompt
    assert "citations/cite_8949_line_1" in prompt


@pytest.mark.m4
def test_related_source_snippet_keeps_formula_context(tmp_path):
    text_path = tmp_path / "instructions.txt"
    source = SourceDocumentInput(
        document_id="instructions_form_8949_2025",
        kind="instructions",
        year="2025",
        url="https://www.irs.gov/pub/irs-pdf/i8949.pdf",
        text="irrelevant\n" * 20000 + "Column (h) gain or loss. Subtract column (e) from column (d).\n",
        text_path=text_path,
    )

    snippet = _related_source_snippet(source, max_chars=500)

    assert "Column (h)" in snippet
    assert len(snippet) <= 500


@pytest.mark.m4
def test_generator_rejects_off_vocab_operation(tmp_path):
    document = _source_document(tmp_path)
    response = _good_response(confidence=0.98)
    response["rules"] = [
        {
            "rule_id": "bad_rule",
            "operation": "MAKE_UP_TAX",
            "description": "Invalid operation.",
            "citation_refs": ["cite_8949_line_1"],
        }
    ]

    with pytest.raises(ExtractionError, match="unsupported operation"):
        parse_generator_response(response, document=document, model="mock-model", root=ROOT)


@pytest.mark.m4
def test_generator_lifts_inline_provenance(tmp_path):
    document = _source_document(tmp_path)
    response = _good_response(confidence=0.98)
    response["provenance"] = []
    response["nodes"][0]["provenance"] = {"source_span": "- 1: Proceeds", "confidence": 0.97}

    batch = parse_generator_response(response, document=document, model="mock-model", root=ROOT)

    node = batch.items("nodes")[0]
    assert "provenance" not in node.data
    assert node.source_span == "- 1: Proceeds"
    assert node.confidence == 0.97


@pytest.mark.m4
def test_deterministic_checks_flag_missing_line_and_bad_quote(tmp_path):
    document = _source_document(tmp_path)
    response = _good_response(confidence=0.98)
    response["nodes"] = []
    response["citations"][0]["quoted_text"] = "This quote is absent."
    batch = parse_generator_response(response, document=document, model="mock-model", root=ROOT)

    report = run_deterministic_checks(document, batch, root=ROOT)

    reasons = [issue.reason for issue in report.issues]
    assert "line 1 has no node" in reasons
    assert "citation quote: quote not found" in reasons
    assert batch.objects[0].flags


@pytest.mark.m4
def test_extract_command_writes_drafts_only_under_drafts(tmp_path, capsys):
    root = _make_project(tmp_path)
    client = FakeLlmClient()

    exit_code = extract_command(doc="form_8949_2025", year="2025", root=root, client=client)

    captured = capsys.readouterr()
    draft_dir = root / "graph" / "2025" / "_drafts" / "form_8949_2025"
    assert exit_code == 0
    assert client.calls == ["tax_graph_draft", "tax_graph_critic"]
    assert "auto_accepted: 2" in captured.out
    assert (draft_dir / "nodes.yaml").exists()
    assert (draft_dir / "citations.yaml").exists()
    assert (draft_dir / "outline.yaml").exists()
    assert (draft_dir / "candidate_spans.yaml").exists()
    assert (draft_dir / "provenance.yaml").exists()
    assert "Drafts remain under `_drafts`" in (draft_dir / "review.md").read_text(encoding="utf-8")
    assert not (root / "graph" / "2025" / "nodes").exists()

    node = yaml.safe_load((draft_dir / "nodes.yaml").read_text(encoding="utf-8"))[0]
    assert node["node_id"] == "form_8949_2025_line_1_proceeds"
    assert "confidence" not in node


@pytest.mark.m4
def test_extract_command_year_runs_manifest_docs(tmp_path, capsys):
    root = _make_project(tmp_path)
    manifest_path = root / "config" / "manifest.yaml"
    manifest_path.write_text(
        "\n".join(
            [
                "tax_year: 2025",
                "documents:",
                "  - document_id: form_8949_2025",
                "    kind: tax_form",
                "    url: https://www.irs.gov/pub/irs-pdf/f8949.pdf",
                "",
            ]
        ),
        encoding="utf-8",
    )
    client = FakeLlmClient()

    exit_code = extract_command(year="2025", root=root, client=client)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "year: 2025" in captured.out
    assert "documents: 1" in captured.out
    assert (root / "graph" / "2025" / "_drafts" / "form_8949_2025" / "review.md").exists()


@pytest.mark.m4
def test_low_confidence_draft_routes_to_human_review(tmp_path):
    root = _make_project(tmp_path)
    client = FakeLlmClient(response=_good_response(confidence=0.40))

    extract_command(doc="form_8949_2025", year="2025", root=root, client=client)

    review = (
        root / "graph" / "2025" / "_drafts" / "form_8949_2025" / "review.md"
    ).read_text(encoding="utf-8")
    assert "Auto-accepted drafts: 0" in review
    assert "Human-review drafts: 2" in review
    assert "confidence 0.400 below threshold 0.950" in review


@pytest.mark.m4
def test_llm_factory_requires_explicit_provider():
    with pytest.raises(LlmUnavailable, match="llm.provider is required"):
        build_llm_client({"llm": {"api_key": "fake-key"}})


@pytest.mark.m4
def test_llm_factory_dispatches_to_openai_adapter(monkeypatch):
    class FakeOpenAI:
        def __init__(self, *, api_key):
            self.api_key = api_key

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))

    client = build_llm_client({"llm": {"provider": "openai", "api_key": "fake-key"}})

    assert client.__class__.__name__ == "OpenAICompatibleLlmClient"
    assert supported_providers() == ("anthropic", "openai", "openrouter")


@pytest.mark.m4
def test_llm_factory_dispatches_to_openrouter_adapter(monkeypatch):
    calls = []

    class FakeOpenAI:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))

    client = build_llm_client(
        {
            "llm": {
                "provider": "openrouter",
                "api_key": "fake-key",
                "app_name": "Tax Graph Tests",
            }
        }
    )

    assert client.__class__.__name__ == "OpenAICompatibleLlmClient"
    assert calls[0]["base_url"] == "https://openrouter.ai/api/v1"
    assert calls[0]["default_headers"]["X-Title"] == "Tax Graph Tests"
    assert client.extra_body["provider"]["require_parameters"] is True


@pytest.mark.m4
def test_llm_factory_openrouter_reasoning_is_opt_in(monkeypatch):
    class FakeOpenAI:
        def __init__(self, **kwargs):
            pass

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))

    client = build_llm_client(
        {
            "llm": {
                "provider": "openrouter",
                "api_key": "fake-key",
                "reasoning_effort": "minimal",
                "reasoning_exclude": True,
            }
        }
    )

    assert client.extra_body["reasoning"]["effort"] == "minimal"
    assert client.extra_body["reasoning"]["exclude"] is True


@pytest.mark.m4
def test_openai_adapter_parses_structured_json():
    class FakeCompletions:
        def create(self, **kwargs):
            self.kwargs = kwargs
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({"nodes": [], "edges": [], "rules": [], "citations": [], "decisions": [], "provenance": []})
                        }
                    }
                ]
            }

    completions = FakeCompletions()
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    client = OpenAILlmClient(fake_client, provider_name="OpenAI")

    result = client.structured_completion(
        prompt="extract",
        schema={"type": "object"},
        model="provider-model",
        max_tokens=100,
        temperature=0,
        purpose="tax_graph_draft",
    )

    assert result["nodes"] == []
    assert completions.kwargs["response_format"]["type"] == "json_schema"
    assert completions.kwargs["response_format"]["json_schema"]["strict"] is False


@pytest.mark.m4
def test_openai_adapter_tolerates_fenced_json():
    class FakeCompletions:
        def create(self, **kwargs):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "```json\n{\"nodes\": [], \"edges\": [], \"rules\": [], \"citations\": [], \"decisions\": []}\n```"
                        }
                    }
                ]
            }

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    client = OpenAILlmClient(fake_client, provider_name="OpenAI")

    result = client.structured_completion(
        prompt="extract",
        schema={"type": "object"},
        model="provider-model",
        max_tokens=100,
        temperature=0,
        purpose="tax_graph_draft",
    )

    assert result["nodes"] == []


@pytest.mark.m4
def test_openai_adapter_extracts_json_from_text_wrapper():
    class FakeCompletions:
        def create(self, **kwargs):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "Here is the JSON:\n{\"nodes\": [], \"edges\": [], \"rules\": [], \"citations\": [], \"decisions\": []}\nDone."
                        }
                    }
                ]
            }

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    client = OpenAILlmClient(fake_client, provider_name="OpenAI")

    result = client.structured_completion(
        prompt="extract",
        schema={"type": "object"},
        model="provider-model",
        max_tokens=100,
        temperature=0,
        purpose="tax_graph_draft",
    )

    assert result["nodes"] == []


def _make_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(ROOT / "config", root / "config")
    shutil.copytree(ROOT / "schemas", root / "schemas")
    shutil.copytree(ROOT / "prompts", root / "prompts")
    raw_dir = root / ".cache" / "raw" / "2025"
    raw_dir.mkdir(parents=True)
    (raw_dir / "form_8949_2025.txt").write_text("# Page 1\n- 1: Proceeds\n", encoding="utf-8")
    (raw_dir / "form_8949_2025.fields.json").write_text(
        json.dumps({"fields": [{"field_name": "f1", "page": 1, "x_cluster": 300, "y_cluster": 100, "line_anchor": "1"}]}),
        encoding="utf-8",
    )
    (raw_dir / "instructions_form_8949_2025.txt").write_text(
        "# Page 1\nColumn h is column d minus column e.\nReport totals on Schedule D.\n",
        encoding="utf-8",
    )
    pages_dir = raw_dir / "instructions_form_8949_2025.pages"
    pages_dir.mkdir()
    (pages_dir / "page-001.md").write_text("Column h is column d minus column e.\n", encoding="utf-8")
    (raw_dir / "instructions_form_8949_2025.links.json").write_text("[]\n", encoding="utf-8")
    return root


def _source_document(tmp_path: Path) -> SourceDocumentInput:
    text_path = tmp_path / "form_8949_2025.txt"
    text_path.write_text("# Page 1\n- 1: Proceeds\n", encoding="utf-8")
    return SourceDocumentInput(
        document_id="form_8949_2025",
        kind="tax_form",
        year="2025",
        url="https://www.irs.gov/pub/irs-pdf/f8949.pdf",
        text=text_path.read_text(encoding="utf-8"),
        text_path=text_path,
        fields={"fields": [{"field_name": "f1", "line_anchor": "1"}]},
    )


def _good_response(*, confidence: float) -> dict:
    return {
        "nodes": [
            {
                "node_id": "form_8949_2025_line_1_proceeds",
                "document_id": "form_8949_2025",
                "label": "Form 8949, line 1 - Proceeds",
                "node_type": "form_line",
                "value_type": "currency",
                "required": "conditional",
                "citation_refs": ["cite_8949_line_1"],
            }
        ],
        "edges": [],
        "rules": [],
        "citations": [
            {
                "citation_id": "cite_8949_line_1",
                "document_id": "form_8949_2025",
                "locator": "line 1",
                "quoted_text": "Proceeds",
                "url": "https://www.irs.gov/pub/irs-pdf/f8949.pdf",
                "retrieved_date": "2026-06-29",
            }
        ],
        "decisions": [],
        "provenance": [
            {
                "kind": "nodes",
                "object_id": "form_8949_2025_line_1_proceeds",
                "source_span": "- 1: Proceeds",
                "confidence": confidence,
            },
            {
                "kind": "citations",
                "object_id": "cite_8949_line_1",
                "source_span": "- 1: Proceeds",
                "confidence": confidence,
            },
        ],
    }
