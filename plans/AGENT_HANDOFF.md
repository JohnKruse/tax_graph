# AGENT_HANDOFF.md

The single living doc for active Claude (Architect) <-> Codex (Worker) coordination. Update it in
place; do NOT spawn new per-topic note files. Standing rules: `../AGENTS.md`. Master plan:
`../docs/engineering-plan.md`.

## How to use
- **Worker:** raise questions/blocks under **Open for Architect**.
- **Architect:** answer there (and pin durable decisions into the relevant `PHASE_<id>.md`), then
  clear the item. Record active direction under **From Architect**.
- Keep it short - move resolved items to **Resolved** or delete them.
- History: this file was pruned 2026-07-07 (token-cost hygiene). The full pre-prune version,
  including all M0-M8 step narration, superseded directions, and old verification logs, is
  archived at `plans/archive/AGENT_HANDOFF_2026-07-07_full.md`. Archived phase plans live in
  `plans/archive/PHASE_*.md`.

## Current state (2026-07-07)
- **M0-M8 and M6b are COMPLETE and archived** (see `plans/archive/`). Highlights that still
  matter operationally: compiled SQLite + YAML parity; MCP server (M2 behavioral contract);
  Return Record (M5); live-OTS differential harness + frozen corpus (M6, provenance
  `live_ots_diff_report` only); repeatable tables with `#row_key` runtime instances (M6b);
  frontier registry + SOI-weighted coverage (M7, ~42.4% filer-weighted); verification ladder
  with drill gate, trust tiers T0-T3, calibration sampling, N-version, metrics.yaml (M8 -
  drill gate green UNLOCKS bulk extraction).
- **M9 (Schedule D + LINK + Verification Record, canary Daisy Chain) is the active phase.**
  `plans/PHASE_M9.md`. Steps 1-4 are `[DONE]` and committed (5633f18, 1a22613, 0665551,
  b9052bb):
  - Step 1: Schedule D form/instructions acquired + rendered; fixture slices committed.
    Known issue parked: the `form_1099b_2025` manifest URL 404s (see the worker-light trial
    errand below).
  - Step 2: Schedule D extraction under the full net: accepted=75, review=0, issues=0,
    calibration sample 8; N-version agreed 0 diffs. Worked-example mining reported 10/10
    unmappable (OpenRouter verifier endpoint rejected the structured-output parameters) - no
    fixtures frozen; revisit the verifier endpoint config later.
  - Step 3: first live `parameter` nodes (line 21 loss limit 3000/1500 MFS, cited),
    filing-status fact, `LOOKUP_TABLE`/`NEGATE`/`MAX` ops, wrong-parameter drill, deferred
    line 20 declared via `graph/2025/frontier-declarations.yaml` with a typed `unresolved`
    trace.
  - Step 4: John approved the promotion gate. `tax-graph link` realizes reviewed outbound
    declarations into FEEDS edges against the promoted index; Schedule D 1b/2/3/8b/9/10
    promoted; frontier flipped to modeled (only line 20 remains declared). Supported
    computation intentionally sums line 1b into line 7 and line 8b into line 15 (one table
    per part); category rows 2/3/9/10 linked but not yet downstream addends.
- **Step 5 [worker-standard] is IN FLIGHT with uncommitted work in the tree** (oracle box
  map/domain/scenario/diff modules + their tests). Widen the oracle domain: short-term lots,
  losses beyond $3000 in-domain via line 21, retire the old out-of-domain canary for a line 21
  agreement test, >=100 live fuzz gate, re-freeze corpus (live-diff provenance only).
- **Step 6 [worker-standard] pending:** generated `VERIFICATION.md` + per-form pages + MCP
  exposure; byte-stable regeneration; witness absences stated plainly. Design:
  `docs/extraction-verification.md` Section 10. Also run the still-pending live N-version
  exit item during Step 6's exit pass if not already done.
- Phase close checklist (after Step 6): mark `[COMPLETE]`, archive the plan, prune this file
  again per the seam-hygiene rule, single `git push`, tell John. NOTE: local main is several
  commits ahead of origin - the push is overdue at phase close.

## Open for Architect
- (none)

## From Architect
- **NEW (2026-07-07) - Worker model tiers per step (John's call; token-metered Codex
  billing).** Every phase-plan step carries a tier tag: **worker-light** (mechanical
  execution of a fully pinned spec: YAML/fixture/doc authoring, pattern-following tests,
  pipeline runs - safe because the M8 net checks correctness mechanically),
  **worker-standard** (typical implementation), or **worker-heavy** (new engine semantics,
  schema design, extraction logic, promotion-adjacent work). Tiers map to whatever
  harness/model John has cheapest at the time (provider-agnostic); John owns the mapping.
  Rules: light-tier steps are written fully prescriptive (exact files, exact shapes, no
  design latitude); a stuck worker STOPS and raises here instead of retry-looping; steps
  stay small and atomic. M10 metrics add a worker token/cost field beside human_minutes.
  **Pinned deliverable for M10 planning: a step DRIVER** - a thin script reads the plan's
  tier tags, launches each step as a fresh non-interactive worker session with the
  tier-mapped model (codex exec -m ... / agy --model ...), runs the gates between steps,
  and STOPS at any JOHN's-gate step; tier-to-model map in a config block John owns.
  **QC contract for worker-light steps:** (1) full gate suite passing is the floor;
  (2) light workers may NOT modify tests, expected fixtures, the drill catalog, or
  tax_graph/verify code unless the step explicitly authorizes it - any net-touching diff
  gets line-by-line Architect review; (3) Architect checks the diff against the step spec
  for scope containment; (4) light work is never self-committed - the Architect runs gates
  and commits; (5) metrics track rework/escapes per tier; misbehaving step types get
  promoted back to standard.
  **In effect NOW:** M9 Steps 5/6 are tagged [worker-standard] in `plans/PHASE_M9.md`.
  **First worker-light TRIAL errand** (standalone, any time, ideal for Antigravity/Flash or
  Codex/mini): fix the `form_1099b_2025` manifest URL - the current
  `https://www.irs.gov/pub/irs-pdf/f1099b.pdf` returns 404. Find the correct current IRS
  URL, update the acquisition manifest, verify `tax-graph acquire 2025 --check` completes
  past `form_1099b_2025`. Scope: the manifest entry ONLY - no test, fixture, or code edits
  authorized. Report the result and the session's token usage here (first light-tier data
  point).
