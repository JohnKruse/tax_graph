# Review panel pilot

This standalone pilot projects a real candidate workspace into one self-contained HTML file.

## M20-S92 row diagnosis harness

`row_bench.py` is a read-only diagnosis surface for one or more derivation rows. Replay mode
reads `attempted_payloads` from a real derivation report, renders the prompt through the same
production renderer, applies the payload through the production boundary, and calls the
production validator. It does not call a provider or write project state. Live mode accepts one
row and calls the configured provider through `derive_cells`; it is intended for a deliberate
single-row experiment.

Replay a row or a group of rows:

    .venv\Scripts\python.exe pilot\row_bench.py form_1040_2025 --line 5a --line 5b --run-dir C:\tmp\m20_s91b\run

The output has one screen per row with the exact prompt, each recorded response payload, and its
validation verdict. Rows rejected before a provider call show the prompt as not sent and retain
the source-side error. Live mode requires exactly one line:

    .venv\Scripts\python.exe pilot\row_bench.py form_1040_2025 --mode live --line 5a

This pilot is measurement evidence only. It does not change prompts, validators, graph files, or
review state.

## M20-S113 production replay harness

`replay_harness.py` replays 25 recorded outline-first micro responses without a provider call. Each
case stores the exact prompt in compressed ASCII form and the raw JSON response, then invokes the
production prompt seam, union schema, micro validator, deterministic operand resolver, and
assembler. The fixture covers computation, filer_entry, election, information_return, and
not_derivable outcomes. The output names the first useful layer boundary instead of reducing a
failure to one aggregate count. Expected failures are part of the fixture: they preserve known
diagnostic shapes such as cross-document references, threshold conditionals, band tables, and
Schedule 2 range references.

Run the provider-free replay from the repository root:

    .venv\Scripts\python.exe pilot\replay_harness.py

The harness is a diagnostic witness only. It does not alter prompts, schemas, graph artifacts, or
review state, and `network_calls=0` is part of its summary.

## M20-S103 source-extents pilot

`source_extents.py` is a provider-free, read-only measurement of the acquired source ranges
behind the current form-face evidence spans. It runs the manifest-defined form and worksheet
corpus, classifies every row as one range, multiple ranges, or an unreconstructable row with a
reason, and reports overlaps plus unclaimed source runs. It does not write graph
state or change production code.

Run it with:

    .venv\Scripts\python.exe pilot\source_extents.py --output C:\tmp\m20_s103\source_extents.yaml

## M20-S104 unclaimed-source partition pilot

The same read-only report partitions every S103 unclaimed run into `scaffolding`,
`rule_bearing`, or `undecided`. The partition is deliberately conservative: layout and page
furniture are scaffolding, explicit conditions and operations are rule-bearing, and prose that
needs a judgment the pilot cannot prove remains undecided with an ASCII preview. The report
also includes `unclaimed_rule_bearing_characters_by_document`, including zero-valued entries,
so the storage round can size the text that is currently dropped.

Run it with:

    .venv\Scripts\python.exe pilot\source_extents.py --output C:\tmp\m20_s104\source_extents.yaml

This pilot only measures acquired source. It does not add citation ranges, write graph state,
or change production extraction.

## M20-S119 instruction extent census

`instruction_extent_census.py` is a provider-free, read-only census of every acquired
instruction booklet. It attributes source bytes to the deterministic instruction-section
locators, reports unclaimed spans and overlaps, classifies unclaimed spans from the heading
hierarchy, and joins truncated bodies to the S116 missing-cell and stub-section populations.
It does not repair extents, write graph state, or change extraction.

The checked-in measurement is `plans/m20_s119_instruction_extent_census.yaml`. Regenerate it with:

    .venv\Scripts\python.exe -m pilot.instruction_extent_census

## M20-S123 model-owned instruction segmentation

`model_instruction_segmenter.py` is a provider-pluggable pilot. The model receives only an
acquired instruction-text window. It returns section headings, absolute source byte ranges,
the owning document, and `governs`. It never receives a cell inventory, form outline, address,
or unmatched list. `governs` is tied to the section heading and scope; an incidental body
mention does not transfer ownership.

The deterministic verifier rebinds a heading pointer only to a unique source line boundary within
256 bytes whose normalized text starts with the returned heading. An invented or ambiguous heading
is rejected and disclosed, while the remaining sections still have to tile the complete booklet.
The A/B scorer reads the M20-S116 reconciliation only after that verification and reports gains,
wrong form owners, and correct sibling-worksheet ownership separately for each booklet and
document.

