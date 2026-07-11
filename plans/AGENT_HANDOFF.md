# AGENT_HANDOFF.md

The single living doc for active Claude (Architect) <-> Codex (Worker) coordination. Update it in
place; do NOT spawn new per-topic note files. Standing rules: `../AGENTS.md`. Master plan:
`../docs/engineering-plan.md`.

## How to use
- **Worker:** raise questions/blocks under **Open for Architect**.
- **Architect:** answer there (and pin durable decisions into the relevant `PHASE_<id>.md`), then
  clear the item. Record active direction under **From Architect**.
- Keep it short - move resolved items to **Resolved** or delete them.
- History: pruned 2026-07-07, at M9 close 2026-07-08, at M11 close 2026-07-09, and at M12 close
  2026-07-10. Full narration lives in `plans/archive/` (phase plans with close notes) and git
  history.

## Current state (2026-07-11)

**BALL: WORKER.** M13 Step 4 corpus work is DONE and committed under John's Option B
(2026-07-11): the widened `m6_seed1315` corpus (100 scenarios: 98 live_ots + 2
IRS-adjudicated OTS SDTW-gate defects) is promoted over `examples/oracle_corpus`, the
stale 0706/0709/0711 batches are pruned, and `test_sidecar_m12` reads a dedicated
`tests/fixtures/sidecar_sample_facts.yaml`. The PolicyEngine liability witness is
RETIRED TO EXPLICIT-PENDING (2 skipped tests) as a NAMED GAP - definition-of-done in
PHASE_M13 Step 4 and "From Architect" below; do NOT claim dual-witness on the widened
domain until that gap closes. Proof: full `pytest -q` -> 294 passed, 6 skipped (7m36s);
corpus/PE/sidecar focused -> 13 passed, 2 skipped; `replay_corpus` 100/100; committed +
pushed, pushed-commit CI in flight. Remaining M13: the PE named gap + `verify
parameter-diff` HoH pin, then Step 5 (records/frontier/field maps/exit run). PyPI alpha
token still waits on John; serve-lifecycle hardening spin-off remains pending (independent).
(Whoever finishes a turn: update this BALL line - it is the first thing read.)

**M13 Step 1 (Codex, completed 2026-07-10):** stopped once on a genuine OTS
input-semantics mismatch (S1_21 is pre-worksheet in OTS, post-worksheet in our
graph - see the Architect ruling pinned in PHASE_M13 Step 1 and "Resolved"
below), then applied the ruling and closed clean: schedule-internal add-lines
chains land, S1 8z / S1A 2a re-admitted, S1_21 stays out with a named frontier
wall. Live `oracle fuzz --n 30 --seed 1301 --source yaml` -> 30/30 agreed.

**M13 Step 2 (Codex implementation + Architect finish, 2026-07-10):** Codex's
session hit its usage limit with Step 2 fully implemented but uncommitted
(Schedule D lines 6/14, the cited Capital Loss Carryover Worksheet, the Return
Record carryforward upgrade, field maps/geometry/drills/docs) - same pattern as
M12's Step-3 stop. Architect (Claude Sonnet 5) verified the work before
committing: worksheet arithmetic cross-checked line-by-line against the cached
IRS instructions text (`.cache/raw/2025/instructions_schedule_d_2025.txt`,
lines 625-650) and citations confirmed verbatim - both correct. Found and fixed
two defects during verification, not present in Codex's own targeted runs
because they only surface via full-suite / cross-fixture interaction:
1. `tax_graph/verify/properties.py::_carryover_worksheet_issues` (new in Step
   2) called `Engine(graph).execute(...)` with no exception handling, unlike
   the sibling sampled-facts loop three lines below it that does. A pre-
   existing M9 drill (`retarget_outbound_flow_line_off`) legitimately produces
   a structurally invalid mutated graph as its whole POINT (proving the
   mismatch gets caught) - the new check's uncaught exception crashed the
   entire drill-catalog test instead of being recorded as a finding. Fixed:
   wrapped in the same try/except pattern, converting to a `PropertyIssue`.
