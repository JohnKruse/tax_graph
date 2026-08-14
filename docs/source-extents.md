# Source extents

A citation should say WHERE its text is, not carry a copy of it.

This is a pipeline-validity change, in the terms of `AGENTS.md` section 1. A boundary that is
stored as a range is pipeline output that a human can inspect and correct once, and the correction
survives regeneration. A boundary that is baked into a copied string is invisible, unverifiable,
and is re-guessed by every consumer that reads it.

## The defect this exists to end

The 2025 Instructions for Form 1040 print the Simplified Method Worksheet as separate lines. The
acquired text preserves that separation exactly:

| Range | Source line |
| --- | --- |
| 118182-118265 | `2. Enter your cost in the plan at the annuity starting date . . . . . 2. \_\_\_\_\_` |
| 118266-118490 | `**Note.** If you completed this worksheet last year, skip line 3 and enter the amount from line 4 of last year's worksheet on line 4 below ... Otherwise, go to line 3.` |
| 118491- | `3. Enter the appropriate number from **Table 1** below ...` |

**Line 2 ends at character 118265. The note is a different chunk, and it governs line 4, which it
names twice.** The boundary was present in the source and the pipeline discarded it. What was
promoted into the graph instead is a copy with the two chunks fused:

```yaml
citation_id: cite_simplified_method_worksheet_2025_lines_2
document_id: simplified_method_worksheet_2025
source_document_id: instructions_form_1040_2025
quoted_text: "2. Enter your cost in the plan at the annuity starting date. Note. If you
  completed this worksheet last year, skip line 3 and enter the amount from line 4 of last
  year's worksheet on line 4 below ..."
```

Once that copy exists **nothing can tell it is wrong**, because there is nothing to compare it
against. The consequences were measured during M20-S102: line 2 admitted a prior-year operand it
should have refused, while line 4 - the row the note actually addresses - had no prior-year cue at
all and refused a correct one. Both defects are downstream of one discarded boundary.

## Why it recurs

**Ten independent functions in `tax_graph/extract/` each decide where a printed thing ends**: the
face fallback cleaner, the extent selector, the bracket builder, the serialized-region unwrapper,
the dot-leader stripper, the region note router, the caption splitter, the instruction-section
slicer, the prior-year cue gate, and the face report's own absorbed-block matcher. Each one
re-derives the same judgement from raw text, so a boundary defect appears in as many forms as
there are consumers, and every repair moves hundreds of faces and breaks a pinned count somewhere
else.

Every one of those deciders works by matching printed surface tokens - a line number, `Note.`, a
dot leader, `last year`, a heading that names a line. That produces exactly two failure shapes,
and the defect ledger is full of both:

- **The cue appears where it does not govern.** Line 2 swallowing line 4's note; the Capital Loss
  Carryover rows swallowing `If line 7 of your 2024 Schedule D is a loss, go to line 5`.
- **The cue is absent where it does govern.** The 170 printed anchors that derive with an empty
  instruction packet because no heading names their line; the untitled worksheet blocks that are
  never harvested because there is no title to key on.

Neither shape is fixable by a better pattern. They are both symptoms of there being no
representation of document structure at all - only text, and regular expressions over it.

## The change

**A citation carries a range into its source document. The text is derived from the range, not
copied alongside it.**

```yaml
citation_id: cite_simplified_method_worksheet_2025_lines_2
document_id: simplified_method_worksheet_2025
source_document_id: instructions_form_1040_2025
start: 118182
end: 118265
```

**Every chunk of the source is claimed by exactly one owner, and a chunk that is not a numbered row
says what it is and what it governs.** Today a note, a routing sentence, or a table header has no
way to exist on its own, so it is glued onto whichever row is nearest. Given a kind and a target,
the note above stops being homeless and stops corrupting its neighbour:

```yaml
citation_id: cite_simplified_method_worksheet_2025_note_after_2
document_id: simplified_method_worksheet_2025
source_document_id: instructions_form_1040_2025
start: 118266
end: 118490
kind: note
governs: "4"
```

`kind` is the small vocabulary the corpus actually shows: a numbered row, a note, a routing
sentence, a table header. `governs` is a printed address, which keeps identity in canonical
addresses exactly as `docs/canonical-addresses.md` requires.

## M20-S106 range-rebinding stage

The pilot remains read-only. The deterministic range-rebinding command reads the manifest, the
configured `core_documents`, acquired text, and the existing citation artifacts:

```text
.venv\Scripts\python.exe -m tax_graph.ingest.core_source_ranges --root . --year 2025
```

