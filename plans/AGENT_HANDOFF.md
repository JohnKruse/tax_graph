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

## Current state (2026-07-10)

**BALL: WORKER.** M13 Step 1 is COMPLETE locally and ready to commit: Schedule 1,
Schedule 1-A, and Schedule A add-lines chains now compute; 8z/2a are re-admitted
under the pinned injection contract; direct S1_21 is a declared worksheet wall with an
offline L4 chain witness. Next action: M13 Step 2 (Capital Loss Carryover Worksheet).
PyPI alpha token still waits on John; serve-lifecycle hardening spin-off still pending
(independent).
(Whoever finishes a turn: update this BALL line - it is the first thing read.)

**M13 active - STOPPED in Step 1 (2026-07-10):** Worker implemented the Schedule 1
and Schedule A add-lines chains locally, restored S1 8z / S1 21 / S1-A 2a to the
oracle domain and box map, and added hermetic M13 coverage. Targeted verification is
green (`pytest -m m13`: 1 passed; related regression selection: 18 passed, 1 skipped;
ASCII green). The required live OTS short gate is NOT green: `oracle fuzz --n 30
--seed 1301 --source yaml` -> 10 agreed / 20 disagreed, triage at
`.cache/m13_step1_ots/triage.yaml` (uncommitted cache). The disagreement is exactly
each nonzero `S1_21`: Tax Graph subtracts it in Schedule 1 line 26, while the shipped
OTS source `src/taxsolve_US_1040_2025.c` reads `S1_21` and then calls
`Calc_StudentLoan_Sched1L21()`, overwriting the injected direct-line amount with its
own calculated zero. Example scenario 0000: TG line 11b 115517 versus OTS 115766,
delta 249 = S1_21. This is an external-oracle input-semantics defect, not a rounding
delta. No Step 1 commit was made; working-tree implementation changes remain for the
Architect's decision. The two full `pytest -q` attempts exceeded 124 seconds without
printing a failure and were terminated; collected suite size is 287.

**M13 Step 1 complete (2026-07-10):** Applied the Architect ruling: removed S1_21
from `oracles/domain_2025.yaml` and `box_map_2025.yaml`; re-admitted S1 8z and S1-A
2a; added the named Student Loan Interest Deduction Worksheet frontier, deferred-review
entry, and offline L4 line-25/26 regression. The domain YAML records the durable direct
injection contract. Verification: `pytest -m m13` -> 1 passed; related regressions ->
28 passed; `validate 2025` and ASCII green; aligned live `oracle fuzz --n 30 --seed
1301 --source yaml` -> 30 agreed / 0 disagreed / 0 rejected; full `pytest -q` -> 283
passed, 4 skipped in 5m30s. The pre-ruling triage remains uncommitted under `.cache/`.

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
- (none)

## From Architect
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