2. Same function hard-coded full-1040-graph node IDs with no existence guard
   (unlike `_parameter_value_issues`'s established `if not node: continue`
   pattern) - it ran unconditionally inside `check_graph_properties`, which
   fires during single-document extraction/routing checks (M4/M9 tests) whose
   narrow test graphs never load the Schedule D worksheet chain, so it
   false-positived "worksheet value None != 4000" on graphs that were never
   supposed to have that worksheet in the first place. Fixed: guard on all
   required node IDs being present in `graph.nodes` before executing.
   Also found (independent, pre-existing since before this session): a test
   in `test_return_record_m5.py` had lost its `def` header at some earlier
   point in history - the `with pytest.raises("unknown option_id")` body sat
   as dead code after a `return` statement inside `_capital_loss_record()`,
   so `validate_decision_resolutions`'s bad-option-id branch was never
   exercised. Restored as its own test,
   `test_decision_resolution_rejects_unknown_option_id`; confirmed it passes
   against current code (the underlying validation was never actually wrong,
   just untested).
Verification after both fixes: `pytest -m m13` -> 2 passed; `validate 2025`
green (340 nodes, 257 citations); ASCII OK; full `pytest -q` -> 285 passed, 4
skipped in 6m01s (up from 283/4, net +2 for the resurrected test and the new
Step 2 tests minus none lost). Live OTS/PE gate for the carryover domain is
Step 4's job per the plan, not Step 2's - not yet run.

**M13 Step 3 (Architect implementation + Codex verification, 2026-07-11):**
Implemented the cited 47-line Schedule D Tax Worksheet, line-17/20 routing,
input-backed lines 18/19, and the `non_sdtw_tax` wrapper around the existing
QDCGT/regular chain. Retired the line-20 wall; declared the 28-percent-rate and
unrecaptured-section-1250 feeder worksheets as named walls; updated field maps,
geometry, frontier, queue, docs, drills, and old-wall tests. Deviation from the
original OTS-based design: IRS text cross-check proved OTS inverts gate2 and has
a 197390/197300 threshold defect, so OTS is not a witness for nonzero 18/19
scenarios; John reported both defects to the maintainer. Local verification:
four hand-traced IRS scenarios execute correctly; `pytest -m m13` -> 8 passed;
updated wall/frontier/validator/drill selection -> 21 passed; `validate 2025`
and ASCII green; full `pytest -q` -> 291 passed, 4 skipped in 7m22s. Step 4 owns
the revised live-oracle domain and corpus work.

