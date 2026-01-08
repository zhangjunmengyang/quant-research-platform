# MCP 架构原理与通信架构

## 一、MCP 协议核心概念

MCP (Model Context Protocol) 是 Anthropic 提出的标准化协议，用于 LLM 应用与外部工具/数据源之间的通信。其核心架构采用 **Client-Host-Server (C-H-S)** 三层模型。

### 1.1 C-H-S 架构定义

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              HOST (宿主)                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                         LLM Application                              │ │
│  │                    (Claude Desktop / Agent)                          │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                    │                                     │
│                                    │ 创建/管理                            │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                         MCP CLIENT                                   │ │
│  │              (协议客户端, 每个 Server 对应一个)                        │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ JSON-RPC 2.0 (HTTP/SSE/stdio)
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                            MCP SERVER                                    │
│                    (工具/资源/Prompt 提供者)                              │
└──────────────────────────────────────────────────────────────────────────┘
```

| 组件 | 职责 | 示例 |
|------|------|------|
| **Host** | 宿主应用，管理 LLM 和 Client 生命周期 | Claude Desktop, LangGraph Agent, IDE 插件 |
| **Client** | 协议客户端，每个 Server 维护一个连接 | langchain-mcp-adapters, MCP SDK Client |
| **Server** | 能力提供者，暴露 Tools/Resources/Prompts | QuantResearchMCP 的各个 Hub |

### 1.2 为什么是三层而非两层?

**设计理由:**
1. **隔离性**: Host 隔离 LLM 与具体通信细节，Client 隔离协议与业务逻辑
2. **多服务器**: 一个 Host 可管理多个 Client，每个 Client 连接一个 Server
3. **安全边界**: Host 控制权限和能力协商，Server 只暴露被允许的功能
4. **生命周期**: Host 管理整体生命周期，Client 管理单个连接状态

## 二、你的系统架构

### 2.1 整体通信架构图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     quant_multi_agent (HOST + CLIENT)                           │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                          LangGraph Agent System                            │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │  │
│  │  │ Strategist  │ │   Factor    │ │   Analyst   │ │   Report    │          │  │
│  │  │    Agent    │ │    Agent    │ │    Agent    │ │    Agent    │          │  │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └─────────────┘          │  │
│  │         │               │               │                                  │  │
│  │         └───────────────┼───────────────┘                                  │  │
│  │                         │                                                  │  │
│  │                         ▼                                                  │  │
│  │  ┌───────────────────────────────────────────────────────────────────────┐│  │
│  │  │                    Tool Registry (src/tools/registry.py)              ││  │
│  │  │  ┌──────────────────────┐  ┌──────────────────────────────────────┐   ││  │
│  │  │  │     Local Tools      │  │            MCP Tools                 │   ││  │
│  │  │  │  - save_factor_code  │  │  (langchain-mcp-adapters 动态加载)   │   ││  │
│  │  │  │  - run_backtest      │  │                                      │   ││  │
│  │  │  └──────────────────────┘  └──────────────────────────────────────┘   ││  │
│  │  └───────────────────────────────────────────────────────────────────────┘│  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                        │                                        │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                     MultiServerMCPClient (CLIENT)                         │  │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐             │  │
│  │  │  factor-hub     │ │   data-hub      │ │  strategy-hub   │ ...         │  │
│  │  │    Session      │ │    Session      │ │    Session      │             │  │
│  │  └────────┬────────┘ └────────┬────────┘ └────────┬────────┘             │  │
│  └───────────┼───────────────────┼───────────────────┼───────────────────────┘  │
└──────────────┼───────────────────┼───────────────────┼──────────────────────────┘
               │                   │                   │
               │ HTTP POST         │ HTTP POST         │ HTTP POST
               │ JSON-RPC 2.0      │ JSON-RPC 2.0      │ JSON-RPC 2.0
               ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        QuantResearchMCP (SERVER)                                │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐  │
│  │   factor-hub    │ │    data-hub     │ │  strategy-hub   │ │   note-hub   │  │
│  │     :6789       │ │     :6790       │ │     :6791       │ │    :6792     │  │
│  │  ┌───────────┐  │ │  ┌───────────┐  │ │  ┌───────────┐  │ │┌───────────┐ │  │
│  │  │  Tools    │  │ │  │  Tools    │  │ │  │  Tools    │  │ ││  Tools    │ │  │
│  │  │ 13 个因子 │  │ │  │ 7 个数据  │  │ │  │ 11 个策略 │  │ ││ 4 个笔记  │ │  │
│  │  │   工具    │  │ │  │   工具    │  │ │  │   工具    │  │ ││   工具    │ │  │
│  │  ├───────────┤  │ │  ├───────────┤  │ │  ├───────────┤  │ │└───────────┘ │  │
│  │  │ Resources │  │ │  │ Resources │  │ │  │ Resources │  │ │              │  │
│  │  │ 因子详情  │  │ │  │ 市场数据  │  │ │  │ 策略配置  │  │ │              │  │
│  │  └───────────┘  │ │  └───────────┘  │ │  └───────────┘  │ │              │  │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘ └──────────────┘  │
│                                        │                                        │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                          mcp_core (统一框架)                               │  │
│  │  BaseMCPServer | ToolRegistry | ResourceProvider | JSON-RPC | SSE         │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                        │                                        │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                          业务服务层 (Services)                             │  │
│  │     factor_service  |  data_loader  |  strategy_service  |  note_service  │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                        │                                        │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                              数据层                                        │  │
│  │              PostgreSQL (pgvector)  |  Redis (缓存)                        │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 详细通信时序图

```
┌────────────────┐    ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
│  LangGraph     │    │ MultiServerMCP │    │  factor-hub    │    │ factor_service │
│    Agent       │    │    Client      │    │    Server      │    │                │
└───────┬────────┘    └───────┬────────┘    └───────┬────────┘    └───────┬────────┘
        │                     │                     │                     │
        │  1. 初始化          │                     │                     │
        │─────────────────────>                     │                     │
        │                     │  2. initialize      │                     │
        │                     │────────────────────>│                     │
        │                     │     (协商能力)      │                     │
        │                     │<────────────────────│                     │
        │                     │   capabilities      │                     │
        │                     │                     │                     │
        │  3. get_tools()     │                     │                     │
        │─────────────────────>                     │                     │
        │                     │  4. tools/list      │                     │
        │                     │────────────────────>│                     │
        │                     │<────────────────────│                     │
        │                     │   [tool definitions]│                     │
        │<─────────────────────                     │                     │
        │   LangChain Tools   │                     │                     │
        │                     │                     │                     │
        │  5. Agent 决策调用   │                     │                     │
        │  list_factors()     │                     │                     │
        │─────────────────────>                     │                     │
        │                     │  6. tools/call      │                     │
        │                     │  {name: "list_factors", arguments: {...}} │
        │                     │────────────────────>│                     │
        │                     │                     │  7. execute()       │
        │                     │                     │────────────────────>│
        │                     │                     │<────────────────────│
        │                     │                     │     results         │
        │                     │<────────────────────│                     │
        │                     │  {content: [...]}   │                     │
        │<─────────────────────                     │                     │
        │   Tool Result       │                     │                     │
        │                     │                     │                     │
