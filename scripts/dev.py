#!/usr/bin/env python3
"""
跨平台本地开发环境管理器。

等价于 `make start/stop/status/logs local`，但不依赖 Unix 工具，
可在 Windows / macOS / Linux 上直接运行。

用法:
    uv run python scripts/dev.py start     # 启动所有服务
    uv run python scripts/dev.py stop      # 停止所有服务
    uv run python scripts/dev.py status    # 查看服务状态
    uv run python scripts/dev.py logs      # 查看最近日志
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
import webbrowser
import gzip
import shutil
from pathlib import Path

# ============================================
# 配置
# ============================================

IS_WIN = sys.platform == "win32"

ROOT = Path(__file__).resolve().parent.parent
PID_DIR = ROOT / ".pids"
COMPOSE_INFRA = ROOT / "docker" / "compose" / "docker-compose.infra.yml"
BACKUP_DIR = ROOT / "backups"
BACKUP_FILE = BACKUP_DIR / "quant_backup.sql.gz"

KILL_TIMEOUT = 5
HEALTH_RETRIES = 15
HEALTH_INTERVAL = 2

# 端口映射
PORTS = {
    "api": 8000,
    "frontend": 5173,
    "mcp-factor": 6789,
    "mcp-data": 6790,
    "mcp-strategy": 6791,
    "mcp-note": 6792,
    "mcp-research": 6793,
    "mcp-experience": 6794,
    "mcp-stock": 6795,
}

# 默认环境变量（与 Makefile _start_local 一致）
DEFAULT_ENV = {
    "PYTHONPATH": "backend",
    "DATABASE_URL": "postgresql://quant:quant123@localhost:5432/quant",
    "REDIS_URL": "redis://localhost:6379",
    "LOG_LEVEL": "INFO",
    "LOG_FORMAT": "json",
}

# 后台服务定义: (名称, 命令, cwd 相对于 ROOT)
BACKEND_SERVICES = [
    ("api", ["uv", "run", "uvicorn", "app.main:app",
             "--host", "0.0.0.0", "--port", "8000",
             "--reload", "--reload-dir", "backend"], None),
    ("mcp-factor", ["uv", "run", "python", "-m",
                     "domains.factor_hub.api.mcp.server"], None),
    ("mcp-data", ["uv", "run", "python", "-m",
                   "domains.data_hub.api.mcp.server"], None),
    ("mcp-strategy", ["uv", "run", "python", "-m",
                       "domains.strategy_hub.api.mcp.server"], None),
    ("mcp-note", ["uv", "run", "python", "-m",
                   "domains.note_hub.api.mcp.server"], None),
    ("mcp-research", ["uv", "run", "python", "-m",
                       "domains.research_hub.api.mcp.server"], None),
    ("mcp-experience", ["uv", "run", "python", "-m",
                         "domains.experience_hub.api.mcp.server"], None),
    ("mcp-stock", ["uv", "run", "python", "-m",
                    "domains.stock_hub.api.mcp.server"], None),
]

FRONTEND_SERVICE = ("frontend", ["pnpm", "dev"], "frontend")


# ============================================
# 工具函数
# ============================================


def info(msg: str) -> None:
    print(f"  {msg}")


def step(n: int, total: int, msg: str) -> None:
    print(f"  [{n}/{total}] {msg}")


def load_env() -> dict[str, str]:
    """构建子进程环境变量: 系统 env + .env 文件 + 默认值。"""
    env = dict(os.environ)
    # 默认值（最低优先级）
    for k, v in DEFAULT_ENV.items():
        env.setdefault(k, v)
    # .env 文件覆盖
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            # 处理 ${VAR} 引用
            if "${" in val:
                import re
                val = re.sub(
                    r"\$\{(\w+)\}",
                    lambda m: env.get(m.group(1), m.group(0)),
                    val,
                )
            if key:
                env[key] = val
    return env


def port_in_use(port: int) -> bool:
    """检查端口是否被占用。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def find_occupied_ports() -> list[str]:
    """列出当前已被占用的业务端口。"""
    return [
        f"{name}:{port}"
        for name, port in PORTS.items()
        if port_in_use(port)
    ]


def which(cmd: str) -> bool:
    """检查命令是否可用。"""
    import shutil
    return shutil.which(cmd) is not None


def read_pid(name: str) -> int | None:
    """读取 PID 文件。"""
    pid_file = PID_DIR / f"{name}.pid"
    if not pid_file.exists():
        return None
    try:
        pid = int(pid_file.read_text().strip())
        return pid if pid > 0 else None
    except (ValueError, OSError):
        return None


