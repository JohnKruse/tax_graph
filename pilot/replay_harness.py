"""Replay recorded micro-extraction responses through production stages."""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
import zlib

from jsonschema import Draft202012Validator

from tax_graph.extract.assembly import _steps_for_plan, assemble_formula_plan
from tax_graph.extract.micro import extract_formula_plan, formula_micro_schema
from tax_graph.extract.outline import (
    build_candidate_spans,
    build_outline_tree,
)
from tax_graph.extract.outline_pipeline import (
    _formula_outline_nodes,
    _instruction_owner_map,
    _outline_line_index,
    _outline_line_metadata,
    _outline_node_id,
    _spans_for_outline_node,
)
from tax_graph.extract.pipeline import load_document_input


STAGES = (
    "schema_valid",
    "validator_accepted",
    "operands_resolved",
    "rule_and_edges_assembled",
)


class ReplayHarnessError(RuntimeError):
    """Raised when a recorded response cannot be replayed."""


@dataclass(frozen=True)
class ReplayContext:
    """Production evidence and resolution context for one form document."""

    document: Any
    node: Any
    spans: list[Any]
    line_index: dict[Any, str]
    line_kinds: dict[Any, str]
    line_children: dict[Any, list[str]]
    target_cell_id: str


@dataclass(frozen=True)
class ReplayResult:
    """Observed and expected layer outcomes for one recorded cell."""

    case_id: str
    document_id: str
    line_anchor: str
    actual: dict[str, bool]
    expected: dict[str, bool]
    errors: dict[str, str]
    object_kinds: tuple[str, ...] = ()

    @property
    def matches_expectation(self) -> bool:
        """Return whether every declared stage outcome matches the baseline."""
        return self.actual == self.expected


class ReplayClient:
    """Small client seam that returns one recorded provider response."""

    def __init__(self, *, expected_prompt: str, response_text: str) -> None:
        self.expected_prompt = expected_prompt
        self.response_text = response_text
        self.seen_prompt: str | None = None

    def structured_completion(self, **request: Any) -> dict[str, Any]:
        """Check prompt identity and return the recorded JSON response."""
        prompt = request.get("prompt")
        self.seen_prompt = prompt if isinstance(prompt, str) else None
        if prompt != self.expected_prompt:
            raise ReplayHarnessError("production prompt differs from recorded prompt")
        try:
            response = json.loads(self.response_text)
        except json.JSONDecodeError as exc:
            raise ReplayHarnessError(f"recorded response is not JSON: {exc}") from exc
        if not isinstance(response, dict):
            raise ReplayHarnessError("recorded response is not a JSON object")
        return response


def _decode_prompt(case: dict[str, Any]) -> str:
    """Decode the ASCII-only compressed prompt stored in the fixture."""
    encoded = case.get("prompt_zlib_b64")
    if not isinstance(encoded, str) or not encoded:
        raise ReplayHarnessError("fixture case has no compressed prompt")
    try:
        return zlib.decompress(base64.b64decode(encoded)).decode("utf-8")
    except (ValueError, zlib.error, UnicodeDecodeError) as exc:
        raise ReplayHarnessError(f"fixture prompt cannot be decoded: {exc}") from exc


