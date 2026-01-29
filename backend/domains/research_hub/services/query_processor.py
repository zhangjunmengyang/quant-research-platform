"""
查询处理服务

提供查询重写和结果重排功能，用于优化 RAG 检索效果。
"""

import logging
from typing import Any

from domains.mcp_core.llm import get_llm_client

logger = logging.getLogger(__name__)


# 查询重写 Prompt
QUERY_REWRITE_SYSTEM_PROMPT = """你是一个查询优化专家。你的任务是将用户的查询改写成更适合向量检索的形式。

改写原则:
1. 保持原始查询的核心意图
2. 扩展同义词和相关术语
3. 使用更精确的专业术语
4. 移除无关的修饰词

只输出改写后的查询，不要输出任何解释。"""

QUERY_REWRITE_USER_PROMPT = """请将以下查询改写成更适合语义检索的形式:

原始查询: {query}

改写后的查询:"""


# 结果重排 Prompt
RERANK_SYSTEM_PROMPT = """你是一个文档相关性评估专家。给定一个查询和多个文档片段，你需要评估每个片段与查询的相关性。

评分标准 (0-10):
- 10: 完全匹配，直接回答查询
- 7-9: 高度相关，包含关键信息
- 4-6: 部分相关，包含一些有用信息
- 1-3: 略微相关，只有边缘关联
- 0: 完全不相关

输出格式: 按相关性从高到低排序，每行一个序号。例如: 3,1,5,2,4"""

RERANK_USER_PROMPT = """查询: {query}

文档片段:
{documents}

请按相关性从高到低排序，只输出序号，用逗号分隔:"""


class QueryProcessor:
    """
    查询处理器

    提供:
    - 查询重写: 优化用户查询以提升检索效果
    - 结果重排: 使用 LLM 对检索结果进行重新排序
    """

    def __init__(self, model_key: str | None = None):
        """
        初始化查询处理器

        Args:
            model_key: LLM 模型 key，None 则使用默认模型
        """
        self.model_key = model_key
        self._llm_client = None

    @property
    def llm_client(self):
        if self._llm_client is None:
            self._llm_client = get_llm_client()
        return self._llm_client

    async def rewrite_query(self, query: str) -> str:
        """
        重写查询

        使用 LLM 将用户查询改写成更适合向量检索的形式。

        Args:
            query: 原始查询

        Returns:
            改写后的查询
        """
        try:
            messages = [
                {"role": "system", "content": QUERY_REWRITE_SYSTEM_PROMPT},
                {"role": "user", "content": QUERY_REWRITE_USER_PROMPT.format(query=query)},
            ]

            rewritten = await self.llm_client.ainvoke(
                messages=messages,
                model_key=self.model_key,
                temperature=0.3,
                max_tokens=256,
                caller="research_hub.query_processor",
                purpose="query_rewrite",
            )

            rewritten = rewritten.strip()
            if not rewritten:
                return query

            logger.info(f"查询重写: '{query[:50]}...' -> '{rewritten[:50]}...'")
            return rewritten

        except Exception as e:
            logger.warning(f"查询重写失败，使用原始查询: {e}")
            return query

    async def rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        重排检索结果

        使用 LLM 对检索结果按相关性重新排序。

        Args:
            query: 查询文本
            results: 检索结果列表
            top_k: 返回前 K 个结果，None 则返回全部

        Returns:
            重排后的结果列表
        """
        if not results:
            return results

        if len(results) <= 1:
            return results

        try:
            # 构建文档列表
            doc_texts = []
            for i, r in enumerate(results):
                content = r.get("content", "")[:500]  # 限制长度
                doc_texts.append(f"[{i + 1}] {content}")

            documents = "\n\n".join(doc_texts)

            messages = [
                {"role": "system", "content": RERANK_SYSTEM_PROMPT},
                {"role": "user", "content": RERANK_USER_PROMPT.format(
                    query=query,
                    documents=documents,
                )},
            ]

            response = await self.llm_client.ainvoke(
                messages=messages,
                model_key=self.model_key,
                temperature=0.1,
                max_tokens=128,
                caller="research_hub.query_processor",
                purpose="rerank",
            )

            # 解析排序结果
            order = self._parse_rerank_response(response, len(results))

            # 按新顺序重排
            reranked = [results[i] for i in order]

            if top_k and top_k < len(reranked):
                reranked = reranked[:top_k]

            logger.info(f"重排完成: {len(results)} -> {len(reranked)} 条结果")
            return reranked

        except Exception as e:
            logger.warning(f"重排失败，返回原始顺序: {e}")
            if top_k and top_k < len(results):
                return results[:top_k]
            return results

    def _parse_rerank_response(self, response: str, total: int) -> list[int]:
        """
        解析重排响应

        Args:
            response: LLM 响应（逗号分隔的序号）
            total: 文档总数

        Returns:
            0-indexed 的排序列表
        """
        try:
            # 提取数字
            parts = response.strip().replace(" ", "").split(",")
            order = []
            seen = set()

            for part in parts:
                try:
                    idx = int(part) - 1  # 转为 0-indexed
                    if 0 <= idx < total and idx not in seen:
                        order.append(idx)
                        seen.add(idx)
                except ValueError:
                    continue

            # 添加缺失的索引（保持原始顺序）
            for i in range(total):
                if i not in seen:
                    order.append(i)

            return order

        except Exception:
            # 解析失败，返回原始顺序
            return list(range(total))


# 单例管理
_query_processor: QueryProcessor | None = None


def get_query_processor(model_key: str | None = None) -> QueryProcessor:
    """获取查询处理器单例"""
    global _query_processor
    if _query_processor is None:
        _query_processor = QueryProcessor(model_key)
    return _query_processor
