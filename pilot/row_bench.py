"""Inspect one or more real derivation rows without changing project state.

Replay reads attempted payloads from a derivation report and validates them
again for free. Live calls the configured provider for exactly one row through
the production ``derive_cells`` path. Both modes print only prompts, response
payloads, and validation verdicts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tax_graph.acquire.manifest import load_manifest
from tax_graph.config import (
    get_config_value,
    load_config,
    resolve_llm_model,
    resolve_llm_seed,
)
from tax_graph.extract.cells import (
    CellFrame,
    CellRecord,
    CellValidationIssue,
    _apply_payload,
    _exception_issue,
    _repair_prompt,
    _render_cell_prompt,
    build_reference_inventory,
    build_cell_frame_from_document,
    derive_cells,
    load_cell_prompt,
    validate_cell_output,
)
from tax_graph.extract.inputs import load_document_input
from tax_graph.io.loader import load_graph


MAX_DEPTH = 3


def _load_context(
    *,
    root: Path,
    year: str,
    document_id: str,
) -> tuple[str, CellFrame, Mapping[str, Any]]:
    """Load the same source frame, prompt, and inventory used by derivation."""
    config = load_config(root=root)
    document = load_document_input(
        document_id,
        year=year,
        root=root,
        config=config,
    )
    frame = build_cell_frame_from_document(document)
    prompt = load_cell_prompt(config, root=root)
    inventory = build_reference_inventory(
        load_graph(year, root),
        manifest=load_manifest(root=root),
    )
    return prompt, frame, inventory


def _report_path(run_dir: Path, document_id: str) -> Path:
    """Find the one derivation report for a document in a run directory."""
    candidates = sorted(run_dir.glob(f"*_{document_id}_derive_cells_report.yaml"))
    if len(candidates) != 1:
        raise FileNotFoundError(
            f"expected one derivation report for {document_id} in {run_dir}, "
            f"found {len(candidates)}"
        )
    return candidates[0]


def _report_rows(run_dir: Path, document_id: str) -> dict[str, list[Mapping[str, Any]]]:
    """Load report rows keyed by printed line, retaining skipped duplicates."""
    path = _report_path(run_dir, document_id)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = data.get("rows_detail") or []
    result: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        line = str(row.get("line") or "").strip().lower()
        if not line:
            continue
        result.setdefault(line, []).append(row)
    return result


def _report_row_for(
    row: CellRecord,
    report_rows: Mapping[str, Sequence[Mapping[str, Any]]],
) -> Mapping[str, Any]:
    """Choose the non-skipped report row for an anchor when headers repeat it."""
    candidates = list(report_rows.get(row.line.strip().lower()) or ())
    if not candidates:
        raise KeyError(f"line {row.line} is absent from the derivation report")
    if len(candidates) == 1:
        return candidates[0]
    non_skipped = [item for item in candidates if item.get("status") != "skipped"]
    if len(non_skipped) == 1:
        return non_skipped[0]
    raise ValueError(f"report has an unresolved duplicate for line {row.line}")


def _select_rows(frame: CellFrame, lines: Sequence[str]) -> list[CellRecord]:
    """Select unique frame rows by case-insensitive printed anchor."""
    selected: list[CellRecord] = []
    for requested in lines:
        line = str(requested).strip().lower()
        matches = [row for row in frame.rows if row.line.strip().lower() == line]
        if len(matches) != 1:
            raise ValueError(
                f"expected one frame row for line {line}, found {len(matches)}"
            )
        selected.append(matches[0])
    return selected


def _issue_text(issue: CellValidationIssue) -> str:
    """Render one issue in the same compact form as production repair prompts."""
    return f"{issue.kind}: {issue.message}"


def _issue_dict(issue: CellValidationIssue) -> dict[str, Any]:
    """Return a JSON-ready issue for test and output consumers."""
    return issue.as_dict()


def replay_payload(
    row: CellRecord,
    payload: Any,
    *,
    reference_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply and validate one recorded payload using production validators."""
    candidate = CellRecord.from_mapping(row.as_dict())
    if not isinstance(payload, Mapping):
        issue = CellValidationIssue("payload", "provider returned a non-object payload")
        return {
            "accepted": False,
            "issues": (issue,),
            "warnings": (),
            "apply_error": _issue_text(issue),
        }
    try:
        _apply_payload(
            candidate,
            payload,
            max_depth=MAX_DEPTH,
            provider="row-bench",
            model=None,
        )
    except Exception as exc:  # noqa: BLE001 - display the production boundary
        issue = _exception_issue(exc)
        return {
            "accepted": False,
            "issues": (issue,),
            "warnings": (),
            "apply_error": _issue_text(issue),
        }
    hard, warnings = validate_cell_output(
        candidate,
        candidate.expression,
        candidate.quote,
        max_depth=MAX_DEPTH,
        reference_inventory=reference_inventory,
    )
    return {
        "accepted": not hard,
        "issues": hard,
        "warnings": warnings,
        "apply_error": None,
    }


