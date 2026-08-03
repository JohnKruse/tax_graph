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

**BALL: WORKER - M20-S35 (FIX THE SPAN MATCHER ON FORM 6251).** Task block under
**From Architect**. **S34 is ACCEPTED at `66a6d60`.**

## Current round

**M20-S34 ACCEPTED (Architect, Claude Opus 5, 2026-08-03) at `66a6d60`.** Steps 1-3 delivered;
the Architect ran step 4. The cleaner fix follows the specced rule exactly - discriminate on
whether the anchor has descriptive text after it, and truncate in both branches, never reorder.
Gates: 107 passed on a short temp root, ASCII OK, `validate 2025` clean, protected set
byte-identical.

**THE TARGETED DEFECT IS GONE. `operand_not_printed` 82 -> 2, repairs 14 -> 4.**

| document | attempted | derived | repaired | errored | was (S33) |
| --- | ---: | ---: | ---: | ---: | --- |
| `form_1040_2025` | 17 | 17 | 0 | 0 | 17 derived |
| `schedule_1_2025` | 4 | **4** | **0** | 0 | **0 derived, 4 repaired** |
| `schedule_2_2025` | 5 | **5** | **0** | 0 | 3 derived, 2 repaired |
| `schedule_3_2025` | 4 | **4** | **0** | 0 | 2 derived, 2 repaired |
| `schedule_1a_2025` | 24 | 22 | 2 | 0 | 23 derived, 1 repaired |
| `schedule_a_2025`, `schedule_d_2025`, `schedule_b_2025` | 11 | 11 | 0 | 0 | unchanged, clean |
| `form_6251_2025` | 29 | 23 | 2 | **4** | 23 derived, 5 repaired, 1 errored |

Schedule 1 is the headline: every row needed a repair last round, none does now. Schedules 2 and
3 are also clean. **Showing the model the printed-line inventory it was being validated against
did exactly what the diagnosis predicted.**

**LABEL DESTRUCTION IS FIXED, measured the same way it was found.** Trailing-token labels across
the corpus **8 -> 0**. Rows keeping under 60% of their source text **3 -> 1**, and the survivor is
correct behaviour (`form_1040_2025` line 21 drops the `a box on line` neighbour contamination).
`schedule_1a_2025` line `36b` recovers its full label - `your spouse was born before January 2,
1961, enter the amount from line 35` - where it previously cleaned to the bare token `36b`.

**THE UNFLATTERING NUMBER: corpus resolution went 93/94 -> 90/94, and all of the loss is on
`form_6251_2025`.** Resolved means derived plus repaired. Two Architect runs of 6251 agree it
declined - 25/29 and 26/29 against S33's 28/29 - so this is not a single bad draw, though 6251 has
been the least stable form in the corpus throughout. Failing rows in run 1: lines 13 and 32
`quote_not_verbatim`, lines 20 and 27 `self_reference`.
**At least one of those is directly attributable to S34.** Line 32's span is page-header text
(`Internal Revenue Service Go to www.irs.gov/Form6251 ...`); under the old cleaner it truncated to
the bare token `32`, and under the new rule it keeps the header as the label. Neither is right -
the SPAN is wrong, not the cleaning - but the model now has plausible-looking junk to quote instead
of an obviously empty label. **This is the span-selection defect recorded in S33, now surfaced
rather than hidden, and it is S35.**

**Process note:** the Worker's commit swept up an uncommitted Architect edit to this file (the
verdict-vocabulary supersession). Architect's fault for leaving it in the tree at handoff; the
content was correct and intended. Workers: `git status` before committing, and do not commit paths
you did not touch.

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
  concatenated).
