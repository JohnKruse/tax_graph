# Construction measurement pilot

This standalone pilot measures construction patterns in a candidate graph
workspace. It is intentionally outside the production pipeline.

The denominator is every printed anchor in each source derivation report. A
construction record contains its anchor count, real candidate anchor ids,
matched source phrases, and the outcome cross-tab. The comparator section
counts anchors whose text uses inclusive or exclusive comparison language;
this is an expressivity-gap measurement, not a derivation success rate.

Vocabulary is collected from all printed-anchor text. The pilot does not
compare terms with an authored operation list, so a phrase that appears in the
IRS corpus remains visible even when no named construction recognizes it.

Run it directly after producing a candidate workspace:

    .venv\Scripts\python.exe pilot\constructions\measure.py C:\tmp\candidate

The default report is `constructions.yaml` beside the candidate. Use
`--output` to choose another report path.
