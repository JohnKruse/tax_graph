# PHASE M13 - Worksheet depth

**Canary:** Deep Ledger
**Depends on:** M12 (output layer; field-map completeness enforced in `validate`), M11
(line 16 under dual witnesses; QDCGT worksheet precedent; rounding pin: cents through
worksheets, whole-dollar once at entry lines), M10 (S1/S1A/A/S2/S3 promoted
structurally), M9 (LINK), M5 (Return Record carryforward + prior-record ingestion).
**Goal:** Deepen the liability branch where the remaining walls actually bite: model
the schedule-internal "Add lines" chains so the S1/S1A/Schedule-A supplemental inputs
re-enter the live oracle domain; land Schedule D lines 6/14 carryover inputs plus the
Capital Loss Carryover Worksheet (upgrading the Return Record's raw-loss memo to the
real worksheet-computed carryover); and convert the Schedule D line 20 wall into a
modeled decision routing to the Schedule D Tax Worksheet. Roadmap context:
engineering-plan "Roadmap M11-M15".

## Why
Three deferred debts converge here. (1) The M11 domain note (oracles/domain_2025.yaml)
pulled S1 8z / S1 21 / S1A 2a fuzz inputs because OTS aggregates them through
schedule-internal totals our graph declares but does not compute - that narrowed the
live witness domain. (2) The Return Record's capital-loss carryforward is honestly
labeled RAW, not the usable amount - the Capital Loss Carryover Worksheet is the
cross-year payoff M5 was built for. (3) Schedule D line 20 is the last pre-existing
liability wall: filers with 28%-rate or unrecaptured-1250 amounts route to the
Schedule D Tax Worksheet, not the QDCGT worksheet, and today we cannot tell them that
honestly at the tax line. This phase also proves the worksheet pattern generalizes
beyond M11's single hand-authored QDCGT instance.

## Supported profile (expansion; everything else stays a wall)
Adds to the M11/M12 profile: prior-year ST/LT capital-loss carryovers (Schedule D
lines 6/14, fed by input facts or an ingested prior Return Record); the modeled
S1/S1A/Schedule-A internal chains feeding 1040 lines 8/10 and the deduction path;
28%-rate gain (Schedule D line 18) and unrecaptured section 1250 gain (line 19) as
INPUT-backed lines whose own feeder worksheets remain declared walls; line 20 decision
routing; line 16 tax via the Schedule D Tax Worksheet when 18/19 are nonzero. NOT in
scope: the 28%-Rate Gain and Unrecaptured 1250 Worksheets' internal math (input-backed
walls this phase, modeled later only as data warrants), QBI, lines 17-24, AMT.

## Guardrails (do not drift)
- **No new engine ops expected.** The Capital Loss Carryover Worksheet is
  SUBTRACT/MIN/MAX arithmetic; the Schedule D Tax Worksheet uses the M11 vocabulary
  (MULTIPLY / LOOKUP_BRACKET / IF_ELSE / MIN / MAX). If a worksheet line genuinely
  demands a new op, STOP and pin the shape with the Architect first.
- **Worksheet provenance honesty.** Try the outline-first extractor on each worksheet;
  where it cannot produce a clean draft, hand-author with per-line citations (M11
  QDCGT precedent). Record which path each worksheet took in its deferred-review queue
  entry - never blur extracted vs authored provenance.
- **Rounding discipline unchanged:** cents carry through every worksheet; whole-dollar
  rounding once at the form entry line (M11 pin; OTS agreement is the proof).
- **Parameters are cited nodes; bulk tables are data resources.** Any new threshold
  (e.g. the 28%/25% rates) enters as a cited parameter node - the L0 drill applies.
- **OTS sign/semantics probes before trusting carryover inputs.** OTS takes D6/D14
  (carryover) and D19/Collectibles (1250 / 28%-rate) inputs; the worker pins each
  input's sign convention and aggregation against the shipped template comments AND a
  live probe before wiring the box map (external-interface QC contract).
