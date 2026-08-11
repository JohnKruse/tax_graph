"""Command-line interface for Tax Graph."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import datetime as _dt
import hashlib
from io import StringIO
import json
from pathlib import Path
from typing import Any, Callable

from tax_graph import __version__
from tax_graph.config import get_config_value, load_config, project_root
from tax_graph.engine import Engine, Graph, MISSING, load_facts, load_facts_document, render_trace
from tax_graph.io.loader import load_yaml
from tax_graph.validate import validate_graph

try:
    import typer

    _HAVE_TYPER = True
except ImportError:  # pragma: no cover - local fallback for unsynced envs.
    typer = None
    _HAVE_TYPER = False


DEFAULT_TARGET = "form_1040_2025_line_7_capital_gain_loss"
DEFAULT_CITATION_SOURCE_MAP = {
    "form_8949_2025": "instructions_form_8949_2025",
}


def validate_command(year: str = "2025", root: str | Path | None = None) -> int:
    """Validate authored graph YAML for a tax year."""
    root_path = Path(root).resolve() if root is not None else project_root()
    load_config(root=root_path)
    result = validate_graph(year, root=root_path)
    print(result.format_report())
    from tax_graph.acquire.reconcile import reconcile_document_lists

    try:
        reconcile = reconcile_document_lists(year, root=root_path)
    except (OSError, ValueError) as exc:
        print("=== document reconcile ===")
        print(f"  status: ERROR ({type(exc).__name__}: {exc})")
    else:
        print(reconcile.format_report(), end="")
    return 0 if result.ok else 1


def run_command(
    facts: str | Path,
    year: str = "2025",
    target: str = DEFAULT_TARGET,
    root: str | Path | None = None,
    source: str | None = None,
    prior_record: str | Path | None = None,
    record_dir: str | Path | None = None,
    no_record: bool = False,
    record_date: str | None = None,
    tax_graph_version: str | None = None,
    return_id: str | None = None,
    output_root: str | Path | None = None,
    export_bundle: bool = False,
) -> int:
    """Execute a graph from taxpayer facts and print values plus trace."""
    root_path = Path(root).resolve() if root is not None else project_root()
    load_config(root=root_path)
    graph = Graph(year, root=root_path, source=source)
    facts_path = Path(facts)
    facts_document = load_facts_document(facts_path)
    fact_values = load_facts(facts_path)
    prior_ingestion = None
    if prior_record is not None:
        from tax_graph.record import ingest_prior_record, load_carryforward_block

        try:
            prior_ingestion = ingest_prior_record(
                load_carryforward_block(prior_record),
                graph,
                explicit_facts=fact_values,
            )
        except ValueError as exc:
            print(f"ERROR: {exc}")
            return 1
        fact_values = prior_ingestion.facts
        facts_document = _facts_document_with_prior(facts_document, prior_ingestion)
    result = Engine(graph).execute(fact_values)
    return_root = None
    resolved_return_id = return_id or facts_document.get("return_id") or facts_document.get("scenario_id") or facts_path.stem
    if not no_record or export_bundle:
        if record_dir is not None:
            from tax_graph.output import validate_direct_return_root

            return_root = validate_direct_return_root(project_root=root_path, return_root=record_dir)
            return_root.mkdir(parents=True, exist_ok=True)
        else:
            from tax_graph.output import resolve_return_root

            resolved_return_id, return_root = resolve_return_root(
                project_root=root_path,
                facts_document=facts_document,
                return_id=str(resolved_return_id),
                output_root=output_root,
            )

    print("=== computed values ===")
    for node_id in graph.nodes:
        print(f"  {node_id} = {result.values.get(node_id)}")
    if result.missing_required_inputs:
        print("\n=== missing required inputs ===")
        for node_id in result.missing_required_inputs:
            print(f"  {node_id}")
    if prior_ingestion is not None:
        _print_prior_record_report(prior_ingestion)
    bundle = None
    if export_bundle:
        from tax_graph.output import export_filing_bundle

        bundle = export_filing_bundle(
            facts_document=facts_document,
            result=result,
            year=year,
            project_root=root_path,
            return_root=return_root,
        )
        print("\n=== filing bundle ===")
        print(f"  root: {return_root}")
    record_paths = None
    if not no_record:
        record_paths = _write_return_record(
            facts_path=facts_path,
            facts_document=facts_document,
            result=result,
            graph=graph,
            year=year,
            target=target,
            record_dir=return_root,
            generated_date=record_date or _dt.date.today().isoformat(),
            tax_graph_version=tax_graph_version or __version__,
            blank_with_note=(bundle or {}).get("blank_with_note", []),
        )
        print("\n=== return record ===")
        print(f"  memo: {record_paths['memo']}")
        print(f"  carryforward: {record_paths['carryforward']}")
    print(f"\n=== audit trace: {target} ===")
    audit_buffer = StringIO()
    with redirect_stdout(audit_buffer):
        render_trace(target, result, graph)
    audit_text = audit_buffer.getvalue()
    print(audit_text, end="")
    if return_root is not None:
        _write_text_lf(return_root / "audit.txt", audit_text)
        diagnostics = {
            "return_id": str(resolved_return_id),
            "tax_year": str(year),
            "target": target,
            "target_value": None if result.values.get(target) is MISSING else result.values.get(target),
            "missing_required_inputs": result.missing_required_inputs,
            "artifacts": {
                "audit": str(return_root / "audit.txt"),
                "record": {key: str(value) for key, value in (record_paths or {}).items()},
                "bundle": bundle or {},
            },
        }
        _write_text_lf(return_root / "run.json", json.dumps(diagnostics, indent=2, sort_keys=True) + "\n")
    return 1 if result.values.get(target) is MISSING else 0


def _facts_document_with_prior(facts_document: dict[str, Any], prior_ingestion: Any) -> dict[str, Any]:
    merged = dict(facts_document)
    merged["facts"] = prior_ingestion.fact_entries + list(facts_document.get("facts", []))
    return merged


def _write_return_record(
    *,
    facts_path: Path,
    facts_document: dict[str, Any],
    result: Any,
    graph: Graph,
    year: str,
    target: str,
    record_dir: str | Path | None,
    generated_date: str,
    tax_graph_version: str,
    blank_with_note: list[dict[str, str]] | None = None,
) -> dict[str, Path]:
    from tax_graph.record import build_return_record, render_carryforward_yaml, render_memo

    output_dir = Path(record_dir).resolve() if record_dir is not None else facts_path.resolve().parent
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"return_record_{year}"
    memo_path = output_dir / f"{stem}.md"
    carryforward_path = output_dir / f"{stem}.carryforward.yaml"
    record = build_return_record(
        facts_document=facts_document,
        result=result,
        graph=graph,
        tax_year=year,
        tax_graph_version=tax_graph_version,
        generated_date=generated_date,
        target_node=target,
        blank_with_note=blank_with_note,
    )
    _write_text_lf(memo_path, render_memo(record))
    _write_text_lf(carryforward_path, render_carryforward_yaml(record.carryforward_block))
    return {"memo": memo_path, "carryforward": carryforward_path}


def _write_text_lf(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _print_prior_record_report(prior_ingestion: Any) -> None:
    if prior_ingestion.warnings:
        print("\n=== prior record warnings ===")
        for warning in prior_ingestion.warnings:
            print(f"  {warning}")
    if prior_ingestion.not_ingested:
        print("\n=== carryforwards NOT ingested ===")
        for item in prior_ingestion.not_ingested:
            target = item.get("target_node") or "-"
            print(f"  {item['carryforward_id']}: {item['reason']} (target: {target})")


def build_command(year: str = "2025", root: str | Path | None = None) -> int:
    """Compile authored graph YAML into a SQLite runtime artifact."""
    from tax_graph.compile import build_sqlite

    root_path = Path(root).resolve() if root is not None else project_root()
    result = build_sqlite(year, root=root_path)
    print(f"built SQLite graph: {result.path}")
    for kind, count in result.counts.items():
        print(f"  {kind}: {count}")
    return 0


def promote_instruction_command(
    year: str = "2025",
    root: str | Path | None = None,
    source_document_id: str | None = None,
    html_path: str | Path | None = None,
    citation_filename: str = "instruction-form-1040-html.yaml",
) -> int:
    """Regenerate the stored 1040 HTML instruction promotion and its findings."""
    from tax_graph.ingest.instruction_promotion import promote_instruction_html

    root_path = Path(root).resolve() if root is not None else project_root()
    source_id = source_document_id or f"instructions_form_1040_{year}"
    source_path = (
        Path(html_path)
        if html_path is not None
        else root_path / ".cache" / "raw" / str(year) / f"{source_id}.html"
    )
    result = promote_instruction_html(
        root_path,
        year=year,
        source_document_id=source_id,
        html_path=source_path,
        citation_filename=citation_filename,
    )
    print(f"promoted instruction sections: {len(result.joins)}")
    print(f"  findings persisted: {len(result.findings)}")
    print(f"  coverage before: {result.coverage_before}")
    print(f"  coverage after: {result.coverage_after}")
    return 0


def harvest_worksheet_command(
    year: str = "2025",
    root: str | Path | None = None,
    source_document_id: str | None = None,
    html_path: str | Path | None = None,
    document_id: str | None = None,
    title: str | None = None,
    start_anchor: str | None = None,
    draft_dir: str | Path | None = None,
    classifier: Any | None = None,
    window_classifier: Any | None = None,
) -> int:
    """Harvest one title or every worksheet table into drafts without promotion."""
    from tax_graph.ingest.worksheet_harvest import (
        QDCGT_WORKSHEET_TARGET,
        WorksheetTarget,
        harvest_worksheets_file,
        harvest_worksheet_file,
        write_worksheet_discovery_report,
        write_worksheet_draft,
    )

    root_path = Path(root).resolve() if root is not None else project_root()
    default_target = QDCGT_WORKSHEET_TARGET
    manifest_entry = None
    if document_id is not None:
        manifest_path = root_path / "config" / "manifest.yaml"
        if manifest_path.exists():
            from tax_graph.acquire.manifest import load_manifest

            manifest_entry = load_manifest(root=root_path).by_document_id().get(document_id)
        if manifest_entry is not None and manifest_entry.is_region:
            if source_document_id and source_document_id != manifest_entry.region_of:
                print(
                    f"worksheet harvest blocked: {document_id} parent is "
                    f"{manifest_entry.region_of}, not {source_document_id}"
                )
                return 1
            source_document_id = manifest_entry.region_of
            title = manifest_entry.region_title
    source_id = source_document_id or default_target.source_document_id or f"instructions_form_1040_{year}"
    source_path = (
        Path(html_path)
        if html_path is not None
        else root_path / ".cache" / "raw" / str(year) / f"{source_id}.html"
    )
    if manifest_entry is not None and manifest_entry.is_region:
        if not source_path.exists():
            print(f"worksheet harvest blocked: missing parent HTML {source_path}")
            return 1
        actual_parent_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if actual_parent_hash != manifest_entry.region_parent_sha256:
            print(
                f"worksheet harvest blocked: parent hash changed for {document_id} "
                f"(expected {manifest_entry.region_parent_sha256}, got {actual_parent_hash})"
            )
            return 1
    if any(value is not None for value in (document_id, start_anchor)):
        if manifest_entry is not None and manifest_entry.is_region:
            target = WorksheetTarget(
                document_id=document_id or default_target.document_id,
                title=title or default_target.title,
                start_anchor=start_anchor or default_target.start_anchor,
                source_document_id=source_id,
                expected_line_count=default_target.expected_line_count
                if title == default_target.title
                else None,
                expected_constant_count=default_target.expected_constant_count
                if title == default_target.title
                else None,
                citation_groups=default_target.citation_groups if title == default_target.title else None,
            )
        else:
            target = WorksheetTarget(
                document_id=document_id or default_target.document_id,
                title=title or default_target.title,
                start_anchor=start_anchor or default_target.start_anchor,
                source_document_id=source_id,
                expected_line_count=default_target.expected_line_count
                if (title or default_target.title) == default_target.title
                else None,
                expected_constant_count=default_target.expected_constant_count
                if (title or default_target.title) == default_target.title
                else None,
                citation_groups=default_target.citation_groups
                if (title or default_target.title) == default_target.title
                else None,
            )
        result = harvest_worksheet_file(
            source_path,
            target,
            source_document_id=source_id,
            year=year,
        )
        if not result.ok:
            print(f"worksheet harvest blocked: {target.document_id}")
            for finding in result.findings:
                print(f"  {finding.kind}: {finding.message}")
            return 1
        output = (
            Path(draft_dir)
            if draft_dir is not None
            else root_path / "graph" / str(year) / "_drafts" / target.document_id
        )
        write_worksheet_draft(result, output)
        print(f"harvested worksheet draft: {target.document_id}")
        print(f"  draft_dir: {output.resolve()}")
        print(f"  lines: {len(result.line_nodes)}")
        print(f"  constants: {len(result.parameter_nodes)}")
        print(f"  citations: {len(result.citations)}")
        print("  promoted: no")
        return 0

    settings = load_config(root=root_path)
    classification_cache_path = root_path / ".cache" / "raw" / str(year) / f"{source_id}.worksheet_tables.yaml"
    window_cache_path = root_path / ".cache" / "raw" / str(year) / f"{source_id}.worksheet_windows.yaml"
    try:
        discovery = harvest_worksheets_file(
            source_path,
            source_document_id=source_id,
            year=year,
            title=title,
            classifier=classifier,
            window_classifier=window_classifier,
            config=settings,
            cache_path=classification_cache_path,
            window_cache_path=window_cache_path,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"worksheet discovery blocked: {exc}")
        return 1
    print(f"worksheet windows observed: {len(discovery.windows)}")
    print(f"worksheets discovered: {len(discovery.worksheets)}")
    if not discovery.classifications:
        print("  no HTML tables; zero worksheets is a valid result")
        print("worksheet attempts: discovered=0; written=0; refused=0; sum=0")
        return 0
    for item in discovery.classifications:
        print(
            f"  table {item.table_id}: {item.kind}; "
            f"heading={item.heading or '(none)'}; lines={','.join(item.lines) or '(none)'}"
        )
    written = 0
    from tax_graph.ingest.worksheet_harvest import ADVISORY_FINDING_KINDS

    refused = sum(item.kind not in ADVISORY_FINDING_KINDS for item in discovery.findings)
    output_root = (
        Path(draft_dir)
        if draft_dir is not None
        else root_path / "graph" / str(year) / "_drafts"
    )
    for result in discovery.worksheets:
        if not result.ok:
            refused += 1
            print(f"  refused {result.target.document_id}")
            for finding in result.findings:
                print(f"    {finding.kind}: {finding.message}")
            continue
        output = output_root / result.target.document_id
        try:
            write_worksheet_draft(result, output)
        except Exception as exc:
            refused += 1
            print(f"  refused {result.target.document_id}: draft write failed: {exc}")
            continue
        written += 1
        print(
            f"  harvested {result.target.document_id}: "
            f"tables={','.join(str(table_id) for table_id in result.source_table_ids)}; "
            f"lines={len(result.line_nodes)}; oracle={result.as_dict()['oracle']['status']}"
        )
    for item in discovery.inventory:
        if item.kind == "classified_not_emitted":
            print(f"  classified-not-emitted: {item.message}")
        elif item.kind == "table_merged":
            print(f"  merged: {item.message}")
        else:
            print(f"  inventory {item.kind}: {item.message}")
    for finding in discovery.findings:
        label = "advisory" if finding.kind in ADVISORY_FINDING_KINDS else "refused"
        print(f"  {label} {finding.kind}: {finding.message}")
    try:
        report_path = write_worksheet_discovery_report(discovery, output_root)
    except Exception as exc:
        refused += 1
        print(f"  refused discovery-report: {exc}")
        report_path = None
    if report_path is not None:
        print(f"discovery report: {report_path}")
    discovered = written + refused
    print(f"worksheet attempts: discovered={discovered}; written={written}; refused={refused}; sum={written + refused}")
    return 0 if refused == 0 else 1


def nomination_list_command(
    *,
    year: str = "2025",
    root: str | Path | None = None,
    run_dir: str | Path | None = None,
    evidence_paths: list[str | Path] | None = None,
    json_output: bool = False,
) -> int:
    """List evidence-backed source-document regions that are not yet held."""
    from tax_graph.ingest.nominations import list_nominations
    from tax_graph.ingest.worksheet_harvest import normalize_printed_title

    root_path = Path(root).resolve() if root is not None else project_root()
    nominations = list_nominations(
        year=year,
        root=root_path,
        run_dir=run_dir,
        evidence_paths=evidence_paths or (),
    )
    from tax_graph.acquire.manifest import load_manifest
    accepted_titles = {
        normalize_printed_title(entry.region_title)
        for entry in load_manifest(root=root_path).documents
        if entry.is_region and entry.region_title
    }
    nominations = tuple(
        item for item in nominations if item.normalized_title not in accepted_titles
    )
    if json_output:
        print(json.dumps([item.as_dict() for item in nominations], indent=2, sort_keys=True))
        return 0
    print("=== outstanding document nominations ===")
    if not nominations:
        print("  none")
        return 0
    for item in nominations:
        print(f"  {item.title}")
        print(f"    references: {item.count}")
        for row in item.citing_rows:
            print(f"    citing row: {row}")
        for evidence in item.evidence:
            print(f"    evidence: {evidence}")
        if item.frontier_ids:
            print(f"    frontier: {', '.join(item.frontier_ids)}")
    return 0


def nomination_accept_command(
    *,
    title: str,
    source_document_id: str,
    year: str = "2025",
    root: str | Path | None = None,
    document_id: str | None = None,
    kind: str = "worksheet",
    run_dir: str | Path | None = None,
    evidence_paths: list[str | Path] | None = None,
    html_path: str | Path | None = None,
) -> int:
    """Accept one evidence-backed region into the manifest."""
    from tax_graph.ingest.nominations import accept_nomination

    root_path = Path(root).resolve() if root is not None else project_root()
    try:
        result = accept_nomination(
            title=title,
            source_document_id=source_document_id,
            year=year,
            root=root_path,
            document_id=document_id,
            kind=kind,
            run_dir=run_dir,
            evidence_paths=evidence_paths or (),
            html_path=html_path,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print("=== document nomination accepted ===")
    print(f"  document: {result['document_id']}")
    print(f"  parent: {source_document_id}")
    print(f"  parent_sha256: {result['parent_sha256']}")
    print(f"  citing rows: {result['evidence'].count}")
    print("  region identity: normalized printed title")
    print("  status: manifest accepted; graph draft remains unpromoted")
    return 0


def nomination_drop_command(
    document_id: str,
    *,
    root: str | Path | None = None,
) -> int:
    """Drop one previously accepted region from the manifest."""
    from tax_graph.ingest.nominations import drop_nomination

    root_path = Path(root).resolve() if root is not None else project_root()
    try:
        drop_nomination(document_id, root=root_path)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"dropped region nomination: {document_id}")
    return 0


def measure_extraction_command(
    year: str = "2025",
    root: str | Path | None = None,
    input_dir: str | Path | None = None,
    corpus_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> int:
    """Measure shipped form-text retention without writing to the raw store."""
    from tax_graph.acquire.measure_form import (
        build_snapshot,
        measure_directory,
        measure_robustness_corpus,
        write_snapshot,
    )

    root_path = Path(root).resolve() if root is not None else project_root()
    source_dir = Path(input_dir) if input_dir is not None else root_path / ".cache" / "raw" / str(year)
    corpus_root = Path(corpus_dir) if corpus_dir is not None else root_path / "tests" / "fixtures" / "m20_producer_corpus"
    destination = Path(output_dir) if output_dir is not None else root_path / "plans" / "m20_s1_measurements"
    forms = measure_directory(source_dir, root=root_path)
    robustness = measure_robustness_corpus(corpus_root, root=root_path) if corpus_root.exists() else []
    snapshot = build_snapshot(
        forms,
        robustness=robustness,
        source_directory=_relative_snapshot_path(source_dir, root_path),
        corpus_directory=_relative_snapshot_path(corpus_root, root_path) if corpus_root.exists() else None,
    )
    json_path, markdown_path = write_snapshot(snapshot, destination)
    print(f"measured form PDFs: {len(forms)}")
    print(f"mean retention: {snapshot['mean_retention_percent']:.1f}%")
    print(f"headline reproduced: {str(snapshot['mean_reproduced']).lower()}")
    print(f"robustness PDFs: {len(robustness)}")
    print(f"machine snapshot: {json_path}")
    print(f"report snapshot: {markdown_path}")
    return 0


def review_table_command(
    *,
    year: str = "2025",
    document: str,
    root: str | Path | None = None,
    output: str | Path | None = None,
    all_rows: bool = False,
    hardest: int | None = None,
    candidate_root: str | Path | None = None,
) -> int:
    """Write the deterministic input-versus-graph review table."""
    from tax_graph.review_table import review_table_command as _review_table_command

    return _review_table_command(
        year=year,
        document_id=document,
        root=root,
        output=output,
        all_rows=all_rows,
        hardest=hardest,
        candidate_root=candidate_root,
    )


def summarize_runs_command(
    *,
    run_paths: list[str | Path],
    output: str | Path,
    expected_documents: list[str] | None = None,
    baseline_window: int = 3,
    root: str | Path | None = None,
) -> int:
    """Build the provider-free, band-aware diff of derivation run reports."""
    from tax_graph.extract.run_summary import summarize_runs_command as _summarize_runs_command

    root_path = Path(root).resolve() if root is not None else project_root()
    return _summarize_runs_command(
        run_paths,
        output=output,
        expected_documents=expected_documents or [],
        baseline_window=baseline_window,
        root=root_path,
    )


def regenerate_candidate_command(
    *,
    run_dir: str | Path,
    output_dir: str | Path,
    year: str = "2025",
    root: str | Path | None = None,
    expected_documents: list[str] | None = None,
) -> int:
    """Materialize a review-only candidate from completed derive reports."""
    from tax_graph.extract.candidate import write_candidate_from_run

    root_path = Path(root).resolve() if root is not None else project_root()
    destination = write_candidate_from_run(
        run_dir,
        output_dir,
        root=root_path,
        year=year,
        expected_documents=expected_documents,
    )
    print(f"candidate: {destination}")
    return 0


def doctor_command(
    *,
    year: str = "2025",
    root: str | Path | None = None,
    max_open_item_commits: int = 20,
) -> int:
    """Check pipeline claims, declared artifacts, vocabulary, and handoff age.

    This command never constructs an LLM client and never repairs the artifact
    it reports.  Exit 0 means all checks are accounted for; exit 1 means a
    check is unknown, layers disagree, or an open item is stale.
    """
    from tax_graph.doctor import render_doctor_report, run_doctor

    report = run_doctor(
        year=year,
        root=root,
        max_open_item_commits=max_open_item_commits,
    )
    print(render_doctor_report(report), end="")
    return 0 if report.ok else 1


def _relative_snapshot_path(path: str | Path, root: Path) -> str:
    """Keep committed measurement snapshots portable across developer machines."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return str(resolved)


