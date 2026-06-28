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

If `uv` is not available in your environment yet, the existing proof-of-concept
scripts can still be run with Python directly.

## CLI Usage

Phase M0 provides a package CLI named `tax-graph`:

```powershell
uv run tax-graph validate 2025
uv run tax-graph run --facts examples\capital_gains_basic\facts.yaml
uv run tax-graph acquire 2025
uv run tax-graph acquire 2025 --check
```

When working from a source checkout before installing console scripts, the same
commands can be run as a module:

```powershell
python -m tax_graph.cli validate 2025
python -m tax_graph.cli run --facts examples\capital_gains_basic\facts.yaml
python -m tax_graph.cli acquire 2025 --check
```

Expected result: `form_1040_2025_line_7_capital_gain_loss = 2000`.

## CI

GitHub Actions runs the deterministic gate on pushes and pull requests:

```powershell
uv sync --all-groups
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
