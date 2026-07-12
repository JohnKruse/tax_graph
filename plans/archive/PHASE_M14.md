# PHASE M14 - Product surface

**[COMPLETE 2026-07-12]** All five steps done and verified; every exit criterion met,
each live pass run for real (fresh-venv wheel; in-app Claude Desktop .mcpb install +
MCP round trip, triple-witnessed - John's chat, the Architect's pre-verified local
engine run, and the Architect's own direct call to the extension server returning the
MFS loss-limit values -4500 / -1500 / -1500; registry schema; release-workflow CI dry
run with the publish job inert; form_2441 extension pilot; intake CLI example).
Notable in-phase findings, all pinned in the handoff/archive: the .mcpb source-build
defect (bundle now ships the wheel), the inert-Windows-watchdog defect (fixed +
real-process tests), the fabricated-intake-citations reopen (re-mined verbatim from
acquired sources; checker with teeth), the records/frontier hash-ordering rule, and
the Desktop UX hazards (install-disabled default, tiny enable link, twin-name
collision between a config dev server and the extension). John-only distribution
actions (PyPI trusted publishing + upload, Connectors submission, Registry publish)
carry forward as post-close actions - artifacts staged and verified.

**Canary:** Open Door
**Depends on:** M13 (worksheet depth; widened OTS corpus under Option B), M12 (output
layer; return-scoped artifacts; live-execution lesson), M10 (frontier registry +
batch pipeline the extension harness reuses), M8 (verification net the extension
harness reuses), M5 (Return Record - intake resolutions land there). Standing pins:
`docs/distribution.md` (channels, hard lines), `docs/self-serve-extension.md` and
`docs/intake.md` (direction stubs this phase fleshes out), serve-lifecycle hardening
(pinned 2026-07-10 - must land in or before the packaging step).
**Goal:** Turn the verified core into a product surface: (1) ship the alpha through
the pinned distribution channels with honest labeling; (2) build the self-serve
extension harness so any form outside the shipped core is a user-gated local
extension, never a support promise; (3) land intake v1 - the doc-drop relevance
layer that routes information-return boxes to graph lines with citations and asks
only what evidence did not resolve. Roadmap context: engineering-plan "Roadmap
M11-M15". Stable release still gates on M15.

## Why
The graph computes tax, files it, and defends the math (M11-M13). What it cannot do
yet is reach anyone: there is no installable artifact, no way for a user to extend
coverage past the shipped 13 documents without reading the repo source, and no way
to start a return from the shoebox of PDFs a real filer actually has. All three are
"open the door" problems, and all three have pinned direction docs waiting on a
build pass. Packaging goes first because every other channel references it and
because the serve-lifecycle bugs (orphaned MCP processes holding the sqlite lock -
bitten twice) become user-facing defects the moment strangers install the server.

## Supported profile (unchanged)
This phase adds NO new modeled tax math. The computation profile stays exactly
M13's. What changes is reach: packaging (install channels), extension (user-gated
coverage growth outside the core), and intake (document-driven fact entry INTO the
existing profile). Any tax-math gap discovered during this phase is frontier work
for a later phase, not scope creep here.

## Design pins (Architect, 2026-07-11 - flesh-out decisions from the two stubs)
These resolve the stubs' open questions for v1. They are pinned unless John
overrides at plan review; a worker who finds one unworkable STOPS and reports
rather than improvising.
1. **Overlay mechanics (extension):** a local extension is a SECOND graph directory
   (`graph_ext/<year>/<doc_id>/`, gitignored) merged at load time by the existing
   YAML loader path. ID collision with a shipped object is a HARD ERROR - no
   shadowing, no blending. Extensions are not compiled into the shipped sqlite;
   sqlite users get extensions via yaml-overlay load. Compiling extensions is
   deferred until demand exists.
2. **Provenance vocabulary (extension):** do NOT extend the T0-T3 ladder. Add an
   orthogonal axis `gate: project | user` carried on every extension object,
   flowing through the Verification Record and every MCP response that touches an
   extension node (stub goal 5). The ladder says how much machine verification ran;
   the gate says who stood at the promotion gate.
3. **No impersonation (extension):** the shipped compiled sqlite carries a content
   hash in a metadata table, stamped at build and checked at load; the generated
   Verification Record prints it. Extension objects render with their own hash and
   the `user` gate. A doctored artifact fails loudly at load.
4. **extend CLI shape:** a new `extend` command group - `extend doctor` (config/
   keys/network/layout check), `extend <doc_id>` (acquire -> render -> extract ->
   M8 net -> review queue -> explicit local accept), `extend package` (bundle the
   extension + its verification artifacts for a contribution PR). No silent
   promotion: `extend accept <doc_id>` is a separate, explicit act.
