# plans/ - working state for the Architect / Worker protocol

Filesystem-persisted plan state so a **fresh Worker session can resume without the original
context** (mitigates context degradation). Adapted from John's multi-agent protocol.

- **Master plan:** `../docs/engineering-plan.md` (phases M0-M6, gates, canaries, config).
- **Per-phase subplans:** `PHASE_<id>.md` here - generated **serially, one phase at a time**
  by the Architect at full resolution. Steps marked `[ ]` / `[DONE]`; a finished phase is
  marked `[COMPLETE]` and moved to `archive/`.
- **archive/** - completed subplans.

## Roles
- **Architect (Claude Opus):** plans only - no implementation code. Writes/updates these files.
- **Worker (Codex / Sonnet / Gemini):** implements an entire phase, step by step - commit per step, push at the end.

## Worker directive (one whole phase per session)
1. Open the lowest-numbered phase here not marked `[COMPLETE]`. **State its Canary and wait
   for confirmation** before starting. Note the session context % (warn if it is getting low).
2. Then work the steps **in order, one at a time, continuing through the whole phase** - do NOT
   stop to ask between steps. For each step:
   - Implement core logic **+** create/update pytest **+** update docstrings/docs.
   - It is not done until the step's tests pass 100%.
   - Mark the step `[DONE]`, log any deviations, and **`git commit`** with a real summary
     (one commit per step). Do not push yet.
3. **Stop and surface to John only on a problem** - a step's tests cannot pass, a real
   ambiguity/blocker, a decision the plan does not cover, a deviation that changes the plan,
   or context running low. Otherwise keep going.
4. When all steps are `[DONE]`: run the phase **exit-criteria command** (must pass 100%), mark
   the phase `[COMPLETE]`, move the subplan to `archive/`, then **`git push`** once (a single
   push at the end of the phase) and report to John.

Global project canary: **Ledger Llama**.

## File format: ASCII-only (enforced)

All operational, planning, docs, and data files (plans/, docs/, config, schema
descriptions, graph YAML labels, Python docstrings) are **ASCII-only**. Use "-" not em/en
dashes, "->" not arrow glyphs, "Section" not the section sign, straight quotes, and plain
ASCII for diagrams. Unicode glyphs break PowerShell (cp1252), patch/diff tooling, and agent
handoffs. `tools/check_ascii.py` enforces this and must be a CI gate.
