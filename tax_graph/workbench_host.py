"""Application host that joins the pipeline callback to the artifact workbench."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence


def serve_workbench(root: str | Path, year: str | int = "2025", *, port: int = 0) -> None:
    """Start the review workbench with the pure pipeline re-derive callback."""
    from tax_graph.extract.rederive import build_rederive_handler
    from workbench.server import serve

    root_path = Path(root).resolve()
    handler = build_rederive_handler(root_path, year)
    serve(root_path, year, port=port, rederive_cell=handler)


def main(argv: Sequence[str] | None = None) -> int:
    """Preserve artifact inspection commands and inject the callback for ``serve``."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not _has_serve_command(arguments):
        from workbench.cli import main as artifact_cli

        return int(artifact_cli(arguments))

    parser = argparse.ArgumentParser(prog="review-workbench")
    parser.add_argument("--root", default=".")
    parser.add_argument("--year", default="2025")
    parser.add_argument("command", choices=["serve"])
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(arguments)
    serve_workbench(args.root, args.year, port=args.port)
    return 0


def _has_serve_command(arguments: Sequence[str]) -> bool:
    """Find the command token without mistaking an option value for a command."""
    options_with_values = {"--root", "--year", "--port"}
    skip_value = False
    for value in arguments:
        if skip_value:
            skip_value = False
            continue
        if value in options_with_values:
            skip_value = True
            continue
        if value == "serve":
            return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
