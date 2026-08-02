# AGENT_HANDOFF.md

The single living doc for active Claude (Architect) <-> Codex (Worker) coordination. Update it in
place; do NOT spawn new per-topic note files. Standing rules: `../AGENTS.md`. Master plan:
`../docs/engineering-plan.md`. Phase plan: `PHASE_M20.md`.

## How to use
- **Worker:** raise questions/blocks under **Open for Architect**.
- **Architect:** answer there (and pin durable decisions into the relevant `PHASE_<id>.md`), then
  clear the item. Record active direction under **From Architect**.
- **Keep it short.** A round that completes gets its narration DELETED, not appended - the
  accepted hash is the record and `git show <hash>` recovers everything. Only the current round,
  the standing constraints, and the binding rulings live here.
- **Prune at every acceptance, not "at phase close".** Pruned 2026-07-23 to 1,198 lines, then
  grew to 7,520 by 2026-08-02 because acceptance never triggered a prune. That is the failure
  mode this section exists to prevent.

## BALL

**BALL: WORKER - M20-S30 (GENERALIZE THE HARNESS, THEN GET THE PER-FORM NUMBER).**
Task block under **From Architect**. **S29 is ACCEPTED at `fca0a4a`.**

## Current round

**M20-S30 Worker status (Codex, 2026-08-02):** Canary **Ground Truth**. Steps 1-2 are
implemented and verified. The harness accepts repeatable `--document` values, defaults to
`form_1040_2025`, reports unloadable documents per row, and rejects repository output paths.
`validate_cell_output` now exempts only the direct self operand of a top-level `REQUIRE_INPUT`
from `operand_not_in_quote`; other operands remain warned. No protected graph directories
changed.

Evidence:

- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\tmp\tax_graph_m20_s30_pytest'; &
  '.venv\Scripts\python.exe' '-m' 'pytest' 'tests/test_derive_cells_m20.py'
  'tests/test_derive_cells_s30.py' '-q'` -> `37 passed in 0.92s`
- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\tmp\tax_graph_m20_s30_pytest'; &
  '.venv\Scripts\python.exe' '-m' 'pytest' 'tests/test_acquire_citation_check.py' '-q'` ->
  `9 passed in 0.18s`
- RAN: `.venv\Scripts\python.exe experiments\derive_cells_s25.py --root . --year 2025
  --output-dir C:\tmp\tax_graph_m20_s30_no_provider --document form_1040_2025
  --document schedule_a_2025 --document schedule_d_2025 --no-provider` -> exit 0; all 3
  documents reported `status: prepared` and wrote artifacts under `C:\tmp`.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> graph integrity OK;
  18 documents, 441 nodes, 409 edges, 401 citations.
- RAN: `.venv\Scripts\python.exe -m workbench.cli preflight --root . --year 2025` -> passed;
  units 2224, derived cells 2120, `legacy_mined=394`.
- RAN: `.venv\Scripts\python.exe tools/check_ascii.py` -> `ASCII check OK`.
- RAN: `git diff --check` -> exit 0; protected graph diff -> empty.
- NOT RUN: M20-S30 step 3 live provider slice; this sandbox has no outbound network, so the
  Architect must run it with approved external access and record the per-form number.

**M20-S29 deterministic half ACCEPTED (Architect, Claude Opus 5, 2026-08-02) at `fca0a4a`.**
Step 3 was not runnable this round - see the blocker note below. The Worker's report was honest,
including flagging that its own headline number was analytic rather than measured. The Architect
ran the provider leg the Worker could not:

| | Worker (analytic) | Architect (measured, live) |
| --- | --- | --- |
| `operand_not_in_quote` | 37 -> 1 | **37 -> 2** |
| 1040 derivation | not run | **17/17**, 0 repaired / 0 gapped / 0 errored |

The gap is the temperature-0 nondeterminism, not a defect in the fix: the Worker projected from the
S28 breakdown, where only 35a carried the warning, and in the Architect's run line 36 also emitted
a self-operand. **All 36 list false positives are gone, as claimed.** Gates: 79 passed on a short
temp root, ASCII OK, `validate 2025` clean, protected set byte-identical across `12240ef..fca0a4a`.

