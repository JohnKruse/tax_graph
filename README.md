# Tax Graph

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

## Run The Current POC

Validate the authored graph:

```powershell
python tools\validate_graph.py 2025
```

Run the capital-gains example:

```powershell
python engine\engine.py examples\capital_gains_basic\facts.yaml 2025
```

Expected result: `form_1040_2025_line_7_capital_gain_loss = 2000`.

## Phase M0 Target

Phase M0 converts the proof of concept into a package named `tax_graph` with a
CLI named `tax-graph`. The target commands are:

```powershell
uv run tax-graph validate 2025
uv run tax-graph run --facts examples\capital_gains_basic\facts.yaml
pytest -m m0
```
