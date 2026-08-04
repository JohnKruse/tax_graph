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

**BALL: WORKER - M20-S49 (FINISH THE TRY-AGAIN LOOP IN THE UI).** Task block under
**From Architect**. **S48 is ACCEPTED at `c55fde5` + `71b064a`** - review is three-state end to end
and the false direction warning is gone.

**RESEQUENCED 2026-08-04 BY JOHN: retry loop first, 2441 after.** He asked where the retry button
was, and it does not exist. Measured: `rederive_cell` and `POST /api/rederive` shipped in S37 and
are properly guarded, but `create_app` is called without the handler so the endpoint answers
**501**, and there are **zero** references to rederive anywhere under `workbench/static/`.
**Architect miss** - S48 added the verdict buttons without checking the loop they feed existed.
Running 2441 first would have generated a pile of review work with no way to do the review.

**Why 2441 next (S50).** Every piece it needs landed in the last eight rounds: the manifest drives the
corpus (S41), conditionals and lookups execute (S46/S47) which 2441's AGI percentage table requires,
and review is three-state with a working bridge (S45/S48). **This is the first end-to-end exercise
of the whole assembly on a form the pipeline has never properly processed** - John's own framing:
*"a good exercise in seeing if our pipeline is reliable and valid."*

**Drafts only. NO PROMOTION** - John rules on that with the artifact in front of him.

**AWAITING JOHN, does not block S49:** what a `questioned` or `rejected` node should mean to
`execute_tax_tree` - see **Open for Architect**. **Rollover policy and run alerting** are pinned at
`docs/engineering-plan.md` -> Year rollover (TY2026), seam 6.

## Current round

**M20-S48 ACCEPTED (Architect, Claude Opus 5, 2026-08-04) at `c55fde5` and `71b064a`. The review
loop is three-state end to end, and the false direction warning is gone.**

**The three states map correctly, verified by calling the mapping directly:**

| stored token | reviewer label | node fields written |
| --- | --- | --- |
| `confirmed` | Accept | `human_confirmed: true`, tier `human-confirmed` |
| `questioned` | Question | `human_confirmed: false`, tier `human-questioned` |
| `rejected` | Reject | `human_confirmed: false`, tier `human-rejected` |

Legacy tokens canonicalize rather than being guessed at - `problem` -> `questioned`, `approved` ->
`confirmed` - and an unknown token raises `unsupported address judgement` instead of defaulting.
Question and Reject require an observation; Accept does not. **That asymmetry is right**: a bare
rejection with no reason is the one verdict that helps nobody.

**Every S45 safety property survived.** Dry-run by default, exact address plus single node binding,
and the fingerprint check still blocks non-confirming states - there is a parametrized test for
precisely that. I also found the ledger is **tamper-evident at load**: editing a record's
`content_fingerprint` to make a stale verdict look fresh fails with
`content_fingerprint does not match reviewed_content`. I hit that trying to forge test records, and
it is a genuinely good property nobody claimed credit for.

**The false warning is fixed and I checked it on the real row.** `_projection_warnings` now prefers
form-face evidence over instruction and quote cues. 1040 line 34 with its live evidence and live
expression: **zero hard failures, zero warnings**, where it previously emitted
`unresolved_comparison_direction` once per corpus run. The real projection path is unchanged and
still resolves `if_greater_than_currency`.

**Engine semantics REPORTED, not wired - correct, and now John's call.** The Worker laid out three
options for what a `questioned` or `rejected` node should mean to `execute_tax_tree`: (a) refuse to
compute and report unresolved - safest, blocks output; (b) compute and flag the result - a number
downstream code could consume; (c) exclude the node and report a gap - conservative but lossy.
**Nothing was wired. See Open for Architect.**

**Gates:** 95 passed on a short temp root, ASCII OK, `git diff --check` clean, protected set
byte-identical across `9c514b1..71b064a`.

