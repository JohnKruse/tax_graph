"""Inspectably record live extraction runs and provider calls.

The recorder uses the standard-library logging package and the existing
``logging.level`` configuration.  It writes one JSON object per line under
the configured, gitignored output directory so a failed extraction can be
diagnosed without a provider dashboard.
"""

from __future__ import annotations

from contextlib import contextmanager
import contextvars
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import threading
import time
from typing import Any, Iterator
import uuid

from tax_graph.config import get_config_value


_CURRENT_RUN: contextvars.ContextVar["RunLogger | None"] = contextvars.ContextVar(
    "tax_graph_extraction_run",
    default=None,
)
_CURRENT_TARGET_CELL: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "tax_graph_extraction_target_cell",
    default=None,
)
_MAX_LOG_STRING_CHARS = 60_000
_REDACTED = "[redacted]"
_SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "default_headers",
    "headers",
    "password",
    "token",
}


@dataclass
class _JsonFormatter(logging.Formatter):
    """Serialize structured log payloads as stable ASCII JSONL."""

    def format(self, record: logging.LogRecord) -> str:
        payload = getattr(record, "payload", None)
        if not isinstance(payload, dict):
            payload = {"event": record.getMessage()}
        return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


@dataclass
class RunLogger:
    """Write one extraction run and its provider calls to a JSONL file."""

    root: Path
    document_id: str
    year: str | int
    config: dict[str, Any]
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    _logger: logging.Logger = field(init=False, repr=False)
    _handler: logging.Handler = field(init=False, repr=False)
    log_path: Path = field(init=False)
    started_monotonic: float = field(init=False, repr=False)
    calls: int = field(default=0, init=False)
    successful_calls: int = field(default=0, init=False)
    failed_calls: int = field(default=0, init=False)
    total_tokens: int = field(default=0, init=False)
    total_cost: float = field(default=0.0, init=False)
    known_token_calls: int = field(default=0, init=False)
    known_cost_calls: int = field(default=0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        output_dir = Path(str(get_config_value(self.config, "project.paths.output_dir", "output")))
        if not output_dir.is_absolute():
            output_dir = self.root / output_dir
        self.log_path = output_dir / "logs" / f"{self.run_id}.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        logger_name = f"tax_graph.extract.run.{self.run_id}"
        self._logger = logging.getLogger(logger_name)
        self._logger.propagate = False
        self._logger.setLevel(_configured_level(self.config))
        self._handler = logging.FileHandler(self.log_path, encoding="utf-8", mode="w")
        self._handler.setFormatter(_JsonFormatter())
        self._logger.addHandler(self._handler)
        self.started_monotonic = time.perf_counter()

    def start(self) -> None:
        """Write the run-level start record with non-secret resolved settings."""
        self.emit(
            "run_start",
            document_id=self.document_id,
            tax_year=str(self.year),
            config={
                "provider": get_config_value(self.config, "llm.provider"),
                "model": get_config_value(self.config, "llm.model"),
                "provider_routing": _safe_value(get_config_value(self.config, "llm.provider_routing", {})),
                "router_metadata": bool(get_config_value(self.config, "llm.router_metadata", True)),
                "mode": get_config_value(self.config, "extraction.mode", "one_pass"),
                "expression_mode": get_config_value(self.config, "extraction.expression_mode", "generator"),
                "concurrency": get_config_value(self.config, "extraction.concurrency", 1),
                "max_tokens": get_config_value(self.config, "llm.max_tokens", 24000),
                "critic_max_tokens": get_config_value(self.config, "llm.critic_max_tokens", 8000),
            },
        )

    def finish(self, *, outcome: str, error: str | None = None) -> None:
        """Write the run-level completion record and close the file handler."""
        payload: dict[str, Any] = {
            "document_id": self.document_id,
            "tax_year": str(self.year),
            "outcome": outcome,
            "duration_ms": round((time.perf_counter() - self.started_monotonic) * 1000, 3),
            "totals": {
                "calls": self.calls,
                "successful_calls": self.successful_calls,
                "failed_calls": self.failed_calls,
                "total_tokens": self.total_tokens if self.known_token_calls else None,
                "total_cost": round(self.total_cost, 10) if self.known_cost_calls else None,
            },
        }
        if error:
            payload["error"] = error
        self.emit(
            "run_end",
            level=logging.ERROR if outcome == "failed" else logging.INFO,
            **payload,
        )
        self._handler.flush()
        self._logger.removeHandler(self._handler)
        self._handler.close()

    def record_call(
        self,
        *,
        document_id: str,
        target_cell_id: str | None = None,
        purpose: str,
        requested_model: str,
        telemetry: Any = None,
        request_body: Any = None,
        response_body: Any = None,
        outcome: str,
        latency_ms: float | None,
        error: str | None = None,
    ) -> None:
        """Write one provider-call record and update run totals."""
        with self._lock:
            self.calls += 1
            if outcome == "success":
                self.successful_calls += 1
            else:
                self.failed_calls += 1
            total_tokens = _value(telemetry, "total_tokens")
            cost = _value(telemetry, "cost")
            if total_tokens is not None:
                self.total_tokens += int(total_tokens)
                self.known_token_calls += 1
            if cost is not None:
                self.total_cost += float(cost)
                self.known_cost_calls += 1

        call: dict[str, Any] = {
            "document_id": document_id,
            "target_cell_id": target_cell_id or _CURRENT_TARGET_CELL.get(),
            "purpose": purpose,
            "requested_model": requested_model,
            "resolved_model": _value(telemetry, "resolved_model"),
            "resolved_provider": _value(telemetry, "resolved_provider"),
            "prompt_tokens": _value(telemetry, "prompt_tokens"),
            "completion_tokens": _value(telemetry, "completion_tokens"),
            "total_tokens": _value(telemetry, "total_tokens"),
            "cost": _value(telemetry, "cost"),
            "finish_reason": _value(telemetry, "finish_reason"),
            "latency_ms": latency_ms,
            "outcome": outcome,
        }
        if error:
            call["error"] = error
        include_bodies = (
            purpose == "tax_graph_micro_formula"
            or outcome != "success"
            or self._logger.isEnabledFor(logging.DEBUG)
        )
        if include_bodies:
            call["request_body"] = _safe_value(request_body)
            call["response_body"] = _safe_value(response_body)
        self.emit(
            "llm_call",
            level=logging.ERROR if outcome != "success" else logging.INFO,
            **call,
        )

    def emit(self, event: str, *, level: int = logging.INFO, **payload: Any) -> None:
        """Write one structured event with a UTC timestamp and run id."""
        event_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "event": event,
            **payload,
        }
        self._logger.log(level, event, extra={"payload": event_payload})


