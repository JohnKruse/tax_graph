# PHASE M9 - Schedule D expansion + LINK + Verification Record   [ ]

**Canary:** Daisy Chain
**Depends on:** M8 (drill gate green - bulk extraction UNLOCKED), M7 (frontier registry -
the worklist that CHOSE this form; LINK and coverage lean on it), M6b (table subunits +
promotion precedent), M6 (oracle harness to extend).
**Goal:** The first data-driven form expansion. Acquire + extract the full Schedule D under
the complete M8 verification net (the first form extracted with the ladder in place from day
one), introduce the project's FIRST `parameter` nodes (the $3000/$1500 capital-loss limit,
line 21), promote (John's gate), realize the 8949 outbound-flow declarations into real edges
via the long-deferred **LINK** step, extend the oracle harness to the widened domain, and
ship the user-facing **Form Verification Record** (`VERIFICATION.md` + per-form pages) now
that the data to generate it exists.

## Why
M7's weighted worklist is unanimous: every open frontier end points at Schedule D (~24M
returns each). This phase converts those `declared` entries to `modeled`, raises the
filer-weighted coverage number, produces the FIRST real verification-economics data (human
minutes, calibration escapes) from an extraction that ran under the full net, and turns the
loss-beyond-$3000 case from an out-of-domain fence into a correctly-modeled branch.

## Exit criteria (must pass 100%)
- `pytest -m m9` green - offline/deterministic (LLM/OCR/oracle mocked or gated).
- Schedule D extraction ran under the full net: tiers assigned, `metrics.yaml` written,
  calibration sample audited, and **`human_minutes` FILLED at promotion** (first real
  payoff datum); N-version + example mining ran for the Schedule D bundle (gated).
- The promoted graph passes `validate`/`build`/base-deps `run`; single-lot parity (line 7 =
  2000) and the multi-lot example (line 7 = 250) unchanged.
- **LINK realized:** the 8949 `outbound_flows.yaml` declarations are real edges targeting
  promoted Schedule D nodes; the rebuilt frontier registry flips those entries `declared ->
  modeled`; `tax-graph frontier` reports a coverage INCREASE with the same SOI provenance.
- **Line 21 works:** a net-loss-beyond-$3000 scenario now computes line 21 = -3000 (or
  -1500 MFS) through cited `parameter` nodes, agrees with OTS live, and the old
  out-of-domain canary is retired in favor of the modeled branch; the raw net loss still
  flows to the Return Record carryforward with its structure-only caveat (carryover
  WORKSHEET remains deferred).
- Gated oracle job: >= 100 fuzz scenarios over the WIDENED domain (short-term + long-term
  lots, mixed, losses past $3000) agree with OTS or are triaged - zero silent; a corpus
  batch re-frozen with live-diff provenance; box map extended to the new Schedule D lines
  and validated against the OTS label inventory.
- `VERIFICATION.md` + per-form record pages are COMMITTED, regenerate byte-identically from
  data (`tax-graph verify record`), and are reachable over MCP (additive surface).
- ASCII check OK; full `pytest` green; runtime stays base-deps light.

## Guardrails (do not drift)
- **Incomplete, but never wrong - now with teeth.** Schedule D branches beyond this phase's
  scope (line 18 28%-rate worksheet, line 19 unrecaptured 1250, line 20/QDCGT tax
  computation, the carryover worksheet, lines 4-6/11-14 passthrough inputs) are EXPLICIT
  frontier entries; the engine emits M7's typed `unresolved` trace through them - never a
  guessed zero. The Verification Record states these gaps in plain language.