- **Hermetic tests (pinned 2026-07-10):** no test reads `graph/<year>/_drafts/` (use
  `tests/fixtures/draft_snapshots/`, refreshing snapshots in the same commit when
  shapes change) or assumes a prebuilt `build/` artifact (build throwaway sqlite in
  tmp_path).
- **Field-map completeness is already enforced:** every newly computed node needs a
  field-map entry or an explicit exclusion, or `validate` fails (M12 seam). New
  worksheet-internal nodes are excluded (they have no official-form box); new form
  lines (D 6/14/17/18/19/20/22) get mapped.
- **Live-execution pass required (M12/M11 lesson):** offline goldens are not
  sufficient proof; the live OTS fuzz gate over the widened domain is the pass, plus
  one filing-bundle export for a loss-carryover scenario.
- **Deferred-review policy in force;** queue entries for every promotion, authored
  worksheet, and the line 20 decision node (decisions are TOP priority).
- Unchanged law: ASCII; additive schemas; drafts never committed; live graph closed;
  base-deps light; IRS line numbers are the spine; full suite green is the commit
  floor; **CI on the pushed commit must be green at every step commit and phase close**.

## Exit criteria (must pass 100%)
- `pytest -m m13` green; full `pytest` green on a SIMULATED CLEAN CHECKOUT (run once
  with `_drafts` and prebuilt sqlite absent); ASCII OK; base-deps
  `validate`/`build`/`run`/`frontier` green; parity examples unchanged (line 7 = 2000
  / 250); GitHub CI green on the pushed close commit.
- Gated live: >= 100 OTS fuzz scenarios agree AT THE TAX LINE over the WIDENED domain
  (S1/S1A/Schedule-A supplemental inputs re-admitted; ST/LT carryovers straddling the
  -3000/-1500 limit and zero boundaries; D19/Collectibles scenarios exercising the
  line 20 -> Schedule D Tax Worksheet branch) or triage - zero silent; corpus
  re-frozen with live-diff provenance; PolicyEngine liability green over the new
  frozen corpus (documented tax-table tolerance rules unchanged).
- Carryover round-trip: a year-N return with a net loss produces a Return Record whose
  carryforward block carries the WORKSHEET-computed ST/LT carryover (not the raw
  loss), and ingesting that record into a year-N+1 run populates Schedule D lines 6/14
  with correct provenance (extends the M5 round-trip test).
- Branch routing proof: a both-18/19-zero scenario still takes the QDCGT path
  (regression); a nonzero-19 scenario takes the Schedule D Tax Worksheet path and
  agrees with OTS at line 16; the boundary is a cited decision/conditional, never a
  silent default.
- Frontier: `deferred_schedule_d_2025_line_20` flips to modeled; the 28%/1250 feeder
  worksheets appear as NEW named walls with typed unresolved traces; coverage
  recomputed honestly.
- Filing bundle for a loss-carryover scenario exports with the new lines filled and
  frontier lines blank-with-note; field maps validate both directions.
- Verification records regenerated byte-stable; queue entries present; handoff BALL
  updated.

## Steps

