# Phase M18 - Instruction ingestion (the missing pipeline stage)

**Status:** DRAFTED by the Architect 2026-07-25 for John to sequence. Not started.

Origin: John's 2026-07-25 review of the M17 workbench. Seeing that the IRS instructions
explain the purpose, operation, and treatment of nearly every cell, he ruled that
ingesting them is ROUTINE PIPELINE WORK, not an enhancement. Pinned as guiding invariant
7 in `docs/engineering-plan.md`.

## Why this phase exists

The pipeline acquires the instruction documents and then throws the content away.

Measured state (2026-07-25, real corpus):
- Instruction PDFs ARE acquired for 7 documents - 1040, 2441, 6251, 8949, and Schedules
  A, B, D - each with `.pdf`, `.txt`, `.ocr.json`, `.links.json`, and a `.pages/`
  directory of per-page markdown (the 1040's is 126 pages).
- Exactly ONE instruction citation exists in the promoted corpus
  (`cite_instruction_form_1040_2025_line_1a`) out of 297 total citations.
- So ~99.7% of acquired instruction text has never reached the graph.

The cost is concrete and already visible to a reviewer: 605 of 1921 corpus cells (~31%)
carry `population_policy: unsupported`, whose generated reason is that the control "has
no authored graph, filer-fact, or decision mapping." The instructions are precisely the
source that says what those cells are for. **Instruction text is therefore not just
review UX - it is the input that lets a coverage gap be RESOLVED rather than reported.**
That is why this should land BEFORE or WITH M16-S5 regeneration, not after it.

## MAJOR REVISION 2026-07-27 - THE HTML CHANNEL (John caught this)

John: "Aren't these instructions???? you should at least do a web search to ensure that
there isn't a non pdf version... how can we build this into the pipeline??" He is right,
and the Architect had assumed the acquired PDFs were the only channel without checking.

**The IRS publishes every instruction document as structured HTML at
`https://www.irs.gov/instructions/<slug>`** (e.g. `i1040gi`, `i6251`, `i1099gi`,
`i1041si`). VERIFIED by fetching them, not assumed. This is materially better than the PDF
path for every purpose this phase has:

1. **Per-line headings carry the SEMANTIC NAME, which is exactly what M19-S3b needs.**
   `Line 1 - Adjusted Total Income or (Loss)`, `Line 1 - Taxable Refunds, Credits, or
   Offsets of State and Local Income Taxes`. The PDF path yields `## Line 1` plus body
   prose to be parsed; the HTML yields a TITLED line. This is the missing semantic
   material that blocks concept minting on line-oriented forms.
2. **Stable anchor ids** (`id111`, `en_US_2025_publink1000285809`) are better citation
   locators than page numbers, and they survive repagination.
3. **The hyphenation prerequisite disappears.** This plan previously required repairing
   column-break hyphenation before any text could be quoted, or citation integrity would
   (correctly) reject it. HTML has no column breaks. No OCR either.
4. **It fixes the non-uniform heading problem.** The PDF survey found 73 `## Line X`
   anchors on the 1040 but ZERO on Schedule B, which forced per-document detection. The
   HTML uses a consistent h2/h3/h4 structure with a table of contents.
5. **It closes the apparent acquisition gap at zero cost.** `i1040gi` carries per-line
   instructions for **Schedule 1, Schedule 1-A, Schedule 2, and Schedule 3** - the four
   S3b-blocked documents that have no standalone instruction PDF. Verified headings
   include `Instructions for Schedule 1 Additional Income and Adjustments to Income`
   (id108), `Lines 2a and 2b` (id113), `Instructions for Schedule 2 Additional Taxes`
   (id165), `Lines 1a Through 1z` (id167), and `Instructions for Schedule 1-A Additional
   Deductions` (id158).

**How it goes into the pipeline (this is the deliverable, not a one-off scrape):**

- `config/manifest.yaml` gains an `instruction_url` per document alongside the existing
  PDF entry. The slug is stable across years; the CONTENT is year-specific, so the URL is
  a first-class manifest field that the rollover re-binder re-fetches.
- Acquisition fetches the HTML into `.cache/raw/<year>/` beside the PDF, recording URL,
  `retrieved_date`, and a content hash - the same provenance discipline as every other
  acquired artifact. **Citations must be verbatim from the ACQUIRED file, never from a
  live fetch at citation time**, so the stored HTML is what `check_citation_integrity`
  verifies against.
- Mining reads the heading tree; a per-line heading yields both the line token and its
  semantic title, and its anchor id becomes the citation `locator`.
- **PDF stays as fallback and cross-check**, not as the primary. Where both exist and
  disagree, that is a finding, not a silent preference.
- **ASCII rule applies at ingest:** IRS headings use em dashes (`Line 1-Adjusted...`
  is really an em dash). Transliterate on the way in, or the ASCII gate bites.

**Consequence for scope:** the 1099/W-2 family HAS HTML instructions too (`i1099gi`,
`i1099div`, `i1099int`, `i1099b`, `iw2w3`), so the "different genre, skip them" argument
weakens - acquisition is now cheap enough that the question is whether the CONTENT is
useful, not whether obtaining it is worth the effort. Still John's ruling to make.

## What makes this tractable (surveyed, not assumed)

The per-page markdown already carries machine anchors, so this is structure-first mining,
not label/geometry guessing - the same discipline M16-S3 established:

- `## Line 3b` / `## Lines 4a, 4b, and 4c` section headings map onto the printed line
  token the canonical address already carries. Counted across the corpus: 1040 **73**
  line-sections, Schedule A 14, 6251 12, 2441 4, Schedule D 2, 8949 1, **Schedule B 0**.
- `### Ordinary Dividends` subheadings give a per-line TITLE distinct from the body.
- Recurring labeled blocks are minable as typed content: `**Exception.**`,
  `**Example 1.**`, bold standalone warnings, bullet lists, and cross-references
  ("See Pub. 550", "See the Schedule B instructions") that are real link targets.

Two hazards the survey already exposed, which the design must handle rather than
discover late:
1. **Schedule B has zero `## Line` headings** - heading conventions are NOT uniform across
   documents. A single miner tuned on the 1040 will silently under-serve the rest. Per-doc
   convention detection is a requirement, and a document whose convention is unrecognized
   must FAIL CLOSED into a report, never be silently skipped.
2. **Column-break hyphenation artifacts** in the extracted text, e.g. "Enter your total
   ordinary div-" / "dividends on line 3b". De-hyphenation and reflow must happen before
   any text is quoted, because quoted text is verbatim and integrity-checked - a mangled
   quote will fail `check_citation_integrity` (correctly).

## Invariants

- **Verbatim from acquired source, always.** Instruction text rides the existing citation
  machinery with `quoted_text`, `locator`, `url`, `retrieved_date`. Never synthesize,
  paraphrase, summarize, or "clean up" instruction prose into a citation.
  `check_citation_integrity` has teeth and the M14 fabricated-citations reopen is the
  precedent.
- **Structure-first join.** Sections join to cells through the canonical address (the
  printed line/box token), never through geometry or mined labels - the M15R identity
  lesson and the M16 resolver rule.
- **Fail closed.** An unmatched section, an ambiguous multi-line heading, or an
  unrecognized document convention is a reported finding, never a guess.
- **Read before write.** The first step produces a report and changes no artifact -
  the M16-S3 pattern.

## Step sequence (proposed; just-in-time refinement per step)

- **S1 - CORPUS SURVEY, READ-ONLY (Worker-suitable).** Per instruction document: detect
  the heading convention, count line-sections, and compute what fraction of that form's
  printed lines have a candidate instruction section. Characterize the block taxonomy
  (line section, exception, example, worksheet, cross-reference, definition) and the text
  hazards (hyphenation, repeated headers/footers, multi-column reflow, table blocks).
  Deliverable: `plans/M18_S1_INSTRUCTION_SURVEY.md` - the work list, including the honest
  list of documents whose convention the miner does NOT yet handle. No artifacts written.
- **S2 - THE MINER, READ-ONLY OUTPUT.** A module (suggested
  `tax_graph/ingest/instruction_sections.py`) that parses a document's `.pages/` markdown
  into structured, typed sections: the line token(s) the heading names, the title, the
  body blocks with their types, the source page, and the character span. De-hyphenate and
  reflow before emitting text. Deterministic and idempotent; emits candidates, promotes
  nothing.
- **S3 - ADDRESS JOIN + PROMOTION (first artifact-writing step; Architect-reviewed).**
  Join sections to canonical addresses on the line token, expanding multi-line headings
  ("Lines 4a, 4b, and 4c") to each address. Promote matched sections as cited spans
  carrying `quoted_text` + `locator` (page + line) + `url` + `retrieved_date`, keyed to
  the address. Ambiguity and misses fail closed into the review queue. Ratchet: a
  named-and-counted coverage number that only moves up.
- **S4 - WORKBENCH SURFACING.** Instruction title + body become the HEADLINE content of
  the M17 cell dossier - "what is this cell for, in the IRS's own words" above the graph
  metadata - with the citation shown and the coverage gap named where no section matched.
  Folds into the M17 S4 dossier layout.
- **S5 - COVERAGE-GAP RESOLUTION (meets M16-S5).** Use the joined instruction text as the
  input for giving the ~605 `unsupported` cells a real disposition: a cited graph rule, a
  filer-fact mapping, an explicit decision, or an explicit out-of-profile reason. This is
  where M18 and M16-S5 regeneration converge; sequence them together.

## Sequencing - DECIDED 2026-07-27

1. **When: M18 runs NEXT, in full (S1+S2+S3).** [DECIDED - John took the recommendation.]
   The M19-S1 survey settled the ordering: M18 precedes M19-S3b (line-oriented forms have
   no semantic material to mint from without it) and precedes M16-S5. Stopping after S1+S2
   would only add a handoff, since S3 is the part that unblocks S3b.
2. **Scope: 1040 as canary, then widen.** [DECIDED - John took the recommendation.]
   The 1040 general instructions are the richest case and now cover Schedules 1, 1-A, 2,
   and 3 as well. Prove the approach on one document before committing, mirroring M16's
   Schedule 2 exemplar. M19 justified this the hard way: S3a looked complete on the 1040
   until the W-2 exposed a whole class of silent flattening.
3. **Acquisition: no new PDFs - build the HTML channel instead.** [ANSWERED by the HTML
   revision above; the remaining ruling is narrow.] The four apparently-missing documents
   (Schedules 1, 1-A, 2, 3) are covered per-line inside `i1040gi`, verified. So nothing
   needs acquiring that is not already reachable. **Still open for John:** whether to
   ingest instructions for the 1099/W-2 family and 13614-C at all. They DO have HTML
   instructions, so cost is no longer the objection; the question is whether
   payer-facing filing instructions (how to FILE the form) help a filer-facing review
   surface (how to READ the form). Architect leans yes for the 1099/W-2 box definitions,
   no for 13614-C, but it is a judgment call about usefulness, not feasibility.
