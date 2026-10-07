# setup.ps1 — one-shot setup for the hybrid origami pipeline (Windows PowerShell)
#
# Run from the anveshan repo root:
#   .\research\origami_hybrid\setup.ps1
#
# What it does:
#   1. Initialises + updates git submodules (FoldingAgent + FoldingAgentSimulator)
#   2. Installs FoldingAgentSimulator in editable mode
#   3. Installs FoldingAgent in editable mode (picks up local simulator)
#   4. Installs hybrid pipeline Python dependencies
#   5. Prints next steps

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = (Resolve-Path "$ScriptDir\..\..").Path

Write-Host "=== Hybrid Origami Pipeline Setup ===" -ForegroundColor Cyan
Write-Host "Repo root: $RepoRoot"
Write-Host ""

# 1. Submodules
Write-Host "[1/4] Initialising git submodules..." -ForegroundColor Yellow
Set-Location $RepoRoot
git submodule update --init --recursive research/origami_hybrid/vendor/FoldingAgent
git submodule update --init --recursive research/origami_hybrid/vendor/FoldingAgentSimulator
Write-Host "      Done." -ForegroundColor Green

# 2. Install simulator
Write-Host "[2/4] Installing FoldingAgentSimulator (editable)..." -ForegroundColor Yellow
python -m pip install -e "$ScriptDir\vendor\FoldingAgentSimulator" --quiet
Write-Host "      Done." -ForegroundColor Green

# 3. Install FoldingAgent
Write-Host "[3/4] Installing FoldingAgent (editable)..." -ForegroundColor Yellow
python -m pip install -e "$ScriptDir\vendor\FoldingAgent" --quiet
Write-Host "      Done." -ForegroundColor Green

# 4. Hybrid pipeline deps
Write-Host "[4/4] Installing hybrid pipeline dependencies..." -ForegroundColor Yellow
python -m pip install "av>=13.0" pillow numpy pydantic python-dotenv "google-genai>=0.3" --quiet
Write-Host "      Done." -ForegroundColor Green

Write-Host ""
Write-Host "=== Setup complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Copy .env.example to .env and fill in your API keys:"
Write-Host "       Copy-Item '$ScriptDir\.env.example' '$ScriptDir\.env'"
Write-Host ""
Write-Host "  2. Set HYBRID_MODEL in .env (default: gemini-3.8-flash)"
Write-Host "     For FoldingAgent, set ANTHROPIC_API_KEY and export it:"
Write-Host "       `$env:ANTHROPIC_API_KEY = 'your-key'"
Write-Host ""
Write-Host "  3. Drop your origami video somewhere and run:"
Write-Host "       python '$ScriptDir\pipeline.py' extract-frames --video <video> --output data/origami/"