**The substring invariant is restored and was verified directly**, not inferred: all four cleaning
branches (split-suffix `1z`/`25d`, leading-contamination `22`, currency-prefix `14`) now return a
literal substring of the whitespace-normalized source. The deferred strict-citation mismatch at
promotion is closed.

**RECORDED TRADE-OFF - deliberate, not a regression to be "fixed" later.** Removing the
reconstruction means split-suffix rows keep their trailing token: `1z` cleans to
`Add lines 1a through 1h 1z`, not `1z Add lines 1a through 1h`. This partially reverts S26's
"every cleaned label starts at its own printed line token". **Accepted, because the retained token
is the row's OWN anchor, not the neighbour contamination the original defect was about**
(`$15,750 14 Add...`, `12a, 12b, 12c, 22 Subtract...`), and derivation is unaffected at 17/17.
Provenance beats label tidiness. Do not reintroduce reordering to recover the cosmetics.

**Nondeterminism at `temperature: 0` persists and is still being recorded, not retried away.**
Four runs of the identical command across S28/S29: 16/1/0/0, 16/0/1/0, 17/0/0/0, 17/0/0/0. It
oscillates in the top band instead of costing rows. Do not add a retry policy to hide it.

**CARRIED TO S30 - the last 2 warnings are the S28 collision in the soft channel.** Both survivors
are 35a and 36: REQUIRE_INPUT rows that name themselves per `prompts/derive_cells.md`, then get
warned that the self-line is not in the quote. This is exactly the collision S28 fixed for
`self_reference` in the hard channel. One exemption takes the noise floor to zero.

**ARCHITECT SPEC ERROR, recorded so it is not repeated.** S29 step 3 asked for a corpus run, but
`experiments/derive_cells_s25.py` is hardcoded to a single document - `form_1040_2025` at line 100,
and the output filename at line 145. **Step 3 was never runnable this round, with or without
network**, and the Architect did not check the harness before speccing it. The Worker reported only
the network half of the blocker. Generalizing the harness is now S30 step 1.

## Standing constraints (every M20 round)

- **PROTECTED SET, hard gate:** `graph/2025/{nodes,edges,rules}/` and `graph/2025/field_maps/`
  must be byte-identical. `git diff --stat` on those directories must be EMPTY. No promotion, no
  hand-authoring, no live graph edit, no verdict write, no operation enum change.
- **`derive_cells` must remain pure - zero disk writes.**
- **PYTEST TEMP ROOT MUST BE SHORT** (e.g. `C:\tgt`). An Architect session was burned reporting 22
  suite failures of which 8+ were `WinError 206` path-length artifacts of a deep temp root. With a
  short root the same files went 11 failed -> 3.
- **KNOWN-RED BASELINE - inherit it, do not get blamed for it, do not fix it in an unrelated
  round.** All three depend on untracked local state, which is why CI is green:
  - `test_review_scope_migration_m15.py::test_live_queue_migration_...` (FileNotFoundError,
    `review_queue/2025/deferred_review.yaml` - tracked dir with no files)
  - `test_schedule_2_m16.py::test_schedule_2_part_i_raw_acroform_identity` (`assert '1a' == 'z'`;
    reads gitignored `.cache/raw/.../schedule_2_2025.fields.json`, regenerated 2026-07-28 while
    the source PDF is unchanged, so a code-only bisect proves nothing)
  - `test_address_campaign_m15r.py::test_form_8949_cross_form_claims_resolve_exactly`
    (`realized 0, expected 6`)
- **The Worker sandbox has NO outbound network.** Live-provider legs fail 17/17 with
  `LlmUnavailable: ... Connection error`. This has cost three rounds. Either run the provider leg
  outside the sandbox with approved access, or declare the round fixture-only UP FRONT.
- **Model is `openai/gpt-5.6-luna`** in `tax-graph.config.yaml` (`llm.micro_model`). Do not switch
  to `google/gemini-3.6-flash` - measured ~15x the cost at our call volume.
- **Evidence discipline:** honest `RAN:` / `NOT RUN:` lines with exact commands and exact output.
  Never a guess, never a paraphrase of a number.

