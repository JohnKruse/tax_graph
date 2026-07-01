# Tax Graph

[![CI](https://github.com/JohnKruse/tax_graph/actions/workflows/ci.yml/badge.svg)](https://github.com/JohnKruse/tax_graph/actions/workflows/ci.yml)

Tax Graph is a local-first project for modeling U.S. tax forms as a typed,
deterministic computation graph. The current proof of concept covers a narrow
2025 capital-gains slice:

```text
1099-B -> Form 8949 -> Schedule D -> Form 1040 line 7
```

The goal is for agents and tools to traverse verified tax graph data instead of
inventing tax logic.

## Install

This project is being packaged for `uv`.

```powershell
uv sync
```

The base install is the light runtime: graph validation, execution, and (in M1)
SQLite build/read commands. It intentionally does not install acquisition,
OCR, PDF rendering, or live LLM SDKs.

Maintainers who need the full build pipeline should install the build extra:

```powershell
uv sync --extra build
```

For local development, including pytest and the build pipeline extras:

```powershell
uv sync --extra dev
```

If `uv` is not available in your environment yet, the existing proof-of-concept
scripts can still be run with Python directly.

Live LLM extraction uses optional provider SDKs. For the default OpenRouter
adapter, install the OpenAI-compatible SDK extra:

```powershell
uv sync --extra llm-openrouter
```

## CLI Usage

Phase M0 provides a package CLI named `tax-graph`:

```powershell
uv run tax-graph validate 2025
uv run tax-graph run --facts examples\capital_gains_basic\facts.yaml
uv run tax-graph build 2025
uv run tax-graph run --facts examples\capital_gains_basic\facts.yaml --source sqlite
uv run tax-graph acquire 2025
uv run tax-graph acquire 2025 --check
uv run tax-graph extract --doc form_8949_2025
```

When working from a source checkout before installing console scripts, the same
commands can be run as a module:

```powershell
python -m tax_graph.cli validate 2025
python -m tax_graph.cli run --facts examples\capital_gains_basic\facts.yaml
python -m tax_graph.cli build 2025
python -m tax_graph.cli acquire 2025 --check
python -m tax_graph.cli extract --doc form_8949_2025
```

Expected result: `form_1040_2025_line_7_capital_gain_loss = 2000`.

`tax-graph build 2025` compiles the authored YAML graph into
`build/tax_graph_2025.sqlite`. The SQLite file is a deterministic runtime
artifact rebuilt from YAML; `build/` is gitignored, so the binary artifact is
not committed.

After a build exists, `tax-graph run` defaults to the SQLite artifact. Use
`--source yaml` to force the authored YAML source or `--source sqlite` to require
the compiled artifact.

## CI

GitHub Actions runs the deterministic gate on pushes and pull requests:

```powershell
uv sync --extra dev
uv run tax-graph validate 2025
uv run tax-graph run --facts examples\capital_gains_basic\facts.yaml
uv run pytest
```

## Acquisition Manifest

Source acquisition starts from `config/manifest.yaml`, a reviewed list of stable
IRS PDF URLs for the supported tax year. M3 begins with the 2025 capital-gains
slice: Form 8949, Schedule D, Form 1040, Form 1099-B, and their instructions
where applicable.

Fetched source documents are stored under the configured raw store, defaulting
to `.cache/raw/<year>/`, with the original PDF, extracted text, and JSON
metadata containing the content hash and retrieval date.

The raw store also keeps `_state.json`, a document-id index of the last seen
content hash. Acquisition uses that state to report new, changed, and unchanged
source documents.

Citation integrity checks compare each authored `quoted_text` span to the
rendered text in the raw store after whitespace normalization. A source map can
point form citations at instruction PDFs when the authoritative quote lives in
the instructions.

Forms, schedules, and source documents render through PyMuPDF into line-numbered
text plus a companion `.fields.json` AcroForm grid. Instruction rendering is
handled separately by Mistral OCR, storing per-document markdown, per-page
markdown, and extracted links. The OCR path caches by content hash and fails
loudly when no OCR client or key is available.

## Extraction Drafts

Phase M4 adds `tax-graph extract --doc <document_id>`, which turns rendered
source artifacts into schema-valid draft graph YAML through a mocked-in-tests
LLM client protocol and a live provider adapter when `llm.provider` is
configured. Drafts are written only under `graph/<year>/_drafts/<document_id>/`, together with
`provenance.yaml`, `review.md`, and a standalone `review.html` source-to-draft
visual review page; the live graph directories are never modified by
extraction.

Live extraction is provider-agnostic behind `tax_graph.extract.llm_client.LlmClient`.
The built-in adapters currently cover `openrouter`, `anthropic`, and `openai`,
with provider SDKs installed only when needed via optional extras. OpenRouter
uses the OpenAI-compatible client with `llm.base_url`, so model ids may use the
gateway's `vendor/model` format. The Mistral-specific path is limited to OCR
for instructions and publications.

Automatic routing is conservative: a draft must meet the configured confidence
threshold, agree with the independent critic, and pass deterministic checks
before it appears in the auto-accepted section of the review report. Anything
else stays on the human-review list.

M4 also includes an outline-first canary path, enabled through config with
`extraction.mode: outline_first`. That path writes local review artifacts
(`outline.yaml`, `candidate_spans.yaml`, and `outbound_flows.yaml`) under the
same `_drafts` directory, asks narrow micro-extraction questions over outline
nodes, and assembles canonical draft graph objects in code. The default remains
`one_pass` until the held-out Form 8949 validation is complete.

## Compatibility Scripts

Validate the authored graph:

```powershell
python tools\validate_graph.py 2025
```

Run the capital-gains example:

```powershell
python engine\engine.py examples\capital_gains_basic\facts.yaml 2025
```

Expected result: `form_1040_2025_line_7_capital_gain_loss = 2000`.
