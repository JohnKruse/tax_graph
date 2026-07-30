"""Provider-agnostic LLM client protocol and adapters."""

from __future__ import annotations

import json
from dataclasses import replace
import time
from typing import Any, Protocol

from tax_graph.config import get_config_value, resolve_secret
from tax_graph.extract.models import LlmCallTelemetry
from tax_graph.extract.observability import log_llm_call


class LlmUnavailable(RuntimeError):
    """Raised when extraction needs an LLM but none is configured."""


class ImplausiblePromptTokens(LlmUnavailable):
    """Raised when a provider reports that the extraction prompt was nearly empty."""


class LlmResponseTruncated(LlmUnavailable):
    """Raised when a provider stops a structured response at its output limit."""


MIN_PLAUSIBLE_PROMPT_TOKENS = 8


class StructuredCompletionResult(dict[str, Any]):
    """Dict-compatible structured output with response-envelope telemetry."""

    def __init__(self, payload: dict[str, Any], metadata: LlmCallTelemetry):
        super().__init__(payload)
        self.metadata = metadata


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
        strict_schema=bool(get_config_value(config, "llm.strict_schema", True)),
        parameter_mode=_parameter_mode(config),
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
        strict_schema=bool(get_config_value(config, "llm.strict_schema", True)),
        parameter_mode=_parameter_mode(config),
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
    parameter_mode = _parameter_mode(config)
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
    if parameter_mode in {"auto", "require"}:
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
        request_body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
            "tool_choice": {"type": "tool", "name": tool_name},
            "tools": [
                {
                    "name": tool_name,
                    "description": "Emit the requested Tax Graph extraction payload.",
                    "strict": True,
                    "input_schema": schema,
                }
            ],
        }
        started = time.perf_counter()
        try:
            response = self.client.messages.create(**request_body)
        except Exception as exc:
            error = LlmUnavailable(f"Anthropic request failed: {exc}")
            log_llm_call(
                document_id="unknown",
                purpose=purpose,
                requested_model=model,
                telemetry=None,
                request_body=request_body,
                response_body=_exception_response(exc),
                outcome="error",
                latency_ms=_elapsed_ms(started),
                error=str(error),
            )
            raise error from exc

        telemetry = _response_telemetry(
            response,
            requested_model=model,
            provider="Anthropic",
            latency_ms=_elapsed_ms(started),
        )
        try:
            _validate_response_telemetry(telemetry, provider="Anthropic")
            for block in getattr(response, "content", []):
                block_type = getattr(block, "type", None)
                block_name = getattr(block, "name", None)
                block_input = getattr(block, "input", None)
                if block_type == "tool_use" and block_name == tool_name and isinstance(block_input, dict):
                    telemetry = replace(telemetry, outcome="success")
                    log_llm_call(
                        document_id="unknown",
                        purpose=purpose,
                        requested_model=model,
                        telemetry=telemetry,
                        request_body=request_body,
                        response_body=response,
                        outcome="success",
                        latency_ms=telemetry.latency_ms,
                    )
                    return StructuredCompletionResult(block_input, telemetry)
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == tool_name:
                    telemetry = replace(telemetry, outcome="success")
                    log_llm_call(
                        document_id="unknown",
                        purpose=purpose,
                        requested_model=model,
                        telemetry=telemetry,
                        request_body=request_body,
                        response_body=response,
                        outcome="success",
                        latency_ms=telemetry.latency_ms,
                    )
                    return StructuredCompletionResult(dict(block.get("input", {})), telemetry)
            raise LlmUnavailable("Anthropic response did not contain the required tool output")
        except LlmUnavailable as exc:
            outcome = _failure_outcome(exc)
            log_llm_call(
                document_id="unknown",
                purpose=purpose,
                requested_model=model,
                telemetry=replace(telemetry, outcome=outcome),
                request_body=request_body,
                response_body=response,
                outcome=outcome,
                latency_ms=telemetry.latency_ms,
                error=str(exc),
            )
            raise


