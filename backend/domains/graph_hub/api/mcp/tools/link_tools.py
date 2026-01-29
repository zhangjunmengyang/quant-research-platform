"""
关联管理 MCP 工具

提供实体间关联关系的创建和删除功能。
"""

from typing import Any

from domains.graph_hub.core.models import (
    GraphEdge,
    NodeType,
    RelationType,
)

from .base import BaseTool, ToolResult


class CreateLinkTool(BaseTool):
    """创建关联工具"""

    @property
    def name(self) -> str:
        return "create_link"

    @property
    def description(self) -> str:
        return """创建实体间的关联关系。

建立不同知识实体之间的关联，用于构建知识图谱，实现知识链路追溯。

支持的实体类型:
- data: 市场数据 (symbol 标识，如 BTC-USDT)
- factor: 因子 (filename 标识，如 Momentum_5d)
- strategy: 策略 (UUID 标识)
- note: 研究笔记 (ID 标识)
- research: 外部研报 (ID 标识)
- experience: 经验记录 (ID 标识)

支持的关系类型:
- derived_from: 派生自 (因子->数据，因子->因子)
  用于记录因子的数据来源或演化关系
- applied_to: 应用于 (策略->因子)
  用于记录策略使用了哪些因子
- verifies: 验证 (检验笔记->假设笔记)
  用于记录假设的验证关系
- references: 引用 (笔记->研报)
  用于记录知识的引用来源
- summarizes: 总结为 (经验->笔记)
  用于记录从笔记提炼出的经验
- related: 通用关联 (默认)
  用于记录一般性的关联关系

使用示例:
1. 记录因子演化:
   create_link("factor", "Momentum_v2", "factor", "Momentum_v1", "derived_from")
   表示 Momentum_v2 是从 Momentum_v1 演化而来

2. 策略应用因子:
   create_link("strategy", "uuid-123", "factor", "Momentum_5d", "applied_to")
   表示策略使用了 Momentum_5d 因子

3. 因子关联数据:
   create_link("factor", "Volume_Ratio", "data", "BTC-USDT", "derived_from")
   表示 Volume_Ratio 因子基于 BTC-USDT 数据计算

4. 建立双向关联:
   create_link("note", "note-1", "note", "note-2", "related", is_bidirectional=True)
   表示两个笔记相互关联"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source_type": {
                    "type": "string",
                    "enum": ["data", "factor", "strategy", "note", "research", "experience"],
                    "description": "源实体类型"
                },
                "source_id": {
                    "type": "string",
                    "description": "源实体标识 (如: BTC-USDT, Momentum_5d, uuid-123)"
                },
                "target_type": {
                    "type": "string",
                    "enum": ["data", "factor", "strategy", "note", "research", "experience"],
                    "description": "目标实体类型"
                },
                "target_id": {
                    "type": "string",
                    "description": "目标实体标识"
                },
                "relation": {
                    "type": "string",
                    "enum": ["derived_from", "applied_to", "verifies", "references", "summarizes", "related"],
                    "default": "related",
                    "description": "关系类型，默认 related"
                },
                "is_bidirectional": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否双向关联，默认 False"
                }
            },
            "required": ["source_type", "source_id", "target_type", "target_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            source_type_str = params.get("source_type")
            source_id = params.get("source_id")
            target_type_str = params.get("target_type")
            target_id = params.get("target_id")
            relation_str = params.get("relation", "related")
            is_bidirectional = params.get("is_bidirectional", False)

            # 解析枚举类型
            try:
                source_type = NodeType(source_type_str)
            except ValueError:
                return ToolResult(success=False, error=f"无效的源实体类型: {source_type_str}")

            try:
                target_type = NodeType(target_type_str)
            except ValueError:
                return ToolResult(success=False, error=f"无效的目标实体类型: {target_type_str}")

            try:
                relation = RelationType(relation_str)
            except ValueError:
                return ToolResult(success=False, error=f"无效的关系类型: {relation_str}")

            # 检查是否已存在
            if self.graph_store.exists(
                source_type=source_type,
                source_id=source_id,
                target_type=target_type,
                target_id=target_id,
                relation=relation,
            ):
                return ToolResult(
                    success=True,
                    data={
                        "source": f"{source_type_str}:{source_id}",
                        "target": f"{target_type_str}:{target_id}",
                        "relation": relation_str,
                        "message": "关联已存在",
                    }
                )

            # 创建边
            edge = GraphEdge(
                source_type=source_type,
                source_id=source_id,
                target_type=target_type,
                target_id=target_id,
                relation=relation,
                is_bidirectional=is_bidirectional,
            )

            success = self.graph_store.create_edge(edge)

            if success:
                return ToolResult(
                    success=True,
                    data={
                        "source": f"{source_type_str}:{source_id}",
                        "target": f"{target_type_str}:{target_id}",
                        "relation": relation_str,
                        "is_bidirectional": is_bidirectional,
                        "message": "创建关联成功",
                    }
                )
            else:
                return ToolResult(success=False, error="创建关联失败，请检查 Neo4j 连接")

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class DeleteLinkTool(BaseTool):
    """删除关联工具"""

    @property
    def name(self) -> str:
        return "delete_link"

    @property
    def description(self) -> str:
        return """删除实体间的关联关系。

