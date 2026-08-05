# AGENT_HANDOFF.md

The single living doc for active Claude (Architect) <-> Codex (Worker) coordination. Update it in
place; do NOT spawn new per-topic note files. Standing rules: `../AGENTS.md`. Master plan:
`../docs/engineering-plan.md`. Phase plan: `PHASE_M20.md`.

## How to use
- **Worker:** raise questions/blocks under **Open for Architect**.
- **Architect:** answer there (and pin durable decisions into the relevant `PHASE_<id>.md`), then
  clear the item. Record active direction under **From Architect**.
- **THIS FILE IS LIVE STATE ONLY.** The ball, the round in flight, the open questions, and the
  ONE task spec being worked. Durable rulings and standing constraints live in `../AGENTS.md`
  and are never pruned. History lives in git. **Queued future rounds are ONE LINE each** - a
  full spec written rounds ahead goes stale, which is exactly what happened to S57.
- **Keep it short.** A round that completes gets its narration DELETED, not appended - the
  accepted hash is the record and `git show <hash>` recovers everything. Only the current round,
  the standing constraints, and the binding rulings live here.
- **Prune at every acceptance, not "at phase close".** Pruned 2026-07-23 to 1,198 lines, then
  grew to 7,520 by 2026-08-02 because acceptance never triggered a prune. That is the failure
  mode this section exists to prevent.

## BALL

**BALL: WORKER - M20-S65 (`doctor`: MAKE THE PLAN FAIL WHEN IT LIES).** Task block under
**From Architect**. **S63 is ACCEPTED at `aec1ef3`.**

**Why this jumped the queue.** John, 2026-08-05: *"On several occasions I've asked you about things
that were kind of forgotten, undone, or memory holed. How do we guard against this?"* **Six
instances in one day.** The cause is not that the docs are too long - it is that they are INERT.
A stale blocker turns nothing red; a discarded artifact fails no test; an operation offered to the
model but projectable by nothing sits there for forty rounds. `doctor` converts the load-bearing
claims into checks. **It is the only queued work that stops a class of failure rather than patching
one instance.**

**QUEUE - one line each, deliberately. A spec written rounds ahead goes stale; that is what happened
to S57.**
1. **S65 `doctor`** - specced below.
2. **The operation registry** - one versioned source of truth for schema, prompt docs, validator
   dispatch, projection and runtime. Converts 2441 line 8 from `repaired` to `derived` and ends the
   defect class that killed S54 and S55.
3. **S64 candidate regeneration** - the first full run under John's model. Expect roughly 121 of 478
   anchors against 441 handcrafted nodes; that measurement is the deliverable.
4. **Column and grid recovery** - 2441 lines 3 and 30 and their class.
5. **Deterministic phrase obligations** - the only queued work targeting semantic correctness;
   catches 2441 line 25, wrong for six consecutive runs while passing every validator.
6. **S53 the approval gate** - what makes "iterate until approved" mean anything.
7. **Known-red cleanup** - independent, pullable forward; four inherited-red tests mean a new
   failure cannot be told from the baseline.

**FOR JOHN, unresolved and not blocking:** "every cell approved before use" and "a human does not
read every new cell" cannot both hold during bootstrap. The pipeline can remove RE-review, not
first review. That decision shapes S53.

## Current round

**M20-S63 ACCEPTED (Architect, Claude Opus 5, 2026-08-05) at `aec1ef3`. Reading a full run is now
cheap, which is what made running one affordable.**

**Verified against the real thing, not fixtures.** The Architect fed it today's actual run history
across the S60 regression and the S61 recovery:

| document | current | delta | observed band | verdict |
| --- | ---: | ---: | ---: | --- |
| `form_1040_2025` | 17 / 17 | 0 | 17..17 | `in_band_noise` |
| `form_2441_2025` | 20 / 21 | +5 derived | 15..19 | `outside_band` |
| `form_6251_2025` | 26 / 29 | +1 derived | 25..25 (one sample) | `outside_band` |

It caught the real recovery, dismissed the flat document as noise, and showed the band with its
source runs named so a reader can see what is being treated as noise. Expression changes are listed
with both renderings; findings are split into appeared and cleared, and the three
`incomplete_evidence` entries clearing IS the S61 fix rendered as a diff.

**Three refinements recorded in BALL, none blocking:** a one-sample band is not a band and should
report insufficient samples; the deliberate nonzero exit needs documenting; commutative
reorderings and prefix-duplicated findings should be normalized before diffing.

**Gates:** deterministic round, no provider constructed anywhere in it; ASCII OK;
`git diff --check` clean; protected set diff empty.

**M20-S65 WORKER IMPLEMENTED LOCALLY (2026-08-05).** Added the provider-free `doctor` command,
which checks the executable outline blocker, manifest-declared source and region harvest artifacts,
cross-layer operation vocabulary, and handoff-item age. The real checkout reports the outline claim
as `CLEARED`, finds the QDCGT `harvest.yaml`, and exits 1 for the existing operation disagreements
and three active handoff items at 72 handoff-touch commits. It does not repair any finding or write
under `graph/`.

