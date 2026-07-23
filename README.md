# Tax Graph

[![CI](https://github.com/JohnKruse/tax_graph/actions/workflows/ci.yml/badge.svg)](https://github.com/JohnKruse/tax_graph/actions/workflows/ci.yml)

Tax Graph is a local-first project for modeling U.S. tax forms as a typed,
deterministic computation graph. The current proof of concept covers a narrow
2025 capital-gains slice:

```text
1099-B -> Form 8949 -> Schedule D -> Form 1040 line 7
```

The goal is for agents and tools to traverse verified tax graph data instead of
inventing tax logic.

## Alpha notice

Tax Graph is an alpha product, not tax advice. Verify every result and all
filing decisions before filing. It runs locally: the distributed runtime does
not send taxpayer data to a hosted service, and it does not e-file a return.

<!-- mcp-name: io.github.johnkruse/tax-graph -->

## Install

Install the alpha runtime from PyPI with `uvx tax-graph serve --year 2025`, or
with pip:

```powershell
pip install tax-graph==0.1.0a1
```

This project is also usable from a source checkout with `uv`.

```powershell
uv sync
```

The base install is the light runtime: graph validation, execution, and (in M1)
SQLite build/read commands. It intentionally does not install acquisition,
OCR, PDF rendering, or live LLM SDKs.

Maintainers who need the full build pipeline should install the build extra:

```powershell
uv sync --extra build
```

For local development, including pytest and the build pipeline extras:

```powershell
uv sync --extra dev
```

If `uv` is not available in your environment yet, the existing proof-of-concept
scripts can still be run with Python directly.

Live LLM extraction uses optional provider SDKs. For the default OpenRouter
adapter, install the OpenAI-compatible SDK extra:

```powershell
uv sync --extra llm-openrouter
```

Live differential oracle runs are optional and gated. The base suite replays
committed fixtures offline; a maintainer who wants to invoke OpenTaxSolver
should install the oracle extra and configure a pinned SourceForge release in
`config/tax-graph.config.yaml`. The example config pins the 2025 Windows
v23.06 zip and sha256 used by M6:

```powershell
uv sync --extra oracles
uv run tax-graph oracle install --year 2025
uv run tax-graph oracle fuzz --year 2025 --n 100 --seed 1234
uv run tax-graph oracle freeze --year 2025 --n 20 --seed 20250705
uv run tax-graph oracle replay-corpus --year 2025
```

The M6 harness keeps its checked-in comparison data under `oracles/`: the 2025
box map links Tax Graph node ids to OTS output labels, and the label inventory
fixture validates that every mapped OTS box is known before any diff runs.
Generated scenarios render both to Tax Graph table-row `facts.yaml` and to an
OTS 1040 input text file plus Form 8949 CSV. The current domain generates 1 to
15 long-term lots, deliberately crossing the printed 11-row Form 8949 grid, and
includes mixed gain/loss rows plus nonzero column (g) adjustments.

M10 widens that oracle surface additively: the 2025 domain now also drives
modeled witness lines from Schedule 1, Schedule 1-A, Schedule 2, Schedule 3,
Schedule A, Schedule B, and Form 6251. The widened box map compares only labels
the installed OTS solver actually emits (for example `B4`, `B6`, `S2_18`, and
`AMT_Form_6251_L2g`), while guard boxes keep the still-unmodeled branches inert.

The differ compares whole-dollar mapped boxes and evaluates guard boxes first.
A guard failure marks the scenario `rejected` as outside the fenced domain; a
mapped-box mismatch marks it `disagreed` for triage, with the full generated
scenario attached to the report.

`tax-graph oracle fuzz` loads the committed domain profile, generates scenarios
from a deterministic seed, writes OTS inputs under `output/oracle_fuzz/`, and
writes a `triage.yaml` for any rejected or disagreed scenario. It requires a
configured local OTS executable and is intended for gated oracle jobs, not the
base CI path.

`tax-graph oracle freeze` runs generated scenarios through live OTS and
materializes only agreed diff reports into
`examples/oracle_corpus/<scenario_id>/facts.yaml` and `expected.yaml`, plus a
`corpus.yaml` manifest. `tax-graph oracle replay-corpus` runs those fixtures
offline through the deterministic engine. `oracles/triage.yaml` records
disagreements and their disposition before any non-agreed pair is allowed into
the frozen corpus. The committed M6b corpus is a live OTS-agreed multi-lot
batch with `live_ots_diff_report` provenance.

M7 adds a committed SOI filing-frequency reference under `data/soi/`.
`form_counts_<soi_year>.yaml` stores return-count weights by graph document id
with SOI provenance, retrieval date, and the sample-based estimate caveat.
`form_id_map.yaml` maps SOI table labels to Tax Graph document ids. Maintainers
can refresh a normalized CSV extract through `tax_graph.acquire.soi`; runtime
commands read only the committed YAML and do not import acquisition extras.

## Step Driver

M10 introduces a phase-step driver at `tools/step_driver.py`. It reads a
`plans/PHASE_<id>.md` file, parses the `[worker-light]` /
`[worker-standard]` / `[worker-heavy]` tags, renders the launcher command for
each tier from `config/driver.yaml`, and runs the deterministic gate suite
between steps.

The driver is intentionally conservative:

- It stops before any step marked with a driver stop marker.
- A gate failure blocks the next step.
- `--dry-run` prints the planned session sequence without launching anything.

Example:

```powershell
python tools/step_driver.py --phase M10 --dry-run
```

`config/driver.yaml` is John-owned and provider-agnostic. The checked-in sample
maps each worker tier to a command template and defines the between-step gate
suite (`pytest`, `validate`, ASCII). Templates may use `{prompt}`,
`{prompt_file}`, `{phase_id}`, `{step_number}`, `{step_tier}`, `{root}`, and
related step context placeholders.

## CLI Usage

Phase M0 provides a package CLI named `tax-graph`:

```powershell
uv run tax-graph validate 2025
uv run tax-graph run --facts examples\capital_gains_basic\facts.yaml
uv run tax-graph build 2025
uv run tax-graph run --facts examples\capital_gains_basic\facts.yaml --source sqlite
uv run tax-graph run --facts examples\capital_gains_basic\facts.yaml --prior-record prior.carryforward.yaml
uv run tax-graph serve --year 2025
uv run tax-graph oracle install --year 2025
uv run tax-graph oracle fuzz --year 2025 --n 100 --seed 1234
uv run tax-graph oracle freeze --year 2025 --n 20 --seed 20250705
uv run tax-graph oracle replay-corpus --year 2025
uv run tax-graph drill run --year 2025
uv run tax-graph verify mine-examples --doc instructions_form_8949_2025 --limit 1
uv run tax-graph verify replay-examples --year 2025
uv run tax-graph verify nversion --doc form_8949_2025
uv run tax-graph verify report --year 2025
uv run tax-graph verify diff-drafts --doc form_8949_2025 --year 2025
uv run tax-graph link --year 2025
uv run tax-graph frontier --year 2025
uv run tax-graph acquire 2025
uv run tax-graph acquire 2025 --check
uv run tax-graph extract --doc form_8949_2025
```

When working from a source checkout before installing console scripts, the same
commands can be run as a module:

```powershell
python -m tax_graph.cli validate 2025
python -m tax_graph.cli run --facts examples\capital_gains_basic\facts.yaml
python -m tax_graph.cli build 2025
python -m tax_graph.cli serve --year 2025
python -m tax_graph.cli oracle install --year 2025
python -m tax_graph.cli oracle fuzz --year 2025 --n 100 --seed 1234
python -m tax_graph.cli oracle freeze --year 2025 --n 20 --seed 20250705
python -m tax_graph.cli oracle replay-corpus --year 2025
python -m tax_graph.cli drill run --year 2025
python -m tax_graph.cli verify mine-examples --doc instructions_form_8949_2025 --limit 1
python -m tax_graph.cli verify replay-examples --year 2025
python -m tax_graph.cli verify nversion --doc form_8949_2025
python -m tax_graph.cli verify report --year 2025
python -m tax_graph.cli verify diff-drafts --doc form_8949_2025 --year 2025
python -m tax_graph.cli link --year 2025
python -m tax_graph.cli frontier --year 2025
python -m tax_graph.cli acquire 2025 --check
python -m tax_graph.cli extract --doc form_8949_2025
```

Expected result: `form_1040_2025_line_7_capital_gain_loss = 2000`.

`tax-graph build 2025` compiles the authored YAML graph into
`build/tax_graph_2025.sqlite`. The SQLite file is a deterministic runtime
artifact rebuilt from YAML; `build/` is gitignored, so the binary artifact is
not committed. Repeatable table subunits compile into the SQLite `tables`
projection alongside nodes, edges, rules, citations, and decisions.

After a build exists, `tax-graph run` defaults to the SQLite artifact. Use
`--source yaml` to force the authored YAML source or `--source sqlite` to require
the compiled artifact.

`tax-graph run` writes a Return Record pair by default next to the facts file:
`return_record_<year>.md` for the human memo and
`return_record_<year>.carryforward.yaml` for the machine-ingestible payload. Use
`--record-dir` to write them elsewhere, `--no-record` to opt out, and
`--prior-record <carryforward.yaml>` to prime a later run from a previous
structured block. Carryforwards without a resolvable `target_node` are reported
as not ingested rather than guessed.

Repeatable table runtime support is additive. Table row instances are supplied
under `tables` in taxpayer facts and keyed by `row_key`; traces address an
instance as `<template_node>#<row_key>`. The live Form 8949 Part I/II graph now
uses promoted repeatable table subunits, and the capital-gains example supplies
its long-term lot as one Part II table row.

The frontier registry is derived data, regenerated with
`tax-graph frontier build --year 2025` into `graph/2025/frontier.yaml`. Query
it with `tax-graph frontier --year 2025` or `--json` for the deferred map data.
After a reviewed form promotion, `tax-graph link --year 2025` resolves
`_drafts/*/outbound_flows.yaml` declarations against the promoted live node
index and writes deterministic FEEDS edges under `graph/2025/edges/`. A
declaration whose target line is still absent remains a frontier entry; LINK
does not realize edges against raw drafts. A committed
`graph/<year>/flow-dispositions.yaml` artifact can also mark a reviewed draft
flow as rejected, which keeps it out of LINK and records the disposition in the
derived frontier registry instead of leaving it as a live declaration forever.
It combines promoted graph references, reviewed outbound-flow declarations,
manifest scope, and committed SOI counts. Modeled entries name already-covered
targets; declared entries are intentional open ends; rejected entries are
reviewed false positives; unmodeled entries are
outside the current manifest scope. Coverage is reported against the full SOI
form-count universe and the currently in-scope weighted manifest set. The
registry is not hand-maintained. The graph validator schema-checks the registry
and only treats a dangling graph edge as intentional when a matching frontier
entry has a target URL and a live citation reference. At runtime, if a modeled
calculation depends on a declared or unmodeled frontier, the engine emits an
`unresolved` trace entry with the frontier URL and citation instead of computing
through the missing dependency.

Outline-first extraction now carries a deterministic repeatable-table detector:
it emits a draft `tables` subunit only when repeated field-grid row bands and a
totals cue agree on the summed columns. A mismatch is routed for human review
instead of guessed.

Distribution path: source installs can use the light runtime (`pip install
tax-graph`) or the maintainer pipeline (`pip install tax-graph[build]`). A later
single-file binary can bundle the runtime plus a prebuilt SQLite artifact so an
end user does not need Python or build-time dependencies.

## MCP Server

Phase M2 adds a local stdio MCP server:

```powershell
uv run tax-graph serve --year 2025
```

If a previous MCP client was forcibly closed, recover any server processes it
left behind before rebuilding the SQLite artifact:

```powershell
uv run tax-graph serve --sweep-orphans
```

The server loads `build/tax_graph_2025.sqlite` when present and falls back to the
authored YAML graph otherwise. It is a runtime adapter over the graph and engine;
it does not fetch sources, run OCR, or call an LLM.

M2 read-only tools expose graph traversal without asking the model to infer tax
rules: `get_document`, `get_node`, `get_dependencies`,
`get_downstream_effects`, and `get_citation`. Node tools accept a future
runtime instance suffix such as `some_column_node#row_key`; the base node is
resolved from the static graph while the row key remains runtime-only.

Execution tools delegate to the deterministic engine: `execute_tax_tree`,
`list_required_inputs`, `explain_calculation`, and `export_audit_file`. They
return computed values, missing required inputs, machine-readable trace entries,
and human-readable audit text without putting tax calculation logic in MCP.
M5 adds `export_return_record`, which returns the Markdown memo text paired with
the structured carryforward block for the supplied facts.

The server instructions tell MCP clients to call tools rather than compute tax
values, to cite every asserted rule, to present decision options including the
escape hatch, and to report missing or unsupported paths instead of guessing.

Example Claude Desktop config while developing from this checkout:

```json
{
  "mcpServers": {
    "tax-graph": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\path\\to\\tax_graph",
        "run",
        "python",
        "-m",
        "tax_graph.cli",
        "serve",
        "--year",
        "2025"
      ]
    }
  }
}
```

## CI

GitHub Actions runs the deterministic gate on pushes and pull requests:

```powershell
uv sync --extra dev
uv run tax-graph validate 2025
uv run tax-graph run --facts examples\capital_gains_basic\facts.yaml
uv run pytest
```

## Acquisition Manifest

Source acquisition starts from `config/manifest.yaml`, a reviewed list of stable
IRS PDF URLs for the supported tax year. M3 begins with the 2025 capital-gains
slice: Form 8949, Schedule D, Form 1040, Form 1099-B, and their instructions
where applicable.

Fetched source documents are stored under the configured raw store, defaulting
to `.cache/raw/<year>/`, with the original PDF, extracted text, and JSON
metadata containing the content hash and retrieval date.

The raw store also keeps `_state.json`, a document-id index of the last seen
content hash. Acquisition uses that state to report new, changed, and unchanged
source documents.

Citation integrity checks compare each authored `quoted_text` span to the
rendered text in the raw store after whitespace normalization. A source map can
point form citations at instruction PDFs when the authoritative quote lives in
the instructions.

Forms, schedules, and source documents render through PyMuPDF into line-numbered
text plus a companion `.fields.json` AcroForm grid. Instruction rendering is
handled separately by Mistral OCR, storing per-document markdown, per-page
markdown, and extracted links. The OCR path caches by content hash and fails
loudly when no OCR client or key is available.

M9 adds a deterministic offline Schedule D fixture slice under
`tests/fixtures/schedule_d_bundle/`. The live cache for Step 1 was produced
from `f1040sd.pdf` and `i1040sd.pdf`; the full manifest acquire currently needs
the Form 1099-B URL reviewed because the configured IRS URL returned 404 during
the M9 Step 1 run. The committed fixture preserves only the lines needed for
loader and outline regression tests.

## Extraction Drafts

Phase M4 adds `tax-graph extract --doc <document_id>`, which turns rendered
source artifacts into schema-valid draft graph YAML through a mocked-in-tests
LLM client protocol and a live provider adapter when `llm.provider` is
configured. Drafts are written only under `graph/<year>/_drafts/<document_id>/`, together with
`provenance.yaml`, `review.md`, and a standalone `review.html` source-to-draft
visual review page; the live graph directories are never modified by
extraction.

Live extraction is provider-agnostic behind `tax_graph.extract.llm_client.LlmClient`.
The built-in adapters currently cover `openrouter`, `anthropic`, and `openai`,
with provider SDKs installed only when needed via optional extras. OpenRouter
uses the OpenAI-compatible client with `llm.base_url`, so model ids may use the
gateway's `vendor/model` format. The Mistral-specific path is limited to OCR
for instructions and publications.

Automatic routing is conservative: a draft must meet the configured confidence
threshold, agree with the independent critic, and pass deterministic checks
before it appears in the auto-accepted section of the review report. Anything
else stays on the human-review list.

M4 also includes an outline-first canary path, enabled through config with
`extraction.mode: outline_first`. That path writes local review artifacts
(`outline.yaml`, `candidate_spans.yaml`, and `outbound_flows.yaml`) under the
same `_drafts` directory, asks narrow micro-extraction questions over outline
nodes, and assembles canonical draft graph objects in code. The default remains
`one_pass` until the held-out Form 8949 validation is complete.
M9 extends this path for Schedule D: the six Form 8949 landing row bands
(`1b`, `2`, `3`, `8b`, `9`, and `10`) use deterministic `d - e + g -> h`
formula assembly, while out-of-scope Schedule D lines and identity/status
fields are carried as a draft `documents.yaml` `not_modeled_fields` record
until the promotion gate.

M9 also introduces cited `parameter` nodes. Schedule D line 21 now selects the
capital-loss limit through `taxpayer_2025_filing_status`: most filing statuses
use the cited `$3000` node, while married filing separately uses the cited
`$1500` node. The engine supports the closed operations needed for this branch
(`LOOKUP_TABLE`, `NEGATE`, and `MAX`) and renders parameter nodes with their
citations in audit traces. Deferred Schedule D neighbors, starting with line 20,
are declared through `graph/2025/frontier-declarations.yaml`; the generated
frontier registry lets the engine emit an `unresolved` trace instead of guessing
worksheet values.

M9 also adds a user-facing verification surface. `tax-graph verify record --year
2025` generates the committed roll-up `VERIFICATION.md` plus per-form pages
under `docs/verification/`, stating what is modeled, which witnesses cover the
branch, and which witness types are still absent. The same summary is available
at runtime over MCP through `get_verification` and `get_document`.

## Verification Drills

M8 starts the extraction verification ladder by mutation-testing the check net
itself. `tax-graph drill run --year 2025` loads the known-good live graph,
injects one seeded defect at a time from `tax_graph/drills/drill_catalog.yaml`,
and reports which ladder layer caught it. The default catalog covers swapped
SUBTRACT roles, dropped addends, wrong outbound flow targets, phantom nodes,
table totals omissions, corrupted citation quotes, confidence inflation as a
no-op, and inline IRS magic numbers in `rule.parameters`.
M9 adds a wrong-parameter-value mutation for the Schedule D line 21 capital-loss
limit.

The drill gate is intentionally offline and deterministic. A caught defect must
name the catching layer; an uncaught catalog entry fails the command honestly
instead of shrinking the catalog.

M8 also tightens AcroForm field completeness. A rendered `.fields.json` entry
must map to a promoted/draft node, a repeatable-table template column, or a
document-level `not_modeled_fields` record with a reason. Form 8949 carries
these explicit not-modeled groups for taxpayer identity/status fields,
non-arithmetic table columns, and deferred line totals.

The same checker accepts an optional MeF line inventory fixture when an official
schema source is available. If no clean official inventory is supplied, the
check skips that witness and relies on the AcroForm grid.

The property layer runs deterministic sample facts through the engine and checks
operation semantics from the trace: COPY identity, SUM addend totals, SUBTRACT
roles and antisymmetry, repeatable-table column `(h)` as `d - e + g`, and table
total aggregation. Extraction runs these checks against draft batches; the
drill harness uses the same layer for F3 seeded defects.

Worked-example mining is gated behind `tax-graph verify mine-examples`. The
miner segments rendered IRS instruction text at `Example` headings, asks a
narrow extraction client for facts and expected node values, executes the graph,
and reports agreed/disagreed/unmappable candidates. Use `--confirm` only after a
human has checked the paragraph; confirmed examples freeze under
`examples/irs_examples/` and replay offline with
`tax-graph verify replay-examples`.
Provider or routing failures are recorded as explicit unmappable candidates, not
as agreed examples and not as committed fixtures.

N-version corroboration is gated behind `tax-graph verify nversion`. Configure
`llm.nversion_model` and `llm.nversion_vendor_family` for a second model family;
the command reruns outline-first micro-extraction, diffs assembled canonical
objects by id, and prints side-by-side review entries for disagreements.

## Compatibility Scripts

Validate the authored graph:

```powershell
python tools\validate_graph.py 2025
```

Run the capital-gains example:

```powershell
python engine\engine.py examples\capital_gains_basic\facts.yaml 2025
```

Expected result: `form_1040_2025_line_7_capital_gain_loss = 2000`.
