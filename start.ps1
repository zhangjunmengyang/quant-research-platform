<#
.SYNOPSIS
    Quant Platform Launcher
.PARAMETER Mode
    dev = hot reload, prod = production build
.PARAMETER SkipDocker
    Skip Docker startup
#>
param(
    [ValidateSet("dev", "prod")]
    [string]$Mode = "prod",
    [switch]$SkipDocker
)

# Set UTF-8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
chcp 65001 | Out-Null

$ProjectRoot = $PSScriptRoot

Write-Host "========================================"
Write-Host " Quant Platform Starting..."
Write-Host " Mode: $Mode"
Write-Host "========================================"

# 1. Start Docker
if (-not $SkipDocker) {
    Write-Host "`n[1/3] Starting PostgreSQL + Redis..."
    docker compose -f "$ProjectRoot\docker\compose\docker-compose.infra.yml" up -d
    Write-Host "Waiting for database..."
    Start-Sleep -Seconds 3
} else {
    Write-Host "`n[1/3] Skip Docker"
}

# 2. Start Backend API (new window)
Write-Host "`n[2/3] Starting Backend API (port 8000)..."
$backendScript = @"
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
`$env:PYTHONUTF8 = '1'
`$env:PYTHONPATH = '.;..'
`$env:PYTHONIOENCODING = 'utf-8'
Set-Location '$ProjectRoot\backend'
Write-Host 'Backend API starting...' -ForegroundColor Green
& '$ProjectRoot\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
"@
$backendProc = Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendScript -PassThru

# 3. Start Frontend (new window)
Write-Host "`n[3/3] Starting Frontend (port 5173)..."
if ($Mode -eq "prod") {
    $frontendCmd = "npm run preview"
} else {
    $frontendCmd = "npm run dev"
}
$frontendScript = @"
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location '$ProjectRoot\frontend'
Write-Host 'Frontend starting ($Mode mode)...' -ForegroundColor Magenta
$frontendCmd
"@
$frontendProc = Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendScript -PassThru

Write-Host "`n========================================"
Write-Host " Started!" -ForegroundColor Green
Write-Host " Backend:  http://127.0.0.1:8000"
Write-Host " Frontend: http://127.0.0.1:5173"
Write-Host " API Docs: http://127.0.0.1:8000/docs"
Write-Host "========================================"
Write-Host "`nTwo new windows opened for Backend and Frontend."
Write-Host "Close those windows to stop services."
Write-Host "Or run: .\stop.ps1"
