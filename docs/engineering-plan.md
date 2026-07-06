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

## Repeatable tables (decided 2026-07-01)

Form 8949 forces a policy for repeatable transaction tables before M1/M2 harden the runtime
contracts (Codex raised it; John set the aggregate-subunit rule). Four things that look alike must
stay distinct:

- **(a) IRS line anchor** - the citeable form address, e.g. Part I line 1. Stable across taxpayers.
  It names the TABLE.
- **(b) Row-template columns + per-row rule** - the graph logic that applies to every row: columns
  (d) proceeds, (e) cost, (g) adjustment as inputs; (h) = (d) - (e) + (g) as the per-row computed
  column (already realized as chained single-op computed nodes, PHASE_M4 pinned decision 1). These
  are TEMPLATES, not instances.
- **(c) Physical printed row slots** - the blank rows the form prints (review labels line 1.01 ..
  line 1.11). Page GEOMETRY only; a 3-transaction return uses 3 slots, a 500-transaction return uses
  an attached statement. Never enters node ids, the runtime graph, or facts - it lives only in
  acquisition/review artifacts and (later) the form filler.
- **(d) Taxpayer fact instances** - the actual N transactions, which may exceed printed slots.
  RUNTIME data, not graph structure.

Decided representation:

1. **A repeatable table is ONE aggregate subunit, not loose sibling lines** (John's rule). It groups
   its row-template columns (line 1) with its totals row (line 2) as a single addressable unit that a
   parser/renderer/engine treats atomically. Additive schema (authored at M6b, not now): a `tables`
   object kind, plus optional `table_id` / `column` / `role in {row_template, total}` on member nodes.
2. **Static ids stay flat and template-level.** table id = the line anchor
   `form_8949_2025_part_i_line_1`; columns = `..._column_d` (already what M4 extraction emits);
   totals = `..._line_2_column_d_total`. No instance ever appears in a static node id.
3. **Instances live only at runtime, in a SEPARATE namespace.** A fact supplies rows against a table
   id, each row carrying a `row_key` (a runtime id - the broker transaction id or a synthesized
   `r0001`), explicitly divorced from physical slots (c). The engine evaluates the row-template rule
   per instance and the totals row aggregates across instances. In the trace / MCP an instance is
   addressed `<column_node_id>#<row_key>`; `#` is DISALLOWED by the node_id pattern `^[a-z0-9_]+$`,
   so a runtime instance id can never collide with a static graph id - the schema itself enforces the
   static/runtime boundary.
4. **The trigger is DETERMINISTIC and dual-signal - not an LLM judgment call** (John's call: nail it
   deterministically). A section becomes an aggregating table subunit only when BOTH hold: (i)
   GEOMETRY - the M3 field grid (`.fields.json` `x_cluster`/`y_cluster`) shows the same column
   x-clusters repeated across >=2 y-row bands under one IRS line anchor (a repeated row-band, not a
   single line); and (ii) TOTALS CUE - a following line in the same section carries an explicit
   aggregation instruction naming its columns (e.g. "Add the amounts in columns (d), (e), (g), and
   (h)") or a geometrically-aligned totals row directly under the band. The outline pass already
   emits these as `kind: transaction_table` + `kind: totals`, so that IS the trigger; assembly groups
   the line-1 rows + line-2 totals into one subunit and takes the SUM columns from the totals cue (the
   per-row (h) formula comes from the column header, PHASE_M4 pinned decision 1). A cross-check
   reconciles the totals' SUM columns against the field-grid columns and the cue; on mismatch, or a
   table with no resolvable totals, FLAG for human review - never emit a guessed aggregation. Row
   COUNT is never inferred at parse time (that is runtime fact (d)). No LLM call and no second
   document fetch are needed to fire the trigger.

This is scheduled as **M6b** (below). Until then the single-lot v0 slice (one instance; totals ==
that instance) is a legitimate supported case and stays as authored.

## Parameters and thresholds (decided 2026-07-05)

Reading OTS's 1040 C solver (John's find) shows what a full form ruleset carries besides
operations: standard-deduction amounts by filing status, bracket boundary/rate tables, the
qualified-dividends worksheet breakpoints (0/15/20 percent), Social Security taxability
thresholds, AMT exemption + phaseout amounts, caps and floors (capital-loss $3000/$1500, SALT
limit), and phase-out ranges. In OTS these are hardcoded C constants. In OUR graph they must be
first-class, or the "roadmap for AI" thesis fails at exactly the numbers that matter:

1. **A parameter is a NODE, never an inline magic number.** Additive schema: a `parameter`
   node_type (year-specific value + citation). Most parameters vary by filing status, so a
   parameter carries keyed values consumed via `LOOKUP_TABLE`/`LOOKUP_BRACKET` (exact
   representation - one node with keyed values vs per-status nodes - is a phase-plan decision;
   the PRINCIPLE is pinned). Rules reach parameters through edges, like any other input.
2. **No-magic-numbers guardrail (drill-enforced under M8):** a numeric literal inside
   `rule.parameters` that is not purely structural (e.g. a rounding increment) is a validator
   flag. If a number came from the IRS, it must be a cited parameter node.
3. **Every parameter is individually cited.** The values live in the instructions/worksheets
   and the annual inflation-adjustment revenue procedure; extraction targets them like any
   other cited object. This makes year-over-year re-extraction sharp: inflation updates are
   parameter-only diffs.
4. **Bulk tables are DATA, not nodes.** The under-$100k tax table (hundreds of rows) compiles
   to a data resource referenced by a `LOOKUP_TABLE` rule, with provenance - not per-row nodes.
5. **Parameter-level differential (new cheap oracle channel; see `docs/oracle-strategy.md`):**
   PolicyEngine-US publishes its parameters as declarative YAML with values-by-date and
   references - a DIRECT structured oracle for exactly these numbers; OTS's C constants are
   mechanically minable as a second witness. Diffing our extracted parameter values against
   both catches wrong-threshold extraction directly, without executing anything.

The closed op vocabulary already covers the mechanics (`LOOKUP_BRACKET`, `IF/IF_ELSE`,
`COMPARE`, `MIN/MAX`, ...) and `worksheet_field` nodes already exist - no vocabulary change.
The engine implements ops as branches need them (it has COPY/SUM/SUBTRACT today; the first
worksheet branch brings the rest). First live parameter when Schedule D is extracted: the
capital-loss limit ($3000 / $1500 MFS) on line 21.

Seams every phase before M6b must respect:
- **M1 (compile):** SQLite is a rebuildable projection of YAML, so adding the table representation
  later is a data change, not a migration. Keep the compiler generic over object kinds and the
  `nodes` row additive; do not assume a flat-scalar-only node set. Single-lot parity (line 7 = 2000)
  is unchanged.
- **M2 (MCP):** adopt this addressing convention from day one - `get_node` / `get_dependencies` /
  `explain_calculation` speak table + column + optional `#row_key` instance - so the client-facing
  contract needs no breaking change when M6b lands.
- **Do NOT promote `graph/2025/_drafts/form_8949_2025/` into the live graph before M6b.** Those
  per-column nodes are correct as templates but would land as loose siblings without the table
  subunit; they stay in `_drafts/` (gitignored) until M6b defines the grouping.

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
- **Scale half (added 2026-07-05; design canonical in `docs/oracle-strategy.md`):** OTS has
  no declarative ruleset to diff against - its logic is imperative C - but its line-labeled
  input/output maps 1:1 to IRS line numbers (our node spine), so the scalable channel is
  EXECUTION at volume: per-form domain profiles -> seeded property-based scenario generator
  -> box-level diff via a drill-tested `box_map.yaml` -> disagreement triage (neither side
  presumed right) -> agreed pairs FROZEN into `examples/` fixtures replayed offline in base
  CI (no oracle installed). Oracle builds, GPL source, generator, and the frozen-corpus
  releases live in a separate **oracle corpus factory repo** created at M6 start (fork OTS
  only if a patch proves necessary). No IRS enrollment ever - MeF ATS certifies e-file
  transmission acceptance, not arithmetic; public ATS scenario PDFs and the MeF schema line
  inventory are used as downloaded data only. Optional time-boxed experiment: statically
  mine OTS's per-line C patterns into a line-dependency graph and diff its shape against
  our edges (flag-only, never load-bearing).

### M6b - Repeatable-table execution (row instances)
- **Goal:** make repeatable transaction tables real end to end - N fact instances -> per-row
  compute -> totals aggregation -> trace - and promote Form 8949 from `_drafts` into the live graph
  as table subunits. Turns the "single covered lot" v0 simplification into arbitrary-N support.
- **Scope:** additive schema (`tables` object kind + node `table_id`/`column`/`role`); a compiler +
  loader pass-through for the new kind/fields; a **deterministic table-detector + column-reconciler**
  (repeated field-grid row-band AND a totals cue -> group as one subunit; mismatch/absent -> review
  flag) that decides WHEN to aggregate; `taxpayer_facts` gains per-table row instances (`row_key` +
  column values); the engine evaluates the row-template rule per instance and aggregates the totals
  row across instances, with per-instance trace addressed `<column_node>#<row_key>`; promote
  `form_8949_2025` Part I/II as table subunits (line 1 rows + line 2 totals). Physical printed slots
  stay OUT (acquisition/review geometry only).
- **Decisions set:** see "Repeatable tables (decided)". Static ids are template-level; instances are
  runtime-only in the `#row_key` namespace; a table is one aggregate subunit (rows + totals).
- **Acceptance:** a multi-transaction 8949 scenario (e.g. 3 lots, mixed gain/loss) computes the
  correct Part totals and 1040 line 7 with a per-instance trace; the deterministic detector groups
  8949 line 1 + line 2 into one subunit from geometry + the totals cue, and a mismatched/absent
  totals cue is FLAGGED, not guessed; the single-lot example still yields line 7 = 2000 (no
  regression); `pytest -m m6b` green.

### M8 - Extraction verification at scale (the trust ladder)
- **Goal:** make extraction accuracy verifiable WITHOUT a hand-authored reference and
  WITHOUT humans re-deriving forms - the held-out-diff method used to close M4 does not
  scale past the canary form. Full design: **`docs/extraction-verification.md`**.
- **Scope (summary; the design doc is canonical):**
  1. **Seeded-defect drills** - mutation-test the check net itself against a defect
     catalog (swapped SUBTRACT roles, dropped addend, off-by-one flow target, phantom
     node, ...); the net must catch 100% of cataloged classes and name the catching
     layer; every later real-world escape joins the catalog.
  2. **Both-direction structural ground truth** - every entry field in the AcroForm grid
     maps to a node or an explicit not-modeled record; optional MeF e-file schema line
     inventory as a second authoritative box-mapping oracle (worker pins availability).
  3. **Property tests from op semantics** - engine-executed algebraic checks generated
     in code per extracted rule (SUM permutation, SUBTRACT antisymmetry, metamorphic
     column (h) relations); offline, no LLM.
  4. **IRS worked-example miner** - extract instruction "Example." blocks into candidate
     facts/expected fixtures, execute through the extracted graph, human-confirm in
     minutes, FREEZE into `examples/` as regression tests. The authoritative numeric
     answer key, per form, from the same source doc.
  5. **N-version extraction** - re-run micro-extractions with a second (cross-VENDOR)
     model via the provider-agnostic seam; diff assembled canonical objects; agreement
     corroborates, disagreement routes to a cheap A/B human decision.
  6. **Trust tiers + metrics + year-over-year delta mode** - T1 structural / T2
     corroborated / T3 behavioral; promotion rule (rules/edges need T3); per-run
     `metrics.yaml` (human minutes per promoted object, escape rate); year N+1 verifies
     as a diff against year N's promoted graph.
- **Decisions set:** confidence scores are telemetry, never load-bearing (drill-enforced);
  humans review exceptions + a calibration sample, never whole forms; decisions (the
  object kind) always get human eyes. Proposed defaults for John: 10% calibration sample
  (min 5), N=2 vendors, 100% drill bar before extracting beyond the capital-gains set.
- **Acceptance:** `pytest -m m8` green (drills catch 100% of the catalog, offline); a
  seeded swapped-role defect on the known-good slice is caught and attributed; a mined
  8949/Schedule D example executes to the IRS-published number; `tax-graph verify report`
  prints tier distribution + human-minutes + escape-rate lines.

### M9 - Schedule D expansion + LINK + Verification Record
- **Goal:** the first data-driven form expansion, chosen by M7's weighted worklist (every
  frontier entry points at Schedule D, ~24M returns each). Full plan: `plans/PHASE_M9.md`
  (canary Daisy Chain).
