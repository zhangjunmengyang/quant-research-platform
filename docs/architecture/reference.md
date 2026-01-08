# 架构参考

本文档提供架构全景，供深入了解时阅读。执行具体任务请阅读 tasks/ 目录下的任务文档。

## 1. 项目定位

量化因子加工厂 - 币圈交易因子的系统性提取、文档化和分析平台。通过 MCP 让 LLM 直接访问因子库。

## 2. 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+, FastAPI, Redis, PostgreSQL 16 + pgvector |
| 前端 | React 18 + TypeScript, Vite, TanStack Query + Zustand, shadcn/ui + Tailwind, ECharts |
| 部署 | Docker + Docker Compose, Caddy, Supervisor |

## 3. 分层架构

```
backend/
  app/                    # HTTP 层
    routes/v1/            # REST API 路由
    schemas/              # Pydantic 模型
    core/                 # 配置、依赖注入

  domains/                # 领域层
    mcp_core/             # MCP 基础设施 (最底层)
    engine/               # 量化引擎核心 (禁止修改 core/)
    factor_hub/           # 因子知识库
    strategy_hub/         # 策略知识库
    data_hub/             # 数据层
    note_hub/             # 笔记知识库
    research_hub/         # 研报知识库 (RAG ChatBot)
    experience_hub/       # 经验知识库 (长期记忆)
```

### 依赖方向

```
mcp_core (基础设施)
    ^
    |
  engine (量化引擎)
    ^
    +--------+--------+
    |        |        |
data_hub factor_hub strategy_hub   (扁平对等，互不依赖)

note_hub (仅依赖 mcp_core)

research_hub (依赖 mcp_core, 使用 pgvector)

experience_hub (依赖 mcp_core, 使用 pgvector, 知识图谱)
```

### 知识层级架构

系统采用 DIKW (Data-Information-Knowledge-Wisdom) 知识金字塔模型:

```
          Wisdom Layer (智慧层)
              experience_hub
                    |
         Knowledge Layer (知识层)
          note_hub + research_hub
                    |
         Artifact Layer (产出层)
        factor_hub + strategy_hub
                    |
           Data Layer (数据层)
              data_hub
```

| 层级 | 业务域 | 职责 | 内容特征 |
|------|-------|------|---------|
| Wisdom | experience_hub | 可迁移的研究智慧 | 抽象、经验证、长期有效 |
| Knowledge | note_hub, research_hub | 研究过程记录、外部输入 | 临时、待整理 |
| Artifact | factor_hub, strategy_hub | 研究产出 | 结构化、可执行 |
| Data | data_hub | 市场原始数据 | 事实、客观 |

详见 [知识与经验体系设计](knowledge-experience-system.md)

## 4. 服务组成

| 服务 | 端口 | 职责 |
|------|------|------|
| Frontend | 5173 | React 前端 |
| API | 8000 | FastAPI REST |
| factor-hub | 6789 | 因子 CRUD、分析 |
| data-hub | 6790 | K 线数据访问 |
| strategy-hub | 6791 | 回测、策略管理 |
| note-hub | 6792 | 笔记管理 |
| research-hub | 6793 | 研报 RAG 对话 |
| experience-hub | 6794 | 经验知识库 |
| PostgreSQL | 5432 | 持久化存储 |
| Redis | 6379 | 任务队列 + 缓存 |

## 5. 业务域概览

### 5.1 engine - 量化引擎

```
engine/
  core/              # 回测引擎核心 (禁止修改)
    backtest.py      # 回测主流程
    select_coin.py   # 因子计算 + 选币
    simulator.py     # 交易模拟器
  services/          # 数据加载、因子计算服务
  chart_utils.py     # Plotly 绘图函数
```

### 5.2 factor_hub - 因子知识库

```
factor_hub/
  core/              # Factor 模型 + FactorStore
  services/          # FactorService, FieldFiller, 分析服务
  api/mcp/           # MCP 服务器 + 工具
  tasks/             # Pipeline 任务处理器
  cli/               # CLI 命令
```

