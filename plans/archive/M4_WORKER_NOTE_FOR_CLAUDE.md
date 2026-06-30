# Archived M4 Worker Note for Claude - Step 5 Concerns

Date: 2026-06-29
Worker: Codex
Phase canary: Spectral Auditor

## Summary

The M4 extraction pipeline is now operational for a live configured provider.
With `llm.provider: openrouter` and `llm.model: z-ai/glm-5.2`, the command:

```powershell
python -m tax_graph.cli extract --doc form_8949_2025
```

successfully called OpenRouter, wrote schema-shaped drafts under:

```text
graph/2025/_drafts/form_8949_2025/
```

and did not touch the live graph directories. The review gate worked:

```text
auto_accepted: 0
human_review: 26
deterministic_issues: 8
```

So the mechanics are working. The held-out quality gate is not.

## What Failed

The plan says the held-out `form_8949_2025` extraction is sound if it recovers:

- core Form 8949 line nodes
- the column (h) calculation, expected in the current slice as `SUBTRACT`
- the Schedule D flow
- gaps flagged rather than guessed

The live draft recovered line-2 total `SUM` rules for columns (d), (e), (g), and (h).
It did not recover the hand-authored row-level rule:

```text
column (h) = column (d) - column (e)
```

It also did not recover the Schedule D flow from this one-document extraction.

This is the key concern: the current Step 5 held-out gate may be asking a form-only
extraction to recover relationships whose strongest authority is outside the sparse
form render.

## Source Input Problem

The rendered form text for Form 8949 is very thin. It currently contains rows like:

```text
- 1: If you enter an amount in column (g),
- 2: Totals. Add the amounts in columns (d), (e), (g), and (h)
```

That is enough evidence for line-2 totals and `SUM` operations. It is not enough
evidence for the row-level gain/loss formula in column (h).

Likely missing evidence:

- Form 8949 table/column header text not captured by the current form renderer.
- The Form 8949 instructions text explaining columns (d), (e), (g), and (h).
- Cross-document context saying Form 8949 totals flow to Schedule D.

## Planning Questions

Please decide what Step 5 should require from the extractor input context:

1. Should `extract --doc form_8949_2025` include paired instructions context automatically?

   For example, a form document could load source snippets from
   `instructions_form_8949_2025` based on a manifest relationship or naming convention.

2. Should cross-document flows be extracted only when extracting a form plus its instructions,
   or should they be deferred to an instruction-document extraction?

   The current held-out gate expects Schedule D flow, but a strict form-only extraction may
   not have the authoritative text for that.

3. Should M3 form rendering be improved before M4 completion?

   The current renderer is line-anchor-oriented. It misses or de-emphasizes table headers and
   column formulas. For extraction, the model likely needs a richer form text artifact:

   - line rows
   - column headers
   - nearby table text
   - page/field layout summaries

4. Should line completeness ignore decorative/non-line anchors from the renderer?

   The live review still reports anchors such as `8949`, `2025`, `a`, and `100` as missing
   nodes. These come from form rendering artifacts, not necessarily IRS line numbers that
   should map one-to-one to graph nodes.

5. Should field-grid reconciliation be table-aware?

   I reduced false positives from AcroForm names like `Table_Line1_Part1...f1_03[0]`, but
   a principled table-aware check would be better than regex heuristics.

## Worker Recommendation

Do not mark M4 Step 5 done yet.

Recommended plan adjustment:

- Add a source-context resolver to M4:
  - form extraction can include paired instruction snippets
  - citation objects can point to the instruction document where the quote lives
  - form-only text remains available, but is not the whole evidence base
- Add a richer form render artifact or improve the existing `.txt` output to include column
  headers and table context.
- Clarify whether Schedule D flow is expected from:
  - `form_8949_2025`
  - `instructions_form_8949_2025`
  - a multi-document extraction bundle
- Refine deterministic line completeness to distinguish true IRS line anchors from renderer
  artifacts.

Only after that should the held-out `form_8949_2025` diff be retried and Step 5 considered
complete.

## Current Implementation Notes

Implemented since the first M4 pass:

- provider-agnostic `LlmClient`
- OpenRouter adapter via OpenAI-compatible client
- config discovery for `config/tax-graph.config.yaml`
- Windows user-environment fallback for secrets
- optional dependency extras for `llm-openrouter`
- `tax-graph extract --doc`
- `tax-graph extract --year`
- review-gated draft writeout
- prompt compaction to avoid live structured-output length failures
- reduced false-positive field-grid checks

Current deterministic gate:

```text
pytest -m m4: passing
pytest: passing
python tools/check_ascii.py: passing
```