### Worker environment (2026-07-23)
The recurring `Access is denied` on `.venv\Scripts\python.exe` was the venv launcher shim spawning
the OUT-OF-WORKSPACE base interpreter, which the Codex sandbox denies per session (it is NOT a
machine state and no restart fixes it). Fixed by mirroring the base interpreter to `.python313/`
inside the repo (gitignored) and rebuilding `.venv` on it, so `pyvenv.cfg home` is in-workspace.
Workers call `.venv\Scripts\python.exe` directly - no `uv` needed.
**Do NOT pass `--basetemp`** (2026-07-25). The root `conftest.py` pins the temp root for every
account and pytest separates accounts via `pytest-of-<username>/`. The old `.pytest_tmp` is
poisoned and unreclaimable; see the hard rule in `AGENTS.md`.
**Launcher cap is 600s** (John, 2026-07-26; was ~124s, then 240s). The Worker runs its OWN e2e and
app-dependent files. Only full partitions and Tier 3 shakedowns stay Architect-side. Anything that
still does not fit gets an honest `NOT RUN:`.
**ALWAYS use the module form, never the console scripts** (2026-07-23, M16-S4):
`.venv\Scripts\python.exe -m tax_graph.cli validate 2025` and
`.venv\Scripts\python.exe -m workbench.cli preflight --year 2025`. The generated `tax-graph.exe` /
`review-workbench.exe` launchers resolve the package through the editable install's `.pth`, which
hardcodes an absolute repo path that does not resolve inside the Codex sandbox
(`ModuleNotFoundError: No module named 'tax_graph.cli'`). Architects: write the module form into
Worker prompts.

**Recurring op note:** orphaned `serve` processes have first-class tooling -
`tax-graph serve --sweep-orphans`. The parent watchdog works on Windows as of M14 (OpenProcess
probe). Serve writes stderr breadcrumbs that Claude Desktop logs verbatim - first stop when a
client-managed server dies.

## Binding rulings (John's, still in force - DO NOT DELETE ON PRUNE)

- **THE HANDCRAFTED SET IS THE TEST SET, AND IS PROTECTED.** A lot of tokens went into it. It is
  not to be thrown away, promoted over, or edited. It is labeled comparison data. This is the
  origin of the protected-set gate above.
- **THE SPINE IS THE FLOW OF THE FORM (2026-07-26, the addressing ruling).** Verbatim: *"The spine
  is the flow of the form. We shouldn't be pedantic about the line numbers."* John named the
  disambiguation case himself - *"there might be 6 different SSNs for example. Which one?"* - and
  rejected positional numbering for repeatable rows. This REVISES the pinned invariant "IRS line
  numbers are the spine" in `AGENTS.md`. **Identity comes only via canonical addresses.**
- **THE BAR IS PRACTICAL RETRIEVAL (2026-07-26).** Offered two labeling schemes, John rejected the
  framing: *"I don't know that i care so much about the addressing scheme being perfect in some
  theoretical manner. We need to be able to refer to these things in a practical way... if you are
  asked about dependents... numbers, SSNs, whatever, we need to be able to pull it out of the
  graph data/metadata."*
- **FILER-PROVIDED IS A FAILOVER, NOT A DEFAULT (2026-07-31).** Verbatim: *"filer provided should
  be a failover rather than a default."* And: *"If I read 'Net proceeds' or 'Interest', my feeling
  is that this is just something to be provided by the filer. If the AI can't find it in the docs
  provided by the filer, it should ask."*
- **THE REVIEW QUEUE IS THE WRONG SHAPE (2026-07-29); this supersedes the reconciler.** There are
  ZERO human verdicts anywhere - the queue's `pending`/`deferred`/`accepted_local` are all
  machine-set, so the 198 re-points and 263 orphan records preserved no human judgement. The churn
  was an IDENTITY defect: 100% of 461 citation refs (keyed on generated sequence ids) churned
  while 1,921 field-control refs (keyed on canonical addresses) churned 0%. The graph already has
  stable cell identity; coverage should be a traversal, not a migrated file. **Verdicts must bind
  to CONTENT, not only to address.**
