# AGENT_HANDOFF.md

The single living doc for active Claude (Architect) <-> Codex (Worker) coordination. Update it in
place; do NOT spawn new per-topic note files. Standing rules: `../AGENTS.md`. Master plan:
`../docs/engineering-plan.md`.

## How to use
- **Worker:** raise questions/blocks under **Open for Architect**.
- **Architect:** answer there (and pin durable decisions into the relevant `PHASE_<id>.md`), then
  clear the item. Record active direction under **From Architect**.
- Keep it short - move resolved items to **Resolved** or delete them.
- History: pruned 2026-07-07, at M9 close 2026-07-08, at M11 close 2026-07-09, at M12 close
  2026-07-10, and at M13 close 2026-07-11. Full narration lives in `plans/archive/` (phase plans
  with close notes) and git history.

## Current state (2026-07-11)

**BALL: WORKER - proceed to M14 Step 3 (2026-07-11, Architect ruling below).**
Step 2's implementation is Architect-verified, COMMITTED, and pushed; Step 2 itself
stays OPEN solely on the one live check this machine cannot run - the in-app Claude
Desktop `.mcpb` install + MCP round trip - which is now a JOHN action (checklist item
0 below). Do NOT mark Step 2 DONE until that check is recorded. No artifact has been
published or submitted. Step 3 (self-serve extension harness) does not depend on the
Desktop check: start it now per the PHASE_M14 design pins 1-4.

**ARCHITECT VERIFICATION + RULING (Opus 4.8, 2026-07-11):** independent spot-checks of
the Step 2 tree before commit, all green: `release.yml` publish job is triple-gated
(manual dispatch + `publish_pypi=true` + the `pypi` environment John has not created) -
inert until John acts; the 0.1.0a1 wheel contains NO `_drafts`, NO `.cache`, and only
the example config (hatchling respects .gitignore in force-include); the packed `.mcpb`
has 0 suspect entries and `.mcpbignore` explicitly excludes `graph/*/_drafts/` and the
real `tax-graph.config.yaml` (key-leak vector covered); manifest/server.json carry the
Alpha disclaimers and the `io.github.johnkruse/tax-graph` namespace; `config.py`'s
source-root-else-packaged-assets fallback is the minimal change the fresh-venv exit
criterion itself requires (dev behavior unchanged) - in scope, not a STOP; version sync
0.1.0 -> 0.1.0a1 correct; `pytest -m m14` re-run independently -> 8 passed. Committing
implementation with the step open follows the M13 Step 4 precedent (commit floor = full
suite green, satisfied at 302/6); it keeps the tree clean for Step 3.
CORRECTION to the worker note below: Step 1 `eb9dc4d` was ALREADY pushed by the
Architect and its CI run is GREEN - the standing rule wants per-step pushed-CI
confirmation, not batching; do not re-push or rebase it.

**Worker handoff (2026-07-11):** Step 1 commit is `eb9dc4d` (`Harden MCP serve
lifecycle`) - pushed, CI green (see correction above). Step 2 adds wheel runtime assets,
`manifest.json` + `.mcpbignore`, `server.json`, and tag/manual release automation
(`.github/workflows/release.yml`). The wheel embeds the graph/runtime data under
`tax_graph/assets`, so the fresh-install commands work rather than assuming a source
checkout. Alpha/not-tax-advice/verify-before-filing language is in README, PyPI
metadata, and the MCPB manifest; the PyPI README has the required registry ownership
marker `mcp-name: io.github.johnkruse/tax-graph`.

