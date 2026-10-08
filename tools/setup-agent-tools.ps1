# Install the coding-agent token tools for Claude Code, Kiro and Antigravity on this machine.
# What and why: docs/architecture/agent-tools.md. Safe to re-run. Official sources only.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

# Graphify: code graph (Claude hooks are already in .claude/settings.json)
if (-not (Have graphify)) { uv tool install graphifyy }
graphify install --platform claude   # ~/.claude/skills/graphify (the /graphify skill)
graphify kiro install          # .kiro/skills/graphify/ (git-ignored) + steering
graphify antigravity install   # .agents/rules, .agents/workflows

# RTK: compresses command output
if (-not (Have rtk)) {
  winget install --id rtk-ai.rtk -e --accept-source-agreements --accept-package-agreements
  $env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
}
rtk init -g --auto-patch                # Claude Code: PreToolUse hook in ~/.claude/settings.json
rtk init --agent antigravity            # Antigravity (project-scoped): .agents/rules/antigravity-rtk-rules.md
# Kiro has no RTK hook: .kiro/steering/agent-tools.md asks it to prefix commands with rtk.

# Ponytail: reuse-first, smallest-change ruleset
$kiroSteering = Join-Path $HOME '.kiro\steering'
New-Item -ItemType Directory -Force $kiroSteering | Out-Null
Invoke-WebRequest 'https://raw.githubusercontent.com/DietrichGebert/ponytail/main/.kiro/steering/ponytail.md' -OutFile (Join-Path $kiroSteering 'ponytail.md')
if (Have agy) { agy plugin install https://github.com/DietrichGebert/ponytail }
elseif (Have gemini) { gemini extensions install https://github.com/DietrichGebert/ponytail }
else { Write-Warning 'Antigravity CLI (agy) not found: install Ponytail from Antigravity''s plugin UI.' }

Write-Host "`nDone. In Claude Code, send these as two separate prompts, then restart:"
Write-Host '  /plugin marketplace add DietrichGebert/ponytail'
Write-Host '  /plugin install ponytail@ponytail'
Write-Host 'Check: graphify --version; rtk --version; rtk gain'
