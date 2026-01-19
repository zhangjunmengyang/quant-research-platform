"""
检索 MCP 工具

提供统一的 RAG 检索接口。
"""

from typing import Any, Dict

from .base import BaseTool, ToolResult


class RetrieveTool(BaseTool):
    """
    统一检索工具

    对外提供简洁的 RAG 检索接口，支持:
    - 查询重写: 使用 LLM 优化查询
    - 前置过滤: 按研报 ID、分类过滤
    - 结果重排: 使用 LLM 对结果重新排序
    """

    @property
    def name(self) -> str:
        return "retrieve"

    @property
    def description(self) -> str:
        return """在研报知识库中检索相关内容。

这是一个 RAG 检索接口，根据查询语义检索最相关的研报片段。

支持功能:
- 查询重写: 自动优化查询以提升检索效果
- 前置过滤: 限定检索范围（按研报 ID 或分类）
- 结果重排: 对检索结果按相关性重新排序

使用场景:
- 查找特定主题的研报内容
- 获取某个概念的相关解释
- 查找量化研究观点"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "检索查询（自然语言）"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回结果数量",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50
                },
                "report_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "限定检索的研报 ID 列表（前置过滤）"
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "限定检索的分类列表（前置过滤）"
                },
                "min_score": {
                    "type": "number",
                    "description": "最小相似度分数 (0-1)",
                    "default": 0.0,
                    "minimum": 0,
                    "maximum": 1
                },
                "enable_rewrite": {
                    "type": "boolean",
                    "description": "是否启用查询重写",
                    "default": False
                },
                "enable_rerank": {
                    "type": "boolean",
                    "description": "是否启用结果重排",
                    "default": False
                }
            },
            "required": ["query"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            query = params.get("query", "")
            top_k = params.get("top_k", 10)
            report_ids = params.get("report_ids")
            categories = params.get("categories")
            min_score = params.get("min_score", 0.0)
            enable_rewrite = params.get("enable_rewrite", False)
            enable_rerank = params.get("enable_rerank", False)

            result = await self.retrieval_service.retrieve(
                query=query,
                top_k=top_k,
                report_ids=report_ids,
                categories=categories,
                min_score=min_score,
                enable_rewrite=enable_rewrite,
                enable_rerank=enable_rerank,
            )

            return ToolResult(
                success=True,
                data={
                    "query": result["query"],
                    "rewritten_query": result.get("rewritten_query"),
                    "total": result["total"],
                    "results": result["results"],
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
