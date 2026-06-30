# PHASE M4 - API-based Extraction (acquired text -> DRAFT graph objects)   [ ]

**Canary:** Spectral Auditor
**Depends on:** M0 (package, `config.py`, schemas, validator) + M3 (acquire/render output).
**Goal:** Turn rendered IRS source text into **DRAFT** graph objects (nodes/edges/rules/
citations/decisions) via a **provider-agnostic** LLM client (config `llm.provider`) - a generator + an independent critic,
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
- A human diffs an extracted draft for a held-out form **plus its instructions** against its
  hand-authored reference (the capital-gains slice forms in `graph/2025/` are built-in references)
  and confirms the method is sound: line/column nodes, the column (h) = (d) - (e) SUBTRACT, and an
  outbound flow declaration to Schedule D - gaps flagged, not guessed.
- CI green (deterministic `-m m4`; the real-API extraction test is a separate gated job).

## Guardrails (do not drift)
- **Drafts only, never auto-merged.** Output to `graph/<year>/_drafts/`; promotion to the live
  graph is a human PR (requirements doc Section 13). The LLM proposes; governance disposes.
- **Constrain the model to a closed set.** Structured output (the provider's tool-use /
  function-calling / JSON-schema) must match the node/edge/rule/citation/decision schemas, and
  `operation` must be one of the **closed 19-op enum** in `schemas/rule.schema.json`. Reject
  anything off-schema or off-vocab.
- **Generator + INDEPENDENT critic.** The critic re-derives from the same source span WITHOUT
  seeing the generator's reasoning; disagreement -> flag. But LLM-vs-LLM agreement is WEAK
  evidence - the real gates are the deterministic checks + the human.
- **Deterministic cross-checks are the real validators:** (a) schema-validate every draft;
  (b) **line-number completeness** - every TRUE line anchor maps to a node, no gaps/dupes (a true
  anchor is field-backed (has an entry widget at its row in `.fields.json`) or
  instruction-referenced - NOT renderer artifacts like the form number, year, or dollar amounts:
  8949, 2025, 100); (c) **field-grid cross-check** -
  node columns/rows reconcile with `.fields.json` `x_cluster`/`y_cluster`; (d) **citation quote
  verification** - reuse `tax_graph/acquire/citation_check.py`: each citation `quoted_text` must
  appear in the cited source `.txt`.
- **Provenance on every draft:** quoted source span, `extracted_by` (model id), confidence.
  Every rule cites a source. Citations reference the INSTRUCTION `document_id` where the text lives.
- **Extraction unit = a form PLUS its instructions (a bundle), not a single file.** Form-only text
  is too thin: the column (h) formula lives in the form's column HEADER (which the line-anchor
  renderer currently drops), and cross-form flows live in the instructions. So the render must
  capture **column + section headers**, and the context resolver loads the form (nodes + field
  grid) AND its paired instructions (declared by an explicit manifest relationship). Cross-form
  flows are emitted as **outbound FEEDS declarations** (target form/line, cited to the
  instructions) and realized into edges at graph-assembly time when the target exists - a single
  form's extraction never authors another form's nodes.
- **PROVIDER-AGNOSTIC LLM (config `llm.*`) - NO privileged vendor.** The extraction LLM is
  pluggable like everything else in the project. `build_llm_client` MUST dispatch on
  `llm.provider` (require it to be set; do NOT silently default to one vendor) to a per-provider
  adapter behind the existing `LlmClient` Protocol; ship adapters for the major providers
  (the example config defaults to **openrouter** - a single OpenAI-compatible gateway to every
  vendor's models; also anthropic, openai, google/gemini, ...), each implementing that provider's
  structured-output mechanism. Key via `resolve_secret(config, "llm.api_key", keyring_path="llm.api_key_keyring",
  env_path="llm.api_key_env")` (set per provider). Deterministic tests MOCK the client; the
  real-API test is `@pytest.mark.network`, gated. The recommended-providers list (docs, seasonal)
  guides capable choices across vendors. (Mistral OCR stays a deliberate, task-specific exception
  for the OCR stage ONLY - it is NOT a precedent for privileging a reasoning-LLM vendor.)
- **ASCII-only** output. Fail loudly if the API/key is unavailable (no silent degraded path).

**Correction (2026-06-29):** `tax_graph/extract/llm_client.py` now requires explicit
`llm.provider`, dispatches to provider adapters behind `LlmClient`, and ships `openrouter`,
`anthropic`, and `openai` adapters to prove the provider-agnostic seam. OpenRouter reuses the
OpenAI-compatible client with `base_url=https://openrouter.ai/api/v1` and `vendor/model` ids.
The `LlmClient` Protocol and the generator/critic remain provider-neutral.

## Steps

- [DONE] **Step 1 - Inputs + LLM client + prompt assembly.** `tax_graph/extract/inputs.py` loads a
  document's rendered artifacts by id+kind (form: `.txt` + `.fields.json`; instructions: `.txt`
  + `.pages/` + `.links.json`). `tax_graph/extract/llm_client.py`: a `LlmClient` Protocol (so
  tests mock it) + a provider-dispatch factory `build_llm_client` keyed on `llm.provider`,
  building a per-provider adapter behind the Protocol (ship >=2 adapters, e.g. anthropic + openai,
  to prove agnosticism; no privileged default). `tax_graph/extract/
  prompts.py` assembles the generator prompt from the document identity, the line-anchored text,
  the target schemas, and the closed op vocabulary (read from `rule.schema.json`); prompt bodies
  live in `prompts/*.md` (referenced from config `extraction.prompts.*`). Test: input loading
  against committed fixtures; deterministic prompt assembly (golden prompt); client mocked. Docs.

