"""
语义检索 MCP 工具

提供研报的语义检索和 RAG 问答功能。
"""

from typing import Any, Dict

from .base import BaseTool, ToolResult


class SearchReportsTool(BaseTool):
    """语义搜索研报工具"""

    @property
    def name(self) -> str:
        return "search_reports"

    @property
    def description(self) -> str:
        return """在研报知识库中进行语义搜索。

使用向量相似度检索与查询语义相关的研报内容片段。
返回最相关的切块及其来源研报信息。

使用场景:
- 查找特定主题的研报内容
- 搜索包含某个概念的研报片段
- 查找相关的量化研究观点"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询（自然语言描述）"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回结果数量",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50
                },
                "report_id": {
                    "type": "integer",
                    "description": "限定搜索的研报 ID（可选）"
                },
                "min_score": {
                    "type": "number",
                    "description": "最小相似度分数（0-1）",
                    "default": 0.0,
                    "minimum": 0,
                    "maximum": 1
                }
            },
            "required": ["query"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            query = params.get("query", "")
            top_k = params.get("top_k", 10)
            report_id = params.get("report_id")
            min_score = params.get("min_score", 0.0)

            results = await self.retrieval_service.search(
                query=query,
                top_k=top_k,
                report_id=report_id,
                min_score=min_score,
            )

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "count": len(results),
                    "results": results,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class AskReportsTool(BaseTool):
    """RAG 问答工具"""

    @property
    def name(self) -> str:
        return "ask_reports"

    @property
    def description(self) -> str:
        return """基于研报知识库进行问答。

使用 RAG (检索增强生成) 技术，先检索相关研报内容，
然后基于检索到的内容生成回答。

回答会附带来源引用，便于验证和深入阅读。

使用场景:
- 询问量化研究相关问题
- 获取研报中的观点和结论
- 理解复杂的量化概念"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "问题（自然语言）"
                },
                "top_k": {
                    "type": "integer",
                    "description": "检索的切块数量",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20
                },
                "report_id": {
                    "type": "integer",
                    "description": "限定的研报 ID（可选，用于针对特定研报提问）"
                }
            },
            "required": ["question"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            question = params.get("question", "")
            top_k = params.get("top_k", 5)
            report_id = params.get("report_id")

            result = await self.retrieval_service.ask(
                question=question,
                top_k=top_k,
                report_id=report_id,
            )

            return ToolResult(
                success=True,
                data={
                    "question": question,
                    "answer": result["answer"],
                    "sources": result["sources"],
                    "retrieved_chunks": result["retrieved_chunks"],
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetSimilarChunksTool(BaseTool):
    """获取相似切块工具"""

    @property
    def name(self) -> str:
        return "get_similar_chunks"

    @property
    def description(self) -> str:
        return """获取与指定切块相似的其他切块。

用于发现相关内容，扩展阅读范围。

使用场景:
- 查找讨论相似主题的其他研报片段
- 发现不同研报中的相关观点
- 扩展阅读相关内容"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "chunk_id": {
                    "type": "string",
                    "description": "参考切块 ID"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回数量",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20
                },
                "exclude_same_report": {
                    "type": "boolean",
                    "description": "是否排除同一研报的切块",
                    "default": False
                }
            },
            "required": ["chunk_id"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            chunk_id = params.get("chunk_id", "")
            top_k = params.get("top_k", 5)
            exclude_same_report = params.get("exclude_same_report", False)

            results = await self.retrieval_service.get_similar_chunks(
                chunk_id=chunk_id,
                top_k=top_k,
                exclude_same_report=exclude_same_report,
            )

            if not results:
                return ToolResult(
                    success=False,
                    error=f"切块不存在或无相似切块: {chunk_id}"
                )

            return ToolResult(
                success=True,
                data={
                    "chunk_id": chunk_id,
                    "count": len(results),
                    "similar_chunks": results,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