The checked-in live responses are replayable without a provider:

    pilot/fixtures/instruction_segmenter_live_recordings.json

Production calls receive the manifest document ids that may own sections in the booklet, and
the structured-output schema rejects every other `document_id`, including the source booklet
id. Replay keeps the raw owner spellings and reports them as wrong-owner evidence. Live calls
persist the recording after every returned window, before frame verification, so a failed
verification does not discard paid responses.

Run the focused pilot tests with:

    .venv\Scripts\python.exe -m pytest pilot/test_model_instruction_segmenter_m20_s123.py -q

The replayed A/B reports Schedule B's topic-organized sections against the line-organized
Schedule D control. Its gains and owner metrics are evidence from the checked-in live recording,
not a provider-free model-quality claim for a future prompt.

## M20-S124 chapter-scoped booklet windows

The segmenter derives deterministic form-context chapters before it opens model windows. Each
window stays inside one chapter, so a Schedule 2 window cannot ask the model to assign a section
to Schedule 3. A chapter permits its form owner plus every worksheet linked to the booklet; the
worksheet vocabulary is not narrowed to the chapter. Chapter boundaries are converted from the
parser's normalized character offsets into raw source-byte offsets before prompts and recordings
are built. A foreign form claim is rejected locally and recorded as a chapter-owner disagreement;
the byte verifier still checks the surviving sections against the complete booklet.

The focused guards cover the real 1040 booklet and the unchanged one-chapter Schedule B and D
fixtures:

    .venv\Scripts\python.exe -m pytest pilot\test_model_instruction_segmenter_m20_s124.py -q

## M20-S128 containment-owned HTML section frame

`html_section_frame_m20_s128.py` builds a provider-free section frame from the eight acquired IRS
instruction HTML booklets. It reads body `publink` targets and the IRS role heading tree, keeps
`inlinehd` run-in labels as line-bearing leaves, and assigns ownership from the nearest ancestor
that names a document in the manifest owner vocabulary. A foreign owner is rejected locally and
does not abort the booklet. The table of contents is not used as a section index.

Every frame records an opaque `publink` id when present, the ancestor chain, and explicit UTF-8
byte offsets into the acquired HTML. The report keeps `line_anchored`, `topic_attributed`, and
`foreign_owner_rejected` separate. It is a pilot measurement only: it does not call a provider,
fetch a URL, change production extraction, or write graph artifacts.

Run the focused guards from the repository root:

    .venv\Scripts\python.exe -m pytest pilot\test_html_section_frame_m20_s128.py -q

Print the eight-booklet report without writing an artifact:

    .venv\Scripts\python.exe -m pilot.html_section_frame_m20_s128

## M20-S129 full-document HTML frame

`html_document_frame_m20_s129.py` keeps the acquired `div.book` body as one explicit content
region, excluding the IRS site shell and the left-column table of contents. Every role heading
and `inlinehd` run-in label starts a section; accepted and foreign-owner-rejected intervals
together tile the content region. The three checked-in model recordings are compared by
normalized heading text only, because HTML and PDF offsets use different coordinate spaces.

This is a provider-free measurement pilot. It does not fetch, call a model, change production
extraction, or write graph artifacts.

Run the focused guards and report from the repository root:

    .venv\Scripts\python.exe -m pytest pilot\test_html_document_frame_m20_s129.py -q
    .venv\Scripts\python.exe -m pilot.html_document_frame_m20_s129

## M20-S130 observed semantic title expansion

`html_document_frame_m20_s130.py` extends the S129 byte-conserving frame with semantic title
markup observed in the acquired HTML: unhandled `role-*` title classes, `h1` through `h6` title
elements, and `p.title` worksheet/table headings. It keeps the S128 role tree as the ownership
authority, so a nested worksheet title cannot reassign a surrounding form cell. Generic bold and
strong runs are excluded because the source uses them for both headings and prose emphasis.

The report records the eight-booklet structural invariants, the remaining 1040 model-only gap, and
the per-document line-anchored score. Its compact heading comparison is accounting telemetry for
OCR punctuation damage, not a PDF-to-HTML accuracy score.

Run the focused guards and report from the repository root:

    .venv\Scripts\python.exe -m pytest pilot\test_html_document_frame_m20_s130.py -q
    .venv\Scripts\python.exe -m pilot.html_document_frame_m20_s130

## M20-S88 context arms

`context_arms.py` measures the S88 hypothesis without changing the production instruction
sectioner or graph writer. It sends the same printed-anchor denominator through
three context packets:

