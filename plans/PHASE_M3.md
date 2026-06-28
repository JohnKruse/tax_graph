# PHASE M3 - Source Acquisition + change detection   [ ]

**Canary:** Thrifty Otter
**Depends on:** M0 (`tax_graph` package, `config.py`, `io/loader.py`, `cli.py`, validator).
**Goal:** Replace ad-hoc document fetching with a **repeatable, manifest-driven acquirer**:
download the IRS source docs, store the raw artifact + hash, detect what changed since last
run, and verify citation quotes still match the source. Build-time infra - it never runs
inside the MCP server.

**Exit criteria (must pass 100%):**
- `pytest -m m3` is green (fetch + change-detection + citation-integrity, all deterministic).
- Manual sanity (network): `uv run tax-graph acquire 2025` fetches the manifest docs, stores
  raw + hashes, and prints a change report. `--check` reports changed-vs-last without
  committing new state.
- CI green (deterministic `-m m3` job only; the real-network fetch is a separate gated job).

## Guardrails (do not drift)
- **Plain HTTP only (httpx). No Playwright/browser crawling.** IRS docs live at stable URLs
  (`irs.gov/pub/irs-pdf/{f|i|p}NNNN.pdf`; prior years `irs-prior/`). A maintained **manifest**
  beats scraping links. Only revisit if a needed *index* page is JS-rendered - verify first.
- **IRS source docs are clean digital-text PDFs** -> use a simple text extractor (pypdf/
  pdfplumber). This is NOT the OCR-adapter concern (that's for the taxpayer's messy docs at
  runtime); keep it deterministic and offline.
- **Politeness:** user-agent, rate-limit, retries, timeout all from `acquire.*` in config.
  Cache raw artifacts so re-runs don't re-hit IRS.
- **Determinism:** `-m m3` tests **mock the network** (fake httpx transport / canned bytes).
  The single real-network fetch test is marked `@pytest.mark.network` and excluded from the
  deterministic gate.
- Store raw + `content_hash` (sha256) + `retrieved_date` for reproducibility/audit.
- New deps to add: `httpx`, `pypdf` (or `pdfplumber`).

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

- [ ] **Step 4 - Citation integrity.** `tax_graph/acquire/citation_check.py`: for each graph
  citation, confirm its `quoted_text` still appears (whitespace-normalized) in the rendered
  text of the source mapped to its `document_id`; report mismatches. Test (fixture text):
  a matching quote passes, a doctored quote is flagged. **Note/deviation to log:** the slice
  citations currently point at *form* `document_id`s while the quote text lives in the
  *instructions* - running this against real data will surface that; resolve by adding
  instruction `document` objects and re-pointing the citations (small graph fix; flag to
  the Architect if it grows).

- [ ] **Step 5 - CLI + gate.** Wire `tax-graph acquire [--year] [--check]` to run
  manifest -> fetch/store/hash/render -> ChangeReport -> citation-integrity, printing a concise
  summary. Test: CLI smoke test (mocked fetch) asserts exit 0 + a change report + integrity
  result. Exit: `pytest -m m3` green. Docs: `acquire` usage in README.

When all steps are `[DONE]`: mark this phase `[COMPLETE]`, move it to `archive/`, and tell
John. The Architect will then generate `PHASE_M4.md` (Extraction - canary *Spectral Auditor*)
- written **after** M0+M3 are real, so it can lean on the actual config and acquired text.
