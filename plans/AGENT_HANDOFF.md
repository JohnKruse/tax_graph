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

**BALL: WORKER - M20-S36 (ASSEMBLE THE WHOLE ROW BEFORE DERIVING).** Task block under
**From Architect**. **S35 is ACCEPTED at `9d53d54`.**

## Current round

**M20-S35 ACCEPTED (Architect, Claude Opus 5, 2026-08-03) at `9d53d54`.** The Worker diagnosed and
reported the count BEFORE writing the fix, as instructed - 1 of 29 rows on `form_6251_2025`, 0 of
14 on every other loadable document - which is what made this a targeted fix rather than an
architecture round. Step 3 was correctly declared NOT RUN; the Architect ran the provider leg.

**THE CORPUS IS AT ITS BEST MEASURED STATE.**

| round | attempted | derived | repaired | gapped | errored | resolved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| S33 | 94 | 79 | 14 | 0 | 1 | 93 |
| S34 | 94 | 86 | 4 | 0 | 4 | 90 |
| **S35** | 94 | **89** | **3** | **0** | **2** | **92** |

Resolution recovered 90 -> 92, and **first-attempt correctness is at an all-time high: derived 79
-> 89.** S33's 93 resolved leaned on 14 repair round-trips; S35's 92 needs 3. Eight of the nine
derivable documents are now perfectly clean on the first attempt, including `schedule_1a_2025`,
which was 22/2 last round and is 24/24 now.

**The span fix hit exactly what it aimed at.** `form_6251_2025` recovered from 25/29 and 26/29
across two S34 runs to **27/29 and 26/29** across two S35 runs, and `quote_not_verbatim` - 3
occurrences last round, including the page-header row - is **gone**. `_span_for_line` now filters
duplicate printed anchors by the outline page and rejects a candidate that lacks the row label's
descriptive tokens, failing closed rather than returning a wrong span. No document-id special case
was added.

**Verified the Worker's honesty claim rather than taking it.** It reported
`tests/test_schedule_d_extraction_m9.py` as 1 failed / 2 passed and attributed it to a pre-existing
Schedule D expectation. Architect bisected the single changed file: the test fails IDENTICALLY with
the S35 resolver reverted. The attribution is correct. **It is now a fourth known-red baseline
entry** - see Standing constraints.

**CORRECTION, SECOND PASS (2026-08-03). The real defect is LABEL TRUNCATION, and both of my
earlier diagnoses of 6251 were wrong.** I called the remaining failures "model quality", then "an
unmodelled worksheet plus an expression-grammar limit". Neither holds. **We capture ONE PHYSICAL
LINE of the page and stop**, so rows whose text wraps are handed to the model as fragments.

**Measured: 16 of 94 formula rows corpus-wide have a label cut off mid-row.**

| document | truncated rows |
| --- | ---: |
| `form_6251_2025` | 9 |
| `schedule_d_2025` | 2 |
| `schedule_1_2025` | 2 |
| `schedule_1a_2025` | 2 |
| `schedule_2_2025` | 1 |

**All five remaining 6251 failures sit on truncated rows.** The decisive case is line 18. We
capture `If line 17 is $239,100 or less (...), multiply line 17 by 26% (0.26).` and drop the
continuation `Otherwise, multiply line 17 by 28% (0.28) and subtract $4,782 ($2,391 if married
filing separately) from the result`. The recorded failure was
`ValueError: IF_ELSE requires exactly 4 arguments` - **the model could not supply the else-branch
because we never showed it the else-branch.** That is not a grammar gap. Line 20 ends on the word
`from`; its continuation `line 14 of the Schedule D Tax Worksheet, whichever applies` is present in
our own text layer and simply never attached. The worksheet-not-modelled finding stands but is
SECONDARY - the model could not see the full reference either.

**JOHN'S POINT, and it is the strongest argument for the second witness so far (2026-08-03).** He
produced the Mistral OCR of 6251 and every one of these rows is complete in it, assembled into one
logical row. Joining wrapped lines is precisely what OCR does well and what our geometry pass does
not do at all. **And the disagreement is machine-checkable WITHOUT trusting OCR:** if our captured
label is a strict prefix of OCR's row text and OCR's row is longer, that is a truncation finding.
We do not need OCR to be right - we need it to disagree in a detectable direction. That is a
deterministic check sitting on top of a nondeterministic witness, and it would have flagged all 16
rows automatically. He also noted, fairly, that we had already agreed to use OCR this way and I
went on hand-diagnosing instead.

**NEXT ROUND IS NOW OBVIOUS AND DETERMINISTIC: assemble the whole logical row before deriving.**
The continuation text is already in `document.text` - this is an assembly defect, not an
acquisition one. Fix that first; the worksheet-addressing question (below) is only worth answering
once the model can see the full reference.

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
  - `test_schedule_d_extraction_m9.py::test_schedule_d_fixture_drafts_include_schema_valid_band_tables`
    (added 2026-08-03; Architect bisected it against the S35 resolver change and it fails
    identically with that change reverted, so it predates S35)
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

