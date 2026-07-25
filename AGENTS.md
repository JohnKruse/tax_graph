# AGENTS.md

Standing instructions for any agent working in this repository. **Read this first**, then the
master plan at `docs/engineering-plan.md`. This file is canonical for roles, the Worker directive,
and the hard rules.

**Ownership (to avoid write-collisions):** the **Architect** maintains this file and the plans/docs.
The **Worker** records active status and questions in `plans/AGENT_HANDOFF.md`, not here. Keep all
coordination in committed text files - no hidden side channels.

## Roles (Architect / Worker split)
- **Architect (Claude Opus):** planning and decomposition only. Writes/updates plans in `plans/`
  and `docs/`. Does NOT write implementation code.
- **Worker (Codex / Sonnet / Gemini):** implements one whole phase at a time from `plans/`.

## Worker directive (one whole phase per session)
1. Open the lowest-numbered phase in `plans/` not marked `[COMPLETE]`. State its Canary, wait for
   John's go, note the session context % (warn if low).
2. Work the steps in order WITHOUT stopping between them. Each step: implement core logic +
   create/update the pytest + update docstrings/docs; not done until tests pass 100%; mark `[DONE]`,
   log deviations, `git commit` (one per step; do not push yet).
3. Stop and surface to John ONLY on a problem (tests stuck, real ambiguity, a decision the plan
   does not cover, a plan-changing deviation, low context). Otherwise keep going.
4. At phase end: run the exit-criteria command (100%), mark `[COMPLETE]`, move the subplan to
   `plans/archive/`, then a single `git push`, and report.

Global project canary: **Ledger Llama**.

## Hard rules (do not violate)
- **Work out of the local-disk clone** (John names the path at session start). That is the
  canonical working copy - the `.venv` and reliable `.git` live there. An SMB-mapped network
  drive (Mac share) is NOT for dev work: it goes stale and git over SMB is unreliable (proven
  in practice). Do not read, edit, or commit under a mapped network path unless John gives
  specific instructions to. If a session starts under one, or under any path that is not the
  local clone, say so and switch before doing any work; treat anything found there as stale.
- **ASCII-only** in every authored file (docs/plans/config/code/data/graph labels/docstrings). Use
  "-" not em/en dashes, "->" not arrows, "Section" not the section sign, straight quotes.
  `tools/check_ascii.py` enforces it (CI gate).
- **Provider-agnostic LLM:** no privileged vendor; the extraction/reasoning LLM is pluggable via
  `llm.provider` with no silent default. Mistral OCR (OCR stage) is the only deliberate exception.
  The example config defaults to `openrouter`, a vendor-neutral gateway.
- **Drafts are never auto-merged and never committed.** LLM extraction output goes to
  `graph/<year>/_drafts/` (gitignored). Promotion into the live graph requires the FULL
  machine witness set green; under the **deferred-review policy (John, 2026-07-08)** the
  human review of a promotion diff may be DEFERRED to a committed review queue instead of
  blocking - with honest pending-review provenance, never asserted as reviewed. No agent
  ever writes `human_confirmed: true` or any equivalent human-review claim on the human's
  behalf; deferral is recorded, review happens later in the review workbench.
- **Runtime stays light:** build-time deps (pymupdf, mistralai, httpx, LLM clients) live in
  `pyproject` extras, never base; a runtime command must not import them.
- **IRS line numbers are the spine:** nodes are keyed on them; they drive extraction chunking and
  completeness checks.
- **NEVER pass `--basetemp` (2026-07-25). Just run `python -m pytest tests/... -q`.** The temp
  root is pinned for every account by the root `conftest.py` (`PYTEST_DEBUG_TEMPROOT` ->
  `.test_tmp/`, gitignored), because the Codex sandbox denies the AppData temp root. pytest
  puts each account in its own `.test_tmp/pytest-of-<username>/` automatically, so there is
  nothing to configure and nothing to re-grant. `--basetemp` DELETES and recreates the directory
  you point it at, which is what poisoned the old shared `.pytest_tmp`: its ownership flipped to
  whichever account ran last, and every `tmp_path` test on the other account then failed with
  `PermissionError: [WinError 5]` while the code under test was fine. `.pytest_tmp` is dead and
  unreclaimable without elevation - ignore it.
  DIAGNOSTIC: a `WinError 5` on temp cleanup makes GREEN tests report as ERRORS. If you see
  errors naming `rm_rf` or `shutil` on a temp path, suspect the temp dir before the code.
