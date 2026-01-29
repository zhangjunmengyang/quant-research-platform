"""
标签管理 MCP 工具

提供实体标签的添加、移除、查询功能，用于给币种、因子、策略等打标签。
"""

from typing import Any

from domains.graph_hub.core.models import NodeType

from .base import BaseTool, ToolResult


class AddTagTool(BaseTool):
    """添加标签工具"""

    @property
    def name(self) -> str:
        return "add_tag"

    @property
    def description(self) -> str:
        return """给实体添加标签。

用于给币种、因子、策略等实体打标签，便于分类管理和研究。
标签作为节点的 tags 属性存储在 Neo4j 图数据库中。

典型使用场景:
- 给币种打标签构建币池（如: 妖币、蓝筹、DeFi、Meme）
- 给因子打标签分类（如: 动量类、反转类、波动类、价值类）
- 给策略打标签（如: 高频、低频、趋势、套利）
- 给笔记打标签便于检索（如: 待验证、已验证、重要发现）

使用示例:
1. 给币种打标签:
   add_tag("data", "BTC-USDT", "蓝筹")
   add_tag("data", "DOGE-USDT", "Meme")

2. 给因子分类:
   add_tag("factor", "Momentum_5d", "动量类")
   add_tag("factor", "RSI_14d", "技术指标")

3. 给策略分类:
   add_tag("strategy", "uuid-123", "趋势跟踪")

注意:
- 标签名称大小写敏感
- 重复添加相同标签不会报错，返回"标签已存在"
- 一个实体可以有多个标签"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["data", "factor", "strategy", "note", "research", "experience"],
                    "description": "实体类型"
                },
                "entity_id": {
                    "type": "string",
                    "description": "实体标识 (如: BTC-USDT, Momentum_5d)"
                },
                "tag": {
                    "type": "string",
                    "description": "标签名称 (如: 妖币, 蓝筹, 高波动)"
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

            # 解析实体类型
            try:
                entity_type = NodeType(entity_type_str)
            except ValueError:
                return ToolResult(success=False, error=f"无效的实体类型: {entity_type_str}")

            # 检查标签是否已存在
            existing_tags = self.graph_store.get_entity_tags(entity_type, entity_id)
            if tag in existing_tags:
                return ToolResult(
                    success=True,
                    data={
                        "entity_type": entity_type_str,
                        "entity_id": entity_id,
                        "tag": tag,
                        "message": "标签已存在",
                    }
                )

            # 添加标签
            success = self.graph_store.add_tag(entity_type, entity_id, tag)

            if success:
                return ToolResult(
                    success=True,
                    data={
                        "entity_type": entity_type_str,
                        "entity_id": entity_id,
                        "tag": tag,
                        "message": "添加标签成功",
                    }
                )
            else:
                return ToolResult(success=False, error="添加标签失败，请检查 Neo4j 连接")

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

用于从币种、因子、策略等实体上移除标签。

使用示例:
1. 移除币种标签:
   remove_tag("data", "DOGE-USDT", "妖币")

2. 移除因子分类:
   remove_tag("factor", "Momentum_5d", "动量类")

注意:
- 移除不存在的标签会返回失败
- 只移除指定的标签，不影响其他标签"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["data", "factor", "strategy", "note", "research", "experience"],
                    "description": "实体类型"
                },
                "entity_id": {
                    "type": "string",
                    "description": "实体标识"
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

            # 解析实体类型
            try:
                entity_type = NodeType(entity_type_str)
            except ValueError:
                return ToolResult(success=False, error=f"无效的实体类型: {entity_type_str}")

            # 移除标签
            success = self.graph_store.remove_tag(entity_type, entity_id, tag)

            if success:
                return ToolResult(
                    success=True,
                    data={
                        "entity_type": entity_type_str,
                        "entity_id": entity_id,
                        "tag": tag,
                        "message": "移除标签成功",
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

查看币种、因子、策略等实体拥有的所有标签。

使用示例:
1. 查看币种标签:
   get_entity_tags("data", "BTC-USDT")
   返回: ["蓝筹", "主流"]

2. 查看因子分类:
   get_entity_tags("factor", "Momentum_5d")
   返回: ["动量类", "技术指标"]

返回内容:
- tags: 标签名称列表
- count: 标签数量"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["data", "factor", "strategy", "note", "research", "experience"],
                    "description": "实体类型"
                },
                "entity_id": {
                    "type": "string",
                    "description": "实体标识"
                }
            },
            "required": ["entity_type", "entity_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            entity_type_str = params.get("entity_type")
            entity_id = params.get("entity_id")

            # 解析实体类型
            try:
                entity_type = NodeType(entity_type_str)
            except ValueError:
                return ToolResult(success=False, error=f"无效的实体类型: {entity_type_str}")

            # 获取标签
            tags = self.graph_store.get_entity_tags(entity_type, entity_id)

            return ToolResult(
                success=True,
                data={
                    "entity_type": entity_type_str,
                    "entity_id": entity_id,
                    "tags": tags,
                    "count": len(tags),
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

用于查询币池、因子分类等。例如获取所有"妖币"标签的币种。

使用示例:
1. 获取妖币池:
   get_entities_by_tag("妖币", entity_type="data")
   返回所有被标记为"妖币"的币种

2. 获取动量类因子:
   get_entities_by_tag("动量类", entity_type="factor")
   返回所有被标记为"动量类"的因子

3. 获取所有使用某标签的实体:
   get_entities_by_tag("重要")
   返回所有被标记为"重要"的实体，不限类型

返回内容:
- entities: 实体列表 [{type, id}, ...]
- count: 实体数量"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tag": {
                    "type": "string",
                    "description": "标签名称 (如: 妖币, 蓝筹)"
                },
                "entity_type": {
                    "type": "string",
                    "enum": ["data", "factor", "strategy", "note", "research", "experience"],
                    "description": "可选，筛选特定类型的实体。不指定则返回所有类型"
                }
            },
            "required": ["tag"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            tag = params.get("tag")
            entity_type_str = params.get("entity_type")

            # 解析实体类型（可选）
            entity_type = None
            if entity_type_str:
                try:
                    entity_type = NodeType(entity_type_str)
                except ValueError:
                    return ToolResult(success=False, error=f"无效的实体类型: {entity_type_str}")

            # 获取实体
            entities = self.graph_store.get_entities_by_tag(tag, entity_type)

            return ToolResult(
                success=True,
                data={
                    "tag": tag,
                    "entity_type_filter": entity_type_str,
                    "entities": entities,
                    "count": len(entities),
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

查看系统中所有标签及其使用次数，用于了解标签体系和使用情况。

使用示例:
list_all_tags()

返回内容:
- tags: 标签列表
  - tag: 标签名称
  - count: 使用该标签的实体数量
- total: 标签总数

返回按使用次数降序排列，便于发现最常用的标签。"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    async def execute(self, **params) -> ToolResult:
        try:
            # 获取所有标签
            tags = self.graph_store.list_all_tags()

            return ToolResult(
                success=True,
                data={
                    "tags": tags,
                    "total": len(tags),
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
