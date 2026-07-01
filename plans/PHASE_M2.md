# PHASE M2 - MCP server (stdio)   [ ]

**Canary:** Polite Robot
**Depends on:** M0 (package, CLI, `config.py`), M1 (compiled `tax_graph_<year>.sqlite` + the
source-agnostic `Graph(year, source=...)` loader), the engine (`Engine.execute` -> `Result` with
`values` / `trace` / `missing_required_inputs`), and the schemas (nodes/edges/rules/citations/
decisions). Independent of M5/M6/M6b.
**Goal:** Ship the **runtime interface**: a local stdio MCP server that exposes the compiled graph +
engine + trace to any MCP client, so an AI agent can traverse the roadmap, execute a return from
facts, and read citations - WITHOUT the model improvising tax logic. This is the "Polite Robot" that
answers the requirements-doc success-criteria questions by walking the graph.

## Why
The durable contribution is the graph; MCP is one interface onto it (requirements doc Section 8,
engineering-plan "Target architecture"). M1 produced the shippable artifact (SQLite) and a
source-agnostic loader; M2 puts a thin, deterministic protocol layer on top so Claude Desktop (and any
other MCP client) can use it. The server is an ADAPTER - all logic stays in engine/loader/validate so
the graph remains useful if MCP is ever replaced.

## Exit criteria (must pass 100%)
- `pytest -m m2` is green (deterministic; tools are exercised by calling the handlers directly - no
  live MCP client, no network).
- `uv run tax-graph serve [--year 2025]` starts a stdio MCP server that loads the compiled 2025 graph
  (falls back to YAML when no build exists) and advertises the M2 tool set.
