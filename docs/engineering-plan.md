# Tax Graph - Engineering Plan (pipeline build-out)

> **How to use this doc.** This is the vision + high-level plan. Each milestone is
> written to be **self-contained** so an implementer (e.g. Codex) can pick it up
> without the design conversation behind it: goal, scope, the interfaces/contracts,
> decisions already settled, and acceptance criteria. It deliberately does **not**
> prescribe every implementation detail - that's the implementer's job.

## What "API-based pipeline" means here

A **runnable Python package + CLI** that executes the build/run pipeline as commands
(and in CI) - *not* a bespoke effort driven turn-by-turn in a chat. The **AI-powered
stages (document extraction, citation discovery) are programmatic LLM API calls inside
the pipeline**, not a human-in-chat. It is **not** a hosted web service (the project is
local-first; the runtime interface is an MCP server over stdio). If a served HTTP API is
actually wanted, flag it - it changes M2.

## Guiding invariants (do not violate)

1. **Roadmap, not oracle.** Mechanical computation lives in the graph; classification/
   judgment stays *outside* it as input facts / decision nodes. The engine never
   improvises tax logic.
2. **Incomplete, but never wrong.** Missing inputs are reported; unsupported cases are
   marked explicitly; nothing is silently guessed.
3. **Deterministic core.** Given facts + graph, execution is reproducible and traceable.
   The LLM is used to *build* and *explain* the graph, never to *compute* a return.
4. **Local-first.** No taxpayer data leaves the machine via the project's own code; no
   hosted storage; secrets in the OS keyring, never committed.
5. **Repeatable & resumable.** Every stage is a re-runnable command. Within-filing state
   (tree, facts, trace) persists so a session survives model throttling.

## Current state (the POC - build on this, don't redo it)

| Exists | Path | Status |
|---|---|---|
| 8 JSON schemas | `schemas/*.schema.json` | v0, validating |
| Capital-gains graph slice | `graph/2025/` | 1099-B->8949->Schedule D->1040 L7 |
| Graph validator | `tools/validate_graph.py` | schema + Section 10.3 integrity |
| Execution engine (POC) | `engine/engine.py` | COPY/SUM/SUBTRACT + audit trace |
| First regression test | `tests/test_capital_gains_slice.py` | example-driven (facts/expected) |
| Design notes | `docs/return-record.md`, requirements doc | - |

The POC proved the thesis (computed 1040 L7 = $2,000 with a trace). M0 turns it into a package.

## Target architecture

```
tax_graph/                 # the package (consolidate the POC into here)
  cli.py                   # CLI entrypoint -> subcommands
  config.py                # paths, settings, secrets (keyring/env)
  models.py                # typed graph objects (pydantic/dataclasses)
  io/loader.py             # load + normalize YAML (shared; tame YAML dates)
  acquire/                 # manifest, HTTP fetch, hashing, change detection
  extract/                 # LLM-API extraction + citation discovery (generator/critic)
  validate/                # port of validate_graph.py
  compile/                 # YAML graph -> SQLite (+ FTS5)
  engine/                  # port of engine.py: traversal + ops + trace
  record/                  # Return Record builder (MD memo + carryforward block)
  mcp/                     # MCP stdio server
graph/ schemas/ examples/ tests/   # data + fixtures (mostly exist)
pyproject.toml             # uv-managed
```

**Pipeline (build-time):** `acquire -> store raw + hash -> detect change -> extract (LLM) ->
author/curate YAML -> validate -> compile -> ship SQLite`.
**Runtime:** MCP server reads the compiled SQLite; engine executes a return from facts and
emits values + audit trace + Return Record.

## CLI surface

| Command | Does |
|---|---|
| `tax-graph validate [--year]` | schema + integrity check (exists) |
| `tax-graph run --facts F [--year]` | execute a return -> values, trace, Return Record |
| `tax-graph build [--year]` | compile YAML graph -> `tax_graph_<year>.sqlite` |
| `tax-graph acquire [--year] [--check]` | fetch docs per manifest, hash, detect changes |
| `tax-graph extract --doc ID` | LLM-draft graph objects from an acquired doc (review-gated) |
| `tax-graph serve` | start the MCP stdio server |

---

## Milestones

### M0 - Foundation: make the POC a runnable package
- **Goal:** `uv`-managed package + CLI; CI green. The POC becomes operable, not chat-run.
- **Scope:** `pyproject.toml` (uv); create `tax_graph/`; port `engine/engine.py` ->
  `tax_graph/engine/` and `tools/validate_graph.py` -> `tax_graph/validate/`; shared
  `io/loader.py` (the date-normalization belongs here); wire `validate` + `run`
  subcommands; GitHub Actions (uv sync, `tax-graph validate`, `pytest`).
