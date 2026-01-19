"""
经验 MCP 工具

提供经验的存储、检索和管理功能。
"""

from typing import Any, Dict

from .base import BaseTool, ToolResult


class StoreExperienceTool(BaseTool):
    """存储经验工具"""

    @property
    def name(self) -> str:
        return "store_experience"

    @property
    def description(self) -> str:
        return """存储新经验。

用于记录量化研究过程中的洞察、经验和发现。
使用 PARL 框架结构化存储:
- Problem: 面临的问题或挑战
- Approach: 采用的方法或策略
- Result: 得到的结果
- Lesson: 总结的教训或规律

使用标签(tags)进行分类管理。

使用场景:
- 记录因子分析的发现
- 保存策略优化的经验
- 积累交易逻辑的洞察"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "经验标题"
                },
                "content": {
                    "type": "object",
                    "description": "PARL 框架内容",
                    "properties": {
                        "problem": {"type": "string", "description": "面临的问题"},
                        "approach": {"type": "string", "description": "采用的方法"},
                        "result": {"type": "string", "description": "得到的结果"},
                        "lesson": {"type": "string", "description": "总结的教训"}
                    },
                    "required": ["problem", "lesson"]
                },
                "context": {
                    "type": "object",
                    "description": "上下文信息",
                    "properties": {
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "自定义标签"},
                        "factor_styles": {"type": "array", "items": {"type": "string"}, "description": "相关因子风格"},
                        "market_regime": {"type": "string", "description": "市场状态（牛市/熊市/震荡）"},
                        "time_horizon": {"type": "string", "description": "时间范围（短期/中期/长期）"},
                        "asset_class": {"type": "string", "description": "资产类别"}
                    }
                },
                "source_type": {
                    "type": "string",
                    "description": "来源类型",
                    "enum": ["research", "backtest", "live_trade", "external", "manual"],
                    "default": "manual"
                },
                "source_ref": {
                    "type": "string",
                    "description": "来源引用（如策略ID、研究会话ID）"
                }
            },
            "required": ["title", "content"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            title = params.get("title", "")
            content = params.get("content", {})
            context = params.get("context")
            source_type = params.get("source_type", "manual")
            source_ref = params.get("source_ref", "")

            success, message, experience_id = self.experience_service.store_experience(
                title=title,
                content=content,
                context=context,
                source_type=source_type,
                source_ref=source_ref,
            )

            if success:
                return ToolResult(
                    success=True,
                    data={
                        "experience_id": experience_id,
                        "title": title,
                        "message": message
                    }
                )
            else:
                return ToolResult(success=False, error=message)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class QueryExperiencesTool(BaseTool):
    """语义检索经验工具"""

    @property
    def name(self) -> str:
        return "query_experiences"

    @property
    def description(self) -> str:
        return """语义检索经验。

使用自然语言查询相关经验，支持多种过滤条件。
返回按相关性排序的经验列表。

