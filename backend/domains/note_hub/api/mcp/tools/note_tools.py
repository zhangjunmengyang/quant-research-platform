"""
笔记 MCP 工具

提供笔记的创建和搜索功能。
"""

from typing import Any, Dict

from .base import BaseTool, ToolResult


class CreateNoteTool(BaseTool):
    """创建笔记工具"""

    @property
    def name(self) -> str:
        return "create_note"

    @property
    def description(self) -> str:
        return """创建一条经验笔记。

用于记录量化研究过程中的洞察、经验和发现。

笔记支持:
- Markdown 格式的内容
- 标签分类
- 来源关联（如关联到某个因子）

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

            success, message, note_id = self.note_service.create_note(
                title=title,
                content=content,
                tags=tags,
                source=source,
                source_ref=source_ref,
            )

            if success:
                return ToolResult(
                    success=True,
                    data={
                        "id": note_id,
                        "title": title,
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
        return """搜索经验笔记。

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
            page = params.get("page", 1)
            page_size = params.get("page_size", 20)

            tags_list = None
            if tags_str:
                tags_list = [t.strip() for t in tags_str.split(',') if t.strip()]

            notes, total = self.note_service.list_notes(
                tags=tags_list,
                source=source,
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
