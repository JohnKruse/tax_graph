# Graph - tax year 2025

Authored graph objects (YAML), validated against `../../schemas/` and compiled to
SQLite by the build step.

## Layout

| Dir | Contents | File shape |
|---|---|---|
| `documents/` | one document per file | a single object |
| `nodes/` | nodes grouped by branch | a list of objects |
| `edges/` | edges grouped by branch | a list |
| `rules/` | reusable rules | a list |
| `citations/` | citation objects grouped by branch | a list |
| `decisions/` | decision (elicitation) nodes | a list |

## What's here (current): capital gains plus the first Form 1040 tax-liability branch

The first runnable branches:

```
1099-B  --COPY-->  Form 8949 (d),(e)
                        | SUBTRACT (d - e)
                        v
                   8949 (h) gain --SUM--> 8949 line 2 total
                                              | COPY
                                              v
                   Schedule D line 8b --SUM--> line 15 (net LT)
                                                   |
   Schedule D line 7 (net ST) --SUM--> line 16 <--+
                                          | COPY
                                          v
                              Form 1040 line 7
```

Supported: long-term, single covered lot, no adjustments (req. doc Section 15.1).
The short-term path (Schedule D line 7) is a stub input (defaults to 0) for now.

M11 Step 3 extends that spine through Form 1040 line 16. The live branch now:

- selects line 12e through a first-class deduction decision (`standard` vs
  `itemized` via Schedule A line 17),
- computes regular tax through the under-$100k tax table or the cited bracket
  worksheet boundary, and
- executes the Qualified Dividends and Capital Gain Tax Worksheet line by line
  for the supported Schedule D / qualified-dividend profile.

M11 Step 4 widens the OTS witness to the tax line. The oracle box map now
compares the live graph against OTS not just through capital-gain carry-ins but
also at Form 1040 `L11b` / `L12` / `L15` / `L16`, across all five filing
statuses and threshold-straddling tax-line scenarios.

## Known v0 simplifications (eyeball list)

- **Operand model:** a computed node is produced by all edges targeting it that
  share a `rule_id`; `role` (minuend/subtrahend/addend) gives order. This was the
  first real schema gap the slice surfaced (added `role` to the edge schema).
- **Citations** point at the form `document_id` with an instructions locator;
  separate *instructions* document objects are a planned refinement.
- **quoted_text** is authored from known phrasing and must be verified verbatim by
  the citation-integrity build step before this branch is marked `supported`.
- **Capital-loss carryover** uses the cited Capital Loss Carryover Worksheet and is stored in
  the Return Record as separate short-term and long-term amounts for Schedule D lines 6 and 14.