### 5.3 strategy_hub - 策略知识库

```
strategy_hub/
  services/          # BacktestRunner, TaskStore, 参数搜索
  api/mcp/           # MCP 服务器 + 工具
  utils/             # 数据处理、绘图函数
```

### 5.4 data_hub - 数据层

```
data_hub/
  services/          # 代理 engine 的数据加载、因子计算
  api/mcp/           # MCP 服务器 + 工具 + 资源
```

### 5.5 note_hub - 笔记库

最简单的业务域，可作为新模块参考模板。

### 5.6 research_hub - 研报知识库

研报 RAG ChatBot 系统，支持 PDF 上传、解析、向量检索和对话。

```
research_hub/
  core/              # 配置、模型、存储
    config.py        # YAML 配置加载
    models.py        # ResearchReport, Chunk, Conversation
    store.py         # ResearchStore, ChunkStore, ConversationStore
  agents/            # Agent 应用层
    base.py          # BaseAgent 抽象类、AgentConfig、AgentResponse
    research_chat.py # ResearchChatAgent (单研报对话)
  rag/               # 模块化 RAG 组件 (数据处理层)
    base/            # 抽象基类 + 注册表
    parsers/         # PDF 解析器 (MinerU, PyMuPDF)
    chunkers/        # 文档切分器
    embedders/       # 嵌入模型 (BGE-M3, OpenAI)
    vector_stores/   # 向量存储 (pgvector)
    retrievers/      # 检索器 (Dense, Hybrid)
    rerankers/       # 重排器 (BGE, Cohere)
    generators/      # 生成器 (LLM)
    pipelines/       # 流水线编排
  services/          # ChatBotService, ReportService
```

**架构分层**:
```
Agent 层 (应用层)
    |-- 管理对话流程、模型选择、工具调用
    |-- ResearchChatAgent, LibraryChatAgent, BriefingAgent...
    v
RAG Pipeline (数据处理层)
    |-- 检索 (Retriever) -> 重排 (Reranker) -> 生成 (Generator)
    v
LLM Client (基础设施层)
    |-- mcp_core/llm/
```

**设计特点**:
- Agent/RAG 分离: RAG 负责数据处理，Agent 负责应用逻辑
- 组件注册表模式，支持 A/B 测试
- 配置驱动的流水线创建
- 动态模型切换 (通过 model_key 参数)

**扩展场景**:

| 场景 | Agent | 说明 |
|------|-------|------|
| 单研报对话 | ResearchChatAgent | 已实现 |
| 全库对话 | LibraryChatAgent | 跨研报检索 |
| 知识简报 | BriefingAgent | 定时生成摘要 |
| 研报比较 | CompareAgent | 多研报对比分析 |

### 5.7 experience_hub - 经验知识库

经验知识库系统，存储结构化的研究经验，支持语义检索、生命周期管理和知识图谱。

```
experience_hub/
  core/              # 配置、模型、存储
    config.py        # 配置加载
    models.py        # Experience, ExperienceContent, ExperienceContext, ExperienceLink
    store.py         # ExperienceStore (PostgreSQL + pgvector)
    schema.sql       # 数据库表结构定义
  services/          # 业务服务层
    experience.py    # ExperienceService
  api/mcp/           # MCP 服务器
    server.py        # ExperienceHubMCPServer
    tools/           # MCP 工具
      experience_tools.py  # CRUD + 检索 + 生命周期管理工具
  tasks/             # 异步任务
    curate.py        # 经验提炼任务
```

**核心概念**:

| 概念 | 说明 |
|------|------|
| Experience Level | strategic(战略级)、tactical(战术级)、operational(操作级) |
| PARL 框架 | Problem-Approach-Result-Lesson 结构化内容 |
| Experience Status | draft(草稿)、validated(已验证)、deprecated(已废弃) |
| Experience Context | market_regime、factor_styles、time_horizon、asset_class、tags |

**MCP 工具**:

| 工具 | 功能 |
|------|------|
| store_experience | 存储新经验 |
| query_experiences | 语义检索经验 |
| get_experience | 获取单个经验详情 |
| list_experiences | 列出经验（支持筛选） |
| validate_experience | 验证经验（增加置信度） |
| deprecate_experience | 废弃经验 |
| link_experience | 关联经验与其他实体 |
| curate_experience | 从低层经验提炼高层经验 |

### 5.8 知识图谱模块

知识图谱用于存储实体和关系，支持语义搜索和图遍历。

**数据库表**:

| 表 | 职责 |
|----|------|
| kg_entities | 实体表（factor, strategy, market_regime, concept 等） |
| kg_relations | 关系表（related_to, derived_from, effective_in 等） |

**实体类型**: factor, strategy, market_regime, concept, metric, time_window, asset, parameter, condition, action

**关系类型**: related_to, derived_from, belongs_to, effective_in, conflicts_with, optimized_by, composed_of, outperforms_in, causes, indicates, precedes, follows, has_parameter, sensitive_to, applies_to, requires

## 6. MCP 工具执行模式

| 模式 | 执行方式 | 超时 | 场景 |
|------|---------|------|------|
| FAST | 直接 async | 5s | list_*, get_* |
| COMPUTE | 专用执行器 (BacktestRunner) | 3600s | run_backtest, analyze_* |

## 7. 前端架构

```
frontend/src/
  components/        # 通用组件 (charts/, layout/, ui/)
  features/          # 功能模块 (factor/, strategy/, data/, note/, log/, research/)
  pages/             # 页面组件
  lib/               # API 客户端、工具函数
```

### Feature 模块结构

```
features/xxx/
  components/        # 模块专用组件
  types.ts           # 类型定义 (镜像后端 Schema)
  api.ts             # API 客户端
  hooks.ts           # React Query Hooks
  store.ts           # Zustand Store (如需要)
```

### Research 模块组件

```
features/research/
  components/
    PDFViewer.tsx      # PDF 预览 (react-pdf)
    ModelSelector.tsx  # LLM 模型选择器
  types.ts             # LLMModel, ChatRequest, Message...
  api.ts               # getModels, getPdfUrl, chatStream...
  hooks.ts             # useModels, useReport, useConversations...
```

### 关键规范

- **API 路径**: 不使用尾部斜杠
- **类型**: 镜像后端 Pydantic，避免 any
- **ECharts**: 禁止 ResizeObserver，用 window.resize

## 8. LLM 基础设施

`mcp_core/llm/` 提供基于 LangChain 的 LLM 调用能力:

```
mcp_core/llm/
  config.py            # LLMSettings (从 llm_models.yaml 加载)
  client.py            # LLMClient (LangChain 封装)
```

### 使用方式

```python
from domains.mcp_core.llm import get_llm_client

client = get_llm_client()
result = await client.ainvoke(
    messages=[{"role": "user", "content": "..."}],
    model_key="claude",      # 可选，覆盖默认模型
    temperature=0.8,         # 可选，覆盖模型配置
    caller="field_filler",   # 调用方标识 (日志)
    purpose="fill_style",    # 调用目的 (日志)
)
```

### 配置优先级

1. 调用参数 (temperature, max_tokens)
2. llm_models.yaml 中模型配置
3. llm_models.yaml 默认配置

### 日志集成

LLMClient 自动与 `observability/llm_logger.py` 集成，记录:
- 请求/响应内容
- Token 统计
- 性能指标
- 错误追踪

## 9. 任务管理

CPU 密集型任务由专用执行器管理:

- **BacktestRunner**: 使用 ThreadPoolExecutor 管理回测任务
- **TaskQueue**: 基于 Redis 的轻量级任务状态追踪（可选）

```python
# 回测任务提交
runner = get_backtest_runner()
runner.submit(task_id, params)

# 查询状态
status = runner.get_status(task_id)
```

状态流转: `pending -> running -> completed/failed`