- Arm A: the current line-owned instruction section.
- Arm B: that section plus a deterministic eight-line buffer in both directions.
- Arm C: a deterministic twelve-line raw-text window around the printed line heading, with no
  section lookup.

All three arms admit every structurally valid row. The report records the historical selector
decision only as comparison telemetry, along with context provenance, model telemetry, returned
quote, and status.
The fixed scoring set is the 32 formulas named in the M20-S88 handoff. Recovery is reported
first, followed by regressions, quote ownership, and cost.

Run the live pilot from a configured local clone with prior reports supplied for regression
comparison:

```text
.venv\Scripts\python.exe pilot\context_arms.py --output C:\tmp\m20_s88 --baseline C:\tmp\m20_s81_run --baseline C:\tmp\m20_s81_rest
```

The output is a measurement artifact only: `m20_s88_context_arms.yaml` is not a draft and is
not eligible for promotion.
It preserves every printed anchor from the source derivation reports. The panel is one full-width
column: the lossless Tree is followed by the same expression flattened as Math. Source layers
remain separate - label, form face, and instruction page - inside each panel's expandable evidence
block.

All pilot consumers read cell evidence through `pilot/cell_access.py`.  Its `CellText` result uses
`None` for absent text, so an absent caption cannot fall through to a different source record.
The panel summary reports caption, instruction-row, and promoted-operation presence and absence
counts. Candidate instruction coverage is also reported across all candidate rows, with a
per-document split. A skipped derivation still keeps its candidate text evidence visible; its
operation remains a hole.

The Tree reads the promoted candidate graph and retains edge roles that are not already determined
by an operation and operand position.  Math is generated from the same tree, not from a second
parser.  The stored graph remains unchanged: implied roles are suppressed only at this human
printing boundary.  A collapsed graph-trace block keeps rule ids, operand node ids, and the
held-back candidate expression available as evidence; a held-back expression is never presented
as a promoted operation.

Missing promoted operations are visible holes with their stored primary reasons. In the current
S89 contract, a structurally valid row reaches derivation even without a formula cue; when the
model returns ``REQUIRE_INPUT``, the panel presents ``model_stated_input`` as an outcome rather
than a hole. Structural and derivation reasons remain actionable. The graph stays unchanged;
role suppression happens only at this human-facing printing boundary. Older pre-S89 candidate
artifacts may still contain the retired selector reason; the panel preserves that exact reason but
labels it ``historical_selector`` and asks for regeneration rather than calling it a current input.

The summary's instruction count is the number of printed-anchor panels whose instruction value is
present through ``cell_access.instruction_section``. Candidate coverage uses the same accessor on
all candidate rows, including rows skipped before operation derivation. It is not a count of
unique instruction locators: the reviewer needs one answer for whether each row has joined text.
The pilot also reports graph node ids containing the banned ``floor`` term without changing those
graph artifacts; that vocabulary cleanup belongs to a later pipeline round.

The panel can rank operation rows with ``--top N``. Ranking is deterministic: operation count is
the primary key and operand count breaks ties. The full corpus counts remain in the summary so a
focused page cannot imply that it contains the whole denominator.

## M20-S75 instruction parser pilot

`instruction_parser.py` measures three separate source views over the seven cached instruction
documents: the current OCR parser, the pilot OCR parser with bold-heading and printed-line repairs,
and the acquired HTML parser. Each section keeps its source provenance and source text. The HTML
view is a witness for printed-line identity; it is not a fallback for missing OCR text.

Run the corpus measurement from the repository root:

    .venv\Scripts\python.exe -m pilot.instruction_parser --raw-root .cache\raw\2025 --output .test_tmp2\m20_s75_instruction_parser.json

The real 2025 corpus measured as follows:

    instructions_form_1040_2025: OCR today 154, OCR with fixes 143, HTML 143
    instructions_form_2441_2025: OCR today 16, OCR with fixes 16, HTML 16
    instructions_form_6251_2025: OCR today 30, OCR with fixes 33, HTML 33
    instructions_form_8949_2025: OCR today 2, OCR with fixes 2, HTML 2
    instructions_schedule_a_2025: OCR today 19, OCR with fixes 19, HTML 19
    instructions_schedule_b_2025: OCR today 0, OCR with fixes 0, HTML 0
    instructions_schedule_d_2025: OCR today 6, OCR with fixes 6, HTML 6

