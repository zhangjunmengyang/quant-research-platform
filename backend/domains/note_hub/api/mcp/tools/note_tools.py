"""
笔记 MCP 工具

提供笔记的创建、搜索和研究记录功能。

Note Hub 定位为"研究草稿/临时记录"层，MCP 工具支持：
- 基础 CRUD（create_note, get_note, list_notes, search_notes）
- 研究记录（record_observation, record_hypothesis, record_finding）
- 研究轨迹（get_research_trail）
- 归档管理（archive_note）
"""

from typing import Any, Dict

from .base import BaseTool, ToolResult


# ==================== 基础 CRUD 工具 ====================


class CreateNoteTool(BaseTool):
    """创建笔记工具"""

    @property
    def name(self) -> str:
        return "create_note"

    @property
    def description(self) -> str:
        return """创建一条经验概览。

用于记录量化研究过程中的洞察、经验和发现。

笔记支持:
- Markdown 格式的内容
- 标签分类
- 来源关联（如关联到某个因子）
- 笔记类型（observation/hypothesis/finding/trail/general）
- 研究会话关联

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
                    "description": "笔记标题"
                },
                "content": {
                    "type": "string",
                    "description": "笔记内容（支持 Markdown 格式）"
                },
                "tags": {
                    "type": "string",
                    "description": "标签（英文逗号分隔，如: 动量,反转,经验）"
                },
                "source": {
                    "type": "string",
                    "description": "来源类型（如: factor, strategy, backtest, manual）",
                    "enum": ["factor", "strategy", "backtest", "manual"]
                },
                "source_ref": {
                    "type": "string",
                    "description": "来源引用（如因子名: Momentum_5d）"
                },
                "note_type": {
                    "type": "string",
                    "description": "笔记类型",
                    "enum": ["observation", "hypothesis", "finding", "trail", "general"],
                    "default": "general"
                },
                "research_session_id": {
                    "type": "string",
                    "description": "研究会话 ID（用于追踪研究轨迹）"
                }
            },
            "required": ["title", "content"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            title = params.get("title", "")
            content = params.get("content", "")
            tags = params.get("tags", "")
            source = params.get("source", "")
            source_ref = params.get("source_ref", "")
            note_type = params.get("note_type", "general")
            research_session_id = params.get("research_session_id")

            success, message, note_id = self.note_service.create_note(
                title=title,
                content=content,
                tags=tags,
                source=source,
                source_ref=source_ref,
                note_type=note_type,
                research_session_id=research_session_id,
            )

            if success:
                return ToolResult(
                    success=True,
                    data={
                        "id": note_id,
                        "title": title,
                        "note_type": note_type,
                        "message": message
                    }
                )
            else:
                return ToolResult(success=False, error=message)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class SearchNotesTool(BaseTool):
    """搜索笔记工具"""

    @property
    def name(self) -> str:
        return "search_notes"

    @property
    def description(self) -> str:
        return """搜索经验概览。

在标题和内容中搜索关键词，返回匹配的笔记列表。