def write_pid(name: str, pid: int) -> None:
    """写入 PID 文件。"""
    PID_DIR.mkdir(exist_ok=True)
    (PID_DIR / f"{name}.pid").write_text(str(pid))


def is_alive(pid: int) -> bool:
    """检查进程是否存活。"""
    if IS_WIN:
        try:
            r = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
                capture_output=True, text=True, timeout=5,
            )
            return str(pid) in r.stdout
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def kill_pid(pid: int, force: bool = False) -> None:
    """终止进程（含子进程树）。"""
    if IS_WIN:
        # /T = 终止进程树, /F = 强制
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True, timeout=10,
        )
    else:
        sig = signal.SIGKILL if force else signal.SIGTERM
        try:
            os.killpg(os.getpgid(pid), sig)
        except OSError:
            pass


def spawn_background(name: str, cmd: list[str], cwd: Path, env: dict) -> int:
    """启动后台进程，返回 PID。"""
    log_file = PID_DIR / f"{name}.log"
    PID_DIR.mkdir(exist_ok=True)

    stdout = open(log_file, "a", encoding="utf-8")
    stderr = subprocess.STDOUT

    kwargs: dict = {
        "cwd": str(cwd),
        "env": env,
        "stdout": stdout,
        "stderr": stderr,
        "stdin": subprocess.DEVNULL,
    }

    if IS_WIN:
        # CREATE_NO_WINDOW 避免弹出控制台窗口
        # CREATE_NEW_PROCESS_GROUP 让子进程独立于父进程
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        )
        # Windows 上 pnpm/uv 等是 .cmd 文件，需要 shell=True
        kwargs["shell"] = True
        popen_cmd: str | list[str] = subprocess.list2cmdline(cmd)
    else:
        kwargs["start_new_session"] = True
        popen_cmd = cmd

    proc = subprocess.Popen(popen_cmd, **kwargs)
    write_pid(name, proc.pid)
    return proc.pid


def tail_file(path: Path, lines: int = 50) -> str:
    """读取文件最后 N 行。"""
    if not path.exists():
        return "(no log file)"
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        all_lines = content.splitlines()
        return "\n".join(all_lines[-lines:])
    except OSError:
        return "(cannot read log)"


