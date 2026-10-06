#!/usr/bin/env bash
# Deterministic code-graph refresh (AST only, no LLM). Never blocks the agent.
# Usage: graphify-update.sh [--filter-code]   (reads hook JSON on stdin when --filter-code)
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
command -v graphify >/dev/null 2>&1 || exit 0

if [ "$1" = "--filter-code" ]; then
  payload=$(cat)
  printf '%s' "$payload" | grep -Eqi '\.(py|ts|tsx|js|jsx|mjs|cjs|json|sh|go|rs|java|css)"' || exit 0
  printf '%s' "$payload" | grep -Eqi 'graphify-out|node_modules|\.claude[\/\]+worktrees' && exit 0
fi

mkdir -p graphify-out
touch graphify-out/.hook_dirty
# Single runner: if one is active, it will see the dirty flag and run again.
mkdir graphify-out/.hook_lock 2>/dev/null || exit 0
(
  trap 'rmdir graphify-out/.hook_lock 2>/dev/null' EXIT
  while [ -f graphify-out/.hook_dirty ]; do
    rm -f graphify-out/.hook_dirty
    sleep 5
    graphify update . >> graphify-out/hook.log 2>&1
  done
) >/dev/null 2>&1 &
disown 2>/dev/null
exit 0
