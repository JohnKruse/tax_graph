# PHASE M20 - Form extraction rebuild and two-witness reconciliation

> Phase plan, 2026-07-28. Architect (Claude Opus 5), at John's direction.
> Evidence: `M20_FORM_EXTRACTION_EXPERIMENT.md` (measurements, John-adjudicated).
> Master plan: `../docs/engineering-plan.md`. Standing rules: `../AGENTS.md`.

**Canary: Ground Truth.**

## 1. Why this phase exists

John, 2026-07-28: "I keep having the feeling that our pipeline is really shoddy and you
just keep manually putting gaffer's tape on it." He was right, and the measurement located
it precisely: `render_form.py` keeps a mean of **52.2%** of each form's printed text
(13614-C 17%, the 1040 52%). It discards every token before a detected line anchor, drops
anchorless rows outright, welds words when it deletes non-ASCII punctuation, and misreads
`box 5` as line 5. That stored `.txt` is what `check_citation_integrity` validates form
citations against, which is why the same defect kept resurfacing at the citation layer
(M16-S2 `z -> 1z`, M18-S2b wrapper pollution). **We were fixing symptoms of one upstream
defect for three phases.**

## 2. The measured asymmetry (this is the whole design)

The two extractors fail in UNCORRELATED ways, and each is near-infallible at what the
other is worst at:

| | deterministic (PyMuPDF) | OCR (Mistral) |
| --- | --- | --- |
| content | **complete by construction** - it IS the text layer | silently omits |
| structure | conflates columns, splits `17a`, misreads option codes as anchors | tables, block types + bboxes, correct label joins, header/footer |
| reproducibility | byte-identical every run | **3 distinct outputs in 4 runs** |
| fabrication | 2.6% (own scaffolding, apostrophe welds) | 0.2% (image syntax, dehyphenation gains) |

Corrected retention, ten UNSEEN forms plus the 16-form corpus: shipped renderer 52.2%,
`find_tables()` 67.9%, OCR 99.4%, and a **prototype corrected deterministic path 100.0% at
0.0% fabrication**. The corrected deterministic path also covers **99.8%** of everything
OCR read - two independent readings corroborating each other.

**The failures that define the architecture, all measured:**

- **OCR omits silently and sometimes STABLY.** Schedule E line 4 `Royalties received` was
  dropped in **all four runs**. Eleven other drops on that page (lines 20-26, 23a-e) were
  transient and recovered on rerun. John reproduced the line-4 drop independently in
  Mistral Studio.
- **The omission is invisible in OCR's own metadata.** The block covering lines 3 and 4
  was correctly DETECTED (`type=list`, bbox spanning both rows) but its transcribed content
  held only line 3. Page confidence was avg **0.9921** / min **0.4915**, and every
  low-confidence token was a dot leader or newline - **nothing near line 4, because a
  dropped row emits no tokens at all**. **Confidence scoring cannot detect omissions.**
- **Voting fixes variance, not bias.** N runs would have recovered the 11 transient drops
  and would NOT have recovered line 4 - and three agreeing runs would have raised false
  confidence in an output missing an income line.

## 3. Architecture

### 3.1 Content authority: deterministic, ALWAYS

Every `quoted_text`, `printed_label`, and citation derives from the deterministic text
layer. **OCR is never a content source.** This single rule neutralizes OCR's worst failure
mode: it cannot delete content we never sourced from it. Given that omissions are silent,
partly stable across runs, and invisible to confidence scoring, any design that takes
content from OCR is unsafe.

The verbatim-from-acquired-source invariant is unchanged and absolute. The M14
fabricated-citations reopen is the precedent.

### 3.2 Structure: proposals from BOTH, authority from NEITHER

OCR proposes table cells, block types + bboxes, reading order, label joins, header/footer.
Deterministic geometry proposes widget positions (AcroForm, spec-level, verified across
three producers) and same-row caption association (measured 82-85% on line-oriented forms,
51% on the 13614-C questionnaire). Both are PROPOSALS that must survive reconciliation.

### 3.3 The three mechanical checks

Each catches a failure we actually observed. None is a quality score.

1. **Content accountability.** Every deterministic content token must land in some
   structural slot; unassigned text is a named finding. **This is what catches Schedule E
   line 4** - OCR's structure has no slot for it, the deterministic text has the words, so
   it surfaces as unassigned instead of vanishing.
2. **Line-number contiguity.** Printed line labels within a section must be contiguous; a
   `3 -> 5` jump is a finding. Catches the same defect **from OCR output alone**, needs no
   second source, and generalizes to every form.
