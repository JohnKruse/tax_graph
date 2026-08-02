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

**BALL: ARCHITECT - M20-S33 COMPLETE, AWAITING ACCEPTANCE.** Worker report is below; no source,
promoted artifact, or verdict changed. Canary: Ground Truth.

## Current round

**M20-S33 WORKER COMPLETE (Codex, 2026-08-02).** The graph loader contains 18 document ids. The
first run used the 17 ids in `graph/2025/documents`; the missing `form_2441_2025` was then run
separately after the discrepancy was found. All live-provider commands ran outside the sandbox
with the configured `openrouter` provider and `openai/gpt-5.6-luna` model. Reports were written
only under `C:\tmp\m20_s33_corpus_20260802` and `C:\tmp\m20_s33_1040_20260802`.

Sorted by derived / attempted, worst first. Empty input documents are listed last.

| document | status | derived / attempted | repaired | gapped | errored | outline | anchors | top validator failures |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `schedule_1_2025` | complete | 0 / 4 (0%) | 4 | 0 | 0 | 66 | 61 | `operand_not_printed=19` |
| `schedule_3_2025` | complete | 2 / 4 (50%) | 2 | 0 | 0 | 38 | 35 | `operand_not_printed=33` |
| `schedule_2_2025` | complete | 3 / 5 (60%) | 2 | 0 | 0 | 52 | 45 | `operand_not_printed=28` |
| `form_6251_2025` | complete | 23 / 29 (79.3%) | 5 | 0 | 1 | 68 | 63 | `missing_floor=3`, `payload=2`, `quote_not_verbatim=1` |
| `schedule_1a_2025` | complete | 23 / 24 (95.8%) | 1 | 0 | 0 | 60 | 48 | `operand_not_printed=2` |
| `schedule_b_2025` | complete | 1 / 1 (100%) | 0 | 0 | 0 | 12 | 8 | none |
| `schedule_a_2025` | complete | 7 / 7 (100%) | 0 | 0 | 0 | 29 | 28 | none |
| `schedule_d_2025` | complete | 3 / 3 (100%) | 0 | 0 | 0 | 31 | 24 | none |
| `form_1040_2025` | complete | 17 / 17 (100%) | 0 | 0 | 0 | 60 | 59 | none |
| `form_2441_2025` | reported | 0 / 0 (-) | 0 | 0 | 0 | - | - | `load_failure=unknown_manifest_document` |
| `form_1099b_2025` | empty | 0 / 0 (-) | 0 | 0 | 0 | 18 | 17 | none |
| `form_1099_div_2025` | empty | 0 / 0 (-) | 0 | 0 | 0 | 28 | 25 | none |
| `form_1099_int_2025` | empty | 0 / 0 (-) | 0 | 0 | 0 | 12 | 11 | none |
| `form_13614_c_2025` | empty | 0 / 0 (-) | 0 | 0 | 0 | 209 | 0 | none |
| `form_8949_2025` | empty | 0 / 0 (-) | 0 | 0 | 0 | 7 | 4 | none |
| `form_w2_2025` | empty | 0 / 0 (-) | 0 | 0 | 0 | 15 | 14 | none |
| `instructions_form_1040_2025` | empty | 0 / 0 (-) | 0 | 0 | 0 | 0 | 0 | none |
| `instructions_schedule_d_2025` | empty | 0 / 0 (-) | 0 | 0 | 0 | 0 | 0 | none |

**Zero classification:** The eight empty documents are correctly empty input or instruction
documents: the four 1099/W-2 inputs, Form 13614-C, Form 8949, and the two instruction documents.
No document was empty-but-should-not-be; every derivation-capable document except `form_2441_2025`
produced frame rows. `schedule_1_2025` is the attempted-but-zero-fully-derived case: all four rows
were repaired, so it is not an all-error run, but no row ended with status `derived`.

Totals over rows that loaded: attempted=94, derived=79, repaired=14, gapped=0, errored=1. The
separate `form_2441_2025` load failure is reported above and is not included in row totals.

**Required repeatability check:** identical `form_1040_2025` commands ran twice. Both returned
`complete`, attempted=17, derived=17, repaired=0, gapped=0, errored=0, outline=60, anchors=59,
validator_failures_by_kind={}. Schedule D line 16 did not flip.

**Gates:**

- `RAN: .venv\Scripts\python.exe tools\check_ascii.py -> ASCII check OK`.
- `RAN: git diff --check -> exit 0`.
- `RAN: git diff --stat -- graph/2025/nodes graph/2025/edges graph/2025/rules graph/2025/field_maps -> empty`.
- `RAN: .venv\Scripts\python.exe -m tax_graph.cli validate 2025 -> exit 0; documents=18, nodes=441, edges=409, citations=401; graph integrity OK`.
- `RAN: .venv\Scripts\python.exe -m workbench.cli preflight --year 2025 -> exit 0; units=2224, derived cells=2120, legacy_mined=394` (approved external read because sandbox ACL blocked the known draft directory).
- `RAN: .venv\Scripts\python.exe -c "from tax_graph.acquire.citation_check import check_graph_citations; report=check_graph_citations(year='2025', raw_store='.cache/raw', root='.'); print(f'checked={report.checked} strict_mismatches={len(report.mismatches)}')" -> checked=401 strict_mismatches=36`.
- `RAN: $env:PYTEST_DEBUG_TEMPROOT = 'C:\tmp'; .venv\Scripts\python.exe -m pytest tests/test_derive_cells_s30.py tests/test_m20_s31.py tests/test_derive_cells_m20.py -q -> 44 passed in 0.95s` (approved external read/write of pytest temp directories; no `--basetemp`).