移除两个实体之间的特定关联。需要精确指定源实体、目标实体和关系类型。

注意事项:
- 只删除指定方向和类型的关联
- 如果原关联是双向的，只会删除正向边
- 删除不存在的关联会返回失败

使用示例:
1. 删除因子演化关系:
   delete_link("factor", "Momentum_v2", "factor", "Momentum_v1", "derived_from")

2. 删除策略与因子的关联:
   delete_link("strategy", "uuid-123", "factor", "Momentum_5d", "applied_to")"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source_type": {
                    "type": "string",
                    "enum": ["data", "factor", "strategy", "note", "research", "experience"],
                    "description": "源实体类型"
                },
                "source_id": {
                    "type": "string",
                    "description": "源实体标识"
                },
                "target_type": {
                    "type": "string",
                    "enum": ["data", "factor", "strategy", "note", "research", "experience"],
                    "description": "目标实体类型"
                },
                "target_id": {
                    "type": "string",
                    "description": "目标实体标识"
                },
                "relation": {
                    "type": "string",
                    "enum": ["derived_from", "applied_to", "verifies", "references", "summarizes", "related"],
                    "description": "关系类型"
                }
            },
            "required": ["source_type", "source_id", "target_type", "target_id", "relation"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            source_type_str = params.get("source_type")
            source_id = params.get("source_id")
            target_type_str = params.get("target_type")
            target_id = params.get("target_id")
            relation_str = params.get("relation")

            # 解析枚举类型
            try:
                source_type = NodeType(source_type_str)
            except ValueError:
                return ToolResult(success=False, error=f"无效的源实体类型: {source_type_str}")

            try:
                target_type = NodeType(target_type_str)
            except ValueError:
                return ToolResult(success=False, error=f"无效的目标实体类型: {target_type_str}")

            try:
                relation = RelationType(relation_str)
            except ValueError:
                return ToolResult(success=False, error=f"无效的关系类型: {relation_str}")

            # 删除边
            success = self.graph_store.delete_edge(
                source_type=source_type,
                source_id=source_id,
                target_type=target_type,
                target_id=target_id,
                relation=relation,
            )

            if success:
                return ToolResult(
                    success=True,
                    data={
                        "source": f"{source_type_str}:{source_id}",
                        "target": f"{target_type_str}:{target_id}",
                        "relation": relation_str,
                        "message": "删除关联成功",
                    }
                )
            else:
                return ToolResult(success=False, error="关联不存在或删除失败")

        except Exception as e:
            return ToolResult(success=False, error=str(e))
