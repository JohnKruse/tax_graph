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

**BALL: WORKER - M20-S34 (STOP LYING TO THE MODEL ABOUT THE FORM).** Task block under
**From Architect**. **S33 is ACCEPTED at `771d169`.**

## Current round

**M20-S33 ACCEPTED (Architect, Claude Opus 5, 2026-08-02) at `771d169`.** The Worker ran the whole
corpus live, reported every document including the one that would not load, and ran the 1040 twice
as asked. No source, promoted artifact, or verdict changed. Gates green; protected set untouched.

**THE CORPUS RESOLVES 93 OF 94 ROWS.** attempted=94, derived=79, repaired=14, gapped=0, errored=1.
Zero gapped is the number that matters most: no row failed after its repair.

**ARCHITECT CORRECTION TO ITS OWN SPEC - the requested sort is misleading.** S33 asked for the
table sorted by `derived / attempted` worst first. That puts `schedule_1_2025` at the top as "0 / 4
(0%)" when all four of its rows SUCCEEDED after one repair each. `repaired` is a success status -
it has been since S25 - so schedule_1 is 4/4, exactly like the 1040. The honest ranking is
`(derived + repaired) / attempted`, with the repair RATE reported alongside as the quality signal.
Read that way the corpus is:

| document | resolved / attempted | needed repair | note |
| --- | ---: | ---: | --- |
| `form_6251_2025` | 28 / 29 | 5 | the only errored row in the corpus |
| `schedule_1_2025` | 4 / 4 | 4 (100%) | every row needed a repair |
| `schedule_3_2025` | 4 / 4 | 2 | |
| `schedule_2_2025` | 5 / 5 | 2 | |
| `schedule_1a_2025` | 24 / 24 | 1 | |
| `form_1040_2025`, `schedule_a_2025`, `schedule_d_2025`, `schedule_b_2025` | 28 / 28 | 0 | clean |

**Zero classification is correct and complete.** The eight empty documents are the four 1099/W-2
inputs, 13614-C, 8949, and the two instruction documents - all correctly empty. **No document was
empty-but-should-not-be.** That is the Schedule D check passing corpus-wide, and it is the single
most reassuring line in the report.

**ROOT CAUSE OF THE REPAIRS - `operand_not_printed`, and it is our defect, not the model's.**
82 occurrences concentrated on schedules 1, 2, 3 and 1a. Architect diagnosed it deterministically
against real data. **The printed-line inventory is complete** - every line Schedule 1 references is
in it, so this is NOT the S27 inventory gap returning. The cause is that **IRS lettered ranges have
holes, and the model is asked to guess which**:

- `9 Total other income. Add lines 8a through 8z` - **8w, 8x and 8y are not printed.**
- `25 Total other adjustments. Add lines 24a through 24z` - **24l through 24y are not printed**, 14
  of them.
- `26 Add lines 11 through 23 and 25` - **line 19 is not printed.**

That is 18 impossible operands on Schedule 1 alone against a reported `operand_not_printed=19`.

**AND HERE IS THE ACTUAL DEFECT: `validate_cell_output` checks operands against a printed-line
inventory that `_render_cell_prompt` never shows the model.** The prompt supplies `form`, `line`,
`label`, `form_face_text`, `instruction_text` and `instruction_locator` - no inventory. So the
model is required to produce members of a closed set it cannot see, it expands "8a through 8z" the
only way anyone would, and the validator rejects the letters the IRS happened to skip. Repair then
succeeds because the failure message finally tells it what the set is. **We are paying a model
round-trip per row to communicate a list we already have.** Fix in S34.

**Repeatability confirmed.** Two identical 1040 runs both returned attempted=17, derived=17,
repaired=0, gapped=0, errored=0, no validator failures. **Schedule D line 16 did not flip**, so the
S32 prompt fix holds across runs and no operand normaliser is needed on this evidence.

**BLOCKED - `form_2441_2025` is a phantom document, and this needs John.** It fails with
`ValueError: unknown manifest document_id`. Diagnosed: `graph/2025/documents/` declares exactly 17
documents, but `validate 2025` reports 18 because `graph/2025/field_maps/form_2441_2025.yaml`
carries a `document_id` for a form that was never acquired. Its field map has `mappings: []` and
its nodes are marked `optional_extension: true` with "no base-profile printable placement", and it
is referenced from the 1040 and Schedule 3 addresses and citations. **So the graph knows about
Form 2441 as an optional extension but has no source document for it, and the extraction manifest
correctly refuses to invent one.** The Worker's handling was right - reported with a reason rather
than crashed or skipped, which is exactly the S31 D10 behaviour working. **This is a scoping
question, not a bug: is Form 2441 in the base profile or not?** If yes it must be acquired like any
other form; if no, the field map should not be contributing a document id to the count. Do not
guess - see Open for Architect.