- [DONE] **Step 2 - Generator extraction.** `tax_graph/extract/generator.py`: call the LLM
  (structured output) to emit draft node/edge/rule/citation/decision objects, each with a quoted
  source span + confidence, `operation` restricted to the closed enum. Test (mocked client with a
  canned structured response over the `f8949` fixture): produces schema-valid drafts; an off-vocab
  operation is rejected. Docs.

- [DONE] **Step 3 - Critic + deterministic cross-checks.** `tax_graph/extract/critic.py`
  (independent re-derivation -> per-object agree/flag) and `tax_graph/extract/checks.py`:
  schema validation, line-number completeness, field-grid reconciliation, and citation-quote
  verification (reuse `citation_check`). Each draft gets a confidence + a flag set. Test:
  a missing line is reported by the completeness check; a citation whose quote is absent is
  flagged; critic disagreement is recorded. Docs.

- [DONE] **Step 4 - Routing + draft writeout + report.** `tax_graph/extract/route.py`: auto-accept
  only when high-confidence AND critic-agrees AND all deterministic checks pass (thresholds from
  `extraction.*`); everything else goes to a human-review list. Write drafts as YAML to
  `graph/<year>/_drafts/<document_id>/` (nodes/edges/rules/citations/decisions) and a
  `review.md` report (auto-accept vs flagged, with reasons). MUST NOT touch the live graph dirs.
  Test: routing logic; drafts land only under `_drafts/`; a deliberately low-confidence draft is
  routed to review. Docs.

- [DONE] **Step 5 - CLI `extract` + review gate.** Wire `tax-graph extract [--doc ID | --year]` to
  run inputs -> generator -> critic -> checks -> route, printing the review summary. Test: CLI smoke
  test (mocked client) asserts exit 0, drafts under `_drafts/`, live graph untouched; plus a
  `@pytest.mark.network` real-API test. Done: a live OpenRouter run produced schema-shaped drafts
  and the review gate worked (0 auto / 26 review / 8 issues). Docs: `extract` usage in README.

- [DONE] **Step 6 - Extraction-context + check fixes (from the M4 worker note).** Make the extractor's
  evidence match where the authority lives:
    - **Bundle resolver:** add an explicit form<->instructions relationship to `config/manifest.yaml`
      (+ `manifest.schema.json`); the context resolver loads a form's nodes/field-grid AND its
      paired instructions text.
    - **Richer form render:** enhance `render_form.py` to capture **column and section headers**
      (the column (h) header carries the SUBTRACT formula) and stop emitting header/note prose as
      fake line rows.
    - **True-anchor completeness:** count only field-backed / instruction-referenced line anchors;
      ignore renderer artifacts (form number, year, dollar amounts).
    - **Positional field-grid reconciliation:** use `x_cluster`/`y_cluster`, not regex on AcroForm
      field names.
    - **Outbound flows + citations:** emit cross-form `FEEDS` declarations cited to the instruction
      doc; citations reference the instruction `document_id`.
  Tests for each fix (deterministic, mocked). Docs.

- [ ] **Step 7 - Outline-first extraction (replaces the per-line chunk; from Codex's outline-first
  proposal).** One-pass whole-document extraction asks a single call to do everything (find
  structure, quote exactly, choose ids, decompose formulas, emit provenance, satisfy schema) - too
  much, and live trials showed it is task SHAPE, not model choice, that fails. Instead: build the
  form's structure deterministically, walk it with tiny model questions, assemble graph objects in
  CODE.
    1. **Outline tree - mostly deterministic.** Build `graph/<year>/_drafts/<id>/outline.yaml` from
       the rendered form text + headers + field-grid geometry + line anchors: sections, lines,
       tables, column groups, checkbox groups, worksheets, outbound-flow cues. LLM **repair only**
       for blocks the deterministic builder cannot confidently classify. Commit it as a reviewable
       draft artifact (a human can sanity-check the structure before any extraction).
    2. **Evidence bundle per outline node:** nearby form text, headers, the node's field-grid rows
       (x/y clusters), and the relevant instruction text (whole instructions are small - pass them,
       cached).
    3. **Micro-extractions - tiny purpose-specific schemas, NOT the full graph schema.** Walk the
       tree asking ONE narrow question per node (classify the node; extract just the formula as an
       `operation_plan` over the closed ops; extract just the outbound flow; select the citation).
       Small prompts + narrow schemas make cheap/fast models viable - support an optional cheaper
       `llm.micro_model` (defaults to `llm.model`), behind the same provider-agnostic `LlmClient`.
    4. **Citations - hybrid, code lifts the exact span.** The model SELECTS the supporting passage
       (or picks among candidate spans); CODE extracts the verbatim substring from the source, so
       the quote passes `citation_check` by construction. The model never free-types quote text.
    5. **Deterministic assembly.** CODE (not the model) assigns stable ids, maps outline ids ->
       node ids, builds schema-shaped objects from the micro-results, attaches provenance, and
       merges Part I/II duplicate patterns. Drafts stay under `_drafts/`.
  Layered checks: outline completeness, evidence completeness, micro-quote-in-evidence, assembly
  schema-validation. The whole-document one-pass stays as a fallback baseline. `form_8949_2025` is
  the canary for outline-first before expanding to Schedule D / 1040.
  Test (mocked client): the outline builder produces the 8949 tree (Part I/II, line-1 tables,
  line-2 totals, flow cues) deterministically; a mocked micro-extraction recovers column (h) =
  d - e + g over closed ops; assembly yields schema-valid objects with code-assigned ids. Docs.

