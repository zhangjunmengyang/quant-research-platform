"""因子查询 MCP 工具"""
from typing import Dict, Any

from domains.mcp_core import ToolResult
from domains.stock_hub.tools.base import StockBaseTool


class ListStockFactorsTool(StockBaseTool):
    """列出A股因子"""

    @property
    def name(self) -> str:
        return "stock_factor_list"

    @property
    def description(self) -> str:
        return """列出A股选股因子，支持按分类和关键词筛选。

共有约1145个因子：
- H财务因子：基于V5财务引擎的基本面因子（以H开头）
- 技术因子：量价类技术指标因子
- 截面因子：横截面统计类因子

返回因子名称、分类、描述等元数据。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "因子分类: H财务 / 技术 / 截面 / 全部",
                    "enum": ["H财务", "技术", "截面", "全部"],
                    "default": "全部",
                },
                "search": {
                    "type": "string",
                    "description": "搜索关键词（匹配因子名或说明）",
                },
                "page": {
                    "type": "integer",
                    "description": "页码（从1开始）",
                    "default": 1,
                    "minimum": 1,
                },
                "page_size": {
                    "type": "integer",
                    "description": "每页数量",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 200,
                },
            },
        }

    async def execute(self, **params) -> ToolResult:
        try:
            category = params.get("category", "全部")
            search = params.get("search")
            page = params.get("page", 1)
            page_size = params.get("page_size", 50)

            factors, total = self.stock_factor_service.list_factors(
                category=category if category != "全部" else None,
                search=search,
                page=page,
                page_size=page_size,
            )

            return ToolResult.ok({
                "factors": [
                    {
                        "name": f.name,
                        "category": f.category,
                        "library": f.library,
                        "description": f.description[:200] if f.description else "",
                        "has_fin_cols": len(f.fin_cols) > 0,
                    }
                    for f in factors
                ],
                "total": total,
                "page": page,
                "page_size": page_size,
                "categories": self.stock_factor_service.get_categories(),
            })
        except Exception as e:
            return ToolResult.fail(str(e))


class GetStockFactorTool(StockBaseTool):
    """获取单个A股因子详情"""

    @property
    def name(self) -> str:
        return "stock_factor_detail"

    @property
    def description(self) -> str:
        return """获取单个A股因子的详细信息，包括：
- 因子说明（公式、经济含义、适用范围）
- 财务字段依赖(fin_cols)
- 选股/过滤因子案例
- 源代码"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "因子名称，如 H估值_市盈率TTM、市值、Rsi",
                },
                "include_code": {
                    "type": "boolean",
                    "description": "是否返回源代码",
                    "default": False,
                },
            },
            "required": ["name"],
        }

    async def execute(self, **params) -> ToolResult:
        try:
            name = params["name"]
            include_code = params.get("include_code", False)

            factor = self.stock_factor_service.get_factor(name)
            if not factor:
                return ToolResult.fail(f"因子不存在: {name}")

            result = factor.model_dump()

            if include_code:
                code = self.stock_factor_service.get_factor_code(name)
                result["code"] = code

            return ToolResult.ok(result)
        except Exception as e:
            return ToolResult.fail(str(e))


class RefreshStockFactorsTool(StockBaseTool):
    """刷新A股因子库缓存"""

    @property
    def name(self) -> str:
        return "stock_factor_refresh"

    @property
    def description(self) -> str:
        return "重新扫描因子库目录，刷新因子元数据缓存。当因子库有新增或修改时使用。"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    async def execute(self, **params) -> ToolResult:
        try:
            self.stock_factor_service.refresh()
            categories = self.stock_factor_service.get_categories()
            total = sum(categories.values())
            return ToolResult.ok({
                "message": f"因子库已刷新，共 {total} 个因子",
                "categories": categories,
            })
        except Exception as e:
            return ToolResult.fail(str(e))
