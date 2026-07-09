# Distribution plan (pinned 2026-07-09)

Status: DECIDED direction; packaging work lands in M14 (Product surface). Public
STABLE release is gated on M15 (Review Workbench campaign - the pre-ship gate).
Name-claiming alpha releases are allowed before that, clearly labeled.

## Channels (priority order)

1. **PyPI** - the foundation every other channel references. Package name `tax-graph`
   (confirmed available 2026-07-09; variants `taxgraph` / `tax-graph-mcp` were also
   free). Users run `uvx tax-graph serve --year <year>`. First upload is a
   name-claiming ALPHA (`0.1.0a1`, Development Status :: 3 - Alpha) - honest labeling,
   no stable expectation. Publishing uses John's PyPI account; CI publish via trusted
   publishing (OIDC) once wired.
2. **Claude Desktop Extension (.mcpb) + Anthropic Connectors Directory** - the headline
   consumer channel and the pinned baseline client. Bundle the server + manifest with
   `mcpb init` / `mcpb pack` (spec: github.com/modelcontextprotocol/mcpb); submit to
   the Connectors Directory for in-app one-click discoverability. M14 deliverable.
3. **Official MCP Registry** (registry.modelcontextprotocol.io) - publish a
   `server.json` referencing the PyPI package. Namespace: `io.github.johnkruse/*` is
   authenticated via John's GitHub account (cannot be squatted; no preemptive action
   needed). A DNS-verified domain namespace is optional later. CI publishes via GitHub
   OIDC (no stored secrets - fits the provenance story).
4. **Community aggregators** (mcp.so, PulseMCP, Smithery, Glama, MCP Find) - mostly
   syndicate from the official registry and GitHub automatically; verify listings after
   channel 3 lands.
5. **Docker MCP Catalog** - containerized variant; nice-to-have, not core for the
   consumer audience.
6. **Client-specific galleries** (VS Code, Cursor, Cline) - developer-oriented; low
   priority.

## Public read-only demo server (idea, unscheduled)
The graph content is public IRS-derived data, so a hosted REMOTE MCP server exposing
ONLY the read tools (`get_document` / `get_node` / `get_citation` / `get_verification` /
search) is compatible with the privacy stance: no taxpayer facts, no execution. It is
the try-before-install channel and the live demo. Computation stays local-only, always.

## Hard lines
- **No taxpayer data ever leaves the machine** in any distributed configuration;
  hosted execution is out of scope permanently unless John re-decides.
- **E-file/MeF submission stays out of scope** (engineering-plan "Output goal").
- **Stable (non-alpha) releases require the M15 gate.** Alpha releases carry the
  not-tax-advice / verify-before-filing disclaimer in README, manifest, and first-run.
- **Seasonal versioning:** releases track tax years (e.g. graph year 2025 served by
  package versions in a `2025`-labeled series once stable); the seasonal provider list
  rides in config.
- Artifacts are hash-stamped; extensions/self-serve outputs can never impersonate
  project-verified forms (self-serve-extension seam).

## Claim status (2026-07-09)
- PyPI `tax-graph`: AVAILABLE, alpha build `0.1.0a1` prepared locally; UPLOAD PENDING
  John's PyPI account/token (the one step only John can do).
- MCP Registry namespace: auto-owned via GitHub auth - nothing to claim preemptively.
- GitHub repo: owned (JohnKruse/tax_graph).
- Connectors Directory: no reservation mechanism; submit at M14.
