# M20 - Form text extraction: measurement and OCR experiment

> Findings report, 2026-07-28. Architect (Claude Opus 5), at John's direction.
> Read-only measurement; no artifact was changed by any of this work.
> Master plan: `../docs/engineering-plan.md`. Related: `../docs/extraction-verification.md`.

**Why this exists.** John, 2026-07-28: "I keep having the feeling that our pipeline is
really shoddy and you just keep manually putting gaffer's tape on it." He was right, and
this is the measurement that shows where. Everything below is reproducible from the
acquired PDFs already on disk; nothing required re-fetching.

## 1. The defect: we discard most of every form's text

`tax_graph/acquire/render_form.py` renders a form PDF to `.cache/raw/<year>/<id>.txt`.
That file is the source of truth `check_citation_integrity` validates form citations
against, and it is a lossy derivation of the PDF.

**Root cause, `_rows_from_words` (render_form.py:96-115).** Words are grouped into visual
rows, then per row:

1. `_anchor_index` scans the FIRST FOUR tokens for a line anchor, regex
   `^(?:[1-9][0-9]?[a-z]?|[a-z])$` - any bare single letter, or 1-2 digits with an
   optional letter.
2. On a match it emits `- {anchor}: {tokens AFTER it}`. **Every token before the anchor is
   discarded.**
3. With no match the ENTIRE ROW is dropped, unless `_header_row` matches its narrow
   whitelist (`column`, `(a)`, `part `, `schedule d`).

Two independent loss mechanisms, both deterministic. A third defect follows from the
regex: `box 5` matches the anchor pattern, so text about **box** 5 is filed under **line**
5 - silent misattribution, not just loss.

**Worked example (Schedule 1-A line 4).** Source: "If you received tips as an employee
with respect to employment with more than one employer, enter -0- on lines 4a and 4b and
see the instructions..." Stored: "If you received tips as an employee with `- 4b:` and see
the instructions...". The operative condition is deleted, not truncated.

**Consequence.** Our verbatim gate for form citations checks quotes against a text missing
much of the form, so only surviving fragments are citable. This is the upstream source of
the `- <token>:` wrapper pollution M18-S2b cleaned out of citation records, and of the
M16-S2 `z -> 1z` anchor-split family. **We have been repeatedly fixing symptoms of this
one defect at the citation layer instead of fixing the extractor.**

## 2. Measured retention, 16 forms

Word-multiset recall against the PDF's own text layer (PyMuPDF `get_text`), which is
complete and deterministic. Arm A is what we ship; arm B is deterministic
`page.find_tables()`; arm C is Mistral OCR (`mistral-ocr-latest`).

| arm | mean recall | range |
| --- | --- | --- |
| A - `render_form.py` (shipped) | **52.2%** | 17.0% - 85.7% |
| B - `find_tables()` deterministic | **67.9%** | 24.0% - 96.7% |
| C - Mistral OCR | **99.4%** | 97.3% - 100% |

Worst arm-A cases: `form_13614_c` 17.0%, `form_1099_div` 24.3%, `form_1099b` 26.2%,
`form_1099_int` 31.7%, `form_w2` 32.8%, `form_1040` **52.0%**. The ranking tracks prose
density exactly - 13614-C is an intake questionnaire (mostly anchorless prose), Schedule 3
is a compact numbered table (85.7%).

All 7 instruction PDFs retain ~100%, because they do not go through `render_form.py`. A
corpus-wide average is therefore misleading: the instruction files are large and mask the
form loss.

## 3. Robustness across authoring tools - NOT established

**All 16 forms report producer `Designer 6.5` (Adobe LiveCycle).** Our corpus is a sample
of ONE authoring tool, so no claim about robustness across tools is supported by it.
John's concern is not answered by this data.

What the data DOES show, from the instruction PDFs' different producer
(`Antenna House`): `find_tables()` returns **zero tables** on 2 of those 7. Same library,
same code, different producer, structure detection silently degrades to nothing.
**Table detection is producer-sensitive and must not be load-bearing for correctness.**

Layer-by-layer confidence:

| layer | mechanism | confidence | evidence |
| --- | --- | --- | --- |
| Text | `get_text()` content stream | High, tool-independent | 23/23 documents yield text; 0 need OCR |
| Widgets + geometry | AcroForm, a PDF spec structure | High | 16/16 forms enumerate (33-297 widgets) |
| Table structure | `find_tables()` heuristics | **Low, producer-sensitive** | 0 tables on 2 Antenna House PDFs |

Caveat: `Designer 6.5` typically emits XFA, read here through PyMuPDF's AcroForm
compatibility layer. 16/16 worked, but that is another untested single-tool assumption. A
state return, a pre-2000 form, or a flattened non-fillable PDF is the real test and we do
not have one in the corpus.

## 4. The OCR experiment

Method: ground truth is the PDF text layer. Two metrics, word-multiset based so reflow
does not skew them - **recall** (fraction of ground truth preserved) and **fabrication**
(fraction of arm words absent from ground truth). Fabrication is the safety metric,
because citations are verbatim-from-source and the M14 fabricated-citations reopen is the
precedent.

**Result: 99.4% recall at 0.2% fabrication.** Every fabricated token was inspected rather
than trusted as a percentage:

- `img` / `jpeg` / `0`, 8x each - markdown image syntax `![img-0.jpeg]`, not content. This
  accounts for **all 8** apparently-numeric fabrications.
- `nonqualified`, `includable` - **dehyphenation gains**; OCR rejoined words the PDF split
  across lines.
- `14a`, `36a`, `8f`, `7a`, `1a`, `2c` - line labels OCR recovered that the text layer
  renders differently.

**Zero invented dollar amounts. Zero invented tax figures.**

### The API returns far more than markdown

The default call populates `blocks` and `confidence_scores` as `null`. Passing the
parameters explicitly (verified on `schedule_1a_2025`) returns:

- **21 blocks** with bounding boxes AND semantic type (`title`, `text`, `table`, `footer`)
- **confidence scores**: page average 0.9957, page **minimum 0.5147**, plus per-word
- **HTML tables** (`table_format="html"`), which carry the object model directly:
  `<td><b>4</b></td><td>{operative prose}</td><td><b>4a</b></td>` - that is
  line token -> prose -> cell reference, machine-readable
- **header/footer extracted separately**, partitioning off `Cat. No.` boilerplate

The page-minimum confidence is the fail-closed hook: a low-confidence region becomes a
named finding instead of silent noise.

## 5. Defects found in the existing OCR path (not yet fixed)

1. **`_ascii_normalize` uses `errors="ignore"`** (`render_ocr.py`), silently DELETING every
   non-ASCII character - checkbox glyphs, curly quotes, dashes. This is on the instructions
   path already in production use.
2. **`render_pdf` narrows the response** to `page.markdown` + `links`, discarding
   dimensions, images, blocks, tables, confidence, header/footer.
3. **Output-path hazard:** `render_instructions_ocr` writes `<document_id>.txt` into its
   output dir. Pointed at `.cache/raw/<year>/`, it would OVERWRITE the form text that
   citation integrity checks against.
4. **The `mistralai` install is broken in this venv** - a namespace package with no
   top-level `__init__.py` (1133 files, only `azure/`, `client/`, `extra/`, `gcp/`). The
   documented `from mistralai import Mistral` fails; only the legacy
   `from mistralai.client import Mistral` fallback works. `render_ocr.py` happens to catch
   this, so OCR fails CLOSED (`RendererUnavailable`) rather than wrong.

## 6. Recommendation

**Rebuild form text acquisition before widening M18 or building the coverage contract.**
The 52% -> 99% gap dominates everything downstream: authority coverage, printed labels, the
394 `legacy_mined` display names, and the ~605 unsupported cells.

Architecture - the same shape M18 already established for instruction HTML (persist the
acquisition artifact, derive deterministically from it):

1. **Deterministic text layer stays the ground truth.** Complete, free, reproducible, and
   what `check_citation_integrity` keeps validating against. The verbatim invariant is
   non-negotiable.
2. **OCR is a STRUCTURE proposal, never an unverified content source.** Persist the full
   raw JSON as the acquisition artifact and hash-pin it. **Reproducibility comes from
   caching the artifact, not from OCR being deterministic - it is not.** A promoted
   artifact must be re-derivable from committed state.
