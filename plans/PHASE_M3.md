# PHASE M3 - Source Acquisition + change detection   [ ]

**Canary:** Thrifty Otter
**Depends on:** M0 (`tax_graph` package, `config.py`, `io/loader.py`, `cli.py`, validator).
**Goal:** Replace ad-hoc document fetching with a **repeatable, manifest-driven acquirer**:
download the IRS source docs, store the raw artifact + hash, detect what changed since last
run, and verify citation quotes still match the source. Build-time infra - it never runs
inside the MCP server.

**Exit criteria (must pass 100%):**
- `pytest -m m3` is green (fetch + change-detection + citation-integrity + rendering, all deterministic).
- Manual sanity (network): `uv run tax-graph acquire 2025` fetches the manifest docs, stores
  raw + hashes, and prints a change report. `--check` reports changed-vs-last without
  committing new state.
- CI green (deterministic `-m m3` job only; the real-network fetch is a separate gated job).

## Guardrails (do not drift)
- **Plain HTTP only (httpx). No Playwright/browser crawling.** IRS docs live at stable URLs
  (`irs.gov/pub/irs-pdf/{f|i|p}NNNN.pdf`; prior years `irs-prior/`). A maintained **manifest**
  beats scraping links. Only revisit if a needed *index* page is JS-rendered - verify first.
- **Rendering = SPLIT BY DOC TYPE** (verified on 1116). Route by manifest `kind`: **forms**
  (tax_form/schedule/source_document) -> **fitz/PyMuPDF** (Step 6); **instructions/publications**
  -> **Mistral OCR 4** (Step 7). Why: visual fidelity is a NON-GOAL - we key on the IRS line/entry
  numbers (1a, 2, 3a-3g, cols A/B/C), which are the form's canonical address = our node-id scheme.
  fitz keeps each numbered line a discrete, column-tagged row + hands us the AcroForm field grid
  (deterministic, free, local); OCR handles 2-column instruction prose where fitz would interleave
  columns. IRS docs are PUBLIC domain, so cloud OCR has NO privacy issue here (privacy only applies
  to the taxpayer's personal docs at runtime). **No raw-PDF text fallback** (pypdf scrambles
  multi-column layout). Deterministic tests use committed fixture markdown / mock the OCR client;
  if a renderer (or OCR key) is unavailable, FAIL LOUDLY. ASCII-normalize all rendered output.
- **Politeness:** user-agent, rate-limit, retries, timeout all from `acquire.*` in config.
  Cache raw artifacts so re-runs don't re-hit IRS.
- **Determinism:** `-m m3` tests **mock the network** (fake httpx transport / canned bytes).
  The single real-network fetch test is marked `@pytest.mark.network` and excluded from the
  deterministic gate.
- Store raw + `content_hash` (sha256) + `retrieved_date` for reproducibility/audit.
- New deps to add: `httpx`, `pymupdf` (fitz, form renderer, Step 6), `mistralai` (OCR, Step 7).
  Drop `pypdf` - raw-PDF text scrambles multi-column forms; not a usable fallback.

## Steps

- [DONE] **Step 1 - Manifest.** Define the acquisition manifest format and module
  (`tax_graph/acquire/manifest.py`); seed `config/manifest.yaml` with the capital-gains docs
  - the **forms and their instructions** (e.g. `f8949.pdf`/`i8949.pdf`, `f1040sd.pdf`/
  `i1040sd.pdf`, `f1040.pdf`/`i1040gi.pdf`, `f1099b.pdf`), each entry: `document_id`, `kind`
  (tax_form|instructions|...), `url`. Add a lightweight `schemas/manifest.schema.json`.
  Test: manifest loads, entries validate, URLs match the IRS pattern. Docs.
  - Verification: `python tools\check_ascii.py`, `pytest -q -m m3`, `pytest -q`,
    and `python -m tax_graph.cli validate 2025` pass.

- [DONE] **Step 2 - Fetcher + raw store + text render.** `tax_graph/acquire/fetch.py`: httpx GET
  driven by `acquire.*` config; store the raw artifact to `<raw_store>/<year>/<document_id>.pdf`;
  compute sha256 `content_hash`; capture `retrieved_date`; render a text version
  (`<document_id>.txt`) via pypdf for downstream use. Test (mocked transport): given canned
  bytes, asserts raw + text stored, hash computed, metadata recorded. Add a separate
  `@pytest.mark.network` real-fetch test (one small doc). Docs.
  - Verification: `python tools\check_ascii.py`, `pytest -q -m m3`, `pytest -q`,
    and `python -m tax_graph.cli validate 2025` pass. The live network test is
    opt-in with `TAX_GRAPH_RUN_NETWORK_TESTS=1`.