- **FOR JOHN - what is next, now that derivation is done? (raised 2026-08-03.)** The corpus
  resolves 92 of 94 rows with 3 repairs, and the only remaining failures are model-quality issues
  on `form_6251_2025`. Chasing those means tuning a nondeterministic model for 2 rows, which is a
  poor trade. Three candidates, and it is a product call:
  **(a) The standalone reviewer.** Package the workbench so colleagues can review a form without a
  dev setup. Needs the three-tier verdict vocabulary (accepted / commented-questioned / rejected)
  and one proven round trip: a comment that survives a pipeline regeneration and shows up as input
  on the next run. That round trip has never actually happened, and it is the prime directive's
  core loop.
  **(b) Structure and association, S3b.** The geometric label path and the AcroForm-tree skeleton,
  which is what would make the 13614-C class of form reviewable at all. Today it derives nothing
  because it has no computed lines, but 297 of its cells are unaddressable by line number.
  **(c) The checker.** Adjudicate disagreements between the AcroForm tree, the geometry and OCR,
  and route them to a findings queue. John's view: set it up, then decide the payload from real
  disagreement instances rather than designing it in advance.
  Architect's recommendation is **(a)**, because it closes the human loop that everything else
  feeds, and because the reviewer surface is what turns (b) and (c) into something a person can
  act on.
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

- **M20-S36 TASK - ASSEMBLE THE WHOLE LOGICAL ROW BEFORE DERIVING (Architect, Claude Opus 5,
  2026-08-03).** Ledger: the RAN/NOT RUN rule, D9, D6. **Deterministic. No model calls in steps
  1-3.**

  **The defect, located precisely.** `build_outline_tree` (`tax_graph/extract/outline.py:191`)
  walks `document.text.splitlines()`. A line matching `LINE_RE` becomes an `OutlineNode` with
  `label=body`, where body is the remainder of **that one physical line**
  (`outline.py:242`). Any line that does not match is **skipped outright**
  (`outline.py:226-227`). So when a printed row wraps, every continuation line is DISCARDED - not
  truncated at the edges, dropped from the outline entirely. The text is present in
  `document.text`; we simply never attach it. **This is an assembly defect, not an acquisition
  one - no OCR and no model is needed to fix it.**

  **Measured impact: 16 of 94 formula rows corpus-wide** - `form_6251_2025` 9,
  `schedule_d_2025` 2, `schedule_1_2025` 2, `schedule_1a_2025` 2, `schedule_2_2025` 1. **All five
  remaining 6251 failures sit on truncated rows.** The decisive case is line 18: we keep
  `If line 17 is $239,100 or less (...), multiply line 17 by 26% (0.26).` and drop
  `Otherwise, multiply line 17 by 28% (0.28) and subtract $4,782 ($2,391 if married filing
  separately) from the result`. The recorded failure was `IF_ELSE requires exactly 4 arguments` -
  the model could not supply an else-branch it was never shown.

  **Step 1 - assemble continuation lines into the row body.** After a `LINE_RE` match, consume
  following lines that are NOT a new line anchor, NOT a `Header:` line, NOT a page marker, and not
  blank, appending them to the body. Stop at the first line that is any of those.
  **Two traps, both of which have already cost this project a round:**
  a. **Keep the evidence span consistent with the label.** `_span_for_line` returns a span whose
     text is a single line. If the prompt shows an assembled label while `validate_cell_output`
     checks the quote against a one-line span, **every quote on an assembled row fails
     `quote_not_verbatim`** - the exact prompt-shows-X / validator-checks-Y defect from S28. The
     evidence span for an assembled row must carry the assembled text.
  b. **State the substring rule in normalized terms.** Joining source lines with a single space
     reproduces the source modulo the newline, so the S29 guarantee still holds as "a literal
     substring of the acquired text **after whitespace normalization**" - which is what
     `clean_form_face_text` already does with `" ".join(text.split())`. Do NOT reorder or
     reconstruct; joining adjacent lines in source order is not reordering.

  **Step 2 - assert the outline shape did not change.** Assembling continuations must not create,
  merge, or lose nodes. Per-document `outline_node_count` and `line_anchor_count` must be
  IDENTICAL to today: `form_1040_2025` 60/59, `schedule_a_2025` 29/28, `schedule_d_2025` 31/24,
  `schedule_1_2025` 66/61, `schedule_2_2025` 52/45, `schedule_3_2025` 38/35,
  `schedule_1a_2025` 60/48, `form_6251_2025` 68/63, `schedule_b_2025` 12/8. Add a test asserting
  these. **A changed count means the assembler swallowed a row - stop and report rather than
  adjusting the expected numbers.**

  **Step 3 - report the truncation count, which is the round's headline. It is 16 today and the
  target is 0.** The check: find the captured label in `document.text`, and look at the next
  non-blank line; if it does not begin a new printed anchor, the row was truncated. Report the
  per-document table in the same shape as above. Also report, without fixing, any row where
  assembly makes the label materially longer - those are the rows whose derivation should change.

  **Step 4 - rerun the full derivable corpus once and `form_6251_2025` twice.** Report per
  document: attempted, derived, repaired, errored, and the top three `validator_failures_by_kind`.
  **The numbers to beat: corpus resolved 92/94 with derived=89 and repaired=3; 6251 resolved 27/29
  and 26/29 across two runs.** Report both 6251 runs even if identical.
  **Expect `payload` on lines 18 and 39 to disappear** - those are the pure else-branch cases. The
  worksheet rows (13, 20, 27) may still fail; that is the separate addressing question and it is
  NOT this round's target. Say plainly which of the five resolved and which did not.
  If approved external network is unavailable, do steps 1-3, declare step 4 NOT RUN up front, and
  hand back - the Architect will run it.

  **Do not:** relax `quote_not_verbatim`, `self_reference`, `operand_not_printed` or any other
  check to accommodate assembled text; add a retry policy; model the Qualified Dividends worksheet
  (separate scoping question, blocked on John); add any per-document special case; reintroduce
  reordering into `clean_form_face_text`; promote anything.
  **Stop conditions:** any diff in the protected directories; `derive_cells` acquiring a disk
  write; any harness output landing inside the repository; a `startswith` on a document id
  anywhere; a change in the per-document outline counts in step 2.
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
