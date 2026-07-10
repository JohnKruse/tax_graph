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

**BALL: ARCHITECT.** M12 (Output layer, canary Paper Trail) is CLOSED and archived. Next action:
write PHASE_M13 (Worksheet depth, canary Deep Ledger) just-in-time on John's go. Nothing waits on
a worker; nothing waits on John except the PyPI alpha token.
(Whoever finishes a turn: update this BALL line - it is the first thing read.)

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
- **Known gap, non-blocking:** `tax-graph build 2025` could not be re-run at M12 close -
  four `tax-graph serve` MCP processes already running in this dev environment hold
  `build/tax_graph_2025.sqlite` open, and Windows blocks the delete-and-replace `build`
  needs. Content is unaffected (M12 added no graph nodes/rules); both parity examples
  (line 7 = 2000 and 250) were confirmed against the existing sqlite build. Whoever next
  needs a fresh `build` should either restart those MCP server processes first or run
  from an environment without them attached.
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
- **Standing directions carried forward:** DEFERRED-REVIEW POLICY (proceed on green machine
  witnesses, queue human review, never assert human_confirmed); worker tiers + QC contract
  (full suite green is the commit floor; external-interface slices need a live probe or
  Architect-supplied ground truth); N-version escalation ladder (config-gated, build only on
  real disagreement volume); roadmap M11-M15 + output goal + distribution plan (canonical in
  engineering-plan and docs/distribution.md; PyPI alpha upload still awaits John's token);
  working directory = C:\Users\devbox\projects\tax_graph (AGENTS.md hard rule); **a phase
  whose job is producing artifacts an outside tool/user consumes needs a real live-execution
  pass in its exit criteria, not just offline goldens** (M12 finding above).
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