3. **Fabrication check.** Every OCR token must exist in the deterministic text, modulo
   three known-benign classes (markdown image syntax, dehyphenation joins, label joins).
   Already prototyped; runs corpus-wide in seconds.

**Explicitly NOT a check: OCR confidence scores.** Measured useless for omissions (3.2).
Cross-run variance IS usable as a structure-stability signal - flag any page whose word
count swings materially between runs (Schedule E ran 289 words against a stable ~480).

### 3.4 Consequence tiers (John's requirement: strictness proportional to consequence)

- **Tier A - must be exact. FAIL CLOSED.** Cell identity, line/widget binding, amounts,
  anything the engine computes from or prints. Disagreement blocks promotion and raises a
  finding. An error here is a filing error.
- **Tier B - must be attributed, wording tolerant. FAIL OPEN with a recorded note.**
  Captions and instruction prose for human/AI understanding. Take the deterministic
  version, record the disagreement, do not block. John's redundancy argument applies: "a
  slightly different form instruction will likely be counteracted by an extracted
  instruction from the instruction page" - the same rule is stated twice, so a wording
  difference is self-correcting.
- **Tier C - cosmetic. Ignore, but COUNT.** Dot leaders, icons, decorative rules. The
  Form 4137 `CAUTION` GIF lives here.

The tolerance in Tier B is about WHICH acquired source a string comes from, never about
whether it is verbatim from one. That invariant holds at every tier.

### 3.5 Human review: light, but expected to find real problems

John, 2026-07-28: review "should be light but some of these forms are so badly designed
that I view it as inevitable that there will be problems found by a reviewer."

Design consequence: **reviewer attention is routed to FINDINGS, never to browsing cells.**
A reviewer should never page through 1,921 cells looking for trouble; the machine produces
a ranked queue of Tier A disagreements, unassigned text, and contiguity gaps, and the
human adjudicates those. The 10-form experiment is the model - roughly 20 disagreements
across ten unseen forms, adjudicated by John in minutes, and every one turned out to be a
real defect on one side or the other.

Measure and report, per form: findings raised, findings upheld, reviewer minutes. If
findings-per-form climbs without upheld-findings climbing, the checks are too noisy and
get tuned; that is the ratchet on review cost.

**DISAGREEMENT OVERLAY (John, 2026-07-28): "would it make sense to somehow show where the
OCR and determ passes don't necessarily agree to just draw the eye of the human
reviewer?"** Yes, and it is nearly free, because a disagreement already HAS coordinates:
OCR blocks carry `top_left_x/y` and `bottom_right_x/y`, deterministic words carry rects,
and the workbench already renders the real page with geometry overlays (M17-S7 captured
per-page width/height/rotation for exactly this kind of positioning).

Requirements when this lands (S4, with the overlay surface prepared in S3):

- Render disagreement regions as a distinct overlay on the page canvas, visually separate
  from the existing selection and policy-state treatments. Follow the M17-S6 lesson: use
  LUMINANCE and SHAPE, not hue alone, so it survives colorblindness and grayscale, and
  keep a minimum marker size so a sub-20px checkbox region still reads.
- **Distinguish the three kinds** so the eye can triage without clicking: text only the
  deterministic pass found (the Schedule E line-4 case), text only OCR found, and a
  disagreement about STRUCTURE (which cell a caption belongs to) rather than content.
- Tier the visual weight (3.4): Tier A disagreements are loud, Tier B is a quiet marker,
  Tier C is not drawn at all but stays countable.
- **An unassigned-text region must be drawable even though no cell owns it** - that is
  precisely the Schedule E line-4 signature, and a surface that can only highlight known
  cells would render it invisible, which is the failure we are trying to make impossible.
- Keep it a projection: the overlay reads reconciliation findings and changes no promoted
  artifact, no verdict, and no human-review claim.

## 4. Step sequence

- **S1 - MEASUREMENT HARNESS [COMPLETE, `cdb209c`, Architect-verified `f1771e0`].**
  Committed `measure-extraction` command, per-document retention/fabrication snapshot, and
  a hash-pinned producer-robustness corpus (California 540 2024, IRS 1040 1999) that is
  test data only and absent from the manifest and graph.
  **Carried defect:** the harness token regex `[a-z0-9$%]+` splits currency on the comma
  (`$1,000` -> `$1` + `000`), so its DISAGREEMENT counts are not trustworthy until fixed.
  Retention percentages are prose-dominated and unaffected.