def _load_fixture(path: Path) -> list[dict[str, Any]]:
    """Load and minimally validate the committed replay fixture."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(cases, list) or not cases:
        raise ReplayHarnessError("replay fixture has no cases")
    return cases


def _contexts(root: Path, cases: list[dict[str, Any]]) -> dict[tuple[str, str], ReplayContext]:
    """Build real outline and evidence contexts once per fixture document."""
    contexts: dict[tuple[str, str], ReplayContext] = {}
    document_ids = sorted({str(case["document_id"]) for case in cases})
    for document_id in document_ids:
        document = load_document_input(document_id, year="2025", root=root)
        outline = build_outline_tree(document)
        spans = build_candidate_spans(document)
        owners = _instruction_owner_map(spans)
        nodes = _formula_outline_nodes(outline.children)
        line_index = _outline_line_index(document_id, outline.children)
        line_kinds, line_children = _outline_line_metadata(document_id, outline.children)
        line_anchors = sorted(
            {
                str(case["line_anchor"])
                for case in cases
                if str(case["document_id"]) == document_id
            }
        )
        for line_anchor in line_anchors:
            matching = [node for node in nodes if str(node.line_anchor) == line_anchor]
            if len(matching) != 1:
                raise ReplayHarnessError(
                    f"{document_id} {line_anchor}: expected one formula outline node, found {len(matching)}"
                )
            node = matching[0]
            node_spans = _spans_for_outline_node(
                document,
                node,
                spans,
                document_id=document_id,
                table_mode=node.kind in {"transaction_table", "totals"},
                instruction_owners=owners,
            )
            contexts[(document_id, line_anchor)] = ReplayContext(
                document=document,
                node=node,
                spans=node_spans,
                line_index=line_index,
                line_kinds=line_kinds,
                line_children=line_children,
                target_cell_id=_outline_node_id(document_id, node),
            )
    return contexts


def _schema_valid(response: dict[str, Any], *, root: Path) -> tuple[bool, str | None]:
    """Run the exact production micro schema and return one diagnostic."""
    errors = sorted(
        Draft202012Validator(formula_micro_schema(root=root)).iter_errors(response),
        key=lambda error: list(error.path),
    )
    if not errors:
        return True, None
    error = errors[0]
    location = ".".join(str(part) for part in error.path) or "root"
    return False, f"{location}: {error.message}"


def _message(exc: BaseException) -> str:
    """Keep diagnostics readable and safe for the ASCII project contract."""
    return str(exc).encode("ascii", errors="replace").decode("ascii")[:300]


def _run_case(case: dict[str, Any], context: ReplayContext, *, root: Path) -> ReplayResult:
    """Replay one response through schema, validator, resolver, and assembler."""
    case_id = str(case.get("case_id", f"{case['document_id']}:{case['line_anchor']}"))
    response_text = case.get("response_text")
    if not isinstance(response_text, str):
        raise ReplayHarnessError(f"{case_id}: fixture case has no raw response")
    try:
        response = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ReplayHarnessError(f"{case_id}: raw response is not JSON: {exc}") from exc
    if not isinstance(response, dict):
        raise ReplayHarnessError(f"{case_id}: raw response is not an object")

    actual = {stage: False for stage in STAGES}
    errors: dict[str, str] = {}
    schema_ok, schema_error = _schema_valid(response, root=root)
    actual["schema_valid"] = schema_ok
    if schema_error:
        errors["schema"] = schema_error

    client = ReplayClient(expected_prompt=_decode_prompt(case), response_text=response_text)
    try:
        extract_formula_plan(
            outline_node=context.node,
            spans=context.spans,
            client=client,
            config={"llm": {"micro_model": "replay"}},
            root=root,
            target_cell_id=context.target_cell_id,
        )
        actual["validator_accepted"] = True
    except Exception as exc:
        errors["validator"] = _message(exc)
        if isinstance(exc, ReplayHarnessError):
            errors["prompt"] = _message(exc)

    try:
        _steps_for_plan(
            context.document,
            context.node,
            response,
            context.spans,
            line_index=context.line_index,
            line_kinds=context.line_kinds,
            line_children=context.line_children,
            resolution_events=[],
        )
        actual["operands_resolved"] = True
    except Exception as exc:
        errors["operands"] = _message(exc)

    object_kinds: tuple[str, ...] = ()
    try:
        batch = assemble_formula_plan(
            context.document,
            context.node,
            response,
            context.spans,
            root=root,
            line_index=context.line_index,
            line_kinds=context.line_kinds,
            line_children=context.line_children,
            resolution_events=[],
        )
        object_kinds = tuple(sorted({object.kind for object in batch.objects}))
        if not {"rules", "edges"}.issubset(object_kinds):
            raise ReplayHarnessError(
                f"assembly returned object kinds {','.join(object_kinds) or 'none'}"
            )
        actual["rule_and_edges_assembled"] = True
    except Exception as exc:
        errors["assembly"] = _message(exc)

    expected = {stage: bool(case.get("expected", {}).get(stage)) for stage in STAGES}
    return ReplayResult(
        case_id=case_id,
        document_id=str(case["document_id"]),
        line_anchor=str(case["line_anchor"]),
        actual=actual,
        expected=expected,
        errors=errors,
        object_kinds=object_kinds,
    )


def run_replay(
    *,
    root: str | Path | None = None,
    fixture: str | Path | None = None,
) -> list[ReplayResult]:
    """Run every fixture case without making a provider call."""
    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    fixture_path = Path(fixture) if fixture is not None else project_root / "pilot" / "fixtures" / "m20_s112_replay.json"
    cases = _load_fixture(fixture_path)
    contexts = _contexts(project_root, cases)
    results: list[ReplayResult] = []
    for case in cases:
        key = (str(case.get("document_id")), str(case.get("line_anchor")))
        context = contexts.get(key)
        if context is None:
            raise ReplayHarnessError(f"missing context for {key[0]} {key[1]}")
        results.append(_run_case(case, context, root=project_root))
    return results


def format_result(result: ReplayResult) -> str:
    """Format one case as a layer-by-layer diagnostic line."""
    flags = " ".join(f"{stage}={'Y' if result.actual[stage] else 'N'}" for stage in STAGES)
    suffix = ""
    if result.errors:
        suffix = " errors=" + "; ".join(f"{key}:{value}" for key, value in result.errors.items())
    return f"{result.case_id}: {flags}{suffix}"


def main(argv: list[str] | None = None) -> int:
    """Run the replay harness and return a process status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--fixture", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        results = run_replay(root=args.root, fixture=args.fixture)
    except Exception as exc:
        print(f"replay harness ERROR: {_message(exc)}")
        return 1
    for result in results:
        print(format_result(result))
    mismatches = [result for result in results if not result.matches_expectation]
    print(f"replay cases={len(results)} mismatches={len(mismatches)} network_calls=0")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
