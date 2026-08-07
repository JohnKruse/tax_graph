# Review notation - working design note

Status: **OPEN DISCUSSION, not settled.** Started 2026-08-05 with John. This note exists so the
thread can be picked up rather than re-derived. Nothing here is implemented.

Mock-ups produced during the discussion (private artifacts):
- three renderings of one cell - worksheet, flowchart, pseudocode
- a review panel with three real cells, instructions beside the diagram

## Why this exists

The reviewer's job is to hold the printed IRS instruction next to what the pipeline understood and
say yes or no. John, 2026-08-05: *"the truth is, it's ability to be reviewed by a human and compared
to the english text of the original instructions/labels is really the key."* Traceability of
sub-parts is secondary to that.

The panel layout John asked for: **instruction sources on the left as headed bullets** - Label, Cell
instruction, Other instructions, never concatenated - **and the diagram beside them**, verdict
controls last. He accepted that diagrams may stretch: *"I understand that these things may stretch
out a bit."*

## The rules agreed so far

Every one of these came from John correcting an Architect draft. The pattern is that **the
Architect's defaults are programmer defaults and are wrong in the same direction every time.**

1. **A diamond asks; the arrows answer.** Never embed the answer in the question. The first draft
   asked `Line 22 checked "No"?` with Yes/No arrows, which is a double negative.
2. **A checkbox diamond is a template, not a paraphrase:** `Line X checked?: <subject>`. Invariant
   wording, only the subject changes, and `checked?` makes the boolean type visible. It degrades
   safely - with no derivable subject, `Line 22 checked?` is still answerable.
3. **Reference lines, never re-narrate them.** The reviewer has the form open. Restating a line is
   noise and invites paraphrase errors: an Architect draft turned line 22's question into
   `line 12 or 13 > 0`, which is **wrong** - line 22 asks whether the money came from
   self-employment, not whether it exists.
4. **The arrow is the reference.** No step letters in a flowchart; a box transforms whatever reaches
   it. Worksheets need letters because they have no arrows.
5. **One operation per box. Nothing compound.** `MAX(line 11b - line 14, 0)` becomes
   `line 11b - line 14` then `MAX(amount, 0)`. Keeps boxes short, and a wrong step is one box rather
   than a clause buried in a nested expression.
6. **Mathy, not prose.** The IRS's *"subtract line 14 from line 11b"* states operands in the reverse
   of computation order - the exact construction behind our recurring `subtract_direction` failures.
   `line 11b - line 14` cannot be misread. Prose stays in the instruction bullets, quoted verbatim.
7. **`amount` is the placeholder for the value arriving on the arrow.** `MAX(0)` alone reads as the
   maximum of a single value and confuses people. Name the operand when it is a line; use `amount`
   when it arrives on the arrow. John: *"a typical joe will see the max of a single value and be
   confused - as I was."*
8. **No specialist vocabulary.** `MIN`/`MAX` are admissible because spreadsheets made them ordinary.
   **`floor`, `ceiling`, `clamp`, `truncate` are not.** John: *"I'm a 60 year old MBA and I had never
   seen floor until 2 years ago."* The test: **a term is either the IRS's own word, or it is
   genuinely common.** Mathematical correctness is not a defence. Note our own validator is named
   `missing_floor` - the jargon is already inside the system and must stop at the human boundary.
