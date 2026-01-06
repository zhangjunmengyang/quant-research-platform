# Quant Research Platform - Windows PowerShell 启动脚本
# 用法: .\scripts\quant.ps1 <命令> [模式]
# 命令: start, stop, restart, status, logs, healthcheck, clean, force-clean, help
# 模式: local, dev, prod (默认: prod)

param(
    [Parameter(Position=0)]
    [string]$Command = "help",

    [Parameter(Position=1)]
    [string]$Mode = "prod"
)

# 配置
$COMPOSE_DIR = "docker/compose"
$COMPOSE_PROD = "$COMPOSE_DIR/docker-compose.yml"
$COMPOSE_DEV = "$COMPOSE_DIR/docker-compose.dev.yml"
$COMPOSE_INFRA = "$COMPOSE_DIR/docker-compose.infra.yml"
$PID_DIR = ".pids"
$PORTS_TO_CLEAN = @(8000, 5173, 6789, 6790, 6791, 6792)

# 颜色输出
function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }

# 检查命令是否存在
function Test-Command {
    param($cmd)
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

# 检查端口是否被占用
function Test-PortInUse {
    param($port)
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    return $null -ne $conn
}

# 杀死占用端口的进程
function Stop-PortProcess {
    param($port)
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($conn) {
        $procIds = $conn.OwningProcess | Select-Object -Unique
        foreach ($procId in $procIds) {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}

# 帮助信息
function Show-Help {
    Write-Host @"
用法: .\scripts\quant.ps1 <命令> [模式]

模式:
  local    - 本机开发 (Python/Node 本地运行，仅 Docker 基础设施)
  dev      - Docker 开发 (全容器化，代码热重载)
  prod     - 生产环境 (全容器化，优化构建) [默认]

命令:
  start <模式>       - 启动服务
  stop <模式>        - 停止服务
  restart <模式>     - 重启服务
  status             - 查看所有服务状态
  healthcheck <模式> - 检查服务健康状态
  logs <模式>        - 查看日志
  clean              - 清理所有环境
  force-clean        - 强制清理
  help               - 显示帮助

示例:
  .\scripts\quant.ps1 start local   # 启动本地开发环境
  .\scripts\quant.ps1 stop local    # 停止本地开发环境
  .\scripts\quant.ps1 status        # 查看状态
  .\scripts\quant.ps1 logs local    # 查看日志

服务地址:
  前端:     http://localhost:5173 (local/dev) | http://localhost (prod)
  API:      http://localhost:8000
  API Docs: http://localhost:8000/docs
  MCP:      localhost:6789-6792
"@
}

# 检查工具
function Test-Tools {
    $missing = @()

    if (-not (Test-Command "docker")) { $missing += "Docker" }
    if (-not (Test-Command "uv")) { $missing += "uv" }
    if (-not (Test-Command "pnpm")) { $missing += "pnpm" }

    if ($missing.Count -gt 0) {
        Write-Err "缺少以下工具: $($missing -join ', ')"
        Write-Host "请参考 README.md 安装依赖"
        exit 1
    }

    # 检查 Docker 是否运行
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Docker 未运行，请先启动 Docker Desktop"
        exit 1
    }
}

# 安装依赖
function Install-Dependencies {
    Write-Info "检查依赖..."

    # Python 依赖
    if (-not (Test-Path ".venv")) {
        Write-Info "安装 Python 依赖..."
        uv sync --dev
    } else {
        Write-Info "同步 Python 依赖..."
        uv sync --dev 2>&1 | Select-String -NotMatch "^Resolved|^Audited|^$"
    }

    # 前端依赖
    if (-not (Test-Path "frontend/node_modules")) {
        Write-Info "安装前端依赖..."
        Push-Location frontend
        pnpm install
        Pop-Location
    }
}

# 检查端口
function Test-Ports {
    $occupied = @()
    foreach ($port in $PORTS_TO_CLEAN) {
        if (Test-PortInUse $port) {
            $occupied += $port
        }
    }

    if ($occupied.Count -gt 0) {
        Write-Warn "以下端口已被占用: $($occupied -join ', ')"
        $answer = Read-Host "是否自动清理这些端口? [y/N]"
        if ($answer -eq 'y' -or $answer -eq 'Y') {
            foreach ($port in $occupied) {
                Write-Info "清理端口 $port..."
                Stop-PortProcess $port
            }
            Start-Sleep -Seconds 1
        } else {
            Write-Err "已取消启动"
            exit 1
        }
    }
}

# 启动本地环境
function Start-Local {
    Test-Tools
    Install-Dependencies
    Test-Ports

    Write-Host ""
    Write-Host "=========================================="
    Write-Host "        启动本地开发环境"
    Write-Host "=========================================="
    Write-Host ""

    # 创建 PID 目录
    if (-not (Test-Path $PID_DIR)) {
        New-Item -ItemType Directory -Path $PID_DIR | Out-Null
    }

    # 启动基础设施
    Write-Info "[1/5] 启动基础设施 (PostgreSQL + Redis)..."
    docker compose -f $COMPOSE_INFRA up -d 2>&1 | Out-Null

    # 等待基础设施就绪
    Write-Info "等待数据库就绪..."
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        $pgReady = docker exec quant-postgres pg_isready -U quant 2>&1
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) {
        Write-Warn "数据库未能在预期时间内就绪，继续启动..."
    }

    # 设置环境变量
    $env:PYTHONPATH = "backend"
    $env:DATABASE_URL = "postgresql://quant:quant123@localhost:5432/quant"
    $env:REDIS_URL = "redis://localhost:6379"

    # 启动 API
    Write-Info "[2/5] 启动 API..."
    $apiJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        $env:PYTHONPATH = "backend"
        $env:PYTHONIOENCODING = "utf-8"
        $env:PYTHONUTF8 = "1"
        $env:DATABASE_URL = "postgresql://quant:quant123@localhost:5432/quant"
        $env:REDIS_URL = "redis://localhost:6379"
        uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend 2>&1
    }
    $apiJob.Id | Out-File "$PID_DIR/api.job"
    Start-Sleep -Seconds 3

    # 启动 MCP 服务
    Write-Info "[3/5] 启动 MCP 服务..."
    $mcpJobs = @()

    $factorJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        $env:PYTHONPATH = "backend"
        $env:PYTHONIOENCODING = "utf-8"
        $env:PYTHONUTF8 = "1"
        $env:DATABASE_URL = "postgresql://quant:quant123@localhost:5432/quant"
        $env:REDIS_URL = "redis://localhost:6379"
        uv run python -m domains.factor_hub.api.mcp.server 2>&1
    }
    $factorJob.Id | Out-File "$PID_DIR/mcp-factor.job"

    $dataJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        $env:PYTHONPATH = "backend"
        $env:PYTHONIOENCODING = "utf-8"
        $env:PYTHONUTF8 = "1"
        $env:DATABASE_URL = "postgresql://quant:quant123@localhost:5432/quant"
        $env:REDIS_URL = "redis://localhost:6379"
        uv run python -m domains.data_hub.api.mcp.server 2>&1
    }
    $dataJob.Id | Out-File "$PID_DIR/mcp-data.job"

    $strategyJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        $env:PYTHONPATH = "backend"
        $env:PYTHONIOENCODING = "utf-8"
        $env:PYTHONUTF8 = "1"
        $env:DATABASE_URL = "postgresql://quant:quant123@localhost:5432/quant"
        $env:REDIS_URL = "redis://localhost:6379"
        uv run python -m domains.strategy_hub.api.mcp.server 2>&1
    }
    $strategyJob.Id | Out-File "$PID_DIR/mcp-strategy.job"

    $noteJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        $env:PYTHONPATH = "backend"
        $env:PYTHONIOENCODING = "utf-8"
        $env:PYTHONUTF8 = "1"
        $env:DATABASE_URL = "postgresql://quant:quant123@localhost:5432/quant"
        $env:REDIS_URL = "redis://localhost:6379"
        uv run python -m domains.note_hub.api.mcp.server 2>&1
    }
    $noteJob.Id | Out-File "$PID_DIR/mcp-note.job"

    Start-Sleep -Seconds 2

    # 启动前端
    Write-Info "[4/5] 启动前端..."
    $frontendJob = Start-Job -ScriptBlock {
        Set-Location "$using:PWD/frontend"
        pnpm dev 2>&1
    }
    $frontendJob.Id | Out-File "$PID_DIR/frontend.job"
    Start-Sleep -Seconds 3

    # 健康检查
    Write-Info "[5/5] 验证服务状态..."
    Start-Sleep -Seconds 2
    Show-HealthcheckLocal

    Write-Host ""
    Write-Success "本地开发环境已启动"
    Write-Host ""
    Write-Host "  前端:     http://localhost:5173"
    Write-Host "  API:      http://localhost:8000"
    Write-Host "  API Docs: http://localhost:8000/docs"
    Write-Host ""
}