- **Never claim a test you did not run (John, 2026-07-25).** For EVERY declared focused test file,
  the handoff must state either `RAN: <exact command> -> <exact result>` or
  `NOT RUN: <reason>`. A file you could not execute is UNVERIFIED, and a step with an unverified
  declared file is NOT complete - say so plainly instead of reporting the round done. Do not
  declare a test file you already know you cannot execute in-session (e.g. an e2e file, when the
  launcher cap blocks it): say so up front so the Architect authors or runs it. "Bundled Node
  syntax checks passed" is NOT test evidence; it proves the file parses, nothing more.
- **Fix your own defects, do not let them be silently patched.** When the Architect's verification
  finds a defect in your work, it is recorded in the Worker defect ledger below. Read the ledger
  BEFORE declaring a step and name, in your session-start checkpoint, which entries apply to what
  you are about to write. Repeating a ledger defect is a process failure, not a typo.

## Worker defect ledger (read before declaring a step)

Real defects found in Worker output by Architect verification. They live here, not in the handoff,
because the handoff is pruned at every phase close and these lessons must outlive it. Append new
entries; do not delete them.

- **D1 - Playwright `Locator.first` is a PROPERTY, not a method.** `cards.first()` raises
  `TypeError: 'Locator' object is not callable`. Use `cards.first`. (M17-S3, 2026-07-24)
- **D2 - `Locator.locator(sel)` matches DESCENDANTS only.** An attribute on the element itself must
  be part of the SAME selector. `cards.locator('[data-page="2"]')` silently resolves to nothing and
  times out after 30s; write `page.locator('#river .review-unit-card[data-page="2"]')`.
  (M17-S3R2, 2026-07-25)
- **D3 - Never assert synchronously right after an action that triggers an async render.** The
  handler may `await` before the DOM settles. Use `wait_for()` / `expect()` on the thing you are
  asserting, not a bare `get_attribute` immediately after `click()`. (M17-S3, 2026-07-24)
- **D4 - Tests must not write to live developer state.** `test_document_session_round_trip_and_scope`
  wrote a real approved review into `.workbench_state/.../form_1040_2025.json`, which then showed up
  as a phantom "1 / 159 approved" in the UI John was reviewing. Point session/artifact stores at a
  tmp dir. Hermetic tests are a standing rule. (M17-S3R2, 2026-07-25)
- **D5 - A change under `workbench/` MUST run `tests/test_workbench_m15.py` locally.** It carries the
  architectural/boundary checks - notably `test_workbench_has_no_pipeline_imports`. The manifest
  partition does NOT exercise it. Skipping it is what turned M17-S2 CI-red. (M17-S2, 2026-07-24)
- **D7 - `offsetTop` is measured from the nearest POSITIONED ancestor, not from your scroll
  container.** `scrollRiverUnitIntoView` set `river.scrollTop` from `card.offsetTop`, but
  `.river-list` is `position: static` and nothing above it is positioned, so `card.offsetParent`
  is `<body>` and `offsetTop` carries the whole page offset. Measured live on the 1040: every
  selection overshot by a constant ~167px, leaving the selected card 92px ABOVE the visible area
  (`inView: false` at cards 0, 5, and 20). The bug is invisible in casual use because the river
  DOES scroll - just to the wrong place. Either use `getBoundingClientRect` deltas against the
  container, or give the container `position: relative`. NOTE: the correct pattern was already in
  the same commit - `scrollOfficialRegionIntoView` does the rect-delta math properly for the
  center pane. Copy the pattern you already got right. (M17-S3R2, 2026-07-25)
- **D6 - Always use the module form of a CLI, never the console script.**
  `.venv\Scripts\python.exe -m tax_graph.cli ...`, not `.venv\Scripts\tax-graph.exe ...`; the
  generated launcher resolves through an editable-install `.pth` with an absolute path that does not
  resolve in the sandbox. (M16-S4, 2026-07-23)

## Coordination
- Active Claude <-> Codex coordination lives in **`plans/AGENT_HANDOFF.md`** - one living ledger
  (latest status, open questions, tests run, next slice). Do NOT spawn new per-topic note files.
- When you finish a meaningful slice: update the handoff with what changed, tests run, and what
  remains; phrase questions as concrete interface/behavior questions; prefer file paths + test
  commands over prose.
- Pin durable architecture decisions into the relevant `plans/PHASE_<id>.md`; keep transient
  implementation notes in the handoff.

## Map
- Master plan + phase gates/canaries: `docs/engineering-plan.md`
- Per-phase subplans: `plans/PHASE_<id>.md`
- Testing rules: `docs/testing-strategy.md`
- Original spec: `docs/tax_graph_requirements.md`
