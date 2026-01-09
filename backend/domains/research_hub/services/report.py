"""
研报管理服务

提供研报的上传、解析、索引等功能。
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from ..core.store import (
    get_research_store,
    get_chunk_store,
    ResearchStore,
    ChunkStore,
)
from ..core.models import (
    ResearchReport,
    ResearchChunk,
    ProcessingStatus,
)
from ..core.config import get_research_hub_settings, get_pipeline_config
from ..rag.base.parser import ParsedDocument
from ..rag.base.chunker import Chunk
from ..rag.base.registry import component_registries

logger = logging.getLogger(__name__)


class ReportService:
    """
    研报管理服务

    功能:
    - 上传研报
    - 解析 PDF
    - 切块和索引
    - 查询和管理

    处理流程:
    1. upload: 保存文件，创建记录，状态 = uploaded
    2. parse: 使用 MinerU 解析 PDF，状态 = parsing -> parsed
    3. chunk: 切分文档，状态 = chunking -> chunked
    4. embed: 生成嵌入，状态 = embedding -> embedded
    5. index: 写入向量库，状态 = indexing -> ready

    使用示例:
        service = ReportService()

        # 上传研报
        report = await service.upload(file_content, "report.pdf")

        # 处理研报（解析 + 切块 + 索引）
        await service.process(report.id)

        # 查询研报
        reports = await service.list_reports()
    """

    def __init__(
        self,
        upload_dir: Optional[str] = None,
        database_url: Optional[str] = None,
    ):
        settings = get_research_hub_settings()
        self.base_dir = Path(upload_dir or settings.upload_dir)

        # 创建目录结构
        self.uploads_dir = self.base_dir / "uploads"  # 原始 PDF
        self.parsed_dir = self.base_dir / "parsed"    # 解析结果
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.parsed_dir.mkdir(parents=True, exist_ok=True)

        # 兼容旧代码
        self.upload_dir = self.uploads_dir

        self.database_url = database_url
        self._research_store: Optional[ResearchStore] = None
        self._chunk_store: Optional[ChunkStore] = None

    @property
    def research_store(self) -> ResearchStore:
        if self._research_store is None:
            self._research_store = get_research_store(self.database_url)
        return self._research_store

    @property
    def chunk_store(self) -> ChunkStore:
        if self._chunk_store is None:
            self._chunk_store = get_chunk_store(self.database_url)
        return self._chunk_store

    # ==================== 上传 ====================

    async def upload(
        self,
        file_content: bytes,
        filename: str,
        title: Optional[str] = None,
        author: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> ResearchReport:
        """
        上传研报文件

        Args:
            file_content: 文件内容
            filename: 文件名
            title: 标题（可选，默认使用文件名）
            author: 作者
            source_url: 来源 URL

        Returns:
            创建的研报记录
        """
        import uuid as uuid_module

        # 生成 UUID，用于存储
        file_uuid = str(uuid_module.uuid4())
        file_ext = Path(filename).suffix.lower()

        # 使用 UUID 作为文件名存储，避免冲突
        stored_filename = f"{file_uuid}{file_ext}"
        file_path = self.uploads_dir / stored_filename
        file_path.write_bytes(file_content)

        # 创建记录
        report = ResearchReport(
            title=title or Path(filename).stem,
            filename=filename,  # 保留原始文件名
            file_path=str(file_path),
            file_size=len(file_content),
            author=author or "",
            source_url=source_url or "",
            status=ProcessingStatus.UPLOADED.value,
        )
        # 使用生成的 UUID
        report.uuid = file_uuid

        report_id = self.research_store.add(report)
        report.id = report_id

        logger.info(f"Uploaded report: {filename} -> {stored_filename}, id={report_id}")
        return report

    async def upload_from_path(
        self,
        file_path: str,
        title: Optional[str] = None,
        author: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> ResearchReport:
        """
        从本地路径上传研报

        Args:
            file_path: 本地文件路径
            title: 标题
            author: 作者
            source_url: 来源 URL

        Returns:
            创建的研报记录
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = path.read_bytes()
        return await self.upload(
            file_content=content,
            filename=path.name,
            title=title,
            author=author,
            source_url=source_url,
        )

    async def upload_batch(
        self,
        file_paths: List[str],
        auto_process: bool = False,
        pipeline_name: Optional[str] = None,
    ) -> List[ResearchReport]:
        """
        批量上传研报

        Args:
            file_paths: 文件路径列表
            auto_process: 是否自动处理
            pipeline_name: 使用的流水线

        Returns:
            创建的研报列表
        """
        reports = []
        for file_path in file_paths:
            try:
                report = await self.upload_from_path(file_path)
                reports.append(report)

                if auto_process:
                    # 启动后台处理
                    import asyncio
                    asyncio.create_task(self.process(report.id, pipeline_name))

            except Exception as e:
                logger.error(f"Failed to upload {file_path}: {e}")

        logger.info(f"Batch uploaded {len(reports)} reports")
        return reports

    async def scan_and_upload(
        self,
        directory: str,
        pattern: str = "*.pdf",
        recursive: bool = True,
        auto_process: bool = False,
        pipeline_name: Optional[str] = None,
    ) -> List[ResearchReport]:
        """
        扫描目录并上传所有 PDF

        Args:
            directory: 目录路径
            pattern: 文件匹配模式
            recursive: 是否递归扫描
            auto_process: 是否自动处理
            pipeline_name: 使用的流水线

        Returns:
            创建的研报列表
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        # 查找所有匹配的文件
        if recursive:
            files = list(dir_path.rglob(pattern))
        else:
            files = list(dir_path.glob(pattern))

        logger.info(f"Found {len(files)} files in {directory}")

        return await self.upload_batch(
            file_paths=[str(f) for f in files],
            auto_process=auto_process,
            pipeline_name=pipeline_name,
        )

    # ==================== 处理流程 ====================

    async def process(
        self,
        report_id: int,
        pipeline_name: Optional[str] = None,
    ) -> bool:
        """
        处理研报（完整流程）

        Args:
            report_id: 研报 ID
            pipeline_name: 使用的流水线配置

        Returns:
            是否成功
        """
        report = self.research_store.get(report_id)
        if not report:
            logger.error(f"Report not found: {report_id}")
            return False

        try:
            # 1. 解析
            await self._parse(report, pipeline_name)

            # 2. 切块
            await self._chunk(report, pipeline_name)

            # 3. 嵌入
            await self._embed(report, pipeline_name)

            # 4. 索引
            await self._index(report, pipeline_name)

            # 更新状态为 ready
            self.research_store.update_status(
                report_id,
                status=ProcessingStatus.READY.value,
                progress=100,
            )

            logger.info(f"Report {report_id} processed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to process report {report_id}: {e}", exc_info=True)
            self.research_store.update_status(
                report_id,
                status=ProcessingStatus.FAILED.value,
                error_message=str(e),
            )
            return False

    async def _parse(
        self,
        report: ResearchReport,
        pipeline_name: Optional[str] = None,
    ) -> ParsedDocument:
        """解析 PDF"""
        self.research_store.update_status(
            report.id,
            status=ProcessingStatus.PARSING.value,
            progress=10,
        )

        config = get_pipeline_config(pipeline_name)
        parser_cls = component_registries.parser.get(config.parser.type)
        parser = parser_cls(**config.parser.options)
        await parser.setup()

        parsed = await parser.parse(report.file_path)

        if not parsed.success:
            raise Exception(f"Parse failed: {parsed.error}")

        # 更新研报内容
        self.research_store.update(
            report.id,
            content_markdown=parsed.content,
            page_count=parsed.page_count or 0,
            parsed_at=datetime.now(),
        )

        self.research_store.update_status(
            report.id,
            status=ProcessingStatus.PARSED.value,
            progress=30,
        )

        return parsed

    async def _chunk(
        self,
        report: ResearchReport,
        pipeline_name: Optional[str] = None,
    ) -> List[Chunk]:
        """切分文档"""
        # 清理旧切块（重新处理时）
        deleted = self.chunk_store.delete_by_report(report.id)
        if deleted > 0:
            logger.info(f"Deleted {deleted} old chunks for report {report.id}")

        self.research_store.update_status(
            report.id,
            status=ProcessingStatus.CHUNKING.value,
            progress=40,
        )

        # 获取解析后的内容
        report = self.research_store.get(report.id)
        if not report.content_markdown:
            raise Exception("No parsed content available")

        config = get_pipeline_config(pipeline_name)
        chunker_cls = component_registries.chunker.get(config.chunker.type)
        chunker = chunker_cls(
            chunk_size=config.chunker.chunk_size,
            chunk_overlap=config.chunker.chunk_overlap,
            **config.chunker.options,
        )

        # 创建 ParsedDocument
        from ..rag.base.parser import ParsedDocument, ContentType
        parsed_doc = ParsedDocument(
            content=report.content_markdown,
            content_type=ContentType.MARKDOWN,
            source_path=report.file_path,
        )

        chunks = await chunker.chunk(parsed_doc)

        # 保存切块到数据库
        for i, chunk in enumerate(chunks):
            research_chunk = ResearchChunk(
                chunk_id=chunk.chunk_id,
                report_id=report.id,
                report_uuid=report.uuid,
                chunk_index=i,
                chunk_type=chunk.metadata.chunk_type.value if hasattr(chunk.metadata.chunk_type, 'value') else str(chunk.metadata.chunk_type),
                content=chunk.content,
                token_count=chunk.token_count or 0,
                heading_path=str(chunk.metadata.heading_path) if chunk.metadata.heading_path else "",
                section_title=chunk.metadata.section_title or "",
            )
            self.chunk_store.add(research_chunk)

        self.research_store.update_status(
            report.id,
            status=ProcessingStatus.CHUNKED.value,
            progress=50,
        )

        logger.info(f"Created {len(chunks)} chunks for report {report.id}")
        return chunks

    async def _embed(
        self,
        report: ResearchReport,
        pipeline_name: Optional[str] = None,
    ) -> None:
        """生成嵌入"""
        config = get_pipeline_config(pipeline_name)

        # 检查是否跳过嵌入
        if config.embedder.type == "none" or not config.embedder.type:
            logger.info(f"Skipping embedding for report {report.id} (embedder=none)")
            self.research_store.update_status(
                report.id,
                status=ProcessingStatus.INDEXED.value,
                progress=80,
            )
            return

        self.research_store.update_status(
            report.id,
            status=ProcessingStatus.EMBEDDING.value,
            progress=60,
        )

        embedder_cls = component_registries.embedder.get(config.embedder.type)
        embedder = embedder_cls(
            model_name=config.embedder.model,
            dimensions=config.embedder.dimensions,
            **config.embedder.options,
        )
        await embedder.setup()

        # 获取切块
        db_chunks = self.chunk_store.get_by_report(report.id)

        # 转换为 Chunk 对象并生成嵌入
        from ..rag.base.chunker import Chunk, ChunkMetadata

        chunks = []
        for db_chunk in db_chunks:
            chunk = Chunk(
                content=db_chunk.content,
                chunk_id=db_chunk.chunk_id,
                token_count=db_chunk.token_count,
                metadata=ChunkMetadata(
                    document_id=db_chunk.report_uuid,
                    chunk_index=db_chunk.chunk_index,
                ),
            )
            chunks.append(chunk)

        # 批量嵌入
        chunks = await embedder.embed_chunks(chunks)

        # 检查是否跳过向量存储
        vs_config = config.vector_store
        if vs_config.type == "none" or not vs_config.type:
            logger.info(f"Skipping vector store for report {report.id} (vector_store=none)")
        else:
            vs_cls = component_registries.vector_store.get(vs_config.type)
            vector_store = vs_cls(
                collection_name=vs_config.collection_name,
                dimensions=config.embedder.dimensions,
            )
            await vector_store.setup()
            await vector_store.upsert(chunks)

        self.research_store.update_status(
            report.id,
            status=ProcessingStatus.INDEXED.value,
            progress=80,
        )

        logger.info(f"Generated embeddings for {len(chunks)} chunks")

    async def _index(
        self,
        report: ResearchReport,
        pipeline_name: Optional[str] = None,
    ) -> None:
        """索引到向量库（嵌入阶段已完成）"""
        # 直接标记为已索引（嵌入阶段已完成向量存储）
        self.research_store.update_status(
            report.id,
            status=ProcessingStatus.INDEXED.value,
            progress=90,
        )

        # 更新索引时间
        self.research_store.update(
            report.id,
            indexed_at=datetime.now(),
        )

        logger.info(f"Indexed report {report.id}")

    # ==================== 查询 ====================

    async def list_reports(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[ResearchReport], int]:
        """列出研报"""
        return self.research_store.query(
            search=search,
            status=status,
            category=category,
            limit=limit,
            offset=offset,
        )

    async def get_report(self, report_id: int) -> Optional[ResearchReport]:
        """获取研报详情"""
        return self.research_store.get(report_id)

    async def delete_report(self, report_id: int) -> bool:
        """
        删除研报

        同时删除:
        - 文件
        - 数据库记录
        - 向量索引
        """
        report = self.research_store.get(report_id)
        if not report:
            return False

        # 删除文件
        if report.file_path and Path(report.file_path).exists():
            Path(report.file_path).unlink()

        # 删除切块（会级联删除）
        self.chunk_store.delete_by_report(report_id)

        # 删除向量索引
        config = get_pipeline_config()
        vs_config = config.vector_store
        vs_cls = component_registries.vector_store.get(vs_config.type)
        vector_store = vs_cls(collection_name=vs_config.collection_name)
        await vector_store.setup()
        await vector_store.delete(document_id=report.uuid)

        # 删除研报记录
        self.research_store.delete(report_id)

        logger.info(f"Deleted report {report_id}")
        return True

    async def get_report_chunks(
        self,
        report_id: int,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Tuple[List[ResearchChunk], int]:
        """获取研报的切块(支持分页)

        Args:
            report_id: 研报ID
            limit: 返回数量限制，None表示返回全部
            offset: 偏移量

        Returns:
            (切块列表, 总数)
        """
        return self.chunk_store.get_by_report(report_id, limit=limit, offset=offset)

    async def get_processing_status(
        self,
        report_id: int,
    ) -> Dict[str, Any]:
        """获取处理状态"""
        report = self.research_store.get(report_id)
        if not report:
            return {"error": "Report not found"}

        chunk_count = self.chunk_store.count_by_report(report_id)

        return {
            "id": report.id,
            "status": report.status,
            "progress": report.progress,
            "error_message": report.error_message,
            "chunk_count": chunk_count,
            "parsed_at": report.parsed_at.isoformat() if report.parsed_at else None,
            "indexed_at": report.indexed_at.isoformat() if report.indexed_at else None,
        }


# 单例管理
_report_service: Optional[ReportService] = None


def get_report_service(
    upload_dir: Optional[str] = None,
    database_url: Optional[str] = None,
) -> ReportService:
    """获取研报服务单例"""
    global _report_service
    if _report_service is None:
        _report_service = ReportService(
            upload_dir=upload_dir,
            database_url=database_url,
        )
    return _report_service
