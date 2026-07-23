# AGENTS.md

Standing instructions for any agent working in this repository. **Read this first**, then the
master plan at `docs/engineering-plan.md`. This file is canonical for roles, the Worker directive,
and the hard rules.

**Ownership (to avoid write-collisions):** the **Architect** maintains this file and the plans/docs.
The **Worker** records active status and questions in `plans/AGENT_HANDOFF.md`, not here. Keep all
coordination in committed text files - no hidden side channels.

## Roles (Architect / Worker split)
- **Architect (Claude Opus):** planning and decomposition only. Writes/updates plans in `plans/`
  and `docs/`. Does NOT write implementation code.
- **Worker (Codex / Sonnet / Gemini):** implements one whole phase at a time from `plans/`.

## Worker directive (one whole phase per session)
1. Open the lowest-numbered phase in `plans/` not marked `[COMPLETE]`. State its Canary, wait for
   John's go, note the session context % (warn if low).
2. Work the steps in order WITHOUT stopping between them. Each step: implement core logic +
   create/update the pytest + update docstrings/docs; not done until tests pass 100%; mark `[DONE]`,
   log deviations, `git commit` (one per step; do not push yet).
3. Stop and surface to John ONLY on a problem (tests stuck, real ambiguity, a decision the plan
   does not cover, a plan-changing deviation, low context). Otherwise keep going.
4. At phase end: run the exit-criteria command (100%), mark `[COMPLETE]`, move the subplan to
   `plans/archive/`, then a single `git push`, and report.

Global project canary: **Ledger Llama**.

## Hard rules (do not violate)
- **Work out of the local-disk clone** (John names the path at session start). That is the
  canonical working copy - the `.venv` and reliable `.git` live there. An SMB-mapped network
  drive (Mac share) is NOT for dev work: it goes stale and git over SMB is unreliable (proven
  in practice). Do not read, edit, or commit under a mapped network path unless John gives
  specific instructions to. If a session starts under one, or under any path that is not the
  local clone, say so and switch before doing any work; treat anything found there as stale.
- **ASCII-only** in every authored file (docs/plans/config/code/data/graph labels/docstrings). Use
  "-" not em/en dashes, "->" not arrows, "Section" not the section sign, straight quotes.
  `tools/check_ascii.py` enforces it (CI gate).
- **Provider-agnostic LLM:** no privileged vendor; the extraction/reasoning LLM is pluggable via
  `llm.provider` with no silent default. Mistral OCR (OCR stage) is the only deliberate exception.
  The example config defaults to `openrouter`, a vendor-neutral gateway.
- **Drafts are never auto-merged and never committed.** LLM extraction output goes to
  `graph/<year>/_drafts/` (gitignored). Promotion into the live graph requires the FULL
  machine witness set green; under the **deferred-review policy (John, 2026-07-08)** the
  human review of a promotion diff may be DEFERRED to a committed review queue instead of
  blocking - with honest pending-review provenance, never asserted as reviewed. No agent
  ever writes `human_confirmed: true` or any equivalent human-review claim on the human's
  behalf; deferral is recorded, review happens later in the review workbench.
- **Runtime stays light:** build-time deps (pymupdf, mistralai, httpx, LLM clients) live in
  `pyproject` extras, never base; a runtime command must not import them.
- **IRS line numbers are the spine:** nodes are keyed on them; they drive extraction chunking and
  completeness checks.

## Coordination
- Active Claude <-> Codex coordination lives in **`plans/AGENT_HANDOFF.md`** - one living ledger
  (latest status, open questions, tests run, next slice). Do NOT spawn new per-topic note files.
- When you finish a meaningful slice: update the handoff with what changed, tests run, and what
  remains; phrase questions as concrete interface/behavior questions; prefer file paths + test
  commands over prose.
- Pin durable architecture decisions into the relevant `plans/PHASE_<id>.md`; keep transient
  implementation notes in the handoff.

## Map
- Master plan + phase gates/canaries: `docs/engineering-plan.md`
- Per-phase subplans: `plans/PHASE_<id>.md`
- Testing rules: `docs/testing-strategy.md`
- Original spec: `docs/tax_graph_requirements.md`
