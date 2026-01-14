"""
LlamaIndex RAG 服务

基于 LlamaIndex 框架的 RAG 实现，替代原有的自研 rag/ 模块。
代码量从 4,834 行精简到约 200 行。
"""

import logging
import os
from typing import Any, Dict, List, Optional

from llama_index.core import Settings, VectorStoreIndex, PromptTemplate
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, TextNode, QueryBundle
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters, FilterOperator
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.postgres import PGVectorStore

logger = logging.getLogger(__name__)


# =============================================================================
# 自定义 PostProcessor（唯一需要继承的组件）
# =============================================================================


class ExcludeSameReportPostProcessor(BaseNodePostprocessor):
    """
    排除同一研报的后处理器

    用于因子对比分析时，排除来自同一研报的切块，
    发现跨研报的相似观点。
    """

    exclude_report_id: Optional[str] = None

    def __init__(self, exclude_report_id: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.exclude_report_id = exclude_report_id

    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        if not self.exclude_report_id:
            return nodes

        return [
            node for node in nodes
            if node.node.metadata.get("report_id") != self.exclude_report_id
            and node.node.metadata.get("report_uuid") != self.exclude_report_id
        ]


# =============================================================================
# 自定义 Prompt
# =============================================================================


QA_PROMPT = PromptTemplate(
    """你是一个专业的量化研究助手，帮助用户理解和分析量化研究报告。

你的职责:
1. 基于提供的研报内容准确回答用户问题
2. 如果上下文不足以回答问题，请明确说明
3. 回答时引用具体来源，使用 [1]、[2] 等标注
4. 保持专业、准确、简洁的风格

注意:
- 只使用提供的上下文信息回答，不要编造内容
- 如果涉及具体数据或公式，确保准确引用
- 对于复杂问题，可以分步骤解释

## 研报内容

{context_str}

## 问题

{query_str}

请基于上述内容回答问题。如果内容不足以回答，请说明。引用来源时使用 [1]、[2] 等标注。"""
)


# =============================================================================
# LlamaIndex RAG 服务
# =============================================================================


class LlamaIndexRAGService:
    """
    基于 LlamaIndex 的 RAG 服务

    功能:
    - 文档摄取（解析 + 切块 + 嵌入 + 存储）
    - 语义检索
    - RAG 问答
    - 相似切块查询

    使用示例:
        service = LlamaIndexRAGService()
        await service.setup()

        # 摄取文档
        nodes = await service.ingest_document(file_path, report_id, report_uuid)

        # 语义检索
        results = await service.search("什么是动量因子")

        # RAG 问答
        answer = await service.ask("动量因子的计算公式是什么？")
    """

    def __init__(
        self,
        embedding_model: str = "text-embedding-3-small",
        embedding_dim: int = 1536,
        llm_model: str = "gpt-4o-mini",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        table_name: str = "research_chunks_llama",
    ):
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim
        self.llm_model = llm_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.table_name = table_name

        self._vector_store: Optional[PGVectorStore] = None
        self._index: Optional[VectorStoreIndex] = None
        self._pipeline: Optional[IngestionPipeline] = None
        self._is_setup = False

    async def setup(self) -> None:
        """初始化服务"""
        if self._is_setup:
            return

        # 配置全局设置
        Settings.embed_model = OpenAIEmbedding(
            model=self.embedding_model,
            api_key=os.getenv("OPENAI_API_KEY"),
            api_base=os.getenv("LLM_API_URL"),
        )
        Settings.llm = OpenAI(
            model=self.llm_model,
            api_key=os.getenv("LLM_API_KEY"),
            api_base=os.getenv("LLM_API_URL"),
        )

        # 初始化向量存储
        self._vector_store = PGVectorStore.from_params(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DB", "quant"),
            user=os.getenv("POSTGRES_USER", "quant"),
            password=os.getenv("DB_PASSWORD", "quant123"),
            table_name=self.table_name,
            embed_dim=self.embedding_dim,
        )

        # 初始化摄取流水线
        self._pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                ),
                Settings.embed_model,
            ],
            vector_store=self._vector_store,
        )

        # 初始化索引
        self._index = VectorStoreIndex.from_vector_store(
            vector_store=self._vector_store,
        )

        self._is_setup = True
        logger.info("LlamaIndex RAG Service initialized")

    async def ingest_document(
        self,
        file_path: str,
        report_id: int,
        report_uuid: str,
        report_title: str = "",
    ) -> List[TextNode]:
        """
        摄取文档

        Args:
            file_path: PDF 文件路径
            report_id: 研报 ID
            report_uuid: 研报 UUID
            report_title: 研报标题

        Returns:
            创建的节点列表
        """
        await self.setup()

        from llama_index.readers.file import PDFReader

        # 加载文档
        reader = PDFReader()
        documents = reader.load_data(file_path)

        # 添加业务元数据
        for doc in documents:
            doc.metadata.update({
                "report_id": report_id,
                "report_uuid": report_uuid,
                "report_title": report_title,
            })

        # 运行摄取流水线
        nodes = await self._pipeline.arun(documents=documents)

        logger.info(f"Ingested {len(nodes)} nodes from {file_path}")
        return nodes

    async def ingest_text(
        self,
        content: str,
        report_id: int,
        report_uuid: str,
        report_title: str = "",
        page_start: Optional[int] = None,
        section_title: str = "",
        chunk_type: str = "text",
    ) -> List[TextNode]:
        """
        摄取文本内容（用于已解析的 Markdown）

        Args:
            content: 文本内容
            report_id: 研报 ID
            report_uuid: 研报 UUID
            report_title: 研报标题
            page_start: 起始页
            section_title: 章节标题
            chunk_type: 切块类型

        Returns:
            创建的节点列表
        """
        await self.setup()

        from llama_index.core import Document

        # 创建文档
        doc = Document(
            text=content,
            metadata={
                "report_id": report_id,
                "report_uuid": report_uuid,
                "report_title": report_title,
                "page_start": page_start,
                "section_title": section_title,
                "chunk_type": chunk_type,
            },
        )

        # 运行摄取流水线
        nodes = await self._pipeline.arun(documents=[doc])

        logger.info(f"Ingested {len(nodes)} nodes from text content")
        return nodes

    async def search(
        self,
        query: str,
        top_k: int = 10,
        report_id: Optional[int] = None,
        report_uuid: Optional[str] = None,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        语义检索

        Args:
            query: 查询文本
            top_k: 返回数量
            report_id: 限定研报 ID
            report_uuid: 限定研报 UUID
            min_score: 最小相似度分数

        Returns:
            检索结果列表
        """
        await self.setup()

        # 构建过滤器
        filters = self._build_filters(report_id, report_uuid)

        # 构建后处理器
        postprocessors = []
        if min_score > 0:
            postprocessors.append(SimilarityPostprocessor(similarity_cutoff=min_score))

        # 获取检索器
        retriever = self._index.as_retriever(
            similarity_top_k=top_k,
            filters=filters,
            node_postprocessors=postprocessors,
        )

        # 执行检索
        nodes = await retriever.aretrieve(query)

        # 转换结果
        results = []
        for node in nodes:
            results.append({
                "chunk_id": node.node.node_id,
                "content": node.node.text,
                "score": node.score or 0.0,
                "report_id": node.node.metadata.get("report_id"),
                "report_uuid": node.node.metadata.get("report_uuid"),
                "report_title": node.node.metadata.get("report_title", ""),
                "page_start": node.node.metadata.get("page_start"),
                "section_title": node.node.metadata.get("section_title", ""),
            })

        logger.info(f"Search completed: query='{query[:50]}...', found {len(results)} results")
        return results

    async def ask(
        self,
        question: str,
        top_k: int = 5,
        report_id: Optional[int] = None,
        report_uuid: Optional[str] = None,
        rerank: bool = True,
    ) -> Dict[str, Any]:
        """
        RAG 问答

        Args:
            question: 用户问题
            top_k: 检索的切块数量
            report_id: 限定研报 ID
            report_uuid: 限定研报 UUID
            rerank: 是否使用重排

        Returns:
            问答结果
        """
        await self.setup()

        # 构建过滤器
        filters = self._build_filters(report_id, report_uuid)

        # 构建后处理器
        postprocessors = [
            SimilarityPostprocessor(similarity_cutoff=0.3),
        ]

        # 添加重排器（如果可用）
        if rerank:
            cohere_key = os.getenv("COHERE_API_KEY")
            if cohere_key:
                try:
                    from llama_index.postprocessor.cohere_rerank import CohereRerank
                    postprocessors.append(CohereRerank(
                        api_key=cohere_key,
                        top_n=top_k,
                    ))
                except ImportError:
                    logger.warning("CohereRerank not available, skipping rerank")

        # 创建查询引擎
        query_engine = self._index.as_query_engine(
            similarity_top_k=top_k * 4 if rerank else top_k,
            filters=filters,
            node_postprocessors=postprocessors,
            text_qa_template=QA_PROMPT,
        )

        # 执行查询
        response = await query_engine.aquery(question)

        # 构建来源引用
        sources = []
        if response.source_nodes:
            for i, node in enumerate(response.source_nodes[:top_k], 1):
                sources.append({
                    "index": i,
                    "chunk_id": node.node.node_id,
                    "content": node.node.text[:200] + "..." if len(node.node.text) > 200 else node.node.text,
                    "score": node.score or 0.0,
                    "report_uuid": node.node.metadata.get("report_uuid"),
                    "report_title": node.node.metadata.get("report_title", ""),
                    "page_number": node.node.metadata.get("page_start"),
                })

        return {
            "answer": str(response),
            "sources": sources,
            "retrieved_chunks": len(response.source_nodes) if response.source_nodes else 0,
        }

    async def get_similar_chunks(
        self,
        chunk_id: str,
        top_k: int = 5,
        exclude_same_report: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        获取相似切块

        Args:
            chunk_id: 参考切块 ID
            top_k: 返回数量
            exclude_same_report: 是否排除同一研报

        Returns:
            相似切块列表
        """
        await self.setup()

        # 获取参考节点
        # 注意：LlamaIndex 的 PGVectorStore 不直接支持按 ID 获取
        # 这里通过查询实现
        try:
            # 使用节点 ID 作为查询
            retriever = self._index.as_retriever(
                similarity_top_k=1,
                filters=MetadataFilters(filters=[
                    MetadataFilter(key="node_id", value=chunk_id),
                ]),
            )
            ref_nodes = await retriever.aretrieve(chunk_id)
            if not ref_nodes:
                return []

            ref_node = ref_nodes[0]
            ref_text = ref_node.node.text
            ref_report_id = ref_node.node.metadata.get("report_uuid")

        except Exception:
            # 如果无法获取参考节点，返回空
            logger.warning(f"Could not find reference chunk: {chunk_id}")
            return []

        # 构建后处理器
        postprocessors = []
        if exclude_same_report and ref_report_id:
            postprocessors.append(ExcludeSameReportPostProcessor(
                exclude_report_id=ref_report_id,
            ))

        # 搜索相似切块
        retriever = self._index.as_retriever(
            similarity_top_k=top_k + 5,  # 多取一些用于过滤
            node_postprocessors=postprocessors,
        )

        nodes = await retriever.aretrieve(ref_text)

        # 转换结果（排除自身）
        results = []
        for node in nodes:
            if node.node.node_id == chunk_id:
                continue

            results.append({
                "chunk_id": node.node.node_id,
                "content": node.node.text,
                "score": node.score or 0.0,
                "report_uuid": node.node.metadata.get("report_uuid"),
                "report_title": node.node.metadata.get("report_title", ""),
            })

            if len(results) >= top_k:
                break

        return results

    async def delete_by_report(self, report_uuid: str) -> int:
        """
        删除研报的所有切块

        Args:
            report_uuid: 研报 UUID

        Returns:
            删除的数量
        """
        await self.setup()

        # LlamaIndex PGVectorStore 支持按条件删除
        # 需要直接操作底层数据库
        try:
            # 使用 vector_store 的 delete 方法
            self._vector_store.delete(
                filters=MetadataFilters(filters=[
                    MetadataFilter(key="report_uuid", value=report_uuid),
                ]),
            )
            logger.info(f"Deleted chunks for report {report_uuid}")
            return 1  # 无法获取精确数量
        except Exception as e:
            logger.error(f"Failed to delete chunks: {e}")
            return 0

    def _build_filters(
        self,
        report_id: Optional[int] = None,
        report_uuid: Optional[str] = None,
    ) -> Optional[MetadataFilters]:
        """构建元数据过滤器"""
        filter_list = []

        if report_id is not None:
            filter_list.append(MetadataFilter(
                key="report_id",
                value=report_id,
                operator=FilterOperator.EQ,
            ))

        if report_uuid:
            filter_list.append(MetadataFilter(
                key="report_uuid",
                value=report_uuid,
                operator=FilterOperator.EQ,
            ))

        if filter_list:
            return MetadataFilters(filters=filter_list)
        return None


# =============================================================================
# 单例管理
# =============================================================================


_llamaindex_rag_service: Optional[LlamaIndexRAGService] = None


def get_llamaindex_rag_service(**kwargs) -> LlamaIndexRAGService:
    """获取 LlamaIndex RAG 服务单例"""
    global _llamaindex_rag_service
    if _llamaindex_rag_service is None:
        _llamaindex_rag_service = LlamaIndexRAGService(**kwargs)
    return _llamaindex_rag_service


async def get_initialized_rag_service(**kwargs) -> LlamaIndexRAGService:
    """获取已初始化的 RAG 服务"""
    service = get_llamaindex_rag_service(**kwargs)
    await service.setup()
    return service