class OpenAICompatibleLlmClient:
    """OpenAI-compatible client using JSON Schema structured outputs."""

    def __init__(
        self,
        client: Any,
        *,
        provider_name: str,
        extra_body: dict[str, Any] | None = None,
        strict_schema: bool = True,
        parameter_mode: str = "omit",
    ):
        self.client = client
        self.provider_name = provider_name
        self.extra_body = extra_body or {}
        self.strict_schema = strict_schema
        self.parameter_mode = parameter_mode

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
        extra_body = dict(self.extra_body)
        if extra_body:
            kwargs["extra_body"] = extra_body
        request_attempts: list[dict[str, Any]] = [kwargs]
        started = time.perf_counter()
        response: Any = None
        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception as exc:
            if self._should_retry_without_provider_hints(exc, extra_body):
                retry_kwargs = dict(kwargs)
                retry_extra_body = dict(extra_body)
                retry_extra_body.pop("provider", None)
                if retry_extra_body:
                    retry_kwargs["extra_body"] = retry_extra_body
                else:
                    retry_kwargs.pop("extra_body", None)
                request_attempts.append(retry_kwargs)
                try:
                    response = self.client.chat.completions.create(**retry_kwargs)
                except Exception as retry_exc:
                    latency_ms = _elapsed_ms(started)
                    log_llm_call(
                        document_id="unknown",
                        purpose=purpose,
                        requested_model=model,
                        telemetry=None,
                        request_body={"attempts": request_attempts},
                        response_body=_exception_response(retry_exc),
                        outcome="error",
                        latency_ms=latency_ms,
                        error=str(_rewrite_openai_compatible_error(retry_exc, provider_name=self.provider_name)),
                    )
                    raise _rewrite_openai_compatible_error(retry_exc, provider_name=self.provider_name) from retry_exc
            else:
                error = _rewrite_openai_compatible_error(exc, provider_name=self.provider_name)
                log_llm_call(
                    document_id="unknown",
                    purpose=purpose,
                    requested_model=model,
                    telemetry=None,
                    request_body={"attempts": request_attempts},
                    response_body=_exception_response(exc),
                    outcome="error",
                    latency_ms=_elapsed_ms(started),
                    error=str(error),
                )
                raise error from exc

        telemetry = _response_telemetry(
            response,
            requested_model=model,
            provider=self.provider_name,
            latency_ms=_elapsed_ms(started),
        )
        try:
            _validate_response_telemetry(telemetry, provider=self.provider_name)
            content = _openai_message_content(response, provider_name=self.provider_name)
            parsed = json.loads(_extract_json_payload(content))
        except json.JSONDecodeError as exc:
            error = LlmUnavailable(f"{self.provider_name} response did not contain JSON")
            log_llm_call(
                document_id="unknown",
                purpose=purpose,
                requested_model=model,
                telemetry=replace(telemetry, outcome="error"),
                request_body={"attempts": request_attempts},
                response_body=response,
                outcome="error",
                latency_ms=telemetry.latency_ms,
                error=str(error),
            )
            raise error from exc
        except LlmUnavailable as exc:
            outcome = _failure_outcome(exc)
            log_llm_call(
                document_id="unknown",
                purpose=purpose,
                requested_model=model,
                telemetry=replace(telemetry, outcome=outcome),
                request_body={"attempts": request_attempts},
                response_body=response,
                outcome=outcome,
                latency_ms=telemetry.latency_ms,
                error=str(exc),
            )
            raise
        if not isinstance(parsed, dict):
            error = LlmUnavailable(f"{self.provider_name} response JSON was not an object")
            log_llm_call(
                document_id="unknown",
                purpose=purpose,
                requested_model=model,
                telemetry=replace(telemetry, outcome="error"),
                request_body={"attempts": request_attempts},
                response_body=response,
                outcome="error",
                latency_ms=telemetry.latency_ms,
                error=str(error),
            )
            raise error
        telemetry = replace(telemetry, outcome="success")
        log_llm_call(
            document_id="unknown",
            purpose=purpose,
            requested_model=model,
            telemetry=telemetry,
            request_body={"attempts": request_attempts},
            response_body=response,
            outcome="success",
            latency_ms=telemetry.latency_ms,
        )
        return StructuredCompletionResult(
            parsed,
            telemetry,
        )

    def _should_retry_without_provider_hints(self, exc: Exception, extra_body: dict[str, Any]) -> bool:
        if self.parameter_mode != "auto":
            return False
        if "provider" not in extra_body:
            return False
        message = str(exc).lower()
        return (
            "require_parameters" in message
            or "provider.require_parameters" in message
            or ("provider" in message and "unsupported parameter" in message)
            or ("provider" in message and "unknown parameter" in message)
            or ("provider" in message and "extra inputs are not permitted" in message)
            or "no endpoints found that can handle the requested parameters" in message
        )