def apply_verdicts_command(
    year: str = "2025",
    root: str | Path | None = None,
    verdict_dir: str | Path | None = None,
) -> int:
    """Apply schema'd human verdict files to the review queue and graph."""
    from tax_graph.review import apply_verdicts

    root_path = Path(root).resolve() if root is not None else project_root()
    result = apply_verdicts(year, root=root_path, verdict_dir=verdict_dir)
    print(f"applied review verdicts: {len(result.applied)}")
    print(f"  confirmed: {len(result.confirmed)}")
    print(f"  questioned: {len(result.questioned)}")
    print(f"  rejected: {len(result.rejected)}")
    print(f"  pipeline defects: {len(result.pipeline_defects)}")
    print(f"  source pathologies: {len(result.source_pathologies)}")
    return 0


def apply_address_verdicts_command(
    year: str = "2025",
    root: str | Path | None = None,
    ledger_path: str | Path | None = None,
    apply: bool = False,
) -> int:
    """Project address-keyed verdicts onto graph nodes, dry-run unless requested."""
    from tax_graph.review import apply_address_verdicts

    root_path = Path(root).resolve() if root is not None else project_root()
    result = apply_address_verdicts(
        year,
        root=root_path,
        ledger_path=ledger_path,
        dry_run=not apply,
    )
    print(f"address verdicts: {len(result.reports)}")
    action = "would apply" if result.dry_run else "applied"
    action_count = len(result.would_apply if result.dry_run else result.applied)
    print(f"  {action}: {action_count}")
    print(f"  stale: {len(result.stale)}")
    print(f"  unresolved: {len(result.unresolved)}")
    print(f"  ambiguous: {len(result.ambiguous)}")
    print(f"  unsupported judgements: {len(result.unsupported_judgements)}")
    for report in result.reports:
        print(f"  {report['address']}: {report['status']}")
        if report["status"] == "stale":
            print(f"    reviewed fingerprint: {report['reviewed_fingerprint']}")
            print(f"    current fingerprint:  {report['current_fingerprint']}")
        if report["status"] in {"would_apply", "applied"}:
            for change in report["field_changes"]:
                print(
                    f"    {change['field']}: {change['before']!r} -> {change['after']!r} "
                    f"(changed={str(change['changed']).lower()})"
                )
        if report["status"] in {"node_binding_ambiguous", "address_ambiguous"}:
            print(f"    candidates: {report.get('node_ids') or report.get('address_matches')}")
    return 0


