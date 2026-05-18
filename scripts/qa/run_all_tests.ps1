# Run all tests (single-terminal runner)
# Usage: powershell -NoProfile -File .\scripts\qa\run_all_tests.ps1

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
Write-Output "Project root: $projectRoot"

# --- Frontend: Playwright E2E ---
Push-Location (Join-Path $projectRoot 'frontend')
Write-Output "==> Running Playwright E2E tests (frontend)"
if (-not (Test-Path 'node_modules')) {
    Write-Output "node_modules missing, running npm ci..."
    npm ci
}
$npxCmd = 'npx playwright test --project=chromium --reporter=list'
Write-Output "Executing: $npxCmd"
Invoke-Expression $npxCmd
$playwrightExit = $LASTEXITCODE
Write-Output "Playwright exit code: $playwrightExit"
Pop-Location

# --- Backend: Python tests ---
Write-Output "==> Locating Python interpreter (searching for .venv)"
$pythonExe = $null
$searchDir = $projectRoot
while ($searchDir -and ($searchDir -ne [System.IO.Path]::GetPathRoot($searchDir))) {
    $candidate = Join-Path $searchDir '.venv\Scripts\python.exe'
    if (Test-Path $candidate) { $pythonExe = $candidate; break }
    $searchDir = Split-Path $searchDir -Parent
}
if (-not $pythonExe) {
    $fallback = 'C:\Users\2504690\Hack\\.venv\\Scripts\\python.exe'
    if (Test-Path $fallback) { $pythonExe = $fallback } else { $pythonExe = 'python' }
}
Write-Output "Using python: $pythonExe"

Push-Location $projectRoot
$pytestExit = 0
if (Test-Path 'tests') {
    Write-Output "==> Running pytest for repository (if available)"
    & $pythonExe -m pytest -q
    $pytestExit = $LASTEXITCODE
    Write-Output "pytest exit code: $pytestExit"
} else {
    Write-Output "No tests/ directory found; skipping pytest"
}

# --- Autonomous orchestrator (if present) ---
$autoExit = 0
$autoPath = Join-Path $projectRoot 'tests\AUTONOMOUS_LIFECYCLE_TEST.py'
if (Test-Path $autoPath) {
    Write-Output "==> Running AUTONOMOUS_LIFECYCLE_TEST.py"
    & $pythonExe $autoPath
    $autoExit = $LASTEXITCODE
    Write-Output "AUTONOMOUS_LIFECYCLE_TEST exit code: $autoExit"
} else {
    Write-Output "No AUTONOMOUS_LIFECYCLE_TEST.py found; skipping"
}
Pop-Location

# --- Summary ---
$failures = @()
if ($playwrightExit -ne 0) { $failures += "playwright:$playwrightExit" }
if ($pytestExit -ne 0) { $failures += "pytest:$pytestExit" }
if ($autoExit -ne 0) { $failures += "autotest:$autoExit" }

if ($failures.Count -eq 0) {
    Write-Output "\nALL TESTS PASSED"
    exit 0
} else {
    Write-Output "\nSOME TESTS FAILED: $($failures -join ',')"
    exit 1
}
