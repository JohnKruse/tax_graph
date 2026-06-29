"""Provider-agnostic LLM client protocol and adapters."""

from __future__ import annotations

import json
from typing import Any, Protocol

from tax_graph.config import get_config_value, resolve_secret


class LlmUnavailable(RuntimeError):
    """Raised when extraction needs an LLM but none is configured."""


class LlmClient(Protocol):
    """Small structured-output client protocol used by deterministic tests."""

    def structured_completion(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        model: str,
        max_tokens: int,
        temperature: float | None,
        purpose: str,
    ) -> dict[str, Any]:
        """Return schema-constrained output."""


def build_llm_client(config: dict[str, Any]) -> LlmClient:
    """Build the configured LLM client."""
    provider = _normalized_provider(config)
    if not provider:
        raise LlmUnavailable("llm.provider is required for live extraction")

    api_key = resolve_secret(
        config,
        "llm.api_key",
        keyring_path="llm.api_key_keyring",
        env_path="llm.api_key_env",
    )
    if not api_key:
        raise LlmUnavailable(f"{provider} extraction requires an API key")

    if provider == "anthropic":
        return _build_anthropic_client(api_key)
    if provider == "openai":
        return _build_openai_client(api_key, config)
    if provider == "openrouter":
        return _build_openrouter_client(api_key, config)
    raise LlmUnavailable(f"unsupported llm.provider: {provider}")


def supported_providers() -> tuple[str, ...]:
    """Return live provider adapters shipped by this package."""
    return ("anthropic", "openai", "openrouter")


def _normalized_provider(config: dict[str, Any]) -> str:
    provider = get_config_value(config, "llm.provider")
    if provider is None or str(provider).strip() == "":
        return ""
    normalized = str(provider).strip().lower()
    aliases = {
        "claude": "anthropic",
        "open_ai": "openai",
        "gpt": "openai",
    }
    return aliases.get(normalized, normalized)


def _build_anthropic_client(api_key: str) -> LlmClient:
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - optional until extract runs live.
        raise LlmUnavailable("anthropic package is not installed") from exc
    return AnthropicLlmClient(anthropic.Anthropic(api_key=api_key))


def _build_openai_client(api_key: str, config: dict[str, Any]) -> LlmClient:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - optional until extract runs live.
        raise LlmUnavailable("openai package is not installed") from exc
    return OpenAICompatibleLlmClient(
        OpenAI(api_key=api_key),
        provider_name="OpenAI",
        strict_schema=bool(get_config_value(config, "llm.strict_schema", False)),
    )


def _build_openrouter_client(api_key: str, config: dict[str, Any]) -> LlmClient:
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - optional until extract runs live.
        raise LlmUnavailable("openai package is not installed") from exc

    base_url = get_config_value(config, "llm.base_url", "https://openrouter.ai/api/v1")
    kwargs: dict[str, Any] = {"api_key": api_key, "base_url": base_url}
    headers = _openrouter_headers(config)
    if headers:
        kwargs["default_headers"] = headers
    return OpenAICompatibleLlmClient(
        OpenAI(**kwargs),
        provider_name="OpenRouter",
        extra_body=_openrouter_extra_body(config),
        strict_schema=bool(get_config_value(config, "llm.strict_schema", False)),
    )


