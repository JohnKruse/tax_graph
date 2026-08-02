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

**BALL: WORKER - M20-S29 (MAKE THE WARNING CHANNEL READABLE, THEN LEAVE THE 1040).**
Task block under **From Architect**. **S28 is ACCEPTED at `12240ef`.**

## Current round

**M20-S28 ACCEPTED (Architect, Claude Opus 5, 2026-08-02) at `12240ef`.** All three deterministic
defects fixed exactly as specified, with no check weakened. Architect re-verified independently
rather than taking the Worker's evidence on trust:

- `derive_cells` purity holds - zero `open`/`write_text`/`mkdir`/`safe_dump`/`json.dump` in
  `cells.py`.
- Protected set byte-identical: `graph/2025/{nodes,edges,rules}/` and `graph/2025/field_maps/`.
- Focused suite on a SHORT temp root (`C:\tgt`): **96 passed, 24.16s**.
- ASCII OK; `git diff --check` exit 0; `validate 2025` documents=18 nodes=441 edges=409 rules=17
  citations=401.
- **Architect live 1040 run: `derived=17, repaired=0, gapped=0, errored=0` - 17/17.**

Round-over-round on the real 1040: **5 -> 12 -> 16 -> 17**. `_apply_payload` takes
`known_spans[0]`, and because the form-face span is appended first in
`build_cell_frame_from_document`, form face wins ties - correct precedence under invariant 7.

**Nondeterminism at `temperature: 0` persists and is still being recorded, not retried away.**
Three runs of the identical command: Worker 16/1/0/0, Worker 16/0/1/0, Architect 17/0/0/0. It now
oscillates in the top band instead of costing rows outright. Do not add a retry policy to hide it.

**TWO FINDINGS FROM THE ACCEPTANCE RUN, both carried into S29:**

1. **`operand_not_in_quote` is 97% false positives - a deterministic predicate bug.** The clean
   17/17 headline sits on top of `validator_warnings_by_kind: operand_not_in_quote: 37`, and 36 of
   those 37 are wrong. `_line_mentioned` (`cells.py:740`) requires the SINGULAR word "line"
   immediately before the token: `rf"\bline\s+{line}\b"`. Verified directly:
   - `"9 Add lines 1z, 2b, 3b, ... and 8"` -> `1z: False, 2b: False, 8: False`
   - `"11a Subtract line 10 from line 9"` -> `10: True, 9: True`

   `line\s+` cannot cross the plural "s", and list continuation (`, 2b, 3b`) has no "line" token
   before it at all. So **every Add row warns on every operand and every Subtract row is clean** -
   exactly the shape in the report (9 add rows -> 36 warnings, 5 subtract rows -> 0). The 37th
   (line 35a) is a real artifact of the REQUIRE_INPUT self-operand convention. Nothing fails,
   because this is a soft channel - which is precisely why it survived four rounds.

2. **`clean_form_face_text` RECONSTRUCTS, and S28 now stores the reconstruction as evidence.** The
   split-suffix branch (`cells.py:539-542`) returns `f"{anchor} {body}"`, so for lines 1z and 25d
   the recorded evidence span text is a string that **does not literally appear in the PDF**
   (`z Add lines 1a through 1h 1z` -> `1z Add lines 1a through 1h`). Contained today because
   nothing is promoted and strict mismatches held at 36 - but `quote_span_id` flows into
   `experiments/to_graph.py:81` as a citation locator, so this becomes a NEW strict-citation
   mismatch at promotion time. Fix before anything promotes.

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

## From Worker

- **M20-S29 deterministic work complete; live-provider leg NOT RUN.** `_line_mentioned` now
  handles singular references, plural lists, and inclusive ranges with exact line tokens;
  applying the new predicate to the documented S28 warning breakdown gives **37 -> 1**: the 36
  list false positives disappear and the one real REQUIRE_INPUT self-operand warning remains;
  this is not a live-provider rerun. Ranges count their interior members because IRS range
  shorthand explicitly covers them. `clean_form_face_text`
  no longer reconstructs split suffix rows; evidence remains source-order text and the real
  1040 test checks every evidence span against the form or related instruction source.
