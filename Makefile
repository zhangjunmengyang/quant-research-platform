.PHONY: help start stop restart logs status clean force-clean local dev prod healthcheck \
	logs-api logs-mcp logs-frontend version backup mcp-tools \
	_check_tools _check_local_tools _check_ports _ensure_deps \
	_start_local _start_dev _start_prod _check_docker_ports _check_docker_ports_prod \
	_wait_infra_ready _wait_docker_healthy _auto_backup _auto_backup_docker \
	_stop_local _stop_dev _stop_prod _verify_ports_released \
	_post_restart_check_local _post_restart_check_docker _healthcheck_local _healthcheck_docker

# ============================================
# 配置
# ============================================
export LOG_LEVEL ?= INFO
export LOG_FORMAT ?= json

COMPOSE_DIR := docker/compose
COMPOSE_PROD := $(COMPOSE_DIR)/docker-compose.yml
COMPOSE_DEV := $(COMPOSE_DIR)/docker-compose.dev.yml
COMPOSE_INFRA := $(COMPOSE_DIR)/docker-compose.infra.yml
PID_DIR := .pids

# 进程终止超时（秒）
KILL_TIMEOUT := 5
# Docker 容器停止超时（秒）
DOCKER_STOP_TIMEOUT := 30
# 健康检查超时（秒）
HEALTH_TIMEOUT := 30
# 健康检查间隔（秒）
HEALTH_INTERVAL := 2
# 健康检查重试次数
HEALTH_RETRIES := 10

# 所有需要清理的端口
PORTS_TO_CLEAN := 8000 5173 6789 6790 6791 6792 6793 6794
# 生产环境额外端口
PORTS_PROD := 80 443

