$ErrorActionPreference = "Stop"
Write-Host "Starting SmartAirAware FastAPI Backend..." -ForegroundColor Cyan

if (Test-Path ".\venv\Scripts\Activate.ps1") {
    . .\venv\Scripts\Activate.ps1
}

uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
