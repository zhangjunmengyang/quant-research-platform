"""
经验 MCP 工具

提供经验的存储、检索、验证和管理功能。
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

经验分为三个层级:
- strategic: 战略级，长期有效的研究原则
- tactical: 战术级，特定场景下的研究结论
- operational: 操作级，具体的研究记录

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
                "experience_level": {
                    "type": "string",
                    "description": "经验层级",
                    "enum": ["strategic", "tactical", "operational"],
                    "default": "operational"
                },
                "category": {
                    "type": "string",
                    "description": "分类（如 factor_performance, market_regime_principle）"
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
                        "market_regime": {"type": "string", "description": "市场状态（牛市/熊市/震荡）"},
                        "factor_styles": {"type": "array", "items": {"type": "string"}, "description": "相关因子风格"},
                        "time_horizon": {"type": "string", "description": "时间范围（短期/中期/长期）"},
                        "asset_class": {"type": "string", "description": "资产类别"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "自定义标签"}
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
                },
                "confidence": {
                    "type": "number",
                    "description": "初始置信度（0-1）",
                    "minimum": 0,
                    "maximum": 1
                }
            },
            "required": ["title", "experience_level", "content"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            title = params.get("title", "")
            experience_level = params.get("experience_level", "operational")
            category = params.get("category", "")
            content = params.get("content", {})
            context = params.get("context")
            source_type = params.get("source_type", "manual")
            source_ref = params.get("source_ref", "")
            confidence = params.get("confidence")

            success, message, experience_id = self.experience_service.store_experience(
                title=title,
                experience_level=experience_level,
                category=category,
                content=content,
                context=context,
                source_type=source_type,
                source_ref=source_ref,
                confidence=confidence,
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
                "experience_level": {
                    "type": "string",
                    "description": "过滤层级",
                    "enum": ["strategic", "tactical", "operational"]
                },
                "category": {
                    "type": "string",
                    "description": "过滤分类"
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
                "min_confidence": {
                    "type": "number",
                    "description": "最低置信度",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0
                },
                "include_deprecated": {
                    "type": "boolean",
                    "description": "是否包含已废弃经验",
                    "default": False
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
            experience_level = params.get("experience_level")
            category = params.get("category")
            market_regime = params.get("market_regime")
            factor_styles = params.get("factor_styles")
            min_confidence = params.get("min_confidence", 0)
            include_deprecated = params.get("include_deprecated", False)
            top_k = params.get("top_k", 5)

            experiences = self.experience_service.query_experiences(
                query=query,
                experience_level=experience_level,
                category=category,
                market_regime=market_regime,
                factor_styles=factor_styles,
                min_confidence=min_confidence,
                include_deprecated=include_deprecated,
                top_k=top_k,
            )

            exp_list = []
            for exp in experiences:
                exp_list.append({
                    "id": exp.id,
                    "uuid": exp.uuid,
                    "title": exp.title,
                    "experience_level": exp.experience_level,
                    "category": exp.category,
                    "summary": exp.summary,
                    "confidence": exp.confidence,
                    "status": exp.status,
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

通过经验 ID 获取完整的经验详情，包括 PARL 内容、上下文、验证状态等。"""

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
                    "experience_level": experience.experience_level,
                    "category": experience.category,
                    "content": experience.content.to_dict() if hasattr(experience.content, 'to_dict') else experience.content,
                    "context": experience.context.to_dict() if hasattr(experience.context, 'to_dict') else experience.context,
                    "source_type": experience.source_type,
                    "source_ref": experience.source_ref,
                    "confidence": experience.confidence,
                    "validation_count": experience.validation_count,
                    "last_validated": str(experience.last_validated) if experience.last_validated else None,
                    "status": experience.status,
                    "deprecated_reason": experience.deprecated_reason,
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