- [DONE] **Step 1 [worker-heavy] - Schedule-internal Add-lines chains + domain
  re-admission.** Land the SUM rules/edges for the schedule-internal totals the M11
  domain note names: Schedule 1 part I (8a-8z -> 9 -> 10) and part II (-> 25),
  Schedule 1-A internal part chains (-> the totals 1040 line 13b consumes), and
  Schedule A's internal adds (-> line 17 total). Nodes exist from M10 - this step
  gives them their arithmetic; extract via the pipeline where drafts support it,
  else author addends with citations (provenance recorded). LINK realizes the totals
  into their 1040 entry lines. Re-admit S1 8z and S1A 2a to oracles/domain_2025.yaml
  with box-map entries (sign/aggregation probed live).
  **ARCHITECT RULING (2026-07-10, unblocking the S1_21 stop):** S1 line 21 does NOT
  re-enter the live OTS domain. Verified in the shipped OTS source
  (`taxsolve_US_1040_2025.c`): the `S1_21` box is PRE-worksheet "interest paid" -
  `Calc_StudentLoan_Sched1L21()` applies the $2,500 cap and the $85k/$170k MAGI
  phase-out and replaces the value - while our `schedule_1_2025_part_ii_line_21` is
  the POST-worksheet form-line deduction. Same label, different semantics; no
  domain constraint fixes that honestly. Instead: (1) line 21 stays an input-backed
  cited line and the **Student Loan Interest Deduction Worksheet becomes a new named
  frontier wall** (typed unresolved trace, queue entry); (2) the line-25/26 chain
  arithmetic with a nonzero line 21 is locked by an offline L4 example fixture
  (compensating witness - the differential cannot see it); (3) **general oracle
  contract, pinned:** a box enters the live domain only after a shipped-source or
  live-probe check that OTS honors direct injection verbatim; a box OTS recomputes
  from lower-level semantics may only be compared once our graph models the same
  computation and drives the same underlying meaning. Record the S1_21 case as the
  precedent in the domain YAML note. Future slice (pre-approved, NOT this phase
  unless Steps 1-5 are green with budget left): model the student-loan worksheet
  (cap + phase-out; small), redefine line 21 as computed-from-interest-paid, then
  re-admit S1_21 with aligned semantics - a DIVIDE op with the phase-out-ratio
  shape (excess / range, clamped to 1) is pre-authorized for that slice.
  Gated: a short live fuzz batch (>= 30) agrees at the tax line with the re-admitted
  inputs (8z, 2a) active. Field maps: new computed lines mapped or excluded. Tests
  (hermetic) + docs + queue entries.

- [DONE] **Step 2 [worker-standard] - Carryover inputs + Capital Loss Carryover
  Worksheet + Return Record upgrade.** Model Schedule D lines 6 and 14 (loss
  carryovers, entered as negative per the form) as input-backed lines feeding lines
  7/15; author/extract the Capital Loss Carryover Worksheet (cited per line) as a
  worksheet subunit computing next-year ST/LT carryover from this year's return;
  upgrade the Return Record carryforward block from `capital_loss_raw` to the
  worksheet-computed ST/LT amounts (keep the raw figure as a secondary field for
  continuity); prior-record ingestion maps the block onto lines 6/14. Drills:
  `wrong_carryover_split` (ST/LT swapped) and `carryover_ignores_limit` mutations
  caught at the expected layer. Test: round-trip year-N record -> year-N+1 lines 6/14;
  worksheet arithmetic reproduces the instructions' example if one exists. Docs.

