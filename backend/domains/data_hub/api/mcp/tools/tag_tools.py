"""
实体标签 MCP 工具

提供实体标签的管理功能，用于给币种、因子、策略等打标签。
支持构建币池（如妖币池）并进行后续研究。
"""

from typing import Any, Dict

from .base import BaseTool, ToolResult

from domains.mcp_core.edge import (
    EdgeEntityType,
    get_edge_store,
)


class AddTagTool(BaseTool):
    """添加标签工具"""

    @property
    def name(self) -> str:
        return "add_tag"

    @property
    def description(self) -> str:
        return """给实体添加标签。

用于给币种、因子、策略等实体打标签，便于分类管理和研究。

典型使用场景:
- 给币种打标签构建币池（如：妖币、蓝筹、DeFi）
- 给因子打标签分类（如：动量类、反转类）
- 给策略打标签（如：高频、低频、趋势）

示例:
- 给 BTC-USDT 打上"蓝筹"标签
- 给 DOGE-USDT 打上"妖币"标签"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": "实体类型",
                    "enum": ["data", "factor", "strategy", "note", "research", "experience"]
                },
                "entity_id": {
                    "type": "string",
                    "description": "实体 ID（如：BTC-USDT、Momentum_5d）"
                },
                "tag": {
                    "type": "string",
                    "description": "标签名称（如：妖币、蓝筹、高波动）"
                }
            },
            "required": ["entity_type", "entity_id", "tag"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            entity_type_str = params.get("entity_type")
            entity_id = params.get("entity_id")
            tag = params.get("tag", "").strip()

            if not tag:
                return ToolResult(success=False, error="标签名称不能为空")

            try:
                entity_type = EdgeEntityType(entity_type_str)
            except ValueError:
                return ToolResult(success=False, error=f"无效的实体类型: {entity_type_str}")

            edge_store = get_edge_store()

            # 检查是否已存在
            if edge_store.has_tag(entity_type, entity_id, tag):
                return ToolResult(
                    success=True,
                    data={
                        "entity_type": entity_type_str,
                        "entity_id": entity_id,
                        "tag": tag,
                        "message": "标签已存在"
                    }
                )

            edge_id = edge_store.add_tag(entity_type, entity_id, tag)

            if edge_id:
                return ToolResult(
                    success=True,
                    data={
                        "edge_id": edge_id,
                        "entity_type": entity_type_str,
                        "entity_id": entity_id,
                        "tag": tag,
                        "message": "添加标签成功"
                    }
                )
            else:
                return ToolResult(success=False, error="添加标签失败")

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class RemoveTagTool(BaseTool):
    """移除标签工具"""

    @property
    def name(self) -> str:
        return "remove_tag"

    @property
    def description(self) -> str:
        return """移除实体的标签。

用于从币种、因子、策略等实体上移除标签。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": "实体类型",
                    "enum": ["data", "factor", "strategy", "note", "research", "experience"]
                },
                "entity_id": {
                    "type": "string",
                    "description": "实体 ID"
                },
                "tag": {
                    "type": "string",
                    "description": "要移除的标签名称"
                }
            },
            "required": ["entity_type", "entity_id", "tag"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            entity_type_str = params.get("entity_type")
            entity_id = params.get("entity_id")
            tag = params.get("tag")

            try:
                entity_type = EdgeEntityType(entity_type_str)
            except ValueError:
                return ToolResult(success=False, error=f"无效的实体类型: {entity_type_str}")

            edge_store = get_edge_store()
            success = edge_store.remove_tag(entity_type, entity_id, tag)

            if success:
                return ToolResult(
                    success=True,
                    data={
                        "entity_type": entity_type_str,
                        "entity_id": entity_id,
                        "tag": tag,
                        "message": "移除标签成功"
                    }
                )
            else:
                return ToolResult(success=False, error="标签不存在或移除失败")

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetEntityTagsTool(BaseTool):
    """获取实体标签工具"""

    @property
    def name(self) -> str:
        return "get_entity_tags"

    @property
    def description(self) -> str:
        return """获取实体的所有标签。

查看币种、因子、策略等实体拥有的所有标签。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": "实体类型",
                    "enum": ["data", "factor", "strategy", "note", "research", "experience"]
                },
                "entity_id": {
                    "type": "string",
                    "description": "实体 ID"
                }
            },
            "required": ["entity_type", "entity_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            entity_type_str = params.get("entity_type")
            entity_id = params.get("entity_id")

            try:
                entity_type = EdgeEntityType(entity_type_str)
            except ValueError:
                return ToolResult(success=False, error=f"无效的实体类型: {entity_type_str}")

            edge_store = get_edge_store()
            tags = edge_store.get_entity_tags(entity_type, entity_id)

            return ToolResult(
                success=True,
                data={
                    "entity_type": entity_type_str,
                    "entity_id": entity_id,
                    "tags": tags,
                    "count": len(tags)
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetEntitiesByTagTool(BaseTool):
    """按标签获取实体工具"""

    @property
    def name(self) -> str:
        return "get_entities_by_tag"

    @property
    def description(self) -> str:
        return """获取拥有指定标签的所有实体。

用于查询币池、因子分类等。例如获取所有"妖币"标签的币种。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tag": {
                    "type": "string",
                    "description": "标签名称（如：妖币、蓝筹）"
                },
                "entity_type": {
                    "type": "string",
                    "description": "可选，筛选特定类型的实体",
                    "enum": ["data", "factor", "strategy", "note", "research", "experience"]
                }
            },
            "required": ["tag"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            tag = params.get("tag")
            entity_type_str = params.get("entity_type")

            entity_type = None
            if entity_type_str:
                try:
                    entity_type = EdgeEntityType(entity_type_str)
                except ValueError:
                    return ToolResult(success=False, error=f"无效的实体类型: {entity_type_str}")

            edge_store = get_edge_store()
            entities = edge_store.get_entities_by_tag(tag, entity_type)

            return ToolResult(
                success=True,
                data={
                    "tag": tag,
                    "entity_type_filter": entity_type_str,
                    "entities": entities,
                    "count": len(entities)
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ListAllTagsTool(BaseTool):
    """列出所有标签工具"""

    @property
    def name(self) -> str:
        return "list_all_tags"

    @property
    def description(self) -> str:
        return """列出所有使用过的标签及其统计。

查看系统中所有标签及其使用次数，用于了解标签体系。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    async def execute(self, **params) -> ToolResult:
        try:
            edge_store = get_edge_store()
            tags = edge_store.list_all_tags()

            return ToolResult(
                success=True,
                data={
                    "tags": tags,
                    "total": len(tags)
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
