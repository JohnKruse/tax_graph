# PHASE M15 - Review Workbench + review campaign

**Canary:** Fresh Eyes
**Depends on:** M14 (product surface; the `gate: project|user` + tier provenance axis
that human-confirmed verdicts flip; a fully populated review queue), M12
(`graph/<year>/node_geometry.json` + `tax_graph.output.resolve_node_geometry`; the
pipeline's `review.html` self-report), M8 (the verification net - calibration sampling,
N-version, mined-example confirmation, and the "human minutes per promoted object"
metric this phase finally measures for real), M7 (frontier registry - the coverage
view is a projection of it), M6 (mined IRS worked examples), M5 (Return Record).
Direction stub this fleshes out: `docs/review-workbench.md`.
**Goal:** Build the standalone, human-facing review workbench against the FINAL
artifact shape; run the one review campaign that drains the deferred-review queue;
measure real `human_minutes` and escape rates; and upgrade trust tiers from pending to
human-confirmed with honest provenance. Roadmap context: engineering-plan "Roadmap
M11-M15". **THIS IS THE PRE-SHIP GATE: nothing is promoted as usable-stable until this
phase passes.** (The M14 alpha may be name-claimed on PyPI; stable waits here.)

## Why
Every phase to date has ended with machine-green verdicts and a queue entry that says,
honestly, `human_confirmed: false`. That honesty was the whole point - the project
never pretended a human had looked when none had. M15 is where the human finally
looks, at 30 queued objects spanning field maps, promotions, decisions, a worksheet,
an extension pilot, intake mining, and an N-version disagreement. Two things come out
of it that exist nowhere else yet: a real cost number (`human_minutes` per object,
which sizes the self-serve-extension "minutes not hours" promise and the whole
maintenance model) and a real trust number (escape rate - how often a human overrides
what the machine majority believed, which is the only honest basis for calling any
tier "human-confirmed"). Until both exist, "ship" is a guess.

## Supported profile (unchanged, with one gated exception)
No new modeled tax math and no new engine ops. The workbench is a read-only viewer over
durable artifacts; the campaign upgrades provenance, it does not expand coverage. THE
ONE EXCEPTION: a `pipeline-defect` verdict (below) licenses a fix + re-extract of the
affected object - that IS a content change, and it re-enters the normal
extract -> verify net and its own re-verification, exactly like any extraction. It is
not scope creep; it is the queue doing its job.

