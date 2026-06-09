# Expert Room - Windows Startup Script

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Expert Room - Windows Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ProjectDir "backend"
$FrontendDir = Join-Path $ProjectDir "frontend"

Write-Host "[1/6] Checking Conda environment..." -ForegroundColor Yellow
try {
    & conda activate Test 2>$null
    if ($LASTEXITCODE -ne 0) { throw "conda activate failed" }
    Write-Host "[OK] Conda 'Test' activated" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Cannot activate Conda 'Test'" -ForegroundColor Red
    Write-Host "Create it first: conda create -n Test python=3.11" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "[2/6] Checking Python..." -ForegroundColor Yellow
try {
    python --version
    Write-Host "[OK] Python available" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "[3/6] Checking Node.js..." -ForegroundColor Yellow
try {
    node --version
    npm --version
    Write-Host "[OK] Node.js available" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Node.js not found" -ForegroundColor Red
    Write-Host "Install Node.js 18+: https://nodejs.org/" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "[4/6] Installing backend dependencies..." -ForegroundColor Yellow
Set-Location $BackendDir

if (-not (Test-Path "requirements.txt")) {
    Write-Host "[ERROR] requirements.txt not found" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] pip install failed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Backend dependencies installed" -ForegroundColor Green

if (-not (Test-Path ".env")) {
    Write-Host "[INFO] Creating .env from .env.example..." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "[OK] .env created" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "[5/6] Initializing database..." -ForegroundColor Yellow
try {
    python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
    Write-Host "[OK] Database initialized" -ForegroundColor Green
} catch {
    Write-Host "[INFO] Database may already exist, continuing..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[6/6] Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location $FrontendDir

if (-not (Test-Path "package.json")) {
    Write-Host "[ERROR] package.json not found" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

if (-not (Test-Path "node_modules")) {
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] npm install failed" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "[SKIP] node_modules exists" -ForegroundColor Yellow
}
Write-Host "[OK] Frontend dependencies installed" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Starting backend..." -ForegroundColor Yellow
$backendCmd = "Set-Location '$BackendDir'; conda activate Test; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Write-Host "Waiting for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host "Starting frontend..." -ForegroundColor Yellow
$frontendCmd = "Set-Location '$FrontendDir'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All Services Started!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Press any key to open browser..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "To stop: close the backend and frontend PowerShell windows" -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to exit"