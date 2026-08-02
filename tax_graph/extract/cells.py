"""Pure cell derivation and deterministic expression-tree projection.

The cell frame is the narrow boundary between source joins and graph assembly.
``derive_cells`` calls a caller-supplied provider and returns a new frame; it
never writes drafts, graph files, logs, or review state.  A provider failure
is recorded on the affected row so one bad request cannot erase the rest of a
run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Protocol, Sequence

from tax_graph.config import get_config_value
from tax_graph.extract.llm_client import LlmClient, response_telemetry
from tax_graph.extract.prompts import load_prompt_template


CELL_INPUT_FIELDS = (
    "form",
    "line",
    "label",
    "form_face_text",
    "instruction_text",
    "instruction_locator",
)


class CellClientFactory(Protocol):
    """Build a provider client from the resolved API key."""

    def __call__(self, api_key: str) -> LlmClient:
        """Return a configured structured-completion client."""


@dataclass
class CellRecord:
    """One input or derived cell, kept JSON-compatible at the edges."""

    form: str
    line: str
    label: str = ""
    form_face_text: str = ""
    instruction_text: str = ""
    instruction_locator: str = ""
    expression: dict[str, Any] | None = None
    rendered: str = ""
    quote: str = ""
    quote_span_id: str = ""
    status: str = "pending"
    error: str | None = None
    model: str | None = None
    provider: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CellRecord":
        """Build a record while preserving unknown source metadata."""
        missing = [key for key in CELL_INPUT_FIELDS if key not in value]
        if missing:
            raise ValueError(f"cell is missing required fields: {', '.join(missing)}")
        known = {
            "form",
            "line",
            "label",
            "form_face_text",
            "instruction_text",
            "instruction_locator",
            "expression",
            "rendered",
            "quote",
            "quote_span_id",
            "status",
            "error",
            "model",
            "provider",
            "prompt_tokens",
            "completion_tokens",
            "cost",
            "metadata",
        }
        return cls(
            **{key: value.get(key, getattr(cls, key, "")) for key in CELL_INPUT_FIELDS},
            expression=value.get("expression"),
            rendered=str(value.get("rendered") or ""),
            quote=str(value.get("quote") or ""),
            quote_span_id=str(value.get("quote_span_id") or ""),
            status=str(value.get("status") or "pending"),
            error=value.get("error"),
            model=value.get("model"),
            provider=value.get("provider"),
            prompt_tokens=_optional_int(value.get("prompt_tokens")),
            completion_tokens=_optional_int(value.get("completion_tokens")),
            cost=_optional_float(value.get("cost")),
            metadata={
                key: item
                for key, item in value.items()
                if key not in known
            } | dict(value.get("metadata") or {}),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a stable JSON-ready row without serializing provider objects."""
        result = {
            "form": self.form,
            "line": self.line,
            "label": self.label,
            "form_face_text": self.form_face_text,
            "instruction_text": self.instruction_text,
            "instruction_locator": self.instruction_locator,
            "expression": self.expression,
            "rendered": self.rendered,
            "quote": self.quote,
            "quote_span_id": self.quote_span_id,
            "status": self.status,
            "error": self.error,
            "model": self.model,
            "provider": self.provider,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost": self.cost,
        }
        result.update(self.metadata)
        return result


@dataclass
class CellFrame:
    """A typed list of cell records with a small coverage report."""

    rows: list[CellRecord]

    @classmethod
    def from_rows(cls, rows: Iterable[CellRecord | Mapping[str, Any]]) -> "CellFrame":
        """Normalize mappings at the frame boundary."""
        return cls([
            row if isinstance(row, CellRecord) else CellRecord.from_mapping(row)
            for row in rows
        ])

    @property
    def coverage(self) -> dict[str, int]:
        """Count row outcomes without turning failures into a run-level exception."""
        counts: dict[str, int] = {"total": len(self.rows)}
        for row in self.rows:
            counts[row.status] = counts.get(row.status, 0) + 1
        return counts

    def as_dicts(self) -> list[dict[str, Any]]:
        """Return rows for JSON/markdown consumers."""
        return [row.as_dict() for row in self.rows]


def load_cell_prompt(
    config: Mapping[str, Any] | None = None,
    *,
    root: str | Path | None = None,
) -> str:
    """Load the cell prompt from config, with one documented project default."""
    settings = dict(config or {})
    path = get_config_value(
        settings,
        "extraction.prompts.cells",
        "prompts/derive_cells.md",
    )
    return load_prompt_template(path, root=root)


