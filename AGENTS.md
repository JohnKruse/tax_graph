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
- **The FLOW of the form is the spine (John, 2026-07-26; REVISES the former "IRS line numbers
  are the spine").** Identity comes from a control's place in the form's semantic flow - section,
  group, role - never from the printed line number. Line numbers remain load-bearing for
  extraction chunking, completeness checks, and human-facing display (they are how humans quote a
  form), but they are PLACEMENT data, not identity. The test when minting any id: **an address key
  must never contain anything the IRS can change without changing the meaning** - no line numbers,
  no years, no printed prose. Corollary (John's SSN case): every concept must be qualified by its
  OWNER or ROLE - a bare `ssn` is never an address, because a form carries several. Design and
  migration: `plans/PHASE_M19.md`.
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
  declare a test file you already know you cannot execute in-session: say so up front so the
  Architect authors or runs it. "Bundled Node syntax checks passed" is NOT test evidence; it
  proves the file parses, nothing more.
- **Worker command cap: 600 seconds (John, 2026-07-26; was ~124s, then 240s).** What this
  changes: a Worker can now run a FULL workbench round in one command - app startup plus the
  API and e2e files together measured 319s, with ~3.5x margin on the worst single file. So
  **e2e files you author are YOURS to run and verify** - the "declare it and let the Architect
  run it" escape hatch no longer applies to them, and ledger entries D1/D2/D3 are all defects
  that this cap would have caught in-session. Real preflight (~138s) and manifest-building
  tests (~150s) also fit comfortably. STILL Architect-side regardless of the cap: full local
  partitions and Tier 3 shakedowns (CI's test job alone is ~47 min). If a command still does
  not fit, the honest `NOT RUN:` line above is the answer - never a guess.
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
- **D9 - When you change a promoted artifact's CONTENT, run the tests that PROJECT that
  content, not just the ones you wrote.** M18-S2b re-derived 217 citation `quoted_text`
  values correctly - the data fix was right and the integrity gate improved 37 -> 36
  mismatches. But it declared only `tests/test_citation_cleanup_m18.py` and
  `tests/test_graph_validator.py`, and left `tests/test_workbench_cells_m17.py` red: that
  file hardcoded the OLD polluted string as its expected value, so it was asserting the
  defect. The Architect caught it in the Tier 3 partition. **This is D8's sibling** - D8 was
  renaming a value without grepping consumers; D9 is changing a value without running the
  consumers' tests. Practical rule: `grep -rln "<a distinctive fragment of the old value>"
  tests/` before declaring your files. A test that pins old output is not a reason to leave
  the fix out; it is a test to update, with a comment saying why. (M18-S2b, 2026-07-27)
- **D8 - Renaming a value in a PROMOTED ARTIFACT is an API change. Grep for every consumer
  before you rename.** M19-S4 was told to normalize 8949 group naming; it also renamed the
  1040 dependents group from the table token `dependents` to the row-template token
  `dependent` in `graph/2025/field_maps/form_1040_2025.yaml`. But `tax_graph/output/fill.py`
  line 78 hard-compares `if repeatable.get("group") != "dependents": continue`, so EVERY
  dependent disposition was silently skipped and **zero dependent fields were written to the
  1040** - a filing-correctness regression, not a cosmetic one. It went CI-red on all three
  interpreters (`tests/test_dependents_m15.py`, 3 failed) and reproduces locally in 31
  seconds. Neither Worker nor Architect ran that file, because both reasoned about the
  workbench projection and forgot the ENGINE also consumes these artifacts. Rules: (a) a
  promoted-artifact value is a contract - `grep -rn "<old-value>" tax_graph/ workbench/`
  before renaming it; (b) `group` names the TABLE (`table=dependents`), not the row template
  (`row_template=dependent`); (c) when a round touches field maps, addresses, or bindings,
  the fill/engine tests are in scope, not just the review-surface tests. (M19-S4, 2026-07-27)
- **D10 - An expected document that yields NOTHING is a finding, not silence.** M18-S3
  promoted 82 correct 1040 instruction citations and reported "Schedule 1-A had no matched
  section in the acquired 1040 HTML and was not guessed." Not guessing was right; the stated
  cause was wrong. The h2 `Instructions for Schedule 1-A Additional Deductions` **is** in the
  stored HTML at `id509` - the same heading the S1 survey had already verified - but the S2
  miner emits ZERO sections under that context, so the join never sees a candidate and
  therefore never raises a finding. All 101 Schedule 1-A addresses ended with zero coverage
  and zero recorded reason. **Fail-closed is about the EMPTY case too:** when a document you
  expected to cover produces no candidates at all, that is the loudest possible signal, and
  it is exactly the one a per-section finding loop cannot emit. Add an explicit
  expected-vs-produced check per document. Corollary: when you report an absence, verify it
  against the SOURCE (grep the stored file, check the survey you already committed) before
  attributing it to the source. (M18-S3, 2026-07-28)
- **D11 - Findings you return but never persist do not exist.** M18-S3's
  `join_instruction_sections` produced 61 fail-closed findings and
  `InstructionJoinFinding.as_dict` even shapes them as review-queue records with a
  `queue_id` - but `promote_instruction_html` never wrote them anywhere, and nothing touched
  `review_queue/`. The task required unmatched sections to fail closed INTO THE REVIEW QUEUE.
  In-memory findings vanish with the session, so committed state cannot answer "what was
  skipped and why". If a contract says queue it, the artifact must land on disk in the
  round that generates it. Related: a promoted artifact needs a committed entry point that
  regenerates it - an ad-hoc `python -c` is not reproducible. (M18-S3, 2026-07-28)
- **D12 - NEVER weaken a verifier to make it pass. Fix the data the verifier protects.**
  M20-S2 rebuilt the form text layer correctly (retention 52.2% -> 100%, apostrophes mapped
  instead of deleted). That correctly caused 26 stale citations to stop verifying, because
  those records still quoted the OLD renderer's damaged text (`isnt`, `didnt` - the
  apostrophe welds the rebuild had just fixed). Citation integrity went 36 -> 69. The Worker
  brought it back to "the exact baseline of 36" partly by rebuilding faithfully, and partly
  by adding fallbacks INSIDE `_contains_normalized` that fold apostrophes out of both sides,
  strip standalone dots, and weld `other-from` -> `otherfrom`. Measured: **26 citations pass
  only via those fallbacks; the strict gate reports 62 mismatches, not 36.** So the restored
  baseline was not a like-for-like comparison.
  Why this is worse than editing the records: the loosening is PERMANENT and applies to
  every FUTURE citation, so the project would ship a verifier that accepts text differing
  from its source - the exact invariant the M14 fabricated-citations reopen exists to
  protect. **The precedent for the right fix was in the same handoff file:** M18-S2b
  re-derived 217 `quoted_text` values from the acquired source and verified each, using
  `tax_graph/acquire/citation_cleanup.py`, which already exists for this.
  Rules: (a) when a gate goes red after you fix an upstream defect, the stale DATA is the
  bug - re-derive it; (b) a compatibility shim in a verifier is a data migration wearing a
  disguise, and it must be a one-shot migration with an expiry, never a permanent branch in
  the check; (c) if you cannot re-derive, STOP and report the ids - that instruction was
  explicit in the task. Credit where due: the Worker did NOT edit any citation, reported the
  69 honestly, and scoped the shim to a damage signature. The honesty was right; the choice
  of WHERE to fix was wrong. (M20-S2, 2026-07-28)
- **D13 - Verbatim is NECESSARY but NOT SUFFICIENT. A re-derived citation must preserve the
  ANCHOR, not merely pass the substring check.** M20-S2b correctly re-derived 25 of 26 stale
  citations (apostrophe welds `isnt -> isn't`), but for `cite_span_schedule_a_2025_0036` it
  replaced the damaged `Otherfrom list in instructions. List type and amount:` with
  `Other taxes. List type and amount:`. Both are real substrings of Schedule A, so the gate
  passed - but they are DIFFERENT LINES: the node is
  `schedule_a_2025_root_line_16_amount` (Other Itemized Deductions), and the new quote is
  **line 6**, in the Taxes You Paid section. Authority for line 16 now cites line 6.
  **The faithful string was available:** `Other-from list in instructions. List type and
  amount:` IS present in the rebuilt text - the em dash had mapped to a hyphen correctly, so
  the correct answer was one character away from the damaged one.
  **The gate cannot catch this class.** `check_citation_integrity` proves a quote came from
  the source; it cannot prove it is the RIGHT quote for the node. Rules: (a) a re-derivation
  must be anchored - the new text must come from the same location/meaning as the old, and a
  change that is not explainable as punctuation restoration needs an explicit justification;
  (b) when the old text is damaged, reconstruct what it WAS (map the deleted character back)
  rather than searching for any nearby string that verifies; (c) check the re-derived text
  against the referencing node's label and printed line before accepting it.
  (M20-S2b, 2026-07-28)
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