**TWO THINGS TO NOTE, NEITHER BLOCKING.** The round produced two commits rather than the specified
one. And the Worker reports two pre-existing failures in `tests/e2e/test_paired_view_m15.py` for a
missing `data-check-group` element - **I did not verify that they predate S48**, so it is recorded
as the Worker's claim, not as an Architect-confirmed baseline entry.

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
- **FOR JOHN - what should a QUESTIONED or REJECTED node mean to the ENGINE? (raised 2026-08-04 by
  S48, reported not wired.)** The three-state vocabulary now writes `human_confirmed: false` with
  tier `human-questioned` or `human-rejected` onto the node, and `execute_tax_tree` currently
  ignores all of it. Three options, and this changes what a filer's return says:
  **(a) Refuse to compute and report unresolved.** Safest and most honest; blocks output on any
  questioned line, which could be a lot of lines early on.
  **(b) Compute and flag the result.** Produces a number downstream code can consume, with the doubt
  attached - but a flagged number is still a number, and something will eventually use it without
  reading the flag.
  **(c) Exclude the node and report a gap.** Conservative, and lossy in a way that may be hard to
  explain to a filer.
  Architect's lean is **(a) for `rejected` and (b) for `questioned`**, because the two states mean
  different things: rejected is "this is wrong", questioned is "I am not sure". Nothing is wired
  either way.

- **M20-S36 denominator decision (raised 2026-08-03).** Logical-row assembly removes the measured
  label/span truncation cases, but it also exposes formula cues on `schedule_a_2025` line 15 and
  `schedule_1a_2025` line 36a, so the current formula set is 96 rows rather than the prior 94.
  Should the next provider leg use the fuller 96-row derivation set, or should formula selection
  remain frozen to the prior 94-row denominator for comparability? No provider result is claimed.
- **FOR JOHN - the two scoping calls that block the last 5 rows (raised 2026-08-03).** Both are the
  same shape as the Form 2441 question below, and answering all three together would clear every
  open scoping item in one pass.
  **(1) ANSWERED IN PRINCIPLE 2026-08-03 - John: yes, and via a harvester, not by hand.** The
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