def derive_cells(
    frame: CellFrame | Sequence[CellRecord | Mapping[str, Any]],
    prompt: str,
    api_key: str | None,
    *,
    client: LlmClient | None = None,
    client_factory: CellClientFactory | None = None,
    model: str = "configured-llm",
    provider: str = "configured-provider",
    operations: Sequence[str] | None = None,
    max_depth: int = 2,
    max_tokens: int = 4000,
    temperature: float | None = None,
) -> CellFrame | list[dict[str, Any]]:
    """Derive every cell independently and return a new frame.

    ``client`` is the provider-agnostic seam used by production callers and
    fixture tests.  ``client_factory`` can construct it from ``api_key`` when
    the caller owns provider configuration.  With neither supplied, rows are
    marked ``error`` rather than silently selecting a vendor or writing state.
    A list input returns a list for compatibility with lightweight callers;
    a ``CellFrame`` input returns a ``CellFrame``.
    """
    input_is_frame = isinstance(frame, CellFrame)
    source = frame if input_is_frame else CellFrame.from_rows(frame)
    result_rows: list[CellRecord] = []
    active_client = client
    client_error: str | None = None
    if active_client is None and client_factory is not None:
        if not api_key:
            client_error = "missing api key for configured cell provider"
        else:
            try:
                active_client = client_factory(api_key)
            except Exception as exc:  # noqa: BLE001 - row-level failure contract
                client_error = f"client construction failed: {type(exc).__name__}: {exc}"
    if active_client is None and client_error is None:
        client_error = (
            "no configured cell provider client; pass client or client_factory "
            "instead of selecting a provider implicitly"
        )

    schema = expression_schema(list(operations or DEFAULT_OPERATIONS), depth=max_depth)
    for original in source.rows:
        row = CellRecord.from_mapping(original.as_dict())
        if client_error:
            _mark_error(row, client_error, provider=provider, model=model)
            result_rows.append(row)
            continue
        try:
            rendered_prompt = _render_cell_prompt(prompt, row)
            response = active_client.structured_completion(
                prompt=rendered_prompt,
                schema=schema,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                purpose="tax_graph_cell_derivation",
            )
            payload = getattr(response, "payload", response)
            if not isinstance(payload, Mapping):
                raise ValueError("provider returned a non-object payload")
            _apply_payload(
                row,
                payload,
                max_depth=max_depth,
                provider=provider,
                model=model,
            )
            telemetry = response_telemetry(response)
            if telemetry is not None:
                row.provider = telemetry.resolved_provider or telemetry.provider
                row.model = telemetry.resolved_model or telemetry.requested_model
                row.prompt_tokens = telemetry.prompt_tokens
                row.completion_tokens = telemetry.completion_tokens
                row.cost = telemetry.cost
            result_rows.append(row)
        except Exception as exc:  # noqa: BLE001 - one row must not fail the frame
            _mark_error(row, f"{type(exc).__name__}: {exc}", provider=provider, model=model)
            result_rows.append(row)

    output = CellFrame(result_rows)
    return output if input_is_frame else output.as_dicts()


def _apply_payload(
    row: CellRecord,
    payload: Mapping[str, Any],
    *,
    max_depth: int,
    provider: str,
    model: str,
) -> None:
    expression = payload.get("expression")
    quote = payload.get("quote")
    validate_expression_tree(expression, max_depth=max_depth)
    if not isinstance(quote, str) or not quote.strip():
        raise ValueError("quote must be a non-empty string")
    known_spans = _known_quote_spans(row, quote)
    if not known_spans:
        raise ValueError("quote is not verbatim from the cell evidence")
    quote_span_id = str(payload.get("quote_span_id") or known_spans[0][0])
    if quote_span_id not in {span_id for span_id, _source in known_spans}:
        raise ValueError("quote_span_id is not a known input evidence span")
    row.expression = dict(expression)
    row.rendered = render(expression)
    row.quote = quote
    row.quote_span_id = quote_span_id
    row.status = "derived"
    row.error = None
    row.provider = provider
    row.model = model


def validate_expression_tree(node: Any, *, max_depth: int = 2) -> None:
    """Validate a bounded tree without recursive JSON Schema references."""
    if not isinstance(node, Mapping):
        raise ValueError("expression must be an object")
    _validate_tree_node(node, depth=0, max_depth=max_depth)