- **Decisions set:** package `tax_graph`, CLI `tax-graph`, deps pyyaml + jsonschema +
  pytest (+ a CLI lib - typer or argparse).
- **Acceptance:** `uv run tax-graph validate` and `uv run tax-graph run --facts
  examples/capital_gains_basic/facts.yaml` succeed; `pytest` passes; CI green on push.

### M1 - Compile to SQLite + runtime read path
- **Goal:** the shippable runtime artifact.
- **Scope:** `compile/to_sqlite.py` builds `tax_graph_<year>.sqlite` (tables for
  documents/nodes/edges/rules/citations/decisions; **FTS5** over IRS text + citation
  `quoted_text`). Engine gains a SQLite-backed loader behind the same interface as the
  YAML loader.
- **Acceptance:** `tax-graph build 2025` emits the DB; `run` against the DB yields
  byte-identical results to the YAML run; an FTS query returns the expected citation.

### M2 - MCP server (stdio)
- **Goal:** the runtime interface; usable from Claude Desktop.
- **Scope:** `mcp/server.py` using the official MCP Python SDK over stdio. Tools (req. doc
  Section 8.2): `get_document`, `get_node`, `get_dependencies`, `get_downstream_effects`,
  `execute_tax_tree`, `list_required_inputs`, `explain_calculation`, `get_citation`,
  `export_audit_file`. Server `instructions` block = the behavioral contract (never
  compute values yourself; never assert a rule without a citation; at a decision present
  options incl. escape hatch; mark unsupported rather than guess).
- **Acceptance:** Claude Desktop connects to a local build and walks the capital-gains
  branch end-to-end, returning the trace + citations.

### M3 - Source acquisition + change detection
- **Goal:** repeatable, manifest-driven document acquisition (replaces ad-hoc fetching).
- **Scope:** `acquire/manifest.py` (declarative: doc_id, year, canonical URL - IRS PDFs
  at `irs.gov/pub/irs-pdf/{f|i|p}NNNN.pdf`, prior years under `irs-prior/`); `fetch.py`
  (HTTP via httpx, polite/rate-limited, stores raw artifact + `content_hash` + revision
  date); `changes.py` (diff vs prior manifest -> changed-docs report). **Plain HTTP, not a
  browser crawler** - only reach for Playwright if a needed index page is JS-rendered.
  Add citation-integrity: stored `quoted_text` must still appear in the fetched source.
- **Acceptance:** `tax-graph acquire 2025` fetches the 4 slice docs, stores raw + hashes;
  `--check` reports changed vs last run; citation-integrity flags a doctored quote.

### M4 - API-based extraction (the AI stage)
- **Goal:** turn acquired document text into **draft** graph objects via LLM API calls.
- **Scope:** `extract/llm_extractor.py` calls the **Anthropic API** (current Claude
  flagship - confirm model id at build time) with **structured outputs constrained to the
  schemas + the closed op vocabulary**. Pattern: **generator** proposes nodes/edges/rules/
  citations with quoted source spans + confidence; an independent **critic** re-derives and
  diffs; disagreement/low-confidence/uncovered -> flagged. Output is a **draft PR for human
  review - never auto-merged** (governance Section 13). `extract/citations.py` discovers candidate
  citations (FTS over acquired text) and verifies verbatim quotes.
- **Decisions set:** provider = Anthropic/Claude default (keyless paths are the *consumer*
  story; this *build* stage uses an API key in the OS keyring). LLM never computes values.
- **Acceptance:** for a held-out form's instructions, produces schema-valid draft YAML with
  provenance + confidence; a human diff against a hand-authored reference shows the method
  is sound; nothing lands without review.

### M5 - Return Record + carryforward output
- **Goal:** the cross-year memory artifact (see `docs/return-record.md`).
- **Scope:** `record/return_record.py` emits, at end of a `run`, the **dual-format** Return
  Record: human-readable MD memo (decisions + *why* + quoted citations) **plus** a
  structured carryforward block validated against `carryforward.schema.json`. Next year's
  `run` can ingest a prior block as input facts.
- **Acceptance:** `tax-graph run` writes a Return Record; a net-capital-loss scenario emits
  a schema-valid capital-loss carryforward; re-ingesting it next year primes the input.

### M6 - Differential-testing harness
- **Goal:** confidence via cross-implementation agreement (no single IRS answer key exists).
- **Scope:** adapters wrapping **OpenTaxSolver** (box-level) and **PolicyEngine-US /
  Tax-Calculator** (liability-level) as oracles; run shared scenarios through Tax Graph + an
  oracle; report diffs. Seed the **IRS Example Regression Suite** (facts/expected pattern,
  already started in `examples/`).
- **Acceptance:** a scenario runs through Tax Graph and >=1 OSS oracle with matching key
  values; a deliberate graph bug is caught by the diff.

---

## Configuration - one-stop tuning