```

## 三、协议层详解

### 3.1 JSON-RPC 2.0 消息格式

**请求 (Client -> Server):**
```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "list_factors",
        "arguments": {
            "search": "momentum",
            "page": 1,
            "page_size": 20
        }
    }
}
```

**响应 (Server -> Client):**
```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "content": [
            {
                "type": "text",
                "text": "{\"factors\": [...], \"total\": 100}"
            }
        ]
    }
}
```

### 3.2 MCP 协议方法

| 方法 | 方向 | 用途 |
|------|------|------|
| `initialize` | Client -> Server | 初始化连接，协商协议版本和能力 |
| `tools/list` | Client -> Server | 获取可用工具列表 |
| `tools/call` | Client -> Server | 调用指定工具 |
| `resources/list` | Client -> Server | 获取可用资源列表 |
| `resources/read` | Client -> Server | 读取指定资源 |
| `prompts/list` | Client -> Server | 获取可用 Prompt 列表 |
| `prompts/get` | Client -> Server | 获取指定 Prompt |
| `ping` | 双向 | 心跳检测 |

### 3.3 传输层

你的系统使用 **HTTP POST** 作为传输层:

```
quant_multi_agent                    QuantResearchMCP
      │                                     │
      │  POST http://localhost:6789/mcp     │
      │  Content-Type: application/json     │
      │  Body: {jsonrpc request}            │
      │─────────────────────────────────────>
      │                                     │
      │  200 OK                             │
      │  Content-Type: application/json     │
      │  Body: {jsonrpc response}           │
      │<─────────────────────────────────────
```

**其他传输选项:**
- **stdio**: 标准输入/输出（适用于本地命令行工具）
- **SSE**: Server-Sent Events（适用于流式响应）
- **WebSocket**: 全双工通信（未实现）

## 四、能力层详解

### 4.1 Tools (工具)

工具是 MCP 最核心的能力，让 LLM 可以执行操作。

**Factor Hub 工具示例:**

| 工具名 | 描述 | 参数 |
|--------|------|------|
| `list_factors` | 获取因子列表 | search, style, score_min, page |
| `get_factor` | 获取因子详情 | factor_id |
| `create_factor` | 创建新因子 | name, code, description |
| `search_by_code` | 按代码相似度搜索 | code_snippet |

**工具调用流程:**
```
LLM 决策 -> 选择工具 -> 填充参数 -> Client 发送请求 -> Server 执行 -> 返回结果
```

### 4.2 Resources (资源)

资源是只读数据源，类似 RESTful GET。

**Factor Hub 资源示例:**

| URI | 描述 |
|-----|------|
| `factor://stats` | 因子库统计信息 |
| `factor://top-scored` | 高分因子列表 |
| `factor://detail/{id}` | 特定因子详情 |