- **Scope (summary):** acquire/render the Schedule D bundle (never rendered - only 8949 was);
  extract it under the complete M8 net (first form with the ladder in place from day one;
  first REAL human-minutes/escape data recorded in metrics); introduce the project's FIRST
  `parameter` nodes (the $3000/$1500 capital-loss limit, line 21 - the "Parameters and
  thresholds (decided)" policy goes live, with the no-magic-numbers flag enforced);
  human-gated promotion replacing the hand-authored Schedule D slice; the long-deferred
  **LINK step** realizes the 8949 outbound-flow declarations into real edges against the
  promoted node index (PHASE_M4 pinned decision 6), flipping frontier entries
  `declared -> modeled` and raising the coverage metric; the oracle harness widens
  (short-term lots; losses past $3000 become IN-domain via line 21); and the user-facing
  **Form Verification Record** ships (`VERIFICATION.md` + generated per-form pages + MCP
  exposure - design pinned in `docs/extraction-verification.md` Section 10).
- **Decisions set:** out-of-scope Schedule D branches (28%-rate and 1250 worksheets, tax
  computation, carryover worksheet, passthrough lines) are explicit frontier entries with
  `unresolved` engine traces - stated in the Verification Record, never guessed.
- **Acceptance:** see PHASE_M9 exit criteria - promoted graph green with parity (2000/250)
  unchanged; LINK edges realized; frontier coverage rises; >=100 widened-domain fuzz
  scenarios agree with OTS; line 21 computes -3000/-1500 through cited parameter nodes;
  committed byte-stable VERIFICATION.md; `pytest -m m9` green.

### M10 - Batch expansion across the OTS-witnessed set (pinned 2026-07-06; plan just-in-time)
- **M9 is the LAST bespoke single-form phase** (John's call). It exists to land the six
  form-agnostic capabilities batch expansion depends on: LINK, parameter nodes + comparison
  ops, a second acquire/OCR run, the Verification Record generator, and the box-map/domain
  growth mechanics - and to measure the true per-form human cost (M9 Step 2 metrics).
- **M10 then runs the pipeline as a BATCH** over the full OTS-witnessed set: grow the
  manifest to the schedules the pinned OTS 1040 solver computes (its metadata fence list:
  Schedules 1, 1-A, 2, 3, A, B, D/8949, Form 6251), acquire/extract/verify them together,
  LINK as promotions land, box maps seeded from the OTS label inventory, human effort
  limited to exception queues + calibration samples + promotion gates. Frontier ordering
  still sequences the PROMOTIONS (dependencies matter even when extraction is parallel).
  Worksheet-heavy branches (QDCGT/tax computation, AMT math) may remain frontier entries
  within otherwise-modeled forms - "incomplete, but never wrong" applies per branch, and
  the Verification Record states each form's actual depth. `PHASE_M10.md` is written
  just-in-time when M9 closes, informed by M9's measured per-form economics.

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
| M6b Repeatable tables | Tandem Abacus | `pytest -m m6b` (multi-row totals + single-lot parity) |
| M7 Frontier/Coverage | Compass Rose | `pytest -m m7` (frontier registry + SOI weights + coverage %) |
| M8 Verification ladder | Skeptical Notary | `pytest -m m8` (drill catalog 100% caught + example fixtures execute) |
| M9 Schedule D + LINK + Verification Record | Daisy Chain | `pytest -m m9` (promoted Sched D + realized LINK edges + coverage rise + committed VERIFICATION.md) |

## Working protocol (Architect / Worker)

Canonical roles, the Worker directive, and the hard rules now live in **`AGENTS.md`** (repo root) -
see there. The phase gates and canaries above are plan-specific.

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

**Reserved - Coverage Map + form front-matter (final-polish "icing", post-MVP).** A user-facing
visual map of what Tax Graph covers: forms as nodes (number + official title), FEEDS edges between
them, colored by status (modeled / declared-frontier / not-modeled) and sized by SOI weight, so a
user sees - before investing - whether their situation is in scope or leads to a brick wall. Nodes
carry the IRS "Purpose of Form" and "Who Must File" text (lifted VERBATIM + cited, never our own
summary) shown on hover/click; even unmodeled nodes carry title + purpose so the wall is a signpost,
not a dead end. The map is GENERATED from the graph + frontier registry (no hand-authoring, no API
key, deterministic SVG; interactive HTML as a fast-follow). Depends on the frontier/coverage policy
(frontier registry + SOI-weighted priorities - still being finalized).

**Reserved seams (do NOT preclude while building now):**
- **Document schema stays additive** - leave room for optional `title`, `purpose`, `who_must_file`
  on a document, each stored as a verbatim citation (quoted_text + locator + URL), populated later.
- **Never discard form front-matter** - renderers/extraction keep the form title line and the
  instruction "Purpose of Form" / "Who Must File" / "What's New" sections in the rendered text
  (today's full-text OCR + form render already do; just do not add a filter that strips them).
- **Allow a light front-matter-only acquisition tier** - capturing a form's title + purpose must NOT
  require fully modeling it (tiered coverage: catalog -> purpose -> modeled; effort by SOI weight).
- **Coverage data is a projection** - the frontier registry should carry per-form id, status, weight,
  edges, and (when present) title/purpose, so a map renders from data with no extra source.

## Sequencing (decided) & remaining confirmations

**Automation-first** (John's call - get out of hand-authoring ASAP):
**M0 -> M3 -> M4 -> M1 -> M2 -> M5 -> M6 -> M6b.** M0 is the prerequisite; then acquisition (M3) + LLM
extraction (M4) replace hand-authoring with reviewed draft generation. The engine already
runs on YAML, so extracted + validated graphs are testable *before* the SQLite/MCP runtime
(M1->M2). Return Record (M5) and differential testing (M6) close out the core pipeline;
repeatable-table execution (M6b) is a follow-on that makes the slice arbitrary-N and differentially
tests a realistic multi-row return.

**M7 (Frontier/Coverage)** slots in after the core pipeline (post-M2; can run alongside M5/M6). It
turns the graph's incompleteness into a derived, SOI-weighted, queryable registry - the data
foundation for the deferred Coverage Map and the backing for the cross-form LINK step (PHASE_M4
pinned decision 6). Its outbound-flow half may be pulled earlier if multi-form extraction lands
first. Plan: `plans/PHASE_M7.md`.

**M8 (Verification ladder)** is the gate between "extraction works on the canary form" and
"extraction scales to the form set": the held-out human diff that closed M4 required a
hand-authored reference and cannot verify the next form. M8's offline steps (drills,
both-direction field completeness, property tests) have no M5/M6 dependency and may be pulled
forward any time; the example miner and N-version steps complete the ladder; M6 supplies the
differential layer. **Hard sequencing rule: no bulk extraction beyond the capital-gains form
set until the M8 drill gate passes.** Design: `docs/extraction-verification.md`; subplan
`PHASE_M8.md` written just-in-time.

**M6b (Repeatable tables)** is a follow-on to M6, not on the critical path to a first working+tested
pipeline (single-lot proves M1/M2/M5/M6). It is the ONE place the scalar-per-node v0 becomes
arbitrary-N: facts row instances + per-row engine execution + totals aggregation, plus the gated
promotion of the Form 8949 draft into a live table subunit. M6 builds the differential harness
(provable on single-lot + a deliberate bug); M6b then makes multi-row real and differentially tests a
realistic multi-transaction return. Its representation and addressing are already decided ("Repeatable
tables (decided)"); M1/M2 only respect the seam. The subplan `PHASE_M6b.md` is written just-in-time
(like PHASE_M2) when M6b becomes next.

Still assumed (flag if wrong): "API-based" = CLI/package with LLM-API stages, **not** a served
web API; CLI lib = **typer**; package name = `tax_graph`.
