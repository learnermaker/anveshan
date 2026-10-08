# Coding-agent token tools (Graphify, RTK, Ponytail)

Status: DECIDED 2026-10-08 (developer tooling only; not part of the product). This page covers the tokens our **coding agents** spend. For the Gemini tokens the **app** spends, see [token-economy.md](token-economy.md).

| Tool | Cuts | How | Claude Code | Kiro | Antigravity |
|---|---|---|---|---|---|
| [Graphify](https://github.com/Graphify-Labs/graphify) | input: re-reading files | a local code graph in `graphify-out/` (git-ignored); agents ask `graphify query/explain/path` before grepping | global skill + `.claude/settings.json` hooks keep the graph fresh ([graphify-update.sh](../../.claude/hooks/graphify-update.sh)) | [.kiro/steering/graphify.md](../../.kiro/steering/graphify.md) | [.agents/rules/graphify.md](../../.agents/rules/graphify.md), `/graphify` workflow |
| [RTK](https://github.com/rtk-ai/rtk) | input: command output | `rtk git/pytest/npm …` compresses output 60–90% | `PreToolUse` hook rewrites Bash commands (global `rtk init -g`) | no hook support: [steering](../../.kiro/steering/agent-tools.md) asks Kiro to prefix noisy commands with `rtk` | [rule](../../.agents/rules/antigravity-rtk-rules.md) (`rtk init --agent antigravity`; no hook) |
| [Ponytail](https://github.com/DietrichGebert/ponytail) | output: code and prose | always-on ruleset: reuse existing code, stdlib and installed deps; smallest complete change | plugin with a SessionStart hook | `~/.kiro/steering/ponytail.md` | `agy plugin install` |

## Set up a machine

Each developer runs this once (Windows PowerShell, from the repo root). It installs only from the official sources above and prints the two Claude Code commands it cannot run for you:

```powershell
powershell -ExecutionPolicy Bypass -File tools/setup-agent-tools.ps1
```

Then, in Claude Code, send these as two separate prompts and restart:

```text
/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail
```

Check: `graphify --version`, `rtk --version`, `rtk gain` (savings so far). In Claude Code, `/plugin` lists ponytail.

## Rules

- Project rules win. [AGENTS.md](../../AGENTS.md), the issue/PR contract, tests and doc updates are never skipped because Ponytail prefers short diffs; Ponytail itself keeps validation, security and accessibility.
- RTK only rewrites commands sent through the **Bash** tool. Claude Code's Read/Grep/Glob and its PowerShell tool are not compressed. When the full output matters (a failing test's traceback), run the command without `rtk`.
- Generated copies stay out of git: `graphify kiro install` writes the full skill to `.kiro/skills/graphify/` (git-ignored; the script regenerates it). Only the short steering, rule and workflow files are committed.
- Nothing here calls Gemini or sends repository content anywhere: Graphify's code graph is AST-only, RTK runs locally, Ponytail is a prompt.
