# PHASE M1 - Compile to SQLite + light runtime   [ ]

**Canary:** Crystalline Ledger
**Depends on:** M0 (package, `io/loader.py`, `engine/`, `validate/`, schemas, `config.py`).
Independent of M3/M4 (compile + runtime build on the authored graph, not on acquisition).
**Goal:** Produce the **shippable runtime**: compile the authored YAML graph to a SQLite artifact
(with FTS5), make the engine read it, and make the **end-user runtime light** - a base install
pulls NO build-time deps. This is what lets a user run Tax Graph from a small artifact without the
maintainer toolchain.

## Why (the packaging gap)
Base `pyproject.toml` `dependencies` currently include **build-time-only** deps: `pymupdf` (form
renderer), `mistralai` (OCR), `httpx` (fetch). A runtime user querying a prebuilt graph needs none
of them. Split them into extras and ship the compiled SQLite so the runtime stays tiny (SQLite is
stdlib; the engine is pure Python).

## Exit criteria (must pass 100%)
- `pytest -m m1` is green (deterministic).
- `uv run tax-graph build 2025` writes `<build_dir>/tax_graph_2025.sqlite`.
- `tax-graph run` against the SQLite yields IDENTICAL computed values + audit trace to the YAML
  run (the `capital_gains_basic` example: Form 1040 line 7 = 2000).
- A **base-only install** (no `[acquire]`/`[extract]` extras) can `build`, `validate`, and `run`,
  and a runtime command does NOT import `pymupdf` or `mistralai`.
- CI green across a Python matrix (3.11 / 3.12 / 3.13).

## Guardrails (do not drift)
- **Runtime base = minimal** (`pyyaml`, `jsonschema`, `typer`; `mcp` is added in M2). Build-time
  deps live in extras: `[acquire]` (httpx, pymupdf, mistralai), `[extract]` (the LLM extras),
  `[build]` = acquire + extract, `[dev]` = pytest + build.
- **Lazy imports.** Heavy modules import inside the CLI `acquire`/`extract` handlers (the renderers
  already do lazy `import fitz`), so `run`/`validate`/`build`/`serve` never import pymupdf/mistralai.
- **YAML stays the source of truth** (authored, validated, git-diffable). SQLite is the
  deterministic COMPILED artifact - rebuild from YAML anytime.
- **Do NOT commit the binary `.sqlite`** (keep `build/` gitignored); a release/binary bundles it.
- **One graph-loader interface.** SQLite-backed and YAML-backed loaders sit behind the same
  interface the engine's `Graph` already uses, so the engine is source-agnostic.
- **Table-aware SEAM (do not foreclose).** A later milestone (M6b) adds repeatable-table objects and
  optional node `table_id`/`column`/`role` fields. Keep the compiler GENERIC over object kinds and
  the compiled `nodes` row ADDITIVE, so that promotion lands as a data change, not a schema-break. Do
  NOT flatten repeatable tables to scalars, hardcode a closed node shape, or assume a flat-scalar-only
  node set. SQLite is a rebuildable projection of YAML, so this costs nothing now. Single-lot parity
  (line 7 = 2000) is unchanged. Full policy: engineering-plan "Repeatable tables (decided)".
- **ASCII-only.**

## Steps

- [DONE] **Step 1 - Runtime/build dependency split + lazy imports (the packaging fix).** In
  `pyproject.toml`, move build-time deps out of base into extras: base = `pyyaml`, `jsonschema`,
  `typer`; `[acquire]` = `httpx`, `pymupdf`, `mistralai`; `[extract]` = the existing LLM extras;
  `[build]` = acquire + extract; `[dev]` = pytest + build. Lazy-import the heavy modules inside the
  CLI's `acquire`/`extract` command handlers so `run`/`validate`/`build` never import pymupdf or
  mistralai. Commit `uv.lock`; add a CI Python matrix (3.11/3.12/3.13). Test: in a base-only
  install, `tax-graph run --facts examples/capital_gains_basic/facts.yaml` and
  `tax-graph validate 2025` succeed, and a guard asserts `fitz`/`mistralai` are NOT in
  `sys.modules` after a runtime command. Docs.
  - Verification: `uv run pytest -m m1`, `uv run tax-graph validate 2025`,
    `uv run tax-graph run --facts examples\capital_gains_basic\facts.yaml`, `uv run pytest`, and
    `uv run python tools\check_ascii.py` pass. Local `uv run pytest` is base-only and skips the
    PyMuPDF render test as expected; CI installs `--extra dev` for build extras.

- [DONE] **Step 2 - YAML -> SQLite compiler (+ FTS5).** `tax_graph/compile/to_sqlite.py`: load the
  authored graph via `io/loader.py` and write `<build_dir>/tax_graph_<year>.sqlite` with tables for
  documents/nodes/edges/rules/citations/decisions (mirroring the schemas) plus an FTS5 index over
  citation `quoted_text` and node labels. Deterministic (stable ordering). Wire
  `tax-graph build [--year]`. Test: build `2025`; per-kind row counts equal the YAML object counts;
  an FTS query for a known phrase returns the expected `citation_id`. Base deps only. Docs.
  - Verification: `uv run tax-graph build 2025` writes `build/tax_graph_2025.sqlite`; SQLite
    metadata reports tax year 2025; FTS for `Subtract` returns `cite_8949_col_h_gain`;
    `uv run pytest -m m1`, `uv run pytest`, and `uv run python tools\check_ascii.py` pass.

- [ ] **Step 3 - SQLite-backed runtime loader (source-agnostic engine).** Add a SQLite-backed graph
  loader behind the SAME interface the engine's `Graph` uses today (nodes / rules / incoming edges),
  so the engine runs from either source. `tax-graph run` gains `--source sqlite|yaml` (default
  sqlite when a build exists, else yaml). Test: PARITY - running `capital_gains_basic` from the
  compiled SQLite yields IDENTICAL computed values AND the same audit trace as the YAML run
  (line 7 = 2000). Docs.

- [ ] **Step 4 - Shippable artifact + light-runtime gate.** Confirm the `build_dir` SQLite is the
  runtime artifact and that a base-only environment (no `[acquire]`/`[extract]`) can `build` and
  `run` against it end to end. Update the README with the two install paths: `pip install tax-graph`
  (light runtime) vs `pip install tax-graph[build]` (maintainer pipeline), and note the eventual
  single-binary path bundles the runtime + prebuilt SQLite (no Python needed for end users). Test: a
  base-only CI job runs `tax-graph build 2025 && tax-graph run --facts examples/capital_gains_basic/
  facts.yaml --source sqlite` green. Exit: `pytest -m m1` green. Docs.

When all steps are `[DONE]`: mark this phase `[COMPLETE]`, move it to `plans/archive/`, and tell
John. The Architect will then generate `PHASE_M2.md` (MCP server over stdio - canary *Polite Robot*),
per the order M0 -> M3 -> M4 -> M1 -> M2 -> M5 -> M6.