5. **Intake schema (relevance layer):** additive kinds in the SAME graph - routing
   edges (information-return box -> form line, cited from recipient instructions),
   trigger nodes (mined from Form 13614-C, each with an obligation class:
   universal_gate | conditional), expectation edges (claim -> expected evidence,
   v1 cardinality presence/absence only). Additive-schema law applies; any need
   beyond these three kinds is a STOP.
6. **Intake v1 document set (bounded):** W-2, 1099-INT, 1099-DIV, 1099-B - the
   information returns that feed the modeled profile - plus the 1040 digital-asset
   universal gate. Every box on these four becomes a routing edge or an explicit
   out-of-scope record (M8-style completeness). Pub 4012 / Pub 17 / who-must-file
   chart mining is EXPLICITLY deferred; 13614-C mining is bounded to universal
   gates plus the conditional triggers whose entry points exist in the modeled
   profile or frontier registry (each other item -> not_modeled record).
7. **Classifier verification story (intake):** classification is AI squish, so it
   gets the standard treatment: a committed labeled fixture corpus (synthetic
   PDFs, no real taxpayer data, hermetic), accuracy asserted in tests offline;
   live classification calls only the user's configured providers. N-version
   classification is config-gated OFF by default (escalation-ladder policy).
8. **Consent moment (intake):** before the first byte of a crawled document leaves
   the machine, the CLI states which provider receives it and requires an explicit
   yes (or a config `intake.consent: always` the user set themselves). Local crawl,
   remote OCR/LLM only - privacy stance unchanged.

## Guardrails (do not drift)
- **No new engine ops, no new tax math.** Intake's relevance layer and the
  extension harness are graph-shape and tooling work. STOP if a step seems to need
  either.
- **Additive schemas only;** the three intake kinds above are the whole allowance.
- **Keyless runtime preserved:** keys are needed only at extraction/intake-
  classification time. `serve`, `run`, `validate`, `explain` on shipped or extended
  graphs stay zero-API-key (stub goal 10).
- **Alpha honesty:** every distributed artifact (README, .mcpb manifest, first-run
  banner, PyPI description) carries the not-tax-advice / verify-before-filing
  disclaimer and the Alpha label. Stable is gated on M15 - nothing in this phase
  weakens that.
- **Hard lines from distribution.md:** no taxpayer data leaves the machine in any
  distributed configuration; hosted execution out of scope; e-file out of scope.
- **External-interface QC contract:** every artifact handed to an outside tool gets
  a REAL live pass - fresh-venv wheel install, real Claude Desktop .mcpb install,
  real registry schema validation - not just offline goldens (M11/M12 lesson,
  standing rule).
- **John-only outward actions:** the actual PyPI upload + trusted-publisher
  configuration, the Connectors Directory submission, and the MCP Registry publish
  are performed by John. Workers PREPARE and VERIFY artifacts; nothing is
  published, submitted, or uploaded by an agent.
- **Hermetic tests** (standing rule): no `_drafts` reads, no prebuilt-artifact
  assumptions; classifier fixtures are committed synthetic documents.
- **Deferred-review policy in force:** queue entries for the intake mining
  (trigger/routing extractions are extractions - they enter the ladder), the
  extension-harness pilot form, and every new decision surface.
- Unchanged law: ASCII (the pre-push hook + CI enforce it); drafts never committed;
  live graph closed; base-deps light; full suite green is the commit floor; **CI on
  the pushed commit must be green at every step commit and phase close**.

## Exit criteria (must pass 100%)
- `pytest -m m14` green; full `pytest` green on a simulated clean checkout; ASCII
  OK; base-deps `validate`/`build`/`run`/`frontier` green; parity examples
  unchanged (line 7 = 2000 / 250); GitHub CI green on the pushed close commit.
- **Serve lifecycle:** killing the parent of a `serve` session leaves no orphan
  process and no held sqlite lock (test + live probe); `build 2025` succeeds
  immediately after a serve session exits (regression on the 2026-07-10 incident).
- **Packaging live pass:** the built wheel installs into a FRESH venv (not the dev
  .venv) and `tax-graph validate/run/serve` work there keyless; the `.mcpb` bundle
  installs into a real Claude Desktop and a get_node + execute_tax_tree round trip
  succeeds; `server.json` validates against the official registry schema; the
  release workflow completes a dry run (build + twine check + hash stamp) in CI.
  Artifacts staged for John's upload with the John-only checklist written in the
  handoff.
- **Extension live pass:** one real IRS form OUTSIDE the shipped 13 documents
  (worker proposes a small one; Architect approves before extraction) goes through
  `extend doctor -> extend <doc_id> -> review -> extend accept` end to end
  locally; it loads as an overlay, computes, and every MCP response touching it
  carries `gate: user`; the frontier escape hatch prints the exact extend command
  for an unresolved dependency (stub goal 7); the impersonation test proves a
  hash-tampered artifact fails at load.
