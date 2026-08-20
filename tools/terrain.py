"""Print the authoritative configuration surface and who reads it.

This exists because on 2026-08-20 the Architect specced a round to build a
machine-readable core set that already existed, in `config/document_tiers.yaml`,
one of four files in `config/`.  The search that missed it looked for the phrase
"core set" in three hand-picked markdown files.

The answer is deliberately NOT a maintained terrain document.  We already have
evidence that hand-written indexes drift: the 2026-08-11 handoff recorded that
"the tier list and the manifest have already drifted", and they had drifted
again by 2026-08-20.  So this output is derived on every run - it cannot go
stale, because nothing stores it.

Usage:
    .venv\\Scripts\\python.exe tools/terrain.py
    .venv\\Scripts\\python.exe tools/terrain.py --key core_documents
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

import yaml


# Where policy lives.  Graph content, drafts and test fixtures are deliberately
# excluded: this is the surface a spec must consult, not the corpus.
AUTHORITATIVE_GLOBS = ("config/*.yaml", "config/*.yml", "data/**/*.yaml")

CODE_GLOBS = ("*.py",)


def _tracked(patterns: tuple[str, ...]) -> list[Path]:
    root = _root()
    out: list[Path] = []
    for pattern in patterns:
        result = subprocess.run(
            ["git", "ls-files", pattern],
            capture_output=True,
            text=True,
            cwd=root,
            check=False,
        )
        out.extend(root / line for line in result.stdout.splitlines() if line.strip())
    return sorted(set(out))


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _readers(name: str, sources: list[tuple[Path, str]]) -> tuple[list[str], str]:
    """Return modules that mention this config file, and how they were matched.

    A literal filename match is not enough.  `data/soi/form_counts_2023.yaml` is
    loaded as an f-string, `f"form_counts_{soi_year}.yaml"`, and via a
    `form_counts_*.yaml` glob, so the first version of this tool reported it as
    dead config.  When the exact name misses, fall back to the stem prefix and
    SAY SO, rather than printing a confident wrong answer.
    """
    def scan(needle: str) -> list[str]:
        return [
            str(path.relative_to(_root())).replace("\\", "/")
            for path, text in sources
            if needle in text
        ]

    hits = scan(name)
    if hits:
        return hits, "exact filename"
    stem = Path(name).stem
    segments = stem.split("_")
    while len(segments) > 1:
        segments.pop()
        prefix = "_".join(segments) + "_"
        hits = scan(prefix)
        if hits:
            return hits, f"prefix {prefix!r} (name is built at runtime)"
    return [], ""


def _summarize(path: Path) -> list[str]:
    """Describe a YAML file by its top-level keys and collection sizes."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - a broken file is still terrain
        return [f"UNREADABLE: {type(exc).__name__}"]
    if isinstance(data, list):
        return [f"(list of {len(data)})"]
    if not isinstance(data, dict):
        return ["(scalar)"]
    lines = []
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}: {len(value)} entries")
        elif isinstance(value, dict):
            lines.append(f"{key}: {len(value)} keys")
        else:
            lines.append(f"{key}: {value!r}"[:70])
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", help="show only files defining this top-level key")
    args = parser.parse_args()

    root = _root()
    code = []
    for path in _tracked(CODE_GLOBS):
        try:
            code.append((path, path.read_text(encoding="utf-8", errors="ignore")))
        except OSError:
            continue

    files = _tracked(AUTHORITATIVE_GLOBS)
    print(f"AUTHORITATIVE CONFIGURATION SURFACE - {len(files)} files")
    print("Derived on every run; nothing here is maintained by hand.\n")

    shown = 0
    for path in files:
        summary = _summarize(path)
        if args.key and not any(line.startswith(f"{args.key}:") for line in summary):
            continue
        shown += 1
        rel = str(path.relative_to(root)).replace("\\", "/")
        print(rel)
        for line in summary:
            print(f"    {line}")
        readers, how = _readers(path.name, code)
        if readers:
            print(f"    read by: {', '.join(readers[:6])}")
            if len(readers) > 6:
                print(f"             (+{len(readers) - 6} more)")
            if how != "exact filename":
                print(f"    matched: {how}")
        else:
            print("    read by: NO REFERENCE FOUND by name or prefix - check before assuming dead")
        print()

    if args.key and not shown:
        print(f"no authoritative file defines a top-level '{args.key}'", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
