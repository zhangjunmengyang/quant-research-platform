# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

本文件为 Claude Code 提供项目指导说明。所有的工作语言均使用中文，文档和编码不要使用 emoji。

## 工作模式 (最重要)

**核心原则: 你是调度者，不是执行者。**

不要事必躬亲。你的角色是:
- 理解用户意图，拆解任务
- 分发任务给 SubAgent
- 审核结果，做出判断
- 统筹全局，确保一致性

```
用户需求 -> 拆解任务 -> 分发给 SubAgent -> 审核结果 -> 交付
```

**不重复造轮子**

绝对不要重复造轮子。优先使用成熟的、能满足需求的组件，评估标准：
1. 是否是经典/常见需求（如 LLM 调用、配置管理）
2. 是否有成熟的开源方案
3. 引入成本 vs 自己实现的维护成本

反模式: 用 aiohttp 手写 LLM 调用逻辑（应使用 mcp_core/llm/）

**不实现临时方案**

- 不仅仅为了快速完成，不顾架构实现短期方案。
- 不仅仅考虑当前功能，而忽略整体架构、项目分层、设计规范。
- 应当以长期主义视角维护项目，避免临时方案和遗留任务。
- 应当及时清理冗余、废弃的代码、文件结构，以维护仓库整洁。

### 反模式 (避免)

- 自己逐个读取文件探索代码库 -> 应使用 Explore agent
- 自己一步步实现复杂功能 -> 应使用 general-purpose agent
- 串行执行多个独立任务 -> 应并行分发多个 Task

### 并行执行

多个独立任务必须并行分发:
```
单条消息中包含多个 Task 工具调用 -> 并行执行 -> 汇总结果
```

## 文档维护 (重要)

代码变更后，必须同步更新相关文档:

| 变更类型 | 需要更新的文档 |
|---------|---------------|
| 新增/删除业务域 | `CLAUDE.md` (业务域表), `docs/architecture/reference.md`, `docs/architecture/tasks/add-domain.md` |
| 新增/修改 API 端点 | `docs/architecture/tasks/add-api-endpoint.md` (如果引入新模式) |
| 新增/修改 MCP 工具 | `docs/architecture/tasks/add-mcp-tool.md` (如果引入新模式) |
| 修改服务端口 | `CLAUDE.md` (服务端口表) |
| 修改目录结构 | `CLAUDE.md` (核心架构), `docs/architecture/reference.md` |
| 新增开发约定 | `CLAUDE.md` (关键约定) |
| 修改部署配置 | `Makefile` 或 `docker/` 目录下的 README |

**原则**: 文档是给未来的 Claude 和开发者看的，保持准确性是对他们的尊重。

## 项目概述

量化因子加工厂 - 币圈交易因子的系统性提取、文档化和分析平台。

## 快速命令

### macOS / Linux

```bash
make start local     # 启动（自动安装依赖）
make stop local      # 停止
make status          # 状态
make logs local      # 日志
make test            # 运行测试
```

### Windows (PowerShell)

Windows 用户请参考 README.md 中的手动启动步骤。

## 服务端口

| 服务 | 端口 |
|------|------|
| Frontend | 5173 |
| API | 8000 |
| factor-hub (MCP) | 6789 |
| data-hub (MCP) | 6790 |
| strategy-hub (MCP) | 6791 |
| note-hub (MCP) | 6792 |
| research-hub (MCP) | 6793 |
| experience-hub (MCP) | 6794 |
| PostgreSQL | 5432 |
| Redis | 6379 |

## 核心架构

```
backend/app/routes/         -> HTTP 层
backend/app/schemas/        -> Schema 层
backend/domains/*/services/ -> 服务层
backend/domains/*/core/     -> 核心层
frontend/src/features/*/    -> 前端模块
```

### 业务域

| 域 | 目录 | 职责 | 知识层级 |
|----|------|------|---------|
| mcp_core | domains/mcp_core/ | MCP 基础设施 (最底层) | - |
| engine | domains/engine/ | 回测引擎核心 | - |
| data_hub | domains/data_hub/ | 市场数据层 | Data |
| factor_hub | domains/factor_hub/ | 因子知识库 | Artifact |
| strategy_hub | domains/strategy_hub/ | 策略知识库 | Artifact |
| note_hub | domains/note_hub/ | 研究笔记 (临时记录) | Knowledge |
| research_hub | domains/research_hub/ | 外部研报 (RAG ChatBot) | Knowledge |
| experience_hub | domains/experience_hub/ | 经验知识库 (长期记忆) | Wisdom |

**知识层级说明**: Data -> Artifact -> Knowledge -> Wisdom，详见 `docs/architecture/knowledge-experience-system.md`

**依赖方向**: routes -> services -> core，业务域互不依赖

**禁止修改**: `backend/domains/engine/core/`

## 关键约定

- **API 路径**: 不使用尾部斜杠
- **Schema**: 复数命名 (`strategies.py`)
- **Service**: 单数命名 (`backtest.py`)
- **前端类型**: 镜像后端 Pydantic
- **ECharts**: 禁止 ResizeObserver

## 开发任务

执行开发任务前，先读取对应文档:

| 任务 | 文档路径 |
|------|---------|
| 添加 API | `docs/architecture/tasks/add-api-endpoint.md` |
| 添加 MCP 工具 | `docs/architecture/tasks/add-mcp-tool.md` |
| 添加异步任务 | `docs/architecture/tasks/add-async-task.md` |
| 添加业务域 | `docs/architecture/tasks/add-domain.md` |
| 添加前端功能 | `docs/architecture/tasks/add-frontend-feature.md` |

深入了解架构: `docs/architecture/reference.md`

知识与经验体系: `docs/architecture/knowledge-experience-system.md`

## 研究任务

执行研究任务时，使用对应的 Skill:

| Skill | 命令 | 用途 |
|-------|------|------|
| factor-research | `/factor-research` | 因子优化研究。针对具体因子进行参数优化、逻辑改进和条件分析，使用回测引擎验证效果 |
| market-research | `/market-research` | 市场规律研究。深入分析币种数据，发现规律，验证假设，生成经验文档 |
| factor-select | `/factor-select` | 因子圈选与更新。查询筛选因子，批量更新字段值 |

Skill 详情见 `.claude/skills/*/SKILL.md`

## 代码规范

- **Python**: ruff，类型注解
- **TypeScript**: biome，避免 any
- **Git**: `<type>: <description>`