支持按层级、分类、状态等条件筛选，返回经验摘要列表。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "experience_level": {
                    "type": "string",
                    "description": "按层级筛选",
                    "enum": ["strategic", "tactical", "operational"]
                },
                "category": {
                    "type": "string",
                    "description": "按分类筛选"
                },
                "status": {
                    "type": "string",
                    "description": "按状态筛选",
                    "enum": ["draft", "validated", "deprecated"]
                },
                "min_confidence": {
                    "type": "number",
                    "description": "最低置信度",
                    "minimum": 0,
                    "maximum": 1
                },
                "include_deprecated": {
                    "type": "boolean",
                    "description": "是否包含已废弃",
                    "default": False
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
        try:
            experience_level = params.get("experience_level", "")
            category = params.get("category", "")
            status = params.get("status", "")
            min_confidence = params.get("min_confidence", 0.0)
            include_deprecated = params.get("include_deprecated", False)
            page = params.get("page", 1)
            page_size = params.get("page_size", 20)

            experiences, total = self.experience_service.list_experiences(
                experience_level=experience_level,
                category=category,
                status=status,
                min_confidence=min_confidence,
                include_deprecated=include_deprecated,
                page=page,
                page_size=page_size,
            )

            exp_list = []
            for exp in experiences:
                exp_list.append({
                    "id": exp.id,
                    "uuid": exp.uuid,
                    "title": exp.title,
                    "experience_level": exp.experience_level,
                    "category": exp.category,
                    "summary": exp.summary,
                    "confidence": exp.confidence,
                    "status": exp.status,
                    "validation_count": exp.validation_count,
                    "updated_at": str(exp.updated_at) if exp.updated_at else None,
                })

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


class ValidateExperienceTool(BaseTool):
    """验证经验工具"""

    @property
    def name(self) -> str:
        return "validate_experience"

    @property
    def description(self) -> str:
        return """验证/增强经验。

当后续研究证实了某条经验时调用。
会增加验证次数、提升置信度、更新状态为 validated。

使用场景:
- 新的回测结果证实了之前的经验
- 实盘表现验证了某个研究结论
- 多次独立观察得出相同结论"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "experience_id": {
                    "type": "integer",
                    "description": "经验 ID"
                },
                "validation_note": {
                    "type": "string",
                    "description": "验证说明（可选）"
                },
                "confidence_delta": {
                    "type": "number",
                    "description": "置信度增量（默认 0.1）",
                    "minimum": 0,
                    "maximum": 0.5
                }
            },
            "required": ["experience_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            experience_id = params.get("experience_id")

            if experience_id is None:
                return ToolResult(success=False, error="experience_id 参数不能为空")

            validation_note = params.get("validation_note")
            confidence_delta = params.get("confidence_delta")

            success, message, data = self.experience_service.validate_experience(
                experience_id=experience_id,
                validation_note=validation_note,
                confidence_delta=confidence_delta,
            )

            if success:
                return ToolResult(success=True, data=data)
            else:
                return ToolResult(success=False, error=message)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class DeprecateExperienceTool(BaseTool):
    """废弃经验工具"""

    @property
    def name(self) -> str:
        return "deprecate_experience"

    @property
    def description(self) -> str:
        return """废弃经验。

当经验被证伪或已过时时调用。
会将状态更新为 deprecated，记录废弃原因。
经验记录会保留，但在检索时会降低权重。

使用场景:
- 市场结构变化导致经验不再适用
- 新的研究结果证伪了之前的结论
- 经验所依赖的条件已不再成立"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "experience_id": {
                    "type": "integer",
                    "description": "经验 ID"
                },
                "reason": {
                    "type": "string",
                    "description": "废弃原因"
                }
            },
            "required": ["experience_id", "reason"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            experience_id = params.get("experience_id")
            reason = params.get("reason", "")

            success, message, data = self.experience_service.deprecate_experience(
                experience_id=experience_id,
                reason=reason,
            )

            if success:
                return ToolResult(success=True, data=data)
            else:
                return ToolResult(success=False, error=message)

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


class CurateExperienceTool(BaseTool):
    """提炼经验工具"""

    @property
    def name(self) -> str:
        return "curate_experience"

    @property
    def description(self) -> str:
        return """从低层经验提炼高层经验。

将多个低层级经验抽象为更高层级的通用规律。
例如:
- 从多个 operational 经验总结为一个 tactical 结论
- 从多个 tactical 结论抽象为一个 strategic 原则

使用场景:
- 积累了多个类似的具体经验后进行总结
- 发现多个独立研究得出相似结论
- 抽象出可迁移的研究原则"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source_experience_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "源经验 ID 列表（至少2个）",
                    "minItems": 2
                },
                "target_level": {
                    "type": "string",
                    "description": "目标层级（必须高于源经验）",
                    "enum": ["tactical", "strategic"]
                },
                "title": {
                    "type": "string",
                    "description": "新经验标题"
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
                    "description": "上下文信息"
                }
            },
            "required": ["source_experience_ids", "target_level", "title", "content"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            source_experience_ids = params.get("source_experience_ids", [])
            target_level = params.get("target_level")
            title = params.get("title", "")
            content = params.get("content", {})
            context = params.get("context")

            success, message, experience_id = self.experience_service.curate_experience(
                source_experience_ids=source_experience_ids,
                target_level=target_level,
                title=title,
                content=content,
                context=context,
            )

            if success:
                return ToolResult(
                    success=True,
                    data={
                        "experience_id": experience_id,
                        "source_count": len(source_experience_ids),
                        "message": message
                    }
                )
            else:
                return ToolResult(success=False, error=message)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
