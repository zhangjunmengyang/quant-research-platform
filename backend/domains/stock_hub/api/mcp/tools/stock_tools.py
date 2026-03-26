"""Stock Hub MCP 工具。"""

from typing import Any

from .base import BaseTool, ToolResult


class StockFactorListTool(BaseTool):
    """因子列表查询工具。"""

    @property
    def name(self) -> str:
        return "stock_factor_list"

    @property
    def description(self) -> str:
        return """搜索和列出A股因子库中的因子。

支持按分类(H财务/技术/截面)和关键词搜索。
返回因子名称、分类、描述等信息。

使用场景:
- 浏览因子库
- 搜索特定因子
- 按分类筛选因子"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "search": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "category": {
                    "type": "string",
                    "description": "分类: H财务, 技术, 截面",
                    "enum": ["H财务", "技术", "截面"],
                },
                "page": {
                    "type": "integer",
                    "description": "页码",
                    "default": 1,
                },
                "page_size": {
                    "type": "integer",
                    "description": "每页数量",
                    "default": 20,
                },
            },
        }

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        svc = self._get_service()
        items, total = svc.list_factors(
            page=arguments.get("page", 1),
            page_size=arguments.get("page_size", 20),
            search=arguments.get("search", ""),
            category=arguments.get("category", ""),
        )
        names = [f["name"] for f in items]
        return ToolResult(
            content=f"共 {total} 个因子 (当前页 {len(names)} 个):\n" + "\n".join(names),
            metadata={"total": total, "items": items},
        )


class StockFactorDetailTool(BaseTool):
    """因子详情查询工具。"""

    @property
    def name(self) -> str:
        return "stock_factor_detail"

    @property
    def description(self) -> str:
        return """查看A股因子的详情和元数据。

返回因子的分类、描述、参数等信息。"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "因子名称",
                },
            },
            "required": ["name"],
        }

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        svc = self._get_service()
        detail = svc.get_factor_detail(arguments["name"])
        if not detail:
            return ToolResult(content=f"因子不存在: {arguments['name']}", is_error=True)
        lines = [
            f"因子: {detail['name']}",
            f"分类: {detail.get('category', '')}",
            f"描述: {detail.get('description', '')}",
        ]
        fin_cols = detail.get("fin_cols", [])
        ov_cols = detail.get("ov_cols", [])
        if fin_cols:
            lines.append(f"财务列: {', '.join(fin_cols)}")
        if ov_cols:
            lines.append(f"行情列: {', '.join(ov_cols)}")
        return ToolResult(content="\n".join(lines), metadata=detail)
