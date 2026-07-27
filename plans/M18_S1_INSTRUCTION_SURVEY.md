# M18-S1 Instruction Survey - 1040 HTML Canary

Status: read-only survey. No citation records, graph objects, promoted artifacts, or
field-map records were changed.

## Source and acquisition

- Document: `instructions_form_1040_2025`
- Instruction URL: `https://www.irs.gov/instructions/i1040gi`
- Stored source: `.cache/raw/2025/instructions_form_1040_2025.html`
- Stored content hash: `0a1a74db99d1f481b49c6d59a928dbfc16f10c640e1dd502c72f3ac816e21ec7`
- Retrieved date: `2026-07-27`
- The same sequential acquisition fetched six manifest-declared instruction HTML pages:
  1040, 6251, 8949, Schedule A, Schedule B, and Schedule D.
- Stored HTML is ASCII-normalized at acquisition. Later parsing reads the stored file,
  never a live URL.

## Heading tree

The parser sees 442 headings in the stored HTML. This includes IRS site navigation before
the publication body. The publication body begins at `1040 (2025)`.

Heading counts by level:

| Level | Count |
|---|---:|
| h1 | 4 |
| h2 | 31 |
| h3 | 88 |
| h4 | 219 |
| h5 | 76 |
| h6 | 24 |

Representative publication tree, with the stable source anchor where present:

```text
- 1040 (2025) [en_US_2025_publink1000274480]
  - 1040 - Introductory Material [no-id]
    - Income [no-id]
      - Line 1a [id107]
        - Total Amount From Form(s) W-2, Box 1 [id107 content span]
      - Line 1b [id111]
        - Household Employee Wages Not Reported on Form(s) W-2 [id111 content span]
    - Instructions for Schedule 1 Additional Income and Adjustments to Income [no-id]
      - Additional Income [no-id]
        - Line 1 [no-id]
    - Instructions for Schedule 1-A Additional Deductions [en_US_2025_publink100079560]
    - Instructions for Schedule 2 Additional Taxes [id552]
      - Specific Instructions [en_US_2025_publink10001910]
        - Lines 1a Through 1z [en_US_2025_publink10002576]
    - Instructions for Schedule 3 Additional Credits and Payments [en_US_2025_publink1000132179]
```

The parser found 143 headings that name at least one printed line. Of those, 86 have a
semantic title from the heading itself or the adjacent semantic child heading. 128 have a
stable anchor captured from the source anchor immediately before the heading; 15 line
headings have no captured anchor and are a finding for the miner. Examples include bare
`Line 1c`, `Line 2a`, and `Line 19c`.

The HTML tree cleanly separates the return-document instruction roots for Schedules 1,
1-A, 2, and 3. The source-document shallow/deep split was not evaluated here because
source-document instruction URLs are not in the S1 canary manifest scope. Form 13614-C
remains intentionally skipped.

## Per-line coverage

Printed lines come from the promoted canonical-address registries. Candidate sections are
line-naming headings below the matching schedule root. A range heading contributes each
endpoint token only; expanding every intermediate token belongs to the miner step.

| Document | Printed lines | Candidate sections | Titled sections | Lines named | Missing printed lines |
|---|---:|---:|---:|---:|---|
| Schedule 1 | 63 | 58 | 18 | 55 | 1a, 5, 6, 8g, 9, 10, 25, 26 |
| Schedule 1-A | 46 | 0 | 0 | 0 | all 46 printed lines |
| Schedule 2 | 42 | 16 | 15 | 18 | 1, 1b-1f, 1y, 7, 17b-17q, 20, 23b |
| Schedule 3 | 31 | 15 | 11 | 16 | 5a, 5b, 6b-6m, 8, 15 |

Schedule 1-A is a deliberate fail-closed finding: `i1040gi` has a schedule-level root
and part-level headings, but no line-naming headings for its 46 printed lines. The
acquisition channel succeeds; line coverage does not yet.

## HTML versus PDF cross-check

A simple token scan of the existing 1040 per-page Markdown found 103 unique line tokens in
Markdown headings. The HTML line-heading scan found 118 unique tokens. The PDF scan had no
tokens absent from HTML; HTML-only tokens were:

`17z`, `19b`, `1z`, `24f`, `24g`, `24h`, `24i`, `24j`, `24k`, `24z`, `27a`, `4b`, `5b`,
`6b`, `6z`.

This is a finding, not a silent preference for HTML. The PDF extraction groups ranges and
uses a different heading convention, so the comparison must be resolved by S2 parsing and
S3 citation cross-check before any instruction text is promoted.

## Work list for S2

1. Filter site-navigation headings from the publication body using the publication root.
2. Preserve the preceding source anchor for every content heading, including headings with
   no HTML `id` attribute of their own.
3. Expand range headings into their named line tokens and keep the original range text.
4. Add a fail-closed finding for Schedule 1-A's absence of line-naming headings.
5. Keep the HTML/PDF disagreement set as a cross-check input; do not synthesize citations.
