# Self-Serve Form Extension (stub)

Status: DIRECTION PINNED 2026-07-07. This is a target statement, not a build plan.
Details are fleshed out just-in-time after M10 measures per-form cost. Nothing here
changes M9 or M10 scope.

## Thesis

tax_graph ships a VERIFIED CORE plus an EXTENSION HARNESS, not an encyclopedia.

- The verified core is the form set the project itself extracted, witnessed, and
  human-gated (capital gains set now; the M10 batch set next). Our name goes only
  on forms whose Verification Record shows passing witnesses.
- Every other form is self-serve: the user (or their AI agent) runs the same
  acquire -> extract -> verify pipeline locally, stands at their own promotion
  gate, and gets a graph extension with honest, machine-generated provenance.
- The frontier registry defines the boundary and makes it visible. Coverage is
  filer-weighted (SOI), so the core covers most returns while the long tail stays
  a contribution surface instead of a maintenance promise.

Why: avoids owning correctness forever for forms almost nobody files, avoids
staleness (currency) risk on the long tail, and keeps liability clean - the
Verification Record states exactly which witnesses ran and which are absent, so
a user-gated extension can never read as a project-verified form.

## End-user goals (what "practical" means)

These are acceptance targets for the eventual build. Each should hold for a
motivated end user who has never read this repo's source.

1. ONE-COMMAND SETUP CHECK. A single command (working name: `tax-graph extend
   doctor`) verifies config, keys, network reachability, and disk layout, and
   prints exactly what is missing and how to fix it. No source-diving to
   discover prerequisites.
2. MINIMAL, TEMPLATED CONFIG. Extension needs at most: Mistral OCR key, one
   LLM provider block (provider-agnostic per repo policy - no vendor default),
   and an optional second-family model for N-version. Ship a commented config
   template; `extend doctor` validates it.
3. ONE COMMAND PER FORM. `tax-graph extend <doc_id>` (working name) chains
   acquire -> render -> extract -> full M8 verification net -> review queue ->
   local promote. The user's decisions are confined to the review/accept step.
4. HUMAN GATE IN MINUTES. The user's promotion gate is a short review of
   flagged items plus the calibration sample, using the existing review.html.
   Target: the M10-measured per-form human-minutes, not hours. An explicit
   accept command performs the local promotion; nothing promotes silently.
5. HONEST PROVENANCE TIERS. A self-extracted form lands at a visibly distinct
   trust tier (machine ladder passed; no differential witness unless one
   exists; user-gated, not project-gated). The tier flows through the graph,
   the generated Verification Record, and every MCP response that touches the
   form's nodes, so a consuming AI always knows what it is standing on.
6. NO IMPERSONATION. Shipped graph artifacts are hash-stamped. Local
   extensions live in a separate overlay location and can never silently
   replace or blend into a shipped form's provenance.
7. GENERATIVE ESCAPE HATCH. When the engine hits an unresolved frontier
   dependency, the trace (CLI and MCP) names the missing form AND prints the
   exact extend command that would model it locally, plus the tier it would
   land at. The frontier registry is the user's map, not just ours.
8. UPSTREAM PATH. `tax-graph extend package` (working name) bundles the
   extension with its verification artifacts (metrics.yaml, drill results,
   example replays, N-version report, generated Verification Record) so a
   contribution PR is reviewable by replaying artifacts, not by a human
   re-deriving the form.
9. CURRENCY BY RE-EXTRACTION. Year-over-year form revisions are handled by
   re-running extend against the new-year PDF with delta verification, so
   users are never blocked waiting for the project to publish an update.
10. KEYLESS RUNTIME PRESERVED. Keys are needed only at extraction time.
    Running, explaining, and serving an extended graph over MCP stays
    zero-API-key, same as the shipped core.

## Non-goals

- Not a promise of correctness for user-extracted forms. The ladder without a
  differential witness is properties + completeness + N-version + mined IRS
  examples; the tier says so plainly.
- Not a hosted service. Everything runs locally under the single-binary /
  uv-CLI distribution posture.
- Not built now. No code, schema, or CLI surface changes until the post-M10
  planning pass; M10's per-form human-minutes data sizes goal 4.

## Open questions (for the flesh-out pass)

- Overlay mechanics: how a local extension composes with the shipped compiled
  SQLite at load time (separate DB attached? second graph dir merged at load?).
- Tier vocabulary: extend T0-T3 or add an orthogonal provenance axis
  (project-gated vs user-gated)?
- Witness discovery: can extend auto-detect an available differential witness
  (OTS fence membership, Direct File fact graph coverage) and wire it in?
- Where the shipped-artifact hash lives and what verifies it.
- Whether `extend` is a new CLI namespace or flags on existing commands.