@contextmanager
def extraction_run(
    *,
    root: str | Path,
    document_id: str,
    year: str | int,
    config: dict[str, Any],
) -> Iterator[RunLogger]:
    """Install a run context and close it with an honest success/failure record."""
    recorder = RunLogger(root=Path(root), document_id=document_id, year=year, config=config)
    token = _CURRENT_RUN.set(recorder)
    recorder.start()
    try:
        yield recorder
    except Exception as exc:
        recorder.finish(outcome="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    else:
        outcome = "success" if recorder.failed_calls == 0 else "completed_with_call_failures"
        recorder.finish(outcome=outcome)
    finally:
        _CURRENT_RUN.reset(token)


def current_run() -> RunLogger | None:
    """Return the current extraction run recorder, if one is installed."""
    return _CURRENT_RUN.get()


@contextmanager
def llm_call_target(target_cell_id: str | None) -> Iterator[None]:
    """Attach the stable target cell to calls made inside this context."""
    token = _CURRENT_TARGET_CELL.set(target_cell_id)
    try:
        yield
    finally:
        _CURRENT_TARGET_CELL.reset(token)


def log_llm_call(**kwargs: Any) -> None:
    """Record a provider call when the caller is inside an extraction run."""
    recorder = current_run()
    if recorder is not None:
        if kwargs.get("document_id") in {None, "", "unknown"}:
            kwargs["document_id"] = recorder.document_id
        kwargs.setdefault("target_cell_id", _CURRENT_TARGET_CELL.get())
        recorder.record_call(**kwargs)


def _configured_level(config: dict[str, Any]) -> int:
    raw = str(get_config_value(config, "logging.level", "INFO")).strip().upper()
    return getattr(logging, raw, logging.INFO)


def _value(value: Any, key: str) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _safe_value(value: Any, *, key: str = "") -> Any:
    """Convert provider objects to capped, key-redacted JSON-safe values."""
    if key.lower() in _SENSITIVE_KEYS:
        return _REDACTED
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        if len(value) <= _MAX_LOG_STRING_CHARS:
            return value
        return value[:_MAX_LOG_STRING_CHARS] + "...[truncated]"
    if isinstance(value, dict):
        return {str(item_key): _safe_value(item_value, key=str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _safe_value(model_dump())
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _safe_value(to_dict())
    values = getattr(value, "__dict__", None)
    if isinstance(values, dict):
        return _safe_value(values)
    return str(value)
