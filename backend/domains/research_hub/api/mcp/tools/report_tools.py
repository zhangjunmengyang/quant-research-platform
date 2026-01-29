"""
研报管理 MCP 工具

提供研报的列表、详情、处理状态查询功能。
"""

from typing import Any

from .base import BaseTool, ToolResult


class ListReportsTool(BaseTool):
    """列出研报工具"""

    @property
    def name(self) -> str:
        return "list_reports"

    @property
    def description(self) -> str:
        return """列出研报知识库中的研报。

支持按状态和关键词筛选，返回研报摘要列表。

使用场景:
- 查看已入库的研报
- 筛选已处理完成的研报
- 搜索特定主题的研报"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "search": {
                    "type": "string",
                    "description": "搜索关键词（在标题和摘要中搜索）"
                },
                "status": {
                    "type": "string",
                    "description": "按状态筛选",
                    "enum": ["uploaded", "parsing", "parsed", "chunking", "chunked",
                             "embedding", "indexed", "ready", "failed"]
                },
                "category": {
                    "type": "string",
                    "description": "按分类筛选"
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
            search = params.get("search")
            status = params.get("status")
            category = params.get("category")
            page = params.get("page", 1)
            page_size = params.get("page_size", 20)

            offset = (page - 1) * page_size

            reports, total = await self.report_service.list_reports(
                search=search,
                status=status,
                category=category,
                limit=page_size,
                offset=offset,
            )

            report_list = []
            for r in reports:
                report_list.append({
                    "id": r.id,
                    "uuid": r.uuid,
                    "title": r.title,
                    "filename": r.filename,
                    "status": r.status,
                    "progress": r.progress,
                    "page_count": r.page_count,
                    "author": r.author,
                    "category": r.category,
                    "tags": r.tags,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                })

            return ToolResult(
                success=True,
                data={
                    "reports": report_list,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetReportTool(BaseTool):
    """获取研报详情工具"""

    @property
    def name(self) -> str:
        return "get_report"

    @property
    def description(self) -> str:
        return """获取单个研报的详细信息。

通过研报 ID 获取完整的研报详情，包括:
- 基本信息（标题、作者、分类等）
- 处理状态和进度
- 解析后的内容摘要
- 标签和分类信息"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "report_id": {
                    "type": "integer",
                    "description": "研报 ID"
                },
                "include_content": {
                    "type": "boolean",
                    "description": "是否包含完整 Markdown 内容",
                    "default": False
                }
            },
            "required": ["report_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            report_id = params.get("report_id")
            include_content = params.get("include_content", False)

            report = await self.report_service.get_report(report_id)
            if report is None:
                return ToolResult(
                    success=False,
                    error=f"研报不存在: {report_id}"
                )

            data = {
                "id": report.id,
                "uuid": report.uuid,
                "title": report.title,
                "filename": report.filename,
                "file_size": report.file_size,
                "page_count": report.page_count,
                "author": report.author,
                "source_url": report.source_url,
                "category": report.category,
                "tags": report.tags,
                "summary": report.summary,
                "status": report.status,
                "progress": report.progress,
                "error_message": report.error_message,
                "created_at": report.created_at.isoformat() if report.created_at else None,
                "parsed_at": report.parsed_at.isoformat() if report.parsed_at else None,
                "indexed_at": report.indexed_at.isoformat() if report.indexed_at else None,
            }

            if include_content:
                data["content_markdown"] = report.content_markdown

            return ToolResult(success=True, data=data)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetReportStatusTool(BaseTool):
    """获取研报处理状态工具"""

    @property
    def name(self) -> str:
        return "get_report_status"

    @property
    def description(self) -> str:
        return """获取研报的处理状态。

用于查询研报的处理进度，包括:
- 当前处理阶段
- 处理进度百分比
- 切块数量
- 错误信息（如果有）"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "report_id": {
                    "type": "integer",
                    "description": "研报 ID"
                }
            },
            "required": ["report_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            report_id = params.get("report_id")

            status = await self.report_service.get_processing_status(report_id)

            if "error" in status:
                return ToolResult(success=False, error=status["error"])

            return ToolResult(success=True, data=status)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetReportChunksTool(BaseTool):
    """获取研报切块工具"""

    @property
    def name(self) -> str:
        return "get_report_chunks"

    @property
    def description(self) -> str:
        return """获取研报的所有切块。

用于查看研报被切分后的内容片段，每个切块包含:
- 切块内容
- 所属章节
- 页码范围
- Token 数量"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "report_id": {
                    "type": "integer",
                    "description": "研报 ID"
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
            },
            "required": ["report_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            report_id = params.get("report_id")
            page = params.get("page", 1)
            page_size = params.get("page_size", 20)

            # 获取所有切块
            chunks = await self.report_service.get_report_chunks(report_id)

            # 分页
            total = len(chunks)
            start = (page - 1) * page_size
            end = start + page_size
            page_chunks = chunks[start:end]

            chunk_list = []
            for c in page_chunks:
                chunk_list.append({
                    "chunk_id": c.chunk_id,
                    "chunk_index": c.chunk_index,
                    "chunk_type": c.chunk_type,
                    "content": c.content,
                    "token_count": c.token_count,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                    "section_title": c.section_title,
                })

            return ToolResult(
                success=True,
                data={
                    "chunks": chunk_list,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
