"""Command-line interface for Tax Graph."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from tax_graph.config import load_config, project_root
from tax_graph.engine import Engine, Graph, MISSING, load_facts, render_trace
from tax_graph.validate import validate_graph

try:
    import typer

    _HAVE_TYPER = True
except ImportError:  # pragma: no cover - local fallback for unsynced envs.
    typer = None
    _HAVE_TYPER = False


DEFAULT_TARGET = "form_1040_2025_line_7_capital_gain_loss"


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
) -> int:
    """Execute a graph from taxpayer facts and print values plus trace."""
    root_path = Path(root).resolve() if root is not None else project_root()
    load_config(root=root_path)
    graph = Graph(year, root=root_path)
    fact_values = load_facts(Path(facts))
    result = Engine(graph).execute(fact_values)

    print("=== computed values ===")
    for node_id in graph.nodes:
        print(f"  {node_id} = {result.values.get(node_id)}")
    if result.missing_required_inputs:
        print("\n=== missing required inputs ===")
        for node_id in result.missing_required_inputs:
            print(f"  {node_id}")
    print(f"\n=== audit trace: {target} ===")
    render_trace(target, result, graph)
    return 1 if result.values.get(target) is MISSING else 0


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
        root: Path | None = typer.Option(None, "--root", help="Project root override."),
    ) -> None:
        """Execute a return graph from taxpayer facts."""
        raise_code = run_command(facts=facts, year=year, target=target, root=root)
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
    run_parser.add_argument("--root", default=None)

    args = parser.parse_args()
    if args.command == "validate":
        return validate_command(year=args.year, root=args.root)
    if args.command == "run":
        return run_command(facts=args.facts, year=args.year, target=args.target, root=args.root)
    return 2


app: Callable[[], int] | object = _build_typer_app() if _HAVE_TYPER else _fallback_app


if __name__ == "__main__":
    if _HAVE_TYPER:
        app()
    else:
        raise SystemExit(_fallback_app())
