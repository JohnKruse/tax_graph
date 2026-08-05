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

**BALL: WORKER - M20-S66 (ONE VERSIONED OPERATION REGISTRY).** Task block under
**From Architect**. **S65 is ACCEPTED at `80b71c5`, and it found something far bigger than it was
built to find.**

**ONLY 3 OF 19 OPERATIONS AGREE ACROSS ALL FOUR LAYERS.** `doctor` reports prompt / validator /
projection / engine per operation. `SUBTRACT`, `LOOKUP_TABLE` and `IF_ELSE` hold. **Sixteen
disagree**, in three distinct families:
- **Offered but undocumented (6):** `COPY`, `SUM`, `MULTIPLY`, `MIN`, `MAX`, `NEGATE` are in the
  emission enum and absent from the prompt. **The model has been choosing from an undocumented
  menu**, which is exactly how it reached for `LOOKUP_BRACKET`.
- **Offered and NOT EXECUTABLE (3):** `DIVIDE`, `ABS`, `ROUND` project to a rule and then hit
  `NotImplementedError("operation ... not implemented in v0")` in
  `tax_graph/engine/operations.py`. **An expression using them would pass every validator and fail
  at runtime.**
- **Documented but unprojectable (7):** `IF`, `AND`, `OR`, `NOT`, `COMPARE`, `REQUIRE_INPUT`, and
  `LOOKUP_BRACKET`. **`REQUIRE_INPUT` is the most-emitted operation on our hard rows** - 2441 lines
  3, 19, 21 and 27 - and it projects to nothing, which is the `unmapped_operation` warning we have
  been reading past for rounds.

**This reframes the registry round.** It was queued as "fix `LOOKUP_BRACKET`". It is actually
**the operation contract is 84% incomplete**, and we have been debugging individual rows on top of
it.

**QUEUE - one line each.**
1. **S66 the operation registry** - one versioned source of truth generating schema, prompt
   documentation, validator dispatch, projection mapping and runtime registration, with `doctor`
   as its acceptance test.
2. **S64 candidate regeneration** - first full run; expect ~121 of 478 anchors.
3. **Column and grid recovery** - 2441 lines 3 and 30 and their class.
4. **Deterministic phrase obligations** - the only queued work targeting semantic correctness.
5. **S53 the approval gate.**
6. **Known-red cleanup** - independent, pullable forward.

**FOR JOHN, unresolved and not blocking:** "every cell approved before use" and "a human does not
read every new cell" cannot both hold during bootstrap. The pipeline can remove RE-review, not first
review.

## Current round

**M20-S65 ACCEPTED (Architect, Claude Opus 5, 2026-08-05) at `80b71c5`. `doctor` works, and its
first real run produced a finding bigger than the round.**

**Verified by running it against the repository, not by reading it.**

| check | result |
| --- | --- |
| executable blocker | `m20_s3a_outline_ready`: **CLEARED**, with the measurement - 1040 60/59, Schedule A 29/28, 2441 40/35. **This is the case nobody notices, and it is now the first thing the command prints.** |
| declared artifacts | 23 sources HOLD; the QDCGT harvest HOLDS at its declared path |
| operation vocabulary | **16 of 19 DISAGREE** - see BALL |
| open item age | three items STALE at 73 commits, correctly flagged |
| exit contract | documented in help text; exit 1 on NEEDS ATTENTION |

**The stale items were the Architect's housekeeping, and doctor caught them rather than John.** All
three are now closed: the S36 denominator question (moot - S51 replaced the denominator with 121 of
478), the two scoping calls (worksheets closed by S59; the filing-status constant answered by
measurement, since `schedule_1a_2025` line 17 and `form_6251_2025` line 18 both emit correct
role-keyed lookups), and "what is next" (John chose option (b), structure and association).

**Architect's own verification of the engine claim, because the finding is severe:**
`tax_graph/engine/operations.py` dispatches `COPY`, `SUM`, `MULTIPLY`, `NEGATE`, `MIN`, `MAX`,
`LOOKUP_BRACKET`, `LOOKUP_TABLE`, `IF_ELSE` and raises
`NotImplementedError("operation ... not implemented in v0")` for everything else. **`DIVIDE`, `ABS`
and `ROUND` are offered to the model and cannot execute.**

**Gates:** deterministic round, no provider constructed; ASCII OK; `git diff --check` clean;
protected set diff empty.

## Open for Architect

**Nothing is open for the Architect.** The three items `doctor` flagged STALE at 73 commits on
2026-08-05 are closed: the **S36 denominator decision** (moot - S51 replaced the denominator
with 121 of 478 anchors and a named reason per skip); the **two scoping calls** (worksheets
closed by the S59 nomination chain; the filing-status constant answered by measurement -
`schedule_1a_2025` line 17 and `form_6251_2025` line 18 both emit correct role-keyed lookups);
and **"what is next"** (John chose option (b), structure and association, on 2026-08-05).

**Open for JOHN, not blocking:** during bootstrap, "every cell receives meaningful human
approval before use" and "a human does not read every new cell" cannot both hold. The pipeline
can eliminate RE-review - approve once against stable semantics, fingerprint the clauses, carry
the verdict while nothing changes - but not first review. That decision shapes S53.

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