OpenAILlmClient = OpenAICompatibleLlmClient


def response_telemetry(value: Any) -> LlmCallTelemetry | None:
    """Return adapter telemetry when a structured response carries it."""
    metadata = getattr(value, "metadata", None)
    return metadata if isinstance(metadata, LlmCallTelemetry) else None


def _response_telemetry(
    response: Any,
    *,
    requested_model: str,
    provider: str,
    latency_ms: float | None = None,
) -> LlmCallTelemetry:
    """Extract provider response metadata without changing the model payload."""
    usage = _get(response, "usage", None)
    prompt_tokens = _as_int(_get(usage, "prompt_tokens", _get(usage, "input_tokens", None)))
    completion_tokens = _as_int(_get(usage, "completion_tokens", _get(usage, "output_tokens", None)))
    total_tokens = _as_int(_get(usage, "total_tokens", None))
    if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
        total_tokens = prompt_tokens + completion_tokens
    cost = _as_float(_get(usage, "cost", _get(response, "cost", None)))
    resolved_model = _get(response, "model", None)
    choices = _get(response, "choices", [])
    finish_reason = _get(choices[0], "finish_reason", None) if choices else _get(response, "stop_reason", None)
    return LlmCallTelemetry(
        provider=provider,
        requested_model=str(requested_model),
        resolved_model=str(resolved_model) if resolved_model else None,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost=cost,
        finish_reason=str(finish_reason) if finish_reason is not None else None,
        latency_ms=latency_ms,
        outcome="received",
    )


def _validate_response_telemetry(telemetry: LlmCallTelemetry, *, provider: str) -> None:
    """Reject provider responses that prove the request was empty or truncated."""
    if (
        telemetry.prompt_tokens is not None
        and telemetry.prompt_tokens < MIN_PLAUSIBLE_PROMPT_TOKENS
    ):
        raise ImplausiblePromptTokens(
            f"{provider} reported implausible prompt token count "
            f"{telemetry.prompt_tokens}; expected at least {MIN_PLAUSIBLE_PROMPT_TOKENS}"
        )
    if telemetry.finish_reason == "length":
        raise LlmResponseTruncated(
            f"{provider} structured response truncated at max_tokens "
            f"(finish_reason=length; completion_tokens={telemetry.completion_tokens})"
        )


def _failure_outcome(error: LlmUnavailable) -> str:
    if isinstance(error, ImplausiblePromptTokens):
        return "implausible_prompt"
    if isinstance(error, LlmResponseTruncated):
        return "truncated"
    return "error"


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)


def _exception_response(error: Exception) -> dict[str, Any]:
    """Return provider error-body fields without serializing request headers."""
    response = _get(error, "response", None)
    response_text: str | None = None
    if response is not None:
        try:
            candidate = _get(response, "text", None)
            response_text = str(candidate) if candidate is not None else None
        except Exception:
            response_text = None
    return {
        "type": type(error).__name__,
        "message": str(error),
        "status_code": _get(error, "status_code", None),
        "body": _get(error, "body", None),
        "response_text": response_text,
    }


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def _parameter_mode(config: dict[str, Any]) -> str:
    raw = get_config_value(config, "llm.require_parameters", "auto")
    if isinstance(raw, bool):
        return "require" if raw else "omit"
    normalized = str(raw).strip().lower()
    if normalized in {"auto", "require", "omit"}:
        return normalized
    raise LlmUnavailable("llm.require_parameters must be true, false, auto, require, or omit")


def _rewrite_openai_compatible_error(exc: Exception, *, provider_name: str) -> LlmUnavailable:
    message = str(exc)
    lowered = message.lower()
    if (
        "response_format" in lowered
        or "json_schema" in lowered
        or "structured output" in lowered
        or "structured-output" in lowered
    ):
        return LlmUnavailable(
            f"{provider_name} endpoint does not support JSON-schema structured outputs; "
            "choose a structured-output-capable endpoint or adjust llm.require_parameters"
        )
    return LlmUnavailable(f"{provider_name} request failed: {message}")