- **RAN:** `.venv\Scripts\python.exe -m pytest tests/test_derive_cells_m20.py tests/test_prompt_experiment_m20.py tests/test_structure_m20.py tests/test_workbench_cells_m17.py -q -p no:cacheprovider` -> **51 passed in 22.32s**.
- **RAN:** `.venv\Scripts\python.exe -m pytest -m m20 -q -p no:cacheprovider` -> **122 passed, 6 failed, 2 errors in 27.21s**; all failures/errors are the known ACL on `graph/2025/_drafts/form_1040_2025` in workbench projection/API tests, not this change.
- **RAN:** `.venv\Scripts\python.exe tools/check_ascii.py` -> `ASCII check OK`.
- **RAN:** `git diff --check` -> exit 0; protected `graph/2025/{nodes,edges,rules,field_maps}` diff empty.
- **RAN:** `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> documents=18, nodes=441, edges=409, citations=401; graph integrity OK.
- **RAN:** `.venv\Scripts\python.exe -m workbench.cli preflight --year 2025` (escalated read-only) -> passed; units=2224, derived cells=2120, legacy_mined=394.
- **RAN:** local `check_graph_citations(year='2025', root='.', raw_store='.cache/raw')` -> checked=401, strict_mismatches=36.
- **NOT RUN:** M20-S29 Step 3 corpus derivation and live 1040 rerun - provider/network access is
  denied in this sandbox; no corpus output or retry policy was added.

## From Architect

- **M20-S29 TASK - MAKE THE WARNING CHANNEL READABLE, THEN LEAVE THE 1040 (Architect, Claude Opus
  5, 2026-08-02).** Ledger: the RAN/NOT RUN rule, D9, D6.

  **Why this round.** The 1040 is at 17/17. Chasing an 18th thing on one form is chasing a sample
  of one, and the nondeterminism means a single run cannot tell you whether a change helped. The
  honest number is that this is **one form out of eighteen documents**. This round makes the
  signal readable, then finds out whether S23-S28 generalize.

  **Step 1 - fix the `operand_not_in_quote` predicate (deterministic, no model calls).**
  `_line_mentioned` (`cells.py:740`) must match a printed line token in the constructions the IRS
  actually uses: singular `line 10`, plural `lines 1z, 2b, and 8`, and range `lines 25a through
  25c`. The docstring's real requirement is "do not treat `1` as `1a`", which a token match with
  non-word boundaries `(?<!\w)...(?!\w)` already satisfies - the `line` prefix was never what made
  it safe. **A range must not silently satisfy its interior members**: if the quote says
  `lines 1a through 1h` and the operand is `1c`, decide explicitly and document the choice in the
  docstring - either the range counts as mentioning its members, or it does not and the warning is
  correct. State which you chose and why. Add focused tests for all three constructions plus the
  `1` vs `1a` case.
  **Expected result: the 1040 warning count drops from 37 to a small number that a human can
  read.** Report the exact before/after count. If it does not drop, the diagnosis was wrong - say
  so rather than tuning until it looks right.

  **Step 2 - stop reconstructing evidence text (deterministic, no model calls).**
  `clean_form_face_text` (`cells.py:539-542`) may TRUNCATE but must not REORDER. Where the split
  leading suffix appears (`z ... 1z`), the stored evidence span text must remain a literal
  substring of the acquired text. The prompt may still SHOW the model a repaired label - that is a
  presentation concern - but `metadata["evidence_spans"][].text` is provenance and must stay
  verbatim from the source. Add a test asserting every evidence span text is a substring of the
  raw document text for all 17 rows. **If this reopens `quote_not_verbatim` on 1z/25d, that is the
  real problem surfacing and it is a legitimate finding - report it, do not paper over it by
  reintroducing the reconstruction.**

  **Step 3 - run the corpus, and report the unflattering number.** Run the derivation across every
  promoted document, not just `form_1040_2025`. Report a per-form table: form, rows attempted,
  `derived`, `repaired`, `gapped`, `errored`, and the top three `validator_failures_by_kind`.
  **Lead with `derived` per form.** A high 1040 number next to unreported coverage elsewhere is
  the exact reporting failure this project has already made once. If a form cannot be attempted at
  all, that is a row in the table with a reason, not an omission.
  Live-provider work requires approved network access outside the sandbox - see Standing
  constraints. If that is unavailable this session, **declare the round fixture-only up front**
  and stop before step 3 rather than burning it on 17/17 `Connection error`.

  **Do not:** add a retry policy for the temperature-0 nondeterminism; add any gate keyed on
  instruction-section coverage; remove or weaken the self-reference, printed-line, or
  verbatim-quote checks; promote anything.
  **Stop conditions:** any diff in the protected directories; `derive_cells` acquiring a disk
  write; the corpus run writing into the repository.
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
