# Start the local Playwright/Celery worker on Windows.
# Run from any directory: powershell -ExecutionPolicy Bypass -File .\workers\run-local-windows.ps1
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $repoRoot "backend"
$venvPython = Join-Path $backendPath "venv\Scripts\python.exe"

if (-not (Test-Path $backendPath)) {
    throw "Backend directory not found: $backendPath"
}

if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python was not found. Install Python 3.11+ and add it to PATH."
    }
    $python = $pythonCommand.Source
}

$env:PYTHONPATH = $backendPath
Set-Location $backendPath

if (-not (Test-Path ".env")) {
    Write-Warning "backend/.env was not found. Ensure DATABASE_URL, CELERY_BROKER_URL, and CELERY_RESULT_BACKEND are configured in the process environment or create backend/.env."
}

Write-Host "Starting local Playwright worker. Keep this window open while jobs run."
Write-Host "Worker concurrency: 1 (Windows solo pool)."
& $python -m celery -A app.worker.celery_app:celery_app worker --pool=solo --concurrency=1 --loglevel=INFO
exit $LASTEXITCODE
