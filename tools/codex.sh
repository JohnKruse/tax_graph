#!/usr/bin/env bash
# Architect-driven Codex Worker launch (John authorized 2026-08-19).
#
# WHY THIS WRAPPER EXISTS
#   codex.exe lives in a hash-named directory that changes on every Codex
#   update, so no literal path stays valid.  We resolve it from CODEX_CLI_PATH
#   in the user's own config.toml, which Codex keeps current.
#
# AUTHENTICATION - READ BEFORE CHANGING
#   Codex runs on John's ChatGPT Plus subscription, NOT on an API key.
#   Verified 2026-08-19: `codex login status` reports "Logged in using ChatGPT",
#   ~/.codex/auth.json carries auth_mode "chatgpt" with a null OPENAI_API_KEY
#   field, and config.toml has no model_provider/base_url/env_key override.
#   OPENAI_API_KEY IS present in the shell environment, for the PIPELINE's own
#   model calls, which are a separate spend line.  We strip it below so a Worker
#   round cannot reach it, whatever Codex's internal precedence would be.
#
#   TO PUT THE API KEY BACK (if the Plus subscription proves unworkable -
#   quota exhaustion, rate limits, refusals): delete the `env -u OPENAI_API_KEY`
#   from the exec line at the bottom of this file.  That is the whole change.
#   Codex then falls back to the environment key when the ChatGPT auth cannot
#   serve a request.  To switch back permanently instead, run
#   `printenv OPENAI_API_KEY | codex login --with-api-key`; return to the
#   subscription with `codex login` (browser flow).  Nothing in the repo other
#   than this one line depends on which way it is set.
#
# REASONING EFFORT
#   HIGH, not xhigh (John, 2026-08-19), matching the pipeline's
#   llm.reasoning_effort in tax-graph.config.yaml.  Set here rather than only in
#   config.toml so a Worker round is reproducible from the repo.
#
# ONE ROUND, ONE SESSION
#   John runs a fresh Codex session per coding cycle deliberately: the cycles are
#   discrete and stale context gums them up.  This wrapper NEVER resumes.  Round
#   state lives in plans/AGENT_HANDOFF.md, which is where the next session reads
#   it from.  Do not add `codex exec resume` here.
#
# USAGE
#   tools/codex.sh "<prompt>"
#   tools/codex.sh -o last.txt "<prompt>"     # extra flags pass through
set -euo pipefail

config="${CODEX_HOME:-$HOME/.codex}/config.toml"
if [ ! -f "$config" ]; then
  echo "codex.sh: no Codex config at $config" >&2
  exit 1
fi

exe="$(sed -n "s/^CODEX_CLI_PATH = '\(.*\)'\s*$/\1/p" "$config" | head -1)"
exe="${exe//\//}"
if [ -z "$exe" ]; then
  echo "codex.sh: CODEX_CLI_PATH not found in $config" >&2
  exit 1
fi
if [ ! -f "$exe" ]; then
  echo "codex.sh: resolved CLI does not exist: $exe" >&2
  exit 1
fi

exec env -u OPENAI_API_KEY "$exe" exec \
  --sandbox danger-full-access \
  --color never \
  -c model_reasoning_effort="high" \
  "$@"
