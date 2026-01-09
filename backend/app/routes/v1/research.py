"""
Research Hub API 端点

提供研报管理功能的 REST API。
研报知识库的核心职责：解析、切块、向量化、索引。
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from domains.research_hub.services import (
    ReportService,
    get_report_service,
    RetrievalService,
    get_retrieval_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Schema ====================


class ReportUploadResponse(BaseModel):
    """研报上传响应"""
    id: int
    uuid: str
    title: str
    filename: str
    status: str


class ReportDetailResponse(BaseModel):
    """研报详情响应"""
    id: int
    uuid: str
    title: str
    filename: str
    file_size: int
    page_count: int
    author: str
    source_url: str
    category: str
    tags: str
    status: str
    progress: int
    error_message: str
    created_at: Optional[str]
    parsed_at: Optional[str]
    indexed_at: Optional[str]


class ReportListResponse(BaseModel):
    """研报列表响应"""
    items: List[ReportDetailResponse]
    total: int
    page: int
    page_size: int


class ProcessingStatusResponse(BaseModel):
    """处理状态响应"""
    id: int
    status: str
    progress: int
    error_message: Optional[str]
    chunk_count: int
    parsed_at: Optional[str]
    indexed_at: Optional[str]


class ScanUploadRequest(BaseModel):
    """扫描上传请求"""
    directory: str
    pattern: str = "*.pdf"
    recursive: bool = True
    auto_process: bool = False
    pipeline: Optional[str] = None


class ScanUploadResponse(BaseModel):
    """扫描上传响应"""
    uploaded: int
    reports: List[ReportUploadResponse]


# ==================== 研报管理 API ====================


@router.post("/reports", response_model=ReportUploadResponse)
async def upload_report(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    source_url: Optional[str] = Form(None),
):
    """
    上传研报

    接受 PDF 文件，创建研报记录。
    上传后需要调用 /reports/{id}/process 进行处理。
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    service = get_report_service()
    content = await file.read()

    try:
        report = await service.upload(
            file_content=content,
            filename=file.filename,
            title=title,
            author=author,
            source_url=source_url,
        )

        return ReportUploadResponse(
            id=report.id,
            uuid=report.uuid,
            title=report.title,
            filename=report.filename,
            status=report.status,
        )
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(500, f"Upload failed: {str(e)}")


@router.post("/reports/{report_id}/process")
async def process_report(
    report_id: int,
    pipeline: Optional[str] = Query(None, description="Pipeline name to use"),
):
    """
    处理研报

    执行 PDF 解析、切块、嵌入、索引流程。
    这是一个异步操作，可通过 /reports/{id}/status 查询进度。
    """
    service = get_report_service()

    # 检查研报是否存在
    report = await service.get_report(report_id)
    if not report:
        raise HTTPException(404, "Report not found")

    # 启动处理（后台任务）
    import asyncio
    asyncio.create_task(service.process(report_id, pipeline_name=pipeline))

    return {"message": "Processing started", "report_id": report_id}