# 检测 docker compose 命令（兼容新旧版本）
DOCKER_COMPOSE := $(shell docker compose version > /dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

# 检测操作系统（macOS 的某些命令行为不同）
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    # macOS: lsof 输出格式略有不同
    SED_INPLACE := sed -i ''
else
    SED_INPLACE := sed -i
endif

# 检测模式: local / dev / prod
MODE := $(word 2,$(MAKECMDGOALS))
ifeq ($(MODE),)
    MODE := prod
endif

# ============================================
# 帮助
# ============================================
help:
	@echo "用法: make <动作> [模式]"
	@echo ""
	@echo "模式:"
	@echo "  local    - 本机开发（Python/Node 本地运行，仅 Docker 基础设施）"
	@echo "  dev      - Docker 开发（全容器化，代码热重载）"
	@echo "  prod     - 生产环境（全容器化，优化构建）"
	@echo ""
	@echo "命令:"
	@echo "  make start local   - 启动本机开发环境（自动安装依赖）"
	@echo "  make start dev     - 启动 Docker 开发环境"
	@echo "  make start [prod]  - 启动生产环境（默认）"
	@echo ""
	@echo "  make stop local    - 停止本机开发环境"
	@echo "  make stop dev      - 停止 Docker 开发环境"
	@echo "  make stop [prod]   - 停止生产环境"
	@echo ""
	@echo "  make restart <模式>      - 重启指定模式"
	@echo "  make status              - 查看所有服务状态"
	@echo "  make healthcheck <模式>  - 检查服务健康状态"
	@echo ""
	@echo "  make logs local    - 查看本机服务日志"
	@echo "  make logs dev      - 查看 Docker 开发日志"
	@echo "  make logs [prod]   - 查看生产日志"
	@echo ""
	@echo "  make clean         - 清理所有环境"
	@echo "  make force-clean   - 强制清理（当 stop 无效时使用）"
	@echo ""
	@echo "  make logs-api      - 实时查看 API 日志"
	@echo "  make logs-mcp      - 实时查看 MCP 日志"
	@echo "  make logs-frontend - 实时查看前端日志"
	@echo "  make version       - 显示版本信息"
	@echo ""
	@echo "  make mcp-tools     - 列出所有 MCP 服务和工具"
	@echo "  make mcp-tools-json    - JSON 格式输出"
	@echo "  make mcp-tools-summary - 仅显示摘要"
	@echo ""
	@echo "服务地址:"
	@echo "  前端:     http://localhost:5173 (local/dev) | http://localhost (prod)"
	@echo "  API:      http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"
	@echo "  MCP:      localhost:6789-6794"

# ============================================
# 伪目标（模式标记）
# ============================================
local dev prod:
	@true

# ============================================
# 内部: 检查必要工具
# ============================================
_check_tools:
	@command -v docker > /dev/null 2>&1 || { echo "错误: 请先安装 Docker"; exit 1; }
	@docker info > /dev/null 2>&1 || { echo "错误: Docker 未运行，请先启动 Docker Desktop"; exit 1; }
	@# 检查 Docker Compose 文件是否存在
	@test -f $(COMPOSE_INFRA) || { echo "错误: 缺少 $(COMPOSE_INFRA)"; exit 1; }

_check_local_tools: _check_tools
	@command -v uv > /dev/null 2>&1 || { echo "错误: 请先安装 uv (curl -LsSf https://astral.sh/uv/install.sh | sh)"; exit 1; }
	@command -v pnpm > /dev/null 2>&1 || { echo "错误: 请先安装 pnpm (npm install -g pnpm)"; exit 1; }
	@command -v curl > /dev/null 2>&1 || { echo "错误: 请先安装 curl"; exit 1; }

# 检查端口是否被占用
_check_ports:
	@echo "检查端口可用性..."
	@occupied=""; \
	for port in $(PORTS_TO_CLEAN); do \
		if lsof -ti :$$port >/dev/null 2>&1; then \
			occupied="$$occupied $$port"; \
		fi; \
	done; \
	if [ -n "$$occupied" ]; then \
		echo "警告: 以下端口已被占用:$$occupied"; \
		echo ""; \
		echo "可选操作:"; \
		echo "  1. 运行 'make stop local' 停止现有服务"; \
		echo "  2. 运行 'make force-clean' 强制清理"; \
		echo "  3. 手动检查占用进程: lsof -i :<端口号>"; \
		echo ""; \
		read -p "是否自动清理这些端口? [y/N] " answer; \
		if [ "$$answer" = "y" ] || [ "$$answer" = "Y" ]; then \
			for port in $$occupied; do \
				echo "  清理端口 $$port..."; \
				lsof -ti :$$port | xargs kill -9 2>/dev/null || true; \
			done; \
			sleep 1; \
		else \
			echo "已取消启动"; \
			exit 1; \
		fi; \
	fi; \
	echo "端口检查通过"

# ============================================
# 内部: 检查并安装依赖
# ============================================
_ensure_deps: _check_local_tools
	@if [ ! -d ".venv" ] || [ ! -f ".venv/pyvenv.cfg" ]; then \
		echo "[依赖] 安装 Python 依赖..."; \
		uv sync --dev; \
	else \
		echo "[依赖] 同步 Python 依赖..."; \
		uv sync --dev 2>&1 | grep -v -E "^Resolved|^Audited|^$$" || true; \
	fi
	@if [ ! -d "frontend/node_modules" ] || [ ! -d "frontend/node_modules/.bin" ]; then \
		echo "[依赖] 安装前端依赖..."; \
		cd frontend && rm -rf node_modules && pnpm install; \
	fi

# ============================================
# 启动服务
# ============================================
start:
ifeq ($(MODE),local)
	@$(MAKE) _start_local
else ifeq ($(MODE),dev)
	@$(MAKE) _start_dev
else
	@$(MAKE) _start_prod
endif

_start_local: _ensure_deps _check_ports
	@echo ""
	@echo "=========================================="
	@echo "        启动本地开发环境"
	@echo "=========================================="
	@echo ""
	@echo "[1/6] 启动基础设施 (PostgreSQL + Redis)..."
	@$(DOCKER_COMPOSE) -f $(COMPOSE_INFRA) up -d --quiet-pull 2>&1 | grep -v -E "^$$|level=warning" || true
	@$(MAKE) _wait_infra_ready
	@$(MAKE) _auto_backup
	@mkdir -p $(PID_DIR)
	@echo "[2/6] 启动 API..."
	@PYTHONPATH=backend DATABASE_URL=postgresql://quant:quant123@localhost:5432/quant \
		REDIS_URL=redis://localhost:6379 LOG_LEVEL=$(LOG_LEVEL) LOG_FORMAT=$(LOG_FORMAT) \
		nohup uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend \
		> $(PID_DIR)/api.log 2>&1 & echo $$! > $(PID_DIR)/api.pid
	@sleep 2
	@if [ -f $(PID_DIR)/api.pid ]; then \
		pid=$$(cat $(PID_DIR)/api.pid); \
		if ! kill -0 $$pid 2>/dev/null; then \
			echo "       [x] API 启动失败"; \
			echo ""; \
			tail -15 $(PID_DIR)/api.log; \
			exit 1; \
		fi; \
	fi
	@echo "[3/6] 启动 MCP 服务..."
	@PYTHONPATH=backend DATABASE_URL=postgresql://quant:quant123@localhost:5432/quant \
		REDIS_URL=redis://localhost:6379 LOG_LEVEL=$(LOG_LEVEL) LOG_FORMAT=$(LOG_FORMAT) \
		nohup uv run python -m domains.factor_hub.api.mcp.server \
		> $(PID_DIR)/mcp-factor.log 2>&1 & echo $$! > $(PID_DIR)/mcp-factor.pid
	@PYTHONPATH=backend DATABASE_URL=postgresql://quant:quant123@localhost:5432/quant \
		REDIS_URL=redis://localhost:6379 LOG_LEVEL=$(LOG_LEVEL) LOG_FORMAT=$(LOG_FORMAT) \
		nohup uv run python -m domains.data_hub.api.mcp.server \
		> $(PID_DIR)/mcp-data.log 2>&1 & echo $$! > $(PID_DIR)/mcp-data.pid
	@PYTHONPATH=backend DATABASE_URL=postgresql://quant:quant123@localhost:5432/quant \
		REDIS_URL=redis://localhost:6379 LOG_LEVEL=$(LOG_LEVEL) LOG_FORMAT=$(LOG_FORMAT) \
		nohup uv run python -m domains.strategy_hub.api.mcp.server \
		> $(PID_DIR)/mcp-strategy.log 2>&1 & echo $$! > $(PID_DIR)/mcp-strategy.pid
	@PYTHONPATH=backend DATABASE_URL=postgresql://quant:quant123@localhost:5432/quant \
		REDIS_URL=redis://localhost:6379 LOG_LEVEL=$(LOG_LEVEL) LOG_FORMAT=$(LOG_FORMAT) \
		nohup uv run python -m domains.note_hub.api.mcp.server \
		> $(PID_DIR)/mcp-note.log 2>&1 & echo $$! > $(PID_DIR)/mcp-note.pid
	@PYTHONPATH=backend DATABASE_URL=postgresql://quant:quant123@localhost:5432/quant \
		REDIS_URL=redis://localhost:6379 LOG_LEVEL=$(LOG_LEVEL) LOG_FORMAT=$(LOG_FORMAT) \
		nohup uv run python -m domains.research_hub.api.mcp.server \
		> $(PID_DIR)/mcp-research.log 2>&1 & echo $$! > $(PID_DIR)/mcp-research.pid
	@PYTHONPATH=backend DATABASE_URL=postgresql://quant:quant123@localhost:5432/quant \
		REDIS_URL=redis://localhost:6379 LOG_LEVEL=$(LOG_LEVEL) LOG_FORMAT=$(LOG_FORMAT) \
		nohup uv run python -m domains.experience_hub.api.mcp.server \
		> $(PID_DIR)/mcp-experience.log 2>&1 & echo $$! > $(PID_DIR)/mcp-experience.pid
	@sleep 1
	@echo "[4/6] 启动前端..."
	@nohup sh -c 'cd frontend && exec pnpm dev' > $(PID_DIR)/frontend.log 2>&1 & echo $$! > $(PID_DIR)/frontend.pid
	@sleep 2
	@echo "[5/6] 验证服务状态..."
	@$(MAKE) _healthcheck_local || echo "  [!] 部分服务可能仍在启动中，请稍后运行 make healthcheck local"
	@echo "[6/6] 完成"

_start_dev: _check_tools _check_docker_ports
	@echo "========== 启动 Docker 开发环境 =========="
	@# 先清理可能存在的旧容器（避免名称冲突）
	@$(DOCKER_COMPOSE) -f $(COMPOSE_DEV) down --remove-orphans 2>/dev/null || true
	@$(DOCKER_COMPOSE) -f $(COMPOSE_DEV) up -d --build
	@$(MAKE) _auto_backup_docker COMPOSE_FILE=$(COMPOSE_DEV)
	@echo ""
	@echo "等待服务启动..."
	@$(MAKE) _wait_docker_healthy COMPOSE_FILE=$(COMPOSE_DEV)
	@echo ""
	@$(DOCKER_COMPOSE) -f $(COMPOSE_DEV) ps
	@echo ""
	@python3 scripts/banner.py 2>/dev/null || echo "Docker 开发环境已启动"

_start_prod: _check_tools _check_docker_ports_prod
	@echo "========== 启动生产环境 =========="
	@# 先清理可能存在的旧容器（避免名称冲突）
	@$(DOCKER_COMPOSE) -f $(COMPOSE_PROD) down --remove-orphans 2>/dev/null || true
	@$(DOCKER_COMPOSE) -f $(COMPOSE_PROD) up -d --build
	@$(MAKE) _auto_backup_docker COMPOSE_FILE=$(COMPOSE_PROD)
	@echo ""
	@echo "等待服务启动..."
	@$(MAKE) _wait_docker_healthy COMPOSE_FILE=$(COMPOSE_PROD)
	@echo ""
	@$(DOCKER_COMPOSE) -f $(COMPOSE_PROD) ps
	@echo ""
	@python3 scripts/banner.py 2>/dev/null || echo "生产环境已启动"

# 检查 Docker 模式端口占用
_check_docker_ports:
	@occupied=""; \
	for port in $(PORTS_TO_CLEAN); do \
		if lsof -ti :$$port >/dev/null 2>&1; then \
			occupied="$$occupied $$port"; \
		fi; \
	done; \
	if [ -n "$$occupied" ]; then \
		echo "警告: 以下端口已被占用:$$occupied"; \
		echo "这可能是本地服务正在运行，请先运行 'make stop local' 或 'make force-clean'"; \
		exit 1; \
	fi

_check_docker_ports_prod: _check_docker_ports
	@for port in $(PORTS_PROD); do \
		if lsof -ti :$$port >/dev/null 2>&1; then \
			echo "警告: 生产端口 $$port 已被占用"; \
			exit 1; \
		fi; \
	done

# 等待基础设施就绪（PostgreSQL + Redis）
_wait_infra_ready:
	@printf "  等待中"
	@for i in $$(seq 1 $(HEALTH_RETRIES)); do \
		if docker exec quant-postgres pg_isready -U quant >/dev/null 2>&1; then \
			pg_ready="yes"; \
		else \
			pg_ready="no"; \
		fi; \
		if docker exec quant-redis redis-cli ping 2>/dev/null | grep -q PONG; then \
			redis_ready="yes"; \
		else \
			redis_ready="no"; \
		fi; \
		if [ "$$pg_ready" = "yes" ] && [ "$$redis_ready" = "yes" ]; then \
			printf " 就绪\n"; \
			exit 0; \
		fi; \
		printf "."; \
		sleep $(HEALTH_INTERVAL); \
	done; \
	printf " 超时\n"; \
	echo "  [!] 基础设施未能在预期时间内就绪，但将继续启动..."

# 等待 Docker 服务健康
_wait_docker_healthy:
	@echo "  检查容器健康状态..."
	@for i in $$(seq 1 $(HEALTH_RETRIES)); do \
		unhealthy=$$($(DOCKER_COMPOSE) -f $(COMPOSE_FILE) ps --format json 2>/dev/null | \
			grep -E '"Health":"(starting|unhealthy)"' | wc -l | tr -d ' '); \
		if [ "$$unhealthy" = "0" ]; then \
			echo "  所有容器已就绪"; \
			break; \
		fi; \
		if [ $$i -eq $(HEALTH_RETRIES) ]; then \
			echo "  警告: 部分容器未能在预期时间内就绪"; \
			$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) ps; \
		else \
			echo "  等待容器就绪... ($$i/$(HEALTH_RETRIES))"; \
			sleep $(HEALTH_INTERVAL); \
		fi; \
	done