- **S2 - DETERMINISTIC TEXT REBUILD (content half; the cheap decisive win).** Rewrite the
  form text path to emit a COMPLETE verbatim text layer plus a SEPARATE line-anchor index
  that points into it - anchor detection must never consume content. Map non-ASCII, never
  delete. No OCR, no vendor, no cost. Target ~100% retention with a per-document ratchet.
- **SEQUENCING CORRECTED 2026-07-28 - S3b MUST PRECEDE S3a. THE BLOCKER IS NOW CLEARED
  (measured 2026-08-05) - see the status note at the end of this bullet.** The plan below
  originally put re-derivation (S3a) before association (S3b), on the reasoning that
  re-deriving was "mechanical, follows directly from S2". **That was wrong, and the pipeline
  proved it twice.** Regeneration runs the extraction pipeline; the pipeline needs an outline;
  `build_outline_tree` parsed the outline with
  `LINE_RE = ^-\s+([0-9]+[a-z]?|[a-z]):\s*(.*)$` plus a `Header:` prefix - both of which are
  the LEGACY RENDERER'S SYNTHETIC MARKUP that S2 removed. Measured then on the corrected text:
  **outline children = 0** for `schedule_a_2025` (92 lines) and `form_1040_2025` (222
  lines), with zero `Header:` lines present. So nothing could be regenerated until the outline
  could be built from real text.
  **THE ARCHITECTURAL FINDING, and it explains the whole phase:** this pipeline never had an
  independent STRUCTURE layer. The anchor wrapper WAS the structure layer, and
  `render_form.py` was doing double duty - lossy text extraction AND structure annotation in
  one pass. **That is why it discarded 52% of the text: it was optimizing for structure
  annotation at the cost of content.** Removing the wrapper (correct - it was destroying
  content and polluting citations) means the structure step must now exist as a real thing
  for the first time. Building it IS S3b.
  Order is therefore: S2/S2b/S2d (done) -> **S3b structure and association** -> **S3a
  regeneration** -> S4 -> S5.
  **STATUS 2026-08-05 - THE BLOCKER IS CLEARED AND WAS CLEARED FOR SEVERAL ROUNDS BEFORE
  ANYONE RECHECKED IT.** `build_outline_tree` now builds from real text via the geometry-first
  structure model. Measured: `schedule_a_2025` **29 flattened nodes / 28 anchors**,
  `form_1040_2025` **60 / 59**, `form_2441_2025` **40 / 35**. The rounds that cleared it are
  S58 (caption split) through S61 (substantive-continuation tightening). **S3a regeneration is
  UNBLOCKED**; it is specced as round M20-S64.
  **The lesson, recorded because it happened three times on 2026-08-05:** a blocker stated as a
  measurement goes stale silently. The worksheet harvester, rollover seam 5, and this all turned
  out to be already built or already unblocked. **Re-measure a stated blocker before treating it
  as current.**

- **S3 - STRUCTURE AND ASSOCIATION (the hard half).** Caption-to-cell association from
  deterministic geometry first, with explicit ambiguity signals; label joining; column
  separation; option codes and section headers excluded from anchor detection. Report
  association coverage per document as a ratcheted number.
- **S4 - OCR AS SECOND WITNESS.** Integrate OCR strictly as a structure proposal and
  cross-check under 3.3, with the raw JSON persisted and hash-pinned as the acquisition
  artifact (reproducibility comes from the pinned artifact, NOT from the model, which is
  nondeterministic). Decide here whether OCR earns a place at all - S3 may leave little
  residual.
- **S5 - COVERAGE CONTRACT.** Per-document expected-vs-produced for cells, addresses,
  policies, and authority, fail-closed on an unexpected empty (ledger D10), ratcheted in
  CI, with the review-cost numbers from 3.5.

### 4.1 Which rounds satisfied which step (added 2026-08-05)

**This phase runs two numbering systems and nothing mapped them, which is how a cleared blocker
went unnoticed for weeks.** The steps above (S1-S5) are the PHASE structure. The rounds handed to
the Worker are numbered independently (M20-S1 upward, currently past S60). Round narration lives in
`AGENT_HANDOFF.md` and in git history - **not here.** This table is the join.

| phase step | status | rounds that did the work |
| --- | --- | --- |
| S1 measurement harness | complete | `cdb209c`, verified `f1771e0` |
| S2 deterministic text rebuild | complete | S2/S2b/S2d |
| S3b structure and association | **complete 2026-08-05** | S58 captions, S60 packet completeness, S61 substantive-continuation tightening |
| S3a regeneration | **unblocked, specced** | M20-S64 |
| S4 OCR as second witness | **open - may be moot, see below** | none |
| S5 coverage contract | partially delivered | S51 denominator, S63 run summary |

