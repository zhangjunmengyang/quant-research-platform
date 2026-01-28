"""
因子关联 MCP 工具

提供因子与其他实体（包括其他因子）的关联管理功能。

支持的关联场景:
- 因子之间的派生关系（factor A derived_from factor B）
- 因子与数据源的关联（factor derived_from data）
- 因子与笔记/研报的引用关系（factor references note/research）
- 因子与策略的应用关系（strategy applied_to factor）
"""

from typing import Any, Dict

from .base import BaseTool, ToolResult


class LinkFactorTool(BaseTool):
    """关联因子工具"""

    @property
    def name(self) -> str:
        return "link_factor"

    @property
    def description(self) -> str:
        return """创建因子与其他实体的关联。

建立因子与数据、其他因子、策略、笔记、研报、经验等实体的关联关系。
用于构建知识图谱，实现因子演化链路追溯。

实体类型:
- data: 数据层（币种、K线等）
- factor: 其他因子（用于记录因子演化关系）
- strategy: 策略
- note: 研究笔记
- research: 外部研报
- experience: 经验记录

关系类型:
- derived_from: 派生自（如：因子B derived_from 因子A，表示B是A的改进版）
- applied_to: 应用于（如：策略 applied_to 因子）
- references: 引用（如：因子 references 研报）
- related: 一般关联（默认）

使用场景:
- 记录因子之间的演化关系（A 是 B 的优化版本）
- 追溯因子的数据来源
- 关联因子与相关研究笔记
- 建立因子知识网络"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "factor_name": {
                    "type": "string",
                    "description": "因子名称"
                },
                "target_type": {
                    "type": "string",
                    "description": "目标实体类型",
                    "enum": ["data", "factor", "strategy", "note", "research", "experience"]
                },
                "target_id": {
                    "type": "string",
                    "description": "目标实体 ID（如：BTC-USDT、Momentum_5d、123）"
                },
                "relation": {
                    "type": "string",
                    "description": "关系类型",
                    "enum": ["derived_from", "applied_to", "verifies", "references", "summarizes", "related"],
                    "default": "related"
                },
                "is_bidirectional": {
                    "type": "boolean",
                    "description": "是否双向关联",
                    "default": False
                }
            },
            "required": ["factor_name", "target_type", "target_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            factor_name = self.normalize_filename(params.get("factor_name", ""))
            target_type = params.get("target_type")
            target_id = params.get("target_id")
            relation = params.get("relation", "related")
            is_bidirectional = params.get("is_bidirectional", False)

            # 如果目标是因子，也需要规范化名称
            if target_type == "factor":
                target_id = self.normalize_filename(target_id)

            success, message, edge_id = self.factor_service.link_factor(
                factor_name=factor_name,
                target_type=target_type,
                target_id=target_id,
                relation=relation,
                is_bidirectional=is_bidirectional,
            )

            if success:
                return ToolResult(
                    success=True,
                    data={
                        "edge_id": edge_id,
                        "factor_name": factor_name,
                        "target_type": target_type,
                        "target_id": target_id,
                        "relation": relation,
                        "message": message
                    }
                )
            else:
                return ToolResult(success=False, error=message)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetFactorEdgesTool(BaseTool):
    """获取因子关联工具"""

    @property
    def name(self) -> str:
        return "get_factor_edges"

    @property
    def description(self) -> str:
        return """获取因子的所有关联。

返回因子与其他实体的关联列表，用于查看因子的知识网络。

使用场景:
- 查看因子基于哪些数据源
- 了解因子与其他因子的演化关系
- 探索因子的知识图谱"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "factor_name": {
                    "type": "string",
                    "description": "因子名称"
                },
                "include_bidirectional": {
                    "type": "boolean",
                    "description": "是否包含双向关联",
                    "default": True
                }
            },
            "required": ["factor_name"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            factor_name = self.normalize_filename(params.get("factor_name", ""))
            include_bidirectional = params.get("include_bidirectional", True)

            edges = self.factor_service.get_factor_edges(
                factor_name=factor_name,
                include_bidirectional=include_bidirectional,
            )

            return ToolResult(
                success=True,
                data={
                    "factor_name": factor_name,
                    "count": len(edges),
                    "edges": edges,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class TraceFactorLineageTool(BaseTool):
    """追溯因子链路工具"""

    @property
    def name(self) -> str:
        return "trace_factor_lineage"

    @property
    def description(self) -> str:
        return """追溯因子的知识链路。

沿着知识图谱追溯因子的来源或演化，实现因子版本追溯。

方向:
- backward: 向上追溯源头（因子基于什么，如原始因子、数据源）
- forward: 向下追溯演化（因子被什么改进/使用，如衍生因子、策略）

使用场景:
- 追溯因子的原始版本
- 查看因子的改进历史
- 理解因子的演化路径"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "factor_name": {
                    "type": "string",
                    "description": "因子名称"
                },
                "direction": {
                    "type": "string",
                    "description": "追溯方向",
                    "enum": ["backward", "forward"],
                    "default": "backward"
                },
                "max_depth": {
                    "type": "integer",
                    "description": "最大追溯深度",
                    "default": 5,
                    "maximum": 10
                }
            },
            "required": ["factor_name"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            factor_name = self.normalize_filename(params.get("factor_name", ""))
            direction = params.get("direction", "backward")
            max_depth = params.get("max_depth", 5)

            lineage = self.factor_service.trace_factor_lineage(
                factor_name=factor_name,
                direction=direction,
                max_depth=max_depth,
            )

            return ToolResult(
                success=True,
                data={
                    "factor_name": factor_name,
                    "direction": direction,
                    "max_depth": max_depth,
                    "count": len(lineage),
                    "lineage": lineage,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