# 停止本地环境
function Stop-Local {
    Write-Info "停止本机服务..."

    # 停止 PowerShell Jobs
    Write-Info "[1/3] 停止后台任务..."
    Get-Job | Where-Object { $_.State -eq 'Running' } | Stop-Job
    Get-Job | Remove-Job -Force

    # 停止进程
    Write-Info "[2/3] 停止进程..."
    Get-Process -Name "python", "uvicorn", "node", "pnpm" -ErrorAction SilentlyContinue | Stop-Process -Force

    # 清理端口
    foreach ($port in $PORTS_TO_CLEAN) {
        Stop-PortProcess $port
    }

    # 停止 Docker 基础设施
    Write-Info "[3/3] 停止基础设施容器..."
    docker compose -f $COMPOSE_INFRA down 2>&1 | Out-Null

    # 清理 PID 文件
    if (Test-Path $PID_DIR) {
        Remove-Item "$PID_DIR/*.job" -Force -ErrorAction SilentlyContinue
    }

    Write-Success "本地开发环境已停止"
}

# 启动 Docker 开发环境
function Start-Dev {
    Test-Tools
    Test-Ports

    Write-Info "启动 Docker 开发环境..."
    docker compose -f $COMPOSE_DEV down --remove-orphans 2>&1 | Out-Null
    docker compose -f $COMPOSE_DEV up -d --build

    Write-Info "等待服务启动..."
    Start-Sleep -Seconds 10

    docker compose -f $COMPOSE_DEV ps
    Write-Success "Docker 开发环境已启动"
}