**M13 Step 4 (Codex active, 2026-07-11):** User authorized live OTS runs despite
known Schedule D defects, with triage retained rather than suppressed. Baseline
`oracle fuzz --n 100 --seed 1314 --source yaml` initially returned 98 agreed / 2
disagreed, both only Form 1040 line-16 half-dollar comparisons (Tax Graph whole
dollar 10163/56353 versus OTS 10162.5/56352.5). Root cause was the differ using
Python banker's rounding; local fix changes it to IRS half-up rounding, with a
unit test. Re-run after the fix: 100 agreed / 0 disagreed / 0 rejected. Direct
OTS probes establish the widened-input convention: OTS positive `D6` / `D14`
maps to Tax Graph negative Schedule D facts; both probes agree at line 16 = 3515.
The explicit nonzero-line-19 repro confirms the documented OTS defect exactly:
Tax Graph / IRS line 16 = 57523, OTS = 55023, with OTS accepting `D19=10000`.
Next: extend the domain renderer with per-side sign transforms for D6/D14 and
add D19/Collectibles coverage; preserve nonzero SDTW disagreements in triage.
Completed the widened run: `oracle fuzz --n 100 --seed 1315 --source yaml` ->
98 agreed / 2 disagreed / 0 rejected. Both disagreements are Form 1040 line 16
with nonzero line 18 AND line 19, matching the known OTS gate defect:
`m6_seed1315_0022` Tax Graph 72938 versus OTS 71923.95 (Collectibles 26282,
D19 25187), and `m6_seed1315_0072` Tax Graph 154907 versus OTS 152767.73
(Collectibles 28792, D19 4101). Triage is retained under
`.cache/m13_step4_ots_widened/triage.yaml`; no disagreement has been frozen or
silently excluded. User direction: continue running OTS and deal with known
Schedule D failures transparently.
Independent-witness checks: the pinned offline PE liability replay is green
(20/20: 8 exact, 12 documented tax-table-tolerance). Live PolicyEngine is not
installed in this environment. The pinned offline parameter fixture is 19/20:
only `form_1040_2025_brackets_hoh` differs. Tax Graph carries the cited 2025
head-of-household top bracket floor 626350; the fixture carries 375800. Do not
alter the cited graph parameter without source review - triage the PE fixture /
upstream parameter separately in Step 4.
Step 4 completion work added the D6/D14 sign transforms, D18/D19 domain inputs,
conditional output box mappings and inventory entries, IRS half-up oracle
rounding, and two offline OTS differ fixtures. The carryover fixture agrees;
the SDTW fixture intentionally records the verified OTS gate defect. Focused
oracle/domain/box-map tests -> 24 passed, 1 skipped; `pytest -m m13` -> 10
passed; ASCII green. Re-ran the live widened gate after the completed box map:
`oracle fuzz --n 100 --seed 1315 --source yaml` -> 98 agreed / 2 disagreed /
0 rejected. Both remaining disagreements are line 16 only, with nonzero 18 and
19, and remain in `output/oracle_fuzz/2025_seed1315/triage.yaml`; a first map
attempt surfaced 92 missing D19 labels on non-SDTW paths and was corrected by
making that output mapping conditional on `schedule_d_2025_sdtw_applies`.
**John selected corpus option 2 (2026-07-11):** the freeze command now requires
the explicit `--adjudicate-known-ots-sdtw-defects` flag before it can retain the
two source-verified OTS defects. Each such corpus entry records
`status: disagreed`, disposition `ots_sdtw_gate_defect_2026_07_11`, and expected
source `irs_adjudicated_schedule_d_tax_worksheet`; expected values use Tax Graph
only for the disagreement and preserve live OTS values for agreeing boxes. A
temporary 100-scenario freeze/replay is green: 98 `live_ots` entries + 2 explicit
adjudications, replay 100/100. Focused corpus/differ/domain/box-map tests -> 32
passed, 1 skipped. The temporary corpus is deliberately not yet promoted over
`examples/oracle_corpus`: doing so would invalidate the old ID-keyed offline PE
fixture before live PE results are available.
**Live PE attempt (2026-07-11):** John authorized the requested run. Installed
the pinned `policyengine-us` 1.768.3 into a short temporary path because Windows
long-path handling prevents its wheel from landing in `.venv`; the temporary
runtime imported and ran. Over the temporary 100-case corpus, live PE returned
6 exact/tolerance agreements, 94 disagreements, and 0 fetch errors. Every
reported disagreement begins with taxable-income mismatch. This is not evidence
to freeze a PE fixture: `scenario_inputs_from_facts` currently renders only
wages, taxable interest, dividends, and 8949 gains, but the widened corpus also
varies S1/S1-A, Schedule A, carryovers, and SDTW inputs. The live run therefore
reveals an incomplete PE input adapter, not a trustworthy graph verdict.

