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

## Open sequencing questions for John

1. **M18 before, with, or inside M16?** Architect recommendation: run **S1+S2 now, in
   parallel with the M17 workbench work** (they are read-only and touch nothing M16 owns),
   then sequence **S3 immediately before M16-S5**, so regeneration has instruction text to
   work from instead of regenerating twice.
2. **Scope of the first pass:** all 7 acquired documents, or the 1040 as canary first?
   Recommendation: 1040 as the S2 canary (73 sections, richest structure), then widen in
   S3 - mirroring M16's Schedule 2 exemplar approach.
3. **Acquire more instruction documents?** Only 7 of the 16 reviewable documents have
   instructions acquired. The 1099/W-2 family are payer-facing information returns whose
   instructions are a different genre; 13614-C is an intake sheet. Worth an explicit
   ruling on which of the remaining documents should be acquired at all.