### 4.3 Prompts (提示词模板)

预定义的交互模板，LLM 可请求使用。

```json
{
    "name": "factor-analysis",
    "description": "分析因子表现的提示词模板",
    "arguments": [
        {"name": "factor_name", "required": true}
    ]
}
```

## 五、你的系统中的具体实现

### 5.1 Client 端 (quant_multi_agent)

**配置文件 `src/config/mcp.yaml`:**
```yaml
servers:
  factor-hub:
    url: "http://localhost:6789/mcp"
    transport: "http"
    timeout: 30
    description: "因子知识库服务"

  data-hub:
    url: "http://localhost:6790/mcp"
    transport: "http"
    timeout: 30

  strategy-hub:
    url: "http://localhost:6791/mcp"
    transport: "http"
    timeout: 120
```

**MCP Client 实现 (`src/tools/mcp_client.py`):**
```python
from langchain_mcp_adapters.client import MultiServerMCPClient

async def get_mcp_tools():
    """获取所有 MCP 工具，转换为 LangChain Tool 格式"""
    client = MultiServerMCPClient(
        connections={
            "factor-hub": {"url": "http://localhost:6789/mcp", "transport": "http"},
            "data-hub": {"url": "http://localhost:6790/mcp", "transport": "http"},
            # ...
        }
    )
    return await client.get_tools()
```

### 5.2 Server 端 (QuantResearchMCP)

**MCP Server 实现 (`domains/mcp_core/server/server.py`):**
```python
class BaseMCPServer:
    """MCP 服务器基类"""

    async def handle_request(self, request: JSONRPCRequest):
        """处理 JSON-RPC 请求"""
        if request.method == "initialize":
            return self._handle_initialize(request.params)
        elif request.method == "tools/list":
            return self._handle_tools_list()
        elif request.method == "tools/call":
            return await self._handle_tools_call(request.params)
        # ...
```

**Factor Hub Server (`domains/factor_hub/api/mcp/server.py`):**
```python
class FactorHubMCPServer(BaseMCPServer):
    def _setup(self):
        # 注册工具
        self.register_tool(ListFactorsTool(), "query")
        self.register_tool(GetFactorTool(), "query")
        self.register_tool(CreateFactorTool(), "mutation")
        # ...

        # 注册资源
        self.set_resource_provider(FactorResourceProvider())
```

## 六、C-H-S 架构的优势

### 6.1 解耦与扩展性

```
                    ┌─────────────────┐
                    │   新增 Agent    │
                    │  (无需改动)     │
                    └────────┬────────┘
                             │
┌────────────────────────────┼────────────────────────────┐
│                     HOST Layer                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              MultiServerMCPClient                │   │
│  │     (自动发现所有 Server 的 Tools)               │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────────────┼────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  factor-hub   │   │   data-hub    │   │  新增 Server  │
│   (现有)      │   │    (现有)     │   │  (即插即用)   │
└───────────────┘   └───────────────┘   └───────────────┘
```

### 6.2 安全边界

```
┌─────────────────────────────────────────────────────────────┐
│                      HOST (安全控制层)                       │
│  - 控制哪些 Server 可连接                                    │
│  - 过滤敏感操作                                              │
│  - 审计日志                                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ 只暴露允许的能力
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      SERVER (能力提供层)                     │
│  - 声明可用工具                                              │
│  - 实现业务逻辑                                              │
│  - 不知道调用者是谁                                          │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 你的系统的具体优势

1. **关注点分离**: quant_multi_agent 专注 Agent 编排，QuantResearchMCP 专注量化能力
2. **独立部署**: 两个项目可独立开发、测试、部署
3. **多客户端**: QuantResearchMCP 可同时服务多个 Agent 系统
4. **动态发现**: 新增工具自动被 Agent 发现和使用

## 七、总结

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            MCP C-H-S 架构总结                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         HOST (quant_multi_agent)                     │   │
│  │  - LangGraph Agent 编排                                              │   │
│  │  - 管理多个 MCP Client                                               │   │
│  │  - 控制工具访问权限                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│                                      │ 创建/管理                            │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                   CLIENT (langchain-mcp-adapters)                    │   │
│  │  - 维护与 Server 的连接                                              │   │
│  │  - 协议转换 (MCP -> LangChain Tool)                                  │   │
│  │  - 会话状态管理                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│                                      │ JSON-RPC 2.0 over HTTP               │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      SERVER (QuantResearchMCP)                       │   │
│  │  - 暴露 Tools / Resources / Prompts                                  │   │
│  │  - 执行实际业务逻辑                                                   │   │
│  │  - 与数据库/外部服务交互                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

关键设计原则:
1. Host 是"大脑" - 决定做什么
2. Client 是"手" - 负责通信
3. Server 是"工具箱" - 提供能力
```