- **M0-M12 are COMPLETE and archived** (see `plans/archive/`, each with a close note).
- **THE GRAPH COMPUTES TAX AND FILES IT.** M11 landed line 16 liability under dual live
  witnesses (OTS + PolicyEngine). M12 landed the output layer: filled official IRS PDFs
  (node -> AcroForm field map, validated both directions), the OTS input sidecar (now
  using the real OTS-shipped template when OTS is installed locally, generic fallback
  otherwise), the return-scoped output contract (every session artifact - filled forms,
  sidecar, Return Record, audit trace, run diagnostics - lands under one
  `output/returns/<return_id>/` root, never into `graph/<year>/`), and the node-to-page
  geometry projection the M15 workbench will consume.
- **M12 finding (worth carrying forward):** the OTS sidecar's real-template
  auto-resolution and the generic fallback template's semicolon-terminator bug were both
  invisible to the offline test suite - the offline goldens were internally consistent
  with a template real OTS cannot parse. Only running the real `taxsolve_US_1040_2025.exe`
  against a freshly emitted sidecar caught it. Same class of gap as M11's premature-
  rounding bug: **offline-green is not sufficient proof for output-layer artifacts a
  real user or a real external tool will consume; a live execution pass belongs in the
  exit criteria whenever a phase's job is "hand something to the outside world."**
- **Resolved 2026-07-10 (post-close):** the `build 2025` file lock is cleared. The four
  stale `tax-graph serve` MCP processes (two reconnect-orphaned pairs, per-process
  parentage confirmed via `Get-CimInstance`) were killed at John's direction; `build`
  re-ran clean (317 nodes, 251 citations) and both parity examples (line 7 = 2000 and
  250) reconfirmed against the fresh sqlite. If this recurs, check for orphaned
  `uv run python -m tax_graph.cli serve` processes before assuming a content bug.