It binds ranges to existing non-HTML core citations, preserves HTML citations on their structural
`html#` locators, and leaves the documented Form 8978 legacy exemption untouched. It does not
write citations for unclaimed gaps. The former `source-extents-m106.yaml` artifact was removed
because no derivation path consumed its records; a measured gap is not a reachable rule.

The S106 measurement recorded 13,989 rule-bearing characters in configured core documents. The
rework deliberately leaves those gaps reportable instead of making the number fall by relabeling
text. A future promotion stage must require all of the following before it writes a citation:

- the quote remains real prose after layout scaffolding is removed;
- every `governs` target is explicitly named by the source chunk; and
- the citation is attached to a row and reaches that row's derivation packet.

The first two checks alone are not a consumer. Until the third check exists, source-gap promotion
is out of scope.

The M20-S106 measurement used the full 731-row corpus with zero overlaps. Its per-source
measurement was:

| Acquired core source | Rule-bearing characters |
| --- | ---: | ---: |
| form_1040_2025 | 1,393 |
| form_1099_div_2025 | 383 |
| form_1099_int_2025 | 142 |
| form_1099b_2025 | 771 |
| form_1116_2025 | 2,156 |
| form_6251_2025 | 995 |
| form_w2_2025 | 200 |
| instructions_form_1040_2025 | 2,940 |
| instructions_schedule_d_2025 | 850 |
| schedule_1a_2025 | 1,644 |
| schedule_2_2025 | 267 |
| schedule_a_2025 | 84 |
| schedule_b_2025 | 1,018 |
| schedule_d_2025 | 1,146 |

The other configured core sources had zero rule-bearing characters in this measurement. The
remaining rule-bearing text in the all-document report belongs to non-core worksheet owners and is
deliberately outside this round's scope.

## What this makes checkable

These replace pinned counts. A count cannot distinguish an intended change from a regression,
which is how a real defect gets re-baselined away; each of the following is an invariant that
holds independently of any measured number.

1. **A citation's text equals the source slice at its range.** A face that is not contiguous in its
   source becomes impossible to represent rather than something a test has to notice. The
   `form_1040_2025` line `3b` defect found in the S102 rework is in this class.
   **A ROW MAY OWN MORE THAN ONE RANGE, and the design is wrong without this.** Measured
   2026-08-13: seven rows across `form_1116_2025`, `form_6251_2025` and `schedule_d_2025` are not
   linear substrings of their source, **and none of them is a defect.** They are multi-column and
   braced layouts - the 6251 line 5 exemption table, the Schedule D line 21 brace pairing two
   alternatives, the 1116 column headers - where the reading order the face needs is legitimately
   not the linear order of the text. **The invariant is that a row's ranges, in order, reconstruct
   its face; it is NOT that a face is one contiguous slice.** A single-range rule would declare
   seven correct rows broken and invite exactly the fudge that hides real breaks. Note what the
   S102 rework had to do without extents: it compares faces against a dot-leader-stripped copy of
   the source, which is a fair like-for-like given string faces, but it also collapses the very
   boundaries a broken face might be jumping. **Ranges remove the question instead of normalizing
   around it.**
2. **Ranges belonging to one document do not overlap.** Bleed becomes arithmetic. Line 2 claiming
   characters past 118265 is visible without any regex hunting for the word `Note`.
3. **An unclaimed source run remains reportable.** It is not silently absorbed into a citation or
   promoted merely because a classifier called it rule-bearing. The run becomes a citation only
   when the quote, governing target, and row-packet consumer are all proven.
4. **The measured corpus equals the core set.** No document may be excluded from a measurement
   while still being changed by the code under measurement. `FACE_EXTENT_EXCLUSIONS` removing
   `form_2441_2025` from the S102 face report hid three separate failures on that document.

## Consequences, stated plainly

**Offsets move when the IRS revises a document.** A range is derived, never a permanent identifier.
On re-acquisition ranges are re-derived and the content fingerprint decides whether a human
approval survives - the mechanism `AGENTS.md` already defines for approvals, not a new one.

**The already-promoted worksheets carry fused boundaries today.** Repairing the extractor does not
repair them; those citations were written with the defect and need re-promotion. Any plan that
treats this as an extraction-only change will leave the graph wrong.

**Information returns are not addressed by this.** W-2 and the 1099 family do not have numbered
rows carrying rules; their acquired faces are filer boilerplate such as
`Go to IRS.gov/InfoReturn for e-file options`, which is junk before and after any boundary repair.
Getting forms, schedules, and worksheets right should carry most documents added later, because
they share the numbered-row structure. It will not carry the information returns, and they need
their own treatment.

## What this does not change

The prior-year predicate, the ownership marking, the refusal accounting, and the Return Record
carryforward path are all unaffected. This is about how a citation records its source, not about
what the graph means. No new vocabulary enters the expression grammar.