3. **Verify mechanically, three ways:** every OCR word checked against the deterministic
   text layer (the fabrication metric above, which runs corpus-wide in seconds); block
   bboxes cross-checked against the widget geometry we already trust; and confidence
   thresholds gating promotion.
4. **Retention gate in CI**: per document, stored content vs PDF text content, ratcheted,
   so this class of loss cannot silently return. This is the first concrete metric of the
   per-document coverage contract.

Sequence: form extraction rebuild -> coverage contract -> two-tier authority (form caption
primary, instructions supplementary) -> M18 widening last.

**Open decisions for John.**
- Extending the Mistral OCR vendor exception (`AGENTS.md`) from instructions/publications
  into the core FORM path. Cost is trivial here (56 pages, about $0.06) but unbounded for
  self-serve with arbitrary uploads.
- Whether to repair the `mistralai` install (an environment change) before depending on it.
- Whether to acquire 2-3 forms from other agencies/eras to actually test producer
  robustness - the cheapest way to convert section 3's caveat from argument to measurement.

## 6b. Blind agreement experiment on 10 UNSEEN forms (2026-07-28), John-adjudicated

Ten IRS forms never previously touched (Schedules C/E/SE/8812, Forms 8863/8962/5695/8889/
4137/8606) were extracted deterministically and by OCR, and every disagreement was put to
John for visual check against the printed form. **This is the first time the pipeline's
output was adjudicated by a human against source.**

