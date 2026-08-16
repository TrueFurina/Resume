# Physics Lab Reschedule System - One-click starter (PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File start.ps1
# Note: Keep this file ASCII-only to avoid encoding issues in Windows PowerShell 5.1

$ErrorActionPreference = "SilentlyContinue"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Physics Lab Reschedule System - Starter" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# 1. Check backend
$backendRunning = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($backendRunning) {
    Write-Host "[OK] Backend already running (8000)" -ForegroundColor Green
} else {
    Write-Host "[..] Starting backend (FastAPI :8000)..." -ForegroundColor Yellow
    Start-Process -FilePath "C:\Users\Lenovo\miniconda3\python.exe" `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000" `
        -WorkingDirectory "E:\Program\physics-scheduler-agent\backend" -WindowStyle Hidden
    Start-Sleep -Seconds 5
    Write-Host "[OK] Backend started" -ForegroundColor Green
}

# 2. Check frontend
$frontendRunning = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($frontendRunning) {
    Write-Host "[OK] Frontend already running (5173)" -ForegroundColor Green
} else {
    Write-Host "[..] Starting frontend (Vite :5173)..." -ForegroundColor Yellow
    Start-Process -FilePath "D:\Node.js\npm.cmd" `
        -ArgumentList "run", "dev" `
        -WorkingDirectory "E:\Program\physics-scheduler-agent\frontend" -WindowStyle Hidden
    Start-Sleep -Seconds 8
    Write-Host "[OK] Frontend started" -ForegroundColor Green
}

# 3. Verify
Start-Sleep -Seconds 2
try {
    $backendOk = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 3 -UseBasicParsing
    if ($backendOk.StatusCode -eq 200) { Write-Host "[OK] Backend http://localhost:8000 ready" -ForegroundColor Green }
} catch { Write-Host "[WARN] Backend not responding" -ForegroundColor Red }

try {
    $frontendOk = Invoke-WebRequest -Uri "http://localhost:5173" -TimeoutSec 3 -UseBasicParsing
    if ($frontendOk.StatusCode -eq 200) { Write-Host "[OK] Frontend http://localhost:5173 ready" -ForegroundColor Green }
} catch { Write-Host "[WARN] Frontend not responding" -ForegroundColor Red }

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Done! Open in browser: http://localhost:5173" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