**JOHN WAS RIGHT ABOUT THE TRAILING LINE TOKENS (raised 2026-08-02). I underplayed this and did
not re-check it corpus-wide.** He repeatedly flagged labels shaped like `Add lines 24a through 24g
24z` and believed they had been fixed. History: **S26** removed them by RECONSTRUCTING - moving the
line token from the end to the front. **S29** stopped the reconstruction, on Architect instruction,
because storing a reconstructed string as evidence broke the provenance rule that evidence text
must be a literal substring of the acquired text. That brought the trailing tokens back. It was
disclosed at the time and recorded as a deliberate trade-off - **but it was described as
"cosmetic", verified on only the 1040's two rows, and never re-measured across the corpus.**

**Measured now: 8 labels across the corpus still carry the trailing token**, and the framing of
"provenance versus cosmetics" was a FALSE DILEMMA. Truncating from BOTH ends gives both: no
reordering, and no trailing token.

| document | rows affected |
| --- | --- |
| `form_1040_2025` | `1z`, `25d` |
| `schedule_a_2025` | `5d`, `8e` |
| `schedule_2_2025` | `1z` |
| `schedule_1a_2025` | `2e`, `14c`, `36b` |

**AND IT IS NOT ONLY COSMETIC - the cleaner DESTROYS real form text on at least one row.**
`clean_form_face_text` truncates from the FIRST occurrence of the anchor token. When the printed
line number sits in a right-hand column, the only occurrence is at the END, so everything before it
is discarded:

- `schedule_1a_2025` line `36b`: raw `your spouse was born before January 2, 1961, enter the amount
  from line 35 36b` cleans to **`36b`** - 4% of the text kept, the entire label gone.
- `form_6251_2025` line `32`: raw `Internal Revenue Service Go to www.irs.gov/Form6251 ... 32`
  cleans to **`32`**. Different defect - the SPAN MATCHER selected page-header text for line 32, so
  the real label was never in the span. Cleaning is not the culprit here; span selection is.

Content loss is the founding defect of M20 (`PHASE_M20.md` section 1). A cleaner that silently
drops a whole label is the same class of bug as the 52%-retention renderer, on a smaller surface.

