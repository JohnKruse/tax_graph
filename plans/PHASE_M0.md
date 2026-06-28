# PHASE M0 — Foundation: make the POC a runnable package   [ ]

**Canary:** Booted Badger
**Goal:** Convert the POC (engine + validator + capital-gains slice) into a `uv`-managed
`tax_graph` package with a CLI and green CI. Prerequisite for every other phase.

**Exit criteria (must pass 100%):**
- `uv run tax-graph validate 2025` succeeds.
- `uv run tax-graph run --facts examples/capital_gains_basic/facts.yaml` prints line 7 = 2000.
- `pytest -m m0` is green.
- CI is green on push.

## Steps

- [ ] **Step 1 — Package + uv skeleton.** `pyproject.toml` (uv; deps: pyyaml, jsonschema,
  pytest, typer). Create `tax_graph/` (`__init__.py`, `config.py` stub, `io/loader.py`).
  Test: `uv run python -c "import tax_graph"`; `tests/test_smoke.py::test_import` (`@pytest.mark.m0`).
  Docs: README install/run section.

- [ ] **Step 2 — Shared loader + port validator.** Implement `tax_graph/io/loader.py` (YAML
  load + the date-normalization that tames YAML implicit typing). Port the validator to
  `tax_graph/validate/graph_validator.py`. Test: integrity test over `graph/2025` passes,
  plus a negative test (a deliberately broken ref is caught). Docs: docstrings.

- [ ] **Step 3 — Port engine.** Move the engine to `tax_graph/engine/` (engine +
  `operations.py` for COPY/SUM/SUBTRACT). Test: `tests/test_capital_gains_slice.py` passes
  against the package import path. Docs: docstrings.

- [ ] **Step 4 — CLI.** `tax_graph/cli.py` (typer) with `validate` and `run` subcommands.
  `config.py` loads `tax-graph.config.yaml` (precedence: value → keyring → env). Test: CLI
  smoke tests assert exit 0 and the expected line-7 value. Docs: CLI usage in README.

- [ ] **Step 5 — CI.** GitHub Actions: `uv sync` → `tax-graph validate` → `pytest`. Exit: CI
  green on push. Docs: CI note/badge in README.

When all steps are `[DONE]`: mark this phase `[COMPLETE]`, move it to `archive/`, and tell
John. The Architect will then generate `PHASE_M3.md` (Acquisition — canary *Thrifty Otter*).
