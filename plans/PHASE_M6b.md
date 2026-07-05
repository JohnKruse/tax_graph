# PHASE M6b - Repeatable-table execution (row instances)   [ ]

**Canary:** Tandem Abacus
**Depends on:** M1 (compiler/loader), M2 (MCP `#row_key` addressing seam already speaks this),
M4 (outline emits `transaction_table` + `totals`), M6 (oracle harness to widen).
**Decided policy (canonical, read first):** engineering-plan **"Repeatable tables (decided
2026-07-01)"** - the (a)/(b)/(c)/(d) split, the aggregate-subunit rule, runtime-only `#row_key`
instances, and the deterministic dual-signal detector. This plan only sequences it.
**Goal:** Make repeatable transaction tables real end to end - N fact rows -> per-row compute ->
totals aggregation -> per-instance trace - and promote Form 8949 Part I/II from `_drafts/` into
the live graph as table subunits (the FIRST draft promotion, human-gated). Turns the single-lot
v0 into arbitrary-N and lets the M6 harness fuzz realistic multi-lot returns against OTS.

## Why
Every transaction-bearing form repeats rows; 8949 is the archetype. The representation is fully
decided; what is missing is execution (facts rows, per-instance engine, totals), the detector
that groups extracted drafts into subunits, and the promotion that finally replaces the
hand-authored single-lot 8949 slice with extracted, table-shaped structure.

## Exit criteria (must pass 100%)
- `pytest -m m6b` green - offline/deterministic.
- A committed multi-lot example (>= 3 lots, mixed gain/loss, at least one nonzero column (g)
  adjustment) computes correct Part I/II totals and 1040 line 7 with a per-instance trace
  addressed `<column_node>#<row_key>`.
- Single-lot parity: the capital-gains example still yields 1040 line 7 = 2000, reauthored as a
  one-row table instance (see Step 5 pin).
- The deterministic detector groups 8949 line 1 + line 2 into ONE subunit from geometry + the
  totals cue on the real cached artifacts; a mismatched/absent totals cue is FLAGGED for review,
  never guessed.
- `tax-graph validate` + `build` + base-deps `run` pass with the promoted table subunits;
  SQLite/YAML parity holds.
- Gated oracle job: >= 100 multi-lot fuzz scenarios agree with OTS box-level (or triaged, zero
  silent); the loss-limit out-of-domain canary still fires; the frozen corpus gains multi-lot
  scenarios with `live_ots_diff_report` provenance.
- `uv run python tools/check_ascii.py` OK; full `pytest` green.

## Guardrails (do not drift)
- **Static ids stay flat and template-level.** No instance ever in a static node id; `#` stays
  banned by the node_id pattern - the schema itself enforces the static/runtime boundary.
- **Physical printed row slots (line 1.01..1.11) never enter ids, the graph, or facts** -
  acquisition/review geometry only. `row_key` is a runtime fact id (broker id or `r0001`) and
  may EXCEED the printed slots.
- **A table is ONE aggregate subunit** (row-template columns + totals row), not loose siblings.
- **Detection is deterministic and dual-signal** (repeated field-grid row-band AND a totals
  cue); ambiguity -> human-review flag. No LLM call fires the trigger. Row COUNT is never
  parsed - it is runtime fact (d).
- **Promotion is human-gated.** Step 5 prepares the diff; John reviews and approves before the
  live graph changes. Drafts are never auto-merged (unchanged law).
- **Schemas are additive-only** (`tables` kind + optional node fields + facts `tables` section);
  existing scalar facts files remain schema-valid.
- **No magic numbers** (engineering-plan "Parameters and thresholds (decided)"): nothing in this
  phase introduces an inline IRS number.
- **Deferred, do not build:** the cross-form LINK command (still only one extracted form);
  ST/LT carryover computation; worksheets; `parameter` nodes. ASCII-only; runtime stays light.

## Steps

- [DONE] **Step 1 - Additive schema + validator.** `schemas/table.schema.json`: a table object
  (`table_id`, `document_id`, `line_anchor`, ordered `columns` [{`column_id` e.g. "d",
  `label`, `input|computed`, `template_node`}], `totals` [{`column_id`, `total_node`}],
  `citation_refs`). Additive optional node fields: `table_id`, `column`, `role` in
  {`row_template`, `total`}. Additive `taxpayer_facts` section: `tables:` list of
  {`table_id`, `rows`: [{`row_key`, `columns`: {column_id: value}}]} - values keyed by COLUMN
  ID from the table definition (never by node id, never computed columns). Validator: table
  members exist and are consistently marked; totals' SUM columns are a subset of row columns;
  a `row_key` matching `^[a-z0-9_]+$` is not required to be unique across TABLES, only within
  one table's rows; facts columns resolve against the table definition; computed columns in
  facts are an ERROR. Tests: valid table validates; each violation fails loudly. Docs:
  `schemas/README.md`.
  - Worker note: added the table schema, additive node/facts fields, a `tables` graph kind,
    semantic table-member validation, and `validate_taxpayer_facts_document()` for table-row facts.
    SQLite pass-through was kept compatible with old local DBs so the added graph kind does not
    break existing auto-source runs before a rebuild.

