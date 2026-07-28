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

## 7. Reproducibility gap - closed by M20-S1

M20-S1 committed the measurement harness at `tax_graph/acquire/measure_form.py` and the
module-form command `python -m tax_graph.cli measure-extraction`. The command writes the
machine-readable and human-readable snapshots under `plans/m20_s1_measurements/` and never
writes beside the source PDFs. The committed snapshot reproduces the 52.2% mean and the
17.0%, 52.0%, and 85.7% headline form figures. The separate producer corpus is pinned by
hash under `tests/fixtures/m20_producer_corpus/`; it is test data only and is not in the
acquisition manifest or graph.