使用场景:
- 查找之前记录的经验
- 搜索特定主题的笔记
- 回顾历史洞察"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回数量限制",
                    "default": 20,
                    "maximum": 50
                }
            },
            "required": ["keyword"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            keyword = params.get("keyword", "")
            limit = params.get("limit", 20)

            notes = self.note_service.search_notes(keyword, limit)

            note_list = []
            for note in notes:
                note_list.append({
                    "id": note.id,
                    "title": note.title,
                    "summary": note.summary,
                    "tags": note.tags,
                    "source": note.source,
                    "note_type": note.note_type,
                    "is_archived": note.is_archived,
                    "updated_at": str(note.updated_at) if note.updated_at else None,
                })

            return ToolResult(
                success=True,
                data={
                    "keyword": keyword,
                    "count": len(note_list),
                    "notes": note_list,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetNoteTool(BaseTool):
    """获取笔记详情工具"""

    @property
    def name(self) -> str:
        return "get_note"

    @property
    def description(self) -> str:
        return """获取单个笔记的完整内容。

通过笔记 ID 获取完整的笔记详情，包括标题、内容、标签等。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "integer",
                    "description": "笔记 ID"
                }
            },
            "required": ["note_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            note_id = params.get("note_id")

            note = self.note_service.get_note(note_id)
            if note is None:
                return ToolResult(
                    success=False,
                    error=f"笔记不存在: {note_id}"
                )

            return ToolResult(
                success=True,
                data={
                    "id": note.id,
                    "title": note.title,
                    "content": note.content,
                    "tags": note.tags,
                    "source": note.source,
                    "source_ref": note.source_ref,
                    "note_type": note.note_type,
                    "research_session_id": note.research_session_id,
                    "promoted_to_experience_id": note.promoted_to_experience_id,
                    "is_archived": note.is_archived,
                    "created_at": str(note.created_at) if note.created_at else None,
                    "updated_at": str(note.updated_at) if note.updated_at else None,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ListNotesTool(BaseTool):
    """获取笔记列表工具"""

    @property
    def name(self) -> str:
        return "list_notes"

    @property
    def description(self) -> str:
        return """获取笔记列表。

支持按标签和来源筛选，返回笔记摘要列表。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "string",
                    "description": "按标签筛选（英文逗号分隔）"
                },
                "source": {
                    "type": "string",
                    "description": "按来源筛选"
                },
                "note_type": {
                    "type": "string",
                    "description": "按笔记类型筛选",
                    "enum": ["observation", "hypothesis", "finding", "trail", "general"]
                },
                "is_archived": {
                    "type": "boolean",
                    "description": "按归档状态筛选（true=已归档，false=未归档）"
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
            tags_str = params.get("tags", "")
            source = params.get("source", "")
            note_type = params.get("note_type", "")
            is_archived = params.get("is_archived")
            page = params.get("page", 1)
            page_size = params.get("page_size", 20)

            tags_list = None
            if tags_str:
                tags_list = [t.strip() for t in tags_str.split(',') if t.strip()]

            notes, total = self.note_service.list_notes(
                tags=tags_list,
                source=source,
                note_type=note_type,
                is_archived=is_archived,
                page=page,
                page_size=page_size,
            )

            note_list = []
            for note in notes:
                note_list.append({
                    "id": note.id,
                    "title": note.title,
                    "summary": note.summary,
                    "tags": note.tags,
                    "source": note.source,
                    "note_type": note.note_type,
                    "is_archived": note.is_archived,
                    "updated_at": str(note.updated_at) if note.updated_at else None,
                })

            return ToolResult(
                success=True,
                data={
                    "notes": note_list,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ==================== 研究记录工具 ====================


class RecordObservationTool(BaseTool):
    """记录观察工具"""

    @property
    def name(self) -> str:
        return "record_observation"

    @property
    def description(self) -> str:
        return """记录研究观察。

观察是对数据或现象的客观记录，是研究的起点。
用于记录在分析过程中发现的有趣现象或数据特征。

使用场景:
- 记录因子在特定市场条件下的表现
- 记录异常数据点或模式
- 记录策略行为的观察结果"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "观察标题"
                },
                "content": {
                    "type": "string",
                    "description": "观察内容（支持 Markdown 格式）"
                },
                "tags": {
                    "type": "string",
                    "description": "标签（英文逗号分隔）"
                },
                "source": {
                    "type": "string",
                    "description": "来源类型",
                    "enum": ["factor", "strategy", "backtest", "manual"]
                },
                "source_ref": {
                    "type": "string",
                    "description": "来源引用"
                },
                "research_session_id": {
                    "type": "string",
                    "description": "研究会话 ID（用于追踪研究轨迹）"
                }
            },
            "required": ["title", "content"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            success, message, note_id = self.note_service.record_observation(
                title=params.get("title", ""),
                content=params.get("content", ""),
                tags=params.get("tags", ""),
                source=params.get("source", ""),
                source_ref=params.get("source_ref", ""),
                research_session_id=params.get("research_session_id"),
            )

            if success:
                return ToolResult(
                    success=True,
                    data={
                        "id": note_id,
                        "title": params.get("title"),
                        "note_type": "observation",
                        "message": "观察记录成功"
                    }
                )
            else:
                return ToolResult(success=False, error=message)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class RecordHypothesisTool(BaseTool):
    """记录假设工具"""

    @property
    def name(self) -> str:
        return "record_hypothesis"

    @property
    def description(self) -> str:
        return """记录研究假设。

假设是基于观察提出的待验证假说。
用于记录需要通过实验或回测验证的猜想。

使用场景:
- 提出新的因子构造假设
- 提出策略改进假设
- 提出市场行为解释假设"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "假设标题"
                },
                "content": {
                    "type": "string",
                    "description": "假设内容（支持 Markdown 格式）"
                },
                "tags": {
                    "type": "string",
                    "description": "标签（英文逗号分隔）"
                },
                "source": {
                    "type": "string",
                    "description": "来源类型",
                    "enum": ["factor", "strategy", "backtest", "manual"]
                },
                "source_ref": {
                    "type": "string",
                    "description": "来源引用"
                },
                "research_session_id": {
                    "type": "string",
                    "description": "研究会话 ID（用于追踪研究轨迹）"
                }
            },
            "required": ["title", "content"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            success, message, note_id = self.note_service.record_hypothesis(
                title=params.get("title", ""),
                content=params.get("content", ""),
                tags=params.get("tags", ""),
                source=params.get("source", ""),
                source_ref=params.get("source_ref", ""),
                research_session_id=params.get("research_session_id"),
            )

            if success:
                return ToolResult(
                    success=True,
                    data={
                        "id": note_id,
                        "title": params.get("title"),
                        "note_type": "hypothesis",
                        "message": "假设记录成功"
                    }
                )
            else:
                return ToolResult(success=False, error=message)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class RecordFindingTool(BaseTool):
    """记录发现工具"""

    @property
    def name(self) -> str:
        return "record_finding"

    @property
    def description(self) -> str:
        return """记录研究发现。

发现是验证后的结论，是研究的成果。
用于记录经过验证的有价值的研究结论。

使用场景:
- 记录回测验证的因子效果
- 记录策略优化的有效改进
- 记录市场规律的发现"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "发现标题"
                },
                "content": {
                    "type": "string",
                    "description": "发现内容（支持 Markdown 格式）"
                },
                "tags": {
                    "type": "string",
                    "description": "标签（英文逗号分隔）"
                },
                "source": {
                    "type": "string",
                    "description": "来源类型",
                    "enum": ["factor", "strategy", "backtest", "manual"]
                },
                "source_ref": {
                    "type": "string",
                    "description": "来源引用"
                },
                "research_session_id": {
                    "type": "string",
                    "description": "研究会话 ID（用于追踪研究轨迹）"
                }
            },
            "required": ["title", "content"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            success, message, note_id = self.note_service.record_finding(
                title=params.get("title", ""),
                content=params.get("content", ""),
                tags=params.get("tags", ""),
                source=params.get("source", ""),
                source_ref=params.get("source_ref", ""),
                research_session_id=params.get("research_session_id"),
            )

            if success:
                return ToolResult(
                    success=True,
                    data={
                        "id": note_id,
                        "title": params.get("title"),
                        "note_type": "finding",
                        "message": "发现记录成功"
                    }
                )
            else:
                return ToolResult(success=False, error=message)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ==================== 研究轨迹工具 ====================


class GetResearchTrailTool(BaseTool):
    """获取研究轨迹工具"""

    @property
    def name(self) -> str:
        return "get_research_trail"

    @property
    def description(self) -> str:
        return """获取研究轨迹。

根据研究会话 ID 获取该会话中的所有笔记，按时间顺序排列。
用于回顾和追溯研究过程。

使用场景:
- 回顾研究过程
- 追溯决策依据
- 总结研究成果"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "research_session_id": {
                    "type": "string",
                    "description": "研究会话 ID"
                },
                "include_archived": {
                    "type": "boolean",
                    "description": "是否包含已归档的笔记",
                    "default": False
                }
            },
            "required": ["research_session_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            research_session_id = params.get("research_session_id", "")
            include_archived = params.get("include_archived", False)

            notes = self.note_service.get_research_trail(
                research_session_id=research_session_id,
                include_archived=include_archived,
            )

            note_list = []
            for note in notes:
                note_list.append({
                    "id": note.id,
                    "title": note.title,
                    "summary": note.summary,
                    "note_type": note.note_type,
                    "type_label": note.type_label,
                    "tags": note.tags,
                    "source": note.source,
                    "is_archived": note.is_archived,
                    "is_promoted": note.is_promoted,
                    "created_at": str(note.created_at) if note.created_at else None,
                })

            return ToolResult(
                success=True,
                data={
                    "research_session_id": research_session_id,
                    "count": len(note_list),
                    "trail": note_list,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ==================== 归档管理工具 ====================


class ArchiveNoteTool(BaseTool):
    """归档笔记工具"""

    @property
    def name(self) -> str:
        return "archive_note"

    @property
    def description(self) -> str:
        return """归档笔记。

将笔记标记为已归档状态，归档后笔记默认不会出现在列表中。
归档不会删除笔记，可以随时取消归档。

使用场景:
- 整理已完成的研究
- 隐藏不再关注的笔记
- 清理笔记列表"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "integer",
                    "description": "笔记 ID"
                }
            },
            "required": ["note_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            note_id = params.get("note_id")

            success, message = self.note_service.archive_note(note_id)

            if success:
                return ToolResult(
                    success=True,
                    data={
                        "note_id": note_id,
                        "message": message
                    }
                )
            else:
                return ToolResult(success=False, error=message)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class UnarchiveNoteTool(BaseTool):
    """取消归档笔记工具"""

    @property
    def name(self) -> str:
        return "unarchive_note"

    @property
    def description(self) -> str:
        return """取消归档笔记。

将笔记从归档状态恢复为正常状态。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "integer",
                    "description": "笔记 ID"
                }
            },
            "required": ["note_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            note_id = params.get("note_id")

            success, message = self.note_service.unarchive_note(note_id)

            if success:
                return ToolResult(
                    success=True,
                    data={
                        "note_id": note_id,
                        "message": message
                    }
                )
            else:
                return ToolResult(success=False, error=message)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ==================== 提炼为经验工具 ====================


class PromoteToExperienceTool(BaseTool):
    """提炼为经验工具"""

    @property
    def name(self) -> str:
        return "promote_to_experience"

    @property
    def description(self) -> str:
        return """标记笔记已提炼为经验。

将笔记标记为已提炼为经验，关联到经验库中的记录。
注意：此工具仅标记关联关系，不会自动创建经验。

使用场景:
- 将有价值的发现提炼为正式经验
- 追踪笔记与经验的关系"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "integer",
                    "description": "笔记 ID"
                },
                "experience_id": {
                    "type": "integer",
                    "description": "经验 ID（经验库中的记录 ID）"
                }
            },
            "required": ["note_id", "experience_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            note_id = params.get("note_id")
            experience_id = params.get("experience_id")

            success, message = self.note_service.promote_to_experience(
                note_id=note_id,
                experience_id=experience_id,
            )

            if success:
                return ToolResult(
                    success=True,
                    data={
                        "note_id": note_id,
                        "experience_id": experience_id,
                        "message": message
                    }
                )
            else:
                return ToolResult(success=False, error=message)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