# ============================================
# 停止服务
# ============================================
stop:
ifeq ($(MODE),local)
	@$(MAKE) _stop_local
else ifeq ($(MODE),dev)
	@$(MAKE) _stop_dev
else
	@$(MAKE) _stop_prod
endif

_stop_local:
	@echo "停止本机服务..."
	@echo "[1/4] 优雅终止进程 (SIGTERM)..."
	@-pkill -TERM -f "uvicorn app.main:app" 2>/dev/null || true
	@-pkill -TERM -f "uv run uvicorn" 2>/dev/null || true
	@-pkill -TERM -f "domains.factor_hub.api.mcp.server" 2>/dev/null || true
	@-pkill -TERM -f "domains.data_hub.api.mcp.server" 2>/dev/null || true
	@-pkill -TERM -f "domains.strategy_hub.api.mcp.server" 2>/dev/null || true
	@-pkill -TERM -f "domains.note_hub.api.mcp.server" 2>/dev/null || true
	@-pkill -TERM -f "domains.research_hub.api.mcp.server" 2>/dev/null || true
	@-pkill -TERM -f "domains.experience_hub.api.mcp.server" 2>/dev/null || true
	@-pkill -TERM -f "pnpm.*dev" 2>/dev/null || true
	@-pkill -TERM -f "vite" 2>/dev/null || true
	@-pkill -TERM -f "esbuild" 2>/dev/null || true
	@sleep $(KILL_TIMEOUT)
	@echo "[2/4] 强制终止残留进程 (SIGKILL)..."
	@-pkill -9 -f "uvicorn app.main:app" 2>/dev/null || true
	@-pkill -9 -f "uv run uvicorn" 2>/dev/null || true
	@-pkill -9 -f "domains.factor_hub.api.mcp.server" 2>/dev/null || true
	@-pkill -9 -f "domains.data_hub.api.mcp.server" 2>/dev/null || true
	@-pkill -9 -f "domains.strategy_hub.api.mcp.server" 2>/dev/null || true
	@-pkill -9 -f "domains.note_hub.api.mcp.server" 2>/dev/null || true
	@-pkill -9 -f "domains.research_hub.api.mcp.server" 2>/dev/null || true
	@-pkill -9 -f "domains.experience_hub.api.mcp.server" 2>/dev/null || true
	@-pkill -9 -f "pnpm.*dev" 2>/dev/null || true
	@-pkill -9 -f "vite" 2>/dev/null || true
	@-pkill -9 -f "esbuild" 2>/dev/null || true
	@echo "[3/4] 清理端口占用..."
	@for port in $(PORTS_TO_CLEAN); do \
		pids=$$(lsof -ti :$$port 2>/dev/null); \
		if [ -n "$$pids" ]; then \
			echo "  端口 $$port: 清理进程 $$pids"; \
			echo "$$pids" | xargs kill -9 2>/dev/null || true; \
		fi; \
	done
	@sleep 1
	@all_clear=true; \
	for port in $(PORTS_TO_CLEAN); do \
		if lsof -ti :$$port >/dev/null 2>&1; then \
			echo "  警告: 端口 $$port 仍被占用"; \
			all_clear=false; \
		fi; \
	done; \
	if [ "$$all_clear" = "false" ]; then \
		echo "  提示: 部分端口未释放，可能需要等待或手动检查"; \
	fi
	@rm -f $(PID_DIR)/*.pid 2>/dev/null || true
	@echo "[4/4] 停止基础设施容器..."
	@$(DOCKER_COMPOSE) -f $(COMPOSE_INFRA) down 2>/dev/null || true
	@echo ""
	@echo "本地开发环境已停止"

_stop_dev:
	@echo "停止 Docker 开发环境..."
	@# 第一阶段: 优雅停止（发送 SIGTERM，等待容器自行退出）
	@$(DOCKER_COMPOSE) -f $(COMPOSE_DEV) stop -t $(DOCKER_STOP_TIMEOUT) 2>/dev/null || true
	@# 第二阶段: 删除容器和网络
	@$(DOCKER_COMPOSE) -f $(COMPOSE_DEV) down --remove-orphans --volumes 2>/dev/null || true
	@# 第三阶段: 清理可能残留的容器（按名称匹配 dev 环境）
	@containers=$$(docker ps -aq --filter "name=quant-" 2>/dev/null | grep -v "^$$" || true); \
	if [ -n "$$containers" ]; then \
		for c in $$containers; do \
			name=$$(docker inspect --format '{{.Name}}' $$c 2>/dev/null); \
			if echo "$$name" | grep -q "\-dev"; then \
				docker rm -f $$c 2>/dev/null || true; \
			fi; \
		done; \
	fi
	@# 验证端口已释放
	@$(MAKE) _verify_ports_released
	@echo "Docker 开发环境已停止"

_stop_prod:
	@echo "停止生产环境..."
	@# 第一阶段: 优雅停止
	@$(DOCKER_COMPOSE) -f $(COMPOSE_PROD) stop -t $(DOCKER_STOP_TIMEOUT) 2>/dev/null || true
	@# 第二阶段: 删除容器和网络（保留数据卷）
	@$(DOCKER_COMPOSE) -f $(COMPOSE_PROD) down --remove-orphans 2>/dev/null || true
	@# 第三阶段: 清理可能残留的容器（排除 dev 环境容器）
	@containers=$$(docker ps -aq --filter "name=quant-" 2>/dev/null | grep -v "^$$" || true); \
	if [ -n "$$containers" ]; then \
		for c in $$containers; do \
			name=$$(docker inspect --format '{{.Name}}' $$c 2>/dev/null); \
			if ! echo "$$name" | grep -q "\-dev"; then \
				docker rm -f $$c 2>/dev/null || true; \
			fi; \
		done; \
	fi
	@# 验证端口已释放
	@$(MAKE) _verify_ports_released EXTRA_PORTS="$(PORTS_PROD)"
	@echo "生产环境已停止"

# 验证端口已释放
_verify_ports_released:
	@sleep 1
	@all_ports="$(PORTS_TO_CLEAN) $(EXTRA_PORTS)"; \
	still_occupied=""; \
	for port in $$all_ports; do \
		if lsof -ti :$$port >/dev/null 2>&1; then \
			still_occupied="$$still_occupied $$port"; \
		fi; \
	done; \
	if [ -n "$$still_occupied" ]; then \
		echo "  警告: 以下端口仍被占用:$$still_occupied"; \
		echo "  可运行 'make force-clean' 强制清理"; \
	fi

# ============================================
# 重启服务
# ============================================
restart:
	@echo "========== 重启服务 ($(MODE)) =========="
	@$(MAKE) stop $(MODE)
	@# 确保端口完全释放后再启动
	@echo "等待端口释放..."
	@sleep 2
	@$(MAKE) start $(MODE)
	@# start 已包含健康检查，无需重复

# ============================================
# 查看日志
# ============================================
logs:
ifeq ($(MODE),local)
	@echo "=== API ===" && tail -30 $(PID_DIR)/api.log 2>/dev/null || echo "(无日志)"
	@echo "" && echo "=== MCP ===" && tail -10 $(PID_DIR)/mcp-factor.log 2>/dev/null || echo "(无日志)"
	@echo "" && echo "=== Frontend ===" && tail -10 $(PID_DIR)/frontend.log 2>/dev/null || echo "(无日志)"
	@echo ""
	@echo "实时日志: tail -f .pids/*.log"
else ifeq ($(MODE),dev)
	@$(DOCKER_COMPOSE) -f $(COMPOSE_DEV) logs -f
else
	@$(DOCKER_COMPOSE) -f $(COMPOSE_PROD) logs -f
endif

# ============================================
# 状态查看
# ============================================
status:
	@echo "=== 本机服务 ==="
	@if pgrep -f "uvicorn app.main:app" > /dev/null 2>&1; then echo "  API:      运行中"; else echo "  API:      未运行"; fi
	@if pgrep -f "domains.factor_hub.api.mcp.server" > /dev/null 2>&1; then echo "  MCP Factor: 运行中"; else echo "  MCP Factor: 未运行"; fi
	@if pgrep -f "domains.data_hub.api.mcp.server" > /dev/null 2>&1; then echo "  MCP Data:   运行中"; else echo "  MCP Data:   未运行"; fi
	@if pgrep -f "domains.strategy_hub.api.mcp.server" > /dev/null 2>&1; then echo "  MCP Strategy: 运行中"; else echo "  MCP Strategy: 未运行"; fi
	@if pgrep -f "domains.note_hub.api.mcp.server" > /dev/null 2>&1; then echo "  MCP Note:   运行中"; else echo "  MCP Note:   未运行"; fi
	@if pgrep -f "domains.research_hub.api.mcp.server" > /dev/null 2>&1; then echo "  MCP Research: 运行中"; else echo "  MCP Research: 未运行"; fi
	@if pgrep -f "domains.experience_hub.api.mcp.server" > /dev/null 2>&1; then echo "  MCP Experience: 运行中"; else echo "  MCP Experience: 未运行"; fi
	@if pgrep -f "vite.*frontend" > /dev/null 2>&1 || pgrep -f "pnpm dev" > /dev/null 2>&1; then echo "  Frontend: 运行中"; else echo "  Frontend: 未运行"; fi
	@echo ""
	@echo "=== Docker 容器 ==="
	@$(DOCKER_COMPOSE) -f $(COMPOSE_INFRA) ps 2>/dev/null || echo "(无)"
	@$(DOCKER_COMPOSE) -f $(COMPOSE_DEV) ps 2>/dev/null || true
	@$(DOCKER_COMPOSE) -f $(COMPOSE_PROD) ps 2>/dev/null || true

# ============================================
# 健康检查
# ============================================
healthcheck:
ifeq ($(MODE),local)
	@$(MAKE) _healthcheck_local
else ifeq ($(MODE),dev)
	@$(MAKE) _healthcheck_docker COMPOSE_FILE=$(COMPOSE_DEV)
else
	@$(MAKE) _healthcheck_docker COMPOSE_FILE=$(COMPOSE_PROD)
endif

# 重启后检查（本地模式）
_post_restart_check_local:
	@echo ""
	@echo "执行本地服务健康检查..."
	@sleep 3
	@$(MAKE) _healthcheck_local || (echo "重启失败，服务未正常启动" && exit 1)

# 重启后检查（Docker 模式）
_post_restart_check_docker:
	@$(MAKE) _healthcheck_docker || (echo "重启失败，容器未正常启动" && exit 1)

# Docker 模式健康检查
_healthcheck_docker:
	@echo "执行 Docker 健康检查..."
	@failed=0; \
	echo "  检查容器状态..."; \
	containers=$$($(DOCKER_COMPOSE) -f $(COMPOSE_FILE) ps --format json 2>/dev/null); \
	if [ -z "$$containers" ]; then \
		echo "    错误: 没有运行中的容器"; \
		exit 1; \
	fi; \
	unhealthy=$$(echo "$$containers" | grep -E '"Health":"unhealthy"' | wc -l | tr -d ' '); \
	if [ "$$unhealthy" != "0" ]; then \
		echo "    警告: $$unhealthy 个容器不健康"; \
		failed=1; \
	fi; \
	exited=$$(echo "$$containers" | grep -E '"State":"exited"' | wc -l | tr -d ' '); \
	if [ "$$exited" != "0" ]; then \
		echo "    警告: $$exited 个容器已退出"; \
		failed=1; \
	fi; \
	echo "  检查 API 服务..."; \
	for i in 1 2 3 4 5; do \
		if curl -sf http://localhost:8000/health >/dev/null 2>&1; then \
			echo "    API: 正常"; \
			break; \
		fi; \
		if [ $$i -eq 5 ]; then \
			echo "    API: 异常"; \
			failed=1; \
		fi; \
		sleep $(HEALTH_INTERVAL); \
	done; \
	if [ $$failed -eq 1 ]; then \
		echo ""; \
		echo "部分服务异常，查看日志: make logs $(MODE)"; \
		exit 1; \
	else \
		echo ""; \
		echo "所有服务正常运行"; \
	fi

_healthcheck_local:
	@failed=0; \
	printf "  API .............. "; \
	api_ok=0; \
	for i in 1 2 3 4 5 6 7 8 9 10; do \
		if curl -sf http://localhost:8000/health >/dev/null 2>&1; then \
			printf "OK\n"; \
			api_ok=1; \
			break; \
		fi; \
		sleep 1; \
	done; \
	if [ $$api_ok -eq 0 ]; then \
		printf "FAIL\n"; \
		failed=1; \
	fi; \
	printf "  Frontend ......... "; \
	if lsof -ti :5173 >/dev/null 2>&1; then \
		printf "OK\n"; \
	else \
		printf "FAIL\n"; \
		failed=1; \
	fi; \
	printf "  MCP Factor ....... "; \
	if lsof -ti :6789 >/dev/null 2>&1; then printf "OK\n"; else printf "FAIL\n"; failed=1; fi; \
	printf "  MCP Data ......... "; \
	if lsof -ti :6790 >/dev/null 2>&1; then printf "OK\n"; else printf "FAIL\n"; failed=1; fi; \
	printf "  MCP Strategy ..... "; \
	if lsof -ti :6791 >/dev/null 2>&1; then printf "OK\n"; else printf "FAIL\n"; failed=1; fi; \
	printf "  MCP Note ......... "; \
	if lsof -ti :6792 >/dev/null 2>&1; then printf "OK\n"; else printf "FAIL\n"; failed=1; fi; \
	printf "  MCP Research ..... "; \
	if lsof -ti :6793 >/dev/null 2>&1; then printf "OK\n"; else printf "FAIL\n"; failed=1; fi; \
	printf "  MCP Experience ... "; \
	if lsof -ti :6794 >/dev/null 2>&1; then printf "OK\n"; else printf "FAIL\n"; failed=1; fi; \
	echo ""; \
	if [ $$failed -eq 1 ]; then \
		echo "  [!] 部分服务异常，查看日志: make logs local"; \
		exit 1; \
	else \
		uv run python scripts/banner.py 2>/dev/null || true; \
	fi

# ============================================
# 清理
# ============================================
clean:
	@echo "清理所有环境..."
	@$(MAKE) _stop_local 2>/dev/null || true
	@$(MAKE) _stop_dev 2>/dev/null || true
	@$(MAKE) _stop_prod 2>/dev/null || true
	@rm -rf $(PID_DIR)
	@echo "清理完成"

# ============================================
# 强制清理（当 stop 无法正常工作时使用）
# ============================================
force-clean:
	@echo "强制清理所有进程和端口..."
	@echo ""
	@echo "[1/4] 清理本地进程..."
	@-pkill -9 -f "uvicorn" 2>/dev/null || true
	@-pkill -9 -f "domains.*mcp.server" 2>/dev/null || true
	@-pkill -9 -f "vite" 2>/dev/null || true
	@-pkill -9 -f "esbuild" 2>/dev/null || true
	@-pkill -9 -f "pnpm" 2>/dev/null || true
	@echo ""
	@echo "[2/4] 清理端口占用..."
	@for port in $(PORTS_TO_CLEAN) $(PORTS_PROD); do \
		pids=$$(lsof -ti :$$port 2>/dev/null); \
		if [ -n "$$pids" ]; then \
			echo "  清理端口 $$port: $$pids"; \
			echo "$$pids" | xargs kill -9 2>/dev/null || true; \
		fi; \
	done
	@echo ""
	@echo "[3/4] 清理 Docker 容器..."
	@# 停止所有 quant 相关容器（兼容 macOS，不使用 xargs -r）
	@containers=$$(docker ps -aq --filter "name=quant-" 2>/dev/null | grep -v "^$$" || true); \
	if [ -n "$$containers" ]; then \
		echo "$$containers" | xargs docker stop -t 5 2>/dev/null || true; \
		echo "$$containers" | xargs docker rm -f 2>/dev/null || true; \
	fi
	@# 清理 compose 项目
	@$(DOCKER_COMPOSE) -f $(COMPOSE_INFRA) down --remove-orphans --volumes 2>/dev/null || true
	@$(DOCKER_COMPOSE) -f $(COMPOSE_DEV) down --remove-orphans --volumes 2>/dev/null || true
	@$(DOCKER_COMPOSE) -f $(COMPOSE_PROD) down --remove-orphans 2>/dev/null || true
	@# 清理悬空网络
	@docker network prune -f 2>/dev/null || true
	@echo ""
	@echo "[4/4] 清理临时文件..."
	@rm -rf $(PID_DIR)
	@echo ""
	@# 最终验证
	@still_occupied=""; \
	for port in $(PORTS_TO_CLEAN) $(PORTS_PROD); do \
		if lsof -ti :$$port >/dev/null 2>&1; then \
			still_occupied="$$still_occupied $$port"; \
		fi; \
	done; \
	if [ -n "$$still_occupied" ]; then \
		echo "警告: 以下端口仍被占用:$$still_occupied"; \
		echo "这些可能是系统进程，请手动检查: lsof -i :<端口>"; \
	else \
		echo "所有端口已释放"; \
	fi
	@echo ""
	@echo "强制清理完成"

# ============================================
# 快捷日志查看（实时）
# ============================================
logs-api:
	@if [ -f $(PID_DIR)/api.log ]; then \
		tail -f $(PID_DIR)/api.log; \
	else \
		echo "API 日志不存在，服务可能未启动"; \
	fi

logs-mcp:
	@echo "MCP Factor:"; tail -20 $(PID_DIR)/mcp-factor.log 2>/dev/null || echo "(无日志)"
	@echo ""; echo "MCP Data:"; tail -20 $(PID_DIR)/mcp-data.log 2>/dev/null || echo "(无日志)"
	@echo ""; echo "MCP Strategy:"; tail -20 $(PID_DIR)/mcp-strategy.log 2>/dev/null || echo "(无日志)"
	@echo ""; echo "MCP Note:"; tail -20 $(PID_DIR)/mcp-note.log 2>/dev/null || echo "(无日志)"
	@echo ""; echo "MCP Research:"; tail -20 $(PID_DIR)/mcp-research.log 2>/dev/null || echo "(无日志)"
	@echo ""; echo "MCP Experience:"; tail -20 $(PID_DIR)/mcp-experience.log 2>/dev/null || echo "(无日志)"
	@echo ""; echo "实时跟踪: tail -f .pids/mcp-*.log"

logs-frontend:
	@if [ -f $(PID_DIR)/frontend.log ]; then \
		tail -f $(PID_DIR)/frontend.log; \
	else \
		echo "Frontend 日志不存在，服务可能未启动"; \
	fi

# ============================================
# 数据库备份
# ============================================
backup:
	@./scripts/backup.sh

# 启动时自动备份（本地模式，使用 quant-postgres）
_auto_backup:
	@if docker exec quant-postgres pg_isready -U quant >/dev/null 2>&1; then \
		echo "[备份] 自动备份数据库..."; \
		./scripts/backup.sh 2>&1 | grep -E "^\[INFO\]|^\[WARN\]|^\[ERROR\]" | head -2 || true; \
	fi

# 启动时自动备份（Docker 模式，等待容器就绪后备份）
_auto_backup_docker:
	@echo "[备份] 等待数据库就绪后自动备份..."
	@for i in 1 2 3 4 5; do \
		container=""; \
		if docker ps --format '{{.Names}}' | grep -q "quant-postgres-dev"; then \
			container="quant-postgres-dev"; \
		elif docker ps --format '{{.Names}}' | grep -q "quant-postgres"; then \
			container="quant-postgres"; \
		fi; \
		if [ -n "$$container" ] && docker exec $$container pg_isready -U quant >/dev/null 2>&1; then \
			./scripts/backup.sh 2>&1 | grep -E "^\[INFO\]|^\[WARN\]|^\[ERROR\]" | head -2 || true; \
			break; \
		fi; \
		sleep 2; \
	done

# ============================================
# 版本信息
# ============================================
version:
	@echo "QuantResearchMCP"
	@echo "================"
	@echo "Docker: $$(docker --version 2>/dev/null || echo '未安装')"
	@echo "Docker Compose: $$($(DOCKER_COMPOSE) version --short 2>/dev/null || echo '未安装')"
	@echo "Python: $$(python3 --version 2>/dev/null || echo '未安装')"
	@echo "uv: $$(uv --version 2>/dev/null || echo '未安装')"
	@echo "pnpm: $$(pnpm --version 2>/dev/null || echo '未安装')"
	@echo "Node: $$(node --version 2>/dev/null || echo '未安装')"

# ============================================
# MCP 工具发现
# ============================================
mcp-tools:
	@uv run python scripts/list_mcp_tools.py

mcp-tools-json:
	@uv run python scripts/list_mcp_tools.py --json

mcp-tools-summary:
	@uv run python scripts/list_mcp_tools.py --summary

# ============================================
# 私有数据同步
# ============================================
sync-export:
	@echo "导出私有数据..."
	@PYTHONPATH=backend uv run python scripts/data_sync.py export --all

sync-import:
	@echo "导入私有数据..."
	@PYTHONPATH=backend uv run python scripts/data_sync.py import --all

sync-status:
	@echo "私有数据同步状态..."
	@PYTHONPATH=backend uv run python scripts/data_sync.py status
