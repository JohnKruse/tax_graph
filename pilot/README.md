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

Run it against the M20-S71 candidate workspace:

    .venv\Scripts\python.exe pilot\review_panel.py C:\path\to\cand_s71 --output C:\tmp\m20_s73_review_panel.html

Run the pilot tests:

    .venv\Scripts\python.exe -m pytest pilot\test_review_panel.py -q