For Form 6251, the current OCR phantom anchors are `3o`, `4a`, `5e`, `8a`, and `11a`; the pilot
reports zero repaired phantoms. Bold-only headings recover lines 2d, 2f, and 2g, and the OCR glyph
confusion in `2IPost-1986 Depreciation` is rebound to printed line 2l using the HTML line witness.
Schedule B remains empty in both sources, but the report records that absence as a finding rather
than treating it as silent success.

Run the pilot parser tests with:

    $env:PYTEST_DEBUG_TEMPROOT='C:\Users\devbox\projects\tax_graph\.test_tmp2'; .venv\Scripts\python.exe -m pytest pilot\test_instruction_parser.py -q

Run it against the M20-S71 candidate workspace:

    .venv\Scripts\python.exe pilot\review_panel.py C:\path\to\cand_s71 --output C:\tmp\m20_s82_review_panel.html

Run the pilot tests:

    .venv\Scripts\python.exe -m pytest pilot\test_review_panel.py -q

## M20-S80 rendering comparison

`render_options.py` renders the same five graph-backed cells five ways: a flow SVG for true
branches, a lookup table for a root lookup, an operation chain for dependent arithmetic, an
IRS-style worksheet, named math equations, registry-worded English, and the current role-labelled
tree. Branch diagrams keep each operation in its own node, show lookup tables as nodes, split the
arms horizontally, and rejoin them at the result. The fixed cells span a branch, the sixteen-band
table, nested arithmetic, one subtraction, and an unresolved operation. Every cell has a non-empty
review surface; an unavailable operation carries its actionable finding reason, never a raw error
or payload dump.

The comparison also runs every renderer against every printed anchor before it writes the page.
Its summary reports produced/attempted counts, failures, empty/placeholder counts, median/max
size, and the declared width and height of every SVG. It also checks that no two connectors share
a start point and direction and that no edge label falls inside another node's box. Flow SVGs are
constrained to a 320-unit column width and grow vertically. Run it against a candidate workspace
with:

    .venv\Scripts\python.exe pilot\render_options.py C:\path\to\candidate --output C:\tmp\m20_s80_renderings.html

The flow SVG and lookup-table cells have a small-card preview trigger. Clicking or pressing Enter
or Space opens the same generated content in an inline dialog at its declared size; the dialog
scrolls vertically for tall diagrams and horizontally for wide tables. Click the backdrop, use
the Close button, or press Escape to return to the comparison. The page has no external scripts,
fonts, or stylesheets, so this interaction works from `file://`.

The page is a projection only. It does not call a provider or write graph artifacts.

## Retired M20-S82/M20-S83 positional panel

These two pilot surfaces are archived at the annotated tag ``archive/m20-flow-column``. The main
panel no longer contains their positional projection or geometry metrics.

## M20-S83 tidy-tree geometry and role printing (retired)

S83's measured geometry and role-printing work is preserved in the archive tag. It proved the
Tree's role suppression invariant before the positional surface was retired.

## M20-S84 full-width Tree and Math panel

The Tree is the sole graphic projection. Math remains directly beneath it, both at full width.
Operation headers are left justified, child indentation is 32px per level, and no arrow glyph is
inserted before a child. The panel keeps every graph edge role in data and prints only roles that
are not already determined by operation and operand position.

Holes retain their stored reason. The archived pre-S89 cand_s71 corpus reports 83
``selector_no_formula_cue`` rows, 7 structural rows, and 2 derivation gaps across 157 anchors.
The CLI reports the operation distribution (51 one-operation rows, 12 two-operation rows, and 2
six-operation rows) and accepts ``--top N`` to render only the ranked operation rows while keeping
the full corpus totals in the summary.

Run it against a candidate workspace as:

    .venv\Scripts\python.exe pilot\review_panel.py C:\path\to\candidate --output C:\tmp\m20_s84\review_panel.html
    .venv\Scripts\python.exe pilot\review_panel.py C:\path\to\candidate --output C:\tmp\m20_s84\top25.html --top 25

## M20-S158 fixed-span instruction attribution

`attribution_m20_s158.py` labels already byte-verified HTML instruction spans with
zero or more tokens from a deterministic printed-line inventory. It does not
choose span boundaries, mine line references from body prose, or write graph or
draft state. Empty `governs` is a first-class answer and the report exposes its
rate, zero-instruction cells before and after, and the Schedule 1-A denominator
with its arithmetic ceiling excluded.

The permitted two-document live measurement writes outside the repository:

    .venv\Scripts\python.exe -m pilot.attribution_m20_s158 --output C:\tmp\m20_s158\attribution.json --document schedule_1a_2025 --document form_1116_2025
