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

**BALL: WORKER - M20-S61 (TIGHTEN "SUBSTANTIVE CONTINUATION").** Task block under
**From Architect**. **S60 is a NARROW REWORK at `1074608`** - it achieved its deliverable and
shrank the corpus, so it cannot be accepted as-is.

**THE WIN, AND IT IS A REAL ONE.** 2441 line 8 now carries **16 of 16 printed bands** and the model
emitted **all sixteen correctly** on live data - `15000/.35` through `43000/.21` plus the open top
band. **That row has never been substantively right before.** It stands at `repaired` only because
`LOOKUP_BRACKET` does not project to a rule, which is the operation-registry round. Line 19 carries
its default branch again, and every packet is still a verbatim subset of the acquired source.

**THE REGRESSION.** `row_packet_incomplete` counts page furniture as missing content - catalog
numbers, revision dates, form identifiers, and the next section's header - and the finding
suppresses the provider call. **Four rows that derived correctly in every prior run are no longer
attempted**: 2441 lines 11, 26 and 31, and 6251 line 40. Attempted across three documents went
**67 -> 63**.

**QUEUE, in order.** S61 (this rework), then S59 (nominations, already specced and John-approved),
then column and grid recovery, the versioned operation registry, deterministic phrase obligations,
and S53 (the approval gate). Each is specced when reached.

**FOR JOHN, unresolved and not blocking:** "every cell receives meaningful human approval before
use" and "a human does not read every new cell" cannot both hold during bootstrap. The pipeline can
remove **re-**review - approve once against stable semantics, fingerprint the source clauses and the
compiled meaning, carry the verdict while both are unchanged - but not first review. That is a
decision about what 98/2 means in year one.

## Current round

**M20-S61 WORKER IMPLEMENTATION COMPLETE, PENDING ARCHITECT PROVIDER LEG (2026-08-05).** The
detector now stops at the first explicit following-section boundary and ignores only identifiable
page furniture: bare numbers, page labels, split `Form (year)` footers, form-page identifiers,
catalog identifiers, and creation-date footer rows. Numeric bands and prose continuations remain
substantive. The verbatim-subset check is unchanged.

The full local manifest report used 23 manifest entries, of which 16 had form PDF/text/field
artifacts and 7 were instruction-only. Findings changed **10 -> 4**, with no new findings:

- Removed: `form_2441_2025` lines 11, 26, 31; `form_6251_2025` line 40; and the pre-existing
  boundary cases `schedule_1a_2025` line 30 and `schedule_d_2025` line 7.
- Remaining pre-existing findings: `schedule_1a_2025` lines 14a and 36a, and
  `form_6251_2025` lines 1a and 5.
- Target attempted counts: 2441 **18 -> 21**, 1040 **17 -> 17**, 6251 **28 -> 29**;
  total **63 -> 67**.
- Real continuations remain protected: 2441 lines 8 and 19 retain their complete table/rule
  text, and Schedule D line 21 retains the loss-limit continuation. Synthetic incomplete packets
  still raise `row_packet_incomplete`.

RAN: `.venv\\Scripts\\python.exe -m pytest tests/test_structure_m20.py tests/test_derive_cells_m20.py -q`
-> **92 passed in 17.50s**.
RAN: `.venv\\Scripts\\python.exe -m pytest tests/test_outline_span_resolution_m20.py tests/test_extract_outline_m4.py tests/test_extract_m16.py -q`
-> **34 passed in 3.04s**.
RAN: `.venv\\Scripts\\python.exe tools/check_ascii.py` -> **ASCII check OK**.
RAN: `git diff --check` -> **exit 0**.
RAN: `.venv\\Scripts\\python.exe -m tax_graph.cli validate 2025` -> **exit 0; graph integrity OK**.
NOT RUN: live provider leg -> Architect-owned and unavailable in the Worker's no-network sandbox.
Protected graph/field-map set: **no diff**. One local commit will contain the implementation,
tests, and this handoff evidence.

**M20-S58 ACCEPTED (Architect, Claude Opus 5, 2026-08-05) at `f21ad6b`. M20-S60 is a NARROW REWORK
at `1074608`.** Both are evidence-layer rounds and they land together.

**S58, captions, verified live.** 96 formula rows across four documents: **12 captioned, 84
correctly left whole, 0 ambiguous**, failing closed with `caption_ambiguous` rather than guessing.
The packet now reads as John asked: `label: Excluded benefits.` with the instruction body separate,
and no caption at all for a row like `Combine lines 12 through 14` that has none. It also removed a
contaminated 1040 label that had bled text in from a neighbouring source row. Live: 1040 unchanged
at 17/17, 2441 at 18 derived within the observed 18-20 band, with the three failures being the
known set and none caption-related.

**S60, packet completeness: the deliverable landed and the corpus shrank.**

The win is real and it is the first of its kind. **2441 line 8 now carries 16 of 16 printed bands**
- Architect-verified deterministically against the source - and the model emitted **all sixteen
correctly** on live data, `15000/.35` through `43000/.21` plus the open top band. **That row has
never been substantively right in any prior round.** It sits at `repaired` only because
`LOOKUP_BRACKET` does not project to a rule. Line 19 carries its default branch again, truncation is
now detectable instead of silent, and **every packet remains a verbatim subset of the acquired
source**.

