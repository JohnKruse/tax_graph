# Schedule 1 (Form 1040) - Additional Income and Adjustments to Income Verification Record (schedule_1_2025)

This page is generated from committed repository data by `tax_graph.verify.record`.

## Summary

- Document id: `schedule_1_2025`
- Document type: `schedule`
- Status: `partial`
- Verification tier: independently witnessed
- Gate: project
- Artifact content hash: `cc75ade7dabef4267548b2459822c3aa03dbb42a537715951b9b4b0ea33b00a5`
- Source URL: https://www.irs.gov/pub/irs-prior/f1040s1--2025.pdf

## Modeled

- citations: 31
- documents: 1
- edges: 27
- nodes: 32
- rules: 2

## Explicit Gaps

- Student Loan Interest Deduction Worksheet line 21: OTS S1_21 is pre-worksheet interest paid, while the graph line is the post-worksheet deduction; model the worksheet before live differential injection.

## Witnesses

- Oracle differential: 100 agreed scenario(s) via OpenTaxSolver `ots_2025_23.06`.
- IRS worked examples: No committed IRS worked-example fixture covers this document.
- N-version corroboration: No committed N-version corroboration artifact for this document.
- Property tests: No committed per-form property-test artifact for this document.
- Calibration audit: sample 0, escapes 0, human minutes not yet recorded.
- Triage outcomes: No committed triage entries for this document.
