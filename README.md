# Quant Research Platform

一个 LLM 原生的量化研究平台，提供因子管理、策略回测、研报分析等功能，并通过 MCP 协议让 AI 助手直接访问量化知识库。

## Features

- **因子知识库** - 因子管理、评分、分析
- **策略回测** - 策略管理、参数搜索
- **研报知识库** - PDF 上传、RAG 对话
- **经验知识库** - 结构化研究经验、语义检索、知识提炼
- **数据服务** - K线数据、因子计算
- **MCP 协议** - LLM 直接访问量化知识库

## Quick Start

### 1. 安装依赖

按顺序安装以下依赖:

| 序号 | 依赖 | macOS / Linux | Windows |
|:----:|------|---------------|---------|
| 1 | Docker | [下载 Docker Desktop](https://www.docker.com/products/docker-desktop/) | [下载 Docker Desktop](https://www.docker.com/products/docker-desktop/) |
| 2 | Node.js 20+ | [下载](https://nodejs.org/) 或 `brew install node` | [下载安装包](https://nodejs.org/) |
| 3 | pnpm | `npm install -g pnpm` | `npm install -g pnpm` |
| 4 | uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `irm https://astral.sh/uv/install.ps1 \| iex` |

> **Windows 提示**: 安装完成后需要重启终端使环境变量生效

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env
```

编辑 `.env` 文件，填入以下必要配置:

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `PRE_DATA_PATH` | 预处理K线数据路径 | `/Users/xxx/Downloads/coin-binance-spot-swap-preprocess-pkl-1h` |
| `COIN_CAP_PATH` | 市值数据路径 (可选) | `/Users/xxx/Downloads/coin-cap` |
| `LLM_API_URL` | LLM API 地址 | `https://api.openai.com/v1` |
| `LLM_API_KEY` | LLM API 密钥 | `sk-xxx` |

### 3. 启动项目

**macOS / Linux:**

```bash
# 克隆项目
git clone https://github.com/your-username/quant-research-platform.git
cd quant-research-platform

# 启动（自动安装依赖、启动数据库、启动服务）
make start local

# 查看服务状态
make status

# 查看日志
make logs local

# 停止服务
make stop local
```

**Windows (PowerShell):**

```powershell
# 一键启动（自动安装依赖、启动所有服务、打开浏览器）
uv run python scripts/dev.py start

# 停止所有服务
uv run python scripts/dev.py stop

# 查看服务状态
uv run python scripts/dev.py status

# 查看日志
uv run python scripts/dev.py logs              # 全部服务
uv run python scripts/dev.py logs api           # 仅 API
uv run python scripts/dev.py logs -n 100 mcp-factor  # 最近 100 行
```

> `scripts/dev.py` 是跨平台任务运行器，也可在 macOS/Linux 上使用，等价于 `make start local`。
> 该脚本会自动启动 PostgreSQL、Redis、API、7 个 MCP 服务和前端，无需手动开多个终端。

### 4. 访问服务

启动后访问:
- 前端界面: http://127.0.0.1:5173
- API 文档: http://127.0.0.1:8000/docs

## MCP Integration

通过 MCP 协议，LLM 可以直接访问平台的所有功能。

### Claude 配置

在 `.mcp.json` 中添加:

```json
{
  "mcpServers": {
    "factor-hub": {
      "url": "http://localhost:6789/mcp"
    },
    "data-hub": {
      "url": "http://localhost:6790/mcp"
    },
    "strategy-hub": {
      "url": "http://localhost:6791/mcp"
    },
    "note-hub": {
      "url": "http://localhost:6792/mcp"
    },
    "research-hub": {
      "url": "http://localhost:6793/mcp"
    },
    "experience-hub": {
      "url": "http://localhost:6794/mcp"
    }
  }
}
```

## Development

### 目录结构

```
quant-research-platform/
├── backend/
│   ├── app/routes/          # HTTP 路由层
│   ├── app/schemas/         # Pydantic 模型
│   └── domains/             # 业务域
│       ├── mcp_core/        # MCP 基础设施
│       ├── factor_hub/      # 因子知识库
│       ├── strategy_hub/    # 策略回测
│       ├── research_hub/    # 研报 RAG
│       ├── experience_hub/  # 经验知识库
│       ├── data_hub/        # 数据服务
│       └── note_hub/        # 笔记管理
├── frontend/
│   └── src/
│       ├── features/        # 功能模块
│       ├── components/      # 通用组件
│       └── lib/             # 工具库
├── docker/                  # 容器配置
├── docs/                    # 文档
└── factors/                 # 因子定义库
```

### 常用命令

```
# 开发
make start local          # 本地开发模式
make start dev            # Docker 开发模式
make logs-api             # API 实时日志
make logs-frontend        # 前端实时日志

# 生产
make start                # 生产模式
make healthcheck prod     # 健康检查
```

### 运行模式

| 模式 | 命令 | 说明 |
|------|------|------|
| local | `make start local` | 本地运行 Python/Node，仅 Docker 运行数据库 |
| dev | `make start dev` | 全容器化，支持热重载 |
| prod | `make start` | 全容器化，优化构建 |

## Tech Stack

**Backend**
- FastAPI, SQLAlchemy 2.0, PostgreSQL 16 + pgvector
- LangChain, Redis, aiohttp
- structlog, ruff, pytest

**Frontend**
- React 18, TypeScript, Vite 6
- TanStack Query, Zustand, shadcn/ui
- AG Grid, ECharts, Tailwind CSS

**Infrastructure**
- Docker, Docker Compose, Caddy, Supervisor

## License

MIT

---

## 重要更新

**因子和截面因子文件已迁移至 `private/` 目录。**

```
# 旧位置（已废弃）
factors/
sections/

# 新位置
private/
  factors/      # 因子代码 (.py)
  sections/     # 截面因子 (.py)
  metadata/     # 因子元数据 (YAML)
```

`private/` 目录已被 gitignore，需通过独立的私有仓库管理。详见 `private/.gitkeep`。
