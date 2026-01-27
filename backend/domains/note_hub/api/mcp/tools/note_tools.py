"""
笔记 MCP 工具

提供笔记的创建、搜索和管理功能。

Note Hub 定位为"研究草稿/临时记录"层，MCP 工具支持：
- 基础 CRUD（create_note, update_note, get_note, list_notes, search_notes）
- 研究流程：通过 create_note 的 note_type 参数区分
  - observation: 观察 - 对数据或现象的客观记录
  - hypothesis: 假设 - 基于观察提出的待验证假说
  - verification: 检验 - 对假设的验证
- 实体关联：通过 link_note 建立与任意实体的关系（Edge 系统）
- 归档管理（archive_note, unarchive_note）
- 提炼为经验（promote_to_experience）
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
    def input_schema(self) -> Dict[str, Any]:
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
    def input_schema(self) -> Dict[str, Any]:
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


# ==================== 知识边关联工具 ====================


class LinkNoteTool(BaseTool):
    """关联笔记工具"""

    @property
    def name(self) -> str:
        return "link_note"

    @property
    def description(self) -> str:
        return """创建笔记与其他实体的关联。

建立笔记与数据、因子、策略、研报、经验等实体的关联关系。
用于构建知识图谱，实现数据-信息-知识-经验的链路追溯。

实体类型:
- data: 数据层（币种、K线等）
- factor: 因子
- strategy: 策略
- note: 其他笔记
- research: 外部研报
- experience: 经验记录

关系类型:
- derived_from: 派生自（如：笔记 derived_from 数据）
- references: 引用（如：笔记 references 研报）
- verifies: 验证（如：检验笔记 verifies 假设笔记）
- summarizes: 总结为（如：笔记 summarizes 多个观察）
- related: 一般关联（默认）

使用场景:
- 记录笔记引用的数据源
- 关联笔记与相关因子/策略
- 建立研究知识网络"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "integer",
                    "description": "笔记 ID"
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
            "required": ["note_id", "target_type", "target_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            note_id = params.get("note_id")
            target_type = params.get("target_type")
            target_id = params.get("target_id")
            relation = params.get("relation", "related")
            is_bidirectional = params.get("is_bidirectional", False)

            success, message, edge_id = self.note_service.link_note(
                note_id=note_id,
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
                        "note_id": note_id,
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


class GetNoteEdgesTool(BaseTool):
    """获取笔记关联工具"""

    @property
    def name(self) -> str:
        return "get_note_edges"

    @property
    def description(self) -> str:
        return """获取笔记的所有关联。

返回笔记与其他实体的关联列表，用于查看笔记的知识网络。

使用场景:
- 查看笔记引用了哪些数据源
- 了解笔记与其他实体的关系
- 探索知识图谱"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "integer",
                    "description": "笔记 ID"
                },
                "include_bidirectional": {
                    "type": "boolean",
                    "description": "是否包含双向关联",
                    "default": True
                }
            },
            "required": ["note_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            note_id = params.get("note_id")
            include_bidirectional = params.get("include_bidirectional", True)

            edges = self.note_service.get_note_edges(
                note_id=note_id,
                include_bidirectional=include_bidirectional,
            )

            return ToolResult(
                success=True,
                data={
                    "note_id": note_id,
                    "count": len(edges),
                    "edges": edges,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class TraceNoteLineageTool(BaseTool):
    """追溯笔记链路工具"""

    @property
    def name(self) -> str:
        return "trace_note_lineage"

    @property
    def description(self) -> str:
        return """追溯笔记的知识链路。

沿着知识图谱追溯笔记的来源或应用，实现数据-信息-知识-经验的链路追溯。

方向:
- backward: 向上追溯源头（笔记引用了什么）
- forward: 向下追溯应用（笔记被什么引用）

使用场景:
- 追溯笔记的数据来源
- 查看笔记被哪些经验引用
- 理解知识的演化路径"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "integer",
                    "description": "笔记 ID"
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
            "required": ["note_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            note_id = params.get("note_id")
            direction = params.get("direction", "backward")
            max_depth = params.get("max_depth", 5)

            lineage = self.note_service.trace_note_lineage(
                note_id=note_id,
                direction=direction,
                max_depth=max_depth,
            )

            return ToolResult(
                success=True,
                data={
                    "note_id": note_id,
                    "direction": direction,
                    "max_depth": max_depth,
                    "count": len(lineage),
                    "lineage": lineage,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
