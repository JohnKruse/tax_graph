# PHASE M7 - Frontier registry + SOI-weighted coverage   [COMPLETE]

**Canary:** Compass Rose
**Depends on:** M3 (acquire - to fetch SOI tables), M4 (extraction - per-form `outbound_flows.yaml`
declarations already exist). Independent of M5/M6; slots in after the core pipeline (post-M2). The
registry's structural layer also backs the deferred cross-form LINK step (see PHASE_M4 pinned
decision 6), so the outbound-flow half may be pulled earlier if multi-form extraction lands first.
**Goal:** Make the graph's incompleteness a **first-class, data-driven, queryable** thing. Build a
derived **frontier registry** (every place the modeled graph reaches beyond itself), join it to
**SOI-derived weights** (real filing frequency), and expose a `tax-graph frontier` worklist plus a
**coverage metric**. This is the data foundation the deferred Coverage Map consumes, and it makes
"incomplete, but never wrong" mechanical: the live graph stays referentially closed; all open ends
live in the registry; the validator and engine treat registry refs as intentional, not as bugs.

## Why
We already have the first instance of a frontier record - the per-form `outbound_flows.yaml`
declaration from M4. We now need: (a) a unified registry of ALL open ends (outbound flows +
references to forms/pubs we do not model), (b) priority weights from real filing data so build
order and coverage are data-driven, not vibes, (c) a query that shows the worklist + a coverage
percentage, and (d) validator/engine rules that distinguish an intentional frontier from a dangling
bug. The power-law of IRS form usage means a small set of forms covers the vast majority of filings;
SOI weights let us SEE and PROVE where the high-value 25% is and where the long tail starts.

## Exit criteria (must pass 100%)
- `pytest -m m7` is green (deterministic; SOI fetch mocked).
- `tax-graph frontier --year 2025` prints a weight-sorted worklist (what to build next) and a
  coverage line: "covers ~X% of filer-weighted form usage" with SOI provenance (year + source).