**S4 is now a decision, not a planned step.** The step itself hedged that "S3 may leave little
residual". S3b's geometry work recovers printed tables and captions deterministically - the Form
2441 line 8 band table went from 6 of 16 bands to 16 of 16 with **no OCR involved**. **Before
building S4, measure what OCR would still add.** If the answer is little, the Mistral vendor
exception in Section 6 does not need extending and the question closes.

**Round-level detail does not belong in this file.** A `### M20-S60 packet completeness` section
was appended here and has been removed; that behaviour is described where it belongs, in the
handoff and in the S60/S61 commits.

### 4.2 Findings that constrain any further instruction work (pinned 2026-08-19)

These were measured during S128-S142 and are pinned here because they outlive the rounds that
found them. Round narration stays in git.

**The artifact we segment is the damaged copy.** We pay Mistral OCR to turn a PDF into markdown
while the IRS publishes the same content as structured HTML we already download
(`.cache/raw/2025/*.html`, since 2026-08-14). Every structural defect of six rounds is an artifact
of the OCR path: `# Page N` markers injected at heading level 1, lost em dashes
(`Example 1Basis Reported to the IRS`), and run-in labels arriving as undifferentiated bold -
Schedule B's HTML tags exactly 7 `inlinehd` labels where the OCR emits 23 undifferentiated bold
runs. John's OCR eval measured WORDS (99.0% of Schedule B's OCR words appear in the HTML);
segmentation depends on KINDS of markup, which words cannot carry. **Do not delete the OCR path
yet** - the lookup tables live in the PDF only (`2025 Tax Table` appears 0 times in the HTML
against 13 in the OCR text).

**Mentioning a line and governing a line are anti-correlated in IRS prose.** Measured over all 69
sections the S132 frame owns for `schedule_1a_2025`: every prose section that GOVERNS a line states
its parameter and never names it, and every cell that IS named in prose is named by something that
does not govern it. `Line 10.`'s body reads *"Skip lines 11 and 12 and enter the amount from
Schedule 1-A, line 7 ... on line 13"* - it governs 10 and mentions 7, 11, 12, 13. **A line-reference
miner over body prose would score well and be wrong in every instance.** This is John's
line-24/line-22 objection, measured. Line ownership comes from HEADINGS and from the typed
`owner_lines` frame, never from references in prose.

**Schedule 1-A's ceiling is about 30 of 48, not 48.** Of its 37 unreached cells, 19 have governing
prose that names no line and 18 are arithmetic the IRS writes nothing for (*"Add lines 4c and 5"*) -
the form face IS the instruction. Same ceiling that made Schedule D's 12 of 24 a full score.

**The citation range is load-bearing and `quoted_text` must not be dropped yet.** Perturbing any of
the 511 stored ranges by +/-200 characters rejects 511 of 511; the whole-file search it replaced
passed all of them. But containment does not constrain EXTENT: a range widened 500 characters still
passes for 491 of 511. `docs/source-extents.md` wants to derive the text FROM the range - **do not,
until extent is checked, not just containment**, or an over-wide range silently serves a
neighbouring row.

**The narrowest owner wins.** A line's instruction packet is the span whose `owner_lines` covers
that line and no other; a family span (`Lines 8a Through 8z`) is context, never the primary
citation, and is never dropped.

## 5. Sequencing and risk

M18 widening stays DEFERRED behind this phase (John, 2026-07-28). Widening on top of a
52%-retention text layer would multiply the defect across six more documents.

**The riskiest step is S2**, because it changes `.cache/raw/<year>/*.txt` for all 16 forms,
and that file is what `check_citation_integrity` validates form citations against. Existing
citations were derived from the LOSSY text; some may no longer verify. That is a mandatory
D9 consumer sweep, and citation integrity is the gate that matters. **S2 must be split from
S3** so the content win lands and is verified before the layout work starts.

## 6. Open decisions for John

- **Extending the Mistral OCR vendor exception** (`AGENTS.md`) from instructions and
  publications into the FORM path. Deferred to S4 by design, and S3's result may make it
  unnecessary. Cost is trivial at our scale (56 pages, about $0.06) but unbounded for
  self-serve with arbitrary uploads.
- **Repairing the `mistralai` install** - currently a namespace package with no top-level
  `__init__.py`; only the legacy `mistralai.client` import works. OCR fails CLOSED today.
- **The ASCII standing rule** should say explicitly that it governs AUTHORED files and must
  never be applied to acquired source text. A reasonable implementer read it into
  `errors="ignore"` twice, in two different renderers, and it corrupted real words
  (`aren't -> arent`, `employee's -> employees`).
