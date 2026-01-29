"""
关联管理 MCP 工具

提供实体间关联关系的创建和删除功能。
"""

from typing import Any

from domains.graph_hub.core.models import (
    GraphEdge,
    LEGACY_RELATION_MAPPING,
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

## 实体类型

- data: 市场数据 (symbol 标识，如 BTC-USDT)
- factor: 因子 (filename 标识，如 Momentum_5d)
- strategy: 策略 (UUID 标识)
- note: 研究笔记 (ID 标识)
- research: 外部研报 (ID 标识)
- experience: 经验记录 (ID 标识)

## 关系类型

**DERIVES (派生关系)** - 有方向，表示 A 产生/影响 B
- based: 代码派生（Momentum_v2 基于 Momentum_v1）
- inspired: 思路启发
- produces: 产出（检验 -> 因子，笔记 -> 经验）
- uses: 使用（策略 -> 因子）
- evolves: 演化/迭代
- enables: 使能

**RELATES (关联关系)** - 默认双向，表示语义关联
- refs: 引用（笔记 -> 研报）
- similar: 相似
- validates: 验证（检验笔记 <-> 假设笔记，metadata.direction 指定 supports/contradicts）
- contrasts: 对比
- temporal: 时序共现

## 使用示例

1. 记录因子演化:
   create_link("factor", "Momentum_v2", "factor", "Momentum_v1", "derives", subtype="based")

2. 策略使用因子:
   create_link("strategy", "uuid-123", "factor", "Momentum_5d", "derives", subtype="uses")

3. 笔记引用研报:
   create_link("note", "note-1", "research", "report-123", "relates", subtype="refs")

4. 带元数据的关联:
   create_link("factor", "A", "factor", "B", "derives", subtype="based",
               metadata={"weight": 0.5, "context": "组合因子成分"})"""

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
                    "enum": ["derives", "relates"],
                    "default": "relates",
                    "description": "关系主类型: derives(派生) 或 relates(关联)"
                },
                "subtype": {
                    "type": "string",
                    "default": "",
                    "description": "关系子类型: based/inspired/uses/produces/refs/validates/similar 等"
                },
                "is_bidirectional": {
                    "type": "boolean",
                    "description": "是否双向关联（不指定时: derives 单向, relates 双向）"
                },
                "metadata": {
                    "type": "object",
                    "description": "扩展元数据: {strength, confidence, context, evidence, weight, direction}",
                    "additionalProperties": True
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
            relation_str = params.get("relation", "relates")
            subtype = params.get("subtype", "")
            is_bidirectional = params.get("is_bidirectional")
            metadata = params.get("metadata", {})

            # 解析枚举类型
            try:
                source_type = NodeType(source_type_str)
            except ValueError:
                return ToolResult(success=False, error=f"无效的源实体类型: {source_type_str}")

            try:
                target_type = NodeType(target_type_str)
            except ValueError:
                return ToolResult(success=False, error=f"无效的目标实体类型: {target_type_str}")

            # 兼容旧关系类型
            if relation_str in LEGACY_RELATION_MAPPING:
                new_rel, default_subtype = LEGACY_RELATION_MAPPING[relation_str]
                relation = RelationType(new_rel)
                if not subtype:
                    subtype = default_subtype
            else:
                try:
                    relation = RelationType(relation_str)
                except ValueError:
                    return ToolResult(success=False, error=f"无效的关系类型: {relation_str}")

            # 双向逻辑: 如果未指定，RELATES 默认双向，DERIVES 默认单向
            if is_bidirectional is None:
                is_bidirectional = relation == RelationType.RELATES

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
                        "relation": relation.value,
                        "subtype": subtype,
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
                subtype=subtype,
                is_bidirectional=is_bidirectional,
                metadata=metadata or {},
            )

            success = self.graph_store.create_edge(edge)

            if success:
                return ToolResult(
                    success=True,
                    data={
                        "source": f"{source_type_str}:{source_id}",
                        "target": f"{target_type_str}:{target_id}",
                        "relation": relation.value,
                        "subtype": subtype,
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
1. 删除因子派生关系:
   delete_link("factor", "Momentum_v2", "factor", "Momentum_v1", "derives")

2. 删除策略与因子的关联:
   delete_link("strategy", "uuid-123", "factor", "Momentum_5d", "derives")"""

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
                    "enum": ["derives", "relates"],
                    "description": "关系主类型"
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

            # 兼容旧关系类型
            if relation_str in LEGACY_RELATION_MAPPING:
                new_rel, _ = LEGACY_RELATION_MAPPING[relation_str]
                relation = RelationType(new_rel)
            else:
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
                        "relation": relation.value,
                        "message": "删除关联成功",
                    }
                )
            else:
                return ToolResult(success=False, error="关联不存在或删除失败")

        except Exception as e:
            return ToolResult(success=False, error=str(e))