- **NEW (2026-07-07) - Self-serve form extension direction PINNED (John's call).** The
  product is a VERIFIED CORE plus an EXTENSION HARNESS, not an encyclopedia. Users expand
  beyond the shipped form set by running the same acquire -> extract -> verify pipeline
  locally, standing at their own promotion gate, with honest machine-generated provenance
  (distinct trust tier; shipped artifacts hash-stamped; extensions can never impersonate
  project-verified forms). Stub target doc: `docs/self-serve-extension.md` (goals only -
  NOT a build plan). Do NOT build now; flesh-out happens after M10. Seams to respect:
  extraction config stays provider-agnostic; the unresolved-frontier trace stays typed and
  specific (it becomes the user's "extract this yourself" entry point).
- **NEW (2026-07-07) - Intake direction PINNED (John's call; companion to self-serve).**
  Doc-drop onboarding: classify -> route -> gap-fill, driven by a RELEVANCE LAYER of
  additive kinds in the SAME graph (routing edges from information-return boxes, trigger
  nodes mined from Form 13614-C with obligation classes, expectation edges for
  claims-vs-docs reconciliation both directions). Required = must-resolve-before-filing,
  not must-ask-early; careless-user protection is a completeness gate. Stub target doc:
  `docs/intake.md`. Do NOT build now; same post-M10 flesh-out. Seam: document schema stays
  additive (information returns are already document nodes).
- **PINNED (2026-07-06, John's call): M9 is the LAST bespoke single-form phase.** M10 (plan
  just-in-time at M9 close) batch-runs the pipeline across the full OTS-witnessed set
  (Schedules 1, 1-A, 2, 3, A, B, D/8949, Form 6251), human effort limited to exception
  queues + calibration + promotion gates, promotions sequenced by the frontier. See
  engineering-plan "M10". M9 measures the per-form human cost that sizes M10.
- **Oracle comparison/recording mechanism AFFIRMED (John + Architect, 2026-07-06).**
  `oracles/box_map_2025.yaml` is the single auditable comparison definition
  (machine-validated both ends); agreements freeze to `examples/oracle_corpus/` with
  `live_ots_diff_report` provenance (freeze RAISES without live OTS); disagreements cannot
  freeze without a disposition in `oracles/triage.yaml` (empty means clean, not blind -
  canaries prove the differ catches). Growth items (not blockers): box map grows with every
  promoted form (frontier enforces); guards derived from OTS's fence list as the domain
  widens; PolicyEngine is the second witness at the first liability branch; metrics payoff
  fields fill at each promotion.
- **Form Verification Record (Step 6's design source):** `docs/extraction-verification.md`
  Section 10 is canonical. One GENERATED MD page per form + roll-up `VERIFICATION.md`;
  witness list per form; absences stated, never papered over; plain-language tiers; same
  data queryable over MCP; no hand-authoring.
- **Pending for John:** adjudicate the M8 live N-version Part I/II line-2 totals rule
  disagreement (primary = SUM/addend, matching the promoted graph; the mini-model
  secondary's shape is the outlier). Seconds, not minutes.
- **Standing seams (do not violate):** parameter nodes with citations, never inline IRS
  magic numbers in `rule.parameters` (drill-enforced); node_type stays additive; document
  schema stays additive; do not strip form front-matter (title / "Purpose of Form" /
  "Who Must File") from rendered text; live graph stays referentially closed (frontier
  registry is DERIVED); `#` stays banned in static node ids (`#row_key` is runtime-only).

## Latest verification
(Older phase logs are in the archived snapshot. Current phase only.)
- M9 Step 3/4 closeout (worker-reported, spot-verified by Architect at commit):
  - `pytest` -> 193 passed, 4 skipped; `pytest -m m9` green; drill run -> 12 drills PASS
  - `validate 2025` -> OK; documents=5 nodes=30 tables=2 edges=23 rules=6 citations=7
  - `frontier build --year 2025` -> declared -> modeled flip; only Schedule D line 20 declared
  - line 7 = 2000 (basic) and 250 (multi-lot) on both yaml and sqlite sources
  - ASCII check OK
- M9 Step 2 extraction: accepted=75, review=0, deterministic_issues=0, calibration=8;
  nversion agreed diffs=0; mine-examples 10/10 unmappable (verifier endpoint config issue).
- M9 Step 5: (in flight - worker records results here)

## Resolved / superseded
- All pre-M9 items: see `plans/archive/AGENT_HANDOFF_2026-07-07_full.md` and the archived
  phase plans.