- [DONE] **Step 3 - Change detection.** `tax_graph/acquire/changes.py` + a persisted state file
  (`<raw_store>/<year>/_state.json`: document_id -> {content_hash, retrieved_date, url}). A run
  compares fresh hashes to stored state and returns a **ChangeReport** (new / changed /
  unchanged) - changed docs are what M4 re-extracts. `--check` diffs without writing state.
  Test: seeded state -> a new hash reports `changed`, same hash reports `unchanged`. Docs.
  - Verification: `python tools\check_ascii.py`, `pytest -q -m m3`, `pytest -q`,
    and `python -m tax_graph.cli validate 2025` pass.

- [DONE] **Step 4 - Citation integrity.** `tax_graph/acquire/citation_check.py`: for each graph
  citation, confirm its `quoted_text` still appears (whitespace-normalized) in the rendered
  text of the source mapped to its `document_id`; report mismatches. Test (fixture text):
  a matching quote passes, a doctored quote is flagged. **Note/deviation to log:** the slice
  citations currently point at *form* `document_id`s while the quote text lives in the
  *instructions* - running this against real data will surface that; resolve by adding
  instruction `document` objects and re-pointing the citations (small graph fix; flag to
  the Architect if it grows).
  - Verification: `python tools\check_ascii.py`, `pytest -q -m m3`, `pytest -q`,
    and `python -m tax_graph.cli validate 2025` pass.
  - Deviation logged: citation checking supports a `source_map` for form-to-instructions
    mappings; the graph citation document ids are unchanged in this step.

- [ ] **Step 5 - Form renderer via fitz (PyMuPDF), line-number-anchored.** Verified on Form 1116:
  fitz un-mashes the dense Part I deductions block that OCR collapsed, and yields the AcroForm
  field grid for free. Add `tax_graph/acquire/render_form.py`: for `kind` in {tax_form, schedule,
  source_document}, group words into rows by y-position (DROP dot-leader fragments), keeping each
  IRS line/entry number as the row anchor; read AcroForm widgets and cluster their x -> columns,
  y -> rows; emit (a) line-numbered markdown with `[entry: A B C ...]` column annotations and
  (b) `<document_id>.fields.json` (the field grid, for the M4 cross-check). Remove the Step 2
  pypdf render (keep its fetch/hash/store). Known weak spot: dense multi-column HEADERS jumble
  (same-y words from different columns concatenate) - mitigate with column-aware x-band grouping;
  not critical since downstream keys on line numbers, not headers. Deterministic + offline.
  Test: against a committed `f1116.pdf` fixture, assert the deductions sub-lines (3a-3g, 4a, 4b)
  come out as separate line-numbered rows with the correct entry columns, and the field grid shows
  the expected column x-clusters. Docs.

- [ ] **Step 6 - Instructions renderer via Mistral OCR 4 + the dispatcher.** For `kind` in
  {instructions, publication}: 2-column prose where fitz reading-order would interleave columns,
  so use OCR. Add `tax_graph/acquire/render_ocr.py` calling Mistral OCR (config `ocr.*`, key from
  keyring/env); store per-doc + per-page markdown + extracted hyperlinks (page-level citation
  locators + URLs). Cache by `content_hash` (paid API). ASCII-normalize. Note: numbered worksheet
  STEPS (prose like "Line 2. Combine...") come through clean - the computation lives there; blank
  worksheet GRIDS mash but are low-value scaffolding; genuinely garbled tabular worksheets -> flag
  for human review, never guess. Add a `render()` dispatcher that routes by `kind` (Step 5 vs
  Step 6) and FAILS LOUDLY if the needed renderer or OCR key is unavailable. Test (mocked OCR
  client): markdown + per-page + hyperlinks stored, cache hit skips re-OCR; deterministic tests
  use committed fixture markdown; a separate `@pytest.mark.network` real-OCR test (one small public
  IRS instructions doc). Docs.

- [ ] **Step 7 - CLI + gate.** Wire `tax-graph acquire [--year] [--check]` to run
  manifest -> fetch/store/hash -> render (the Step 5/6 dispatcher) -> ChangeReport ->
  citation-integrity, printing a concise summary. The renderers from Steps 5-6 now exist, so the
  CLI wires real components (not a render that does not exist yet). Test: CLI smoke test (mocked
  fetch + mocked renderers) asserts exit 0 + a change report + integrity result. Exit:
  `pytest -m m3` green. Docs: `acquire` usage in README.

When all steps are `[DONE]`: mark this phase `[COMPLETE]`, move it to `archive/`, and tell
John. The Architect will then generate `PHASE_M4.md` (Extraction - canary *Spectral Auditor*)
- written **after** M0+M3 are real, so it can lean on the actual config and acquired text.
