# 任务: 添加新业务域

## 完整流程

```
1. 创建目录结构: domains/new_hub/{core,services,api/mcp/tools,tasks}
2. 实现核心模型和存储层 (core/)
3. 实现服务层 (services/)
4. 实现 MCP 服务器继承 BaseMCPServer
5. 添加 Makefile/supervisord 配置
```

## 目录结构

```bash
mkdir -p backend/domains/new_hub/{core,services,api/mcp/tools,tasks}
touch backend/domains/new_hub/__init__.py
touch backend/domains/new_hub/core/{__init__,models,store}.py
touch backend/domains/new_hub/services/{__init__,new_service}.py
touch backend/domains/new_hub/api/mcp/{__init__,server}.py
```

## 实现示例

### 1. 核心模型

```python
# backend/domains/new_hub/core/models.py
from dataclasses import dataclass

@dataclass
class NewEntity:
    id: str
    name: str
    # ...
```

### 2. 存储层

```python
# backend/domains/new_hub/core/store.py
class NewStore:
    def __init__(self):
        self.database_url = get_database_url()

    def get(self, id: str) -> Optional[NewEntity]:
        ...

    def add(self, entity: NewEntity) -> bool:
        ...
```

### 3. 服务层

```python
# backend/domains/new_hub/services/new_service.py
class NewService:
    def __init__(self, store: NewStore):
        self.store = store

    def create(self, data: dict) -> NewEntity:
        # 业务逻辑
        pass
```

### 4. MCP 服务器

```python
# backend/domains/new_hub/api/mcp/server.py
from domains.mcp_core import BaseMCPServer, MCPConfig, run_server

class NewHubMCPServer(BaseMCPServer):
    def __init__(self, config=None):
        if config is None:
            config = MCPConfig(
                server_name="new-hub",
                port=6793,
            )
        super().__init__(config)

    def _setup(self):
        from .tools.query_tools import ListTool, GetTool
        from .tools.mutation_tools import CreateTool

        self.register_tool(ListTool())
        self.register_tool(GetTool())
        self.register_tool(CreateTool())

if __name__ == "__main__":
    server = NewHubMCPServer()
    run_server(server)
```

### 5. Makefile 配置

在 Makefile 的 `_start_local` 中添加：

```makefile
@PYTHONPATH=backend ... \
    nohup uv run python -m domains.new_hub.api.mcp.server \
    > $(PID_DIR)/new-hub.log 2>&1 & echo $$! > $(PID_DIR)/new-hub.pid
```

## 依赖规则

- 只依赖 mcp_core 和 engine
- 不依赖其他业务域（factor_hub, strategy_hub, data_hub）
- 保持扁平对等架构