The same pytest command without the temp-root override was attempted first: `39 passed, 5 setup
errors` from `WinError 5` scanning `.test_tmp\pytest-of-devbox`; it is not test evidence and was
re-run successfully with the documented override.

**Live commands:** the full 17-document command completed with exit 0 in 445.4s; the separate
`form_2441_2025` command completed with exit 0 and `ValueError: unknown manifest document_id`.
The two identical 1040 commands each completed with exit 0 in 47.8s and 44.4s. No code or graph
artifact changed. No source fix is authorized by S33; the next round should size the six forms with
zero or partial derivation and decide whether the `form_2441_2025` projection belongs in this
harness input set.

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

- **M20-S33 TASK - RUN THE WHOLE CORPUS AND REPORT EVERY FORM (Architect, Claude Opus 5,
  2026-08-02).** Ledger: the RAN/NOT RUN rule, D9, D6, D10.

  **Why now.** Three forms are green: 17/17, 7/7, 3/3, zero failures, zero warnings. The harness is
  document-agnostic, an empty result is loud, and the prompt renders. Every reason we had for
  staying on a slice is gone. There are 18 documents in the graph and we have numbers for three.
  **The remaining fifteen are the unflattering metric.**

  **Step 1 - run every document in the 2025 graph.** Not a curated list - enumerate what the graph
  actually contains and run all of it, so a form cannot be quietly left out of the report. Expect
  forms that derive nothing: `form_w2_2025` and the 1099s are input documents with no computed
  lines, and `status: empty` is the CORRECT answer for them. That is why S31 step 2 exists.

  **Step 2 - report the table, one row per document**, with: document id, status, attempted,
  derived, repaired, gapped, errored, `outline_node_count`, `line_anchor_count`, and the top three
  `validator_failures_by_kind`. **Lead with `derived` per form, and put the totals last, not
  first.** A corpus total is the number most likely to flatter us; the per-form column is the one
  that tells us where the pipeline stops working.
  **Sort the table by derived-over-attempted ascending, worst first.** The reader should hit the
  problems before the successes.

  **Step 3 - separate the three kinds of zero, because they mean different things.**
  a. **Correctly empty** - an input document with no computed lines. Expected, not a defect.
  b. **Empty but should not be** - the form has computed lines and the frame found none. This is
     the Schedule D signature and it is a real finding.
  c. **Attempted but nothing derived** - the frame found rows and every one failed. A model or
     evidence problem, and the failure kinds say which.
  For every (b) and (c), report the form, the counts, and the top failure kinds. **Do not fix them
  this round.** Diagnosis sizes the next rounds; attempting fixes across an unknown number of forms
  in one round is how a round turns into a swamp.

  **Step 4 - run the 1040 twice** with the identical command and report both results. We have four
  data points suggesting nondeterminism has settled into the top band, and the corpus run is the
  right moment to confirm it cheaply. **Report both numbers even if identical.** If line 16 on
  Schedule D flips between runs, say so - that is the trigger for a code-side operand normaliser.

  **On cost:** the three-form slice was roughly two to three minutes of provider time. The full
  corpus is a modest multiple of that, and the information is worth it. If any single document
  turns out to be pathologically large, report it and stop rather than looping.
  If approved external network is unavailable, declare the whole round NOT RUN up front and hand
  back - the Architect will run it. Do not burn the round on `Connection error`.

  **Do not:** fix any form's derivation this round; relax any validator to improve a number; add a
  retry policy; add an operand normaliser (that waits on step 4's evidence); add any per-document
  special case; promote anything.
  **Stop conditions:** any diff in the protected directories; `derive_cells` acquiring a disk
  write; any harness output landing inside the repository.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, preflight with `legacy_mined` explicit (394), strict citations (36).
  **ONE local commit** - or say up front why it is more; no push.

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

- **M20-S32 (`70e8b6d`, Architect-verified):** prompt placeholders moved from `{name}` to
  `<<name>>` with a shared fail-closed `render_prompt`, so JSON examples need no escaping; the
  substring prompt assertion was replaced by a render test over every file in `prompts/`.
  Architect slice: 1040 17/17, Schedule A 7/7, **Schedule D 3/3**.
- **M20-S31 (`fb2833e`, `a466a9e`; step 3 `e18767f` rejected):** Schedule D carve-out deleted and
  `document_id` dropped from `_formula_outline_nodes`; a zero-row document now reports
  `status: empty` with outline and anchor counts. Step 3's prompt edit broke rendering for every
  form and was superseded by S32.
- **M20-S30 (`00b5f38`, Architect-verified):** harness takes repeatable `--document`, refuses
  in-repo output, and reports per-document failures; REQUIRE_INPUT self-operands exempt from
  `operand_not_in_quote`. Architect slice: 1040 17/17, Schedule A 7/7, Schedule D 0 - the zero
  traced to a hardcoded carve-out, 2/3 with it lifted.
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

- **M20-S32 (2026-08-02, Architect):** live three-form slice all green - `form_1040_2025` 17/17,
  `schedule_a_2025` 7/7, `schedule_d_2025` 3/3, zero validator failures and zero warnings on all
  three; 102 passed on a short temp root; protected set byte-identical.
- **M20-S30 (2026-08-02, Architect):** live three-form slice - `form_1040_2025` 17/17,
  `schedule_a_2025` 7/7 (matches the S14 labeled set), `schedule_d_2025` 0 attempted;
  `operand_not_in_quote` 0 on both non-empty forms; protected set byte-identical; working tree
  clean after the in-memory carve-out probe.
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
