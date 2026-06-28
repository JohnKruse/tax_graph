# PHASE M0 — Foundation: make the POC a runnable package   [ ]

**Canary:** Booted Badger
**Goal:** Convert the POC (engine + validator + capital-gains slice) into a `uv`-managed
`tax_graph` package with a CLI and green CI. Prerequisite for every other phase.

**Incorporates Codex review findings:** P1 (missing-input invariant — Step 3) and P2 (full
§10.3 graph validation — Step 2). The POC was happy-path; the *port* is where these get
hardened — do not copy the POC's gaps forward. (P3 = package shape = this whole phase.)

**Exit criteria (must pass 100%):**
- `uv run tax-graph validate 2025` succeeds.
- `uv run tax-graph run --facts examples/capital_gains_basic/facts.yaml` prints line 7 = 2000.
- Omitting a required input (e.g. 1099-B basis) reports it as missing and does **not**
  produce a fabricated line-7 value (P1 invariant test).
- The validator catches a duplicate id, a cycle, and a cross-year reference (P2 tests).
- `pytest -m m0` is green.
- CI is green on push.

## Steps

- [DONE] **Step 1 — Package + uv skeleton.** `pyproject.toml` (uv; deps: pyyaml, jsonschema,
  pytest, typer). Create `tax_graph/` (`__init__.py`, `config.py` stub, `io/loader.py`).
  Test: `uv run python -c "import tax_graph"`; `tests/test_smoke.py::test_import` (`@pytest.mark.m0`).
  Docs: README install/run section.
  - Verification: `python -c "import tax_graph; print(tax_graph.__version__)"`,
    `pytest -q -m m0`, `pytest -q`, and `python tools\validate_graph.py 2025` pass.
  - Deviation: `uv` is not installed in this environment, so the exact `uv run ...`
    smoke command could not be executed locally yet.

- [DONE] **Step 2 — Shared loader + port validator.** Implement `tax_graph/io/loader.py` (YAML
  load + the date-normalization that tames YAML implicit typing). Port the validator to
  `tax_graph/validate/graph_validator.py` and **harden it to the full §10.3 contract (review
  finding P2):**
    - **Duplicate IDs** — detect at *load time*, before any dict-keying collapses them (this
      bites the engine too, `engine.py` line ~48). A repeated node/edge/rule/citation id fails.
    - **Illegal cycles** — the dependency graph must be a DAG (no cycle unless an edge is
      explicitly marked as an allowed exception).
    - **Tax-year consistency** — a node's `document_id`, and the ids it references, resolve
      within the same tax year.
  Tests: existing integrity over `graph/2025` passes; a negative test for **each** new check
  (dup id, cycle, cross-year ref) is caught. Docs: docstrings.
  - Verification: `pytest -q -m m0`, `pytest -q`, and
    `python tools\validate_graph.py 2025` pass.

- [DONE] **Step 3 — Port engine + enforce the missing-input invariant (review finding P1).**
  Move the engine to `tax_graph/engine/` (engine + `operations.py` for COPY/SUM/SUBTRACT).
  **Do NOT coerce a missing required input to 0.** Behavior:
    - An input node marked `required` with no provided fact is `MISSING` (a sentinel, not 0).
    - `MISSING` **propagates**: any computation consuming a MISSING operand yields MISSING —
      never a fabricated number.
    - The engine **reports the list of missing required inputs** (the `list_required_inputs`
      capability) and leaves dependent outputs undetermined.
    - `include_blank_as_zero` applies only to *non-required* (optional/blank-allowed)
      operands — not to required inputs that weren't supplied.
  Tests: `tests/test_capital_gains_slice.py` still passes; **and** omitting 1099-B basis
  reports a missing required input and leaves Form 1040 line 7 undetermined — it must NOT
  compute 12000. Docs: docstrings.
  - Verification: `pytest -q -m m0`, `pytest -q`,
    `python tools\validate_graph.py 2025`, and
    `python engine\engine.py examples\capital_gains_basic\facts.yaml 2025` pass.

- [DONE] **Step 4 — CLI.** `tax_graph/cli.py` (typer) with `validate` and `run` subcommands.
  `config.py` loads `tax-graph.config.yaml` (precedence: value → keyring → env). Test: CLI
  smoke tests assert exit 0 and the expected line-7 value. Docs: CLI usage in README.
  - Verification: `pytest -q -m m0`, `pytest -q`,
    `python -m tax_graph.cli validate 2025`, and
    `python -m tax_graph.cli run --facts examples\capital_gains_basic\facts.yaml` pass.
  - Deviation: `uv` and Typer are not installed in this environment, so the local smoke
    used the module CLI fallback. The `tax-graph` console script and Typer dependency are
    declared in `pyproject.toml` for synced environments.

- [ ] **Step 5 — CI.** GitHub Actions: `uv sync` → `tax-graph validate` → `pytest`. Exit: CI
  green on push. Docs: CI note/badge in README.

When all steps are `[DONE]`: mark this phase `[COMPLETE]`, move it to `archive/`, and tell
John. The Architect will then generate `PHASE_M3.md` (Acquisition — canary *Thrifty Otter*).
