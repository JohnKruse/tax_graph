# PHASE M4 - API-based Extraction (acquired text -> DRAFT graph objects)   [ ]

**Canary:** Spectral Auditor
**Depends on:** M0 (package, `config.py`, schemas, validator) + M3 (acquire/render output).
**Goal:** Turn rendered IRS source text into **DRAFT** graph objects (nodes/edges/rules/
citations/decisions) via the Anthropic (Claude) API - a generator + an independent critic,
constrained to the schemas and the closed op vocabulary, with deterministic cross-checks and
a human-review gate. This is what gets us out of hand-authoring. **Drafts are NEVER
auto-merged into the live graph.**

## Inputs (produced by M3, in `<raw_store>/<year>/`)
- **Forms** (`kind` tax_form/schedule/source_document): `<document_id>.txt` (line-anchored
  rows, e.g. `- 3g: Multiply line 3c by line 3f`) + `<document_id>.fields.json`
  (`{"fields":[{field_name,page,x0,y0,x1,y1,x_cluster,y_cluster}]}`).
- **Instructions** (`kind` instructions/publication): `<document_id>.txt` +
  `<document_id>.pages/page-NNN.md` (page-level citation locators) + `<document_id>.links.json`
  (citation URLs).
- Document `kind` and ids from `config/manifest.yaml` (note: it already has separate
  `instructions_*` ids, so citation objects can point at the doc where the quote actually lives).

## Exit criteria (must pass 100%)
- `pytest -m m4` is green (deterministic; the LLM client is MOCKED).
- `uv run tax-graph extract --doc <id>` writes schema-valid DRAFT YAML to
  `graph/<year>/_drafts/<id>/` plus a review report, and does NOT modify the live graph.
- A human diffs an extracted draft for a held-out form against its hand-authored reference
  (the capital-gains slice forms in `graph/2025/` are built-in references) and confirms the
  method is sound.
- CI green (deterministic `-m m4`; the real-API extraction test is a separate gated job).

## Guardrails (do not drift)
- **Drafts only, never auto-merged.** Output to `graph/<year>/_drafts/`; promotion to the live
  graph is a human PR (requirements doc Section 13). The LLM proposes; governance disposes.
- **Constrain the model to a closed set.** Structured output (Anthropic tool-use) must match the
  node/edge/rule/citation/decision schemas, and `operation` must be one of the **closed 19-op
  enum** in `schemas/rule.schema.json`. Reject anything off-schema or off-vocab.
- **Generator + INDEPENDENT critic.** The critic re-derives from the same source span WITHOUT
  seeing the generator's reasoning; disagreement -> flag. But LLM-vs-LLM agreement is WEAK
  evidence - the real gates are the deterministic checks + the human.
- **Deterministic cross-checks are the real validators:** (a) schema-validate every draft;
  (b) **line-number completeness** - every line anchor in the form `.txt` maps to a node, no
  gaps/dupes (the IRS numbering is the spine and the audit); (c) **field-grid cross-check** -
  node columns/rows reconcile with `.fields.json` `x_cluster`/`y_cluster`; (d) **citation quote
  verification** - reuse `tax_graph/acquire/citation_check.py`: each citation `quoted_text` must
  appear in the cited source `.txt`.
- **Provenance on every draft:** quoted source span, `extracted_by` (model id), confidence.
  Every rule cites a source. Citations reference the INSTRUCTION `document_id` where the text lives.
- **Claude API via config `llm.*`** (model `llm.model`; key via
  `resolve_secret(config, "llm.api_key", keyring_path="llm.api_key_keyring", env_path="llm.api_key_env")`).
  Deterministic tests MOCK the client (mirror the `OcrClient` Protocol pattern in `render_ocr.py`);
  the real-API test is `@pytest.mark.network`, gated. Confirm current model id + Anthropic SDK
  structured-output mechanics at build time (consult the Anthropic SDK docs / claude-api reference).
- **ASCII-only** output. Fail loudly if the API/key is unavailable (no silent degraded path).

## Steps

- [ ] **Step 1 - Inputs + LLM client + prompt assembly.** `tax_graph/extract/inputs.py` loads a
  document's rendered artifacts by id+kind (form: `.txt` + `.fields.json`; instructions: `.txt`
  + `.pages/` + `.links.json`). `tax_graph/extract/llm_client.py`: a `LlmClient` Protocol (so
  tests mock it) + a real Anthropic client built from `llm.*` config. `tax_graph/extract/
  prompts.py` assembles the generator prompt from the document identity, the line-anchored text,
  the target schemas, and the closed op vocabulary (read from `rule.schema.json`); prompt bodies
  live in `prompts/*.md` (referenced from config `extraction.prompts.*`). Test: input loading
  against committed fixtures; deterministic prompt assembly (golden prompt); client mocked. Docs.

- [ ] **Step 2 - Generator extraction.** `tax_graph/extract/generator.py`: call the LLM
  (structured output) to emit draft node/edge/rule/citation/decision objects, each with a quoted
  source span + confidence, `operation` restricted to the closed enum. Test (mocked client with a
  canned structured response over the `f8949` fixture): produces schema-valid drafts; an off-vocab
  operation is rejected. Docs.

- [ ] **Step 3 - Critic + deterministic cross-checks.** `tax_graph/extract/critic.py`
  (independent re-derivation -> per-object agree/flag) and `tax_graph/extract/checks.py`:
  schema validation, line-number completeness, field-grid reconciliation, and citation-quote
  verification (reuse `citation_check`). Each draft gets a confidence + a flag set. Test:
  a missing line is reported by the completeness check; a citation whose quote is absent is
  flagged; critic disagreement is recorded. Docs.

- [ ] **Step 4 - Routing + draft writeout + report.** `tax_graph/extract/route.py`: auto-accept
  only when high-confidence AND critic-agrees AND all deterministic checks pass (thresholds from
  `extraction.*`); everything else goes to a human-review list. Write drafts as YAML to
  `graph/<year>/_drafts/<document_id>/` (nodes/edges/rules/citations/decisions) and a
  `review.md` report (auto-accept vs flagged, with reasons). MUST NOT touch the live graph dirs.
  Test: routing logic; drafts land only under `_drafts/`; a deliberately low-confidence draft is
  routed to review. Docs.

- [ ] **Step 5 - CLI `extract` + gate + held-out validation.** Wire `tax-graph extract
  [--doc ID | --year]` to run inputs -> generator -> critic -> checks -> route, printing the
  review summary. Test: CLI smoke test (mocked client) asserts exit 0, drafts under `_drafts/`,
  live graph untouched; plus a `@pytest.mark.network` real-API test (one small doc). **Held-out
  validation:** extract `form_8949_2025` and diff the drafts against the hand-authored
  `graph/2025/` nodes/edges/rules - the method is sound if the core line nodes + the
  `8949 (h) = (d) - (e)` SUBTRACT and the Schedule-D flow come back correctly (gaps -> flagged,
  not guessed). Exit: `pytest -m m4` green. Docs: `extract` usage in README.

When all steps are `[DONE]`: mark this phase `[COMPLETE]`, move it to `plans/archive/`, and tell
John. The Architect will then generate `PHASE_M1.md` (Compile to SQLite - canary
*Crystalline Ledger*), per the automation-first order M0 -> M3 -> M4 -> M1 -> M2 -> M5 -> M6.