def _openrouter_headers(config: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {}
    site_url = get_config_value(config, "llm.site_url")
    app_name = get_config_value(config, "llm.app_name")
    if site_url:
        headers["HTTP-Referer"] = str(site_url)
    if app_name:
        headers["X-Title"] = str(app_name)
    return headers


def _openrouter_extra_body(config: dict[str, Any]) -> dict[str, Any]:
    reasoning_effort = get_config_value(config, "llm.reasoning_effort")
    reasoning_exclude = get_config_value(config, "llm.reasoning_exclude")
    extra_body: dict[str, Any] = {}
    reasoning: dict[str, Any] = {}
    if reasoning_effort:
        reasoning["effort"] = str(reasoning_effort)
    if reasoning_exclude is not None:
        reasoning["exclude"] = bool(reasoning_exclude)
    if reasoning:
        extra_body["reasoning"] = reasoning
    if bool(get_config_value(config, "llm.require_parameters", True)):
        extra_body["provider"] = {"require_parameters": True}
    return extra_body


class AnthropicLlmClient:
    """Anthropic Messages API client using strict tool outputs."""

    def __init__(self, client: Any):
        self.client = client

    def structured_completion(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        model: str,
        max_tokens: int,
        temperature: float | None,
        purpose: str,
    ) -> dict[str, Any]:
        """Return the input payload of the required strict tool call."""
        tool_name = f"emit_{purpose}"
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
            tool_choice={"type": "tool", "name": tool_name},
            tools=[
                {
                    "name": tool_name,
                    "description": "Emit the requested Tax Graph extraction payload.",
                    "strict": True,
                    "input_schema": schema,
                }
            ],
        )
        for block in getattr(response, "content", []):
            block_type = getattr(block, "type", None)
            block_name = getattr(block, "name", None)
            block_input = getattr(block, "input", None)
            if block_type == "tool_use" and block_name == tool_name and isinstance(block_input, dict):
                return block_input
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == tool_name:
                return dict(block.get("input", {}))
        raise LlmUnavailable("Anthropic response did not contain the required tool output")


class OpenAICompatibleLlmClient:
    """OpenAI-compatible client using JSON Schema structured outputs."""

    def __init__(
        self,
        client: Any,
        *,
        provider_name: str,
        extra_body: dict[str, Any] | None = None,
        strict_schema: bool = False,
    ):
        self.client = client
        self.provider_name = provider_name
        self.extra_body = extra_body or {}
        self.strict_schema = strict_schema

    def structured_completion(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        model: str,
        max_tokens: int,
        temperature: float | None,
        purpose: str,
    ) -> dict[str, Any]:
        """Return the parsed strict JSON-schema response payload."""
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": purpose,
                    "schema": schema,
                    "strict": self.strict_schema,
                },
            },
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if self.extra_body:
            kwargs["extra_body"] = self.extra_body
        response = self.client.chat.completions.create(**kwargs)
        content = _openai_message_content(response, provider_name=self.provider_name)
        try:
            parsed = json.loads(_extract_json_payload(content))
        except json.JSONDecodeError as exc:
            raise LlmUnavailable(f"{self.provider_name} response did not contain JSON") from exc
        if not isinstance(parsed, dict):
            raise LlmUnavailable(f"{self.provider_name} response JSON was not an object")
        return parsed


OpenAILlmClient = OpenAICompatibleLlmClient


def _openai_message_content(response: Any, *, provider_name: str = "OpenAI") -> str:
    choices = _get(response, "choices", [])
    if not choices:
        raise LlmUnavailable("OpenAI response did not contain choices")
    message = _get(choices[0], "message", None)
    if message is None:
        raise LlmUnavailable("OpenAI response did not contain a message")
    parsed = _get(message, "parsed", None)
    if isinstance(parsed, dict):
        return json.dumps(parsed)
    content = _get(message, "content", "")
    if isinstance(content, str):
        return content
    finish_reason = _get(choices[0], "finish_reason", "unknown")
    raise LlmUnavailable(f"{provider_name} response message content was not text; finish_reason={finish_reason}")


def _extract_json_payload(content: str) -> str:
    stripped = content.strip()
    fenced = _strip_json_fence(stripped)
    if fenced.startswith("{"):
        return fenced
    return _balanced_json_object(fenced)


def _strip_json_fence(content: str) -> str:
    if not content.startswith("```"):
        return content
    lines = content.splitlines()
    if len(lines) < 2:
        return content
    first_line = lines[0].strip().lower()
    if not first_line.startswith("```json") and first_line != "```":
        return content
    if lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return "\n".join(lines[1:]).strip()


def _balanced_json_object(content: str) -> str:
    start = content.find("{")
    if start < 0:
        return content

    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(content[start:], start=start):
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_string:
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start : index + 1]
    return content[start:].strip()


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)