def _attempt_prompt(
    base_prompt: str,
    row: CellRecord,
    first_verdict: Mapping[str, Any] | None,
) -> str:
    """Build the exact production repair prompt from the first verdict."""
    if not first_verdict:
        return base_prompt
    issues = first_verdict.get("issues") or ()
    if not issues:
        return base_prompt
    return _repair_prompt(base_prompt, row, issues)


def _format_payload(payload: Any) -> str:
    """Display the parsed provider payload without changing its values."""
    if payload is None:
        return "(no recorded response)"
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _format_verdict(
    verdict: Mapping[str, Any] | None,
    *,
    recorded_status: str,
    recorded_error: str | None,
) -> list[str]:
    """Format a payload verdict or a source-side no-call result."""
    lines = [f"recorded_status: {recorded_status}"]
    if recorded_error:
        lines.append(f"recorded_error: {recorded_error}")
    if verdict is None:
        lines.append("validation: not reached; production made no provider call")
        return lines
    lines.append(f"validation: {'accepted' if verdict['accepted'] else 'rejected'}")
    apply_error = verdict.get("apply_error")
    if apply_error:
        lines.append(f"payload_boundary: {apply_error}")
    issues = verdict.get("issues") or ()
    lines.append("hard_failures:")
    if issues:
        lines.extend(f"- {_issue_text(issue)}" for issue in issues)
    else:
        lines.append("- none")
    warnings = verdict.get("warnings") or ()
    lines.append("warnings:")
    if warnings:
        lines.extend(f"- {_issue_text(issue)}" for issue in warnings)
    else:
        lines.append("- none")
    return lines


def _screen(
    *,
    document_id: str,
    row: CellRecord,
    base_prompt: str,
    attempts: Sequence[tuple[str, str, Any, Mapping[str, Any] | None]],
    recorded_status: str,
    recorded_error: str | None,
) -> str:
    """Render one row as a prompt/response/verdict screen."""
    output = [f"=== {document_id} line {row.line} ==="]
    if not attempts:
        output.extend(
            [
                "prompt (not sent):",
                base_prompt,
                "response:",
                "(no recorded response)",
                "verdict:",
                *_format_verdict(
                    None,
                    recorded_status=recorded_status,
                    recorded_error=recorded_error,
                ),
            ]
        )
        return "\n".join(output)
    for index, (attempt, prompt, payload, verdict) in enumerate(attempts):
        if index:
            output.append("")
        output.extend(
            [
                f"prompt ({attempt}):",
                prompt,
                f"response ({attempt}):",
                _format_payload(payload),
                f"verdict ({attempt}):",
                *_format_verdict(
                    verdict,
                    recorded_status=recorded_status,
                    recorded_error=recorded_error,
                ),
            ]
        )
    return "\n".join(output)


def replay_rows(
    *,
    root: str | Path,
    year: str,
    document_id: str,
    lines: Sequence[str],
    run_dir: str | Path,
) -> list[str]:
    """Replay recorded attempts and return one output screen per row."""
    root_path = Path(root).resolve()
    prompt, frame, inventory = _load_context(
        root=root_path,
        year=year,
        document_id=document_id,
    )
    report_rows = _report_rows(Path(run_dir).resolve(), document_id)
    screens: list[str] = []
    for row in _select_rows(frame, lines):
        report_row = _report_row_for(row, report_rows)
        recorded_attempts = report_row.get("attempted_payloads") or []
        attempts: list[tuple[str, str, Any, Mapping[str, Any] | None]] = []
        first_verdict: Mapping[str, Any] | None = None
        base_prompt = _render_cell_prompt(
            prompt,
            row,
            reference_inventory=inventory,
        )
        for item in recorded_attempts:
            if not isinstance(item, Mapping):
                continue
            attempt = str(item.get("attempt") or "first")
            payload = item.get("payload")
            verdict = replay_payload(
                row,
                payload,
                reference_inventory=inventory,
            )
            if attempt == "first":
                first_verdict = verdict
            attempt_prompt = (
                base_prompt
                if attempt == "first"
                else _attempt_prompt(base_prompt, row, first_verdict)
            )
            attempts.append((attempt, attempt_prompt, payload, verdict))
        screens.append(
            _screen(
                document_id=document_id,
                row=row,
                base_prompt=base_prompt,
                attempts=attempts,
                recorded_status=str(report_row.get("status") or "unknown"),
                recorded_error=(
                    str(report_row.get("error"))
                    if report_row.get("error") is not None
                    else None
                ),
            )
        )
    return screens