All tunables live in **`tax-graph.config.yaml`** (gitignored; copy from
`config/tax-graph.config.example.yaml`) - the single place to change prompts, model/
provider, **API keys**, paths, rate limits, and thresholds **without touching code**. Loaded
by `tax_graph/config.py`. **Secret resolution order: explicit config value -> OS keyring ->
environment variable** (keys fail back to env vars; real secrets never committed). Prompts
live in `prompts/*.md`, referenced from the config so they're tuned in one place. Sections:
`project` (years, paths), `llm` (provider, model, key/key_env/keyring), `extraction`
(confidence thresholds, critic toggle, prompt paths), `acquire`, `oracles`, `logging`.

## Phase gates & canaries

Each phase carries a humorous 2-word **canary** the Worker must state before starting (proves
it read the subplan) and an **exit-criteria** command that must pass 100%. Global project
canary: **Ledger Llama**.

| Phase (exec order) | Canary | Exit criteria |
|---|---|---|
| M0 Foundation | Booted Badger | `tax-graph validate` + `tax-graph run` ok; `pytest -m m0`; CI green |
| M3 Acquisition | Thrifty Otter | `pytest -m m3` (fetch + change-detect + citation-integrity) |
| M4 Extraction | Spectral Auditor | `pytest -m m4` (schema-valid, review-gated draft for a held-out form) |
| M1 Compile | Crystalline Ledger | `pytest -m m1` (SQLite run == YAML run) |
| M2 MCP server | Polite Robot | `pytest -m m2` + manual Claude Desktop walk-through |
| M5 Return Record | Future Echo | `pytest -m m5` (record + carryforward round-trip) |
| M6 Differential | Twin Witness | `pytest -m m6` (Tax Graph == an OSS oracle) |

## Working protocol (Architect / Worker)

Adapted from John's multi-agent protocol (filesystem state to resist context degradation):
- **ASCII-only files (no Unicode):** all operational/planning/docs/data files use plain ASCII
  ("-" not em dashes, "->" not arrows, "Section" not the section sign, straight quotes, ASCII
  diagrams). Unicode breaks PowerShell/patching/handoffs. `tools/check_ascii.py` enforces it in CI.
- **Architect (Claude Opus):** plans only, no implementation code. Master plan = this doc;
  per-phase detail in `plans/PHASE_<id>.md`, generated **serially, one phase at a time**.
- **Worker (Codex/Sonnet/Gemini):** implements an entire phase, step by step, from `plans/`.
  Full directive in `plans/README.md`.
- **Every step MUST:** implement core logic + create/update pytest (reuse, don't proliferate)
  + update docstrings/docs. Not done until tests pass 100%.
- **Worker run (whole phase):** state the phase canary & await confirmation, then work the steps
  in order WITHOUT stopping between them. Each step = implement+test+docs -> green -> mark
  `[DONE]` + log deviations -> **git commit** (one per step, no push yet). Stop and surface to
  John only on a problem (tests stuck, real ambiguity, plan-changing deviation, low context).
  At phase end: run the exit-criteria command, mark `[COMPLETE]`, archive the subplan, then
  **git push once** and report. Check context % at the start.

## Cross-cutting

- **Config & secrets:** `config.py`; API keys via OS keyring or env, never committed;
  spending-cap guidance documented.
- **Testing:** see **`docs/testing-strategy.md`** (hard guardrails). pytest, phase-tagged;
  every step updates tests + docs; a branch isn't `supported` without a passing example +
  citations + (where an oracle exists) a differential test.
- **CI:** GitHub Actions - validate + pytest on every push (extraction/oracle jobs gated/
  optional since they need keys/network).
- **Packaging/distribution:** single per-OS binary later (PyInstaller); `uvx`/PyPI for
  early adopters. (Client/onboarding story is separate - see memory.)
- **Invariants in code:** engine reports missing required inputs and marked-unsupported
  cases rather than guessing; decisions always expose an escape hatch.

## Deferred (explicitly not now)
Capital-loss carryover *computation* (structure only); Form 1116 and the rest of the form
set (build after the pipeline is solid; 1116 last); full prompt library + agent-behavior
evals; web service.

## Sequencing (decided) & remaining confirmations

**Automation-first** (John's call - get out of hand-authoring ASAP):
**M0 -> M3 -> M4 -> M1 -> M2 -> M5 -> M6.** M0 is the prerequisite; then acquisition (M3) + LLM
extraction (M4) replace hand-authoring with reviewed draft generation. The engine already
runs on YAML, so extracted + validated graphs are testable *before* the SQLite/MCP runtime
(M1->M2). Return Record (M5) and differential testing (M6) close it out.

Still assumed (flag if wrong): "API-based" = CLI/package with LLM-API stages, **not** a served
web API; CLI lib = **typer**; package name = `tax_graph`.
