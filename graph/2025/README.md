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

## What's here (v0): the capital-gains MVP slice

The first runnable branch:

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

## Known v0 simplifications (eyeball list)

- **Operand model:** a computed node is produced by all edges targeting it that
  share a `rule_id`; `role` (minuend/subtrahend/addend) gives order. This was the
  first real schema gap the slice surfaced (added `role` to the edge schema).
- **Citations** point at the form `document_id` with an instructions locator;
  separate *instructions* document objects are a planned refinement.
- **quoted_text** is authored from known phrasing and must be verified verbatim by
  the citation-integrity build step before this branch is marked `supported`.
- **Capital-loss carryover** (when line 16 is a net loss) is deferred (Section 9.3); the
  Return Record's carryforward block is where it will live.
