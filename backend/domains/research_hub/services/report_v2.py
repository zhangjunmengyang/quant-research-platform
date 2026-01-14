"""
研报管理服务 (LlamaIndex 版本)

基于 LlamaIndex 的研报上传、解析、索引服务。
"""

import logging
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
from ..core.config import get_research_hub_settings
from .llamaindex_rag import get_llamaindex_rag_service, LlamaIndexRAGService

logger = logging.getLogger(__name__)


class ReportService:
    """
    研报管理服务

    功能:
    - 上传研报
    - 解析 PDF
    - 切块和索引（使用 LlamaIndex）
    - 查询和管理

    处理流程:
    1. upload: 保存文件，创建记录，状态 = uploaded
    2. process: 使用 LlamaIndex 完成解析、切块、嵌入、索引

    使用示例:
        service = ReportService()

        # 上传研报
        report = await service.upload(file_content, "report.pdf")

        # 处理研报
        await service.process(report.id)
    """

    def __init__(
        self,
        upload_dir: Optional[str] = None,
        database_url: Optional[str] = None,
    ):
        settings = get_research_hub_settings()
        self.base_dir = Path(upload_dir or settings.upload_dir)

        # 创建目录结构
        self.uploads_dir = self.base_dir / "uploads"
        self.parsed_dir = self.base_dir / "parsed"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.parsed_dir.mkdir(parents=True, exist_ok=True)

        # 兼容旧代码
        self.upload_dir = self.uploads_dir

        self.database_url = database_url
        self._research_store: Optional[ResearchStore] = None
        self._chunk_store: Optional[ChunkStore] = None
        self._rag_service: Optional[LlamaIndexRAGService] = None

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

    @property
    def rag_service(self) -> LlamaIndexRAGService:
        if self._rag_service is None:
            self._rag_service = get_llamaindex_rag_service()
        return self._rag_service

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

        # 使用 UUID 作为文件名存储
        stored_filename = f"{file_uuid}{file_ext}"
        file_path = self.uploads_dir / stored_filename
        file_path.write_bytes(file_content)

        # 创建记录
        report = ResearchReport(
            title=title or Path(filename).stem,
            filename=filename,
            file_path=str(file_path),
            file_size=len(file_content),
            author=author or "",
            source_url=source_url or "",
            status=ProcessingStatus.UPLOADED.value,
        )
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
        """从本地路径上传研报"""
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
        """批量上传研报"""
        reports = []
        for file_path in file_paths:
            try:
                report = await self.upload_from_path(file_path)
                reports.append(report)

                if auto_process:
                    import asyncio
                    asyncio.create_task(self.process(report.id))

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
        """扫描目录并上传所有 PDF"""
        dir_path = Path(directory)
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

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
        pipeline_name: Optional[str] = None,  # 保留兼容性
    ) -> bool:
        """
        处理研报（使用 LlamaIndex）

        Args:
            report_id: 研报 ID
            pipeline_name: 保留兼容性，LlamaIndex 版本不使用

        Returns:
            是否成功
        """
        report = self.research_store.get(report_id)
        if not report:
            logger.error(f"Report not found: {report_id}")
            return False

        try:
            # 更新状态为处理中
            self.research_store.update_status(
                report_id,
                status=ProcessingStatus.PARSING.value,
                progress=10,
            )

            # 使用 LlamaIndex 摄取文档
            # LlamaIndex 会自动完成: 解析 -> 切块 -> 嵌入 -> 索引
            nodes = await self.rag_service.ingest_document(
                file_path=report.file_path,
                report_id=report.id,
                report_uuid=report.uuid,
                report_title=report.title,
            )

            # 更新进度
            self.research_store.update_status(
                report_id,
                status=ProcessingStatus.CHUNKED.value,
                progress=50,
            )

            # 保存切块信息到业务数据库（用于查询和管理）
            for i, node in enumerate(nodes):
                chunk = ResearchChunk(
                    chunk_id=node.node_id if hasattr(node, 'node_id') else str(i),
                    report_id=report.id,
                    report_uuid=report.uuid,
                    chunk_index=i,
                    content=node.text if hasattr(node, 'text') else str(node),
                    token_count=len(node.text.split()) if hasattr(node, 'text') else 0,
                )
                self.chunk_store.add(chunk)

            # 更新状态为就绪
            self.research_store.update_status(
                report_id,
                status=ProcessingStatus.READY.value,
                progress=100,
            )

            self.research_store.update(
                report_id,
                indexed_at=datetime.now(),
            )

            logger.info(f"Report {report_id} processed with {len(nodes)} chunks")
            return True

        except Exception as e:
            logger.error(f"Failed to process report {report_id}: {e}", exc_info=True)
            self.research_store.update_status(
                report_id,
                status=ProcessingStatus.FAILED.value,
                error_message=str(e),
            )
            return False

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

        # 删除切块记录
        self.chunk_store.delete_by_report(report_id)

        # 删除向量索引
        await self.rag_service.delete_by_report(report.uuid)

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
        """获取研报的切块"""
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