def migrate_review_scope_command(
    year: str = "2025",
    root: str | Path | None = None,
    refresh: bool = False,
) -> int:
    """Backfill deterministic object scopes in the deferred-review queue."""
    from tax_graph.review_scope import migrate_review_scope

    root_path = Path(root).resolve() if root is not None else project_root()
    result = migrate_review_scope(root=root_path, year=year, refresh=refresh)
    print(f"migrated review scopes: {len(result.changed_entries)}")
    print(f"  unchanged or skipped: {len(result.skipped_entries)}")
    print(f"  queue: {result.queue_path}")
    return 0


def migrate_field_dispositions_command(
    year: str = "2025",
    root: str | Path | None = None,
    output: str | Path | None = None,
) -> int:
    """Write a deterministic field-disposition authored-work list."""
    from tax_graph.output.field_maps import migrate_field_dispositions

    root_path = Path(root).resolve() if root is not None else project_root()
    result = migrate_field_dispositions(year, root_path, output_path=output)
    proposed = sum(len(item.proposed_dispositions) for item in result.documents)
    authored = sum(len(item.authored_work) for item in result.documents)
    print(f"field disposition migration: {len(result.documents)} documents")
    print(f"  provable proposals: {proposed}")
    print(f"  authored work: {authored}")
    print(f"  worklist: {result.output_path}")
    return 0


def frontier_build_command(year: str = "2025", root: str | Path | None = None) -> int:
    """Build the derived frontier registry."""
    from tax_graph.frontier import build_frontier_registry

    root_path = Path(root).resolve() if root is not None else project_root()
    result = build_frontier_registry(year, root=root_path)
    counts: dict[str, int] = {}
    for entry in result.registry.get("frontiers", []):
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    print(f"built frontier registry: {result.path}")
    for status in sorted(counts):
        print(f"  {status}: {counts[status]}")
    return 0


def frontier_query_command(
    year: str = "2025",
    root: str | Path | None = None,
    json_output: bool = False,
) -> int:
    """Print the frontier worklist and SOI-weighted coverage."""
    from tax_graph.frontier.build import render_frontier_summary, summarize_frontier

    root_path = Path(root).resolve() if root is not None else project_root()
    summary = summarize_frontier(year, root=root_path)
    print(render_frontier_summary(summary, json_output=json_output), end="")
    return 0


def link_command(year: str = "2025", root: str | Path | None = None) -> int:
    """Resolve reviewed outbound-flow declarations into live FEEDS edges."""
    from tax_graph.link import link_outbound_flows

    root_path = Path(root).resolve() if root is not None else project_root()
    result = link_outbound_flows(year, root=root_path)
    print(f"wrote linked outbound edges: {result.path}")
    print(f"  realized: {len(result.realized)}")
    print(f"  unresolved: {len(result.unresolved)}")
    print(f"  rejected: {len(result.rejected)}")
    for item in result.unresolved:
        print(
            "  - "
            f"{item.get('flow_id')}: {item.get('source_node_id')} -> "
            f"{item.get('target_document_id')} line {item.get('target_line')}"
        )
    for item in result.rejected:
        print(
            "  - "
            f"{item.get('flow_id')}: rejected ({item.get('resolution')}: {item.get('reason')})"
        )
    return 0


def serve_command(
    year: str = "2025",
    root: str | Path | None = None,
    source: str | None = None,
    sweep_orphans: bool = False,
) -> int:
    """Start the Tax Graph MCP stdio server."""
    if sweep_orphans:
        from tax_graph.mcp.lifecycle import sweep_orphaned_servers

        stopped = sweep_orphaned_servers()
        print(f"stopped {len(stopped)} orphaned Tax Graph serve process(es): {stopped}")
        return 0
    from tax_graph.mcp import run_mcp_server

    root_path = Path(root).resolve() if root is not None else project_root()
    run_mcp_server(year=year, root=root_path, source=source)
    return 0


def drill_run_command(
    year: str = "2025",
    root: str | Path | None = None,
    catalog: str | Path | None = None,
) -> int:
    """Run seeded-defect drills against the verification ladder."""
    from tax_graph.drills import run_drills

    root_path = Path(root).resolve() if root is not None else project_root()
    report = run_drills(year=year, root=root_path, catalog=catalog)
    print(report.format_report())
    return 0 if report.ok else 1


