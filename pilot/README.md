# Review panel pilot

This standalone pilot projects a real candidate workspace into one self-contained HTML file.
It preserves every printed anchor from the source derivation reports and keeps the three source
layers separate: label, form face, and instruction page.

All pilot consumers read cell evidence through `pilot/cell_access.py`.  Its `CellText` result uses
`None` for absent text, so an absent caption cannot fall through to a different source record.
The panel summary reports caption, instruction-row, and promoted-operation presence and absence
counts. Candidate instruction coverage is also reported across all candidate rows, with a
per-document split. A skipped derivation still keeps its candidate text evidence visible; its
operation remains a hole.

The operation column reads the promoted candidate graph. It shows the graph operation, the saved
rendered expression, rule ids, and every operand node id with the edge role stored on that edge.
A held-back candidate expression is displayed as evidence, never as a promoted operation.

The flow column follows review notation rule 9. Branching graph trees get a diagram, deeper
non-branching trees get a linear chain, and depth-1 trees explicitly say that no diagram is shown.
Nested printed-line references stop at ``line X`` so the panel does not re-narrate the form. A
repeated operation subtree is rendered once and then referenced. Missing promoted operations are
red holes with their stored findings. Flow output contains no graph node ids.

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

    .venv\Scripts\python.exe pilot\review_panel.py C:\path\to\cand_s71 --output C:\tmp\m20_s73_review_panel.html

Run the pilot tests:

    .venv\Scripts\python.exe -m pytest pilot\test_review_panel.py -q