- The Form 8949 outbound flows appear as registry entries targeting Schedule D lines (status
  `declared`, weight = Schedule D's SOI return-count).
- The validator PASSES a reference that is a registered frontier entry and FAILS a genuine dangling
  edge (a live edge whose target node does not exist and is not a registered frontier).
- Base-deps-only `validate`/`run`/`frontier` work; SOI fetch lives behind the `[acquire]` extra.

## Guardrails (do not drift)
- **Live graph stays referentially CLOSED.** Every live edge target exists; all open ends live in
  the registry. The registry is the only place the graph is allowed to point outside itself.
- **The registry is DERIVED, not hand-maintained.** A deterministic builder regenerates it from the
  graph + outbound-flow declarations + manifest scope + the SOI table, so it can never drift from
  reality. Rebuild anytime (same spirit as the SQLite compile).
- **Weight = returns-filed (user interactions), NOT dollars.** A high-dollar, low-count form is low
  priority for us. Form-level grain for v1 (line-level only where SOI's 1040 detail tables provide
  it - a later refinement).
- **SOI is sample-based and lagged.** Counts are stratified-sample estimates weighted to population,
  typically ~2 years old. Label provenance (SOI year + table URL + "estimate"); never imply
  precision. The ranking is stable year to year, so the lag is harmless.
- **Reserve, do not populate, front-matter.** Registry/document entries leave room for optional
  `title`/`purpose`/`who_must_file` (the sibling reserved item) but this phase does not extract them.
- **The visual map is OUT OF SCOPE here** (deferred icing). This phase delivers the data + query it
  will consume (`tax-graph frontier --json`).
- **ASCII-only.** Base-deps runtime; SOI fetch lazy under `[acquire]`.

## Steps

- [DONE] **Step 1 - SOI weight reference table (acquire + commit).** Add an acquire helper that
  fetches the IRS SOI "Individual Income Tax Returns" table(s) of return counts by form/schedule
  (irs.gov/statistics; the worker pins the exact table) and parses them to `form_id -> returns_count`.
  Write a committed reference file `data/soi/form_counts_<soi_year>.yaml` carrying provenance
  (`soi_year`, `source_url`, `retrieved_date`, `note: sample-based estimate`). Include an explicit
  `data/soi/form_id_map.yaml` mapping SOI labels to our document ids (unmapped forms get no weight).
  Where the table is too awkward to parse cleanly, a hand-curated extract WITH the same provenance
  block is acceptable. Test: the file loads; the core forms (1040, Schedule D, 8949, Schedule B,
  Schedule 3) have counts; a power-law sanity check (1040 outranks 1116 outranks an obscure form).
  Docs: the source, the lag, and the sample caveat.

- [DONE] **Step 2 - Frontier registry schema + deterministic builder.** Define
  `schemas/frontier.schema.json` (entry: `frontier_id`, `kind` =
  `outbound_flow|form_reference|pub_reference`, `source` [node_id or document_id], `target`
  [document_id (+ `line` for outbound_flow) or external pub id], `target_url`, `citation_ref`,
  `status` = `modeled|declared|unmodeled`, `weight` [number or null], reserved optional
  `title`/`purpose`). Implement `tax_graph/frontier/build.py`: scan the live graph (edges +
  citations) + promoted outbound-flow declarations + manifest scope + the SOI table, and emit
  `graph/<year>/frontier.yaml` (deterministic, stable ordering). Status: `modeled` if the target is
  in the live graph; `declared` if it is in the manifest scope but not yet modeled; `unmodeled` if it
  is referenced but out of scope. Weight = the SOI count of the target form. Wire `tax-graph
  frontier build [--year]`. Test: build 2025; the 8949 outbound flows are `outbound_flow` entries
  targeting Schedule D lines with `status: declared` and `weight` = Schedule D's SOI count; a
  reference to a publication maps to `pub_reference` with `weight: null`. Base deps only. Docs.

- [DONE] **Step 3 - `tax-graph frontier` query (worklist + coverage metric).** Read `frontier.yaml` +
  the SOI table + the modeled set and print: (a) the **worklist** - `status: declared` entries
  sorted by weight descending (the data-driven "build this next" list); and (b) the **coverage
  metric** - `sum(weight of modeled forms) / sum(weight over the universe)` as
  "covers ~X% of filer-weighted form usage", reported BOTH against the full SOI universe and against
  the in-scope target set, with the SOI provenance line. Add `--json` for machine output (the
  deferred map consumes this). Test: coverage is between 0 and 100; marking a form modeled increases
  coverage; the worklist is weight-sorted; `--json` validates. Docs.

- [DONE] **Step 4 - Validator integration (intentional incompleteness vs dangling bug).** Extend
  `tools/validate_graph.py`: a live edge whose target node is missing is an ERROR **unless** that
  reference is a well-formed registered frontier entry (valid target address + `target_url` +
  `citation_ref`); a frontier entry missing its url or citation is an error. So the registry blesses
  intentional open ends while genuine dangling edges still fail. Test: a dangling edge with no
  frontier entry fails; the same reference with a valid frontier entry passes; a malformed frontier
  entry fails. Docs.

- [DONE] **Step 5 - Engine frontier behavior (never compute through the wall).** When a computed node's
  input chain reaches a frontier (a `declared`/`unmodeled` upstream), the engine emits a typed
  `unresolved` Tax Trace entry - "depends on <target address>, not yet modeled, see <target_url>" -
  rather than a number, extending the existing invariant that the engine reports missing inputs
  instead of guessing. Test: a node depending on a pending frontier yields an explicit
  unresolved-with-citation trace entry and never 0/null; a fully-modeled chain still computes
  normally. Exit: `pytest -m m7` green. Docs.

When all steps are `[DONE]`: mark this phase `[COMPLETE]`, move it to `plans/archive/`, and tell
John. The deferred Coverage Map render (engineering-plan "Reserved - Coverage Map") then consumes
`tax-graph frontier --json` - no new data layer needed.