- [DONE] **Step 2 - Compiler + loader pass-through.** `tables` compile to SQLite (additive table;
  nodes row already generic per the M1 seam) and load back through the same `Graph` interface;
  YAML/SQLite parity for a graph containing a table subunit. Tests: build + parity (exact
  values and trace). Docs.
  - Worker note: `Graph.tables` now round-trips through YAML and SQLite, with a temporary
    table-bearing graph fixture proving exact values/trace parity. README notes the SQLite
    `tables` projection.

- [ ] **Step 3 - Engine row instances + totals aggregation + trace.** Facts rows instantiate
  the row-template rules per `row_key`: each computed template column evaluates per instance
  (column (h) chain: d-e intermediate then +g); totals nodes aggregate their column across ALL
  instances. Trace entries for instances are addressed `<column_node_id>#<row_key>`; totals
  trace lists the instances it summed. Missing a required column value in a row -> reported
  per-instance (never guessed); zero rows -> totals compute to 0 with an explicit "no instances
  supplied" trace note. MCP needs no new tools (execute/explain delegate to Engine; `#row_key`
  resolution shipped in M2) - add one MCP test asserting per-instance trace passes through.
  Tests: 3-lot mixed gain/loss with one nonzero (g); per-instance missing-input; zero-row
  totals; MCP pass-through. Docs.

- [ ] **Step 4 - Deterministic detector + column reconciler (extraction assembly).** In the
  outline-first assembly: when (i) the field grid shows the same column x-clusters repeated
  across >= 2 y-row bands under one line anchor AND (ii) the outline carries the totals cue
  (`transaction_table` + `totals` kinds, e.g. "Add the amounts in columns (d), (e), (g), and
  (h)"), emit the grouped `table` object (Step 1 shape) into the draft. Cross-check: the
  totals' SUM columns reconcile against the grid columns and the cue text; mismatch, or a
  repeated band with NO resolvable totals -> human-review flag on the draft, no table emitted.
  Tests (mocked/offline over the real cached 8949 artifacts): both Parts detected as one
  subunit each; a doctored cue (drops column (g)) -> flagged; a doctored grid (single row
  band) -> no trigger. Docs.

- [ ] **Step 5 - Promote Form 8949 (human-gated) + example reauthor.** Regenerate the 8949
  draft with table grouping; prepare the promotion diff: replace the hand-authored 8949 nodes
  in `graph/2025/` with the extracted table subunits (Part I and Part II), PRESERVING the
  existing hand-authored FEEDS edges into the live Schedule D lines (retarget their sources to
  the promoted totals nodes; outbound-flow declarations beyond the live slice stay
  declarations). Reauthor `examples/capital_gains_basic/facts.yaml` as a ONE-ROW table instance
  (pinned: no scalar-compat shim, no dual input paths - the facts file migrates; line 7 = 2000
  is the parity proof). Present the diff to John for review; only after his approval does the
  live graph change. Then `validate`, `build`, base-deps `run`, full suite. Tests: promoted
  graph passes validator; single-lot parity; trace snapshot still cites the 8949 SUBTRACT.
  Docs: README graph status.

- [ ] **Step 6 - Widen the M6 oracle harness to N lots.** Scenario model gains multiple lots
  (and nonzero adjustments - column (g) is now modeled); OTS render lists all lots in the 8949
  CSV; the Tax Graph render emits table rows. Domain profile: 1..15 lots (crossing the 11
  printed slots on purpose - instances exceed physical geometry), mixed gains/losses, zero and
  boundary values, net loss still capped at $3000. Live gate: >= 100 multi-lot fuzz scenarios
  vs OTS; freeze a multi-lot corpus batch (live-diff provenance only). Offline tests: renderer
  goldens for a 3-lot scenario; generator bounds. Docs. Exit-criteria commands run.

When all steps are `[DONE]`: mark this phase `[COMPLETE]`, move it to `plans/archive/`, update
`plans/AGENT_HANDOFF.md`, single `git push`, and tell John. Next by milestone order: **M8**
(verification ladder, canary Skeptical Notary - plan written just-in-time; its drill gate must
pass before extraction expands beyond the capital-gains form set), with **M7** (Compass Rose)
still available as the parallel track.
