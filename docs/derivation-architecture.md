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
