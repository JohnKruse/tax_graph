# PHASE M11 - First liability branch   [COMPLETE]

**Closed 2026-07-09 by the Architect.** ROLE DEVIATION NOTE (M8-close precedent): Steps
4, 5b, and 6 were completed by the ARCHITECT at John's explicit direction after Codex
ran out of tokens mid-Step-4; Steps 2 and 5a ran on Antigravity under per-slice
authorizations with line-by-line Architect review; Steps 1 and 3 were Codex. Close-out:
full pytest 260 passed / 4 skipped; pytest -m m11 26 passed; ASCII OK; validate/build
green; base-deps run + frontier green; parity 2000/250 unchanged. LIVE GATES: OTS fuzz
100/100 AGREED AT THE TAX LINE (seed 20260710; wages, all five filing statuses, QDCGT
breakpoints, the 100k table/formula boundary); corpus re-frozen seed 20260711 with
live_ots_diff_report provenance; PolicyEngine liability 20/20 (8 exact, 12 within the
documented tax-table tolerance) plus parameter-diff 20/20. Notable findings during the
phase: OTS carries cents so whole-dollar rounding happens ONCE at line 16
(lookup_bracket_tax now carries cents); S1/S1A/Schedule-A supplemental fuzz inputs left
the live domain until M13 models the schedule-internal Add-lines chains (pinned in
oracles/domain_2025.yaml + box_map notes); new walls DECLARED in the frontier: 1040
line 13a QBI and the lines 17-24 total-tax chain (incl. AMT).

**Canary:** Rate Ladder
**Depends on:** M10 (batch surface promoted; Schedules 1/1-A/2/3/A/B + 6251 live), M9
(parameter nodes + LOOKUP_TABLE precedent, LINK), M8 (verification net), M6 (live OTS
witness; the harness already renders 1040 inputs).
**Goal:** The graph computes a TAX NUMBER. Extract/promote the Form 1040
income-to-taxable-income spine, land the year's core parameter tables (standard
deduction, brackets, QDCGT thresholds, the under-$100k tax table as a compiled data
resource), author the QDCGT worksheet as the project's first worksheet-shaped subunit,
and compute **Form 1040 line 16** for the supported profile. OTS witnesses the tax line
live; **PolicyEngine joins as the second witness** (the liability-level channel pinned in
`docs/oracle-strategy.md`). Roadmap context: engineering-plan "Roadmap M11-M15".

## Why
Everything so far moves numbers BETWEEN forms; nothing yet answers "what do I owe."
Line 16 is where capital-gains preferential rates actually apply (the QDCGT worksheet),
so for this project's core use case the liability branch IS the payoff. It also
activates the second independent witness (PolicyEngine), which only becomes meaningful
at liability level.

## Supported profile (the modeled branch; everything else is a wall)
All five filing statuses; income from wages (input), interest/ordinary+qualified
dividends (Schedule B / inputs), capital gains (D/8949), and the modeled Schedule 1
lines; **standard deduction OR itemized via the existing Schedule A total, chosen by a
DECISION node** (decisions get top-priority queue entries); taxable income >= 0 path and
the zero-floor. NOT in scope (explicit frontier walls with typed `unresolved` traces):
QBI (line 13), credits/other-taxes/total-tax chain (lines 17-24), AMT computation
(6251 stays structural), additional worksheets behind line 15 edge cases.

