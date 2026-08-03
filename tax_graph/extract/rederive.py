"""Single-cell human-loop re-derivation entry points.

This module is the live, non-persisting boundary used by the review workbench.
It loads one acquired document, selects one printed line, applies either a
trial comment or the newest curated comment, and delegates to the pure
``derive_cells`` function.  The result is returned to the caller; no draft,
graph, review ledger, or other project state is written here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from tax_graph.config import get_config_value, load_config, project_root
from tax_graph.extract.cells import (
    CellFrame,
    build_cell_frame_from_document,
    derive_cells,
    load_cell_prompt,
)
from tax_graph.extract.inputs import load_document_input
from tax_graph.extract.llm_client import build_llm_client


def rederive_cell(
    document_id: str,
    line: str,
    draft_comment: str | None = None,
    *,
    year: str | int = "2025",
    root: str | Path | None = None,
    config: Mapping[str, Any] | None = None,
    api_key: str | None = None,
    client: Any | None = None,
    comment_history: Iterable[Mapping[str, Any]] | None = None,
    raw_store: str | Path | None = None,
) -> dict[str, Any]:
    """Derive one document line with an optional unpersisted human comment.

    ``draft_comment`` is deliberately distinct from ``comment_history``.  A
    draft is the reviewer's current try-again input and wins even when it is an
    empty string.  When no draft is supplied, only the latest curated ledger
    comment for the resolved canonical address is applied.  Contributed and
    legacy comments are never sent to the model.
    """
    document_value = str(document_id).strip()
    line_value = str(line).strip().lower()
    if not document_value:
        raise ValueError("document_id is required")
    if not line_value:
        raise ValueError("line is required")

    root_path = Path(root).resolve() if root is not None else project_root()
    settings = dict(config) if config is not None else load_config(root=root_path)
    document = load_document_input(
        document_value,
        year=year,
        root=root_path,
        config=settings,
        raw_store=raw_store,
    )
    frame = build_cell_frame_from_document(document)
    matches = [row for row in frame.rows if str(row.line).lower() == line_value]
    if len(matches) != 1:
        raise ValueError(
            f"document line must resolve to exactly one derivable cell: "
            f"{document_value}:{line_value} (found {len(matches)})"
        )

    row = matches[0]
    row.canonical_address = _canonical_formula_address(
        root_path, year, document_value, line_value,
    )
    comment_source = "none"
    if draft_comment is not None:
        row.human_comment = str(draft_comment)
        comment_source = "draft"
    elif comment_history is not None:
        curated = _latest_curated_comment(row.canonical_address, comment_history)
        if curated:
            row.human_comment = curated
            comment_source = "curated"

    active_client = client
    if active_client is None:
        active_client = build_llm_client(settings)
    prompt = load_cell_prompt(settings, root=root_path)
    result = derive_cells(
        CellFrame.from_rows([row]),
        prompt,
        api_key,
        client=active_client,
        model=str(
            get_config_value(
                settings,
                "llm.micro_model",
                get_config_value(settings, "llm.model", "configured-llm"),
            )
        ),
        provider=str(get_config_value(settings, "llm.provider", "configured-provider")),
        max_tokens=int(get_config_value(settings, "extraction.micro_max_tokens", 4000)),
        temperature=_optional_temperature(settings),
    )
    if not isinstance(result, CellFrame):
        raise TypeError("single-cell derivation returned an unexpected result")
    derived = result.rows[0]
    return {
        "document_id": document_value,
        "line": line_value,
        "address": row.canonical_address,
        "comment_source": comment_source,
        "comment": row.human_comment or None,
        "result": derived.as_dict(),
        "validation": result.validation_report,
    }


def build_rederive_handler(
    root: str | Path,
    year: str | int,
    *,
    config: Mapping[str, Any] | None = None,
    api_key: str | None = None,
    client: Any | None = None,
) -> Any:
    """Build a workbench callback that reads the current curated ledger.

    The callback keeps the artifact-only workbench free of pipeline imports.
    Its closure is owned by the application host, which may pass it to
    ``workbench.server.create_app``.
    """
    root_path = Path(root).resolve()

    def handler(document_id: str, line: str, draft_comment: str | None = None) -> dict[str, Any]:
        from workbench.address_verdicts import load_address_verdicts, verdict_store_path

        ledger_path = verdict_store_path(root_path, year)
        history = load_address_verdicts(ledger_path) if ledger_path.is_file() else []
        return rederive_cell(
            document_id,
            line,
            draft_comment,
            year=year,
            root=root_path,
            config=config,
            api_key=api_key,
            client=client,
            comment_history=history,
        )

    return handler


def _latest_curated_comment(address: str, history: Iterable[Mapping[str, Any]]) -> str | None:
    """Read the bounded curated-comment projection without importing at module load."""
    from workbench.address_verdicts import latest_curated_comment

    return latest_curated_comment(address, history)


def _canonical_formula_address(
    root: Path,
    year: str | int,
    document_id: str,
    line: str,
) -> str:
    """Resolve a formula line to its stable flow address when one is mapped."""
    field_map = root / "graph" / str(year) / "field_maps" / f"{document_id}.yaml"
    if field_map.is_file():
        payload = yaml.safe_load(field_map.read_text(encoding="utf-8")) or {}
        mappings = payload.get("mappings", []) if isinstance(payload, dict) else []
        candidates = [
            str(item.get("address_id"))
            for item in mappings
            if isinstance(item, dict)
            and str(item.get("address_id") or "").lower().find(f"/line={line}/") >= 0
            and str(item.get("address_id") or "").lower().endswith("/control=amount")
        ]
        if candidates:
            return sorted(candidates)[0]
    base_document = document_id.removesuffix(f"_{year}")
    return f"{year}/document={base_document}/line={line}/control=amount"


def _optional_temperature(settings: Mapping[str, Any]) -> float | None:
    """Return configured temperature while preserving the provider default."""
    value = get_config_value(settings, "llm.temperature")
    return None if value is None else float(value)
