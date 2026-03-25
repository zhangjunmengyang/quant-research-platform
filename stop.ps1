# 量化研究平台停止脚本

Write-Host "停止量化研究平台服务..." -ForegroundColor Yellow

# 停止后台任务
Get-Job -Name "Backend" -ErrorAction SilentlyContinue | Stop-Job -PassThru | Remove-Job
Get-Job -Name "Frontend" -ErrorAction SilentlyContinue | Stop-Job -PassThru | Remove-Job

# 停止 uvicorn 进程
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn*"
} | Stop-Process -Force -ErrorAction SilentlyContinue

# 停止 node 进程 (vite)
Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*vite*"
} | Stop-Process -Force -ErrorAction SilentlyContinue

# 停止 Docker 容器
$answer = Read-Host "是否同时停止 Docker 容器 (PostgreSQL/Redis)? [y/N]"
if ($answer -eq "y" -or $answer -eq "Y") {
    docker compose -f "$PSScriptRoot\docker\compose\docker-compose.infra.yml" down
    Write-Host "Docker 容器已停止" -ForegroundColor Green
}

Write-Host "服务已停止" -ForegroundColor Green
