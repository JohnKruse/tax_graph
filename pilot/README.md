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