def _validate_tree_node(node: Mapping[str, Any], *, depth: int, max_depth: int) -> None:
    if "form" in node and "line" in node:
        if set(node) != {"form", "line"} or not str(node["form"]).strip() or not str(node["line"]).strip():
            raise ValueError("cross-form operand requires form and line")
        return
    if "line" in node:
        if set(node) != {"line"} or not str(node["line"]).strip():
            raise ValueError("line operand must contain only a non-empty line")
        return
    if "const" in node:
        if set(node) != {"const"} or not isinstance(node["const"], (int, float)) or isinstance(node["const"], bool):
            raise ValueError("const operand must contain one numeric value")
        return
    if set(node) != {"op", "args"}:
        raise ValueError("expression nodes require only op and args")
    op = str(node.get("op") or "").upper()
    if op not in DEFAULT_OPERATIONS:
        raise ValueError(f"unsupported expression operation: {op}")
    args = node.get("args")
    if not isinstance(args, list) or not args:
        raise ValueError(f"{op} requires at least one argument")
    if depth >= max_depth:
        if any(isinstance(arg, Mapping) and "op" in arg for arg in args):
            raise ValueError("expression tree exceeds configured depth")
    expected = {"COPY": 1, "NEGATE": 1, "ABS": 1, "ROUND": 1, "REQUIRE_INPUT": 1,
                "NOT": 1, "SUBTRACT": 2, "DIVIDE": 2, "MULTIPLY": 2,
                "COMPARE": 2, "IF": 2, "IF_ELSE": 4}
    if op in expected and len(args) != expected[op]:
        raise ValueError(f"{op} requires exactly {expected[op]} arguments")
    for arg in args:
        if not isinstance(arg, Mapping):
            raise ValueError("expression arguments must be objects")
        _validate_tree_node(arg, depth=depth + 1, max_depth=max_depth)


DEFAULT_OPERATIONS = (
    "COPY", "SUM", "SUBTRACT", "MULTIPLY", "DIVIDE", "MIN", "MAX", "NEGATE",
    "ABS", "ROUND", "LOOKUP_TABLE", "LOOKUP_BRACKET", "IF", "IF_ELSE", "AND",
    "OR", "NOT", "COMPARE", "REQUIRE_INPUT",
)


def expression_schema(operations: Sequence[str] | None = None, depth: int = 2) -> dict[str, Any]:
    """Build a bounded nested expression schema without recursive ``$ref``."""
    allowed = list(operations or DEFAULT_OPERATIONS)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["expression", "quote"],
        "properties": {
            "expression": _expression_node_schema(allowed, depth),
            "quote": {"type": "string", "minLength": 1},
            "quote_span_id": {"type": "string", "minLength": 1},
        },
    }


def _expression_node_schema(operations: list[str], depth: int) -> dict[str, Any]:
    operands: list[dict[str, Any]] = [
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["line"],
            "properties": {"line": {"type": "string", "minLength": 1}},
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["form", "line"],
            "properties": {
                "form": {"type": "string", "minLength": 1},
                "line": {"type": "string", "minLength": 1},
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["const"],
            "properties": {"const": {"type": "number"}},
        },
    ]
    if depth > 0:
        operands.append(_expression_node_schema(operations, depth - 1))
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["op", "args"],
        "properties": {
            "op": {"type": "string", "enum": operations},
            "args": {"type": "array", "minItems": 1, "items": {"anyOf": operands}},
        },
    }

INFIX = {"SUM": " + ", "SUBTRACT": " - ", "MULTIPLY": " * ", "DIVIDE": " / "}


def render(node: Mapping[str, Any], in_infix: bool = False) -> str:
    """Render a validated expression tree for review and graph labels."""
    if "form" in node and "line" in node:
        return f"{node['form']} line {node['line']}"
    if "line" in node:
        return f"line {node['line']}"
    if "const" in node:
        value = node["const"]
        return str(int(value)) if float(value).is_integer() else str(value)
    op = str(node.get("op", "?")).upper()
    args = [render(arg, in_infix=op in INFIX and len(node.get("args") or []) > 1) for arg in node.get("args") or []]
    if op in INFIX and len(args) > 1:
        body = INFIX[op].join(args)
        return f"({body})" if in_infix else body
    return f"{op.lower()}({', '.join(args)})"


@dataclass(frozen=True)
class GraphProjection:
    """Deterministic graph objects produced from one derived expression."""

    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    rules: list[dict[str, Any]]
    findings: list[str]


ROLE_FOR_OP = {
    "SUM": ("addend",),
    "SUBTRACT": ("minuend", "subtrahend"),
    "DIVIDE": ("numerator", "denominator"),
    "MULTIPLY": ("factor",),
    "MAX": ("candidate",),
    "MIN": ("candidate",),
    "COPY": ("source",),
    "NEGATE": ("value",),
}

RULE_FOR_OP = {
    "SUM": "sum_currency",
    "SUBTRACT": "subtract_currency",
    "MULTIPLY": "multiply_currency",
    "DIVIDE": "divide_currency",
    "MIN": "min_currency",
    "MAX": "max_currency",
    "NEGATE": "negate_currency",
    "ABS": "abs_currency",
    "ROUND": "round_currency",
    "COPY": "copy_currency_value",
}


def expression_to_graph(
    *,
    form: str,
    line: str,
    expression: Mapping[str, Any],
    quote_span_id: str = "",
) -> GraphProjection:
    """Flatten a tree into stable intermediate nodes and role-bearing edges."""
    validate_expression_tree(expression)
    converter = _GraphConverter(form, line, quote_span_id)
    converter.walk(expression, converter.target)
    return GraphProjection(converter.nodes, converter.edges, converter.rules, converter.findings)