The regression is bounded and diagnosed. `row_packet_incomplete` counts page furniture as missing
content, and the finding suppresses the provider call, so **four rows that derived correctly in
every prior run are no longer attempted** - 2441 lines 11, 26, 31 and 6251 line 40. Attempted across
three documents went **67 -> 63**. The detector's own detail strings name the culprits: a catalog
number and revision date, the next section's header, and the form's own footer identifiers. S61 is
the narrow fix.

**A prediction of mine that failed, recorded because it matters.** I expected the truncation fix to
change 2441 line 19. With the complete packet it **still** emits `require_input(line 19)`. Two of
its three branches are genuinely unresolvable, so the open question is whether it should emit a
status-keyed lookup with a resolvable default or a typed unresolved dependency. That belongs to the
`REQUIRE_INPUT`-overloading work.

**Gates:** ASCII OK, `git diff --check` clean, protected set diff empty, 115 passed on the Worker's
focused suites.

## Architect decision - notation

John, 2026-08-04: *"do what makes sense. We are not boiling the ocean here. I just don't want to
reinvent and perfect the wheel either."*

**BORROW THE DECISION-TABLE SHAPE FOR LOOKUPS. DO NOT ADOPT A FORMALISM.** Prior art exists and two
pieces are on point: **DMN** decision tables (named input/output columns plus a hit policy, designed
for exactly "if income is in this band, the rate is that"), and **Catala** (a language for encoding
tax law with the legal text attached, philosophically closest to our citation discipline). We also
already touch **PolicyEngine-US** as a parameter witness (`tax_graph/oracles/pe_liability.py`,
`verify parameter-diff`), currently `policyengine_enabled: false`.

**Ruling:** take the decision-table STRUCTURE for the lookup problem and nothing else. Our lookups
break because arguments are a bare ordered list - `(status, 239100, 119550)` - with no way to say
which value belongs to which status; a decision table names them structurally, which is a solved
problem we should not re-solve. **Do not adopt DMN, FEEL, or Catala wholesale.** The property that
makes this project checkable is a narrow emission vocabulary a deterministic validator can verify;
a general-purpose expression language widens exactly what we need kept narrow. Revisit only if a
real form defeats the borrowed shape.

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

- **APPROVAL IS THE GATE ON COMPUTATION (John, 2026-08-04). This SUPERSEDES the three-option
  question S48 raised, and the Architect's own lean; both were the wrong frame.** Verbatim: *"in my
  mind, this thing should only compute if every cell is approved."* An approved cell is valid for
  the computing AI to use. Everything else does not compute.
  **The middle states are a work queue, not engine semantics.** John on the "the AI cannot produce
  the right operation" case: *"i can't believe that. These are relatively simple operatons for
  normal people to execute."* He intends to iterate the cells in the core forms until they are all
  valid - *"Otherwise, WTF am i doing here?"* So `questioned` and `rejected` are transient states a
  human burns down, and we do NOT design engine behaviour around keeping them computable. S50
  supports him: eleven of twelve 2441 cells were correct on the first attempt.
  **The residual real case is an out-of-corpus reference**, and it gets a payload rather than a
  silent hole: the cell carries the IRS labels and instruction text so the consuming AI can see what
  the line is, while the operation field says explicitly that it is not completed and that resolving
  it is the caller's problem. `graph/2025/frontier.yaml` already declares 89 such branches with a
  target node and a citation; what it lacks is the printed text and the explicit handoff.
  **Third-party ingestion is explicitly out of our control.** John: *"If some other yoyo decides to
  ingest a new form and does a shitty job, I can't control that... not my call."* Noted by the
  Architect, and the gate protects us anyway - their unapproved cells refuse to compute here
  regardless of what they thought of their own work.
- **THE ODD DOCUMENTS ARE TREATED EXACTLY AS A FORM IS TREATED (John, restated 2026-08-04; he
  first said this "a long time ago" and the Architect asked again anyway).** Verbatim: *"these odd
  things should be treated the same way as a form is treated. They are analogous."* Worksheets,
  optional extensions, and oddball documents are documents: acquired through the manifest, derived
  by the same pipeline, reviewed through the same surface, promoted by the same path as the 1040.
  **There is no second class, no per-form gate, and no separate promotion decision to escalate.**
  If a question about one of them cannot also be asked about the 1040, it is the wrong question.
  This is the ruling that makes S42's worksheet harvester and 2441's manifest entry the SAME piece
  of work, and it condemns the two surviving special cases: `optional_extension` in
  `graph/2025/field_maps/form_2441_2025.yaml` and the `graph_ext/` overlay that holds 2441 alone.
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
  Before S48, the code accepted only `confirmed`/`rejected` (`workbench/static/app.js`), so the
  middle tier was missing. The ledger is already address-keyed and append-only, so adding it is
  small.

## Open for Architect
- **ANSWERED 2026-08-04 and CLOSED: what a QUESTIONED or REJECTED node means to the engine.** John
  rejected the three-option framing entirely - approval is the gate, the middle states are a work
  queue, and the out-of-corpus reference is the only case that needs a designed payload. Pinned as
  the first binding ruling; specced as S52 and S53.