- **M20-S49 TASK - FINISH THE TRY-AGAIN LOOP IN THE UI (Architect, Claude Opus 5, 2026-08-04;
  John: *"i thought we were going to add a button to retry processing a rejected cell/line so that
  the human can leave comments that bring the entry into alignment with actual IRS intent"*).**
  Ledger: the RAN/NOT RUN rule. **This was designed, the backend shipped in S37, and the front half
  was never built. Architect miss: S48 added the verdict buttons without checking that the loop they
  feed existed.**

  **Measured state before this round.** `rederive_cell` and `build_rederive_handler` exist and are
  pure. `POST /api/rederive` exists and is properly guarded - write token, field whitelist
  (`document_id`, `line`, `draft_comment`), 10,000-char cap, `ValueError` -> 400, provider failure
  -> 502. **But `create_app` at serve time is called without `rederive_cell`, so the endpoint
  answers `501 cell re-derive is not configured`, and there are ZERO references to rederive in any
  file under `workbench/static/`.** There is no button.

  **Why it matters more than it looks.** The pinned design says try-again is the MAIN action and
  reject is the escape hatch, and that the stored comment is one the reviewer has VERIFIED works.
  Without the button every comment is written blind and Reject is the only move a reviewer has -
  which is the opposite of the intended loop.

  **Step 1 - wire the handler without breaking the layering.** `build_rederive_handler`'s docstring
  is explicit: the callback exists so the artifact-only workbench stays free of pipeline imports,
  and **its closure is owned by the application host.** Wire it where both halves are already
  available; **do not import pipeline code into `workbench/`.** Report where you wired it and why.
  The endpoint must keep answering 501 - not crash - when a host chooses not to configure it.

  **Step 2 - the button and the comment box.** On a cell: a comment field and a Try again action
  that POSTs to `/api/rederive` with the write token. **Persist nothing on retry** - that is the
  whole point of the pure function, and it is what makes the loop safe to run repeatedly. Saving a
  comment as curated stays a separate, explicit action.

  **Step 3 - show the result honestly, including the parts that are uncomfortable.**
  - Show the new expression **and its validator failures**. A comment must never talk the model past
    a validator, so when the retry still fails, say so plainly rather than presenting the new answer
    as an improvement.
  - **Distinguish "you changed the comment" from "same comment, fresh attempt".** Re-running with an
    unchanged comment can return a different answer - measured repeatedly at `temperature: 0`. If
    the UI hides that, reviewers will tune toward superstition. This is a pinned design requirement,
    not polish.
  - Show a pending state. Measured feasibility: **~6.0s for one row cold, ~2.7s for the model call
    alone** on a warm server.

  **Step 4 - contributed vs curated must hold at the UI boundary.** Only a curated comment may reach
  the model. A `contributed` comment is retained and displayed and **never sent**. Confirm the UI
  cannot send one, and test it.

  **Step 5 - prove the loop end to end with a fixture client, no provider.** Drive it with a stub
  handler: comment in, expression out, validator failures surfaced, nothing persisted. **Report
  explicitly that no graph, draft, ledger, or session state changed during a retry.** A live
  provider round trip is the Architect's leg, not the Worker's.

  **Do not:** persist anything on retry; let a `contributed` comment reach the model; import
  pipeline modules into `workbench/`; weaken the write-token guard; author or edit anything under
  `graph/2025/`; build convergence tracking (rounds-to-approval and the reopened-twice flag are a
  later slice - keep this round to the loop itself). **Stop conditions:** any diff in the protected
  directories; a retry writing to disk; the endpoint crashing rather than returning 501 when
  unconfigured. Tier 3. ASCII, `git diff --check`, module-form `validate 2025`. **ONE local commit.**

- **M20-S50 TASK (QUEUED BEHIND S49; SPEC COMPLETE AND STILL STANDS) - RUN THE WHOLE PIPELINE AT
  FORM 2441, AS A RELIABILITY EXERCISE (Architect,
  Claude Opus 5, 2026-08-04; John's call: *"adding it might be a good exercise in seeing if our
  pipeline is reliable and valid"*).** Ledger: the RAN/NOT RUN rule, D10. **Drafts only. NO
  PROMOTION in this round - John decides that with the artifact in front of him.**

  **Why now.** Every piece 2441 needs has landed in the last eight rounds: the manifest drives the
  corpus (S41), conditionals and lookups are executable (S46/S47) which 2441's AGI percentage table
  requires, and review is three-state with a working bridge (S45/S48) so the output can be judged
  rather than trusted. **This is the first end-to-end exercise of the whole assembly on a form the
  pipeline has never properly processed.**

  **What 2441 is today, measured.** 24 nodes but only **2 edges**, `gate: user`, `status: partial`,
  seven lines flagged "unmodeled in the M10 Step 4 batch draft", and visibly mangled ids such as
  `form_2441_2025_part_iii_line_28_part_iii_line_28`. It is in the graph and **not in the
  manifest**, while `form_2441_2025.pdf`, its `.txt`, and its instructions are already in the raw
  store - the `raw_not_in_manifest` pair the S41 reconcile names every run. **Nothing needs
  fetching.**

  **Step 1 - declare it, do not hand-author it.** Add `form_2441_2025` and
  `instructions_form_2441_2025` to `config/manifest.yaml` with their real URLs and sha pins, and
  verify the pins against the files already in `.cache/raw/2025/`. **Report whether the sha of the
  stored PDF matches what the manifest declares** - a mismatch is a finding, not something to paper
  over. The S41 reconcile must then show `raw_not_in_manifest` empty.

  **Step 2 - run the pipeline and report honestly.** Cell derivation over 2441 with the corpus
  harness, and the worksheet harvester if the instructions carry one. **Report attempted / derived /
  repaired / errored, and the validator failures by kind.** A low derived count is a finding about
  the pipeline, which is the entire point of the exercise - **do not tune the prompt to make 2441
  look good.**

  **Step 3 - the AGI percentage table is the real test.** Form 2441 line 8 selects a decimal from a
  fifteen-band table (.35 at $0-15,000 down to .20 above $43,000) keyed on line 7. **This is exactly
  the shape S46/S47 built the named-role lookup for**, and it is the first time it meets a table the
  pipeline has never seen. Report what the model emits for line 8, whether it projects onto a real
  rule with named roles, and whether the bands are complete and correctly bounded. **If the fifteen
  bands defeat the current lookup shape, that is the most valuable result this round can produce -
  report it plainly and do not invent a new operation.**

  **Step 4 - report the diff against what is already there.** The 24 existing nodes and 2 edges
  versus what the pipeline produces: which lines the pipeline covers that the M10 draft left
  unmodeled, which existing node ids the pipeline would supersede, and where the two disagree.
  **Report both directions honestly**, as the QDCGT canary did.

  **Step 5 - stop at drafts.** Write to `graph/2025/_drafts/` only. **The protected set stays
  byte-identical.** Report exactly what promotion WOULD change, and whether the output belongs in
  the project graph or the extension overlay given the existing nodes are `gate: user`. **John rules
  on promotion; it would be the first in this phase.**

  **Do not:** promote anything; edit anything under `graph/2025/` outside `_drafts/`; hand-author a
  node or a citation to improve the numbers; tune the prompt against 2441; invent an operation.
  **Stop conditions:** any diff in the protected directories; a citation emitted that is not
  verbatim in the acquired source; `derive_cells` acquiring a disk write. Tier 3. Declared files plus
  honest `RAN:`/`NOT RUN:` - **the provider leg is the Architect's**. ASCII, `git diff --check`,
  module-form `validate 2025`, preflight `legacy_mined` explicit. **ONE local commit.**

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

- **M20-S49 Worker implementation (2026-08-04, fixture-only; awaiting Architect verification):**
  wired the application host to inject `build_rederive_handler` without importing pipeline code
  into `workbench/`; the unconfigured artifact server still returns 501. Added the generated-cell
  Try again panel, local attempt labels and pending state, returned expression/validator display,
  and address-keyed review-history projection. Contributed comments are displayed as retained
  history and never sent to the model; an empty retry uses curated history through the pipeline
  callback, while a typed correction is sent only for that attempt. No retry writes graph, drafts,
  ledger, or session state. Form 2441 remains queued for S50; its manifest commit is already in
  history at `f637df0` and was not changed here.
  RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\testtmp-s49'; .venv\Scripts\python.exe -m pytest tests\test_workbench_s49.py tests\test_workbench_rederive_m20.py tests\test_rederive_m20.py -q` -> 7 passed in 0.45s.
  RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\pytest-run-s49'; .venv\Scripts\python.exe -m pytest tests\test_workbench_s49.py tests\test_workbench_rederive_m20.py tests\test_rederive_m20.py tests\test_workbench_m15.py -q` -> 11 passed in 0.67s.
  RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\testtmp-s49'; .venv\Scripts\python.exe -m pytest tests\test_workbench_m15.py -q` -> 4 passed in 1.20s.
  RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\testtmp-s49'; .venv\Scripts\python.exe -m pytest tests\e2e\test_workbench_v2_m17.py::test_generated_cell_try_again_shows_fresh_result_without_session_progress -q` -> 1 passed in 1.59s.
  RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK.
  RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> exit 0, graph integrity OK; reconcile differences named.
  RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\testtmp-s49'; .venv\Scripts\python.exe -m pytest tests\test_workbench_m15.py tests\test_workbench_server_m15.py tests\test_workbench_write_api_m15.py tests\test_rederive_m20.py tests\test_workbench_rederive_m20.py tests\test_workbench_s49.py -q` -> 11 passed, 13 errors; all errors stop at protected `graph/2025/_drafts/form_1040_2025` read access during live-app fixture setup.
  NOT RUN: provider leg - live provider access is outside the fixture-only round and unavailable in the sandbox.
  NOT RUN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\testtmp-s49'; .venv\Scripts\python.exe -m pytest tests\e2e\test_workbench_v2_m17.py -q` - fixture setup fails with the same protected-draft `PermissionError` before browser assertions.

- **M20-S48 Worker implementation (2026-08-04, Worker-verified; awaiting Architect verification):**
  landed the three-state observation contract. The reviewer-facing labels are Accept, Question,
  and Reject; the canonical stored tokens are `confirmed`, `questioned`, and `rejected`.
  Question and Reject reveal a comment box and require an observation; Accept needs no comment.
  Legacy cause tokens remain accepted only as named ingestion aliases and are canonicalized to the
  three states. The address bridge applies all three states with exact address/node binding and
  fingerprint protection; Question and Reject write `human_confirmed: false` with explicit
  `human-questioned` or `human-rejected` tiers. No engine code or protected graph artifact changed.
  `_projection_warnings` now prefers form-face evidence over instruction/quote cues; the real
  projection path is unchanged. The standalone workbench CLI also exposes the new verdicts and
  `--comment`.
  Engine semantics report (not implemented, per S48): (a) refuse to compute and report unresolved,
  safest but blocks output; (b) compute and flag the result, producing a number that downstream
  code could consume; or (c) exclude the node and report a gap, conservative but lossy. John must
  choose; current `execute_tax_tree` behaviour is unchanged.
  RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\08\04\019fcdb1-04e6-7c20-b0e5-2287ddd04329\pytest_s48_final'; .venv\Scripts\python.exe -m pytest tests\test_review_address_bridge_m20.py tests\test_review_verdicts_m20.py -k "not real_derived_projection" tests\test_derive_cells_m20.py tests\test_review_workbench_verdicts_m15.py tests\test_workbench_m15.py tests\test_workbench_write_api_m15.py -q` -> 105 passed, 1 deselected in 69.28s.
  RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\08\04\019fcdb1-04e6-7c20-b0e5-2287ddd04329\pytest_s48_final'; .venv\Scripts\python.exe -m pytest tests\e2e\test_workbench_v2_m17.py -q` -> 4 passed in 133.65s.
  RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK; compileall -> no errors;
  schema JSON load -> OK; `git diff --check` -> clean apart from the existing CRLF conversion
  warning on `workbench/server.py`; protected-set diff stat -> empty; module-form `validate 2025`
  -> exit 0, graph integrity OK, reconcile differences named.
  RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\08\04\019fcdb1-04e6-7c20-b0e5-2287ddd04329\pytest_s48_elev'; .venv\Scripts\python.exe -m pytest tests\e2e\test_workbench_v2_m17.py tests\e2e\test_paired_view_m15.py -q` -> 4 passed, 2 failed. Both failures are the pre-existing paired-view lookup for `[data-document-id="form_1040_2025"][data-check-group="identity_inputs"]`; the app renders document buttons but not those group elements. The changed S48 browser suite is green above. NOT RUN: provider leg - prohibited by the S48 task and unavailable in the sandbox.

- **M20-S45 Worker implementation (2026-08-04, Worker-verified; awaiting Architect verification):** added
  `tax_graph.review.apply_address_verdicts` and `review apply-address-verdicts`, dry-run by default.
  Exact canonical address plus one node binding plus one unchanged content fingerprint is required;
  the existing `_apply_graph_review` writes the three node fields on an explicit temporary apply.
  Stale, missing, ambiguous, and unsupported records are reported with no write. The real ledger
  entry is stale: reviewed `151f0df27ea00babb02732005d1aed7d2753bb1a0cb0117ab9464c1d75d30ca4`;
  current `e270b15dd0e41720e0a5b7143e9ce8ace5526b008f3cbef8fc91a25c28ac26d1`. No live graph write.
  RAN: `$env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\.codex\visualizations\2026\08\04\019fcd22-0dbe-7481-9da9-77388ec5d84c\pytest_m20_s45_focus';
  .venv\Scripts\python.exe -m pytest tests\test_review_address_bridge_m20.py tests\test_review_workbench_verdicts_m15.py
  tests\test_workbench_m15.py tests\test_review_verdicts_m20.py -q` -> 33 passed.
  RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> ASCII check OK; `git diff --check` -> clean;
  module-form `validate 2025` -> exit 0, graph integrity OK, reconcile differences named.
  RAN: protected-set `git diff --stat -- graph/2025/nodes graph/2025/edges graph/2025/rules graph/2025/field_maps`
  -> empty. RAN: module-form live dry-run -> 1 stale, 0 unresolved, 0 ambiguous, 0 writes, with both
  fingerprints printed. RAN: temporary graph copy using the real ledger record -> `would_apply`, exact
  address/node resolution, node `form_1040_2025_root_line_z`, all three field changes printed, and
  applied/stale/unresolved/ambiguous lists empty because the run was dry.
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