**ARCHITECT PROPOSAL, PARTIALLY TESTED - and the first version was WRONG.** Tried: keep whichever
truncation retains more text. **Rejected - it regressed 4 rows**, restoring neighbour
contamination on `form_1040_2025` lines 22, 34 and 37 (`12a, 12b, 12c, 22 Subtract...`,
`Refund 34 If line 33...`) because on those rows the extra text IS the contamination. Text length
is the wrong discriminator.
**Corrected rule - discriminate on WHERE the anchor sits, not on length:** if some occurrence of
the anchor has descriptive text AFTER it, the label starts there - truncate from the first such
occurrence and drop a repeated trailing token (today's behaviour, correct for lines 22, 34, 37).
If the anchor occurs ONLY as the final token, it is a right-column artifact - keep the preceding
text, dropping a split leading suffix and the trailing anchor (correct for `1z`, `25d`, `5d`, `8e`,
`2e`, `14c`, and crucially `36b`). Both branches only ever TRUNCATE, so the S29 substring guarantee
holds in every case. This is reasoned and spot-checked, **not fully re-run - the Worker must
implement it against tests rather than take it on trust.**

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

- **M20-S34 TASK - SHOW THE MODEL THE PRINTED LINES (Architect, Claude Opus 5, 2026-08-02).**
  Ledger: the RAN/NOT RUN rule, D9, D6. **Deterministic work plus one measurement round.**

  **Why.** The corpus resolves 93 of 94 rows, but 14 of them cost an extra model round-trip to
  `operand_not_printed`, and that failure is ours. `validate_cell_output` checks every operand
  against the printed-line inventory; `_render_cell_prompt` never puts that inventory in the
  prompt. The model is asked to name members of a closed set it cannot see. When a label says
  `Add lines 8a through 8z` it expands the range the only sensible way, and the IRS has skipped
  8w, 8x and 8y - so we reject it, then spend a repair telling it what we knew all along.

  **Step 1 - fix `clean_form_face_text` so it stops destroying labels (deterministic, no model
  calls). Do this first; it is content loss, which outranks everything else in M20.**
  Discriminate on WHERE the anchor sits, not on how much text a branch keeps - the Architect tested
  a length-based tiebreak and it regressed lines 22, 34 and 37 by restoring neighbour
  contamination. Rule: if any occurrence of the anchor has descriptive text after it, the label
  starts there - truncate from the first such occurrence and drop a repeated trailing token. If the
  anchor occurs ONLY as the final token, it is a right-hand-column artifact - keep the preceding
  text, dropping a split leading suffix and the trailing anchor. **Both branches must only
  TRUNCATE**, so the S29 rule that evidence text stays a literal substring of the acquired text
  holds unconditionally. Add a test asserting the substring property for every formula row in the
  corpus, and table-driven cases for all of these, which are the real strings:
  - `z Add lines 1a through 1h 1z` (1040 `1z`) -> `Add lines 1a through 1h`
  - `d Add lines 25a through 25c 25d` (1040 `25d`) -> `Add lines 25a through 25c`
  - `e Add lines 8a through 8c 8e` (Sch A `8e`) -> `Add lines 8a through 8c`
  - `c Add lines 14a and 14b 14c` (Sch 1A `14c`) -> `Add lines 14a and 14b`
  - `your spouse was born before January 2, 1961, enter the amount from line 35 36b` (Sch 1A `36b`)
    -> the sentence WITHOUT the trailing `36b`, **not** `36b`
  - `12a, 12b, 12c, 22 Subtract line 21 from line 18. If zero or less, enter -0- 22` (1040 `22`)
    -> `22 Subtract line 21 from line 18. If zero or less, enter -0-` (unchanged - do not regress)
  - `Refund 34 If line 33 is more than...` (1040 `34`) -> starts at `34` (unchanged)
  **Report the corpus count of labels still ending in their own line token. It is 8 today and the
  target is 0.**

  **Step 2 - put the printed-line inventory in the prompt.** `build_cell_frame_from_document`
  already carries `printed_lines` in row metadata and the validator already uses it. Add it to the
  values passed by `_render_cell_prompt` and reference it from `prompts/derive_cells.md` with the
  new `<<name>>` syntax. State plainly in the prompt that operands naming a line on THIS form must
  come from that list, and that a printed range may skip entries - `8a through 8z` means the
  members that are actually printed, not every letter.
  **Order the list the way the form does** (use the existing `_line_sort_key`), and do not
  truncate it - Schedule 1 has 61 anchors and the 1040 has 59, which are small.

  **Step 3 - do NOT silently filter operands in code.** The tempting shortcut is to intersect the
  model's operands with the inventory and drop the rest. **Do not.** That would mask a genuine
  wrong-line answer as a clean derivation. `operand_not_printed` stays exactly as strict as it is
  now; the point of step 1 is that it should stop firing because the model was told the truth, not
  because we stopped checking.

  **Step 4 - measure, and report the repair rate as the headline.** Rerun the full corpus. Report
  per document: resolved `(derived + repaired) / attempted`, **the repair count and rate**,
  errored, and the top three `validator_failures_by_kind`. **Sort by repair rate descending, worst
  first** - not by derived, which mis-ranked schedule_1 last round as 0% when it was 4/4.
  **The number to beat: 14 repairs across the corpus, 82 `operand_not_printed` occurrences, 4/4
  repairs on `schedule_1_2025`.** If those do not fall materially, step 1 did not work and the
  diagnosis was wrong - say so plainly rather than tuning the prompt until it looks better.
  Also report `form_6251_2025`, the only errored row in the corpus, with its failure kind. It is
  not this round's target, but it should stop being invisible.

  **Also report, do not fix:** `form_6251_2025` line 32 cleans to `32` because the SPAN MATCHER
  selected page-header text (`Internal Revenue Service Go to www.irs.gov/Form6251 ...`) for that
  row. That is a span-selection defect, not a cleaning defect, and it is the likely cause of the
  corpus's only errored row. Name it in the report so it can be sized as its own round.

  **On the provider leg:** if approved external network is unavailable, do steps 1-3, declare step
  4 NOT RUN up front, and hand back - the Architect will run it.

  **Do not:** filter or normalise operands to make the check pass; relax any validator; add a
  retry policy; add a per-document special case; touch `form_2441_2025` (blocked on John, see Open
  for Architect); promote anything.
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