# 停止 Docker 开发环境
function Stop-Dev {
    Write-Info "停止 Docker 开发环境..."
    docker compose -f $COMPOSE_DEV down --remove-orphans --volumes 2>&1 | Out-Null
    Write-Success "Docker 开发环境已停止"
}

# 启动生产环境
function Start-Prod {
    Test-Tools
    Test-Ports

    Write-Info "启动生产环境..."
    docker compose -f $COMPOSE_PROD down --remove-orphans 2>&1 | Out-Null
    docker compose -f $COMPOSE_PROD up -d --build

    Write-Info "等待服务启动..."
    Start-Sleep -Seconds 10

    docker compose -f $COMPOSE_PROD ps
    Write-Success "生产环境已启动"
}

# 停止生产环境
function Stop-Prod {
    Write-Info "停止生产环境..."
    docker compose -f $COMPOSE_PROD down --remove-orphans 2>&1 | Out-Null
    Write-Success "生产环境已停止"
}

# 状态
function Show-Status {
    Write-Host "=== 本机服务 ==="

    # 检查 API
    if (Test-PortInUse 8000) {
        Write-Host "  API:          运行中" -ForegroundColor Green
    } else {
        Write-Host "  API:          未运行" -ForegroundColor Gray
    }

    # 检查 Frontend
    if (Test-PortInUse 5173) {
        Write-Host "  Frontend:     运行中" -ForegroundColor Green
    } else {
        Write-Host "  Frontend:     未运行" -ForegroundColor Gray
    }

    # 检查 MCP
    $mcpPorts = @{6789="Factor"; 6790="Data"; 6791="Strategy"; 6792="Note"}
    foreach ($port in $mcpPorts.Keys) {
        $name = $mcpPorts[$port]
        if (Test-PortInUse $port) {
            Write-Host "  MCP $($name):".PadRight(16) + "运行中" -ForegroundColor Green
        } else {
            Write-Host "  MCP $($name):".PadRight(16) + "未运行" -ForegroundColor Gray
        }
    }

    Write-Host ""
    Write-Host "=== Docker 容器 ==="
    docker compose -f $COMPOSE_INFRA ps 2>&1
    docker compose -f $COMPOSE_DEV ps 2>&1 | Select-String -NotMatch "no configuration file"
    docker compose -f $COMPOSE_PROD ps 2>&1 | Select-String -NotMatch "no configuration file"
}

# 本地健康检查
function Show-HealthcheckLocal {
    $failed = $false

    # API
    Write-Host -NoNewline "  API .............. "
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-Host "OK" -ForegroundColor Green
    } catch {
        Write-Host "FAIL" -ForegroundColor Red
        $failed = $true
    }

    # Frontend
    Write-Host -NoNewline "  Frontend ......... "
    if (Test-PortInUse 5173) {
        Write-Host "OK" -ForegroundColor Green
    } else {
        Write-Host "FAIL" -ForegroundColor Red
        $failed = $true
    }

    # MCP 服务
    $mcpPorts = @{6789="Factor"; 6790="Data"; 6791="Strategy"; 6792="Note"}
    foreach ($port in $mcpPorts.Keys) {
        $name = $mcpPorts[$port]
        Write-Host -NoNewline "  MCP $name ".PadRight(19, '.')
        Write-Host -NoNewline " "
        if (Test-PortInUse $port) {
            Write-Host "OK" -ForegroundColor Green
        } else {
            Write-Host "FAIL" -ForegroundColor Red
            $failed = $true
        }
    }

    if ($failed) {
        Write-Host ""
        Write-Warn "部分服务异常"
    }
}