- **CI CORRECTION (2026-07-10, found via John's failure email):** GitHub CI had been
  RED on every push since M9 close (2026-07-06, ~30 runs) - tests copied fixture data
  from the gitignored `graph/2025/_drafts/`, which exists only as local extraction
  state, so a clean checkout failed 10 tests in setup; plus M12's new sqlite-source
  test assumed a prebuilt `build/tax_graph_2025.sqlite` CI never builds. Consequence:
  every "full pytest green" claim in the M9-M12 close notes was true only in the dev
  sandbox and was never verified against a clean checkout. Fixed in `df8e3b8`: frozen
  minimal draft snapshots committed under `tests/fixtures/draft_snapshots/` (fixtures
  for mechanics, not promotion sources; drafts-never-committed rule unchanged), test
  helpers repointed, and the sqlite test now builds its own tmp artifact. Proof: full
  pytest with `_drafts` and the prebuilt sqlite renamed away -> 282 passed, 4 skipped.
  **Standing rule addition: no test may read `graph/<year>/_drafts/` or assume a
  prebuilt `build/` artifact; phase close-outs must confirm the CI run on the pushed
  commit is green, not just the local suite.**
- **Dual-witness state (unchanged from M11):** live OTS fuzz 100/100 at the tax line;
  PolicyEngine liability 20/20 (8 exact, 12 within the documented tax-table tolerance)
  and parameter-diff 20/20.
- **Named walls (frontier-declared, unchanged - M12 did not move modeled-math
  coverage):** 1040 line 13a QBI, 1040 lines 17-24 credits/total-tax chain incl. AMT,
  Schedule D line 20 QDCGT-worksheet branch. Coverage 90.1% full / 100.0% in-scope.
- **Deferred to M13 (pinned in oracles/domain_2025.yaml):** S1/S1A/Schedule-A supplemental
  fuzz inputs are out of the live domain until the schedule-internal "Add lines" chains are
  modeled - OTS aggregates them into AGI/line 13b; our graph does not yet.
- **Review queue:** M10/M11 promotion entries plus M12's 11 field_map_review entries
  (high priority, pending, human_confirmed: false) plus the QDCGT worksheet (high) and
  the deduction decision node (TOP priority). `human_minutes` stays honestly null until
  M15.
- **Year rollover (TY2026):** pinned in engineering-plan.md; delta workflow + named
  unbuilt seams (cross-year identity mapping, tier inheritance, manifest templating,
  witness re-pinning). Sequenced after M15 or when TY2026 docs drop, whichever is later.
- Worker-attribution note for tier metrics: M12 Steps 1-3 Codex (Steps 4-5 implemented
  in the same Codex worktree session but its commit was blocked by a usage-limit reset
  mid-Step-3); Step 6 plus finishing/committing Steps 3-5 and the OTS template bug fix
  ARCHITECT (Claude Sonnet 5) at John's direction after the Codex session hit its 5-hour
  limit (role deviation, M8/M11-close precedent, recorded in the archived plan).

## Open for Architect
- (none) - the M13 Step 4 PE-evidence decision is RESOLVED (John chose Option B,
  2026-07-11): promote the widened corpus under OTS + IRS adjudication and retire the
  PolicyEngine liability witness to explicit-pending as a named gap, rather than keep
  the old narrow PE corpus as a parallel witness. See "From Architect" below and the
  PHASE_M13 Step 4 pin for the definition-of-done.

## From Architect
- **DECISION - M13 Step 4 corpus promotion + PE witness (John, 2026-07-11, Option B;
  pinned in PHASE_M13 Step 4):** the widened `m6_seed1315` corpus (100 scenarios: 98
  `live_ots` + 2 IRS-adjudicated OTS SDTW-gate defects) is promoted over
  `examples/oracle_corpus`; stale 0706/0709/0711 batches pruned; `test_sidecar_m12`
  now reads `tests/fixtures/sidecar_sample_facts.yaml`. The PolicyEngine liability
  witness is RETIRED TO EXPLICIT-PENDING (two `@pytest.mark.skip` tests in
  `tests/test_pe_liability_m11.py`), NOT kept on the old corpus. **NAMED GAP (gates any
  future dual-witness-on-widened-domain claim):** widen `scenario_inputs_from_facts`
  (`pe_liability.py`) to render S1 / Schedule A / D6 / D14 / SDTW-18-19 inputs -> live
  `policyengine-us` run over `m6_seed1315` (blocked here by Windows long-path wheel
  install) -> refreeze `pe_liability_2025.json` on seed1315 IDs -> re-enable the two
  skipped tests. Until then OTS + IRS adjudication is the sole live witness for the
  widened Schedule D domain, and the parameter-diff HoH floor (626350 vs 375800) stays
  pinned for separate source review. The old `pe_liability_2025.json` is left in place
  (unused) as the schema template for the refreeze - delete if preferred.
- **ANSWERED - M13 Step 1 S1_21 ruling (2026-07-10), pinned in PHASE_M13 Step 1:**
  option (a), refined. Architect verified the shipped source: OTS's `S1_21` box is
  PRE-worksheet "interest paid" (`Calc_StudentLoan_Sched1L21()` applies the $2,500
  cap + $85k/$170k MAGI phase-out and replaces the value); our line 21 node is the
  POST-worksheet deduction - a semantic mismatch, not a rounding or defect issue.
  Also verified: `S1_8z` and `S1A_2a` injections ARE honored verbatim (the S1A_2a
  `GetLineF` inside `sched_1A()` is commented out, but the caller parses it at the
  `get_parameter` site), so BOTH stay re-admitted; your diagnosis that all 20
  disagreements were S1_21 is consistent with source. Do: drop S1_21 from the
  domain/box map; add the Student Loan Interest Deduction Worksheet as a named
  frontier wall with a queue entry; add an offline L4 example fixture with nonzero
  line 21 locking the line-25/26 chain; record the injection-contract rule in the
  domain YAML note (boxes enter the live domain only after a source/probe check that
  OTS honors direct injection; OTS-recomputed boxes require semantic alignment
  first). The 30-scenario gate applies to the re-admitted set (8z, 2a). Full text +
  the pre-approved future worksheet slice (incl. DIVIDE op shape): PHASE_M13 Step 1.
- **Full-suite runtime note for Codex:** `pytest -q` legitimately takes ~5.5 minutes
  (287 tests); your two 124-second terminations were a sandbox timeout, not a hang.
  Run with a >= 600s command timeout, or split the suite into halves and record both
  results. The commit floor (full suite green) is unchanged.
- **Standing directions carried forward:** DEFERRED-REVIEW POLICY (proceed on green machine
  witnesses, queue human review, never assert human_confirmed); worker tiers + QC contract
  (full suite green is the commit floor; external-interface slices need a live probe or
  Architect-supplied ground truth); N-version escalation ladder (config-gated, build only on
  real disagreement volume); roadmap M11-M15 + output goal + distribution plan (canonical in
  engineering-plan and docs/distribution.md; PyPI alpha upload still awaits John's token);
  working directory = C:\Users\devbox\projects\tax_graph (AGENTS.md hard rule); **a phase
  whose job is producing artifacts an outside tool/user consumes needs a real live-execution
  pass in its exit criteria, not just offline goldens** (M12 finding above); **no test may
  read `graph/<year>/_drafts/` or assume a prebuilt `build/` artifact - use
  `tests/fixtures/draft_snapshots/` and build throwaway sqlite in tmp; phase close-outs
  confirm the pushed commit's CI run is green, not just the local suite** (CI correction
  above).
- **Seams M13 must respect (for the Architect writing PHASE_M13):** worksheet
  extraction/authoring pattern generalizes from M11's hand-authored QDCGT precedent;
  re-admitting S1/S1A/Schedule-A supplemental fuzz inputs requires modeling the
  schedule-internal "Add lines" chains OTS already aggregates into AGI/line 13b; the
  field-map/geometry artifacts M12 built are additive and should extend cleanly to any
  newly-modeled lines (new nodes need field-map entries or explicit exclusions, per the
  M12 completeness guardrail already wired into `validate`).

## Latest verification
- M12 phase close (Architect, Claude Sonnet 5, 2026-07-10) - GREEN (one known gap noted):
  - `pytest -q` -> 281 passed, 4 skipped; `pytest -m m12` -> 22 passed; ASCII OK
  - `validate 2025` green (field-map + node-geometry validation both wired in)
  - Base-deps `uv run --no-dev`: `validate` green; `run` (yaml) line 7 = 2000; `run`
    (sqlite) line 7 = 2000; `frontier` -> 90.1% full / 100.0% in-scope (unchanged)
  - `build 2025` blocked by MCP server file lock (see "Known gap" above) - not a content
    regression; parity confirmed against the existing sqlite build instead
  - Parity: capital_gains_basic line 7 = 2000 (yaml + sqlite); capital_gains_multi_lot
    line 7 = 250 (yaml + sqlite)
  - End-to-end: `tax-graph run --export-bundle` on taxable_income_basic produced filled
    1040 + 5 schedules, OTS sidecar, Return Record, audit trace, run.json all under one
    return-scoped root; frontier lines (13a QBI, 17-24, Sched D line 20) blank AND listed
    in both the Return Record and run.json
  - Node geometry: `resolve_node_geometry` for `form_1040_2025_root_line_16` resolves to
    a real page 2 rect
  - Gated live: `taxsolve_US_1040_2025.exe` run directly against a freshly emitted
    sidecar (after the template fix) -> L22/L24 = 13777.00, agrees exactly with our
    computed line 16 (13777)
  - `verify record` -> VERIFICATION.md + 11 pages regenerated byte-stable (no diff)
- M11 phase close (Architect, 2026-07-09) - ALL GREEN: see `plans/archive/PHASE_M11.md`.

## Resolved / superseded
- M12 items: `plans/archive/PHASE_M12.md` (close note with role attribution) + git history.
- M11 items: `plans/archive/PHASE_M11.md` (close note with role attribution) + git history.
- Pre-M11: `plans/archive/` phase plans and prior handoff snapshots.