- **M20-S36 denominator decision (raised 2026-08-03).** Logical-row assembly removes the measured
  label/span truncation cases, but it also exposes formula cues on `schedule_a_2025` line 15 and
  `schedule_1a_2025` line 36a, so the current formula set is 96 rows rather than the prior 94.
  Should the next provider leg use the fuller 96-row derivation set, or should formula selection
  remain frozen to the prior 94-row denominator for comparability? No provider result is claimed.
- **FOR JOHN - the two scoping calls that block the last 5 rows (raised 2026-08-03).** Both are the
  same shape as the Form 2441 question below, and answering all three together would clear every
  open scoping item in one pass.
  **(1) CLOSED 2026-08-05.** John ruled the nomination mechanism in; it is specced as S59.
  worksheets are in scope; the mechanism is S42. Two sub-calls remain his: the manifest schema change
  that lets a document declare a region of another acquired document (S42 step 4 reports it,
  implements nothing), and **his standing requirement that adding or removing a document, an
  instruction set, or a worksheet must never require an agent.** Original framing below.
  **(1) Are the tax worksheets in the base profile?** 6251 lines 13, 20 and 27 reference the
  Qualified Dividends and Capital Gain Tax Worksheet and the Schedule D Tax Worksheet. Both live in
  the IRS *instructions* rather than as standalone forms, and neither is a document in our graph,
  so those rows reference addresses that do not exist. Either model them as documents, or declare
  them out of scope and make the reference fail closed with a named reason instead of a confusing
  self-reference. The 1040 and Schedule D reference the same worksheets, so this recurs.
  **(2) Should the expression grammar carry a filing-status-dependent constant? PARTLY ANSWERED BY
  MEASUREMENT, 2026-08-03 - it is now a correctness question, not a cost one.** 6251 lines 18 and 39
  need a threshold ($239,100 / $119,550) and a subtrahend ($4,782 / $2,391) that both vary by filing
  status. Once S39 showed the model `taxpayer_2025_filing_status`, it reached for it unprompted and
  produced a rule that DOES cover married filing separately - but via a positional
  `LOOKUP_TABLE(node, 239100, 119550)` that maps to no rule and no roles, so the engine returns
  MISSING. The graph already contains the shape it needs (`lookup_capital_loss_limit`: one `key`
  edge plus one role-per-status edge), and the positional expression schema cannot express it. **So
  the question is no longer whether to carry the constant, but whether the grammar grows a
  role-keyed selection - and whether the four 6251 parameter nodes are hand-authored or pipeline-
  minted.** S40 step 3 asks for the mapping report that makes this decidable; the hand-author
  versus pipeline call remains John's under the prime directive.
- **FOR JOHN - what is next, once the scoping calls are made? (raised 2026-08-03.)** The corpus
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
- **WITHDRAWN 2026-08-04: "do 2441's drafts get promoted?" was a malformed question and John said
  so.** See the new binding ruling below. There is no per-form promotion gate: no form's derived
  output is promoted, 2441's drafts sit where the 1040's sit, and asking about this one form
  invented a decision that does not exist. The real finding stands and is pipeline work, not a
  John call: `optional_extension` appears in exactly ONE file in the entire graph
  (`graph/2025/field_maps/form_2441_2025.yaml`, 24 excluded nodes), and 2441 is the only document
  parked in a `graph_ext/` overlay. **That special case is the defect.**

## From Architect

- **M20-S61 TASK - TIGHTEN "SUBSTANTIVE CONTINUATION" (Architect, Claude Opus 5, 2026-08-05).**
  Ledger: the RAN/NOT RUN rule, D10, and the standing rules in `AGENTS.md`. **Narrow rework of S60.
  Keep everything else S60 did - it worked.**

  **OPEN ITEMS AND SEAMS THIS ROUND TOUCHES:** advances the evidence foundation only. **Leaves
  untouched:** nominations (S59), column/grid recovery, the operation registry, phrase obligations,
  the approval gate (S53).

  **What S60 got right and must be preserved.** Architect-verified deterministically and live:
  2441 line 8 now carries **16 of 16 printed bands** and the model emitted all sixteen correctly
  with the right thresholds - the first substantively correct result that row has ever produced.
  Line 19 carries its default branch again. **Every packet is still a verbatim subset of the
  acquired source.** Truncation is now detectable instead of silent, which was the deliverable.

  **The defect.** `row_packet_incomplete` treats page furniture and neighbouring-section text as
  missing content, and because the finding suppresses the provider call, **four rows that derived
  correctly in every prior run are no longer attempted.** Attempted across three documents went
  67 -> 63. The detector's own detail strings name the culprits:
  - `form_2441_2025` line 11: *"18, 2025, 25, created"* - catalog number and revision date.
  - `form_2441_2025` line 26: *"27, 31, below, complete, lines, through"* - the NEXT section's
    header.
  - `form_2441_2025` line 31: *"2025, 2441"* - the form's own footer identifiers.
  - `form_6251_2025` line 40: same class.

  **Step 1 - define "substantive" so it excludes furniture.** Bare numerals, four-digit years, form
  and catalog identifiers, revision dates, page numbers, and text that belongs to a following
  section are NOT substantive continuation. **Report the rule you implement and every row it changes
  across the full manifest**, in both directions: rows that stop being flagged, and any row that
  starts.

  **Step 2 - prove the true positives survive.** 2441 lines 8 and 19 and Schedule D line 21 were the
  three genuine interruptions S60 found. **They must still be detected**, and line 8 and line 19 must
  still carry their complete text. A fix that silences the detector everywhere is worse than the
  regression.

  **Step 3 - report the attempted count per document before and after.** The target is 67 attempted
  across 2441/1040/6251 with the genuine interruptions still repaired rather than suppressed.

  **Do not:** weaken the verbatim-subset guarantee; reconstruct text; disable the finding rather than
  narrowing it; touch the caption split, the operation vocabulary, or the addressing layer.
  **Stop conditions:** any diff in the protected directories; a packet containing text that is not
  verbatim in the source; a genuine interruption no longer detected. Tier 3. Honest `RAN:`/`NOT RUN:`
  - **the provider leg is the Architect's, and this round is not accepted until the attempted count
  is restored with the true positives intact.** ASCII, `git diff --check`, module-form
  `validate 2025`. **ONE local commit.**

  **Recorded, not for this round:** with the complete packet, 2441 line 19 STILL emits
  `require_input(line 19)`. The Architect predicted the truncation fix would change that row; it did
  not. Two of its three branches are genuinely unresolvable - spouse's earned income has no node,
  and one branch says only "see instructions" - so the honest question is whether it should emit a
  status-keyed lookup with a resolvable default, or a typed unresolved dependency. **That belongs to
  the REQUIRE_INPUT-overloading work, not here.**