- **VERDICT VOCABULARY - SUPERSEDED 2026-08-02. The four-button scheme is RETIRED.** John withdrew
  his own earlier ruling that "Pipeline defect" vs "Source pathology" is the reviewer's
  distinction, and he is right: **that is a DIAGNOSIS, and a reviewer has no way to make it.**
  Verbatim: *"as a human, i have zero insight into the why. I just know that this
  instruction/cell label is wrong."* Asking a reviewer to classify cause yields guesses carrying
  false authority.
  **The scheme is three OBSERVATIONS, not causes: accepted / commented-questioned / rejected.**
  That is already an ordinal confidence scale - the middle tier is "something looks off and I am
  not certain" - so do NOT add a separate numeric confidence field on top of it.
  **Reviewers are instructed NOT to comment when a cell is fine.** John: *"the last thing I would
  want is some guy saying 'good entry', 'this looks ok'."* Accept must be a single cheap action
  with no text box; the comment box appears only for the other two tiers, and **text is REQUIRED
  for those two** - a bare "rejected" is as useless as a cause the reviewer had to invent.
  Silence-as-approval is safe only if the queue records what was PRESENTED as well as what was
  acted on, so "reviewed and fine" stays distinguishable from "never shown".
  Diagnosis moves downstream to where the evidence lives: the checker proposes the cause from the
  witness disagreement, the maintainer confirms. **Reviewer detects; pipeline diagnoses.**
  Current code accepts only `confirmed`/`rejected` (`workbench/static/app.js`), so the middle tier
  is missing. The ledger is already address-keyed and append-only, so adding it is small.

## Open for Architect

- **FOR JOHN - is Form 2441 in the base profile? (raised 2026-08-02, blocks nothing else.)** The
  graph counts 18 documents but only 17 exist: `graph/2025/field_maps/form_2441_2025.yaml` carries
  a `document_id` for a form that was never acquired, its `mappings` are empty, its nodes are
  marked `optional_extension: true` with no base-profile printable placement, and the 1040 and
  Schedule 3 reference it in addresses and citations. Two coherent answers, and it is a product
  call rather than a technical one:
  **(a) Yes, 2441 is in scope** - acquire the PDF like any other form, give it a document record,
  and it joins the corpus and the derivation runs.
  **(b) No, it is an optional extension** - then the field map should stop contributing a document
  id to the count, so `validate 2025` reports the 17 documents that actually exist and no future
  corpus run trips over a phantom.
  Nothing is broken either way: the harness reports it as a load failure with a reason rather than
  skipping it silently, which is the S31 D10 behaviour doing its job.

## From Architect