class _GraphConverter:
    def __init__(self, form: str, line: str, citation: str):
        self.form = _slug(form)
        self.base = f"{self.form}_root_line_{_slug(line)}"
        self.target = self.base
        self.citation = citation
        self.nodes: list[dict[str, Any]] = []
        self.edges: list[dict[str, Any]] = []
        self.rules: list[dict[str, Any]] = []
        self.findings: list[str] = []
        self._steps = 0

    def walk(self, node: Mapping[str, Any], target: str) -> None:
        op = str(node.get("op", "")).upper()
        rule = RULE_FOR_OP.get(op)
        if rule is None:
            self.findings.append(f"no reusable rule for operation {op}")
            rule = f"unmapped_{op.lower()}"
        args = node.get("args") or []
        for index, arg in enumerate(args):
            if isinstance(arg, Mapping) and "op" in arg:
                self._steps += 1
                if op == "MAX" and index == 0 and str(arg.get("op", "")).upper() == "SUBTRACT":
                    intermediate = f"{target}_pre_floor"
                else:
                    intermediate = f"{target}_step{self._steps}"
                self._add_node(intermediate, f"{target} intermediate: {render(arg)}")
                self.walk(arg, intermediate)
                source = intermediate
            else:
                source = self._operand_id(arg)
            role = _role_for(op, index)
            self.edges.append({
                "edge_id": f"e_{_slug(source)}_to_{_slug(target)}_{role}",
                "source": source,
                "target": target,
                "relationship": "CALCULATES",
                "rule_id": rule,
                "role": role,
                **({"citation_refs": [self.citation]} if self.citation else {}),
            })

    def _operand_id(self, operand: Any) -> str:
        if not isinstance(operand, Mapping):
            self.findings.append(f"unrecognised operand: {operand}")
            return f"{self.base}_unresolved"
        if "form" in operand and "line" in operand:
            return f"{_slug(str(operand['form']))}_line_{_slug(str(operand['line']))}"
        if "line" in operand:
            return f"{self.form}_root_line_{_slug(str(operand['line']))}"
        if "const" in operand:
            value = operand["const"]
            suffix = "zero_floor" if float(value) == 0 else f"const_{str(value).replace('.', '_')}"
            node_id = f"{self.form}_{suffix}"
            self._add_node(node_id, f"{self.form} constant {value}", node_type="parameter", constant_value=value)
            return node_id
        self.findings.append(f"unrecognised operand: {operand}")
        return f"{self.base}_unresolved"

    def _add_node(
        self,
        node_id: str,
        label: str,
        *,
        node_type: str = "computed",
        constant_value: Any = None,
    ) -> None:
        if any(node["node_id"] == node_id for node in self.nodes):
            return
        node: dict[str, Any] = {
            "node_id": node_id,
            "document_id": self.form,
            "label": label,
            "node_type": node_type,
            "value_type": "currency",
            "required": "optional",
        }
        if constant_value is not None:
            node["constant_value"] = constant_value
        if self.citation:
            node["citation_refs"] = [self.citation]
        self.nodes.append(node)


def _role_for(operation: str, index: int) -> str:
    roles = ROLE_FOR_OP.get(operation, ("operand",))
    return roles[index] if index < len(roles) else roles[-1]


def _render_cell_prompt(template: str, row: CellRecord) -> str:
    values = {
        "form": row.form,
        "line": row.line,
        "label": row.label,
        "form_face_text": row.form_face_text,
        "instruction_text": row.instruction_text,
        "instruction_locator": row.instruction_locator,
    }
    try:
        return template.format(**values)
    except KeyError as exc:
        raise ValueError(f"cell prompt has unsupported placeholder: {exc.args[0]}") from exc


def _known_quote_spans(row: CellRecord, quote: str) -> list[tuple[str, str]]:
    """Return input-owned span ids whose source contains the returned quote."""
    fallback_span_id = row.instruction_locator
    candidates = [
        (str(row.metadata.get("form_face_span_id") or fallback_span_id or ""), row.form_face_text),
        (
            str(row.metadata.get("instruction_span_id") or fallback_span_id or ""),
            row.instruction_text,
        ),
    ]
    return [
        (span_id, source)
        for span_id, source in candidates
        if span_id and source and _contains_verbatim(source, quote)
    ]


def _contains_verbatim(source: str, quote: str) -> bool:
    if quote in source:
        return True
    normalize = lambda value: " ".join(str(value).split())
    return normalize(quote) in normalize(source)


def _mark_error(row: CellRecord, error: str, *, provider: str, model: str) -> None:
    row.status = "error"
    row.error = error
    row.provider = provider
    row.model = model


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_") or "item"


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