9. **AMENDED 2026-08-07. Every cell shows something; the FORM varies, never the presence.**
   Originally: draw a diagram only where the cell branches, because a flowchart for
   `line 15 - line 22` is worse than text. That still holds for the *flowchart* form, but the S77
   options page implemented it as a dead-end message and John rejected the result: *"I'd be inclined
   to show some kind of diagram for even simple math operations... or just show the operation
   mathematically. It is just difficult to review a row with holes."*
   **The reviewing eye must land in the same place on every row.**
   **REFINED 2026-08-07 (John, on 2441 line 20): the gate is OPERATION COUNT, not branch presence.**
   He asked why `min(line 17, line 18, line 19)` then `max(amount, 0)` was not drawn - *"there are
   two operations here"* - and he is right; the first amendment sent it to a one-line math form.
   - **one operation** -> the math line, `line 23 = line 15 - line 22`.
   - **more than one, no branch** -> a **vertical chain of boxes**, one operation each.
   - **branches** -> a diamond whose arms **genuinely diverge**. Two arrows leaving the same vertex
     down the same axis is the S78 defect: they overlap, read as one exit, and the second passes
     through the first box while its label lands inside it.
   - **lookup table** -> a **table**, which is a NODE SHAPE, not a separate rendering. It may stand
     alone (2441 line 8) or feed a box inside a flowchart (6251 line 18's threshold and offset).
   - **no operation** -> a named finding in the same vocabulary, **carrying its actual reason**.
   **An empty column, a bare "no branch" string, a raw payload dump, or a reason-free "needs review"
   is never an acceptable answer.**
11. **NEW 2026-08-07. THE PANEL IS TWO COLUMNS, AND POSITION CARRIES MEANING.**
    John chose the layout after comparing five generated renderings. **Left third: the Tree, with the
    Math beneath it** - *"I like the idea of two lossless reps in the same col."* Both are faithful
    projections of the stored expression; the Tree's labels ARE the graph's edge roles, and the Math
    is the same tree flattened. **Right two thirds: the flow diagram.**

    **Arrow position is the notation, borrowed from IDEF0's ICOM discipline but ROTATED, because our
    flow is vertical where IDEF0's is horizontal.** John: *"our flows are now vertical from top to
    bottom. I feel like numbers/lines should flow from the top, conditions and thresholds from the
    sides."* No IDEF0 numbering (rule 4 forbids step letters) and no ICOM vocabulary (rule 8);
    **the position is the label.**
    - **Top** - values entering: line references and amounts from the previous step.
    - **Bottom** - the result leaving.
    - **Right** - **moderators**: thresholds, rates, constants, and the facts that SELECT among
      variants. One gutter, not two - John: *"i fear it being a width constraint."*

    **This is what finally shows a hidden decision.** On `form_6251_2025` line 18 the threshold is
    `$239,100` OR `$119,550` depending on filing status; today it arrives looking like any other
    value. As a labelled moderator with filing status beside it, the reviewer can SEE the number was
    chosen rather than given - the open question this document has carried from the start.

    **Colour REINFORCES, it never carries the meaning alone.** Colour fails for colour-blind readers,
    dies in print, and needs a legend, which is vocabulary by another name. **The arrow's label does
    the work** - and it is free, because the graph already stores the edge role (`threshold`, `key`,
    `default`, `multiplier`, `subtrahend`).

    **Shape capacity:** a **rectangle** may take several right-entering moderators, stacked at
    different heights. A **diamond** takes exactly one, at its right vertex - several arrows
    converging on a single point cross and read badly, and rule 5 already makes one enough. A
    **table** absorbs its own key and variants as rows, needing no arrows at all. **A shape wanting
    more is rule 5 saying the cell should be split**, not a layout problem.

12. **Phrasing belongs in the operation registry**, one declared wording per operation, so the
    flowchart, worksheet and pseudocode cannot drift apart. Same single-source pattern that fixed the
    operation vocabulary in S66/S67.

## OPEN - raised by John and not resolved

- **A threshold is a decision, but is not written as one.** In the 6251 line 18 draft the threshold
  is a process box (`threshold = $239,100 / $119,550 if married filing separately`) feeding a
  decision diamond. But **selecting the threshold is itself a decision** - it depends on filing
  status - so the diagram has a hidden branch drawn as a straight line. Either the notation needs a
  way to show a status-dependent value without a full branch, or these need two diamonds. Unresolved.

- **The `UNRESOLVED` block on 2441 line 25 is obviously recoverable to a human.** John: *"the chart
  for form 2441 line 25 has this unresolved block, when it is clearly MIN(line 20, line 21), which is
  in a different branch."* A person reads the sibling branch and knows instantly what belongs there.
  The pipeline does not. Open question whether a repeated sub-expression referenced from a sibling
  branch should be recoverable deterministically, and what that implies for rendering versus for
  derivation.

- **What the panel should do with a hole.** Architect's view, not agreed: a cell containing an
  unresolvable operand should fail before reaching a reviewer, because asking someone to review a
  diagram with a gap in it spends the scarce resource for nothing.

## Findings behind the discussion

- **2441 line 25 was never derivable.** The correct expression needs depth 4; the emitted wire schema
  permits 3, verified by validating the correct tree against it. Eight consecutive runs produced
  partial answers because the shape was forbidden, not because the model reasoned badly. John
  approved raising the bound; measured cost is linear, roughly +1,600 tokens at depth 6, so there is
  no real cost.
- **`{"node": "__invalid__"}` was written by the model, not by our code** - grep confirms the string
  appears nowhere in `tax_graph/`. Cornered by the depth ceiling, the model reached for the one
  escape hatch the grammar offers, a named-node operand, and had nothing to point at. **An
  unresolvable node operand is therefore a reliable signal that the grammar could not express what
  the source says** - a different problem from a wrong answer, and worth its own finding kind rather
  than being folded into `payload`.
- **A checkbox is boolean and the PDF already says so.** Form 2441 carries 57 `Text` widgets and 15
  `CheckBox` widgets. Line 22 additionally carries **both an answer and an amount** - check No and
  its value is -0-, check Yes and it holds the figure - so line 25 branches on the answer while other
  rows consume the value. Any model that collapses them loses a distinction the form makes.
- **Showing the two instruction sources separately caught a real defect.** The booklet section joined
  to 6251 line 18 is the **Form 1040-NR variant**. The arithmetic matches so every validator passes,
  but the source shown to a reviewer would be for the wrong filer. Concatenated into one blob nobody
  would have seen it.

## Prior art considered

**ASD-STE100 Simplified Technical English** - the aerospace standard John recalled, created in the
1980s for civil aviation maintenance manuals; current edition January 2025 is 53 writing rules plus
about 900 approved words, each with one meaning and one part of speech. Its principles apply: active
voice, one instruction per sentence, no synonyms, one approved term per concept.

**Do not adopt it.** Its tooling is checkers for humans writing prose; we are realising a bounded
expression tree, which is a far smaller problem - roughly 30 words, not 900, and generated from the
registry rather than policed after the fact. **And our controlled dictionary should be derived from
the IRS corpus, not authored** - STE would never contain *smaller of*. A rendering term that never
appears in the corpus is a signal we have drifted into our own dialect.
