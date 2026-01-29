"""
图查询 MCP 工具

提供实体关联查询、链路追溯和路径查找功能。
"""

from typing import Any

from domains.graph_hub.core.models import NodeType

from .base import BaseTool, ToolResult


class GetEdgesTool(BaseTool):
    """获取实体关联工具"""

    @property
    def name(self) -> str:
        return "get_edges"

    @property
    def description(self) -> str:
        return """获取实体的所有关联。

查询指定实体的出边（该实体作为源的关联），返回关联列表。
用于探索实体的知识网络，了解实体与其他实体的关系。

返回内容包括:
- 关联的目标实体类型和 ID
- 关系主类型 (derives/relates)
- 关系子类型 (based/uses/refs/validates 等)
- 是否双向关联
- 元数据
- 创建时间

使用示例:
1. 查看因子的所有关联:
   get_edges("factor", "Momentum_5d")
   返回该因子关联的数据源、其他因子、策略等

2. 查看策略使用的因子:
   get_edges("strategy", "uuid-123")
   返回策略关联的所有因子

3. 查看包含双向关联:
   get_edges("note", "note-1", include_bidirectional=True)
   包含作为目标的双向边"""

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
                    "description": "实体标识 (如: BTC-USDT, Momentum_5d, uuid-123)"
                },
                "include_bidirectional": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否包含双向关联的反向边，默认 True"
                }
            },
            "required": ["entity_type", "entity_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            entity_type_str = params.get("entity_type")
            entity_id = params.get("entity_id")
            include_bidirectional = params.get("include_bidirectional", True)

            # 解析实体类型
            try:
                entity_type = NodeType(entity_type_str)
            except ValueError:
                return ToolResult(success=False, error=f"无效的实体类型: {entity_type_str}")

            # 获取边
            edges = self.graph_store.get_edges_by_entity(
                entity_type=entity_type,
                entity_id=entity_id,
                include_bidirectional=include_bidirectional,
            )

            # 转换为字典列表
            edges_data = [edge.to_dict() for edge in edges]

            return ToolResult(
                success=True,
                data={
                    "entity_type": entity_type_str,
                    "entity_id": entity_id,
                    "count": len(edges_data),
                    "edges": edges_data,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class TraceLineageTool(BaseTool):
    """追溯知识链路工具"""

    @property
    def name(self) -> str:
        return "trace_lineage"

    @property
    def description(self) -> str:
        return """追溯实体的知识链路。

沿着知识图谱追溯实体的来源或影响范围，实现知识溯源和演化分析。

追溯方向:
- backward: 向上追溯源头（实体依赖什么、基于什么）
  例如: 追溯因子的原始数据源、演化历史
- forward: 向下追溯影响（什么依赖该实体、基于该实体）
  例如: 追溯因子被哪些策略使用、衍生了哪些新因子

使用示例:
1. 追溯因子演化历史:
   trace_lineage("factor", "Momentum_v3", "backward", max_depth=5)
   返回: Momentum_v3 -> Momentum_v2 -> Momentum_v1 -> data

2. 查看因子影响范围:
   trace_lineage("factor", "Momentum_5d", "forward", max_depth=3)
   返回: Momentum_5d -> strategy1, strategy2, Momentum_10d

3. 追溯经验的知识来源:
   trace_lineage("experience", "exp-1", "backward")
   返回: experience -> notes -> research

返回内容:
- nodes: 链路节点列表
  - depth: 距离起点的深度
  - node_type: 节点类型
  - node_id: 节点标识
  - relation: 与前一节点的关系"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["data", "factor", "strategy", "note", "research", "experience"],
                    "description": "起始实体类型"
                },
                "entity_id": {
                    "type": "string",
                    "description": "起始实体标识"
                },
                "direction": {
                    "type": "string",
                    "enum": ["backward", "forward"],
                    "default": "backward",
                    "description": "追溯方向: backward=向上追溯源头, forward=向下追溯影响"
                },
                "max_depth": {
                    "type": "integer",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10,
                    "description": "最大追溯深度，默认 5，最大 10"
                }
            },
            "required": ["entity_type", "entity_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            entity_type_str = params.get("entity_type")
            entity_id = params.get("entity_id")
            direction = params.get("direction", "backward")
            max_depth = params.get("max_depth", 5)

            # 限制深度
            max_depth = min(max(1, max_depth), 10)

            # 解析实体类型
            try:
                entity_type = NodeType(entity_type_str)
            except ValueError:
                return ToolResult(success=False, error=f"无效的实体类型: {entity_type_str}")

            # 执行链路追溯
            result = self.graph_store.trace_lineage(
                entity_type=entity_type,
                entity_id=entity_id,
                direction=direction,
                max_depth=max_depth,
            )

            return ToolResult(
                success=True,
                data=result.to_dict()
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class FindPathTool(BaseTool):
    """查找路径工具"""

    @property
    def name(self) -> str:
        return "find_path"

    @property
    def description(self) -> str:
        return """查找两个实体之间的最短路径。

在知识图谱中查找两个实体之间的连接路径，用于发现潜在的知识关联。
使用无向搜索，可以发现间接关系。

使用示例:
1. 查找因子与策略的关联路径:
   find_path("factor", "Momentum_5d", "strategy", "uuid-123")
   可能返回: factor -> strategy (直接应用)
   或: factor -> factor2 -> strategy (间接关联)

2. 查找笔记与经验的关联:
   find_path("note", "note-1", "experience", "exp-1")
   返回笔记如何演化为经验的路径

3. 查找两个因子的关系:
   find_path("factor", "Momentum_5d", "factor", "RSI_14d")
   发现两个因子是否有共同来源或关联

返回内容:
- paths: 路径列表（目前返回最短路径）
  - 每条路径包含节点和关系的交替列表
  - node: {type, label, id, position}
  - relationship: {type, relation, position}

注意:
- 如果两实体没有连接，返回空路径列表
- max_depth 影响搜索范围，越大越可能找到间接路径"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source_type": {
                    "type": "string",
                    "enum": ["data", "factor", "strategy", "note", "research", "experience"],
                    "description": "起始实体类型"
                },
                "source_id": {
                    "type": "string",
                    "description": "起始实体标识"
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
                "max_depth": {
                    "type": "integer",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10,
                    "description": "最大搜索深度，默认 5，最大 10"
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
            max_depth = params.get("max_depth", 5)

            # 限制深度
            max_depth = min(max(1, max_depth), 10)

            # 解析实体类型
            try:
                source_type = NodeType(source_type_str)
            except ValueError:
                return ToolResult(success=False, error=f"无效的源实体类型: {source_type_str}")

            try:
                target_type = NodeType(target_type_str)
            except ValueError:
                return ToolResult(success=False, error=f"无效的目标实体类型: {target_type_str}")

            # 查找路径
            result = self.graph_store.find_path(
                source_type=source_type,
                source_id=source_id,
                target_type=target_type,
                target_id=target_id,
                max_depth=max_depth,
            )

            return ToolResult(
                success=True,
                data=result.to_dict()
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
