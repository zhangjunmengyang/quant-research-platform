"""
笔记 MCP 工具

提供笔记的创建、搜索和管理功能。

Note Hub 定位为"研究草稿/临时记录"层，MCP 工具支持：
- 基础 CRUD（create_note, update_note, delete_note, get_note, list_notes, search_notes）
- 研究流程：通过 create_note 的 note_type 参数区分
  - observation: 观察 - 对数据或现象的客观记录
  - hypothesis: 假设 - 基于观察提出的待验证假说
  - verification: 检验 - 对假设的验证
- 实体关联：通过 link_note 建立与任意实体的关系（Edge 系统）
- 归档管理（archive_note, unarchive_note）
- 提炼为经验（promote_to_experience）
"""

from typing import Any

from .base import BaseTool, ToolResult

# ==================== 基础 CRUD 工具 ====================


class CreateNoteTool(BaseTool):
    """创建笔记工具"""

    @property
    def name(self) -> str:
        return "create_note"

    @property
    def description(self) -> str:
        return """创建一条研究笔记。

用于记录量化研究过程中的观察、假设和检验。

笔记类型（通过 note_type 参数指定）:
- observation: 观察 - 对数据或现象的客观记录（默认）
- hypothesis: 假设 - 基于观察提出的待验证假说
- verification: 检验 - 对假设的验证过程和结论

创建笔记后，可使用 link_note 工具建立与其他实体的关联:
- 关联数据源: link_note(note_id, "data", "BTC-USDT", "derived_from")
- 检验关联假设: link_note(verification_id, "note", str(hypothesis_id), "verifies")

使用场景:
- 记录因子在特定条件下的表现（observation）
- 提出因子构造或策略改进假设（hypothesis）
- 记录假设验证的过程和结论（verification）"""

    @property
    def input_schema(self) -> dict[str, Any]:
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
                "note_type": {
                    "type": "string",
                    "description": "笔记类型",
                    "enum": ["observation", "hypothesis", "verification"],
                    "default": "observation"
                }
            },
            "required": ["title", "content"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            title = params.get("title", "")
            content = params.get("content", "")
            tags = params.get("tags", "")
            note_type = params.get("note_type", "observation")

            success, message, note_id = self.note_service.create_note(
                title=title,
                content=content,
                tags=tags,
                note_type=note_type,
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


class UpdateNoteTool(BaseTool):
    """更新笔记工具"""

    @property
    def name(self) -> str:
        return "update_note"

    @property
    def description(self) -> str:
        return """更新笔记字段。

支持更新标题、内容、标签等字段。
只需提供需要更新的字段，未提供的字段保持不变。

使用场景:
- 修改笔记标题
- 更新笔记内容
- 调整标签分类
- 变更笔记类型"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "integer",
                    "description": "笔记 ID"
                },
                "title": {
                    "type": "string",
                    "description": "新标题"
                },
                "content": {
                    "type": "string",
                    "description": "新内容（支持 Markdown 格式）"
                },
                "tags": {
                    "type": "string",
                    "description": "新标签（英文逗号分隔）"
                },
                "note_type": {
                    "type": "string",
                    "description": "新笔记类型",
                    "enum": ["observation", "hypothesis", "verification"]
                }
            },
            "required": ["note_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            note_id = params.get("note_id")

            # 构建更新字段
            update_fields = {}
            for field in ["title", "content", "tags", "note_type"]:
                if field in params and params[field] is not None:
                    update_fields[field] = params[field]

            if not update_fields:
                return ToolResult(success=False, error="没有需要更新的字段")

            # 验证笔记存在
            note = self.note_service.get_note(note_id)
            if note is None:
                return ToolResult(success=False, error=f"笔记不存在: {note_id}")

            success = self.note_service.update_note(note_id, **update_fields)

            if success:
                # 获取更新后的笔记
                updated_note = self.note_service.get_note(note_id)
                return ToolResult(
                    success=True,
                    data={
                        "id": note_id,
                        "title": updated_note.title,
                        "updated_fields": list(update_fields.keys()),
                        "message": "更新成功"
                    }
                )
            else:
                return ToolResult(success=False, error="更新失败")

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
    def input_schema(self) -> dict[str, Any]:
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
    def input_schema(self) -> dict[str, Any]:
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
                    "note_type": note.note_type,
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

支持按标签筛选，返回笔记摘要列表。"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "string",
                    "description": "按标签筛选（英文逗号分隔）"
                },
                "note_type": {
                    "type": "string",
                    "description": "按笔记类型筛选",
                    "enum": ["observation", "hypothesis", "verification"]
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
            note_type = params.get("note_type", "")
            is_archived = params.get("is_archived")
            page = params.get("page", 1)
            page_size = params.get("page_size", 20)

            tags_list = None
            if tags_str:
                tags_list = [t.strip() for t in tags_str.split(',') if t.strip()]

            notes, total = self.note_service.list_notes(
                tags=tags_list,
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


# ==================== 删除工具 ====================


class DeleteNoteTool(BaseTool):
    """删除笔记工具"""

    @property
    def name(self) -> str:
        return "delete_note"

    @property
    def description(self) -> str:
        return """永久删除笔记。

删除操作不可恢复，请谨慎使用。
如果只是想隐藏笔记，建议使用 archive_note 进行归档。

使用场景:
- 删除错误创建的笔记
- 清理无价值的临时记录"""

    @property
    def input_schema(self) -> dict[str, Any]:
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

            # 验证笔记存在
            note = self.note_service.get_note(note_id)
            if note is None:
                return ToolResult(success=False, error=f"笔记不存在: {note_id}")

            success = self.note_service.delete_note(note_id)

            if success:
                return ToolResult(
                    success=True,
                    data={
                        "note_id": note_id,
                        "message": "删除成功"
                    }
                )
            else:
                return ToolResult(success=False, error="删除失败")

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
    def input_schema(self) -> dict[str, Any]:
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
    def input_schema(self) -> dict[str, Any]:
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
    def input_schema(self) -> dict[str, Any]:
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


# 注: 知识边关联工具已迁移至 graph-hub (端口 6795)
# 请使用 graph-hub 的 create_link, delete_link, get_edges, trace_lineage 工具
