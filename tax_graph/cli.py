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
    "schedule_d_2025": "instructions_schedule_d_2025",
    "form_1040_2025": "instructions_form_1040_2025",
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
            print(f"  - {mismatch.citation_id}: {mismatch.reason}")


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

    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--year", "-y", default="2025")
    serve_parser.add_argument("--source", choices=["sqlite", "yaml"], default=None)
    serve_parser.add_argument("--root", default=None)

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
    if args.command == "serve":
        return serve_command(year=args.year, root=args.root, source=args.source)
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