- **Parameters are nodes, never inline numbers** (engineering-plan "Parameters and
  thresholds (decided)"). The $3000/$1500 limit enters as cited `parameter` node(s)
  (additive `node_type`), consumed via the closed ops (`MIN`/`MAX`/`IF_ELSE`/
  `LOOKUP_TABLE` as the worker judges best); the engine implements only the ops this
  branch needs. The no-magic-numbers validator flag must PASS on the promoted graph, and
  the drill catalog gains a wrong-parameter-value mutation.
- **LINK resolves against the PROMOTED live index only** (PHASE_M4 pinned decision 6) -
  never against another form's raw drafts. Declarations whose targets are still absent
  stay declarations (frontier), silently realizing nothing.
- **Promotion is JOHN's gate** (M6b precedent): prepare the diff - extracted Schedule D
  subunits/lines replacing the 8 hand-authored `schedule_d_2025` nodes, PRESERVING the
  edge into 1040 line 7 - and stop for approval before the live graph changes.
- **The Verification Record is GENERATED, never hand-written** (design pinned in
  `docs/extraction-verification.md` Section 10): rendered deterministically from
  metrics/corpus/triage/drill/example/frontier data; witness ABSENCES stated plainly;
  plain-language tiers from the supported-branch bar; committed because it describes
  public forms. Regeneration must be byte-stable (no clocks; dates from provenance).
- **Offline core / gated network+OCR+LLM+oracle** (established pattern). Acquisition needs
  the `[acquire]` extra + Mistral OCR key for the instructions; extraction/N-version/
  mining need the LLM key; fuzz needs the installed OTS. Every gated artifact lands as
  committed fixtures the offline suite replays.
- **Deferred, do not build:** tax LIABILITY computation (and with it PolicyEngine
  witnessing); Form 1040 full extraction (next expansion, chosen by the frontier
  worklist); the Coverage Map render (consumes `frontier --json`, still reserved);
  carryover computation. ASCII-only; schemas additive-only; drafts law unchanged.

## Steps

- [DONE] **Step 1 - Acquire + render the Schedule D bundle.** The manifest already declares
  `schedule_d_2025` + `instructions_schedule_d_2025` but only the 8949 bundle was ever
  rendered (check `.cache/raw/2025/`). Run acquire/OCR/render for the pair (gated:
  network + Mistral key); verify the artifacts (line-anchored `.txt`, `.fields.json`
  grid, instruction `.pages/` + `.links.json`), citation-integrity, and that the form
  render keeps column/section headers and front-matter (reserved-seam rule). Commit any
  fixture slices the offline tests need. Test: input loader resolves the new bundle;
  outline builder produces a sane Schedule D tree (Parts I/II/III, the line 1b-3 and
  8b-10 row bands, the line 21 cue) from the real artifacts. Docs.

- [DONE] **Step 2 - Extract under the full net (first real economics data).** Outline-first
  extraction of `schedule_d_2025` with its instructions: tiers, `metrics.yaml`,
  calibration sample; gated N-version (cross-family) and worked-example mining from the
  Schedule D instructions (freeze confirmed examples). Both-direction field completeness
  must pass or carry explicit `not_modeled` records (Parts/lines out of scope). John (or
  the worker, timed) reviews ONLY the exception queue + calibration sample and RECORDS
  the minutes - the first live measurement of the payoff metric. No promotion in this
  step. Test (offline, mocked): Schedule D fixtures produce schema-valid drafts with
  table subunits for the 1b-3 / 8b-10 bands; unmapped fields flag. Docs.

- [ ] **Step 3 - First parameter nodes + the line 21 loss-limit branch.** Additive
  `parameter` node_type in `node.schema.json`; author/extract the capital-loss limit
  parameters ($3000; $1500 MFS) with verbatim citations from the Schedule D instructions;
  the line 21 rule computes the smaller-of (loss, limit by filing status) via closed ops;
  engine implements the op(s) needed; `taxpayer_facts` already carries `filing_status`.
  Validator: the no-magic-numbers flag (numeric literal in `rule.parameters` that is not
  structural) is now enforced repo-wide; drill catalog gains `wrong_parameter_value`
  (mutate 3000 -> 3500; expect the example/oracle layer to catch). Unmodeled neighbors
  (lines 18-20, carryover worksheet) become frontier entries with `unresolved` engine
  traces. Test: loss 5000 -> line 21 = -3000 (single) / -1500 (MFS) with the parameter
  node in the trace + citation; gain scenarios bypass; unresolved trace for a line-20
  dependency; magic-number drill fires. Docs.

- [ ] **Step 4 - Promotion (JOHN's gate) + LINK realization + frontier flip.** Prepare the
  promotion diff (replace the hand-authored Schedule D slice; preserve the 1040 line 7
  edge; wire the promoted 8b/1b/etc. lines to receive the 8949 totals); STOP for John's
  approval. After approval: implement the LINK step (`tax-graph link --year 2025` or an
  assembly-time pass, worker's call) that resolves `outbound_flows.yaml` declarations
  against the promoted live node index into real FEEDS edges - declarations with absent
  targets remain declarations. Rebuild the frontier registry: the five Schedule D entries
  flip to `modeled`; `tax-graph frontier` coverage rises; validator green (registered
  frontier passes, dangling edge still fails). Parity: line 7 = 2000 and 250 examples
  unchanged. Test: LINK realizes exactly the resolvable declarations, idempotently; a
  declaration targeting an absent form stays declared. Docs.

- [ ] **Step 5 - Extend the oracle harness to the widened domain.** Box map grows to the
  newly-modeled Schedule D lines (labels from the committed OTS inventory: D1b*, D2*,
  D3*, D8b*, D9*, D10*, D21, ...) - validated both ways; scenario model gains SHORT-TERM
  lots (Part I) and losses beyond $3000 (now in-domain via line 21); carryover inputs
  stay fenced at zero with a guard; retire the old loss-limit out-of-domain canary in
  favor of an agreement test at line 21. Gated: >= 100 fuzz scenarios over the widened
  domain agree or triage; re-freeze a corpus batch (live-diff provenance only). Offline:
  renderer goldens for an ST+LT mixed scenario; differ fixtures for line 21. Docs.

- [ ] **Step 6 - Form Verification Record (user-facing trust surface).**
  `tax-graph verify record --year 2025`: generate `VERIFICATION.md` (roll-up: coverage %
  from frontier, per-form tier/witness summary, drill-gate status) + per-form pages
  (`docs/verification/<document_id>.md`): what is modeled / explicitly not modeled;
  the witness list with counts and versions (OTS scenarios, IRS examples, N-version,
  properties, calibration + escapes); triage outcomes; plain-language tier. Byte-stable
  regeneration from committed data (metrics from the M9 extraction get committed as the
  per-form record source or regenerated - worker pins which, keeping `_drafts/`
  gitignored law intact: the RECORD is committed, raw drafts are not). MCP: additive
  exposure (verification summary on `get_document` or a `get_verification` tool),
  following the M2 behavioral contract. Test: golden record for 8949 + Schedule D;
  regeneration is byte-identical; a witness absence renders as an explicit statement,
  never an omission. Exit-criteria commands run. Docs: README.

When all steps are `[DONE]`: mark this phase `[COMPLETE]`, move it to `plans/archive/`,
update `plans/AGENT_HANDOFF.md`, single `git push`, and tell John. Next expansion target is
whatever `tax-graph frontier` then ranks first (expected: Form 1040 itself and the 1099-B
fact seam) - the Architect plans it just-in-time from the worklist.
