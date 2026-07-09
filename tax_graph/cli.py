"""Command-line interface for Tax Graph."""

from __future__ import annotations

import argparse
import datetime as _dt
from pathlib import Path
from typing import Any, Callable

from tax_graph import __version__
from tax_graph.config import get_config_value, load_config, project_root
from tax_graph.engine import Engine, Graph, MISSING, load_facts, load_facts_document, render_trace
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

    print("=== computed values ===")
    for node_id in graph.nodes:
        print(f"  {node_id} = {result.values.get(node_id)}")
    if result.missing_required_inputs:
        print("\n=== missing required inputs ===")
        for node_id in result.missing_required_inputs:
            print(f"  {node_id}")
    if prior_ingestion is not None:
        _print_prior_record_report(prior_ingestion)
    record_paths = None
    if not no_record:
        record_paths = _write_return_record(
            facts_path=facts_path,
            facts_document=facts_document,
            result=result,
            graph=graph,
            year=year,
            target=target,
            record_dir=record_dir,
            generated_date=record_date or _dt.date.today().isoformat(),
            tax_graph_version=tax_graph_version or __version__,
        )
        print("\n=== return record ===")
        print(f"  memo: {record_paths['memo']}")
        print(f"  carryforward: {record_paths['carryforward']}")
    print(f"\n=== audit trace: {target} ===")
    render_trace(target, result, graph)
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
) -> int:
    """Start the Tax Graph MCP stdio server."""
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
) -> int:
    """Freeze generated oracle-agreed scenarios into offline examples."""
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
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("=== oracle corpus freeze ===")
    print(f"  scenarios: {summary.scenario_count}")
    print(f"  corpus: {summary.corpus_dir}")
    print(f"  manifest: {summary.manifest_path}")
    return 0


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
    from tax_graph.acquire.fetch import fetch_manifest_documents
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
    _print_acquire_summary(report, citation_report)
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


def _print_acquire_summary(report: Any, citation_report: Any) -> None:
    print("=== acquisition change report ===")
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

    @cli.command("serve")
    def serve_cli(
        year: str = typer.Option("2025", "--year", "-y", help="Tax year to serve."),
        source: str | None = typer.Option(None, "--source", help="Graph source: sqlite or yaml. Defaults to sqlite when built, else yaml."),
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Start the MCP stdio server."""
        raise_code = serve_command(year=year, root=root, source=source)
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

    return cli


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
    run_parser.add_argument("--root", default=None)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("year", nargs="?", default="2025")
    build_parser.add_argument("--root", default=None)

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
    oracle_freeze_parser.add_argument("--root", default=None)

    oracle_replay_corpus_parser = oracle_subparsers.add_parser("replay-corpus")
    oracle_replay_corpus_parser.add_argument("--year", "-y", default="2025")
    oracle_replay_corpus_parser.add_argument("--corpus-dir", default=None)
    oracle_replay_corpus_parser.add_argument("--source", choices=["sqlite", "yaml"], default=None)
    oracle_replay_corpus_parser.add_argument("--root", default=None)

    acquire_parser = subparsers.add_parser("acquire")
    acquire_parser.add_argument("year", nargs="?", default="2025")
    acquire_parser.add_argument("--check", action="store_true")
    acquire_parser.add_argument("--root", default=None)

    extract_parser = subparsers.add_parser("extract")
    extract_parser.add_argument("--doc", default=None)
    extract_parser.add_argument("--year", "-y", default="2025")
    extract_parser.add_argument("--root", default=None)

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
        )
    if args.command == "build":
        return build_command(year=args.year, root=args.root)
    if args.command == "frontier" and args.frontier_command == "build":
        return frontier_build_command(year=args.year, root=args.root)
    if args.command == "frontier":
        return frontier_query_command(year=args.year, root=args.root, json_output=args.json)
    if args.command == "link":
        return link_command(year=args.year, root=args.root)
    if args.command == "serve":
        return serve_command(year=args.year, root=args.root, source=args.source)
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
        )
    if args.command == "oracle" and args.oracle_command == "replay-corpus":
        return oracle_replay_corpus_command(
            year=args.year,
            root=args.root,
            corpus_dir=args.corpus_dir,
            source=args.source,
        )
    if args.command == "acquire":
        return acquire_command(year=args.year, check=args.check, root=args.root)
    if args.command == "extract":
        return extract_command(doc=args.doc, year=args.year, root=args.root)
    return 2


app: Callable[[], int] | object = _build_typer_app() if _HAVE_TYPER else _fallback_app


if __name__ == "__main__":
    if _HAVE_TYPER:
        app()
    else:
        raise SystemExit(_fallback_app())
