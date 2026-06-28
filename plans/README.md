# plans/ — working state for the Architect / Worker protocol

Filesystem-persisted plan state so a **fresh Worker session can resume without the original
context** (mitigates context degradation). Adapted from John's multi-agent protocol.

- **Master plan:** `../docs/engineering-plan.md` (phases M0–M6, gates, canaries, config).
- **Per-phase subplans:** `PHASE_<id>.md` here — generated **serially, one phase at a time**
  by the Architect at full resolution. Steps marked `[ ]` / `[DONE]`; a finished phase is
  marked `[COMPLETE]` and moved to `archive/`.
- **archive/** — completed subplans.

## Roles
- **Architect (Claude Opus):** plans only — no implementation code. Writes/updates these files.
- **Worker (Codex / Sonnet / Gemini):** implements one phase, one step at a time.

## Worker directive (start of a Worker session)
1. Open the lowest-numbered phase here not marked `[COMPLETE]`. **State its Canary and wait
   for confirmation** before doing anything. Remind me to check the session context %.
2. Take the first step not marked `[DONE]`.
3. Implement core logic **+** create/update pytest **+** update docstrings/docs.
4. You are not done until the step's tests pass 100%.
5. Mark the step `[DONE]`, log any deviations, then **git commit** with a real summary.
6. **Stop and ask permission** to proceed to the next step. Don't offer to do anything else.

Global project canary: **Ledger Llama**.
