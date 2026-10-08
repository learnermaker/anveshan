# start.ps1 — Anveshan local development launcher
#
# Usage:
#   .\start.ps1          interactive mode selection
#   .\start.ps1 mock     UI only, no backend, no API key needed  → http://localhost:5174
#   .\start.ps1 full     UI + backend service (requires .env)    → http://localhost:5173
#
# The Vite dev server proxies /api to http://localhost:8080 (the service).
# Override the target with ANVESHAN_API_PROXY if you run the service on a different port.

param([string]$Mode = "")

$Root   = $PSScriptRoot
$Python = "$Root\.venv\Scripts\python.exe"

function Write-Step { param($m) Write-Host "`n  $m" -ForegroundColor Cyan }
function Write-Ok   { param($m) Write-Host "  [ok] $m" -ForegroundColor Green }
function Write-Warn { param($m) Write-Host "  [!]  $m" -ForegroundColor Yellow }
function Write-Err  { param($m) Write-Host "  [x]  $m" -ForegroundColor Red }

Write-Host ""
Write-Host "  Anveshan — local launcher" -ForegroundColor White

# ── Mode selection ────────────────────────────────────────────────────────────
if (-not $Mode) {
    Write-Host ""
    Write-Host "  mock  UI only, recorded responses, no API key needed  (port 5174)" -ForegroundColor Gray
    Write-Host "  full  UI + backend service, .env with GEMINI_API_KEY  (UI :5173, API :8080)" -ForegroundColor Gray
    Write-Host ""
    $Mode = (Read-Host "  Mode [mock]").Trim().ToLower()
    if (-not $Mode) { $Mode = "mock" }
}
$Mode = $Mode.Trim().ToLower()
if ($Mode -notin @("mock", "full")) {
    Write-Err "Unknown mode '$Mode'. Use 'mock' or 'full'."
    exit 1
}

# ── Preflight checks ──────────────────────────────────────────────────────────
Write-Step "Checking prerequisites..."

if (-not (Test-Path $Python)) {
    Write-Err ".venv not found."
    Write-Host "       Run: python -m venv .venv" -ForegroundColor Gray
    Write-Host "            .venv\Scripts\pip install -r service\requirements.txt" -ForegroundColor Gray
    exit 1
}
Write-Ok ".venv  $Python"

if (-not (Test-Path "$Root\app\node_modules")) {
    Write-Err "app\node_modules not found. Run: cd app && npm install"
    exit 1
}
Write-Ok "node_modules  app\node_modules"

if ($Mode -eq "full") {
    if (-not (Test-Path "$Root\.env")) {
        Write-Err ".env not found. Copy .env.example to .env and fill in GEMINI_API_KEY."
        exit 1
    }
    $envContent = Get-Content "$Root\.env" -Raw -ErrorAction SilentlyContinue
    if ($envContent -notmatch 'GEMINI_API_KEY\s*=\s*\S') {
        Write-Warn "GEMINI_API_KEY appears empty in .env — live model calls will fail."
    } else {
        Write-Ok ".env  GEMINI_API_KEY present"
    }
    if (-not (Test-Path "$Root\var")) {
        New-Item -ItemType Directory -Path "$Root\var" | Out-Null
        Write-Ok "Created var/  (session and upload data)"
    } else {
        Write-Ok "var/  exists"
    }
}

# ── Launch processes ──────────────────────────────────────────────────────────
Write-Step "Launching '$Mode' mode..."

if ($Mode -eq "mock") {
    # UI only — no backend, all data is synthetic/recorded
    $uiCmd = "Set-Location '$Root\app'; Write-Host '  Anveshan UI (mock)' -ForegroundColor Cyan; npm run dev:mock"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $uiCmd

    Write-Host ""
    Write-Ok "UI window opened."
    Write-Host ""
    Write-Host "  Open  http://localhost:5174" -ForegroundColor White
    Write-Host ""
    Write-Host "  Recorded responses, no API key needed." -ForegroundColor Gray
    Write-Host "  To test with a real backend use: .\start.ps1 full" -ForegroundColor Gray
}

if ($Mode -eq "full") {
    # Backend — uvicorn on port 8080 (Vite proxy target)
    $svcCmd = "Set-Location '$Root'; Write-Host '  Anveshan service (port 8080)' -ForegroundColor Cyan; " +
              "& '$Python' -m uvicorn anveshan_service.main:app --app-dir service --host 127.0.0.1 --port 8080 --reload"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $svcCmd

    Write-Host "  Backend window opened — waiting 3 s for startup..." -ForegroundColor Gray
    Start-Sleep -Seconds 3

    # Frontend — Vite dev on port 5173, proxies /api → 8080
    $uiCmd = "Set-Location '$Root\app'; Write-Host '  Anveshan UI (dev, port 5173)' -ForegroundColor Cyan; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $uiCmd

    Write-Host ""
    Write-Ok "Service and UI windows opened."
    Write-Host ""
    Write-Host "  UI       http://localhost:5173" -ForegroundColor White
    Write-Host "  API docs http://localhost:8080/api/docs" -ForegroundColor White
    Write-Host ""
    Write-Host "  The UI proxies /api to the service automatically — no CORS config needed." -ForegroundColor Gray
    Write-Host "  Override the proxy target: set ANVESHAN_API_PROXY in your shell before running." -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Steward access: add ANVESHAN_STEWARD_TOKEN=<code> to .env, or set" -ForegroundColor Gray
    Write-Host "  ANVESHAN_STEWARD_OPEN=1 for local dev (no token check)." -ForegroundColor Gray
}

Write-Host ""