Token-multiset agreement (order-independent, so OCR's table restructuring does not skew it):
nine forms at **98.7% - 100%**, mean **99.6%**. One outlier: **schedule_e at 76.8%**.

**JOHN'S VERDICTS.**

1. **Label splits - OCR IS RIGHT (confirmed visually).** On 7 of 10 forms the deterministic
   path reads the printed label as two tokens (`"17"` + `"a"`) because the PDF draws them as
   separate positioned runs; OCR reads `17a`. John: "There's no way that I'd view these as
   split from my visual read." Affected: 5695 `17a/21a/23a/24a`, 8606 `15a/25a`,
   8889 `14a/17a`, 8962 `8a`, schedule_c `27a`, schedule_se `1a/4a/5a/8a`.
   **S2 needs a label-joining rule.** Same family as the M16-S2 `z -> 1z` fix.
   **John's follow-up:** "if there is an a, there is a b and so it would kinda go against our
   breakout scheme." Resolution: these are different layers and do not conflict. `17a` is the
   PRINTED LABEL (what a human quotes, what goes in `official_ref`); the a/b sub-items are
   STRUCTURE carried by the address tree's parent/child. Consistent with the standing rule
   that line numbers are PLACEMENT, not identity - it would only break if `"17a"` were ever
   used as an identity key, which that rule already forbids.
2. **CORRECTED 2026-07-28 (see section 6c) - most of this was TRANSIENT.** The claim below
   stands only for line 4; the other eleven drops recovered on rerun. Left in place because
   the correction matters more than the original claim.
   **schedule_e page 1 is a REAL OCR FAILURE - confirmed.** OCR read **289 of 570 words**;
   page 2 was perfect (642 = 642). John verified against the printed form that OCR silently
   dropped real line labels and cross-references: line 4 `Royalties received`, `1a Physical
   address of each property` (with A/B/C sublines), line 21 (`file Form 6198`), line 22
   (`on Form 8582`), and `23a` through `23e`. **OCR cannot be trusted as a sole source.**
3. **Non-issue:** form_4137 `CAUTION` is a GIF icon (triangle/exclamation) with a caption -
   "not really germane".

**TWO DEFECTS IN THE ARCHITECT'S OWN LOCALIZATION PROBE (John caught both).**

- **Section headers inherit the preceding line's anchor.** The probe reported form_8606
  text as "line 15c"; it is actually the **Part II subheader** ("Complete this part if you
  converted part or all of your traditional IRAs to a Roth IRA in 2025").
- **Option codes are misread as line anchors.** The probe reported schedule_e "line 2"; that
  is the **Type of Property list** (codes 1-8 - Single Family Residence, Multi-Family, ...),
  not a line number.

Both are the SAME family as `render_form.py` reading `box 5` as line 5 (section 1). The
Architect reproduced the defect it is proposing to fix, inside the tool built to measure it.
**S2 HARD REQUIREMENT: anchor detection must distinguish printed line numbers from option
codes and column letters, and a section/Part header must never inherit a preceding line's
anchor.**

**MEASUREMENT ARTIFACT (not an extraction defect).** `x $1,000` on 5695 line 10 splits into
`$1` + `000` because the harness token regex `[a-z0-9$%]+` breaks on the comma. Currency
amounts therefore inflate disagreement counts corpus-wide. **The S1 harness tokenizer must
be fixed before its disagreement counts are trusted**; the retention percentages, which are
dominated by prose, are not materially affected.

**WHAT THE EXPERIMENT SETTLES.** Every disagreement investigated turned out to be a real
defect on one side or the other (excepting the icon and the tokenizer artifact). Neither
extractor is sufficient alone: deterministic is right on CONTENT and wrong on STRUCTURE
(column conflation - 34 rows where a y-grouped row glues two form columns, e.g. schedule_c
`Advertising ... Office expense`; plus the label splits); OCR is right on STRUCTURE and
demonstrably drops CONTENT (schedule_e p1). **The two-witness cross-check is therefore the
verification mechanism, not a fallback** - it surfaced roughly 20 real issues across 10
unseen forms, and a human confirmed them in minutes. That is the coverage contract working.

## 6c. THREE CORRECTIONS after rerunning Schedule E (2026-07-28)

John: "can u run sched E thru the OCR again? i am wondering if there was a hiccup... i'd be
inclined to run the OCR thrice per doc and then vote." He was right to ask, and the reruns
overturn part of section 6b.

**Correction 1 - eleven of the twelve schedule_e drops were TRANSIENT.** Three fresh runs
recovered lines 20, 21, 22, 23a-e, 24, 25, and 26. The original call was an outlier at 289
words against a stable ~480. The Architect built an argument on a single flaky run and
should have rerun before reporting it.

**Correction 2 - OCR IS NONDETERMINISTIC.** Four runs produced three distinct outputs
(original 5,544 chars; run1 and run2 byte-identical at 8,721; run3 at 8,844). Any promoted
artifact derived from OCR must therefore be reproducible from a HASH-PINNED stored
response, never from re-calling the model. This mirrors the M18 stored-HTML pattern.

**Correction 3 - line 4 is a STABLE blind spot, and CONFIDENCE CANNOT SEE IT.**
`Royalties received` was dropped in **all four runs**; John independently reproduced it in
Mistral Studio, observing that it parses the income lines as a list and draws a box around
lines 3 and 4 while emitting only 3. The rich-parameter call confirms it exactly: the block
is correctly DETECTED (`type=list`, bbox `(43,440)-(741,469)`, about two rows tall) but its
transcribed content holds only line 3. Page confidence was avg **0.9921** / min **0.4915**,
and every low-confidence token was a dot leader or a newline - **nothing near line 4,
because a dropped row emits no tokens to be unconfident about.**

**Consequences for the design (now in `PHASE_M20.md`):**
- **Voting fixes VARIANCE, not BIAS.** N runs recover the eleven transient drops and never
  recover line 4 - and three agreeing runs would raise FALSE confidence in an output
  missing an income line.
- **OCR confidence scores are not a usable gate for omissions.** The Architect had proposed
  them as the fail-closed hook; that proposal is dead.
- What does catch line 4: content accountability against the deterministic text, and a
  line-number contiguity check (`3 -> 5` is a gap) which needs no second source at all.
- Cross-run word-count variance IS a usable signal (289 vs ~480 would trip immediately).

## 7. Reproducibility gap - closed by M20-S1

M20-S1 committed the measurement harness at `tax_graph/acquire/measure_form.py` and the
module-form command `python -m tax_graph.cli measure-extraction`. The command writes the
machine-readable and human-readable snapshots under `plans/m20_s1_measurements/` and never
writes beside the source PDFs. The committed snapshot reproduces the 52.2% mean and the
17.0%, 52.0%, and 85.7% headline form figures. The separate producer corpus is pinned by
hash under `tests/fixtures/m20_producer_corpus/`; it is test data only and is not in the
acquisition manifest or graph.