- [ ] **Step 3 [worker-heavy] - Schedule D lines 17-22 + line 20 decision + Schedule D
  Tax Worksheet.** Model line 17 (are both 15 and 16 gains?), lines 18/19 as
  input-backed cited lines (feeder worksheets = new declared walls), the line 20
  decision (both 18/19 zero-or-blank -> QDCGT worksheet; else -> Schedule D Tax
  Worksheet; line 22 path for the loss side), and the Schedule D Tax Worksheet as a
  cited worksheet subunit (28%/25% rate lines enter as parameter nodes). Line 16 tax
  routing extends: QDCGT / SDTW / table / bracket, one entry point, cents-through
  discipline. The line 20 node is a DECISION (top-priority queue entry). Test: both
  paths compute line by line in the trace; the routing boundary flips on a one-dollar
  change in line 19; wrong-rate drill caught. Docs.

  **ARCHITECT DESIGN NOTE (2026-07-10, de-risking this step before implementation):**
  The Architect researched this step against the shipped OTS source
  (`taxsolve_US_1040_2025.c`, function `sched_D_tax_worksheet()` at line 1436, and
  the routing block at line 1355 that sets `Do_SDTW`/`Do_QDCGTW`) rather than
  hand-deriving the worksheet from instruction text alone - OTS's C code is a
  pre-validated reference for the worksheet's exact conditional structure. Started
  authoring the graph nodes/citations for all 47 lines, caught a real design flaw
  before writing any edges, and reverted the inert (edge-less, non-computing)
  scaffolding rather than commit an unverified partial worksheet. Full findings
  below so the next session does not have to redo this research.

  *Routing (verified, matches M11 exactly at the boundary):* line 17 test is
  `MIN(SchedD[15], SchedD[16]) > 0`; if true, D18 and D19 become live and line 20
  tests `MAX(D18, D19) > 0` (if true, run SDTW; else QDCGT). If line 17 is false
  (or Schedule D is a loss/zero), OTS falls through to the EXISTING M11 line-22
  gate (`qualified dividends > 0 -> QDCGT`), which is already correctly modeled as
  `form_1040_2025_qdcgt_line_4 > 0` - no change needed there. The new routing is
  strictly an ADDITIONAL outer IF_ELSE wrapping the current `form_1040_2025_root_line_16`
  chain: `condition = MIN(line17_min, line20_max) > 0` -> when_true = SDTW line 47,
  when_false = the existing (unchanged) QDCGT-vs-regular-tax chain. Verify with an
  M11 regression run (existing QDCGT/table/bracket scenarios must produce byte-identical
  results after the refactor) BEFORE adding the new SDTW branch.

  *Worksheet line map:* SDTW line 1 = `form_1040_2025_root_line_15` (reuse, no new
  node). Lines 3/4 (Form 4952) are out of scope - model as cited zero-constant
  parameter nodes, not a guessed input (Form 4952 stays unmodeled project-wide).
  Line 15 threshold reuses `form_1040_2025_qdcgt_breakpoint_0_*` (identical figures,
  same `lookup_selected_value` pattern already used for the QDCGT worksheet - see
  `graph/2025/edges/form-1040.yaml` lines 556-606 for the exact key/role wiring to
  copy). Line 26 reuses `form_1040_2025_qdcgt_breakpoint_15_*` (identical figures).
  Line 19 needs ONE new parameter set (`form_1040_2025_sdtw_breakpoint_32_*`):
  $197,300 single/MFS/HOH, $394,600 MFJ/QSS - verified against the cited instructions
  text AND cross-checked against the existing `form_1040_2025_brackets_single`
  0.32-rate floor (also 197,300) as an independent internal witness.
  **Known oracle discrepancy, do not copy:** OTS's own C source hardcodes 197390.0
  for single/MFS at this exact line (a likely OTS-side typo, not present in the
  IRS text or our own bracket data) - use 197,300 as authoritative per our citation
  and flag the ~$90 single/MFS income sliver as a documented, non-blocking triage
  entry if live fuzz ever lands exactly there (astronomically unlikely at n=100).
  Line 44 and line 46 both need "tax on an arbitrary income amount," but only line
  46's input (full taxable income) matches the existing `form_1040_2025_regular_tax`
  chain exactly (reuse it directly, zero new nodes) - line 44's input is SDTW line 21,
  a different value, so its `lookup_tax_table_amount` / `lookup_bracket_tax` /
  `if_less_than_currency` triad must be cloned with line 21 as the amount source
  (see `graph/2025/edges/form-1040.yaml` lines 378-449 for the exact pattern to
  clone).

  **The bug caught in design review - handle this correctly, it is the crux of the
  step:** lines 23-43 exist only when `line 1 > line 16` (call this gate1); nested
  inside that, lines 33-43 exist only when `line 1 == line 32` (gate2); nested
  inside THAT, lines 35-40 additionally require `SchedD[19] != 0` and lines 41-43
  additionally require `SchedD[18] != 0`. A naive implementation that computes each
  gate's condition independently from possibly-ungated upstream values is WRONG:
  if gate1 is false, line 24 (`= line 22`, itself never gated because line 22 is
  used outside this block too) can still be nonzero, and line 32 (`= line24 + line30`)
  can end up numerically equal to line 1 in a real edge case (when line 17's own
  floor to zero and line 22 = line 1 coincide), which would make gate2's naive
  `line1 == line32` test fire even though gate1 was false - silently computing 15%/
  20%/25%/28%-rate tax that should not apply. Do not rely on any single line's
  "natural" flooring to imply an enclosing gate's zero-ness; every value read by an
  OUTER gate's condition test must itself already be gated by that same outer gate
  (or the gate must be applied at every consuming line, not just the block's first
  line) - use nested nested IF_ELSE mirroring the C code's actual brace nesting,
  not independent flat conditions. Test this specific interaction with a scenario
  where line 1 == line 16 (gate1 false) but line 22 alone would coincidentally
  satisfy a naive gate2 test, to prove the nested version does NOT misfire.
  Recommended implementation order to de-risk: (1) the line 16-vs-SDTW routing
  refactor alone, verified against unchanged M11 behavior; (2) SDTW lines 1-22
  (no nested gates yet, these are unconditional); (3) the gate1 wrapper around
  lines 23-32 alone, verified with a scenario that has ONLY gate1 relevant
  (D18=D19=0 is impossible here since that would route to QDCGT instead - use a
  scenario where D18/D19 are nonzero but small, gate1 true, gate2/3/4 all false,
  and confirm lines 33-43 output zero); (4) gate2 nested inside gate1 with the
  adversarial coincidence scenario above; (5) gates 3/4 nested inside gate2 last.
  Verify EACH stage against a hand-traced OTS run (build the exact input, run
  `taxsolve_US_1040_2025.exe` on it directly, diff the `ws[]` trace lines it prints
  to stderr/output against your graph's trace) before adding the next nesting
  level - this is not optional given the blast radius (every taxpayer with 28%-rate
  or unrecaptured-1250 gain routes through this exact logic).

- [ ] **Step 4 [worker-standard] - Oracle widening + corpus re-freeze + PE re-run.**
  Box map adds D6/D14/D19/Collectibles (sign conventions from Step 1's probe
  discipline); domain adds carryover ranges straddling the loss-limit boundaries and
  D19/Collectibles ranges exercising both line 20 outcomes; retire/convert obsoleted
  canaries. Gated: >= 100 live fuzz at the tax line over the full widened domain -
  zero silent; re-freeze the corpus (live-diff provenance only); `oracle pe-liability`
  green over the new corpus; `verify parameter-diff` green including the new rate
  parameters where PolicyEngine publishes them. Offline: differ fixtures for one
  carryover scenario and one SDTW scenario. Docs.

- [ ] **Step 5 [worker-light] - Records, frontier, field maps, exit run.** Regenerate
  VERIFICATION.md + per-form pages (byte-stable); rebuild frontier (line 20 flips to
  modeled; 28%/1250 feeder worksheets declared as new walls; coverage recomputed);
  confirm field maps validate both directions; run every exit-criteria command
  including the simulated-clean-checkout pytest and the loss-scenario bundle export;
  after the close push, confirm the GitHub CI run is green (`gh run watch`); record
  results in the handoff; update the BALL line. NOT authorized: edits outside
  generated records, docs, and the handoff.

When all steps are `[DONE]`: mark `[COMPLETE]`, archive to `plans/archive/`, prune
`plans/AGENT_HANDOFF.md`, single `git push`, CONFIRM CI GREEN on that push, tell John.
Next per the pinned roadmap: M14 (Product surface, canary Open Door) - plan written
just-in-time; note the serve-lifecycle hardening (sqlite handle release, parent
watchdog, orphan sweep - pinned 2026-07-10) must land in or before M14's packaging
work if the pending spin-off task has not already done it.
