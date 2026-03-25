# 量化研究平台启动脚本 (独立窗口版)
# 每个服务在单独的窗口中运行，方便查看日志

param(
    [ValidateSet("dev", "prod")]
    [string]$Mode = "prod",
    [switch]$SkipDocker
)

$ProjectRoot = $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 量化研究平台启动中..." -ForegroundColor Cyan
Write-Host " 模式: $Mode" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan

# 1. 启动 Docker
if (-not $SkipDocker) {
    Write-Host "[1/3] 启动 Docker 基础设施..." -ForegroundColor Green
    docker compose -f "$ProjectRoot\docker\compose\docker-compose.infra.yml" up -d
    Start-Sleep -Seconds 2
}

# 2. 启动后端 (新窗口)
Write-Host "[2/3] 启动后端 API..." -ForegroundColor Green
$backendCmd = @"
cd '$ProjectRoot\backend'
`$env:PYTHONPATH = '.;..'
`$env:PYTHONUTF8 = '1'
Write-Host '后端 API 启动中...' -ForegroundColor Green
& '$ProjectRoot\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
Read-Host 'Press Enter to exit'
"@
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# 3. 启动前端 (新窗口)
Write-Host "[3/3] 启动前端..." -ForegroundColor Green
if ($Mode -eq "prod") {
    $frontendCmd = "cd '$ProjectRoot\frontend'; Write-Host '前端构建并启动中...' -ForegroundColor Green; npm run preview; Read-Host 'Press Enter to exit'"
} else {
    $frontendCmd = "cd '$ProjectRoot\frontend'; Write-Host '前端开发服务器启动中...' -ForegroundColor Green; npm run dev; Read-Host 'Press Enter to exit'"
}
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " 启动完成！" -ForegroundColor Green
Write-Host " 后端 API: http://127.0.0.1:8000" -ForegroundColor White
Write-Host " 前端页面: http://127.0.0.1:5173" -ForegroundColor White
Write-Host " API 文档: http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`n关闭各窗口即可停止对应服务" -ForegroundColor Yellow
