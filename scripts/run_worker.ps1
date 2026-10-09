$ErrorActionPreference = "Stop"
Write-Host "Starting SmartAirAware Background Worker..." -ForegroundColor Cyan

if (Test-Path ".\venv\Scripts\Activate.ps1") {
    . .\venv\Scripts\Activate.ps1
}

python -m worker.main