# 查看日志
function Show-Logs {
    param($mode)

    switch ($mode) {
        "local" {
            # 收集所有 Job 的最新输出
            $jobs = Get-Job | Where-Object { $_.State -eq 'Running' -or $_.HasMoreData }

            if ($jobs.Count -eq 0) {
                Write-Warn "没有运行中的后台任务"
                return
            }

            # 显示每个服务的日志
            foreach ($job in $jobs) {
                $jobId = $job.Id
                $jobName = switch -Wildcard ($job.Command) {
                    "*uvicorn*" { "API" }
                    "*factor*" { "MCP-Factor" }
                    "*data*" { "MCP-Data" }
                    "*strategy*" { "MCP-Strategy" }
                    "*note*" { "MCP-Note" }
                    "*pnpm*" { "Frontend" }
                    default { "Job-$jobId" }
                }

                Write-Host ""
                Write-Host "=== $jobName (Job $jobId, $($job.State)) ===" -ForegroundColor Cyan

                $output = Receive-Job -Id $jobId -Keep -ErrorAction SilentlyContinue
                if ($output) {
                    # 只显示最后 20 行
                    $lines = $output -split "`n" | Select-Object -Last 20
                    $lines | ForEach-Object { Write-Host $_ }
                } else {
                    Write-Host "  (暂无输出)" -ForegroundColor Gray
                }
            }

            Write-Host ""
            Write-Host "提示: 使用 Ctrl+C 退出，或运行 'Receive-Job -Id <JobId> -Keep' 查看完整日志" -ForegroundColor Yellow
        }
        "dev" {
            docker compose -f $COMPOSE_DEV logs -f
        }
        default {
            docker compose -f $COMPOSE_PROD logs -f
        }
    }
}

# 强制清理
function Clear-Force {
    Write-Info "强制清理所有进程和端口..."

    Write-Info "[1/3] 停止所有后台任务..."
    Get-Job | Stop-Job -ErrorAction SilentlyContinue
    Get-Job | Remove-Job -Force -ErrorAction SilentlyContinue

    Write-Info "[2/3] 清理端口..."
    foreach ($port in $PORTS_TO_CLEAN) {
        Stop-PortProcess $port
    }

    Write-Info "[3/3] 清理 Docker 容器..."
    docker compose -f $COMPOSE_INFRA down --remove-orphans --volumes 2>&1 | Out-Null
    docker compose -f $COMPOSE_DEV down --remove-orphans --volumes 2>&1 | Out-Null
    docker compose -f $COMPOSE_PROD down --remove-orphans 2>&1 | Out-Null

    # 停止所有 quant 相关容器
    $containers = docker ps -aq --filter "name=quant-" 2>&1
    if ($containers) {
        docker stop $containers 2>&1 | Out-Null
        docker rm -f $containers 2>&1 | Out-Null
    }

    # 清理 PID 目录
    if (Test-Path $PID_DIR) {
        Remove-Item $PID_DIR -Recurse -Force -ErrorAction SilentlyContinue
    }

    Write-Success "强制清理完成"
}

# 主逻辑
switch ($Command.ToLower()) {
    "start" {
        switch ($Mode.ToLower()) {
            "local" { Start-Local }
            "dev" { Start-Dev }
            default { Start-Prod }
        }
    }
    "stop" {
        switch ($Mode.ToLower()) {
            "local" { Stop-Local }
            "dev" { Stop-Dev }
            default { Stop-Prod }
        }
    }
    "restart" {
        switch ($Mode.ToLower()) {
            "local" { Stop-Local; Start-Sleep -Seconds 2; Start-Local }
            "dev" { Stop-Dev; Start-Sleep -Seconds 2; Start-Dev }
            default { Stop-Prod; Start-Sleep -Seconds 2; Start-Prod }
        }
    }
    "status" {
        Show-Status
    }
    "healthcheck" {
        switch ($Mode.ToLower()) {
            "local" { Show-HealthcheckLocal }
            default { Write-Info "Docker 健康检查暂未实现" }
        }
    }
    "logs" {
        Show-Logs $Mode
    }
    "clean" {
        Stop-Local
        Stop-Dev
        Stop-Prod
    }
    "force-clean" {
        Clear-Force
    }
    default {
        Show-Help
    }
}
