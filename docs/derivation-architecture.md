# Derivation architecture - the mid-term target (pinned 2026-08-16)

**Written after four consecutive rounds broke derivation while passing their tests. This exists so
that a niggling problem does not divert the direction. Read it before speccing any derivation
round.**

## The one thing that is proven

**Given the right evidence, the model reads IRS forms correctly.** Every failure opened end to end
this week had a CORRECT model answer: `form_1040` 11a, `schedule_2` 1z, `form_6251` 13 and 18,
`form_2441` 15. `form_1040` 36 answered the wrong question correctly - it was routed to an
arithmetic prompt by a substring match, and `COPY` was the best available answer to
*"what operation combines which lines"*.

**The AI half is not the risk.** Every catastrophic failure came from the deterministic half: the
evidence-packet builder (zeroed derivation for two weeks), the arity/role contract (zeroed it
twice), a response-schema shape (zeroed it once), the formula cue matcher (misroutes elections).

## Why rounds keep failing

**The model-to-graph contract lives in FOUR places that must agree**: the prompt, the response
schema, the validator, and assembly/resolution. **Nothing checks that they agree.** The only thing
that has ever caught a disagreement is a twelve-minute corpus re-derive reporting a single number.
Four rounds, four breaks, each a mismatch between two of the four layers - and each passed its
targeted tests (67, 90, 91, 91 passed).

**A floor is an acceptance gate, not a development signal.** It says THAT something broke, never
WHICH layer or WHY. Optimising against one end-of-pipeline number is how whack-a-mole happens.

## The target architecture

**1. The deterministic layer shrinks to what it is good at: FETCH, RESOLVE, EXECUTE.**
Fetch the evidence for a line; resolve printed references to canonical addresses; execute
arithmetic. **It stops making judgement calls** - no cue matcher deciding what a line "is", no
guessing which operand shape was meant.

**2. The model owns classification and reading.** One call per addressable line returns a
discriminated kind - computation, filer entry, election, information return, not derivable - with
the fields that kind requires. Cue phrases become EXAMPLES in the prompt, never gates. **The prompt
requires grounding: answer only from the supplied evidence, else return not-derivable.**

**3. Confidence comes from voting, not from gates.** Three samples at different seeds, majority on
the canonicalised answer (operation plus a role-to-operand map; the QUOTE is excluded - two answers
may cite different sentences and mean the same rule). 3-0 green, 2-1 yellow, 1-1-1 red.
**Agreement is a CONFIDENCE signal, never a correctness signal** - `form_1040` 36 would be a
confident 3-0 and wrong.

**4. Systematic error is caught by lints over the printed face, not by voting.** `pilot/face_lint.py`
already finds what voting never will: a line printed as a filer election that derived as `COPY`.
**Vocabulary belongs in the CHECKER, not the prompt** - a wrong lint costs a reviewer seconds, a
wrong prompt instruction corrupts output silently.

**5. Human review is adjudication, and the COMMENT is the durable artifact.** The reviewer sees the
variants, the agreement colour, and the lint flags, and picks A/B/C or None-of-the-above with a
comment. **A pick alone does not survive regeneration; the reason does.** None-of-the-above is a
NEGATIVE CONSTRAINT - "not these three, and here is why" - which prunes the space far better than a
bare rejection. `rederive_cell(document_id, line, draft_comment)` already exists; it needs the
candidate set passed through.

## Sequencing, and why this order

**FIRST: a replay harness.** Recorded real model responses replayed through the whole
resolve-and-assemble path, in seconds. **Nothing else lands safely until this exists** - it converts
a twelve-minute pass/fail into a five-second diff that names the layer. Every one of this week's
four breaks would have surfaced instantly.

**THEN: the model owns the path** (the withdrawn S111), measured against the cue matcher before the
matcher is deleted.

**THEN: voting**, and the review UI that consumes agreement plus lint flags.

**Ordering rule: never change the mechanism and the measurement in the same round.**

## Standing constraints learned the hard way

- **A green targeted test set is NOT evidence for a response-schema change.** `tests/` validates
  hand-written payloads against the validator; nothing asserts a real response still resolves end to
  end.
- **A corpus re-derive costs $0.046 and twelve minutes.** Cost is never a reason to skip a
  measurement.
- **Output varies +/-2 rules run to run.** State floors as RANGES; a smaller delta is not evidence.
- **Open at least three individual failures end to end before naming a class** (`AGENTS.md` hard
  rule). An error string names the stage that raised, not the cause.