def verify_mine_examples_command(
    *,
    doc: str,
    year: str = "2025",
    root: str | Path | None = None,
    output_dir: str | Path | None = None,
    confirm: bool = False,
    freeze_agreed: bool = False,
    limit: int | None = None,
    source: str | None = None,
    client: object | None = None,
) -> int:
    """Mine IRS worked examples from rendered source text."""
    from tax_graph.extract.llm_client import build_llm_client
    from tax_graph.verify.examples import mine_examples

    root_path = Path(root).resolve() if root is not None else project_root()
    config = load_config(root=root_path)
    llm_client = client or build_llm_client(config)
    try:
        report = mine_examples(
            document_id=doc,
            year=year,
            root=root_path,
            client=llm_client,
            config=config,
            output_dir=output_dir,
            confirm=confirm,
            freeze_agreed=freeze_agreed,
            limit=limit,
            source=source,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("=== IRS example mining ===")
    print(f"  document: {doc}")
    print(f"  examples: {len(report.examples)}")
    print(f"  agreed: {report.agreed}")
    print(f"  disagreed: {report.disagreed}")
    print(f"  unmappable: {report.unmappable}")
    for example in report.examples:
        if example.output_dir:
            print(f"  frozen: {example.output_dir}")
            if example.review_queue_path:
                print(f"  review queue: {example.review_queue_path}")
        elif example.mismatches:
            print(f"  - {example.block.example_id}: {example.status} ({'; '.join(example.mismatches)})")
    return 0 if report.disagreed == 0 else 1


def verify_replay_examples_command(
    *,
    year: str = "2025",
    root: str | Path | None = None,
    examples_dir: str | Path | None = None,
    source: str | None = None,
) -> int:
    """Replay frozen IRS worked-example fixtures."""
    from tax_graph.verify.examples import replay_irs_examples

    root_path = Path(root).resolve() if root is not None else project_root()
    try:
        report = replay_irs_examples(year=year, root=root_path, examples_dir=examples_dir, source=source)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("=== IRS example replay ===")
    print(f"  examples: {report.example_count}")
    if report.ok:
        print("  result: OK")
        return 0
    print("  result: FAILED")
    for issue in report.issues:
        print(f"  - {issue.example_id} {issue.node_id}: got {issue.actual}, want {issue.expected}")
    return 1


def verify_nversion_command(
    *,
    doc: str,
    year: str = "2025",
    root: str | Path | None = None,
    primary_client: object | None = None,
    secondary_client: object | None = None,
) -> int:
    """Run N-version extraction corroboration for one document."""
    from tax_graph.extract.inputs import load_document_input
    from tax_graph.extract.llm_client import build_llm_client
    from tax_graph.verify.nversion import run_nversion_extraction

    root_path = Path(root).resolve() if root is not None else project_root()
    config = load_config(root=root_path)
    try:
        client_a = primary_client or build_llm_client(config)
        client_b = secondary_client or build_llm_client(config)
        document = load_document_input(doc, year=year, root=root_path, config=config)
        report = run_nversion_extraction(
            document,
            primary_client=client_a,
            secondary_client=client_b,
            config=config,
            root=root_path,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("=== N-version extraction ===")
    print(f"  document: {doc}")
    print(f"  primary: {report.primary_family} {report.primary_model}")
    print(f"  secondary: {report.secondary_family} {report.secondary_model}")
    print(f"  status: {report.status}")
    print(f"  diffs: {len(report.diffs)}")
    for diff in report.diffs:
        print(f"  - {diff.kind}/{diff.object_id}: {diff.reason}")
    return 0 if report.ok else 1


def verify_report_command(
    year: str = "2025",
    root: str | Path | None = None,
) -> int:
    """Print the cross-form verification metrics roll-up."""
    from tax_graph.verify.metrics import collect_metrics, render_report

    root_path = Path(root).resolve() if root is not None else project_root()
    config = load_config(root=root_path)
    graph_dir = str(get_config_value(config, "project.paths.graph_dir", "graph"))
    reports = collect_metrics(root_path, year=year, graph_dir=graph_dir)
    print(render_report(reports, year=year), end="")
    return 0


def verify_expression_agreement_command(
    year: str = "2025",
    root: str | Path | None = None,
) -> int:
    """Compare generated draft expressions with the protected live graph."""
    from tax_graph.verify.expressions import build_expression_agreement_report, write_expression_agreement_report

    root_path = Path(root).resolve() if root is not None else project_root()
    report = build_expression_agreement_report(year=year, root=root_path)
    path = write_expression_agreement_report(report, root=root_path)
    print(f"expression agreement report: {path}")
    coverage = report["coverage"]
    accuracy = report["accuracy"]
    print(
        "  coverage: {paired_expressions}/{live_expressions} "
        "({rate:.1%})".format(**coverage)
    )
    print(
        "  accuracy: operation {operation_agreement}/{paired_expressions}; "
        "expression {expression_agreement}/{paired_expressions}".format(**accuracy)
    )
    for category, count in report["totals"].items():
        print(f"  {category}: {count}")
    return 0


def verify_form_completeness_command(
    year: str = "2025",
    root: str | Path | None = None,
    *,
    documents: tuple[str, ...] = ("form_1040_2025", "schedule_1_2025", "schedule_a_2025"),
) -> int:
    """Write the form-completeness report and retain handcrafted diffs as flags."""
    from tax_graph.verify.form_completeness import build_form_completeness_report, write_form_completeness_report

    root_path = Path(root).resolve() if root is not None else project_root()
    report = build_form_completeness_report(year=year, root=root_path, documents=documents)
    path = write_form_completeness_report(report, root=root_path)
    totals = report["totals"]
    print(f"form completeness report: {path}")
    print(
        "  completeness: {expression_and_form_face_citation}/{formula_cells} "
        "({completeness_rate:.1%})".format(**totals)
    )
    print(
        "  instruction coverage: {instruction_page_citation}/{instruction_review_cells} "
        "({instruction_page_citation_rate:.1%})".format(
            **{
                "instruction_page_citation": sum(
                    item["instruction_page_citation"] for item in report["by_document"].values()
                ),
                "instruction_review_cells": sum(
                    item["instruction_review_cells"] for item in report["by_document"].values()
                ),
                "instruction_page_citation_rate": (
                    sum(item["instruction_page_citation"] for item in report["by_document"].values())
                    / sum(item["instruction_review_cells"] for item in report["by_document"].values())
                    if sum(item["instruction_review_cells"] for item in report["by_document"].values())
                    else 0.0
                ),
            }
        )
    )
    print(
        "  non-computed policy coverage: {policy_controls_with_policy}/{policy_controls} "
        "({policy_coverage_rate:.1%}); policy + form-face citation: "
        "{policy_and_form_face_citation}/{policy_controls} "
        "({policy_and_form_face_citation_rate:.1%})".format(**totals)
    )
    print(
        "  policy origin: derived={policy_derived}, defaulted={policy_defaulted}, "
        "authored={policy_authored}".format(**totals)
    )
    print(
        "  policy mix after: {policy_mix_after}; failover classes: {failover_class_counts}".format(
            **totals
        )
    )
    print("  handcrafted expression set: review flag only")
    return 0


def verify_record_command(
    year: str = "2025",
    root: str | Path | None = None,
    *,
    rollup_path: str | Path | None = None,
    pages_dir: str | Path | None = None,
) -> int:
    """Generate VERIFICATION.md plus per-form verification pages."""
    from tax_graph.verify.record import write_verification_record

    root_path = Path(root).resolve() if root is not None else project_root()
    load_config(root=root_path)
    result = write_verification_record(year=year, root=root_path, rollup_path=rollup_path, pages_dir=pages_dir)
    print("=== verification record ===")
    print(f"  rollup: {result.rollup_path}")
    print(f"  pages: {len(result.page_paths)}")
    for document_id, path in sorted(result.page_paths.items()):
        print(f"  - {document_id}: {path}")
    return 0


def verify_diff_drafts_command(
    *,
    doc: str,
    year: str = "2025",
    root: str | Path | None = None,
) -> int:
    """Structurally diff a draft re-extraction against the promoted live graph."""
    from tax_graph.verify.delta import diff_drafts_against_live, render_delta

    root_path = Path(root).resolve() if root is not None else project_root()
    load_config(root=root_path)
    try:
        delta = diff_drafts_against_live(doc, year=year, root=root_path)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(render_delta(delta), end="")
    return 0 if delta.ok else 1


def verify_parameter_diff_command(
    year: str = "2025",
    root: str | Path | None = None,
    offline_fixture: str | Path | None = None,
) -> int:
    """Diff parameter nodes against PolicyEngine US."""
    from tax_graph.verify.parameter_diff import compare_parameter_diff

    root_path = Path(root).resolve() if root is not None else project_root()
    load_config(root=root_path)
    try:
        offline_path = Path(offline_fixture).resolve() if offline_fixture else None
        report = compare_parameter_diff(year=year, root=root_path, offline_fixture=offline_path)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print(report.format_report(), end="")
    return 0 if report.disagree == 0 else 1


def oracle_install_command(
    year: str = "2025",
    root: str | Path | None = None,
    archive: str | Path | None = None,
) -> int:
    """Install a pinned OpenTaxSolver release for live oracle jobs."""
    from tax_graph.oracles import find_ots_executable, install_ots_release, release_from_config

    root_path = Path(root).resolve() if root is not None else project_root()
    config = load_config(root=root_path)
    try:
        release = release_from_config(config, root=root_path, year=year)
        install_dir = install_ots_release(release, archive_path=archive)
        executable = find_ots_executable(
            install_dir,
            year=year,
            executable=release.executable,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("=== oracle install ===")
    print(f"  oracle: OpenTaxSolver")
    print(f"  version: {release.version}")
    print(f"  install_dir: {install_dir}")
    print(f"  executable: {executable}")
    return 0


def oracle_fuzz_command(
    year: str = "2025",
    n: int = 100,
    seed: int = 0,
    root: str | Path | None = None,
    output_dir: str | Path | None = None,
    source: str | None = None,
) -> int:
    """Run seeded scenarios through Tax Graph and a live OTS binary."""
    from tax_graph.oracles.fuzz import resolve_ots_executable, run_fuzz

    root_path = Path(root).resolve() if root is not None else project_root()
    config = load_config(root=root_path)
    executable = resolve_ots_executable(config, root=root_path, year=year)
    if executable is None:
        print(f"ERROR: no OTS 1040 {year} executable configured; run oracle install or set OTS_1040_{year}_BIN")
        return 1
    out_dir = (
        Path(output_dir).resolve()
        if output_dir is not None
        else root_path / "output" / "oracle_fuzz" / f"{year}_seed{seed}"
    )
    try:
        summary = run_fuzz(
            year=year,
            n=n,
            seed=seed,
            root=root_path,
            output_dir=out_dir,
            executable=executable,
            source=source,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("=== oracle fuzz ===")
    print(f"  generated: {summary.generated}")
    print(f"  agreed: {summary.agreed}")
    print(f"  disagreed: {summary.disagreed}")
    print(f"  rejected: {summary.rejected}")
    print(f"  triage: {summary.triage_path}")
    return 0 if summary.disagreed == 0 and summary.rejected == 0 else 1


def oracle_freeze_command(
    year: str = "2025",
    n: int = 20,
    seed: int = 0,
    root: str | Path | None = None,
    corpus_dir: str | Path | None = None,
    generated_date: str | None = None,
    oracle_version: str = "ots_2025_23.06",
    source: str | None = None,
    adjudicate_known_ots_sdtw_defects: bool = False,
) -> int:
    """Freeze generated scenarios into offline examples with explicit triage."""
    from tax_graph.oracles import freeze_generated_corpus
    from tax_graph.oracles.fuzz import resolve_ots_executable

    root_path = Path(root).resolve() if root is not None else project_root()
    config = load_config(root=root_path)
    executable = resolve_ots_executable(config, root=root_path, year=year)
    if executable is None:
        print(f"ERROR: no OTS 1040 {year} executable configured; run oracle install or set OTS_1040_{year}_BIN")
        return 1
    output_dir = (
        Path(corpus_dir).resolve()
        if corpus_dir is not None
        else root_path / "examples" / "oracle_corpus"
    )
    try:
        summary = freeze_generated_corpus(
            year=year,
            root=root_path,
            corpus_dir=output_dir,
            scenario_count=n,
            seed=seed,
            generated_date=generated_date or _dt.date.today().isoformat(),
            oracle_version=oracle_version,
            source=source,
            executable=executable,
            adjudicate_known_ots_sdtw_defects=adjudicate_known_ots_sdtw_defects,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("=== oracle corpus freeze ===")
    print(f"  scenarios: {summary.scenario_count}")
    print(f"  corpus: {summary.corpus_dir}")
    print(f"  manifest: {summary.manifest_path}")
    return 0


def oracle_pe_liability_command(
    year: str = "2025",
    root: str | Path | None = None,
    corpus_dir: str | Path | None = None,
    offline_fixture: str | None = None,
) -> int:
    """Diff PolicyEngine liability against the frozen OTS-agreed corpus."""
    from tax_graph.oracles.pe_liability import run_pe_liability

    root_path = Path(root).resolve() if root is not None else project_root()
    input_dir = (
        Path(corpus_dir).resolve()
        if corpus_dir is not None
        else root_path / "examples" / "oracle_corpus"
    )
    try:
        report = run_pe_liability(
            year=year,
            corpus_dir=input_dir,
            offline_fixture=offline_fixture,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(report.format_report(), end="")
    return 0 if report.ok else 1


def oracle_replay_corpus_command(
    year: str = "2025",
    root: str | Path | None = None,
    corpus_dir: str | Path | None = None,
    source: str | None = None,
) -> int:
    """Replay frozen oracle corpus examples through the engine."""
    from tax_graph.oracles import replay_corpus

    root_path = Path(root).resolve() if root is not None else project_root()
    input_dir = (
        Path(corpus_dir).resolve()
        if corpus_dir is not None
        else root_path / "examples" / "oracle_corpus"
    )
    try:
        report = replay_corpus(year=year, root=root_path, corpus_dir=input_dir, source=source)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("=== oracle corpus replay ===")
    print(f"  scenarios: {report.scenario_count}")
    if report.ok:
        print("  result: OK")
        return 0
    print("  result: FAILED")
    for issue in report.issues:
        print(f"  - {issue.scenario_id} {issue.node_id}: got {issue.actual}, want {issue.expected}")
    return 1


def acquire_command(
    year: str = "2025",
    *,
    check: bool = False,
    root: str | Path | None = None,
    fetch_bytes: Callable[..., bytes] | None = None,
    renderer: Callable[..., object] | None = None,
    citation_checker: Callable[..., Any] | None = None,
) -> int:
    """Acquire source docs, render them, detect changes, and check citations."""
    from tax_graph.acquire.changes import detect_changes
    from tax_graph.acquire.citation_check import check_graph_citations
    from tax_graph.acquire.fetch import fetch_instruction_html_documents, fetch_manifest_documents
    from tax_graph.acquire.manifest import load_manifest

    root_path = Path(root).resolve() if root is not None else project_root()
    config = load_config(root=root_path)
    raw_store = root_path / get_config_value(config, "project.paths.raw_store", ".cache/raw")
    manifest = load_manifest(root=root_path)
    if str(manifest.tax_year) != str(year):
        raise ValueError(f"manifest tax_year {manifest.tax_year} does not match requested {year}")

    fetched = fetch_manifest_documents(
        manifest.documents,
        year=year,
        raw_store=raw_store,
        config=config,
        fetch_bytes=fetch_bytes,
    )
    fetched_instruction_html = fetch_instruction_html_documents(
        manifest.documents,
        year=year,
        raw_store=raw_store,
        config=config,
        fetch_bytes=fetch_bytes,
    )
    report = detect_changes(fetched, raw_store=raw_store, year=year, check=check)
    _render_fetched_documents(
        manifest.by_document_id(),
        fetched,
        raw_store=raw_store,
        year=year,
        config=config,
        renderer=renderer,
    )
    citation_report = (
        citation_checker(year=year, raw_store=raw_store, root=root_path)
        if citation_checker
        else check_graph_citations(
            year=year,
            raw_store=raw_store,
            root=root_path,
            source_map=DEFAULT_CITATION_SOURCE_MAP,
        )
    )
    _print_acquire_summary(report, citation_report, instruction_html_count=len(fetched_instruction_html))
    return 0 if citation_report.ok else 1


def extract_command(
    *,
    doc: str | None = None,
    year: str = "2025",
    root: str | Path | None = None,
    client: object | None = None,
) -> int:
    """Extract draft graph objects for one document or manifest year."""
    from tax_graph.extract import extract_document, extract_year

    root_path = Path(root).resolve() if root is not None else project_root()
    config = load_config(root=root_path)
    if doc:
        routed = extract_document(doc, year=year, root=root_path, client=client, config=config)
        _print_extract_summary(doc, routed)
        return 0

    routed_year = extract_year(year=year, root=root_path, client=client, config=config)
    print("=== extraction review ===")
    print(f"  year: {year}")
    print(f"  documents: {len(routed_year)}")
    print(f"  auto_accepted: {sum(len(item.accepted) for item in routed_year)}")
    print(f"  human_review: {sum(len(item.review) for item in routed_year)}")
    print(f"  deterministic_issues: {sum(len(item.issues) for item in routed_year)}")
    return 0


def prompt_bench_command(
    *,
    doc: str,
    target_ids: list[str],
    year: str = "2025",
    root: str | Path | None = None,
    client: object | None = None,
) -> int:
    """Print exact micro prompts, responses, and validation decisions."""
    from tax_graph.extract.inputs import load_document_input
    from tax_graph.extract.llm_client import build_llm_client
    from tax_graph.extract.prompt_bench import run_prompt_bench

    root_path = Path(root).resolve() if root is not None else project_root()
    config = load_config(root=root_path)
    document = load_document_input(doc, year=year, root=root_path, config=config)
    llm_client = client or build_llm_client(config)
    results = run_prompt_bench(
        document,
        target_ids,
        client=llm_client,
        config=config,
        root=root_path,
    )
    for result in results:
        print(f"=== prompt bench: {result['target_id']} ===")
        print(f"target_type: {result['target_type']}")
        print("prompt:")
        print(result["prompt"])
        print("response:")
        print(json.dumps(result["response"], indent=2, sort_keys=True, ensure_ascii=True))
        print(f"decision: {'accepted' if result['accepted'] else 'rejected'}")
        print(f"why: {result['validation_error'] or 'all deterministic validations passed'}")
        print("matched_spans:")
        print(json.dumps(result["matched_spans"], indent=2, sort_keys=True, ensure_ascii=True))
    return 0 if all(result["accepted"] for result in results) else 1


def extend_doctor_command(
    *,
    root: str | Path | None = None,
    network: bool = False,
    network_url: str | None = None,
) -> int:
    """Check local prerequisites for user-gated form extensions."""
    from tax_graph.extension import doctor_extension

    root_path = Path(root).resolve() if root is not None else project_root()
    report = doctor_extension(root=root_path, check_network=network, network_url=network_url)
    print(report.format_report(), end="")
    return 0 if report.ok else 1


def extend_document_command(
    document_id: str,
    *,
    year: str = "2025",
    root: str | Path | None = None,
    url: str | None = None,
    kind: str | None = None,
    title: str | None = None,
    instructions_url: str | None = None,
    instructions_document_id: str | None = None,
) -> int:
    """Run the acquire -> extract -> verify pipeline into the local queue."""
    from tax_graph.extension import run_extension

    root_path = Path(root).resolve() if root is not None else project_root()
    try:
        result = run_extension(
            document_id,
            year=year,
            root=root_path,
            url=url,
            kind=kind,
            title=title,
            instructions_url=instructions_url,
            instructions_document_id=instructions_document_id,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print("=== extension draft ===")
    print(f"  document: {result.document_id}")
    print(f"  draft_dir: {result.draft_dir}")
    print(f"  source_hash: {result.source_hash}")
    print(f"  verification_tier: {result.verification_tier}")
    print(f"  review_queue: {result.review_queue_path}")
    print("  status: pending explicit local accept")
    return 0


def extend_accept_command(
    document_id: str,
    *,
    year: str = "2025",
    root: str | Path | None = None,
) -> int:
    """Explicitly accept one user-gated extension into the YAML overlay."""
    from tax_graph.extension import accept_extension

    root_path = Path(root).resolve() if root is not None else project_root()
    try:
        result = accept_extension(document_id, year=year, root=root_path)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print("=== extension accepted locally ===")
    print(f"  document: {result.document_id}")
    print(f"  overlay: {result.extension_dir}")
    print(f"  content_hash: {result.content_hash}")
    print("  gate: user")
    print("  human_review: pending")
    return 0


def extend_package_command(
    document_id: str,
    *,
    year: str = "2025",
    root: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> int:
    """Package one accepted extension with its verification artifacts."""
    from tax_graph.extension import package_extension

    root_path = Path(root).resolve() if root is not None else project_root()
    try:
        result = package_extension(document_id, year=year, root=root_path, output_dir=output_dir)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print("=== extension package ===")
    print(f"  document: {result.document_id}")
    print(f"  package: {result.path}")
    print(f"  content_hash: {result.content_hash}")
    print("  gate: user")
    return 0


def intake_command(
    drop_dir: str | Path,
    *,
    year: str = "2025",
    root: str | Path | None = None,
    claims_path: str | Path | None = None,
    resolutions_path: str | Path | None = None,
    output: str | Path | None = None,
    provider: str | None = None,
    consent: bool = False,
) -> int:
    """Crawl a local document drop and run the cited intake completeness gate."""
    from tax_graph.intake import run_intake

    root_path = Path(root).resolve() if root is not None else project_root()
    claims = load_yaml(claims_path) if claims_path else {}
    resolutions = load_yaml(resolutions_path) if resolutions_path else {}
    try:
        result = run_intake(
            drop_dir,
            year=year,
            root=root_path,
            claims=claims or {},
            resolutions=resolutions or {},
            provider=provider,
            consent=True if consent else None,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    payload = result.to_dict()
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print(f"intake result: {output_path}")
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    print(f"completeness gate: {'PASS' if result.complete else 'BLOCKED'}")
    return 0 if result.complete else 1


def _print_extract_summary(doc: str, routed) -> None:
    print("=== extraction review ===")
    print(f"  document: {doc}")
    print(f"  draft_dir: {routed.output_dir}")
    print(f"  auto_accepted: {len(routed.accepted)}")
    print(f"  human_review: {len(routed.review)}")
    print(f"  deterministic_issues: {len(routed.issues)}")


def _render_fetched_documents(
    entries_by_id,
    fetched: list[Any],
    *,
    raw_store: Path,
    year: str,
    config: dict,
    renderer: Callable[..., object] | None = None,
) -> None:
    from tax_graph.acquire.render import render_source

    output_dir = raw_store / str(year)
    render = renderer or render_source
    for document in fetched:
        entry = entries_by_id[document.document_id]
        render(
            entry,
            pdf_path=document.raw_path,
            output_dir=output_dir,
            content_hash=document.content_hash,
            config=config,
        )


def _print_acquire_summary(report: Any, citation_report: Any, *, instruction_html_count: int = 0) -> None:
    print("=== acquisition change report ===")
    print(f"  instruction_html: {instruction_html_count}")
    print("  new:", ", ".join(report.new) if report.new else "-")
    print("  changed:", ", ".join(report.changed) if report.changed else "-")
    print("  unchanged:", ", ".join(report.unchanged) if report.unchanged else "-")
    print("\n=== citation integrity ===")
    print(f"  checked: {citation_report.checked}")
    if citation_report.ok:
        print("  result: OK")
    else:
        print("  result: FAILED")
        for mismatch in citation_report.mismatches:
            print(
                f"  - {mismatch.citation_id}: {mismatch.reason} "
                f"(doc={mismatch.document_id}, source={mismatch.source_document_id})"
            )


def _build_typer_app():
    cli = typer.Typer(help="Tax Graph command-line interface.")

    @cli.command("validate")
    def validate_cli(
        year: str = typer.Argument("2025"),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Validate authored graph YAML for a tax year."""
        raise_code = validate_command(year=year, root=root)
        if raise_code:
            raise typer.Exit(raise_code)

    @cli.command("run")
    def run_cli(
        facts: Path = typer.Option(..., "--facts", "-f", help="Path to taxpayer facts YAML."),
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to execute."),
        target: str = typer.Option(DEFAULT_TARGET, "--target", "-t", help="Target node for the audit trace."),
        source: str | None = typer.Option(None, "--source", help="Graph source: sqlite or yaml. Defaults to sqlite when built, else yaml."),
        prior_record: Path | None = typer.Option(None, "--prior-record", help="Prior Return Record carryforward YAML."),
        record_dir: Path | None = typer.Option(None, "--record-dir", help="Directory for Return Record outputs."),
        no_record: bool = typer.Option(False, "--no-record", help="Do not write Return Record outputs."),
        return_id: str | None = typer.Option(None, "--return-id", help="Stable id for the return output directory."),
        output_root: Path | None = typer.Option(None, "--output-root", help="Base directory for return-scoped outputs."),
        export_bundle: bool = typer.Option(False, "--export-bundle", help="Fill official PDFs and emit the OTS sidecar."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Execute a return graph from taxpayer facts."""
        raise_code = run_command(
            facts=facts,
            year=year,
            target=target,
            root=root,
            source=source,
            prior_record=prior_record,
            record_dir=record_dir,
            no_record=no_record,
            return_id=return_id,
            output_root=output_root,
            export_bundle=export_bundle,
        )
        if raise_code:
            raise typer.Exit(raise_code)

    @cli.command("build")
    def build_cli(
        year: str = typer.Argument("2025"),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Compile authored graph YAML into SQLite."""
        raise_code = build_command(year=year, root=root)
        if raise_code:
            raise typer.Exit(raise_code)

    @cli.command("promote-instructions")
    def promote_instruction_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to promote."),
        source_document_id: str | None = typer.Option(None, "--source-document-id", help="Acquired instruction source id."),
        html_path: Path | None = typer.Option(None, "--html-path", help="Stored acquired HTML path."),
        citation_filename: str = typer.Option(
            "instruction-form-1040-html.yaml",
            "--citation-filename",
            help="Citation artifact filename to update.",
        ),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Regenerate stored HTML instruction citations and review findings."""
        raise_code = promote_instruction_command(
            year=year,
            root=root,
            source_document_id=source_document_id,
            html_path=html_path,
            citation_filename=citation_filename,
        )
        if raise_code:
            raise typer.Exit(raise_code)

    @cli.command("harvest-worksheet")
    def harvest_worksheet_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to harvest."),
        source_document_id: str | None = typer.Option(None, "--source-document-id", help="Acquired instruction source id."),
        html_path: Path | None = typer.Option(None, "--html-path", help="Stored acquired HTML path."),
        document_id: str | None = typer.Option(None, "--document-id", help="Worksheet draft document id."),
        title: str | None = typer.Option(None, "--title", help="Worksheet title."),
        start_anchor: str | None = typer.Option(
            None,
            "--start-anchor",
            help="Observed source anchor retained for diagnostics; title selects the worksheet.",
        ),
        draft_dir: Path | None = typer.Option(None, "--draft-dir", help="Explicit _drafts output directory."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Discover HTML worksheet tables into _drafts without promotion."""
        raise_code = harvest_worksheet_command(
            year=year,
            root=root,
            source_document_id=source_document_id,
            html_path=html_path,
            document_id=document_id,
            title=title,
            start_anchor=start_anchor,
            draft_dir=draft_dir,
        )
        if raise_code:
            raise typer.Exit(raise_code)

    nomination_cli = typer.Typer(help="Evidence-backed source-document nominations.")

    @nomination_cli.command("list")
    def nomination_list_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to inspect."),
        run_dir: Path | None = typer.Option(None, "--run-dir", help="Corpus run directory containing derive reports."),
        evidence: list[Path] = typer.Option([], "--evidence", help="Additional derive or incomplete-cell report."),
        json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """List outstanding nominations with citing-row evidence."""
        raise_code = nomination_list_command(
            year=year,
            root=root,
            run_dir=run_dir,
            evidence_paths=evidence,
            json_output=json_output,
        )
        if raise_code:
            raise typer.Exit(raise_code)

    @nomination_cli.command("accept")
    def nomination_accept_cli(
        title: str = typer.Option(..., "--title", help="Printed title to accept."),
        source_document_id: str = typer.Option(..., "--source-document-id", help="Manifest parent document id."),
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to accept."),
        document_id: str | None = typer.Option(None, "--document-id", help="Stable region document id."),
        kind: str = typer.Option("worksheet", "--kind", help="Manifest document kind."),
        run_dir: Path | None = typer.Option(None, "--run-dir", help="Corpus run directory containing evidence."),
        evidence: list[Path] = typer.Option([], "--evidence", help="Additional evidence report."),
        html_path: Path | None = typer.Option(None, "--html-path", help="Acquired parent HTML override."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Accept a title-identified region into the acquisition manifest."""
        raise_code = nomination_accept_command(
            title=title,
            source_document_id=source_document_id,
            year=year,
            root=root,
            document_id=document_id,
            kind=kind,
            run_dir=run_dir,
            evidence_paths=evidence,
            html_path=html_path,
        )
        if raise_code:
            raise typer.Exit(raise_code)

    @nomination_cli.command("drop")
    def nomination_drop_cli(
        document_id: str = typer.Argument(..., help="Region document id to remove."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Remove one accepted region from the acquisition manifest."""
        raise_code = nomination_drop_command(document_id, root=root)
        if raise_code:
            raise typer.Exit(raise_code)

    cli.add_typer(nomination_cli, name="nomination")

    @cli.command("measure-extraction")
    def measure_extraction_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to measure."),
        input_dir: Path | None = typer.Option(None, "--input-dir", help="Directory containing source PDFs."),
        corpus_dir: Path | None = typer.Option(None, "--corpus-dir", help="Separate producer-robustness corpus."),
        output_dir: Path | None = typer.Option(None, "--output-dir", help="Snapshot output directory."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Measure form-text retention and PDF producer layers."""
        raise_code = measure_extraction_command(
            year=year,
            root=root,
            input_dir=input_dir,
            corpus_dir=corpus_dir,
            output_dir=output_dir,
        )
        if raise_code:
            raise typer.Exit(raise_code)

    @cli.command("review-table")
    def review_table_cli(
        document: str = typer.Option(..., "--document", "--doc", help="Manifest document id to review."),
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to review."),
        output: Path | None = typer.Option(None, "--output", help="HTML output file outside the repository."),
        all_rows: bool = typer.Option(False, "--all-rows", help="Include every source row."),
        hardest: int | None = typer.Option(None, "--hardest", help="Include the N highest-scoring rows."),
        candidate_root: Path | None = typer.Option(None, "--candidate-root", help="Candidate workspace produced from a completed derivation run."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Render cleaned input, graph expression, and deterministic pseudocode."""
        raise_code = review_table_command(
            year=year,
            document=document,
            root=root,
            output=output,
            all_rows=all_rows,
            hardest=hardest,
            candidate_root=candidate_root,
        )
        if raise_code:
            raise typer.Exit(raise_code)

    @cli.command("summarize-runs")
    def summarize_runs_cli(
        run_dir: list[Path] = typer.Option(..., "--run-dir", help="Ordered run directory; repeat oldest to newest."),
        output: Path = typer.Option(..., "--output", help="Markdown output outside the repository."),
        expected_document: list[str] = typer.Option([], "--expected-document", help="Expected document id; repeat as needed."),
        baseline_window: int = typer.Option(3, "--baseline-window", min=1, help="Number of preceding runs used for the noise band."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Summarize ordered derivation runs without constructing a provider client."""
        raise_code = summarize_runs_command(
            run_paths=run_dir,
            output=output,
            expected_documents=expected_document,
            baseline_window=baseline_window,
            root=root,
        )
        if raise_code:
            raise typer.Exit(raise_code)

    @cli.command("regenerate-candidate")
    def regenerate_candidate_cli(
        run_dir: Path = typer.Option(..., "--run-dir", help="Completed run directory containing derive reports."),
        output_dir: Path = typer.Option(..., "--output-dir", help="New candidate workspace outside the repository."),
        year: str = typer.Option("2025", "--year", "-y", help="Tax year of the run."),
        expected_document: list[str] = typer.Option([], "--expected-document", help="Expected document id; repeat to override the manifest."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Build a pending-review candidate without calling a provider or publishing it."""
        raise_code = regenerate_candidate_command(
            run_dir=run_dir,
            output_dir=output_dir,
            year=year,
            root=root,
            expected_documents=expected_document or None,
        )
        if raise_code:
            raise typer.Exit(raise_code)

    @cli.command("doctor")
    def doctor_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to inspect."),
        max_open_item_commits: int = typer.Option(
            20,
            "--max-open-item-commits",
            min=0,
            help="Flag an open handoff item after this many commits touching the handoff.",
        ),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Check plan claims and pipeline agreements; exit 1 when evidence is missing or inconsistent."""
        raise_code = doctor_command(
            year=year,
            root=root,
            max_open_item_commits=max_open_item_commits,
        )
        if raise_code:
            raise typer.Exit(raise_code)

    review_cli = typer.Typer(help="Human review verdict helpers.")

    @review_cli.command("apply-verdicts")
    def review_apply_verdicts_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to apply."),
        verdict_dir: Path | None = typer.Option(None, "--verdict-dir", help="Directory of append-only verdict YAML."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Apply human verdict files and propagate confirmed provenance."""
        raise_code = apply_verdicts_command(year=year, root=root, verdict_dir=verdict_dir)
        if raise_code:
            raise typer.Exit(raise_code)

    @review_cli.command("apply-address-verdicts")
    def review_apply_address_verdicts_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to project."),
        ledger_path: Path | None = typer.Option(None, "--ledger", help="Address verdict JSONL override."),
        apply: bool = typer.Option(False, "--apply", help="Write confirmed flags to graph YAML."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Project address-keyed verdicts onto graph nodes."""
        raise_code = apply_address_verdicts_command(
            year=year,
            root=root,
            ledger_path=ledger_path,
            apply=apply,
        )
        if raise_code:
            raise typer.Exit(raise_code)

    @review_cli.command("migrate-scope")
    def review_migrate_scope_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to migrate."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
        refresh: bool = typer.Option(False, "--refresh", help="Rebuild existing scopes."),
    ) -> None:
        """Backfill explicit object scopes for pending review entries."""
        raise_code = migrate_review_scope_command(year=year, root=root, refresh=refresh)
        if raise_code:
            raise typer.Exit(raise_code)

    @review_cli.command("migrate-field-dispositions")
    def review_migrate_field_dispositions_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to migrate."),
        output: Path | None = typer.Option(None, "--output", help="Authored-work output path."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Propose only provable field dispositions and list unresolved work."""
        raise_code = migrate_field_dispositions_command(year=year, root=root, output=output)
        if raise_code:
            raise typer.Exit(raise_code)

    cli.add_typer(review_cli, name="review")

    @cli.command("serve")
    def serve_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to serve."),
        source: str | None = typer.Option(None, "--source", help="Graph source: sqlite or yaml. Defaults to sqlite when built, else yaml."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
        sweep_orphans: bool = typer.Option(False, "--sweep-orphans", help="Stop abandoned Tax Graph serve processes and exit."),
    ) -> None:
        """Start the MCP stdio server."""
        raise_code = serve_command(year=year, root=root, source=source, sweep_orphans=sweep_orphans)
        if raise_code:
            raise typer.Exit(raise_code)

    drill_cli = typer.Typer(help="Extraction verification drill helpers.")

    @drill_cli.command("run")
    def drill_run_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to drill."),
        catalog: Path | None = typer.Option(None, "--catalog", help="Override drill catalog YAML."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Run seeded-defect drills and report layer attribution."""
        raise_code = drill_run_command(year=year, root=root, catalog=catalog)
        if raise_code:
            raise typer.Exit(raise_code)

    cli.add_typer(drill_cli, name="drill")

    verify_cli = typer.Typer(help="Extraction verification helpers.")

    @verify_cli.command("mine-examples")
    def verify_mine_examples_cli(
        doc: str = typer.Option(..., "--doc", help="Manifest document id to mine."),
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to mine."),
        output_dir: Path | None = typer.Option(None, "--output-dir", help="Directory for confirmed fixtures."),
        confirm: bool = typer.Option(False, "--confirm", help="Freeze agreed examples after human confirmation."),
        freeze_agreed: bool = typer.Option(
            False,
            "--freeze-agreed",
            help="Freeze machine-agreed examples with pending human review and a deferred-review queue entry.",
        ),
        limit: int | None = typer.Option(None, "--limit", help="Maximum examples to mine."),
        source: str | None = typer.Option(None, "--source", help="Graph source: sqlite or yaml. Defaults to auto."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Mine worked examples from rendered IRS source text."""
        raise_code = verify_mine_examples_command(
            doc=doc,
            year=year,
            root=root,
            output_dir=output_dir,
            confirm=confirm,
            freeze_agreed=freeze_agreed,
            limit=limit,
            source=source,
        )
        if raise_code:
            raise typer.Exit(raise_code)

    @verify_cli.command("replay-examples")
    def verify_replay_examples_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to replay."),
        examples_dir: Path | None = typer.Option(None, "--examples-dir", help="Directory of frozen IRS example fixtures."),
        source: str | None = typer.Option(None, "--source", help="Graph source: sqlite or yaml. Defaults to auto."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Replay frozen IRS worked-example fixtures."""
        raise_code = verify_replay_examples_command(year=year, root=root, examples_dir=examples_dir, source=source)
        if raise_code:
            raise typer.Exit(raise_code)

    @verify_cli.command("nversion")
    def verify_nversion_cli(
        doc: str = typer.Option(..., "--doc", help="Manifest document id to corroborate."),
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to corroborate."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Run N-version extraction corroboration."""
        raise_code = verify_nversion_command(doc=doc, year=year, root=root)
        if raise_code:
            raise typer.Exit(raise_code)

    @verify_cli.command("report")
    def verify_report_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to report."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Roll up per-form verification metrics (tiers, flags, payoff lines)."""
        raise_code = verify_report_command(year=year, root=root)
        if raise_code:
            raise typer.Exit(raise_code)

    @verify_cli.command("expression-agreement")
    def verify_expression_agreement_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to compare."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Compare generated expressions with the protected live graph."""
        raise_code = verify_expression_agreement_command(year=year, root=root)
        if raise_code:
            raise typer.Exit(raise_code)

    @verify_cli.command("form-completeness")
    def verify_form_completeness_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to report."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Measure expressions plus verbatim citations against form cells."""
        raise_code = verify_form_completeness_command(year=year, root=root)
        if raise_code:
            raise typer.Exit(raise_code)

    @verify_cli.command("prompt-bench")
    def verify_prompt_bench_cli(
        doc: str = typer.Option(..., "--doc", help="Manifest document id to inspect."),
        target_ids: list[str] = typer.Option(..., "--id", help="Field-map control or formula cell id; repeat for a small list."),
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to inspect."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Print exact prompts, responses, and deterministic validation results."""
        raise_code = prompt_bench_command(
            doc=doc,
            target_ids=target_ids,
            year=year,
            root=root,
        )
        if raise_code:
            raise typer.Exit(raise_code)

    @verify_cli.command("record")
    def verify_record_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to render."),
        rollup_path: Path | None = typer.Option(None, "--rollup-path", help="Optional VERIFICATION.md output path."),
        pages_dir: Path | None = typer.Option(None, "--pages-dir", help="Optional per-form page output directory."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Generate VERIFICATION.md plus per-form verification pages."""
        raise_code = verify_record_command(year=year, root=root, rollup_path=rollup_path, pages_dir=pages_dir)
        if raise_code:
            raise typer.Exit(raise_code)

    @verify_cli.command("diff-drafts")
    def verify_diff_drafts_cli(
        doc: str = typer.Option(..., "--doc", help="Manifest document id to diff."),
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to diff."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Diff a draft re-extraction against the promoted live graph."""
        raise_code = verify_diff_drafts_command(doc=doc, year=year, root=root)
        if raise_code:
            raise typer.Exit(raise_code)

    @verify_cli.command("parameter-diff")
    def verify_parameter_diff_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to diff."),
        offline_fixture: Path | None = typer.Option(None, "--offline-fixture", help="Path to offline PE parameter JSON."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Diff parameter nodes against PolicyEngine US."""
        raise_code = verify_parameter_diff_command(year=year, root=root, offline_fixture=offline_fixture)
        if raise_code:
            raise typer.Exit(raise_code)

    cli.add_typer(verify_cli, name="verify")

    oracle_cli = typer.Typer(help="Differential oracle helpers.")

    @oracle_cli.command("install")
    def oracle_install_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to install."),
        archive: Path | None = typer.Option(None, "--archive", help="Use a local pre-downloaded OTS archive."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Install the pinned OpenTaxSolver release."""
        raise_code = oracle_install_command(year=year, root=root, archive=archive)
        if raise_code:
            raise typer.Exit(raise_code)

    @oracle_cli.command("fuzz")
    def oracle_fuzz_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to fuzz."),
        n: int = typer.Option(100, "--n", help="Number of generated scenarios."),
        seed: int = typer.Option(0, "--seed", help="Deterministic PRNG seed."),
        output_dir: Path | None = typer.Option(None, "--output-dir", help="Directory for OTS inputs and triage."),
        source: str | None = typer.Option(None, "--source", help="Graph source: sqlite or yaml. Defaults to auto."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Run a seeded live OTS fuzz comparison."""
        raise_code = oracle_fuzz_command(
            year=year,
            n=n,
            seed=seed,
            root=root,
            output_dir=output_dir,
            source=source,
        )
        if raise_code:
            raise typer.Exit(raise_code)

    @oracle_cli.command("freeze")
    def oracle_freeze_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to freeze."),
        n: int = typer.Option(20, "--n", help="Number of generated scenarios."),
        seed: int = typer.Option(0, "--seed", help="Deterministic PRNG seed."),
        corpus_dir: Path | None = typer.Option(None, "--corpus-dir", help="Directory for frozen corpus examples."),
        generated_date: str | None = typer.Option(None, "--generated-date", help="Manifest generated date override."),
        oracle_version: str = typer.Option("ots_2025_23.06", "--oracle-version", help="Pinned oracle version label."),
        source: str | None = typer.Option(None, "--source", help="Graph source: sqlite or yaml. Defaults to auto."),
        adjudicate_known_ots_sdtw_defects: bool = typer.Option(
            False,
            "--adjudicate-known-ots-sdtw-defects",
            help="Freeze only the source-verified OTS Schedule D gate defect with IRS-adjudicated values.",
        ),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Freeze agreed oracle scenarios into offline examples."""
        raise_code = oracle_freeze_command(
            year=year,
            n=n,
            seed=seed,
            root=root,
            corpus_dir=corpus_dir,
            generated_date=generated_date,
            oracle_version=oracle_version,
            source=source,
            adjudicate_known_ots_sdtw_defects=adjudicate_known_ots_sdtw_defects,
        )
        if raise_code:
            raise typer.Exit(raise_code)

    @oracle_cli.command("replay-corpus")
    def oracle_replay_corpus_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to replay."),
        corpus_dir: Path | None = typer.Option(None, "--corpus-dir", help="Directory for frozen corpus examples."),
        source: str | None = typer.Option(None, "--source", help="Graph source: sqlite or yaml. Defaults to auto."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Replay frozen oracle corpus examples."""
        raise_code = oracle_replay_corpus_command(year=year, root=root, corpus_dir=corpus_dir, source=source)
        if raise_code:
            raise typer.Exit(raise_code)

    @oracle_cli.command("pe-liability")
    def oracle_pe_liability_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to diff."),
        corpus_dir: Path | None = typer.Option(None, "--corpus-dir", help="Directory for frozen corpus examples."),
        offline_fixture: str | None = typer.Option(None, "--offline-fixture", help="Canned PE results JSON (offline mode)."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Diff PolicyEngine liability against the frozen corpus (second witness)."""
        raise_code = oracle_pe_liability_command(
            year=year, root=root, corpus_dir=corpus_dir, offline_fixture=offline_fixture
        )
        if raise_code:
            raise typer.Exit(raise_code)

    cli.add_typer(oracle_cli, name="oracle")

    frontier_cli = typer.Typer(help="Frontier registry and coverage helpers.", invoke_without_command=True)

    @frontier_cli.callback(invoke_without_command=True)
    def frontier_query_cli(
        ctx: typer.Context,
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to query."),
        json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Print the frontier worklist and SOI-weighted coverage."""
        if ctx.invoked_subcommand is not None:
            return
        raise_code = frontier_query_command(year=year, root=root, json_output=json_output)
        if raise_code:
            raise typer.Exit(raise_code)

    @frontier_cli.command("build")
    def frontier_build_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to build."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Build the derived frontier registry."""
        raise_code = frontier_build_command(year=year, root=root)
        if raise_code:
            raise typer.Exit(raise_code)

    cli.add_typer(frontier_cli, name="frontier")

    @cli.command("link")
    def link_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to link."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Resolve reviewed outbound-flow declarations into live edges."""
        raise_code = link_command(year=year, root=root)
        if raise_code:
            raise typer.Exit(raise_code)

    @cli.command("acquire")
    def acquire_cli(
        year: str = typer.Argument("2025"),
        check: bool = typer.Option(False, "--check", help="Report changes without updating state."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Acquire source documents and verify rendered citations."""
        raise_code = acquire_command(year=year, check=check, root=root)
        if raise_code:
            raise typer.Exit(raise_code)

    @cli.command("extract")
    def extract_cli(
        doc: str | None = typer.Option(None, "--doc", help="Manifest document id to extract."),
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to extract."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Extract draft graph objects from rendered source artifacts."""
        raise_code = extract_command(doc=doc, year=year, root=root)
        if raise_code:
            raise typer.Exit(raise_code)

    @cli.command("intake")
    def intake_cli(
        drop_dir: Path = typer.Option(..., "--drop-dir", help="Local directory containing rendered tax documents."),
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to route."),
        claims: Path | None = typer.Option(None, "--claims", help="YAML claims/resolutions input."),
        resolutions: Path | None = typer.Option(None, "--resolutions", help="YAML trigger resolutions."),
        output: Path | None = typer.Option(None, "--output", help="Write machine-readable intake JSON."),
        provider: str | None = typer.Option(None, "--provider", help="Override the configured classifier provider."),
        consent: bool = typer.Option(False, "--consent", help="Explicitly consent to configured provider egress."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Crawl, classify, route, and reconcile a local document drop."""
        raise_code = intake_command(
            drop_dir,
            year=year,
            root=root,
            claims_path=claims,
            resolutions_path=resolutions,
            output=output,
            provider=provider,
            consent=consent,
        )
        if raise_code:
            raise typer.Exit(raise_code)

    @cli.command(
        "extend",
        context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    )
    def extend_cli(ctx: typer.Context) -> None:
        """Run ``extend doctor``, ``extend <doc_id>``, ``extend accept``, or ``extend package``."""
        raise_code = _dispatch_extend_tokens(list(ctx.args))
        if raise_code:
            raise typer.Exit(raise_code)

    return cli


def _dispatch_extend_tokens(tokens: list[str]) -> int:
    """Dispatch the compact ``extend`` command surface for Typer and tests."""
    if not tokens:
        print("Usage: tax-graph extend doctor | <doc_id> | accept <doc_id> | package <doc_id>")
        return 2
    action = tokens[0]
    if action == "doctor":
        parser = argparse.ArgumentParser(prog="tax-graph extend doctor")
        parser.add_argument("--network", action="store_true")
        parser.add_argument("--network-url", default=None)
        parser.add_argument("--root", default=None)
        args = parser.parse_args(tokens[1:])
        return extend_doctor_command(root=args.root, network=args.network, network_url=args.network_url)
    if action in {"accept", "package"}:
        parser = argparse.ArgumentParser(prog=f"tax-graph extend {action}")
        parser.add_argument("doc_id")
        parser.add_argument("--year", "-y", default="2025")
        parser.add_argument("--root", default=None)
        if action == "package":
            parser.add_argument("--output-dir", default=None)
        args = parser.parse_args(tokens[1:])
        if action == "accept":
            return extend_accept_command(args.doc_id, year=args.year, root=args.root)
        return extend_package_command(args.doc_id, year=args.year, root=args.root, output_dir=args.output_dir)

    parser = argparse.ArgumentParser(prog="tax-graph extend <doc_id>")
    parser.add_argument("doc_id")
    parser.add_argument("--year", "-y", default="2025")
    parser.add_argument("--url", default=None)
    parser.add_argument("--kind", default=None)
    parser.add_argument("--title", default=None)
    parser.add_argument("--instructions-url", default=None)
    parser.add_argument("--instructions-document-id", default=None)
    parser.add_argument("--root", default=None)
    args = parser.parse_args(tokens)
    return extend_document_command(
        args.doc_id,
        year=args.year,
        root=args.root,
        url=args.url,
        kind=args.kind,
        title=args.title,
        instructions_url=args.instructions_url,
        instructions_document_id=args.instructions_document_id,
    )


def _fallback_app() -> int:
    parser = argparse.ArgumentParser(prog="tax-graph")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("year", nargs="?", default="2025")
    validate_parser.add_argument("--root", default=None)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--facts", "-f", required=True)
    run_parser.add_argument("--year", "-y", default="2025")
    run_parser.add_argument("--target", "-t", default=DEFAULT_TARGET)
    run_parser.add_argument("--source", choices=["sqlite", "yaml"], default=None)
    run_parser.add_argument("--prior-record", default=None)
    run_parser.add_argument("--record-dir", default=None)
    run_parser.add_argument("--no-record", action="store_true")
    run_parser.add_argument("--return-id", default=None)
    run_parser.add_argument("--output-root", default=None)
    run_parser.add_argument("--export-bundle", action="store_true")
    run_parser.add_argument("--root", default=None)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("year", nargs="?", default="2025")
    build_parser.add_argument("--root", default=None)

    review_parser = subparsers.add_parser("review")
    review_subparsers = review_parser.add_subparsers(dest="review_command", required=True)
    review_apply_parser = review_subparsers.add_parser("apply-verdicts")
    review_apply_parser.add_argument("--year", "-y", default="2025")
    review_apply_parser.add_argument("--verdict-dir", default=None)
    review_apply_parser.add_argument("--root", default=None)
    review_address_parser = review_subparsers.add_parser("apply-address-verdicts")
    review_address_parser.add_argument("--year", "-y", default="2025")
    review_address_parser.add_argument("--ledger", dest="ledger_path", default=None)
    review_address_parser.add_argument("--apply", action="store_true")
    review_address_parser.add_argument("--root", default=None)
    review_scope_parser = review_subparsers.add_parser("migrate-scope")
    review_scope_parser.add_argument("--year", "-y", default="2025")
    review_scope_parser.add_argument("--root", default=None)
    review_scope_parser.add_argument("--refresh", action="store_true")
    review_field_parser = review_subparsers.add_parser("migrate-field-dispositions")
    review_field_parser.add_argument("--year", "-y", default="2025")
    review_field_parser.add_argument("--output", default=None)
    review_field_parser.add_argument("--root", default=None)

    frontier_parser = subparsers.add_parser("frontier")
    frontier_parser.add_argument("--year", "-y", default="2025")
    frontier_parser.add_argument("--json", action="store_true")
    frontier_parser.add_argument("--root", default=None)
    frontier_subparsers = frontier_parser.add_subparsers(dest="frontier_command", required=False)
    frontier_build_parser = frontier_subparsers.add_parser("build")
    frontier_build_parser.add_argument("--year", "-y", default="2025")
    frontier_build_parser.add_argument("--root", default=None)

    link_parser = subparsers.add_parser("link")
    link_parser.add_argument("--year", "-y", default="2025")
    link_parser.add_argument("--root", default=None)

    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--year", "-y", default="2025")
    serve_parser.add_argument("--source", choices=["sqlite", "yaml"], default=None)
    serve_parser.add_argument("--root", default=None)
    serve_parser.add_argument("--sweep-orphans", action="store_true")

    drill_parser = subparsers.add_parser("drill")
    drill_subparsers = drill_parser.add_subparsers(dest="drill_command", required=True)
    drill_run_parser = drill_subparsers.add_parser("run")
    drill_run_parser.add_argument("--year", "-y", default="2025")
    drill_run_parser.add_argument("--catalog", default=None)
    drill_run_parser.add_argument("--root", default=None)

    verify_parser = subparsers.add_parser("verify")
    verify_subparsers = verify_parser.add_subparsers(dest="verify_command", required=True)
    verify_mine_parser = verify_subparsers.add_parser("mine-examples")
    verify_mine_parser.add_argument("--doc", required=True)
    verify_mine_parser.add_argument("--year", "-y", default="2025")
    verify_mine_parser.add_argument("--output-dir", default=None)
    verify_mine_parser.add_argument("--confirm", action="store_true")
    verify_mine_parser.add_argument("--freeze-agreed", action="store_true")
    verify_mine_parser.add_argument("--limit", type=int, default=None)
    verify_mine_parser.add_argument("--source", choices=["sqlite", "yaml"], default=None)
    verify_mine_parser.add_argument("--root", default=None)

    verify_replay_parser = verify_subparsers.add_parser("replay-examples")
    verify_replay_parser.add_argument("--year", "-y", default="2025")
    verify_replay_parser.add_argument("--examples-dir", default=None)
    verify_replay_parser.add_argument("--source", choices=["sqlite", "yaml"], default=None)
    verify_replay_parser.add_argument("--root", default=None)

    verify_nversion_parser = verify_subparsers.add_parser("nversion")
    verify_nversion_parser.add_argument("--doc", required=True)
    verify_nversion_parser.add_argument("--year", "-y", default="2025")
    verify_nversion_parser.add_argument("--root", default=None)

    verify_prompt_bench_parser = verify_subparsers.add_parser("prompt-bench")
    verify_prompt_bench_parser.add_argument("--doc", required=True)
    verify_prompt_bench_parser.add_argument("--id", dest="target_ids", action="append", required=True)
    verify_prompt_bench_parser.add_argument("--year", "-y", default="2025")
    verify_prompt_bench_parser.add_argument("--root", default=None)

    verify_record_parser = verify_subparsers.add_parser("record")
    verify_record_parser.add_argument("--year", "-y", default="2025")
    verify_record_parser.add_argument("--rollup-path", default=None)
    verify_record_parser.add_argument("--pages-dir", default=None)
    verify_record_parser.add_argument("--root", default=None)

    oracle_parser = subparsers.add_parser("oracle")
    oracle_subparsers = oracle_parser.add_subparsers(dest="oracle_command", required=True)
    oracle_install_parser = oracle_subparsers.add_parser("install")
    oracle_install_parser.add_argument("--year", "-y", default="2025")
    oracle_install_parser.add_argument("--archive", default=None)
    oracle_install_parser.add_argument("--root", default=None)

    oracle_fuzz_parser = oracle_subparsers.add_parser("fuzz")
    oracle_fuzz_parser.add_argument("--year", "-y", default="2025")
    oracle_fuzz_parser.add_argument("--n", type=int, default=100)
    oracle_fuzz_parser.add_argument("--seed", type=int, default=0)
    oracle_fuzz_parser.add_argument("--output-dir", default=None)
    oracle_fuzz_parser.add_argument("--source", choices=["sqlite", "yaml"], default=None)
    oracle_fuzz_parser.add_argument("--root", default=None)

    oracle_freeze_parser = oracle_subparsers.add_parser("freeze")
    oracle_freeze_parser.add_argument("--year", "-y", default="2025")
    oracle_freeze_parser.add_argument("--n", type=int, default=20)
    oracle_freeze_parser.add_argument("--seed", type=int, default=0)
    oracle_freeze_parser.add_argument("--corpus-dir", default=None)
    oracle_freeze_parser.add_argument("--generated-date", default=None)
    oracle_freeze_parser.add_argument("--oracle-version", default="ots_2025_23.06")
    oracle_freeze_parser.add_argument("--source", choices=["sqlite", "yaml"], default=None)
    oracle_freeze_parser.add_argument("--adjudicate-known-ots-sdtw-defects", action="store_true")
    oracle_freeze_parser.add_argument("--root", default=None)

    oracle_replay_corpus_parser = oracle_subparsers.add_parser("replay-corpus")
    oracle_replay_corpus_parser.add_argument("--year", "-y", default="2025")
    oracle_replay_corpus_parser.add_argument("--corpus-dir", default=None)
    oracle_replay_corpus_parser.add_argument("--source", choices=["sqlite", "yaml"], default=None)
    oracle_replay_corpus_parser.add_argument("--root", default=None)

    oracle_pe_liability_parser = oracle_subparsers.add_parser("pe-liability")
    oracle_pe_liability_parser.add_argument("--year", "-y", default="2025")
    oracle_pe_liability_parser.add_argument("--corpus-dir", default=None)
    oracle_pe_liability_parser.add_argument("--offline-fixture", default=None)
    oracle_pe_liability_parser.add_argument("--root", default=None)

    acquire_parser = subparsers.add_parser("acquire")
    acquire_parser.add_argument("year", nargs="?", default="2025")
    acquire_parser.add_argument("--check", action="store_true")
    acquire_parser.add_argument("--root", default=None)

    extract_parser = subparsers.add_parser("extract")
    extract_parser.add_argument("--doc", default=None)
    extract_parser.add_argument("--year", "-y", default="2025")
    extract_parser.add_argument("--root", default=None)

    promote_instructions_parser = subparsers.add_parser("promote-instructions")
    promote_instructions_parser.add_argument("--year", "-y", default="2025")
    promote_instructions_parser.add_argument("--source-document-id", default=None)
    promote_instructions_parser.add_argument("--html-path", default=None)
    promote_instructions_parser.add_argument(
        "--citation-filename",
        default="instruction-form-1040-html.yaml",
    )
    promote_instructions_parser.add_argument("--root", default=None)

    harvest_worksheet_parser = subparsers.add_parser("harvest-worksheet")
    harvest_worksheet_parser.add_argument("--year", "-y", default="2025")
    harvest_worksheet_parser.add_argument("--source-document-id", default=None)
    harvest_worksheet_parser.add_argument("--html-path", default=None)
    harvest_worksheet_parser.add_argument("--document-id", default=None)
    harvest_worksheet_parser.add_argument("--title", default=None)
    harvest_worksheet_parser.add_argument("--start-anchor", default=None)
    harvest_worksheet_parser.add_argument("--draft-dir", default=None)
    harvest_worksheet_parser.add_argument("--root", default=None)

    nomination_parser = subparsers.add_parser("nomination")
    nomination_subparsers = nomination_parser.add_subparsers(dest="nomination_command", required=True)
    nomination_list_parser = nomination_subparsers.add_parser("list")
    nomination_list_parser.add_argument("--year", "-y", default="2025")
    nomination_list_parser.add_argument("--run-dir", default=None)
    nomination_list_parser.add_argument("--evidence", action="append", default=[])
    nomination_list_parser.add_argument("--json", action="store_true")
    nomination_list_parser.add_argument("--root", default=None)

    nomination_accept_parser = nomination_subparsers.add_parser("accept")
    nomination_accept_parser.add_argument("--title", required=True)
    nomination_accept_parser.add_argument("--source-document-id", required=True)
    nomination_accept_parser.add_argument("--year", "-y", default="2025")
    nomination_accept_parser.add_argument("--document-id", default=None)
    nomination_accept_parser.add_argument("--kind", default="worksheet")
    nomination_accept_parser.add_argument("--run-dir", default=None)
    nomination_accept_parser.add_argument("--evidence", action="append", default=[])
    nomination_accept_parser.add_argument("--html-path", default=None)
    nomination_accept_parser.add_argument("--root", default=None)

    nomination_drop_parser = nomination_subparsers.add_parser("drop")
    nomination_drop_parser.add_argument("document_id")
    nomination_drop_parser.add_argument("--root", default=None)

    measure_extraction_parser = subparsers.add_parser("measure-extraction")
    measure_extraction_parser.add_argument("--year", "-y", default="2025")
    measure_extraction_parser.add_argument("--input-dir", default=None)
    measure_extraction_parser.add_argument("--corpus-dir", default=None)
    measure_extraction_parser.add_argument("--output-dir", default=None)
    measure_extraction_parser.add_argument("--root", default=None)

    review_table_parser = subparsers.add_parser("review-table")
    review_table_parser.add_argument("--document", "--doc", dest="document", required=True)
    review_table_parser.add_argument("--year", "-y", default="2025")
    review_table_parser.add_argument("--output", default=None)
    review_table_parser.add_argument("--all-rows", action="store_true")
    review_table_parser.add_argument("--hardest", type=int, default=None)
    review_table_parser.add_argument("--candidate-root", default=None)
    review_table_parser.add_argument("--root", default=None)

    summarize_runs_parser = subparsers.add_parser("summarize-runs")
    summarize_runs_parser.add_argument("--run-dir", action="append", required=True)
    summarize_runs_parser.add_argument("--output", required=True)
    summarize_runs_parser.add_argument("--expected-document", action="append", default=[])
    summarize_runs_parser.add_argument("--baseline-window", type=int, default=3)
    summarize_runs_parser.add_argument("--root", default=None)

    regenerate_candidate_parser = subparsers.add_parser("regenerate-candidate")
    regenerate_candidate_parser.add_argument("--run-dir", required=True)
    regenerate_candidate_parser.add_argument("--output-dir", required=True)
    regenerate_candidate_parser.add_argument("--year", "-y", default="2025")
    regenerate_candidate_parser.add_argument("--expected-document", action="append", default=[])
    regenerate_candidate_parser.add_argument("--root", default=None)

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Check plan claims and pipeline agreements; exit 1 when evidence is missing or inconsistent.",
    )
    doctor_parser.add_argument("--year", "-y", default="2025")
    doctor_parser.add_argument("--max-open-item-commits", type=int, default=20)
    doctor_parser.add_argument("--root", default=None)

    intake_parser = subparsers.add_parser("intake")
    intake_parser.add_argument("--drop-dir", required=True)
    intake_parser.add_argument("--year", "-y", default="2025")
    intake_parser.add_argument("--claims", default=None)
    intake_parser.add_argument("--resolutions", default=None)
    intake_parser.add_argument("--output", default=None)
    intake_parser.add_argument("--provider", default=None)
    intake_parser.add_argument("--consent", action="store_true")
    intake_parser.add_argument("--root", default=None)

    extend_parser = subparsers.add_parser("extend")
    extend_parser.add_argument("action_or_doc", nargs="?", default=None)
    extend_parser.add_argument("doc_id", nargs="?", default=None)
    extend_parser.add_argument("--year", "-y", default="2025")
    extend_parser.add_argument("--url", default=None)
    extend_parser.add_argument("--kind", default=None)
    extend_parser.add_argument("--title", default=None)
    extend_parser.add_argument("--instructions-url", default=None)
    extend_parser.add_argument("--instructions-document-id", default=None)
    extend_parser.add_argument("--network", action="store_true")
    extend_parser.add_argument("--network-url", default=None)
    extend_parser.add_argument("--output-dir", default=None)
    extend_parser.add_argument("--root", default=None)

    args = parser.parse_args()
    if args.command == "validate":
        return validate_command(year=args.year, root=args.root)
    if args.command == "run":
        return run_command(
            facts=args.facts,
            year=args.year,
            target=args.target,
            root=args.root,
            source=args.source,
            prior_record=args.prior_record,
            record_dir=args.record_dir,
            no_record=args.no_record,
            return_id=args.return_id,
            output_root=args.output_root,
            export_bundle=args.export_bundle,
        )
    if args.command == "build":
        return build_command(year=args.year, root=args.root)
    if args.command == "review" and args.review_command == "apply-verdicts":
        return apply_verdicts_command(year=args.year, root=args.root, verdict_dir=args.verdict_dir)
    if args.command == "review" and args.review_command == "apply-address-verdicts":
        return apply_address_verdicts_command(
            year=args.year,
            root=args.root,
            ledger_path=args.ledger_path,
            apply=args.apply,
        )
    if args.command == "review" and args.review_command == "migrate-scope":
        return migrate_review_scope_command(year=args.year, root=args.root, refresh=args.refresh)
    if args.command == "review" and args.review_command == "migrate-field-dispositions":
        return migrate_field_dispositions_command(year=args.year, root=args.root, output=args.output)
    if args.command == "frontier" and args.frontier_command == "build":
        return frontier_build_command(year=args.year, root=args.root)
    if args.command == "frontier":
        return frontier_query_command(year=args.year, root=args.root, json_output=args.json)
    if args.command == "link":
        return link_command(year=args.year, root=args.root)
    if args.command == "serve":
        return serve_command(year=args.year, root=args.root, source=args.source, sweep_orphans=args.sweep_orphans)
    if args.command == "drill" and args.drill_command == "run":
        return drill_run_command(year=args.year, root=args.root, catalog=args.catalog)
    if args.command == "verify" and args.verify_command == "mine-examples":
        return verify_mine_examples_command(
            doc=args.doc,
            year=args.year,
            root=args.root,
            output_dir=args.output_dir,
            confirm=args.confirm,
            freeze_agreed=args.freeze_agreed,
            limit=args.limit,
            source=args.source,
        )
    if args.command == "verify" and args.verify_command == "replay-examples":
        return verify_replay_examples_command(
            year=args.year,
            root=args.root,
            examples_dir=args.examples_dir,
            source=args.source,
        )
    if args.command == "verify" and args.verify_command == "nversion":
        return verify_nversion_command(doc=args.doc, year=args.year, root=args.root)
    if args.command == "verify" and args.verify_command == "prompt-bench":
        return prompt_bench_command(
            doc=args.doc,
            target_ids=args.target_ids,
            year=args.year,
            root=args.root,
        )
    if args.command == "verify" and args.verify_command == "record":
        return verify_record_command(
            year=args.year,
            root=args.root,
            rollup_path=args.rollup_path,
            pages_dir=args.pages_dir,
        )
    if args.command == "oracle" and args.oracle_command == "install":
        return oracle_install_command(year=args.year, root=args.root, archive=args.archive)
    if args.command == "oracle" and args.oracle_command == "fuzz":
        return oracle_fuzz_command(
            year=args.year,
            n=args.n,
            seed=args.seed,
            root=args.root,
            output_dir=args.output_dir,
            source=args.source,
        )
    if args.command == "oracle" and args.oracle_command == "freeze":
        return oracle_freeze_command(
            year=args.year,
            n=args.n,
            seed=args.seed,
            root=args.root,
            corpus_dir=args.corpus_dir,
            generated_date=args.generated_date,
            oracle_version=args.oracle_version,
            source=args.source,
            adjudicate_known_ots_sdtw_defects=args.adjudicate_known_ots_sdtw_defects,
        )
    if args.command == "oracle" and args.oracle_command == "replay-corpus":
        return oracle_replay_corpus_command(
            year=args.year,
            root=args.root,
            corpus_dir=args.corpus_dir,
            source=args.source,
        )
    if args.command == "oracle" and args.oracle_command == "pe-liability":
        return oracle_pe_liability_command(
            year=args.year,
            root=args.root,
            corpus_dir=args.corpus_dir,
            offline_fixture=args.offline_fixture,
        )
    if args.command == "acquire":
        return acquire_command(year=args.year, check=args.check, root=args.root)
    if args.command == "extract":
        return extract_command(doc=args.doc, year=args.year, root=args.root)
    if args.command == "promote-instructions":
        return promote_instruction_command(
            year=args.year,
            root=args.root,
            source_document_id=args.source_document_id,
            html_path=args.html_path,
            citation_filename=args.citation_filename,
        )
    if args.command == "harvest-worksheet":
        return harvest_worksheet_command(
            year=args.year,
            root=args.root,
            source_document_id=args.source_document_id,
            html_path=args.html_path,
            document_id=args.document_id,
            title=args.title,
            start_anchor=args.start_anchor,
            draft_dir=args.draft_dir,
        )
    if args.command == "nomination" and args.nomination_command == "list":
        return nomination_list_command(
            year=args.year,
            root=args.root,
            run_dir=args.run_dir,
            evidence_paths=args.evidence,
            json_output=args.json,
        )
    if args.command == "nomination" and args.nomination_command == "accept":
        return nomination_accept_command(
            title=args.title,
            source_document_id=args.source_document_id,
            year=args.year,
            root=args.root,
            document_id=args.document_id,
            kind=args.kind,
            run_dir=args.run_dir,
            evidence_paths=args.evidence,
            html_path=args.html_path,
        )
    if args.command == "nomination" and args.nomination_command == "drop":
        return nomination_drop_command(args.document_id, root=args.root)
    if args.command == "measure-extraction":
        return measure_extraction_command(
            year=args.year,
            root=args.root,
            input_dir=args.input_dir,
            corpus_dir=args.corpus_dir,
            output_dir=args.output_dir,
        )
    if args.command == "review-table":
        return review_table_command(
            year=args.year,
            document=args.document,
            root=args.root,
            output=args.output,
            all_rows=args.all_rows,
            hardest=args.hardest,
            candidate_root=args.candidate_root,
        )
    if args.command == "summarize-runs":
        return summarize_runs_command(
            run_paths=args.run_dir,
            output=args.output,
            expected_documents=args.expected_document,
            baseline_window=args.baseline_window,
            root=args.root,
        )
    if args.command == "regenerate-candidate":
        return regenerate_candidate_command(
            run_dir=args.run_dir,
            output_dir=args.output_dir,
            year=args.year,
            root=args.root,
            expected_documents=args.expected_document or None,
        )
    if args.command == "doctor":
        return doctor_command(
            year=args.year,
            root=args.root,
            max_open_item_commits=args.max_open_item_commits,
        )
    if args.command == "intake":
        return intake_command(
            args.drop_dir,
            year=args.year,
            root=args.root,
            claims_path=args.claims,
            resolutions_path=args.resolutions,
            output=args.output,
            provider=args.provider,
            consent=args.consent,
        )
    if args.command == "extend":
        if args.action_or_doc == "doctor":
            return extend_doctor_command(root=args.root, network=args.network, network_url=args.network_url)
        if args.action_or_doc == "accept":
            return extend_accept_command(args.doc_id, year=args.year, root=args.root)
        if args.action_or_doc == "package":
            return extend_package_command(args.doc_id, year=args.year, root=args.root, output_dir=args.output_dir)
        if args.action_or_doc:
            return extend_document_command(
                args.action_or_doc,
                year=args.year,
                root=args.root,
                url=args.url,
                kind=args.kind,
                title=args.title,
                instructions_url=args.instructions_url,
                instructions_document_id=args.instructions_document_id,
            )
        return 2
    return 2


app: Callable[[], int] | object = _build_typer_app() if _HAVE_TYPER else _fallback_app


if __name__ == "__main__":
    if _HAVE_TYPER:
        app()
    else:
        raise SystemExit(_fallback_app())