@router.get("/reports", response_model=ReportListResponse)
async def list_reports(
    search: Optional[str] = Query(None, description="Search in title and summary"),
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """列出研报"""
    service = get_report_service()
    offset = (page - 1) * page_size

    reports, total = await service.list_reports(
        search=search,
        status=status,
        category=category,
        limit=page_size,
        offset=offset,
    )

    return ReportListResponse(
        items=[
            ReportDetailResponse(
                id=r.id,
                uuid=r.uuid,
                title=r.title,
                filename=r.filename,
                file_size=r.file_size,
                page_count=r.page_count,
                author=r.author,
                source_url=r.source_url,
                category=r.category,
                tags=r.tags,
                status=r.status,
                progress=r.progress,
                error_message=r.error_message,
                created_at=r.created_at.isoformat() if r.created_at else None,
                parsed_at=r.parsed_at.isoformat() if r.parsed_at else None,
                indexed_at=r.indexed_at.isoformat() if r.indexed_at else None,
            )
            for r in reports
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/reports/{report_id}", response_model=ReportDetailResponse)
async def get_report(report_id: int):
    """获取研报详情"""
    service = get_report_service()
    report = await service.get_report(report_id)

    if not report:
        raise HTTPException(404, "Report not found")

    return ReportDetailResponse(
        id=report.id,
        uuid=report.uuid,
        title=report.title,
        filename=report.filename,
        file_size=report.file_size,
        page_count=report.page_count,
        author=report.author,
        source_url=report.source_url,
        category=report.category,
        tags=report.tags,
        status=report.status,
        progress=report.progress,
        error_message=report.error_message,
        created_at=report.created_at.isoformat() if report.created_at else None,
        parsed_at=report.parsed_at.isoformat() if report.parsed_at else None,
        indexed_at=report.indexed_at.isoformat() if report.indexed_at else None,
    )


@router.get("/reports/{report_id}/status", response_model=ProcessingStatusResponse)
async def get_report_status(report_id: int):
    """获取研报处理状态"""
    service = get_report_service()
    status = await service.get_processing_status(report_id)

    if "error" in status:
        raise HTTPException(404, status["error"])

    return ProcessingStatusResponse(**status)


@router.get("/reports/{report_id}/pdf")
async def get_report_pdf(report_id: int):
    """
    获取研报 PDF 文件

    返回原始 PDF 文件，用于前端预览。
    """
    service = get_report_service()
    report = await service.get_report(report_id)

    if not report:
        raise HTTPException(404, "Report not found")

    file_path = Path(report.file_path)
    if not file_path.exists():
        raise HTTPException(404, "PDF file not found")

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=report.filename,
    )


@router.delete("/reports/{report_id}")
async def delete_report(report_id: int):
    """删除研报"""
    service = get_report_service()
    success = await service.delete_report(report_id)

    if not success:
        raise HTTPException(404, "Report not found")

    return {"message": "Report deleted", "report_id": report_id}


@router.post("/reports/scan", response_model=ScanUploadResponse)
async def scan_and_upload(request: ScanUploadRequest):
    """
    扫描目录并批量上传研报

    从指定目录扫描 PDF 文件并上传到系统。
    适用于批量导入大量研报。

    示例:
        POST /research/reports/scan
        {
            "directory": "/path/to/reports",
            "pattern": "*.pdf",
            "recursive": true,
            "auto_process": false
        }
    """
    service = get_report_service()

    try:
        reports = await service.scan_and_upload(
            directory=request.directory,
            pattern=request.pattern,
            recursive=request.recursive,
            auto_process=request.auto_process,
            pipeline_name=request.pipeline,
        )

        return ScanUploadResponse(
            uploaded=len(reports),
            reports=[
                ReportUploadResponse(
                    id=r.id,
                    uuid=r.uuid,
                    title=r.title,
                    filename=r.filename,
                    status=r.status,
                )
                for r in reports
            ],
        )
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Scan upload failed: {e}")
        raise HTTPException(500, f"Scan upload failed: {str(e)}")


# ==================== 语义搜索 API ====================


class SearchRequest(BaseModel):
    """语义搜索请求"""
    query: str
    top_k: int = 10
    report_id: Optional[int] = None
    min_score: float = 0.0


class SearchResultItem(BaseModel):
    """搜索结果项"""
    chunk_id: str
    content: str
    score: float
    report_id: Optional[int]
    report_uuid: str
    report_title: str
    page_start: Optional[int]
    section_title: str


class SearchResponse(BaseModel):
    """搜索响应"""
    query: str
    count: int
    results: List[SearchResultItem]


class AskRequest(BaseModel):
    """RAG 问答请求"""
    question: str
    top_k: int = 5
    report_id: Optional[int] = None


class SourceItem(BaseModel):
    """来源项"""
    chunk_id: str
    content: str
    page_number: Optional[int]
    relevance: float
    report_uuid: str
    report_title: str


class AskResponse(BaseModel):
    """问答响应"""
    question: str
    answer: str
    sources: List[SourceItem]
    retrieved_chunks: int


@router.post("/search", response_model=SearchResponse)
async def search_reports(request: SearchRequest):
    """
    语义搜索研报内容

    使用向量相似度检索与查询语义相关的研报内容片段。
    """
    service = get_retrieval_service()

    try:
        results = await service.search(
            query=request.query,
            top_k=request.top_k,
            report_id=request.report_id,
            min_score=request.min_score,
        )

        return SearchResponse(
            query=request.query,
            count=len(results),
            results=[SearchResultItem(**r) for r in results],
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(500, f"Search failed: {str(e)}")


@router.post("/ask", response_model=AskResponse)
async def ask_reports(request: AskRequest):
    """
    基于研报知识库进行问答

    使用 RAG (检索增强生成) 技术，先检索相关研报内容，
    然后基于检索到的内容生成回答。
    """
    service = get_retrieval_service()

    try:
        result = await service.ask(
            question=request.question,
            top_k=request.top_k,
            report_id=request.report_id,
        )

        return AskResponse(
            question=request.question,
            answer=result["answer"],
            sources=[SourceItem(**s) for s in result["sources"]],
            retrieved_chunks=result["retrieved_chunks"],
        )
    except Exception as e:
        logger.error(f"Ask failed: {e}")
        raise HTTPException(500, f"Ask failed: {str(e)}")


# ==================== 切块 API ====================


class ChunkItem(BaseModel):
    """切块项"""
    chunk_id: str
    chunk_index: int
    chunk_type: str
    content: str
    token_count: int
    page_start: Optional[int]
    page_end: Optional[int]
    section_title: str


class ChunkListResponse(BaseModel):
    """切块列表响应"""
    report_id: int
    total: int
    page: int
    page_size: int
    chunks: List[ChunkItem]


class SimilarChunksRequest(BaseModel):
    """相似切块请求"""
    chunk_id: str
    top_k: int = 5
    exclude_same_report: bool = False


class SimilarChunkItem(BaseModel):
    """相似切块项"""
    chunk_id: str
    content: str
    score: float
    report_id: Optional[int]
    report_uuid: str
    report_title: str
    section_title: str


class SimilarChunksResponse(BaseModel):
    """相似切块响应"""
    reference_chunk_id: str
    count: int
    similar_chunks: List[SimilarChunkItem]


@router.get("/reports/{report_id}/chunks", response_model=ChunkListResponse)
async def get_report_chunks(
    report_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    获取研报的所有切块

    返回研报解析后的切块列表，包括内容、章节标题、页码等信息。
    """
    service = get_report_service()
    report = await service.get_report(report_id)

    if not report:
        raise HTTPException(404, "Report not found")

    if report.status not in ("chunked", "embedded", "indexing", "ready"):
        raise HTTPException(400, f"Report not chunked yet, current status: {report.status}")

    try:
        chunks, total = await service.get_report_chunks(
            report_id=report_id,
            limit=page_size,
            offset=(page - 1) * page_size,
        )

        return ChunkListResponse(
            report_id=report_id,
            total=total,
            page=page,
            page_size=page_size,
            chunks=[
                ChunkItem(
                    chunk_id=c.chunk_id,
                    chunk_index=c.chunk_index,
                    chunk_type=c.chunk_type,
                    content=c.content,
                    token_count=c.token_count,
                    page_start=c.page_start,
                    page_end=c.page_end,
                    section_title=c.section_title,
                )
                for c in chunks
            ],
        )
    except Exception as e:
        logger.error(f"Get chunks failed: {e}")
        raise HTTPException(500, f"Get chunks failed: {str(e)}")


@router.post("/chunks/similar", response_model=SimilarChunksResponse)
async def get_similar_chunks(request: SimilarChunksRequest):
    """
    获取相似切块

    根据指定切块，找到向量空间中最相似的其他切块。
    用于发现相关内容和扩展阅读。
    """
    service = get_retrieval_service()

    try:
        results = await service.get_similar_chunks(
            chunk_id=request.chunk_id,
            top_k=request.top_k,
            exclude_same_report=request.exclude_same_report,
        )

        return SimilarChunksResponse(
            reference_chunk_id=request.chunk_id,
            count=len(results),
            similar_chunks=[SimilarChunkItem(**r) for r in results],
        )
    except Exception as e:
        logger.error(f"Get similar chunks failed: {e}")
        raise HTTPException(500, f"Get similar chunks failed: {str(e)}")
