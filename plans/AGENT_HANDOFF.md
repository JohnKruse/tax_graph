# AGENT_HANDOFF.md

The single living doc for active Claude (Architect) <-> Codex (Worker) coordination. Update it in
place; do NOT spawn new per-topic note files. Standing rules: `../AGENTS.md`. Master plan:
`../docs/engineering-plan.md`.

## How to use
- **Worker:** raise questions/blocks under **Open for Architect**.
- **Architect:** answer there (and pin durable decisions into the relevant `PHASE_<id>.md`), then
  clear the item. Record active direction under **From Architect**.
- Keep it short - move resolved items to **Resolved** or delete them.
- History: pruned 2026-07-07, at M9 close 2026-07-08, and at M11 close 2026-07-09. Full
  narration lives in `plans/archive/` (phase plans with close notes) and git history.

## Current state (2026-07-09)

**BALL: ARCHITECT.** Next action: write PHASE_M12 (Output layer, canary Paper Trail)
just-in-time on John's go. M11 is CLOSED and archived; nothing waits on a worker;
nothing waits on John.
(Whoever finishes a turn: update this BALL line - it is the first thing read.)

- **M0-M11 are COMPLETE and archived** (see `plans/archive/`, each with a close note).
- **THE GRAPH COMPUTES TAX.** M11 landed the Form 1040 taxable-income spine (lines 1a-15),
  the first parameter tables (standard deduction, brackets, QDCGT breakpoints - every value
  witnessed by IRS source text AND live PolicyEngine), the under-$100k tax table as a
  compiled data resource, three new engine ops (MULTIPLY / LOOKUP_BRACKET / IF_ELSE), the
  hand-authored QDCGT worksheet (cited per line), the deduction-method decision node, and
  line 16 routing across the QDCGT / tax-table / bracket paths.
- **Dual-witness state:** live OTS fuzz 100/100 agreed AT THE TAX LINE (all five filing
  statuses, QDCGT breakpoints, the $100k table/formula boundary); frozen corpus seed
  20260711 (`live_ots_diff_report`); PolicyEngine liability 20/20 (8 exact, 12 within the
  documented tax-table tolerance - PE computes the bracket formula, not the IRS table) and
  parameter-diff 20/20. Rounding discipline pinned: cents carry through the worksheet,
  whole-dollar rounding once at the line 16 entry.
- **Named walls (frontier-declared):** Schedule D line 20 QDCGT-worksheet branch
  (pre-existing), 1040 line 13a QBI, 1040 lines 17-24 credits/total-tax chain incl. AMT.
- **Deferred to M13 (pinned in oracles/domain_2025.yaml):** S1/S1A/Schedule-A supplemental
  fuzz inputs are out of the live domain until the schedule-internal "Add lines" chains are
  modeled - OTS aggregates them into AGI/line 13b; our graph does not yet.
- **Review queue:** promotion entries for all M10/M11 promotions plus the authored QDCGT
  worksheet (high) and the deduction decision node (TOP priority), one frozen IRS example,
  one flow rejection. `human_minutes` stays honestly null until M15.
- Worker-attribution note for tier metrics: M11 Steps 1/3 Codex; 2/5a Antigravity
  (Architect-reviewed; one value error and one hallucinated-API rework caught); 4/5b/6
  ARCHITECT at John's direction (role deviation recorded in the archived plan). A stale
  Codex BALL edit ("Step 4 closeout rerun blocked on approval budget") was superseded by
  the Architect completing Steps 4-6.

## Open for Architect
- (none)

## From Architect
- **Standing directions carried forward:** DEFERRED-REVIEW POLICY (proceed on green machine
  witnesses, queue human review, never assert human_confirmed); worker tiers + QC contract
  (full suite green is the commit floor; external-interface slices need a live probe or
  Architect-supplied ground truth); N-version escalation ladder (config-gated, build only on
  real disagreement volume); roadmap M11-M15 + output goal + distribution plan (canonical in
  engineering-plan and docs/distribution.md; PyPI alpha upload still awaits John's token);
  working directory = C:\Users\devbox\projects\tax_graph (AGENTS.md hard rule).
- **Seams M12 must respect (for the Architect writing PHASE_M12):** filled-PDF field
  mapping validates both directions like the oracle box map; blank-with-note for frontier
  lines on official forms; return-scoped output contract extends the Return Record pin
  (includes the `run` CLI diagnostics scoping observation from M10 close); the OTS input
  sidecar reuses the existing differential renderer; node-to-page geometry built here is
  reused by the M15 workbench.

## Latest verification
- M11 phase close (Architect, 2026-07-09) - ALL GREEN:
  - `pytest -q` -> 260 passed, 4 skipped; `pytest -m m11` -> 26 passed; ASCII OK
  - `validate 2025` / `build 2025` green; parity line 7 = 2000 (yaml + sqlite) and 250
  - Base-deps `uv run --no-dev`: run -> 2000; frontier -> 90.1% full / 100.0% in-scope
  - Live OTS fuzz seed 20260710 -> 100/100 agreed at line 16; `oracle replay-corpus` ->
    20 OK; `oracle pe-liability` live -> 20/20 (0 disagree, 0 fetch_error)
  - `verify parameter-diff` live -> 20/20; drills -> 13/13 caught incl.
    `wrong_bracket_value` / `wrong_standard_deduction` at L3
  - `verify record` -> VERIFICATION.md + 11 pages regenerated
  - Example run: taxable_income_basic computes line 15/16 with QDCGT worksheet trace

## Resolved / superseded
- M11 items: `plans/archive/PHASE_M11.md` (close note with role attribution) + git history.
- Pre-M11: `plans/archive/` phase plans and prior handoff snapshots.