- **M20-S59 TASK - NOMINATE A REGION OF A DOCUMENT TO BE A FULL DOCUMENT (Architect, Claude Opus 5,
  2026-08-05; John's call: *"Yes, I think we have to have some mech for at least nominating these
  odd things to be full-fledged docs."*).** Ledger: the RAN/NOT RUN rule, D10, and the standing
  rules in `AGENTS.md`. **Runs after S58. One change, no passengers.**

  **OPEN ITEMS AND SEAMS THIS ROUND TOUCHES:**
  - **ANSWERS AND CLOSES** the long-open worksheet sub-call: *"the manifest schema change that lets
    a document declare a region of another acquired document"*, open since 2026-08-03, reported by
    S42 step 4 which implemented nothing.
  - **IMPLEMENTS** the binding ruling that odd documents are treated exactly as forms.
  - **MUST HONOR** John's self-serve ruling (2026-08-03): **adding or removing a document, an
    instruction set, or a worksheet must never require an agent.** The nomination and acceptance
    flow is a CLI a person runs, not a code edit. Today the only manifest-facing commands are
    `acquire` and `harvest-worksheet`.
  - **UNBLOCKS** 6251 lines 13, 20 and 27 - three of the six most compound cells in the corpus,
    all of which reference the Qualified Dividends and Capital Gain Tax Worksheet or the Schedule D
    Tax Worksheet.
  - **LEAVES UNTOUCHED:** the caption work (S58), column recovery, the instruction join, S53.

  **Why "nominate" and not "declare".** Nobody should have to know in advance which worksheets
  matter. **The pipeline already discovers them:** an out-of-corpus reference produces an S52
  incomplete cell with reason `reference_not_in_corpus`, naming the target, and `frontier.yaml`
  holds 89 declared branches. **That IS the nomination queue** - it exists, it is evidence-backed,
  and nothing consumes it. This round adds the step that turns a nomination into a declared
  document.

  **Step 1 - report the nomination set from real data.** Derive the candidate list from the
  incomplete cells and frontier entries actually produced by a corpus run: which named worksheets
  and documents are referenced but not held, how often, and from which citing rows. **Report it
  before building the acceptance path.** A nomination nobody hit is not worth a manifest entry.

  **Step 2 - the manifest schema change.** A document entry may declare itself a REGION of another
  acquired document instead of carrying its own URL. **Identity is the normalized printed title** -
  exact after NFKC, case and punctuation folding - which S43 established and proved by rewriting all
  1,480 `publink` ids in the real source and getting identical output, and by confirming that a
  renamed title blocks even with the declared publink present. **The title is the key, never the
  anchor id.** Pinning: a region document pins its PARENT's sha256 plus its title; it has no hash of
  its own. **Fail closed** when the title matches zero or several sections, naming every candidate.

  **Step 3 - the flow is self-serve.** One command lists outstanding nominations with their evidence;
  one accepts a nomination into the manifest. **A person must be able to add or drop a worksheet
  without an agent and without editing YAML by hand.** Report the exact command lines.

  **Step 4 - run it end to end on the QDCGT worksheet and report honestly.** Accept the nomination,
  harvest it with the existing `harvest-worksheet` path, and report what the corpus does afterwards:
  specifically whether 6251 lines 13, 20 and 27 now resolve to cross-document references instead of
  failing closed. **Drafts only - no promotion.** If they still fail, that is the finding and it is
  worth more than a green number.

  **Do not:** hand-author a worksheet; invent a title that is not printed in the source; give a
  region document its own sha pin; promote anything; edit `graph/2025/` outside `_drafts/`; change
  the caption or column work. **Stop conditions:** any diff in the protected directories; a region
  resolved by anchor id rather than printed title; a nomination accepted without evidence of a real
  citing row. Tier 3. Honest `RAN:`/`NOT RUN:` - **the provider leg is the Architect's.** ASCII,
  `git diff --check`, module-form `validate 2025`. **ONE local commit.**

- **M20-S53 TASK - THE APPROVAL GATE, BEHIND A SWITCH, DEFAULT OFF (Architect, Claude Opus 5,
  2026-08-04, from John's approval-is-the-gate ruling).** Ledger: the RAN/NOT RUN rule, D10.
  **Depends on S52's payload. Do not start this before S52 lands.**

  **Why.** John: *"this thing should only compute if every cell is approved."* Today the engine
  ignores every verdict - `Engine.execute` walks and evaluates every node unconditionally, and the
  only place review state is read is `provenance_for_node` (`tax_graph/engine/engine.py:97`), which
  decorates the response. A cell John rejected still computes and still reaches the filled PDF.

  **THE TRAP, AND THE REASON THIS IS SPECCED CAREFULLY.** `human_confirmed: false` is ALSO the mint
  default for every node nobody has reviewed - `tax_graph/extension.py` sets it false in four places.
  **Gate on `human_confirmed` and the entire graph goes dark on day one**, because there are zero
  human approvals in the graph today. **Key on `verification_tier` being explicitly
  `human-confirmed`**, and treat a missing tier as its own state, reported separately from a tier
  that says a human looked and objected.

  **Step 1 - the switch.** One config key, default OFF, following the `policyengine_enabled: false`
  pattern in `config/tax-graph.config.yaml`. **Default off is not timidity** - John intends to flip
  it once he has iterated the core forms, and flipping it before that turns off every test, demo and
  export in the repo. Report what the suite does with it ON: **a large number of newly non-computing
  nodes is the CORRECT result**, not a regression to fix by weakening the gate.

  **Step 2 - gate on approval, emit S52's payload.** An unapproved node does not compute; it emits
  an incomplete cell with reason `not_approved` and its IRS text, so a caller sees what the line is
  and why it stopped. **Anything downstream of it is also incomplete** - report how that propagates,
  because one unapproved cell high in the 1040 can dark a whole return, and John should see that
  number before he flips the switch.

  **Step 3 - report the three populations separately, on the real graph.** Approved, explicitly
  objected to (`human-questioned` / `human-rejected`), and never reviewed. **Report the counts.**
  The expected answer today is zero approved and everything unreviewed; if it is not, that is a
  finding about how those fields got set and it matters more than the round.

  **Step 4 - the switch must be observable.** Whatever the engine returns must say which mode it ran
  in. A caller that cannot tell whether it received a full return or a gated one will eventually
  treat one as the other.

  **Do not:** enable the switch by default; weaken the gate to make a suite pass; gate on
  `human_confirmed`; write an approval into the graph to make a test green; promote anything.
  **Stop conditions:** any diff in the protected directories; any test that passes only because a
  verdict was authored by the Worker rather than by a human. Tier 3. Honest `RAN:`/`NOT RUN:`.
  ASCII, `git diff --check`, module-form `validate 2025`. **ONE local commit.**

## Architect decisions

- **THE REVIEW LOOP, as designed with John 2026-08-03. This is the shape S37-S39 build toward.**
  - **The FORM is the unit of approval, not the cell.** John: *"I view the form as a unit."* No
    per-cell sign-off across ~1,921 controls; findings route attention to the handful that need it.
  - **Try again, not reject, is the main action.** The reviewer edits a comment, re-derives that one
    cell live, and iterates. Reject is the escape hatch for a cell that will not converge.
    Feasibility measured before committing to it: **6.0s for one row cold, ~2.7s for the model call
    alone**; a warm server does not repeat the setup.
  - **This is only safe because `derive_cells` is pure.** The zero-disk-write gate defended every
    round since S24 is what lets a request handler call it with a modified evidence packet.
  - **The stored comment is one that has been VERIFIED to work.** Because the reviewer tunes wording
    until the cell comes out right, the ledger accumulates known-good instructions rather than
    hopeful ones. This is strictly better than a comment written blind and batched.
  - **Two classes of comment.** `contributed` is raw input from another reviewer - John's example:
    *"this is broke"* - retained and shown but NEVER sent to the model. `curated` is the lead's
    edited instruction; only curated comments feed derivation. Turning the first into the second is
    the irreplaceable human act.
  - **Latest curated comment per address wins**, with full history retained for audit and display.
    Keeps the prompt bounded as comments accumulate over years.
  - **A comment must never override a validator.** It steers interpretation; it cannot talk the
    model past `quote_not_verbatim`, `operand_not_printed` or `self_reference`.
  - **Show nondeterminism rather than hide it.** Try-again with an unchanged comment can return a
    different answer - measured repeatedly at `temperature: 0`. The UI must distinguish "you changed
    the comment" from "same comment, fresh attempt", or reviewers tune toward superstition.
  - **Convergence needs a measure and an escape hatch.** Track rounds-to-approval per cell and flag
    anything reopened more than twice; at that point it needs a human decision, not another pass.
  - **The reviewer's scarce resource is attention.** John: apathy is a bigger risk than
    over-control. Findings-first ranking is therefore not polish - it is what makes a contributor's
    fifteen minutes productive. Measure findings raised vs findings upheld, and minutes per upheld
    finding; that is the ratchet the phase plan asks for and we have never been able to compute.
  - **Audited 2026-08-03: NONE of this is surfaced today.** The workbench API is six calls - list
    documents, load cells, load/save session, save progress, submit verdict. There is no findings
    endpoint, no per-cell problem badge, and no ranking. Derivation quality IS generated every run
    (per-row failures, warnings, repair events) and is written to a temp report and discarded. S38
    carries it into the surface.


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

- **M20-S54 -> S56 (`47784e6`, `e35b658`, accepted at `c359d65`; two reworks):** the lookup
  completeness validator, the `totals` label fix (2441 12 -> 21 admitted), `classification:
  total`, and the `NOT_COMPUTED_AGENT_MUST_RESOLVE` rename all landed in S54 - alongside a
  provider-schema change that killed every live call for two rounds. S54 shipped `allOf`, which
  OpenAI rejects; S55 removed it and left the S46 configuration (`role` in `properties`, absent
  from `required`); S56 restored the S47 shape and un-inverted the three guards S54 had edited to
  agree with the broken code. **Live 2441 went 0/21 -> 19/21.** Four standing rules added to
  `AGENTS.md` at `af89b22`; the guard-inversion one is the root cause.
- **M20-S52 (`2dac757`, Architect-verified):** the incomplete-cell payload.
  `Result.incomplete_cells` is separate from `missing_required_inputs`, carries the canonical
  address, printed IRS label, instruction text, citations split form-face/instruction, and the
  operation `NOT_COMPUTED_AGENT_MUST_RESOLVE`; the reason enum is closed and already accepts
  `not_approved` for S53. Reaches `execute_tax_tree` and the filled-form `bundle.json`. Architect
  drove the real graph: 89 frontiers with **12** printed labels and 77 without, 3 live incomplete
  cells all carrying a label and 2 of 3 carrying instruction text. Worker reported the hash as
  `d2637e3`, orphaned by an amend; the record is `2dac757`.
- **M20-S51 (`1541a67`, Architect-verified; provider leg Architect-run):** the derivation
  denominator is explicit. `build_derivation_denominator` reports every line anchor as admitted
  or skipped with a named reason, keeping the pre-S51 decision beside the current one. Corpus:
  478 anchors, 108 admitted before, 121 now; 2441 goes 12 -> 19 of 35. Architect's live leg put
  line 8's AGI table in front of the model for the first time: the named-role lookup shape held
  and **6 of 16 bands were transcribed**, with no validator checking completeness. Three round
  defects (a `totals` label never read, a skip reason that misdescribes the cause, an unreachable
  `incomplete` state) -> **S54**.
- **M20-S50 (`f637df0` manifest + `059231e` report, Architect-verified; provider leg Architect-run):**
  the 2441 reliability exercise. Manifest declaration with Architect-hashed sha pins; reconcile clean
  both directions. Two live runs: 12 attempted of 35 line anchors, derived 12 / 11+1 repaired, and
  the one divergent row (line 25) is semantically wrong in BOTH runs while passing every validator in
  run 1. Line 8's AGI table never entered the denominator, so the S46/S47 lookup was not exercised;
  the table has 16 bands, not the 15 the spec assumed. Worksheet harvest impossible - 2441
  instructions are PDF-only and the harvester is HTML-table based. Nothing promoted; protected set
  untouched. **Finding -> S51.**
- **M20-S49 (`1bd2bf1`, Architect-verified):** the try-again loop is closed. `tax_graph/workbench_host.py`
  injects `build_rederive_handler` into `serve` without importing pipeline code into `workbench/`;
  the unconfigured server still answers 501. UI adds the Try again panel, pending state, returned
  expression with validator failures, and attempt labels distinguishing "same correction (fresh
  try)" from "changed correction". Nothing persists on retry. Architect drove it LIVE through the
  injected handler: 6251 line 18 in 8.9s and 7.7s, both derived, working tree clean; browser e2e
  5 passed from an account that can read the draft directory.
- **M20-S48 (`c55fde5` + `71b064a`, Architect-verified):** review is three-state end to end -
  Accept/Question/Reject stored as `confirmed`/`questioned`/`rejected`, legacy tokens canonicalized
  (`problem` -> `questioned`), unknown tokens rejected rather than defaulted. Question and Reject
  write `human_confirmed: false` with `human-questioned`/`human-rejected` tiers and require an
  observation. Every S45 property held, including fingerprint blocking for non-confirming states;
  the ledger is also tamper-evident at load. The false `unresolved_comparison_direction` warning on
  1040 line 34 is gone. Engine semantics reported, not wired -> John.
- **M20-S46 + S47 (`85a83ca` REWORK, fixed at `1b9f116`, Architect-verified):** conditionals and
  lookups are now executable. `IF_ELSE` maps to `if_greater_than_currency`/`if_less_than_currency`
  with direction resolved deterministically from the row's own wording; `LOOKUP_TABLE` maps to
  `lookup_selected_value` with named roles borrowed from the DMN decision-table shape; a bare
  ordered lookup fails closed. S46 shipped an invalid provider schema (`role` in `properties` but
  not `required`) that killed the live corpus 96/96 - S47 made the schema strict and added the
  local guard test that would have caught it. Live: derived 89/91, resolved 93/93,
  `unmapped_operation` 9/7 -> 3/3, and the three target rows project real rules with zero findings.
- **M20-S45 (`467685c`, Architect-verified):** `apply_address_verdicts` plus
  `review apply-address-verdicts`, dry-run by default, reusing the existing `_apply_graph_review`
  rather than adding a second applier. Architect ran the live dry-run: the one real ledger record
  reports STALE with both fingerprints printed and writes nothing, which is the property the M15
  path lacked. Vocabulary gap reported not invented -> S47.
- **M20-S44 (`e0a3f35`, Architect-verified):** `operand_type_mismatch` hard-fails a nonnumeric graph
  node in a numeric slot while still allowing a status node as a `LOOKUP_TABLE` key; incomplete node
  metadata is recorded as `operand_type_undetermined_nodes` and allowed through; `REQUIRE_INPUT` no
  longer emits an unmapped-operation warning. Architect ran both corpus legs: derived 92/92,
  resolved 93, `unmapped_operation` down 12-14 -> 9/7, and 6251 line 39 correctly shaped in both.
- **M20-S43 (`ba7a1f8`, Architect-verified):** worksheet start resolves by normalized printed title,
  exact after NFKC/case/punctuation folding with one allowance for the IRS `-Line N` suffix; zero or
  multiple matches fail closed with every candidate named; the publink is demoted to an observation
  and no longer appears in the stored locator. Architect rewrote all 1,480 publink ids in the real
  source and got identical output (25/13/13 with 0 mismatches/2), and confirmed a renamed title
  blocks even with the declared publink still present - the title is the key, not a fallback.
- **M20-S42 (`b6e9be7`, Architect-verified):** `tax_graph/ingest/worksheet_harvest.py` plus the
  `harvest-worksheet` CLI - pure over acquired instruction HTML, writes only under `_drafts`, no
  schema change. QDCGT canary met the prediction exactly: 25 contiguous lines, 13 constants, 13
  citations with zero mismatches under the project's own checker, and **both Form 2555 conditional
  routes that the hand-authored graph drops.** Declared scope limit: no computed nodes and no
  `CALCULATES` edges, so it does not harvest the arithmetic. Architect finding -> S43.
- **M20-S41 (`40530b1`, Architect-verified):** `tax_graph.acquire.reconcile_document_lists` names
  every graph/manifest/raw difference, degrades the raw leg to `skipped`, and reports non-fatally
  through `validate`; the derivation harness now defaults to the manifest's declared order. Architect
  ran the provider leg: 21 documents, 9 complete, 12 empty, zero errored, 96 rows unchanged, the
  2441 phantom gone. All six instruction documents derive zero rows -> the case for S42.
- **M20-S40 (`e032cfd`, Architect-verified):** `missing_floor` accepts a zero-valued `parameter`
  node, the prompt inventory is scoped per document (26 for 1040, 3 for Schedule D, 1 elsewhere),
  unmapped projection operations became warnings, and the harness reports expressions and external
  mints. Closed the S39 regression: derived 92/91 across four runs. Delivered the operation-mapping
  report with no protected-set change. Its warning surfaced the type-free grammar hole -> S41.
- **M20-S39 (`ef39dfe`, Architect-verified, REWORK):** the node inventory reached the prompt, the
  unseen-form hard fail became a minted unresolved required input, and the four 6251 parameter nodes
  were reported rather than invented. Corpus fell to derived=87 on two runs; A/B isolated it to
  `form_1040_2025_zero_floor` being rejected by a `missing_floor` check that only accepts a literal
  zero. Placement was tested and ruled out. Reworked as S40.
- **M20-S38 (`514443e`, Architect-verified):** `{"node": ...}` operand plus positional conditional
  semantics; best first-attempt corpus to that point (derived=92, repaired=1, resolved 93/96), and
  6251 lines 18 and 39 derived with no repair. Its new `operand_document_not_found` hard fail
  rejected the correct Form 4684 answer on Schedule A line 15 - fixed in S39 step 2.
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

- **M20-S50 (2026-08-04, Architect live):** two provider runs over `form_2441_2025`, attempted=12
  both, derived 12 and 11, repaired 0 and 1, gapped 0, errored 0; `validator_failures_by_kind` empty
  in run 1 and `operand_node_not_found` x1 in run 2. Denominator measured directly against
  `_formula_outline_nodes`: 40 outline nodes, 35 line anchors, 12 admitted, 23 dropped with the cue
  responsible named per line. All twelve expressions checked by hand against the acquired form face -
  eleven correct, line 25 wrong in both runs (the `min(20,21) - 24` else-branch), line 5 a
  filer-provided default where the row states a rule. `.cache/raw/2025/` has no 2441 instructions
  HTML, so the worksheet harvest is NOT RUN by construction. ASCII OK; `validate 2025` exit 0 with
  reconcile clean both directions; protected-set diff empty; `git status` clean; all harness output
  written outside the repository.
- **M20-S49 (2026-08-04, Architect live):** live re-derive through the exact handler `serve()`
  injects - 6251 line 18, no comment then with an MFS correction: 8.9s and 7.7s, both `derived`,
  named-role lookup returned, `git status` clean after. API driven directly: unconfigured -> 501,
  configured -> 200 with the draft comment passed, no token -> 403, ledger unchanged. Browser e2e
  `tests/e2e/test_workbench_v2_m17.py` -> 5 passed in 141s. Focused suites 11 passed; ASCII OK;
  `git diff --check`; protected set byte-identical.
- **M20-S47 (2026-08-04, Architect live):** two corpus runs, attempted=96 both, derived 89 and 91,
  repaired 4 and 2, errored 3, resolved 93 both; `unmapped_operation` 3 and 3. Emitted schema walked
  directly: zero objects with a property outside `required`, `role` nullable. 1040 line 34 ->
  `if_greater_than_currency`+`subtract_currency`; 6251 lines 18 and 39 -> `if_less_than_currency`,
  `lookup_selected_value`, `multiply_currency`, `subtract_currency`; all three zero findings. Bare
  and null-role lookups still fail closed. 82 passed on a short temp root; ASCII OK;
  `git diff --check`; protected set byte-identical across `cc73710..1b9f116`.
- **M20-S44 (2026-08-04, Architect live):** two corpus runs, attempted=96 both, derived 92 and 92,
  repaired 1 and 1, errored 3, resolved 93 both; `unmapped_operation` 9 and 7 (was 12 and 14);
  `operand_type_mismatch` fired once on live data. Type check verified directly: status node in the
  `IF_ELSE` condition slot hard-fails, the same node as a `LOOKUP_TABLE` key passes,
  `REQUIRE_INPUT` warns zero times. 72 passed on a short temp root; ASCII OK; `git diff --check`;
  protected set byte-identical across `0310ba1..e0a3f35`.
- **M20-S43 (2026-08-04, Architect):** independent year-turn simulation - all 1,480
  `en_US_2025_publink*` ids in the acquired HTML rewritten to a 2026 scheme, headings untouched;
  harvest output identical (25 lines, 13 constants, 13 citations with 0 mismatches, 2 conditions)
  with the new anchor recorded as an observation. Negative case verified directly: heading text
  renamed with the declared publink left intact blocks with `missing_start_title`. 73 passed on a
  short temp root; ASCII OK; `git diff --check`; `validate 2025` exit 0 with all six reconcile
  differences named; protected set byte-identical across `c04db97..ba7a1f8`.
- **M20-S42 (2026-08-04, Architect):** harvester run directly against
  `.cache/raw/2025/instructions_form_1040_2025.html` - `ok=True`, zero findings, 25 line nodes, 13
  parameter nodes, 13 citations, 42 edges, 2 conditions (Form 2555, lines 1 and 25). Citations
  re-checked with `check_citation_integrity`: **checked=13, mismatches=0**. 77 passed on a short
  temp root; ASCII OK; `git diff --check`; protected set byte-identical across `25d2895..b6e9be7`.
- **M20-S41 (2026-08-04, Architect live):** manifest-driven corpus, 21 documents, 9 complete /
  12 empty / 0 errored; attempted=96, derived=90, repaired=3, errored=3, resolved=93 (third sample
  in the 90-92 band; no derivation code changed). 78 passed on a short temp root; ASCII OK;
  `validate 2025` exit 0 with the reconcile report printing all six named differences; protected set
  byte-identical across `8dc3511..40530b1`.
- **M20-S40 (2026-08-03, Architect live):** two full corpus runs (output under `C:\tmp`, outside the
  repo), attempted=96 both, derived 92 and 91, repaired 1 and 2, errored 3 both, resolved 93 both;
  `form_1040_2025` 17/17 in both. Focused suites 67 passed on a short temp root; ASCII OK;
  `git diff --check`; `validate 2025` (18 documents, 441 nodes, 409 edges, 401 citations); preflight
  `units=2224 derived_cells=2120 legacy_mined=394`; protected set byte-identical across
  `4935053..e032cfd`. `unmapped_operation` 12 and 14, of which 8 and 9 are REQUIRE_INPUT; the true
  signal is three rows in both runs. Exactly one external mint in both runs
  (`schedule_a_2025` line 15 -> `form_4684_2025_root_line_18`).
- **M20-S39 (2026-08-03, Architect live):** two full corpus runs, attempted=96 both, derived=87 both,
  repaired 6 / 5, errored 3 / 4, resolved 93 / 92. Focused suites 60 passed on a short temp root;
  ASCII OK; `git diff --check`; `validate 2025` (18 documents, 441 nodes, 409 edges, 401 citations);
  protected set byte-identical across `514443e..ef39dfe`. Inventory verified at 37 parameter/fact
  nodes. Schedule A line 15 recovers `copy(form_4684_2025:18)` and mints
  `form_4684_2025_root_line_18`; both fabrication shapes still rejected. Floor A/B on five rows
  across three forms: 1 of 24 clean with `zero_floor` in the inventory, 12 of 12 clean without.
  Placement A/B on two rows: 0 of 8 clean either way.
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
