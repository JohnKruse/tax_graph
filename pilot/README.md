# Review panel pilot

This standalone pilot projects a real candidate workspace into one self-contained HTML file.
It preserves every printed anchor from the source derivation reports and keeps the three source
layers separate: label, form face, and instruction page.

The operation column reads the promoted candidate graph. It shows the graph operation, the saved
rendered expression, rule ids, and every operand node id with the edge role stored on that edge.
A held-back candidate expression is displayed as evidence, never as a promoted operation.

The flow column follows review notation rule 9. Branching graph trees get a diagram, deeper
non-branching trees get a linear chain, and depth-1 trees explicitly say that no diagram is shown.
Missing promoted operations are red holes with their stored findings.
The pilot also reports graph node ids containing the banned ``floor`` term without changing those
graph artifacts; that vocabulary cleanup belongs to a later pipeline round.

Run it against the M20-S68 candidate workspace:

    .venv\Scripts\python.exe pilot\review_panel.py C:\tmp\m20_s68_candidate --output C:\tmp\m20_s69_review_panel.html

Run the pilot tests:

    .venv\Scripts\python.exe -m pytest pilot\test_review_panel.py -q
