# 任务: 添加 MCP 工具

## 完整流程

```
1. backend/domains/*/api/mcp/tools/ -> 创建工具类继承 BaseTool
2. 设置 execution_mode（FAST/COMPUTE）
3. 实现 name, description, input_schema, execute 方法
4. 在 server.py 的 _setup() 中注册
```

## 执行模式

| 模式 | 适用场景 | 执行方式 | 超时 |
|------|---------|---------|------|
| FAST | I/O 密集型（< 100ms） | 直接 async | 5s |
| COMPUTE | CPU 密集型任务 | 专用执行器 (BacktestRunner) | 3600s |

## 实现示例

### 1. 创建工具类

```python
# backend/domains/factor_hub/api/mcp/tools/custom_tool.py
from domains.mcp_core.base.tool import BaseTool, ToolResult, ExecutionMode

class CustomAnalysisTool(BaseTool):
    category = "analysis"
    execution_mode = ExecutionMode.COMPUTE
    execution_timeout = 60.0

    @property
    def name(self) -> str:
        return "custom_analysis"

    @property
    def description(self) -> str:
        return "执行自定义因子分析"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "factor_name": {"type": "string", "description": "因子名称"},
                "option": {"type": "string", "enum": ["a", "b", "c"]},
            },
            "required": ["factor_name"],
        }

    async def execute(self, factor_name: str, option: str = "a") -> ToolResult:
        try:
            from ....services import get_custom_service
            service = get_custom_service()
            result = service.analyze(factor_name, option)
            return ToolResult.ok(result)
        except Exception as e:
            return ToolResult.fail(str(e))
```

### 2. 注册工具

```python
# backend/domains/factor_hub/api/mcp/server.py
class FactorHubMCPServer(BaseMCPServer):
    def _setup(self):
        from .tools.custom_tool import CustomAnalysisTool
        self.register_tool(CustomAnalysisTool())
```

## 现有工具分类

| 类别 | 工具 | 模式 |
|------|------|------|
| query | list_factors, get_factor, search_by_code | FAST |
| mutation | update_factor, create_factor | FAST |
| analysis | analyze_factor, get_factor_ic, compare_factors | COMPUTE |