- **Intake live pass:** a doc-drop directory of synthetic W-2 + 1099-INT + 1099-DIV
  + 1099-B fixtures classifies, routes with citations, and produces a gap list via
  `list_required_inputs`; the completeness gate BLOCKS while a universal gate is
  unresolved and while a planted stray 1099-NEC is unreconciled (docs-without-
  claims); resolutions land in the Return Record with provenance; the consent
  moment fires before first egress.
- Both-direction completeness for intake v1: every box on the four document types
  is a routing edge or an explicit out-of-scope record; every 13614-C item in
  bounds is a trigger or a not_modeled record.
- Verification records regenerated byte-stable; frontier rebuilt (no coverage
  change expected - no new modeled math); queue entries present; disclaimers
  present in README, manifest, and first-run; handoff BALL updated.

## Steps

- [DONE] **Step 1 [worker-standard] - Serve-lifecycle hardening.** The pinned spin-off,
  landed first because packaging makes it user-facing: (a) sqlite handle release on
  server shutdown (context-managed connection lifecycle); (b) parent-process
  watchdog - a stdio MCP server whose parent dies exits itself within a bounded
  interval (implement portably; verify on Windows, where both incidents occurred);
  (c) an orphan sweep helper (`serve --sweep-orphans` or equivalent) that finds and
  stops abandoned serve processes, replacing the manual Get-CimInstance hunt.
  Tests: lifecycle unit tests plus a live kill-the-parent probe; regression:
  build-after-serve succeeds. Docs.

- [DONE] **Step 2 [worker-standard; closed 2026-07-12 after the in-app Desktop live
  pass finally ran clean - see the archive header for the three-witness evidence and
  the two real defects the live pass caught on the way] - Packaging + release
  automation.** Build on the
  prepared `0.1.0a1`: release workflow (tag-driven; build sdist+wheel; twine
  check; hash-stamp artifacts; PyPI trusted-publishing OIDC wiring ready but
  publish step inert until John configures the publisher); README + first-run +
  PyPI description carry the Alpha + disclaimer language; `.mcpb` bundle via mcpb
  init/pack with the disclaimer in the manifest; `server.json` for the MCP
  Registry referencing the PyPI package. Live passes per exit criteria (fresh
  venv, real Claude Desktop, registry schema). Deliverable to John: a short
  checklist of the three John-only actions with exact commands/links. STOP if any
  channel's mechanics demand a change to runtime behavior.

- [DONE] **Step 3 [worker-heavy] - Self-serve extension harness.** Implement design
  pins 1-4: overlay load with collision hard-error; `gate: project|user` axis
  through graph objects, Verification Record, and MCP responses; shipped-sqlite
  content hash stamped at build and checked at load; the `extend` command group
  (doctor / <doc_id> / accept / package) chaining the EXISTING acquire-extract-
  verify pipeline - this step wires and gates, it does not rebuild extraction.
  Frontier escape hatch: unresolved-dependency traces print the extend command and
  target tier. Pilot: one small real form end to end (worker proposes, Architect
  approves). Tests hermetic (pipeline stages mocked or replayed from committed
  fixtures; the live pilot is the live pass). Queue entries; docs update
  (`docs/self-serve-extension.md` graduates from stub to as-built).

- [DONE] **Step 4 [worker-heavy; reopened once by Architect review (fabricated
  citations, pin-6 completeness, missing queue entries) and closed after the
  re-mine passed independent re-verification - see AGENT_HANDOFF 2026-07-12] -
  Intake v1 relevance layer.** Implement design pins
  5-8: the three additive kinds; mine 13614-C (bounded per pin 6) and the four
  information returns' recipient instructions through the standard acquire ->
  extract -> verify net with citations; `intake` CLI (crawl -> consent -> classify
  -> route -> gap list -> completeness gate); classifier fixture corpus + offline
  accuracy tests; Return Record resolution provenance; MCP relevance queries so
  the AI asks only unresolved questions with citations in hand. Both-direction
  completeness enforced in `validate`. Live pass per exit criteria. Queue entries;
  docs update (`docs/intake.md` graduates from stub to as-built).

- [DONE] **Step 5 [worker-light] - Records, docs, exit run, close.** Regenerate
  VERIFICATION.md + per-form pages (byte-stable); rebuild frontier (coverage
  unchanged); run every exit-criteria command including the simulated-clean
  pytest and all four live passes' evidence collection; write the John-only
  distribution checklist into the handoff; update the BALL. NOT authorized:
  edits outside generated records, docs, and the handoff.

When all steps are `[DONE]`: mark `[COMPLETE]`, archive to `plans/archive/`, prune
`plans/AGENT_HANDOFF.md`, single `git push`, CONFIRM CI GREEN on that push, tell
John. Next per the pinned roadmap: M15 (Review Workbench + review campaign, canary
Fresh Eyes - the pre-ship gate). Carried-forward gaps that M15 must still see: the
PolicyEngine liability-witness definition-of-done and the parameter-diff HoH-floor
source review (both pinned in the handoff).