class _CaptureClient:
    """Delegate a live client while retaining exact prompts and responses."""

    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate
        self.calls: list[dict[str, Any]] = []

    def structured_completion(self, **request: Any) -> Any:
        call: dict[str, Any] = {"prompt": request["prompt"]}
        try:
            response = self.delegate.structured_completion(**request)
        except Exception as exc:  # noqa: BLE001 - derive_cells records row errors
            call["error"] = f"{type(exc).__name__}: {exc}"
            self.calls.append(call)
            raise
        call["response"] = response
        self.calls.append(call)
        return response


def _config_temperature(config: Mapping[str, Any]) -> float | None:
    """Read temperature while preserving an explicit zero."""
    value = get_config_value(config, "llm.temperature")
    if value is None or value == "":
        return None
    return float(value)


def live_row(
    *,
    root: str | Path,
    year: str,
    document_id: str,
    line: str,
) -> str:
    """Call the provider through derive_cells for one row."""
    from tax_graph.extract.llm_client import build_llm_client

    root_path = Path(root).resolve()
    config = load_config(root=root_path)
    prompt, frame, inventory = _load_context(
        root=root_path,
        year=year,
        document_id=document_id,
    )
    row = _select_rows(frame, [line])[0]
    delegate = build_llm_client(config)
    capture = _CaptureClient(delegate)
    result = derive_cells(
        CellFrame([row]),
        prompt,
        None,
        client=capture,
        model=resolve_llm_model(config, "micro"),
        provider=str(get_config_value(config, "llm.provider", "configured-provider")),
        temperature=_config_temperature(config),
        seed=resolve_llm_seed(config),
        reference_inventory=inventory,
    )
    result_row = result.rows[0]
    attempts: list[tuple[str, str, Any, Mapping[str, Any] | None]] = []
    for index, call in enumerate(capture.calls):
        attempt = "first" if index == 0 else "repair"
        payload = None
        if "response" in call:
            response = call["response"]
            payload = getattr(response, "payload", response)
        verdict = (
            replay_payload(row, payload, reference_inventory=inventory)
            if "response" in call
            else None
        )
        attempts.append(
            (
                attempt,
                call["prompt"],
                payload,
                verdict,
            )
        )
    if not capture.calls:
        base_prompt = _render_cell_prompt(
            prompt,
            row,
            reference_inventory=inventory,
        )
    else:
        base_prompt = capture.calls[0]["prompt"]
    return _screen(
        document_id=document_id,
        row=row,
        base_prompt=base_prompt,
        attempts=attempts,
        recorded_status=result_row.status,
        recorded_error=result_row.error,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run replay or one live row bench."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document_id")
    parser.add_argument("--line", action="append", required=True, dest="lines")
    parser.add_argument("--mode", choices=("replay", "live"), default="replay")
    parser.add_argument("--run-dir", help="derivation run directory for replay mode")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--year", default="2025")
    args = parser.parse_args(argv)
    if args.mode == "replay" and not args.run_dir:
        parser.error("--run-dir is required in replay mode")
    if args.mode == "live" and len(args.lines) != 1:
        parser.error("live mode accepts exactly one --line")
    if args.mode == "replay":
        screens = replay_rows(
            root=args.root,
            year=args.year,
            document_id=args.document_id,
            lines=args.lines,
            run_dir=args.run_dir,
        )
    else:
        screens = [
            live_row(
                root=args.root,
                year=args.year,
                document_id=args.document_id,
                line=args.lines[0],
            )
        ]
    print("\n\n".join(screens))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