## Design pins (Architect, 2026-07-12 - flesh-out decisions from docs/review-workbench.md)
Pinned unless John overrides at plan review; a worker who finds one unworkable STOPS
and reports rather than improvising.
1. **Home = workspace member, NOT a separate repo.** The workbench lives in this repo
   under `workbench/` (or `tax_graph/workbench/` - worker's call) with an ENFORCED
   no-import boundary: a committed test fails if workbench code imports
   `tax_graph.extract`, `tax_graph.acquire`, or any pipeline internal. Objectivity is
   guaranteed by the artifact-only input contract + that lint, not by repo separation
   (over-engineering for alpha; a split repo can happen later without changing the
   contract).
2. **Input contract = published artifact formats ONLY.** The workbench reads the
   compiled SQLite graph, `node_geometry.json`, the source PDFs, draft directories,
   `review_queue/<year>/deferred_review.yaml`, `metrics.yaml`, N-version reports, and
   mined-example fixtures. Anything it needs that artifacts do not carry becomes an
   ADDITIVE field request on the pipeline side - the workbench never reverse-engineers
   pipeline internals. Direct file/SQLite reads for v1; MCP-client mode is a nice
   future dogfood, deferred.
3. **Rendering = prebaked page images.** PyMuPDF (already behind the `pdf` extra)
   rasterizes each form page to PNG at build time; the static bundle overlays two
   independent geometry layers on the image - AcroForm field rects and
   resolved-provenance anchors from `resolve_node_geometry`. NOT pdf.js (more moving
   parts, and a CDN/bundle concern against the no-external-CDN rule).
4. **Delivery = static-first, generated per form-year.** `review-workbench build
   --year 2025` emits a self-contained offline HTML bundle (zero API keys, no CDN,
   ASCII sources). A tiny `review-workbench serve` is the ESCAPE HATCH only if
   verdict write-back friction proves unworkable - do not build the server first.
5. **Decisions flow OUT as append-only verdict files, never as edits.** The workbench
   NEVER writes graph YAML, drafts, or the queue. It emits schema'd verdict YAML
   (`review_verdicts/<year>/*.yaml`) that a NEW pipeline command
   (`review apply-verdicts`) consumes - same pattern as `--confirm` on example mining.
   This read-only stance is what makes the tool's witness trustworthy; promotion
   mechanics stay where they already live.
6. **Verdict taxonomy (engineering-plan, pinned exactly):** every queue object reaches
   one terminal verdict - `confirmed` (machine result upheld; tier flips to
   human-confirmed), `pipeline_defect` (machine was wrong for a fixable reason ->
   fix + re-extract + re-verify; the object re-queues at the bottom), or
   `source_pathology` (the IRS source itself is the problem -> licenses a MARKED manual
   override carrying human provenance, never a silent graph edit). Every verdict
   records reviewer id, timestamp, `human_minutes`, and a required short reason for
   anything other than `confirmed`.
7. **`review.html` survives** as the pipeline's cheap self-report; the workbench is
   where human GATES happen. Not deleted, not merged.
8. **Two v1 workflows, chosen to fit the ACTUAL queue** (the doc's "pick two, defer
   the rest"): (a) **field-map + promotion confirmation** - the 20 field_map/promotion
   entries: highlight a box or region on the form, see the node/rule/citation/edges/
   tier it carries, confirm or flag; (b) **decision-node review** - the TOP-priority
   deduction-method decision and the Schedule D line-20 decision: the panel presents
   the options AND the escape hatch and the reviewer confirms the routing, never
   choosing for a filer. Mined-example confirmation and the coverage heatmap are
   deferred to backlog. EXCEPTION: any BLOCKING N-version disagreement (all families
   disagreed) MUST be surfaced for adjudication before ship - check whether the pinned
   Part I/II line-2 case is still live and either adjudicate it in-workbench or record
   it already resolved.

## Guardrails (do not drift)
- **No new engine ops, no new tax math** (except a `pipeline_defect` re-extract, which
  re-enters the normal net). The workbench is a viewer + a verdict emitter.
- **No-import boundary enforced by a committed test** (pin 1). The workbench must stay
  runnable and the pipeline must stay fully runnable WITHOUT the workbench - it is not
  part of CI's correctness path and not a taxpayer-facing UI.
- **Read-only stance absolute:** the workbench never mutates graph/drafts/queue;
  verdicts are the only output, applied by a separate CLI step.
- **Human provenance is never faked.** `human_confirmed` flips true ONLY through an
  applied verdict carrying a real reviewer id + timestamp + minutes. A
  `source_pathology` override is MARKED as such and carries the human's reason in the
  Verification Record and every MCP response that touches it. No agent may set
  `human_confirmed: true` - that is the one bit only a human earns.
- **Displays all three addressing vocabularies without conflating them** (physical row
  slots = display geometry; runtime instances = `<node>#<row_key>`; static ids flat).
- Unchanged law: ASCII (pre-push hook + CI); no external CDNs; provider-agnostic;
  offline/zero-key; hermetic tests (no `_drafts` reads, no shared `build/` artifact);
  close-out ordering `frontier build` then `verify record`; full suite green is the
  commit floor; **CI green on every pushed step commit and the phase close.**

## Exit criteria (must pass 100%)
- `pytest -m m15` green; full `pytest` green on a simulated clean checkout; ASCII OK;
  base-deps `validate`/`build`/`run`/`frontier` green; parity examples unchanged
  (line 7 = 2000 / 250); GitHub CI green on the pushed close commit; the no-import
  boundary test passes.
- **Workbench live pass:** `review-workbench build --year 2025` produces an offline
  bundle; highlight-to-inspect resolves a real form region to its nodes/rules/
  citations (verbatim)/edges/tier/queue-items on a real page via `resolve_node_geometry`;
  an unresolvable anchor is shown AS a finding, not hidden; both geometry layers
  overlay correctly; the two v1 workflows work end to end.
- **Verdict round-trip:** a verdict emitted by the workbench, applied by
  `review apply-verdicts`, updates the queue + (for confirmed) flips `human_confirmed`
  + tier in the graph, the Verification Record, and MCP responses; re-verify is
  byte-stable; a fabricated/edited verdict file fails validation loudly.
- **CAMPAIGN COMPLETE (John's, measured):** every one of the ~30 queue entries reaches
  a terminal verdict (`confirmed` | `pipeline_defect` fixed-and-re-verified |
  `source_pathology` marked); `human_minutes` recorded per object; escape rate computed
  (human overrides / reviewed) and recorded; the pinned BLOCKING N-version item
  adjudicated. Tier upgrades applied; the queue's honest `human_confirmed: false`
  entries become either confirmed or an explicit still-open item with a reason.
- **Ship-readiness ledger:** the two carried-forward machine-witness gaps (PolicyEngine
  liability witness; parameter-diff HoH floor 626350 vs 375800) and any residual alpha
  limitations are each either CLOSED or explicitly recorded as an accepted, documented
  alpha limitation with rationale - a single ledger that makes the stable-release
  decision auditable.
- Records regenerated byte-stable (frontier first); `docs/review-workbench.md`
  graduates from stub to as-built; measured tier metrics + escape rate written into the
  handoff and the Verification Record; queue reflects the campaign outcome.

## Steps

- [ ] **Step 1 [worker-heavy] - Workbench scaffold + artifact read layer + import
  boundary.** Create the `workbench/` member; implement read-only loaders over the
  published artifacts (SQLite graph, `node_geometry.json`, PDFs, drafts, queue,
  metrics, N-version reports, mined examples) using ONLY public schemas. Commit the
  no-import boundary test (fails if workbench imports any pipeline internal). No UI yet;
  this step is the honest read seam + its enforcement. Tests hermetic; docs.

- [ ] **Step 2 [worker-heavy] - Highlight-to-inspect + the two v1 workflows.** Prebake
  page PNGs (PyMuPDF); overlay AcroForm rects + resolved-provenance anchors via
  `resolve_node_geometry`; hit-test a clicked/dragged region against both layers; the
  side panel shows node ids/labels, rule shape, verbatim citations (clickable back to
  their own page region), the local in/out edge subgraph with cross-form targets named,
  tier + per-layer L0-L5 outcomes, open queue/N-version items, and mined examples
  touching the node. Wire the two pinned workflows (field-map/promotion confirm;
  decision review with options + escape hatch). Uncovered regions render as visible
  gaps. Static offline bundle via `review-workbench build`. Live pass per exit
  criteria. Docs.

- [ ] **Step 3 [worker-heavy] - Verdict schema + apply pipeline + tier propagation.**
  Schema the append-only verdict YAML (reviewer id, timestamp, human_minutes, verdict,
  reason, object ref, and for source_pathology the marked override + provenance);
  emit verdicts from the workbench; implement `review apply-verdicts` that consumes
  them and updates the queue, flips `human_confirmed` + tier for confirmed objects, and
  routes pipeline_defect objects back to re-extraction. Propagate human-confirmed tier
  through the graph, the Verification Record generator, and MCP responses (extends the
  M14 gate/tier plumbing). Round-trip + tamper-rejection tests. NO agent sets
  human_confirmed true. Docs.

- [ ] **Step 4 [HUMAN CAMPAIGN - John; worker instruments + prepares only] - Drain the
  queue, measure.** This step is NOT worker-completable: it is John (or a designated
  reviewer) using the workbench to reach a terminal verdict on all ~30 objects,
  including the BLOCKING N-version adjudication. The worker's job is to make it
  frictionless: pre-stage every queue object into the workbench, verify each opens to
  the right page region, instrument per-object `human_minutes` capture, and provide a
  one-command "apply today's verdicts + re-verify" loop. Deliverables OUT of this step:
  the applied verdicts, measured human_minutes per object, the computed escape rate,
  and the tier upgrades. Sequencing: Steps 1-3 must be closed and CI-green before this
  starts; a worker session pauses here and hands to John.

- [ ] **Step 5 [worker-light] - Records, ledger, docs, exit run, close.** Regenerate
  VERIFICATION.md + per-form pages (frontier first, byte-stable), now carrying real
  human-confirmed tiers + human_minutes; write the ship-readiness ledger (PE-witness
  gap, HoH floor, residual alpha limitations: each closed or accepted-with-rationale);
  graduate `docs/review-workbench.md` from stub to as-built; run every exit-criteria
  command including the simulated-clean pytest and the workbench live pass; update the
  BALL. NOT authorized: edits outside generated records, docs, the ledger, and the
  handoff.

When all steps are `[DONE]`: mark `[COMPLETE]`, archive to `plans/archive/`, prune
`plans/AGENT_HANDOFF.md`, single `git push`, CONFIRM CI GREEN on that push, tell John.
M15 passing is the pre-ship gate clearing: after it, the stable (non-alpha) release
per `docs/distribution.md` is unblocked, John runs the John-only distribution actions,
and the remaining roadmap item is the TY2026 year rollover (its own phase plan, when
TY2026 docs drop or after this close, whichever is later).