## Guardrails (do not drift)
- **Parameters are nodes; bulk tables are data resources** (engineering-plan "Parameters
  and thresholds"). Standard deduction, bracket tables, and QDCGT breakpoints enter as
  cited `parameter` nodes / LOOKUP data with per-value citations from the 2025
  instructions. The under-$100k tax table compiles as a DATA RESOURCE (never per-row
  nodes). No inline magic numbers - the L0 drill applies.
- **New engine ops: ONLY what this branch needs.** Expected minimum: `MULTIPLY`,
  `LOOKUP_BRACKET`, and one conditional (`IF_ELSE` or the narrowest equivalent the
  worksheet requires - worker pins the exact shape with the Architect if it grows
  beyond these three). Current vocabulary: COPY/SUM/SUBTRACT/NEGATE/MIN/MAX/LOOKUP_TABLE.
- **The QDCGT worksheet is hand-AUTHORED this phase, cited per line** from the Form 1040
  instructions (the outline-first extractor was built for forms, not worksheet prose;
  generalizing worksheet extraction is M13's job). Authored objects carry honest
  human-authored provenance and their own deferred-review queue entries.
- **Whole-dollar exact agreement with OTS at the tax line.** The tax table (<$100k) and
  the bracket formula (>=$100k) must switch exactly where the IRS switches - OTS
  agreement across that boundary is the proof.
- **Deferred-review policy in force** (AGENT_HANDOFF pin): promotions and authored
  worksheet subunits proceed machine-gated with queue entries; no blocking human stop;
  no agent ever writes `human_confirmed: true`.
- **Runtime stays base-deps light:** PolicyEngine lives behind an extras group, never
  base; offline tests use canned fixtures.
- Unchanged law: ASCII; additive schemas; drafts never committed; live graph closed;
  worker tiers + QC contract (full suite green is the commit floor).

## Exit criteria (must pass 100%)
- `pytest -m m11` green (offline/deterministic); full `pytest` green; ASCII OK;
  base-deps `validate`/`build`/`run`/`frontier` work.
- A supported-profile scenario computes line 15 taxable income and line 16 tax through
  cited parameter nodes and the QDCGT worksheet trace; a non-QDCGT scenario computes
  line 16 via the tax table / bracket path; parity examples unchanged (line 7 = 2000 /
  250).
- Gated live OTS fuzz: >= 100 scenarios over the widened domain (wages + filing
  statuses + incomes straddling the QDCGT breakpoints AND the $100k table/formula
  boundary) agree AT THE TAX LINE or are triaged - zero silent; corpus re-frozen with
  `live_ots_diff_report` provenance.
- PolicyEngine witness: liability-level agreement on the frozen corpus (or explicit
  triage dispositions); parameter-value diff of our parameter nodes against
  policyengine-us parameter data recorded (the cheap channel from oracle-strategy).
- Drill catalog gains and catches `wrong_bracket_value` and
  `wrong_standard_deduction` mutations (expected layer attributed).
- Verification records regenerated byte-stable; frontier updated (new walls named);
  deferred-review queue entries for the 1040 promotion, the worksheet subunit, and the
  deduction decision node.

## Steps

- [ ] **Step 1 [worker-heavy] - 1040 spine extraction + promotion.** Extract
  `form_1040_2025` under the full net (artifacts already acquired in M10); promote the
  income-to-taxable-income spine - wages/income lines feeding line 9 total, line 10
  adjustments (from Schedule 1 line 25 as modeled), line 11 AGI, line 12 deduction,
  line 14, line 15 taxable income (zero-floored via MAX) - replacing the hand-authored
  1040 slice while PRESERVING line 7 semantics (M6b/M9 promotion precedent). LINK
  realizes the schedule totals into their 1040 lines (Schedule 1 -> 8/10, Schedule B ->
  2b/3b). Line 13 QBI and lines 16+ stay walls this step. Queue entries per promotion.
  Test: spine computes taxable income for a wages+gains fixture on yaml AND sqlite;
  parity unchanged; frontier flips for newly modeled lines. Docs.

- [x] **Step 2 [worker-standard] - Parameter tables + data-resource tax table.** Cited
  `parameter` nodes for the 2025 standard deduction (by filing status) and QDCGT
  breakpoints; bracket tables per filing status as LOOKUP_BRACKET data; the under-$100k
  tax table compiled from the official 1040 instructions table into a DATA RESOURCE
  (schema + compiler + SQLite projection, additive). Citations carry the instruction
  page/line provenance. Drills: `wrong_bracket_value`, `wrong_standard_deduction`
  added to the catalog with expected catching layer. Test: parameter lookups by filing
  status; table lookup matches published table cells at boundary incomes; drills
  caught. Docs.

- [ ] **Step 3 [worker-heavy] - Engine ops + QDCGT worksheet subunit + line 16.** Add
  the minimum ops (`MULTIPLY`, `LOOKUP_BRACKET`, one conditional); author the QDCGT
  worksheet as a worksheet-shaped subunit with per-line citations; line 12 deduction
  becomes a DECISION node (standard vs itemized via the Schedule A total path); line 16
  = worksheet result when the worksheet applies, else tax table (<$100k) / bracket
  formula (>=$100k). Absent inputs stay missing-input; the zero-floor uses MAX. Test:
  a qualified-dividends + LT-gain fixture reproduces the worksheet arithmetic line by
  line in the trace with parameter citations; a wages-only fixture takes the
  table path; the boundary income takes the right path on both sides. Docs.

- [ ] **Step 4 [worker-standard] - Oracle widening to the tax line.** Box map adds the
  OTS labels for AGI/deduction/taxable-income/tax (per the committed label inventory);
  domain adds wages, all filing statuses, and income ranges straddling every QDCGT
  breakpoint and the $100k boundary; retire/convert any canary this obsoletes. Gated:
  live >= 100 fuzz agrees at the tax line or triages; re-freeze a corpus batch
  (live-diff provenance only). Offline: renderer goldens + differ fixtures for a QDCGT
  scenario and a table-path scenario. Docs.

- [ ] **Step 5 [worker-standard] - PolicyEngine second witness.** Adapter behind a new
  extras group: render our frozen corpus scenarios into policyengine-us household
  inputs, diff liability-level results (whole-dollar), shared triage discipline with
  the OTS channel (disagreements never pass silently). Plus the cheap channel:
  diff our `parameter` node values against policyengine-us parameter YAML and record
  the comparison. Offline tests: canned PE fixtures; live runs gated on the extra
  being installed. Test: corpus scenarios agree or carry dispositions; a seeded wrong
  parameter is flagged by the parameter diff. Docs: install + gating.

- [ ] **Step 6 [worker-light] - Records, frontier, exit run.** Regenerate
  `VERIFICATION.md` + per-form pages (byte-stable); rebuild frontier (new walls named:
  QBI, 17-24, AMT); run every exit-criteria command; record results + any honest-null
  cost fields in the handoff; update the BALL line. NOT authorized: edits outside
  generated records, docs, and the handoff.

When all steps are `[DONE]`: mark `[COMPLETE]`, archive to `plans/archive/`, prune
`plans/AGENT_HANDOFF.md`, single `git push`, tell John. Next per the pinned roadmap:
M12 (Output layer, canary Paper Trail) - plan written just-in-time.
