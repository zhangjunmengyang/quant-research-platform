"""
Research Hub API 端点

提供研报管理和对话功能的 REST API。
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field

from domains.research_hub.services import (
    ChatBotService,
    ReportService,
    get_chatbot_service,
    get_report_service,
)
from domains.mcp_core.llm import get_llm_settings

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


class ConversationResponse(BaseModel):
    """对话响应"""
    id: int
    uuid: str
    title: str
    report_id: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]


class MessageResponse(BaseModel):
    """消息响应"""
    id: Optional[int]
    role: str
    content: str
    sources: Optional[str]
    created_at: Optional[str]


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    report_id: Optional[int] = None
    model_key: Optional[str] = None


class ChatResponse(BaseModel):
    """对话响应"""
    content: str
    sources: str
    metadata: Dict[str, Any]


class CreateConversationRequest(BaseModel):
    """创建对话请求"""
    title: Optional[str] = None
    report_id: Optional[int] = None


class LLMModelInfo(BaseModel):
    """LLM 模型信息"""
    key: str
    name: str
    model: str
    provider: str
    is_default: bool = False


class LLMModelsResponse(BaseModel):
    """LLM 模型列表响应"""
    models: List[LLMModelInfo]
    default_model: str


# ==================== LLM 配置 API ====================


@router.get("/llm/models", response_model=LLMModelsResponse)
async def get_llm_models():
    """
    获取可用的 LLM 模型列表

    从 config/llm_models.yaml 读取配置，返回可用模型列表。
    用于前端模型选择器展示。
    """
    settings = get_llm_settings()
    models = []

    for key, config in settings.models.items():
        models.append(
            LLMModelInfo(
                key=key,
                name=key.upper(),
                model=config.model,
                provider=config.provider,
                is_default=(key == settings.default_model),
            )
        )

    return LLMModelsResponse(
        models=models,
        default_model=settings.default_model,
    )


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


# ==================== 对话 API ====================


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(request: CreateConversationRequest):
    """创建新对话"""
    service = get_chatbot_service()
    conv = await service.create_conversation(
        title=request.title,
        report_id=request.report_id,
    )

    return ConversationResponse(
        id=conv.id,
        uuid=conv.uuid,
        title=conv.title,
        report_id=conv.report_id,
        created_at=conv.created_at.isoformat() if conv.created_at else None,
        updated_at=conv.updated_at.isoformat() if conv.updated_at else None,
    )


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """列出所有对话"""
    service = get_chatbot_service()
    conversations = await service.list_conversations(limit=limit, offset=offset)

    return [
        ConversationResponse(
            id=conv.id,
            uuid=conv.uuid,
            title=conv.title,
            report_id=conv.report_id,
            created_at=conv.created_at.isoformat() if conv.created_at else None,
            updated_at=conv.updated_at.isoformat() if conv.updated_at else None,
        )
        for conv in conversations
    ]


@router.get("/conversations/{conv_id}", response_model=ConversationResponse)
async def get_conversation(conv_id: int):
    """获取对话详情"""
    service = get_chatbot_service()
    conv = await service.get_conversation(conv_id)

    if not conv:
        raise HTTPException(404, "Conversation not found")

    return ConversationResponse(
        id=conv.id,
        uuid=conv.uuid,
        title=conv.title,
        report_id=conv.report_id,
        created_at=conv.created_at.isoformat() if conv.created_at else None,
        updated_at=conv.updated_at.isoformat() if conv.updated_at else None,
    )


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: int):
    """删除对话"""
    service = get_chatbot_service()
    success = await service.delete_conversation(conv_id)

    if not success:
        raise HTTPException(404, "Conversation not found")

    return {"message": "Conversation deleted", "conversation_id": conv_id}


@router.get("/conversations/{conv_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conv_id: int,
    limit: int = Query(100, ge=1, le=500),
):
    """获取对话消息"""
    service = get_chatbot_service()
    messages = await service.get_messages(conv_id, limit=limit)

    return [
        MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            sources=msg.sources,
            created_at=msg.created_at.isoformat() if msg.created_at else None,
        )
        for msg in messages
    ]


@router.post("/conversations/{conv_id}/chat", response_model=ChatResponse)
async def chat(conv_id: int, request: ChatRequest):
    """
    发送消息并获取回复

    这是同步 API，会等待完整回复后返回。
    对于流式响应，使用 /conversations/{conv_id}/chat/stream
    """
    service = get_chatbot_service()

    # 检查对话是否存在
    conv = await service.get_conversation(conv_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")

    try:
        response = await service.chat(
            conv_id=conv_id,
            message=request.message,
            report_id=request.report_id,
            model_key=request.model_key,
        )

        return ChatResponse(
            content=response["content"],
            sources=response["sources"],
            metadata=response["metadata"],
        )
    except Exception as e:
        logger.error(f"Chat failed: {e}", exc_info=True)
        raise HTTPException(500, f"Chat failed: {str(e)}")


@router.post("/conversations/{conv_id}/chat/stream")
async def chat_stream(conv_id: int, request: ChatRequest):
    """
    流式对话

    使用 Server-Sent Events (SSE) 返回增量响应。
    """
    service = get_chatbot_service()

    # 检查对话是否存在
    conv = await service.get_conversation(conv_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")

    async def generate():
        import json
        try:
            async for chunk in service.chat_stream(
                conv_id=conv_id,
                message=request.message,
                report_id=request.report_id,
                model_key=request.model_key,
            ):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