- **M20-S35 TASK - FIX THE SPAN MATCHER ON FORM 6251 (Architect, Claude Opus 5, 2026-08-03).**
  Ledger: the RAN/NOT RUN rule, D9, D6. **Diagnose first, then fix. Small round.**

  **Why.** `form_6251_2025` is the only form that got worse in S34 and the only one carrying
  errors. Its line 32 evidence span is the PAGE HEADER - `Internal Revenue Service Go to
  www.irs.gov/Form6251 for instructions and the latest information. 32` - so no amount of label
  cleaning can help; `_span_for_line` picked the wrong region of the page. S34 changed the symptom
  (bare token `32` became header text) without touching the cause.

  **Step 1 - diagnose, and report before fixing.** For every 6251 row, print the selected span and
  say how `_span_for_line` chose it. Report specifically: how many 6251 rows have a span whose text
  does not contain the row's own printed line token in a plausible label position, and whether the
  same condition occurs on any other form. **Write the count in this file before writing the fix**
  - if it is one row this is a targeted fix, and if it is eight it is an architecture problem and
  the round changes shape.

  **Pre-fix diagnosis (2026-08-03):** the 29-row 6251 inventory was printed with the exact command
  below. One row, line 32 (1/29), selected the page-1 header span `Internal Revenue Service Go to
  www.irs.gov/Form6251 for instructions and the latest information. 32`; it was selected because
  the resolver collected all exact `32` anchor offsets and returned the first source span whose text
  line matched any of them. The row's outline page is 2 and its label is `32 Add lines 23 and 30 32`.
  The same outline-label mismatch occurred in 0/14 other loadable documents, including 0/8 other
  documents with formula rows. The full per-row selection table is the command output recorded in
  the Worker session:
  `.venv\\Scripts\\python.exe -` with the 6251 inventory script.

  **Step 2 - fix the selection, not the symptom.** A span that is page header, footer, or a
  different section is not a candidate for a row's label. Use what is already available - the
  printed-line inventory, the row's own anchor, and the outline node - to reject a span that cannot
  belong to this row. **Fail closed: a row with no plausible span must report that, not fall back
  to a wrong one.** An honestly empty label is better than page-header text, because the empty one
  is visible and the junk one is not.
  **Do not** special-case `form_6251_` or any document id - that is the S31 carve-out defect and it
  is a stop condition.

  **Step 3 - rerun 6251 twice and the full derivable corpus once.** Report per document: attempted,
  derived, repaired, errored, and the top three `validator_failures_by_kind`. **The numbers to
  beat: 6251 resolved 25/29 and 26/29 across two runs; corpus resolved 90/94.** S33's 6251 was
  28/29, so that is the bar to recover. Report both 6251 runs even if identical - it is the least
  stable form in the corpus and one run proves nothing about it.
  **Do not chase the other three 6251 failures this round** (lines 13, 20, 27 -
  `quote_not_verbatim` and `self_reference`) unless the span fix happens to resolve them. Report
  whether it did.

  **On the provider leg:** if approved external network is unavailable, do steps 1-2, declare step
  3 NOT RUN up front, and hand back - the Architect will run it.

  **Worker status (2026-08-03):** Step 1 is `[DONE]`: the targeted count is 1/29 on 6251 and
  0/14 on the other loadable documents. Step 2 is `[DONE]`: `_span_for_line` now filters duplicate
  printed anchors by the outline page from the field inventory, resolves the resulting text line,
  and rejects candidates without row-label context. No document-id special case was added. The
  regression set includes the duplicate-header case, fail-closed rejection, and the real 6251
  line-32 frame.

  Step 3 is `NOT RUN`: live provider access is unavailable in the Worker sandbox, so the two live
  6251 runs and full derivable corpus run were not attempted. The Architect must run that provider
  leg outside the sandbox.

  Focused evidence:
  `RAN: $env:PYTEST_DEBUG_TEMPROOT='C:\\Users\\devbox\\projects\\tax_graph\\.test_tmp_codex'; .venv\\Scripts\\python.exe -m pytest tests/test_outline_span_resolution_m20.py tests/test_structure_m20.py tests/test_extract_outline_m4.py tests/test_m20_s31.py tests/test_derive_cells_m20.py tests/test_extract_m16.py -q -> 87 passed, 1 warning in 6.73s`.
  `RAN: $env:PYTEST_DEBUG_TEMPROOT='C:\\Users\\devbox\\projects\\tax_graph\\.test_tmp_codex'; .venv\\Scripts\\python.exe -m pytest tests/test_schedule_d_extraction_m9.py -q -> 1 failed, 2 passed; pre-change resolver replay also produced old_resolver_prompts=3, so this is an unrelated existing expectation for Schedule D lines 7/15/16.`
  `RAN: .venv\\Scripts\\python.exe tools\\check_ascii.py -> ASCII check OK`.
  `RAN: .venv\\Scripts\\python.exe -m tax_graph.cli validate 2025 -> graph integrity OK (441 nodes, 409 edges, 401 citations)`.
  `RAN: .venv\\Scripts\\python.exe -m workbench.cli preflight --year 2025 -> passed (2224 units, 2120 derived cells, legacy_mined=394; elevated read-only ACL access)`.
  `RAN: strict citation integrity check -> checked=401 strict_mismatches=36 (known baseline)`.
  Protected directories have an empty diff.

  **Do not:** relax `quote_not_verbatim`, `self_reference`, or `operand_not_printed`; add a retry
  policy; add any per-document special case; reintroduce reordering into `clean_form_face_text`;
  promote anything.
  **Stop conditions:** any diff in the protected directories; `derive_cells` acquiring a disk
  write; any harness output landing inside the repository; a `startswith` on a document id
  anywhere in the pipeline.
  Tier 3. Declared files plus honest `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form
  `validate 2025`, preflight with `legacy_mined` explicit (394), strict citations (36).
  **ONE local commit** - and run `git status` first; do not commit paths you did not touch.

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

- **M20-S33 (`771d169`, Architect-verified):** first full-corpus live run. 93 of 94 rows resolve
  (derived=79, repaired=14, gapped=0, errored=1); all eight empty documents correctly empty; 1040
  identical across two runs. Diagnosed the repairs to `operand_not_printed` on IRS ranges with
  holes, against an inventory the prompt never shows the model.
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

- **M20-S33 (2026-08-02, Worker live, Architect-verified):** full corpus, 18 ids, 17 loadable.
  attempted=94, derived=79, repaired=14, gapped=0, errored=1. Two identical 1040 runs both 17/17
  with no validator failures. ASCII, `git diff --check`, `validate 2025` (441 nodes, 409 edges,
  401 citations), preflight `legacy_mined=394`, strict citations 36, protected set empty diff.
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