- **The Worker cannot run pytest bare in its sandbox** - it hits `WinError 5` on the poisoned
  `.test_tmp\pytest-of-devbox` ACL and reports 46 passed / 36 errors. **Bare-run verification is the
  ARCHITECT's job.** Do not write it into a Worker floor.

## What the replay harness can and cannot do (measured 2026-08-16, `80980e7`)

`pilot/replay_harness.py` replays 21 recorded `(prompt, raw response)` pairs through the PRODUCTION
validator, operand resolver and assembler. **21 cases, 0 mismatches, 5 seconds, zero network calls.**
Diagnostics are per layer and name the cell, e.g.
`form_6251:18 schema_valid=Y validator_accepted=N operands_resolved=Y assembled=N`.

**IT CATCHES:** regressions in the resolve-and-assemble path, and schema breaks like S108's
structured-output `400` and S111's `kind` change. Pointed at S109 (`c47f5fa`) it fails 20 of 21,
exit 1.

**IT CANNOT CATCH:** what a CHANGED PROMPT will make the LIVE model emit. It replays OLD responses.
S109 broke because its new prompt drove the model to produce `{"form": "9", "line": "9"}` - a shape
no recorded fixture contains - so on the S109 tree the harness reports
`production prompt differs from recorded prompt` on 19 of 20 cases and `assembled=Y` on several,
while the live corpus was at 16 rules.

**THEREFORE the prompt-drift tripwire is the most valuable signal in it, not noise.** It means: *the
recorded evidence is stale and predicts nothing; go run the corpus.*
**A GREEN HARNESS IS NEVER PERMISSION TO SKIP THE CORPUS RE-DERIVE ON A PROMPT OR SCHEMA CHANGE.**
That is exactly the round type that has broken derivation four times.

## Rulings from John, 2026-08-16

**THE S113 RECLASSIFICATION IS CORRECT AND S113 IS ACCEPTED.** Rules fell 108 -> 78 because the
model stopped forcing non-computations into arithmetic. **A rule COUNT is not a quality metric and
must never again be used as a floor.** Six floors were written that the work could not satisfy as
specified, most of them by assuming more rules is better. **State floors as OUTCOMES** - what a
named cell produces, whether a lint class is empty, whether a surface opens - never as a count the
round's own success would violate.

**`filer_entry` NEEDS A REASON TAXONOMY, NOT A SINGLE FLAG.** S115 introduces *filer-supplied
because derivation FAILED*. John: *"we just added a type of filer entered because of failure,
perhaps we should have a filer entered because of missing/unprocessed form."* At least two reasons,
and they mean different things to a reader and to the roadmap:
- **`derivation_failed`** - the pipeline had the evidence and could not resolve it. A defect.
- **`source_form_not_modelled`** - the answer legitimately comes from a form outside the corpus.
  `form_1040` 1f, *"Employer-provided adoption benefits from Form 8839, line 31"*, is this: Form
  8839 is not acquired. **Not a defect - a scope fact, and a queue entry for acquisition.**

**WORKSHEETS EXIST TO SUPPORT THE FORMS THAT REFERENCE THEM.** John: *"we model the worksheets so
that they can support the forms."* `form_1040` 6b declined with *"the evidence says to use the
Social Security Benefits Worksheet, but the worksheet is not in the packet"* - **and that worksheet
is in the graph.** An honest decline over a document we already own is a PACKET defect, not a
correct outcome. **When a line's evidence names a worksheet the graph contains, that worksheet's
content belongs in the packet.**

**ROUTING IS ITS OWN CONSTRUCT. IT IS NOT AN ELECTION AND NOT A COMPUTATION.** John on
`schedule_d` 17, *"Are lines 15 and 16 both gains? Yes. Go to line 18. No. Skip lines 18 through
21"*: *"line 17 is a choice for flow control purposes. It causes you to either fill or skip 18-21.
So, I'd call it a routing."*
- The graph has no way to express control flow, so `election` absorbed it - **the same failure mode
  as `COPY` absorbing `form_1040` 36.** A kind with no competitor collects everything.
- The family is larger than one line: the Schedule D Tax Worksheet carries *"If lines 1 and 16 are
  the same, skip lines 23 through 43 and go to line 44"* and several siblings.
- **Until routing exists, `election` must be validated so it does not keep absorbing branches** - an
  election is a choice the FILER makes; a branch determined by other lines is not one.