**Verification:**
- RAN: `$env:PYTEST_DEBUG_TEMPROOT = 'C:\Users\devbox\.codex\visualizations\2026\08\05\019fd398-d99b-74b0-ac65-57a2580e9904\pytest_tmp'; & .venv\Scripts\python.exe -m pytest tests/test_doctor_m20.py -q` -> `5 passed`.
- RAN: same temp-root command with `tests/test_runtime_light_m1.py -q` -> `1 passed`.
- RAN: same temp-root command with `tests/test_cli.py -q -k 'expression_agreement_command_writes_report or cli_validate_succeeds or cli_run_reports_line_7_value'` -> `3 passed, 4 deselected`.
- RAN: `.venv\Scripts\python.exe tools\check_ascii.py` -> `ASCII check OK`.
- RAN: `.venv\Scripts\python.exe -m tax_graph.cli validate 2025` -> `graph integrity OK`.
- RAN: `.venv\Scripts\python.exe -m pytest -m m20 -q` -> `259 passed, 8 failed, 3 errors`; failures/errors are the existing ACL-poisoned draft/workbench reads, the manifest-less worksheet test, and the S51 denominator expectation. No guard was edited.
- NOT RUN: provider derivation; this round is explicitly deterministic and provider-free.

**Environment deviation:** the repository-pinned `.test_tmp` is unreadable by this account
(`WinError 5`); focused pytest commands used the writable Codex visualization temp root through
`PYTEST_DEBUG_TEMPROOT`, without `--basetemp`. The full `tests/test_cli.py` also remains red at
`test_harvest_worksheet_command_writes_only_a_draft`; the three affected CLI smoke tests pass.

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

**One spec at a time. Queued rounds are one-liners in
BALL until they are next.**

- **M20-S65 TASK - `doctor`: MAKE THE PLAN FAIL WHEN IT LIES (Architect, Claude Opus 5, 2026-08-05,
  from John's question about forgotten and memory-holed work).** Ledger: the RAN/NOT RUN rule, D10,
  and the standing rules in `AGENTS.md`. **Deterministic. No provider call.** One change, no
  passengers.

  **OPEN ITEMS AND SEAMS THIS ROUND TOUCHES:** none - it is new machinery that guards all of them.
  **Leaves untouched:** the operation registry, S64 regeneration, phrase obligations, S53.

  **Why, with the evidence.** John: *"On several occasions I've asked you about things that were
  kind of forgotten, undone, or memory holed. How do we guard against this?"* **Six instances in one
  day, and the common cause is not volume - it is that our knowledge is prose, and prose cannot
  fail.**
  1. The worksheet harvester was built and proven in S42; its output went to a temp directory and
     was never landed. Nothing tracked that a declared artifact should exist.
  2. Rollover seam 5 specifies a caption-and-geometry re-binder; the Architect invented a thinner
     scheme from scratch because the seam lives in a 935-line document nobody opens when speccing.
  3. `PHASE_M20.md` blocked regeneration on "outline children = 0", **measured 29 and 60 on
     2026-08-05**. A blocker stated as a measurement went stale silently for weeks.
  4. The S36 denominator question dissolved without being closed.
  5. S26 weakened the instruction-text gate; **50 of 67 rows have had no instruction text ever
     since**, and the 1040's booklet IS acquired, so it is a join failure nobody re-raised.
  6. `LOOKUP_BRACKET` has been in the emission enum since S24, undocumented in the prompt and
     projectable by nothing.
  **A stale blocker turns nothing red. A discarded artifact fails no test. That is the defect.**

  **Step 1 - executable blockers.** A plan claim that gates work must be a CHECK, not a sentence.
  Provide a small declarative registry of checkable claims - claim id, the assertion, and the
  command or predicate that evaluates it - and report each as HOLDS, CLEARED, or UNKNOWN. **Seed it
  with the real one:** the outline-children claim from `PHASE_M20.md`, which must now report
  CLEARED. **A blocker that has cleared is the highest-value output of this command**, because that
  is the case nobody notices.

  **Step 2 - declared artifacts exist.** Anything the manifest or a plan declares should exist on
  disk must exist: acquired sources for every manifest document, and a harvest output for every
  accepted region nomination. **The QDCGT case is the test** - accepted, harvested, and it must be
  found where it is declared.

  **Step 3 - cross-layer vocabulary agreement.** Every operation offered to the model must be
  documented in the prompt, dispatchable by the validator, projectable to a rule, and implemented by
  the engine. **Report each operation as a row with a column per layer.** `LOOKUP_BRACKET` must show
  up as a real disagreement, not be special-cased. **This is a REPORT in this round, not a fix** -
  the registry round owns the fix.

  **Step 4 - open items age.** Report every item under **Open for Architect** with how long it has
  been open, measured in commits touching the handoff. **Flag anything older than 20.** John should
  never again be the mechanism by which a stale item is discovered.

  **Step 5 - one command, honest exit code.** `doctor` prints a short report and exits nonzero when
  anything is UNKNOWN or disagreeing. **Document the exit-code contract in its help text** - S63
  shipped a deliberate nonzero exit that reads as a crash because nothing said so.

  **Do not:** call a provider; write inside `graph/`; fix any defect the command finds; add a check
  that cannot fail (a guard that cannot fire is worse than no guard - see S51). **Stop conditions:**
  any diff in the protected directories; a check whose failure mode is untested. Tier 3. Honest
  `RAN:`/`NOT RUN:`. ASCII, `git diff --check`, module-form `validate 2025`. **ONE local commit.**

## History

Everything before M20-S23, and all per-round Worker narration, lives in git history. This file was
pruned from 7,520 lines on 2026-08-02 at S28 acceptance; `git show 12240ef:plans/AGENT_HANDOFF.md`
is the last unpruned copy. Earlier prune: 2026-07-23, from 1,198 lines, for public-repo prep.
Durable rulings were carried forward into **Binding rulings** above rather than deleted; A9
rulings remain pinned in `plans/PHASE_M15.md`; the defect ledger (D6, D9, D10, D12, D13, D14) is
in `AGENTS.md`.