使用场景:
- 查找之前记录的类似经验
- 在开始新研究前检索相关历史教训
- 寻找特定场景下的最佳实践"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "自然语言查询"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "过滤标签"
                },
                "market_regime": {
                    "type": "string",
                    "description": "过滤市场环境"
                },
                "factor_styles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "过滤因子风格"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回数量",
                    "default": 5,
                    "maximum": 20
                }
            },
            "required": ["query"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            query = params.get("query", "")
            tags = params.get("tags")
            market_regime = params.get("market_regime")
            factor_styles = params.get("factor_styles")
            top_k = params.get("top_k", 5)

            experiences = self.experience_service.query_experiences(
                query=query,
                tags=tags,
                market_regime=market_regime,
                factor_styles=factor_styles,
                top_k=top_k,
            )

            exp_list = []
            for exp in experiences:
                exp_list.append({
                    "id": exp.id,
                    "uuid": exp.uuid,
                    "title": exp.title,
                    "summary": exp.summary,
                    "tags": exp.tags,
                    "content": exp.content.to_dict() if hasattr(exp.content, 'to_dict') else exp.content,
                    "context": exp.context.to_dict() if hasattr(exp.context, 'to_dict') else exp.context,
                    "updated_at": str(exp.updated_at) if exp.updated_at else None,
                })

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "count": len(exp_list),
                    "experiences": exp_list,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetExperienceTool(BaseTool):
    """获取经验详情工具"""

    @property
    def name(self) -> str:
        return "get_experience"

    @property
    def description(self) -> str:
        return """获取单个经验的完整内容。

通过经验 ID 获取完整的经验详情，包括 PARL 内容、上下文等。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "experience_id": {
                    "type": "integer",
                    "description": "经验 ID"
                }
            },
            "required": ["experience_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            experience_id = params.get("experience_id")

            if experience_id is None:
                return ToolResult(
                    success=False,
                    error="experience_id 参数不能为空"
                )

            experience = self.experience_service.get_experience(experience_id)
            if experience is None:
                return ToolResult(
                    success=False,
                    error=f"经验不存在: {experience_id}"
                )

            return ToolResult(
                success=True,
                data={
                    "id": experience.id,
                    "uuid": experience.uuid,
                    "title": experience.title,
                    "content": experience.content.to_dict() if hasattr(experience.content, 'to_dict') else experience.content,
                    "context": experience.context.to_dict() if hasattr(experience.context, 'to_dict') else experience.context,
                    "source_type": experience.source_type,
                    "source_ref": experience.source_ref,
                    "created_at": str(experience.created_at) if experience.created_at else None,
                    "updated_at": str(experience.updated_at) if experience.updated_at else None,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ListExperiencesTool(BaseTool):
    """获取经验列表工具"""

    @property
    def name(self) -> str:
        return "list_experiences"

    @property
    def description(self) -> str:
        return """获取经验列表。

支持多种过滤条件，返回经验完整内容。
不传任何参数则返回全部经验（分页）。

过滤条件:
- 标签筛选
- 来源类型筛选
- 市场环境筛选
- 因子风格筛选
- 时间范围筛选（创建时间/更新时间）"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "按标签筛选（AND 逻辑）"
                },
                "source_type": {
                    "type": "string",
                    "description": "按来源类型筛选",
                    "enum": ["research", "backtest", "live_trade", "external", "manual"]
                },
                "market_regime": {
                    "type": "string",
                    "description": "按市场环境筛选（牛市/熊市/震荡）"
                },
                "factor_styles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "按因子风格筛选"
                },
                "created_after": {
                    "type": "string",
                    "description": "创建时间起始（ISO 格式，如 2024-01-01）"
                },
                "created_before": {
                    "type": "string",
                    "description": "创建时间截止（ISO 格式）"
                },
                "updated_after": {
                    "type": "string",
                    "description": "更新时间起始（ISO 格式）"
                },
                "updated_before": {
                    "type": "string",
                    "description": "更新时间截止（ISO 格式）"
                },
                "include_content": {
                    "type": "boolean",
                    "description": "是否包含完整内容（PARL），默认 true",
                    "default": True
                },
                "page": {
                    "type": "integer",
                    "description": "页码",
                    "default": 1,
                    "minimum": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "每页数量",
                    "default": 20,
                    "maximum": 50
                }
            }
        }

    async def execute(self, **params) -> ToolResult:
        from datetime import datetime

        try:
            tags = params.get("tags")
            source_type = params.get("source_type", "")
            market_regime = params.get("market_regime", "")
            factor_styles = params.get("factor_styles")
            include_content = params.get("include_content", True)
            page = params.get("page", 1)
            page_size = params.get("page_size", 20)

            # 解析时间参数
            created_after = None
            created_before = None
            updated_after = None
            updated_before = None

            if params.get("created_after"):
                created_after = datetime.fromisoformat(params["created_after"])
            if params.get("created_before"):
                created_before = datetime.fromisoformat(params["created_before"])
            if params.get("updated_after"):
                updated_after = datetime.fromisoformat(params["updated_after"])
            if params.get("updated_before"):
                updated_before = datetime.fromisoformat(params["updated_before"])

            experiences, total = self.experience_service.list_experiences(
                tags=tags,
                source_type=source_type,
                market_regime=market_regime,
                factor_styles=factor_styles,
                created_after=created_after,
                created_before=created_before,
                updated_after=updated_after,
                updated_before=updated_before,
                page=page,
                page_size=page_size,
            )

            exp_list = []
            for exp in experiences:
                item = {
                    "id": exp.id,
                    "uuid": exp.uuid,
                    "title": exp.title,
                    "tags": exp.tags,
                    "source_type": exp.source_type,
                    "source_ref": exp.source_ref,
                    "created_at": str(exp.created_at) if exp.created_at else None,
                    "updated_at": str(exp.updated_at) if exp.updated_at else None,
                }
                if include_content:
                    item["content"] = exp.content.to_dict() if hasattr(exp.content, 'to_dict') else exp.content
                    item["context"] = exp.context.to_dict() if hasattr(exp.context, 'to_dict') else exp.context
                exp_list.append(item)

            return ToolResult(
                success=True,
                data={
                    "experiences": exp_list,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class LinkExperienceTool(BaseTool):
    """关联经验工具"""

    @property
    def name(self) -> str:
        return "link_experience"

    @property
    def description(self) -> str:
        return """关联经验与其他实体。

建立经验与因子、策略、笔记、研报的关联关系。
方便后续通过实体查找相关经验。

使用场景:
- 关联经验与相关因子
- 关联经验与策略回测
- 关联经验与外部研报"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "experience_id": {
                    "type": "integer",
                    "description": "经验 ID"
                },
                "entity_type": {
                    "type": "string",
                    "description": "实体类型",
                    "enum": ["factor", "strategy", "note", "research", "experience"]
                },
                "entity_id": {
                    "type": "string",
                    "description": "实体 ID（因子名、策略ID等）"
                },
                "relation": {
                    "type": "string",
                    "description": "关系类型",
                    "enum": ["related", "derived_from", "applied_to"],
                    "default": "related"
                }
            },
            "required": ["experience_id", "entity_type", "entity_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            experience_id = params.get("experience_id")
            entity_type = params.get("entity_type")
            entity_id = params.get("entity_id")
            relation = params.get("relation", "related")

            success, message, data = self.experience_service.link_experience(
                experience_id=experience_id,
                entity_type=entity_type,
                entity_id=entity_id,
                relation=relation,
            )

            if success:
                return ToolResult(success=True, data=data)
            else:
                return ToolResult(success=False, error=message)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetAllTagsTool(BaseTool):
    """获取所有标签工具"""

    @property
    def name(self) -> str:
        return "get_all_tags"

    @property
    def description(self) -> str:
        return """获取经验库中所有使用过的标签。

用于了解现有的标签分类体系。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    async def execute(self, **params) -> ToolResult:
        try:
            tags = self.experience_service.get_all_tags()

            return ToolResult(
                success=True,
                data={
                    "tags": tags,
                    "count": len(tags),
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