def run_cmd(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """运行命令并返回结果。"""
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def run_auto_backup() -> None:
    """在基础设施就绪后自动备份数据库。"""
    pg = run_cmd(["docker", "exec", "quant-postgres", "pg_isready", "-U", "quant"])
    if pg.returncode != 0:
        info("Skipping auto backup: PostgreSQL is not ready")
        return

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [
            "docker",
            "exec",
            "quant-postgres",
            "pg_dump",
            "-U",
            "quant",
            "-d",
            "quant",
            "--no-owner",
            "--no-acl",
        ],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        with gzip.open(BACKUP_FILE, "wb") as gz:
            assert proc.stdout is not None
            shutil.copyfileobj(proc.stdout, gz)
        stderr = ""
        if proc.stderr is not None:
            stderr = proc.stderr.read().decode("utf-8", errors="replace").strip()
        if proc.wait() != 0:
            BACKUP_FILE.unlink(missing_ok=True)
            info(f"Auto backup skipped: {stderr or 'pg_dump failed'}")
            return
    finally:
        if proc.stdout is not None:
            proc.stdout.close()
        if proc.stderr is not None:
            proc.stderr.close()

    size_kib = BACKUP_FILE.stat().st_size / 1024
    info(f"Auto backup saved: {BACKUP_FILE} ({size_kib:.1f} KiB)")


# ============================================
# 命令: start
# ============================================


def cmd_start() -> int:
    print()
    print("  ==========================================")
    print("   Quant Research Platform - Local Dev")
    print("  ==========================================")
    print()

    total = 7

    # 1. 前置检查
    step(1, total, "Checking prerequisites ...")
    errors = []
    for tool, hint in [
        ("docker", "Install Docker Desktop: https://www.docker.com/"),
        ("uv", "Install: https://astral.sh/uv"),
        ("pnpm", "Run: npm install -g pnpm"),
        ("node", "Install: https://nodejs.org/"),
    ]:
        if which(tool):
            info(f"  {tool:8s} OK")
        else:
            info(f"  {tool:8s} MISSING - {hint}")
            errors.append(tool)

    # docker 是否在运行
    if which("docker"):
        r = run_cmd(["docker", "info"])
        if r.returncode != 0:
            info("  docker   NOT RUNNING - Please start Docker Desktop")
            errors.append("docker-running")

    # .env
    if (ROOT / ".env").exists():
        info(f"  {'env':8s} OK")
    else:
        info(f"  {'env':8s} MISSING - Copy .env.example to .env")
        errors.append(".env")

    if errors:
        print()
        info("Fix the above issues and try again.")
        return 1

    occupied = find_occupied_ports()
    if occupied:
        print()
        info(f"Ports already in use: {', '.join(occupied)}")
        info("Stop the existing services first:")
        info("  uv run python scripts/dev.py stop")
        return 1

    # 2. 依赖安装
    step(2, total, "Ensuring dependencies ...")
    info("Syncing Python dependencies ...")
    py_sync = subprocess.run(["uv", "sync", "--dev"], cwd=str(ROOT))
    if py_sync.returncode != 0:
        info("Python dependency sync failed")
        return py_sync.returncode

    fe_modules = ROOT / "frontend" / "node_modules"
    if not fe_modules.exists():
        info("Installing frontend dependencies ...")
        fe_install = subprocess.run(["pnpm", "install"], cwd=str(ROOT / "frontend"))
        if fe_install.returncode != 0:
            info("Frontend dependency installation failed")
            return fe_install.returncode
    else:
        info("Frontend deps OK")

    # 3. Docker 基础设施
    step(3, total, "Starting infrastructure (PostgreSQL + Redis) ...")
    infra_up = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_INFRA), "up", "-d"],
        cwd=str(ROOT),
    )
    if infra_up.returncode != 0:
        info("Infrastructure startup failed")
        return infra_up.returncode

    # 4. 等待基础设施就绪
    step(4, total, "Waiting for infrastructure ...")
    for i in range(HEALTH_RETRIES):
        pg = run_cmd(["docker", "exec", "quant-postgres",
                       "pg_isready", "-U", "quant"])
        redis = run_cmd(["docker", "exec", "quant-redis",
                          "redis-cli", "ping"])
        if pg.returncode == 0 and "PONG" in (redis.stdout or ""):
            info("PostgreSQL + Redis ready")
            break
        time.sleep(HEALTH_INTERVAL)
    else:
        info("Infrastructure may not be fully ready, continuing ...")

    run_auto_backup()

    # 5. 启动后端服务
    step(5, total, "Starting backend services ...")
    env = load_env()

    for name, cmd, cwd_rel in BACKEND_SERVICES:
        cwd = ROOT if cwd_rel is None else ROOT / cwd_rel
        pid = spawn_background(name, cmd, cwd, env)
        port = PORTS.get(name, "?")
        info(f"  {name:20s} PID={pid}  port={port}")

    time.sleep(2)
    # 验证 API 是否启动
    api_pid = read_pid("api")
    if api_pid and not is_alive(api_pid):
        info("WARNING: API process exited immediately, check .pids/api.log")

    # 6. 启动前端
    step(6, total, "Starting frontend ...")
    fe_name, fe_cmd, fe_cwd = FRONTEND_SERVICE
    fe_pid = spawn_background(fe_name, fe_cmd, ROOT / fe_cwd, env)
    info(f"  {fe_name:20s} PID={fe_pid}  port={PORTS.get(fe_name, '?')}")

    # 7. 健康检查
    step(7, total, "Health check ...")
    time.sleep(5)
    all_ok = True
    for name, port in PORTS.items():
        ok = port_in_use(port)
        status = "OK" if ok else "FAIL"
        info(f"  {name:20s} :{port}  {status}")
        if not ok:
            all_ok = False

    print()
    if all_ok:
        # 调用 banner
        try:
            subprocess.run(
                ["uv", "run", "python", "scripts/banner.py"],
                cwd=str(ROOT), timeout=5,
            )
        except Exception:
            pass
    else:
        info("Some services may still be starting. Run:")
        info("  uv run python scripts/dev.py status")

    # 打开浏览器
    print()
    info("Frontend:  http://localhost:5173")
    info("API Docs:  http://localhost:8000/docs")
    print()
    webbrowser.open("http://localhost:5173")

    info("To stop:   uv run python scripts/dev.py stop")
    print()
    return 0


# ============================================
# 命令: stop
# ============================================