- A **manual Claude Desktop walk-through** (the human gate, like M4's live-API gate) connects to the
  local server and traverses `1099-B -> Form 8949 -> Schedule D -> Form 1040 line 7`, getting computed
  values + audit trace + IRS citations.
- **Base-only** install (no `[acquire]`/`[extract]` extras) can `serve`; a runtime guard asserts
  `fitz`/`mistralai` are NOT imported by `serve`.
- CI green (the deterministic `-m m2` job; the manual Desktop walk-through is documented, not
  automated).

## Guardrails (do not drift)
- **MCP is an interface, not the core.** The server is a thin adapter over the existing
  engine/loader/validate. Put NO tax logic in `tax_graph/mcp/`. The graph must stay usable without MCP.
- **The model never computes.** The server never computes tax values itself; `execute_tax_tree`
  delegates to `Engine`. The server `instructions` block forbids the client model from computing, from
  asserting a rule without a citation, and from guessing past a decision or an unsupported case.
- **Every asserted rule carries its citation; missing/unsupported is reported, never guessed**
  (invariant "incomplete, but never wrong"). Decision nodes present their options INCLUDING the escape
  hatch (`decision.schema.json` requires an other/unsupported/escalate option).
- **Client-agnostic (provider-agnostic).** The server privileges NO vendor; Claude Desktop is only the
  reference/testing client. Any MCP client must work.
- **Runtime stays light.** Add `mcp` to BASE deps (base = pyyaml, jsonschema, typer, mcp). `serve`
  imports NO build-time deps (pymupdf/mistralai/httpx). Reads the compiled SQLite via the M1
  source-agnostic loader; rebuildable from YAML; local-first stdio; no network.
- **Table-aware addressing seam (M6b forward-compat).** Node-addressing tools accept and round-trip an
  optional runtime instance suffix `#<row_key>` and must NOT assume a node_id lacks `#`. Static ids
  stay flat/template-level; instances are runtime-only. This keeps the client-facing addressing
  contract stable when M6b lands repeatable-table execution. See engineering-plan "Repeatable tables
  (decided)".
- **ASCII-only.**

## Tool set (requirements doc Section 8.2, curated for M2)
Read-only graph: `get_document`, `get_node`, `get_dependencies`, `get_downstream_effects`,
`get_citation`. Execution + explanation: `execute_tax_tree`, `list_required_inputs`,
`explain_calculation`, `export_audit_file`. **Deferred (NOT M2):** `build_tax_tree` (Personal Tax Tree
pruning - the engine currently executes the whole graph from facts) and `trace_value_flow` (subsumed
by `explain_calculation` + `get_dependencies` for now).

## Steps

- [DONE] **Step 1 - `mcp` dep + `serve` entrypoint (stdio skeleton).** Add `mcp` (official MCP Python
  SDK) to BASE `dependencies` in `pyproject.toml` (base stays light: pyyaml, jsonschema, typer, mcp);
  refresh `uv.lock`. Create `tax_graph/mcp/server.py` that builds a stdio MCP server, loads the graph
  through the source-agnostic loader (`Graph(year, source=...)`, default sqlite when built else yaml),
  and registers the M2 tools (handlers may be stubs this step). Wire `tax-graph serve [--year]
  [--source]` in `cli.py` (typer command + argparse fallback, matching the existing pattern). Test:
  the server object builds and advertises exactly the M2 tool names; importing/constructing `serve`
  does NOT import `fitz`/`mistralai` (assert not in `sys.modules`). Docs (README serve section + a
  Claude Desktop config snippet).
  - Verification: `uv run pytest -m m2` -> 2 passed, 74 deselected; `uv run pytest` -> 73 passed,
    3 skipped; `uv run python tools\check_ascii.py` -> ASCII check OK.

- [DONE] **Step 2 - Read-only graph tools.** Implement `get_document`, `get_node`, `get_dependencies`
  (upstream, from the engine's `incoming` index), `get_downstream_effects` (a derived OUTGOING index -
  the reverse of `incoming`), and `get_citation` (from the citations table; support search-by-phrase
  via the compiled `graph_fts` FTS5 index). Node addressing: accept a `node_id` with an optional
  `#<row_key>` suffix, resolve the base node, and note instances are runtime-only (M6b). Test: on the
  capital-gains slice, `get_dependencies(schedule_d_2025_line_16_total)` returns line 7 + line 15;
  `get_downstream_effects(form_8949_2025_partii_total_gain_loss)` reaches
  `form_1040_2025_line_7_capital_gain_loss`; `get_citation(cite_8949_col_h_gain)` returns its
  `quoted_text`; an FTS query for "Subtract" returns that citation id. Docs.
  - Verification: `uv run pytest -m m2` -> 5 passed, 74 deselected; direct MCP tool tests cover
    document/node lookup, `#row_key` base-node resolution, upstream/downstream traversal, citation id
    lookup, and compiled FTS citation search.

- [ ] **Step 3 - Execution + explanation tools.** `execute_tax_tree(facts)` loads facts (same shape as
  `examples/.../facts.yaml`), runs `Engine.execute`, and returns computed `values` +
  `missing_required_inputs` + the per-node `trace` (NEVER computing anything in the tool itself).
  `list_required_inputs(facts)` returns missing required leaf inputs. `explain_calculation(node)`
  returns that node's rule/operation/operands/citations from the trace. `export_audit_file(target)`
  returns the human-readable trace (the `render_trace` rendering) for a node. The return/trace shape
  must be able to carry instance-addressed rows (`<column_node>#<row_key>`) later (do not assume ids
  lack `#`). Test: `execute_tax_tree` on `capital_gains_basic` yields
  `form_1040_2025_line_7_capital_gain_loss` = 2000 with a trace; `list_required_inputs` flags a removed
  1099-B box as missing; `explain_calculation` on the 8949 gain node shows the SUBTRACT + its citation;
  `export_audit_file` contains the SUBTRACT/SUM chain and citation ids. Docs.

- [ ] **Step 4 - Behavioral contract + decisions + light-runtime gate.** Populate the server
  `instructions` block with the contract: (1) never compute values yourself - call `execute_tax_tree`;
  (2) never assert a rule without its citation; (3) at a decision node, present the options INCLUDING
  the escape hatch, never rule yourself; (4) report missing inputs and marked-unsupported cases rather
  than guess. Surface decision nodes (the `decisions` kind) so a client sees `question` + `options` +
  the escape option. Confirm a base-only (`uv --no-dev`, no `[acquire]`/`[extract]`) environment can
  `serve` end to end. Test: the `instructions` string contains the four contract clauses; a decision
  node exposes options with at least one `other`/`unsupported`/`escalate`; a base-only guard asserts
  `fitz`/`mistralai` are not imported by `serve`. Exit: `pytest -m m2` green.

## Human gate (John)
The **manual Claude Desktop walk-through** is John's action, not automatable. Follow M4's precedent:
Codex completes Steps 1-4 with `pytest -m m2` green and marks them `[DONE]`, but does NOT mark the
phase `[COMPLETE]` or archive it until John confirms the Desktop walk-through (capital-gains branch ->
values + trace + citations). Surface that the walk-through is pending in the handoff.

When all steps are `[DONE]` and John confirms the walk-through: mark this phase `[COMPLETE]`, move it
to `plans/archive/`, single `git push`, and tell John. Next by the execution order
(M0 -> M3 -> M4 -> M1 -> M2 -> M5 -> M6 -> M6b) is **M5** (Return Record, canary *Future Echo*); the
Architect generates `PHASE_M5.md`. Note `plans/PHASE_M7.md` already exists and may run alongside.
