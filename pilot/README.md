# Review panel pilot

This standalone pilot projects a real candidate workspace into one self-contained HTML file.
It preserves every printed anchor from the source derivation reports.  The panel has two columns:
the lossless role-labelled Tree with the same expression flattened as Math on the left, and a
vertical Flow on the right.  Source layers remain separate - label, form face, and instruction
page - inside each panel's expandable evidence block.

All pilot consumers read cell evidence through `pilot/cell_access.py`.  Its `CellText` result uses
`None` for absent text, so an absent caption cannot fall through to a different source record.
The panel summary reports caption, instruction-row, and promoted-operation presence and absence
counts. Candidate instruction coverage is also reported across all candidate rows, with a
per-document split. A skipped derivation still keeps its candidate text evidence visible; its
operation remains a hole.

The Tree reads the promoted candidate graph and retains the edge roles.  Math is generated from
the same tree, not from a second parser.  A collapsed graph-trace block keeps rule ids, operand
node ids, and the held-back candidate expression available as evidence; a held-back expression
is never presented as a promoted operation.

The Flow follows review notation rule 11. Values enter from the top, the result leaves from the
bottom, and moderators enter through one right-hand gutter. Every moderator arrow carries its
stored edge role as text; colour only reinforces that label. Lookup tables absorb their key and
variants as rows. Missing promoted operations are red holes with their stored findings. Flow
output contains no graph node ids.

The summary's instruction count is the number of printed-anchor panels whose instruction value is
present through ``cell_access.instruction_section``. Candidate coverage uses the same accessor on
all candidate rows, including rows skipped before operation derivation. It is not a count of
unique instruction locators: the reviewer needs one answer for whether each row has joined text.
The pilot also reports graph node ids containing the banned ``floor`` term without changing those
graph artifacts; that vocabulary cleanup belongs to a later pipeline round.

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

## M20-S82 two-column positional panel

The review panel is now the selected Rule 11 surface: expandable IRS source evidence, Tree and
Math in the left third, and a vertical Flow in the right two thirds.  Flow positions are semantic:
values enter from the top, results leave from the bottom, and threshold, key, default, multiplier,
and subtrahend moderators enter through one right-hand gutter.  Moderator arrows always carry the
stored edge role as visible text, so the page remains understandable in grayscale.  The generated
panel summary reports every flow SVG's declared width and height, connector and label geometry
checks, and the count of moderator arrows without labels.

Run it against a candidate workspace with:

    .venv\Scripts\python.exe pilot\review_panel.py C:\path\to\candidate --output C:\tmp\m20_s82_review_panel.html

The S82 pilot uses the candidate workspace as input only.  It does not call a provider or write
graph artifacts.