- [ ] **Step 8 - Held-out validation (corrected gate).** Extract `form_8949_2025` **with its
  instructions** and diff against the hand-authored `graph/2025/` reference. Sound if it recovers:
  the line/column nodes, column (h) = (d) - (e) **combined with (g)** (an `operation_plan` of
  SUBTRACT then SUM over the closed ops, cited), and **outbound FEEDS declarations** to Schedule D
  (e.g. lines 1b, 2, 3, 8b, 9, 10; the realized edges are validated when Schedule D is also
  extracted). Gaps flagged, not guessed. Exit:
  `pytest -m m4` green + the human held-out diff confirmed.

  Worker note 2026-06-29: CLI wiring, deterministic mocked-client M4 tests, README usage, and
  `pytest -m m4` are complete. Live configured-provider extraction and the human held-out diff
  remain pending, so the phase is not marked `[COMPLETE]` or archived.

  Worker note 2026-06-29 live trial: OpenRouter extraction with `z-ai/glm-5.2` ran for
  `form_8949_2025` and wrote drafts to `graph/2025/_drafts/form_8949_2025/` with
  `auto_accepted=0`, `human_review=26`, and `deterministic_issues=8`. This proves the live
  draft/writeout path works and stays review-gated, but the held-out quality gate is NOT met:
  the draft recovered line-2 total SUM rules, not the hand-authored column (h) SUBTRACT rule or
  Schedule-D flow. Do not mark Step 7 `[DONE]` or M4 `[COMPLETE]` until source rendering/prompting
  recovers those core structures or flags the absence more specifically.

  Worker note 2026-06-29 follow-up: Step 6 fixes are implemented and deterministic tests are
  green. OpenRouter trials showed model variance: `z-ai/glm-5.2` was unreliable for the
  JSON-schema contract, `qwen/qwen3.7-plus` recovered SUBTRACT/FEEDS but was slow/flaky, and the
  local ignored config currently uses `openai/gpt-5.2-chat` through OpenRouter. With the bundled
  instructions and stronger model, `form_8949_2025` live extraction now recovers line/column nodes,
  the column (h) SUBTRACT calculation, and outbound FEEDS declarations to Schedule D lines 1b, 3,
  8b, and 10 (also 2 and 9 where the instructions imply them). The review gate remains conservative
  (`auto_accepted=0`, `human_review=32`, `deterministic_issues=19`) because exact quote/provenance
  and some line-anchor issues still need human review. Step 7 remains open for John's held-out diff.

## Housekeeping (for Codex)
- **Gitignore `graph/<year>/_drafts/`** - extraction drafts are regenerated every run; do not commit
  churny LLM output. `git rm -r --cached graph/2025/_drafts` and delete the stale glm-5.2 drafts
  under `graph/2025/_drafts/form_8949_2025/`. The human promotes ACCEPTED objects into the live
  `graph/<year>/` (which IS committed), not the raw drafts. (If PR-visible drafts are wanted later,
  revisit - but default to gitignore.)
- **Write generated files with LF newlines** (`newline="\n"`) in the renderers / draft writers so
  output stops tripping the `.gitattributes` CRLF->LF normalization warnings on Windows.
- **Retire the worker-note files** once M4 is `[COMPLETE]`: `plans/M4_WORKER_NOTE_FOR_CLAUDE.md` and
  `plans/M4_OUTLINE_FIRST_EXTRACTION_PROPOSAL_FOR_CLAUDE.md` are addressed (their decisions are in
  this plan now) - delete them or move to `plans/archive/`.

When all steps are `[DONE]`: mark this phase `[COMPLETE]`, move it to `plans/archive/`, and tell
John. The Architect will then generate `PHASE_M1.md` (Compile to SQLite - canary
*Crystalline Ledger*), per the automation-first order M0 -> M3 -> M4 -> M1 -> M2 -> M5 -> M6.