def cmd_stop() -> int:
    print()
    print("  ==========================================")
    print("   Stopping all services ...")
    print("  ==========================================")
    print()

    total = 4

    # 1. 优雅终止
    step(1, total, "Terminating processes (graceful) ...")
    pids_found = []
    all_services = [s[0] for s in BACKEND_SERVICES] + [FRONTEND_SERVICE[0]]
    for name in all_services:
        pid = read_pid(name)
        if pid and is_alive(pid):
            kill_pid(pid, force=False)
            pids_found.append((name, pid))
            info(f"  {name:20s} PID={pid} SIGTERM")
        else:
            info(f"  {name:20s} not running")

    if pids_found:
        step(2, total, f"Waiting {KILL_TIMEOUT}s for graceful shutdown ...")
        time.sleep(KILL_TIMEOUT)

        # 2. 强制终止残留
        for name, pid in pids_found:
            if is_alive(pid):
                kill_pid(pid, force=True)
                info(f"  {name:20s} PID={pid} force killed")
    else:
        step(2, total, "No processes to wait for")

    # 3. 清理 PID 文件
    step(3, total, "Cleaning up PID files ...")
    if PID_DIR.exists():
        for f in PID_DIR.glob("*.pid"):
            f.unlink(missing_ok=True)

    # 4. 停止 Docker 基础设施
    step(4, total, "Stopping infrastructure (PostgreSQL + Redis) ...")
    if which("docker"):
        subprocess.run(
            ["docker", "compose", "-f", str(COMPOSE_INFRA), "down"],
            cwd=str(ROOT),
            capture_output=True,
        )
    else:
        info("Skipping infrastructure shutdown: docker is not installed")

    print()
    # 验证端口释放（等待 TIME_WAIT 状态消散）
    time.sleep(2)
    still_occupied = []
    for name, port in PORTS.items():
        if port_in_use(port):
            still_occupied.append(f"{name}:{port}")
    if still_occupied:
        info(f"Ports in TIME_WAIT (will clear soon): {', '.join(still_occupied)}")
    else:
        info("All ports released")

    print()
    info("All services stopped.")
    print()
    return 0


# ============================================
# 命令: status
# ============================================


def cmd_status() -> int:
    print()
    print("  === Service Status ===")
    print()

    all_services = [s[0] for s in BACKEND_SERVICES] + [FRONTEND_SERVICE[0]]
    for name in all_services:
        pid = read_pid(name)
        port = PORTS.get(name, 0)
        pid_alive = pid is not None and is_alive(pid)
        port_open = port_in_use(port) if port else False

        if pid_alive and port_open:
            status = "running"
        elif pid_alive:
            status = "starting"
        elif port_open:
            status = "port in use (external?)"
        else:
            status = "stopped"

        pid_str = str(pid) if pid else "-"
        info(f"  {name:20s}  PID={pid_str:>8s}  :{port:<5d}  {status}")

    # Docker 容器
    print()
    info("=== Docker Containers ===")
    print()
    if which("docker"):
        subprocess.run(
            ["docker", "compose", "-f", str(COMPOSE_INFRA), "ps"],
            cwd=str(ROOT),
        )
    else:
        info("docker is not installed")
    print()
    return 0


# ============================================
# 命令: logs
# ============================================


def cmd_logs() -> int:
    # 解析 --lines 参数
    lines = 30
    service_filter = None
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-n", "--lines") and i + 1 < len(args):
            try:
                lines = int(args[i + 1])
            except ValueError:
                print("Invalid value for --lines")
                return 1
            i += 2
            continue
        elif not arg.startswith("-"):
            service_filter = arg
        i += 1

    all_services = [s[0] for s in BACKEND_SERVICES] + [FRONTEND_SERVICE[0]]
    if service_filter:
        all_services = [s for s in all_services if service_filter in s]

    for name in all_services:
        log_file = PID_DIR / f"{name}.log"
        print(f"\n  === {name} (last {lines} lines) ===\n")
        print(tail_file(log_file, lines))

    print()
    return 0


# ============================================
# 入口
# ============================================


COMMANDS = {
    "start": cmd_start,
    "stop": cmd_stop,
    "status": cmd_status,
    "logs": cmd_logs,
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage: uv run python scripts/dev.py <command>")
        print()
        print("Commands:")
        print("  start    Start all local development services")
        print("  stop     Stop all services")
        print("  status   Show service status")
        print("  logs     Show recent logs ([-n LINES] [SERVICE])")
        print()
        print("Examples:")
        print("  uv run python scripts/dev.py start")
        print("  uv run python scripts/dev.py logs api")
        print("  uv run python scripts/dev.py logs -n 100 mcp-factor")
        return 1

    return COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    sys.exit(main())