- **REVIEW PANEL LAYOUT (parked S6-2, still binding when UI work resumes).** The expression, the
  two instruction sources, the verdict controls, AND the comment box go TOGETHER; today the
  controls sit in the left rail while content is in the right river. Keep the 15/40/45
  proportions. Show the two instruction sources SEPARATELY (form face, instruction page - never
  concatenated). Wire the four buttons that already exist and **keep John's labels** - "Pipeline
  defect" vs "Source pathology" is his distinction.

## Open for Architect

- *(empty - the S3a outline-adapter question was answered 2026-08-02, see Architect decisions)*

## From Architect

- **M20-S30 TASK - GENERALIZE THE HARNESS, THEN GET THE PER-FORM NUMBER (Architect, Claude Opus 5,
  2026-08-02).** Ledger: the RAN/NOT RUN rule, D9, D6, D10.

  **Why this round.** The 1040 is at 17/17 with a readable warning channel. That is one form out of
  eighteen, and S29 proved the harness physically cannot say anything about the other seventeen.
  This round makes the corpus measurable and then measures a slice of it.

  **Step 1 - generalize the harness (deterministic, no model calls).**
  `experiments/derive_cells_s25.py` hardcodes `form_1040_2025` at line 100 and its output filename
  at line 145. Take `--document` (repeatable) and default to the 1040 so existing invocations keep
  working; derive the output filename from the document id. `--no-provider` must keep working
  per-document. **`derive_cells` stays pure - the harness owns every write, and no output may land
  inside the repository.** A document that cannot be loaded is a REPORTED ROW with a reason, never
  a crash and never a silent skip (ledger D10: fail closed on an unexpected empty).

  **Step 2 - exempt REQUIRE_INPUT self-operands from `operand_not_in_quote`.** Both surviving
  warnings in the Architect's live run (35a, 36) are rows obeying
  `prompts/derive_cells.md` - "if this line is not computed, use REQUIRE_INPUT with one line
  operand naming itself" - and then being warned that the self-line is absent from the quote. This
  is the S28 `self_reference` collision in the soft channel. Exempt the SELF-operand of a top-level
  REQUIRE_INPUT only. Every other operand on every other operation keeps the warning. Add a focused
  test. **Expected: the 1040 warning count goes to 0.**

  **Step 3 - run the three-form slice and report the unflattering number.** NOT the full corpus
  yet - the point of a slice is to learn the shape before spending on eighteen documents:
  - `form_1040_2025` - the known baseline, expected 17/17, a regression check on steps 1-2.
  - `schedule_a_2025` - has a handcrafted labeled set (S14 scored it 7/7), so derived output can be
    compared against known-good rather than merely counted.
  - `schedule_d_2025` - structurally the hardest, columns and tables rather than a line list. This
    is where S23-S28 are most likely NOT to generalize, which is exactly why it is in the slice.

  Report a per-form table: form, rows attempted, `derived`, `repaired`, `gapped`, `errored`, and
  the top three `validator_failures_by_kind`. **Lead with `derived` per form.** A high 1040 number
  next to unreported coverage elsewhere is the exact reporting failure this project has already
  made once. If a form cannot be attempted, that is a row with a reason, not an omission.
  **A low number on Schedule D is a SUCCESSFUL round**, not a failure - it is the finding that
  sizes the rest of the phase. Do not tune anything to make it look better; report it and stop.

  **On the provider leg:** the Worker sandbox has no outbound network (Standing constraints). If
  approved external access is not available this session, do steps 1-2, **declare step 3 NOT RUN up
  front**, and hand back - the Architect will run the slice. Do not burn the round on
  `Connection error`.

  **Do not:** add a retry policy for the temperature-0 nondeterminism; add any gate keyed on
  instruction-section coverage; weaken the self-reference, printed-line, or verbatim-quote checks;
  reintroduce reordering into `clean_form_face_text` to recover label cosmetics (see the recorded
  trade-off); promote anything.
  **Stop conditions:** any diff in the protected directories; `derive_cells` acquiring a disk
  write; any harness output landing inside the repository.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, preflight with `legacy_mined` explicit (394), strict citations (36).
  ONE local commit; no push.

## Architect decisions