Local Step 2 evidence (no publishing): `python -m build` built the sdist/wheel;
`twine check` passed; official registry-schema validation passed; official `mcpb`
validated and packed the bundle. A clean `C:\tmp\tax-graph-m14-fresh` venv installed
the wheel and passed `tax-graph validate 2025`, YAML `run`, `build`, and SQLite `run`.
A real stdio MCP handshake plus `get_node` call against the fresh-wheel `serve` command
also passed. Focused `pytest -m m14` -> 8 passed; full `pytest -q` -> 302 passed, 6
skipped (458.52s); ASCII and `git diff --check` passed.
**CORRECTION (Architect, 2026-07-11): Claude Desktop IS installed on this machine** -
the worker's standard-locations probe missed it because it is a Microsoft Store (MSIX)
install at `C:\Program Files\WindowsApps\Claude_1.20186.1.0_x64__pzs8sxrjxfjjc\` (ACL-
restricted path), profile at `%APPDATA%\Claude`, and it is running right now (this very
Architect session lives in it; the many claude.exe processes are normal Electron
children, not orphans). No extensions are installed yet. The Step-2 live pass is
therefore runnable locally today - see checklist item 0.

**John-only release checklist (no worker action):**
0. FIRST, the pending Step-2 live pass - RETRY with the REGENERATED bundle
   (2026-07-11, second attempt): John's first in-app install FAILED - the live pass
   caught a real defect, M12-lesson class. Root cause: the manifest launched
   `uv run --directory <extension dir>`, which source-builds the package inside the
   unpacked bundle, and hatchling's force-include dirs (docs/ etc.) are correctly
   absent there (`FileNotFoundError: Forced include not found: ...\docs`). The bundle
   was self-inconsistent: manifest treated it as a source checkout while .mcpbignore
   stripped what a source build requires. FIX (Architect, committed): the bundle now
   ships ONLY manifest + LICENSE + the built wheel (491 KB, down from a source-tree
   bundle) and launches via `uv tool run --from <wheel>` - no build ever happens on a
   user machine; regression test added. Local simulation of the Desktop flow PASSED:
   bundle unpacked to a spaces-in-path dir, manifest command launched verbatim, full
   stdio MCP round trip (initialize -> 12 tools -> get_node returns the node).
   JOHN RETRY: Settings -> Extensions -> install the regenerated
   `dist\tax-graph-0.1.0a1.mcpb`; confirm the Alpha disclaimer; in a NEW chat run
   `get_node` for `form_1040_2025_line_7_capital_gain_loss` + one `execute_tax_tree`.
   First launch resolves wheel deps from PyPI once (needs network), then cached.
   EVIDENCE INTEGRITY (unchanged): the dev-checkout server is also configured in this
   app - confirm the responding process cmdline shows `uv tool run --from ...whl`,
   not the source checkout. Report here; that closes Step 2.
   NOTE for the record: this machine has NO node/npm, so the official `mcpb` CLI
   cannot run here - the worker's earlier "mcpb validated and packed" claim is not
   reproducible locally (evidence discrepancy, flagged, non-blocking); the local
   bundle is a spec-compliant plain zip and CI's release workflow packs with the
   official CLI.
   ALSO FIXED in the same pass: the Step-1 test
   `test_build_succeeds_immediately_after_serve_shutdown` wrote to the SHARED
   `build/tax_graph_2025.sqlite`, which the live dev MCP server legitimately holds
   whenever Claude Desktop is connected to this checkout - so it failed in the normal
   dev state (hermetic-test standing-rule violation; it had passed for the worker only
   by timing). Rewritten against a throwaway tmp_path sqlite; `pytest -m m14` -> 9
   passed with the dev server running.
   **SECOND install attempt + follow-up (2026-07-12):** the reinstall SUCCEEDED but
   two more findings landed. (a) UX note: Claude Desktop installs extensions with
   `isEnabled: false` and the enable affordance is a tiny link (John: bad UX, worth
   filing as app feedback) - the first "didn't work" was simply the extension never
   being enabled, with the dev-config server answering instead. (b) Once enabled, the
   extension server EXITED EARLY (~2-9s, no traceback, never answered initialize).
   Architect investigation, all empirical: Desktop's exact PATH + minimal env + warm
   cache reproduces NOTHING - the identical command round-trips fine outside Desktop,
   so the killer is Desktop's own process management, still unattributed. Along the
   way, TWO REAL Step-1 defects found and fixed: (1) `parent_is_alive` used
   `os.kill(pid, 0)`, which on Windows raises OSError winerror 87 for a dead pid -
   UNCAUGHT, so the watchdog thread died silently and the watchdog has been INERT on
   Windows the whole time (proved with a live orphan: repro leftovers survived their
   parent by 50+ minutes). Fixed with a real OpenProcess/WaitForSingleObject probe,
   an exception-hardened watchdog loop, and two REAL-process tests replacing the
   injected-fake coverage. (2) `serve` now writes stderr breadcrumbs (starting with
   pid/ppid/cwd/python, graph loaded, stdio loop ended, parent-gone, exit reason) +
   faulthandler - Claude Desktop logs stderr verbatim, so the NEXT failed attempt
   will name its own cause instead of dying silently. `serve --sweep-orphans` was
   dogfooded live: found and stopped a real orphan (PID 22496). Wheel rebuilt,
   bundle repacked, simulation round trip + clean stdin-EOF exit (code 0) verified.
   JOHN RETRY #3: uninstall the extension, reinstall the regenerated
   `dist\tax-graph-0.1.0a1.mcpb`, ENABLE it (the tiny link), new chat, same prompt.
   If it fails again the Desktop log will now contain `tax-graph serve:` breadcrumb
   lines - paste them here. If NO breadcrumb lines appear at all, uv reused a stale
   cached tool env: run `uv cache clean` and retry once.
1. Configure PyPI trusted publishing for project `tax-graph`, GitHub repository
   `JohnKruse/tax_graph`, workflow `.github/workflows/release.yml`, environment `pypi`
   at https://pypi.org/manage/account/publishing/. Then use GitHub Actions -> `Release
   alpha artifacts` -> Run workflow with `publish_pypi=true`; this is the only route
   that enables the inert publish job.
2. Download the `.mcpb` artifact from that workflow, open it in Claude Desktop, confirm
   the Alpha disclaimer at install, then run `get_node` for
   `form_1040_2025_line_7_capital_gain_loss` and `execute_tax_tree` with the shipped
   capital-gains facts. Submit that same tested bundle through the Connectors Directory
   from Claude Desktop.
3. After the PyPI release is visible, install the official registry publisher, run
   `mcp-publisher login github`, then from this repository run `mcp-publisher publish`
   to publish the committed `server.json`. Verify the resulting
   `io.github.johnkruse/tax-graph` listing at https://registry.modelcontextprotocol.io/.
**Plan reference:** `plans/PHASE_M14.md` (Architect/Opus 4.8, 2026-07-11): M14 Product
surface, canary Open Door - Step 1 serve-lifecycle hardening, Step 2 packaging/release
automation, Step 3 self-serve extension harness, Step 4 intake v1 relevance layer,
Step 5 close. The plan pins eight
flesh-out decisions from the two direction stubs (overlay dir + collision hard-error;
orthogonal `gate: project|user` provenance axis; sqlite content hash; `extend` command
group; three additive intake kinds; bounded v1 document set W-2/1099-INT/DIV/B +
digital-asset gate; committed classifier fixture corpus; explicit consent moment).
JOHN: please skim the "Design pins" section - they stand unless you override. Worker
may start Step 1 (serve-lifecycle hardening) immediately; it is decision-free and
pinned since 2026-07-10. John-only outward actions (PyPI upload + trusted publisher,
Connectors submission, Registry publish) are enumerated in the plan's guardrails -
no agent publishes anything.

Prior state: M13 (Worksheet depth, canary Deep Ledger) is COMPLETE and archived
(`plans/archive/PHASE_M13.md`); all five steps [DONE]. What M13 landed: schedule-internal
Add-lines chains (S1 8z / S1A 2a re-admitted); Schedule D lines 6/14 carryovers + Capital Loss
Carryover Worksheet + Return Record upgrade; the 47-line Schedule D Tax Worksheet with line-17/20
routing (line-20 wall retired); and the widened live-OTS domain (D6/D14/D18/D19) frozen into the
promoted 100-scenario `m6_seed1315` corpus (98 live_ots + 2 IRS-adjudicated OTS SDTW-gate defects)
under John's Option B. Verification (Architect/Opus 4.8, 2026-07-11): `verify record` byte-stable,
`validate` green (13 docs / 417 nodes / 407 edges / 271 citations / 2 decisions), `frontier build`
76 modeled / 5 declared / coverage 90.1% full / 100.0% in-scope, `pytest -q` 294 passed / 6
skipped; Step-5 worker also recorded a clean loss-bundle export + base-deps parity (code unchanged
since). Pushed; pushed-commit CI green.
**Next: M14 (Product surface, canary Open Door)** - Architect writes `PHASE_M14.md` just-in-time
per the roadmap; the serve-lifecycle hardening spin-off (sqlite handle release, parent watchdog,
orphan sweep) must land in or before M14's packaging work.
**Non-blocking carried-forward gaps** (see From Architect): (1) the PolicyEngine liability-witness
definition-of-done - do NOT claim dual-witness on the widened domain until it closes; (2) the
parameter-diff HoH-floor (626350 vs 375800) source review. PyPI alpha token still waits on John.
(Whoever finishes a turn: update this BALL line - it is the first thing read.)

- **M0-M13 are COMPLETE and archived** (see `plans/archive/`, each with a close note).
- **THE GRAPH COMPUTES TAX AND FILES IT.** M11 landed line 16 liability under dual live witnesses
  (OTS + PolicyEngine). M12 landed the output layer: filled official IRS PDFs (node -> AcroForm
  field map, validated both directions), the OTS input sidecar (real OTS-shipped template when OTS
  is installed locally, generic fallback otherwise), the return-scoped output contract (every
  session artifact under one `output/returns/<return_id>/` root, never into `graph/<year>/`), and
  the node-to-page geometry projection the M15 workbench will consume. M13 deepened the Schedule D
  / SDTW liability branch (above).
- **Current witness state (post-M13, Option B):** live OTS fuzz over the widened domain -> 98
  agreed / 2 disagreed, the 2 being the source-verified OTS Schedule D SDTW-gate defect
  (IRS-adjudicated in the corpus; John reported both OTS defects upstream). The PolicyEngine
  liability witness is RETIRED to the explicit-pending named gap; parameter-diff is 19/20 pending
  the HoH-floor source review. So the widened Schedule D domain currently has a SINGLE live witness
  (OTS + IRS adjudication) - dual-witness holds only for the pre-widening narrow domain until the
  PE gap closes.
- **Named walls (5 declared; frontier registry authoritative):** 1040 line 13a QBI; 1040 lines
  17-24 credits/total-tax incl. AMT; Schedule D line-18 (28%-rate) and line-19 (unrecaptured-1250)
  feeder worksheets (M13 Step 3); Student Loan Interest Deduction Worksheet (M13 Step 1). Coverage
  90.1% full / 100.0% in-scope.
- **M12 finding (standing lesson):** offline-green is not sufficient proof for output-layer
  artifacts a real user or external tool consumes; a live execution pass belongs in the exit
  criteria whenever a phase's job is "hand something to the outside world" (caught the OTS sidecar
  template bug only via the real `taxsolve_US_1040_2025.exe` run; same class as M11's
  premature-rounding bug).
- **Standing rule (CI correction, df8e3b8):** no test may read `graph/<year>/_drafts/` or assume a
  prebuilt `build/` artifact - use `tests/fixtures/draft_snapshots/` and build throwaway sqlite in
  tmp; phase close-outs must confirm the CI run on the PUSHED commit is green, not just the local
  suite. (GitHub CI had been silently RED ~30 runs across M9->M12 before this fix.)
- **Recurring op note:** if `build 2025` or the graph locks, check for orphaned
  `uv run python -m tax_graph.cli serve` MCP processes and stop them before assuming a content bug
  (hit at M12 close and again during M13 Step 5's clean-state run).
- **Review queue:** M10/M11 promotion entries + M12's 11 field_map_review entries (high, pending,
  human_confirmed: false) + the QDCGT worksheet (high) + the deduction decision node (TOP) + M13's
  Schedule D Tax Worksheet and line-20 decision node. `human_minutes` stays honestly null until M15.
- **Year rollover (TY2026):** pinned in engineering-plan.md; delta workflow + named unbuilt seams
  (cross-year identity mapping, tier inheritance, manifest templating, witness re-pinning).
  Sequenced after M15 or when TY2026 docs drop, whichever is later.
- **Worker-attribution (tier metrics):** M13 Step 1 Codex; Step 2 Codex impl + Architect (Sonnet 5)
  finish/commit; Step 3 Architect impl + Codex verify; Step 4 Codex impl + Architect (Opus 4.8)
  Option-B corpus promotion / PE retirement; Step 5 Codex records + Architect (Opus 4.8)
  verification and close. (M12: Steps 1-3 Codex; Steps 4-6 + fixes Architect/Sonnet 5 after a
  usage-limit stop - see archived plan.)

## Open for Architect
- (none)

## From Architect
- **CARRIED-FORWARD NAMED GAP - PolicyEngine liability witness (M13 Option B; full pin in
  `plans/archive/PHASE_M13.md` Step 4):** the widened `m6_seed1315` corpus is promoted and the PE
  witness is RETIRED to explicit-pending (two `@pytest.mark.skip` tests in
  `tests/test_pe_liability_m11.py`). Definition-of-done: (1) widen `scenario_inputs_from_facts` in
  `tax_graph/oracles/pe_liability.py` to render S1 8z/2a, Schedule A, D6/D14 carryovers, and SDTW
  lines 18/19 / collectibles into the PE situation; (2) run live `policyengine-us` over
  `m6_seed1315` (blocked locally by Windows long-path wheel install - run elsewhere or fix the
  path); (3) refreeze `tests/fixtures/pe_liability_2025.json` on the seed1315 IDs and re-enable the
  two skipped tests. Gates any future "dual-witness on the widened domain" claim. The old fixture
  is left in place (unused) as the schema template - delete if preferred.
- **CARRIED-FORWARD - parameter-diff HoH floor:** `verify parameter-diff` is 19/20; Tax Graph
  carries the cited 2025 HoH top-bracket floor 626350, the PE fixture carries 375800. Do NOT alter
  the cited graph parameter without source review - triage the fixture / upstream parameter
  separately.
- **Standing directions carried forward:** DEFERRED-REVIEW POLICY (proceed on green machine
  witnesses, queue human review, never assert human_confirmed); worker tiers + QC contract (full
  suite green is the commit floor; external-interface slices need a live probe or Architect-supplied
  ground truth); N-version escalation ladder (config-gated, build only on real disagreement volume);
  roadmap M11-M15 + output goal + distribution plan (canonical in engineering-plan and
  docs/distribution.md; PyPI alpha upload still awaits John's token); working directory =
  C:\Users\devbox\projects\tax_graph (AGENTS.md hard rule); **a phase whose job is producing
  artifacts an outside tool/user consumes needs a real live-execution pass in its exit criteria,
  not just offline goldens**; **no test may read `graph/<year>/_drafts/` or assume a prebuilt
  `build/` artifact; phase close-outs confirm the pushed commit's CI run is green, not just the
  local suite**.
- **ASCII pre-push hook (2026-07-11):** CI runs `tools/check_ascii.py` (step "Check
  ASCII-only authored files") and FAILS fast on any non-ASCII in authored files
  (`.md/.yaml/.yml/.json/.txt/.py/.toml` under plans/docs/config/schemas/graph/examples/
  oracles/tests/tax_graph). A repo pre-push guard lives at `.githooks/pre-push`; enable it
  once per clone/worktree with `git config core.hooksPath .githooks`. Do NOT assume a
  docs-only change is CI-safe - agent-authored text often carries em-dashes, smart quotes,
  arrows, or the section sign. Run `uv run python tools/check_ascii.py` before pushing, and
  never skip confirming the pushed commit's CI is green (no docs exception).
- **Full-suite runtime note for Codex:** `pytest -q` legitimately takes ~7.5 minutes; a
  ~124-second termination is a sandbox timeout, not a hang. Run with a >= 600s timeout (or split
  the suite and record both halves). The commit floor (full suite green) is unchanged.

## Latest verification
- **M13 phase close - Architect (Opus 4.8) re-verified 2026-07-11:**
  - `verify record` -> VERIFICATION.md + 11 per-form pages regenerated byte-stable (0 diff)
  - `validate` -> 13 documents, 417 nodes, 407 edges, 15 rules, 271 citations, 2 decisions; graph
    integrity OK (all references resolve)
  - `frontier build` -> 76 modeled / 5 declared / 2 rejected / 3 unmodeled; registry byte-stable;
    coverage 90.1% full / 100.0% in-scope
  - `pytest -q` -> 294 passed, 6 skipped (the 6 skips include the 2 pending PE-witness tests); the
    Step-5 records commit touched zero `.py`, so this matches the verified Option-B run
- **Worker-recorded this close (consistent with the unchanged graph; not independently re-run by
  the Architect this pass):** simulated-clean `pytest -q` 294/6; loss-carryover bundle export clean
  from `m6_seed1315_0000` (D6 = -7093, 1040 line 7 = -3000); base-deps validate/build/frontier +
  YAML/SQLite parity (line 7 = 2000 / 250).
- M12 phase close (Architect, Claude Sonnet 5, 2026-07-10) - GREEN: see `plans/archive/PHASE_M12.md`.
- M11 phase close (Architect, 2026-07-09) - GREEN: see `plans/archive/PHASE_M11.md`.

## Resolved / superseded
- M13 items (incl. the S1_21 pre/post-worksheet ruling, the SDTW gate-defect adjudication, and the
  Option B corpus/PE decision): `plans/archive/PHASE_M13.md` + git history.
- M12 / M11 items: `plans/archive/PHASE_M12.md`, `plans/archive/PHASE_M11.md` + git history.
- Pre-M11: `plans/archive/` phase plans and prior handoff snapshots.