- **S3a -> S3b: YES, the structure step owns a deterministic outline adapter. S3a regeneration
  stays blocked until it lands. (Answered 2026-08-02; open since 2026-07-28.)** The bare positional
  index is not enough, and the reason is the one this phase already discovered twice: **identity
  must be resolved in CODE from a stable anchor, never from position.** An exact string offset that
  can land on repeated anchor text in another semantic row is position-based identity - the same
  class of defect as keying the review queue on generated sequence ids (100% churn) and as asking
  the model to name a `quote_span_id` (fixed in S28). The adapter belongs to S3b because
  `PHASE_M20.md` section 3 is explicit that this pipeline never had an independent structure layer
  and that building one IS S3b; an outline is structure, not regeneration. Requirements: build it
  from the corrected text plus `line_anchors` plus page/geometry, resolve each anchor to exactly
  one semantic row, and **fail closed at row granularity** when an anchor is ambiguous - matching
  the S2d/S2e span-resolver ruling. Do not promote a draft or hand-edit a citation or label to get
  past an ambiguity.

## Recent rounds (condensed; full narration in git history - `git show <hash>`)

- **M20-S29 (`fca0a4a`, Architect-verified):** `_line_mentioned` handles singular, plural-list and
  range references; `clean_form_face_text` truncates instead of reconstructing, restoring the
  substring invariant. Live 1040 17/17 with warnings 37 -> 2. Step 3 blocked - single-document
  harness.
- **M20-S28 (`12240ef`, Architect-verified):** the three deterministic last-five-row defects -
  cleaned evidence text, REQUIRE_INPUT exempt from the self-reference check, `quote_span_id`
  resolved in code and dropped from the schema. Real 1040 **17/17**.
- **M20-S27 (`8027161`, Architect-verified):** `printed_lines` carries all 59 printed anchors (was
  17 formula-only); `operand_not_printed` collapsed 31 -> 1; per-row span-id enum; generic
  `provider: openai` honors `llm.base_url`. Real 1040 12/17.
- **M20-S26 (`b3e102b`, Architect-verified):** `missing_instruction_text` -> `missing_evidence`
  (face OR instruction), so `attempted` went 4 -> 17; ownership issues DROP the section instead of
  killing the row; label contamination fixed 17/17. **First real expressions in M20**, including
  the floors the flat schema had been dropping (`line 15 -> max(line 11b - line 14, 0)`).
- **M20-S25 (`ff62119`, Architect-verified):** property validators and repair-once. Architect then
  diagnosed derived=0 against real data: the instruction booklet does not document computed lines,
  the form face does - which set up S26.
- **M20-S24 (`e6e94e3`):** `derive_cells` as a pure function with expression trees.
- **M20-S23 (`0831694`):** the `instruction_sections` artifact and its join.

## Latest verification

- **M20-S29 (2026-08-02, Architect):** focused suite 79 passed on a short temp root; ASCII;
  `validate 2025` (18 documents, 441 nodes, 409 edges, 401 citations); protected set
  byte-identical across `12240ef..fca0a4a`; live 1040 17/17 with `operand_not_in_quote` 37 -> 2;
  substring invariant verified directly on all four cleaning branches.
- **M20-S28 (2026-08-02, Architect):** focused suite 96 passed on a short temp root; ASCII;
  `git diff --check`; `validate 2025` (18 documents, 441 nodes, 409 edges, 401 citations);
  preflight units=2224, derived cells=2120, `legacy_mined=394` (ratchet unchanged); strict
  citations `checked=401 strict_mismatches=36`; protected set byte-identical; live 1040 17/17.
- **Preflight note:** the sandbox run hits a known pre-existing `WinError 5` on
  `graph/2025/_drafts/form_1040_2025` (a draft ACL, not a regression). The same read-only command
  with escalation passes.
- Prior phase closes: `plans/archive/PHASE_M13.md` and earlier - each with a close note.

## History

Everything before M20-S23, and all per-round Worker narration, lives in git history. This file was
pruned from 7,520 lines on 2026-08-02 at S28 acceptance; `git show 12240ef:plans/AGENT_HANDOFF.md`
is the last unpruned copy. Earlier prune: 2026-07-23, from 1,198 lines, for public-repo prep.
Durable rulings were carried forward into **Binding rulings** above rather than deleted; A9
rulings remain pinned in `plans/PHASE_M15.md`; the defect ledger (D6, D9, D10, D12, D13, D14) is
in `AGENTS.md`.
