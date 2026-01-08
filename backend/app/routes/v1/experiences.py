"""Experience API routes.

提供经验知识库的 REST API 接口。

NOTE: 所有同步服务调用都使用 run_sync 包装，避免阻塞 event loop。
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.common import ApiResponse, PaginatedResponse, model_to_dict
from app.schemas.experience import (
    ExperienceResponse,
    ExperienceContentSchema,
    ExperienceContextSchema,
    ExperienceCreateRequest,
    ExperienceUpdateRequest,
    ExperienceQueryRequest,
    ExperienceValidateRequest,
    ExperienceValidateResponse,
    ExperienceDeprecateRequest,
    ExperienceDeprecateResponse,
    ExperienceLinkRequest,
    ExperienceLinkResponse,
    ExperienceLinkSchema,
    ExperienceCurateRequest,
    ExperienceCurateResponse,
    ExperienceStatsResponse,
    ExperienceLevelEnum,
    ExperienceStatusEnum,
    SourceTypeEnum,
)
from app.core.deps import get_experience_or_404, get_experience_service
from app.core.async_utils import run_sync

logger = logging.getLogger(__name__)

router = APIRouter()


def _experience_to_response(exp) -> ExperienceResponse:
    """将经验对象转换为响应 Schema"""
    exp_dict = model_to_dict(exp)

    # 处理嵌套对象
    content = exp_dict.get("content", {})
    if isinstance(content, dict):
        exp_dict["content"] = ExperienceContentSchema(**content)
    elif hasattr(content, "to_dict"):
        exp_dict["content"] = ExperienceContentSchema(**content.to_dict())

    context = exp_dict.get("context", {})
    if isinstance(context, dict):
        exp_dict["context"] = ExperienceContextSchema(**context)
    elif hasattr(context, "to_dict"):
        exp_dict["context"] = ExperienceContextSchema(**context.to_dict())

    return ExperienceResponse(**exp_dict)


@router.post("", response_model=ApiResponse[ExperienceResponse])
async def create_experience(
    request: ExperienceCreateRequest,
    service=Depends(get_experience_service),
):
    """
    创建新经验

    存储结构化的研究经验，基于 PARL 框架（Problem-Approach-Result-Lesson）。
    """
    # 构建内容和上下文字典
    content_dict = request.content.model_dump() if request.content else {}
    context_dict = request.context.model_dump() if request.context else None

    success, message, experience_id = await run_sync(
        service.store_experience,
        title=request.title,
        experience_level=request.experience_level.value,
        category=request.category,
        content=content_dict,
        context=context_dict,
        source_type=request.source_type.value,
        source_ref=request.source_ref,
        confidence=request.confidence,
    )

    if not success or experience_id is None:
        raise HTTPException(status_code=400, detail=message)

    experience = await run_sync(service.get_experience, experience_id)
    return ApiResponse(data=_experience_to_response(experience), message="创建成功")


@router.get("", response_model=ApiResponse[PaginatedResponse[ExperienceResponse]])
async def list_experiences(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    experience_level: Optional[ExperienceLevelEnum] = None,
    category: Optional[str] = None,
    status: Optional[ExperienceStatusEnum] = None,
    source_type: Optional[SourceTypeEnum] = None,
    market_regime: Optional[str] = None,
    factor_styles: Optional[str] = None,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    include_deprecated: bool = False,
    order_by: str = "updated_at",
    order_desc: bool = True,
    service=Depends(get_experience_service),
):
    """
    获取经验列表

    支持分页、筛选和排序。
    """
    # 解析因子风格
    factor_styles_list = None
    if factor_styles:
        factor_styles_list = [s.strip() for s in factor_styles.split(',') if s.strip()]

    experiences, total = await run_sync(
        service.list_experiences,
        experience_level=experience_level.value if experience_level else "",
        category=category or "",
        status=status.value if status else "",
        source_type=source_type.value if source_type else "",
        market_regime=market_regime or "",
        factor_styles=factor_styles_list,
        min_confidence=min_confidence,
        include_deprecated=include_deprecated,
        order_by=order_by,
        order_desc=order_desc,
        page=page,
        page_size=page_size,
    )

    items = [_experience_to_response(exp) for exp in experiences]

    return ApiResponse(
        data=PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/stats", response_model=ApiResponse[ExperienceStatsResponse])
async def get_stats(service=Depends(get_experience_service)):
    """获取经验统计信息"""
    stats = await run_sync(service.get_stats)

    return ApiResponse(
        data=ExperienceStatsResponse(
            total=stats.get("total", 0),
            by_status=stats.get("by_status", {}),
            by_level=stats.get("by_level", {}),
            categories=stats.get("categories", []),
            categories_count=stats.get("categories_count", 0),
        )
    )


@router.post("/query", response_model=ApiResponse[List[ExperienceResponse]])
async def query_experiences(
    request: ExperienceQueryRequest,
    service=Depends(get_experience_service),
):
    """
    语义查询经验

    使用自然语言查询相关经验，优先使用向量检索。
    """
    # 解析因子风格
    factor_styles_list = request.factor_styles if request.factor_styles else None

    experiences = await run_sync(
        service.query_experiences,
        query=request.query,
        experience_level=request.experience_level.value if request.experience_level else None,
        category=request.category,
        market_regime=request.market_regime,
        factor_styles=factor_styles_list,
        min_confidence=request.min_confidence,
        include_deprecated=request.include_deprecated,
        top_k=request.top_k,
    )

    items = [_experience_to_response(exp) for exp in experiences]
    return ApiResponse(data=items)


@router.post("/curate", response_model=ApiResponse[ExperienceCurateResponse])
async def curate_experience(
    request: ExperienceCurateRequest,
    service=Depends(get_experience_service),
):
    """
    从低层经验提炼高层经验

    从多个 operational 经验总结为一个 tactical 结论，
    或从多个 tactical 结论抽象为一个 strategic 原则。
    """
    content_dict = request.content.model_dump() if request.content else {}
    context_dict = request.context.model_dump() if request.context else None

    success, message, experience_id = await run_sync(
        service.curate_experience,
        source_experience_ids=request.source_experience_ids,
        target_level=request.target_level.value,
        title=request.title,
        content=content_dict,
        context=context_dict,
    )

    if not success or experience_id is None:
        raise HTTPException(status_code=400, detail=message)

    return ApiResponse(
        data=ExperienceCurateResponse(
            experience_id=experience_id,
            message=message,
        ),
        message="提炼成功",
    )


@router.get("/{experience_id}", response_model=ApiResponse[ExperienceResponse])
async def get_experience(experience=Depends(get_experience_or_404)):
    """获取经验详情"""
    return ApiResponse(data=_experience_to_response(experience))


@router.patch("/{experience_id}", response_model=ApiResponse[ExperienceResponse])
async def update_experience(
    update: ExperienceUpdateRequest,
    experience=Depends(get_experience_or_404),
    service=Depends(get_experience_service),
):
    """更新经验字段"""
    update_fields = update.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    # 处理嵌套对象
    if "content" in update_fields and update_fields["content"]:
        update_fields["content"] = update_fields["content"]
    if "context" in update_fields and update_fields["context"]:
        update_fields["context"] = update_fields["context"]
    if "experience_level" in update_fields and update_fields["experience_level"]:
        update_fields["experience_level"] = update_fields["experience_level"].value

    experience_id = experience.id
    success = await run_sync(service.update_experience, experience_id, **update_fields)
    if not success:
        raise HTTPException(status_code=500, detail="更新失败")

    updated = await run_sync(service.get_experience, experience_id)
    return ApiResponse(data=_experience_to_response(updated), message="更新成功")


@router.delete("/{experience_id}", response_model=ApiResponse[None])
async def delete_experience(
    experience=Depends(get_experience_or_404),
    service=Depends(get_experience_service),
):
    """删除经验"""
    success = await run_sync(service.delete_experience, experience.id)
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")

    return ApiResponse(message="删除成功")


@router.post("/{experience_id}/validate", response_model=ApiResponse[ExperienceValidateResponse])
async def validate_experience(
    request: ExperienceValidateRequest = None,
    experience=Depends(get_experience_or_404),
    service=Depends(get_experience_service),
):
    """
    验证/增强经验

    当后续研究证实了某条经验时调用，会增加验证次数和置信度。
    """
    validation_note = request.validation_note if request else None
    confidence_delta = request.confidence_delta if request else None

    success, message, result = await run_sync(
        service.validate_experience,
        experience_id=experience.id,
        validation_note=validation_note,
        confidence_delta=confidence_delta,
    )

    if not success or result is None:
        raise HTTPException(status_code=400, detail=message)

    return ApiResponse(
        data=ExperienceValidateResponse(
            experience_id=result["experience_id"],
            new_confidence=result["new_confidence"],
            validation_count=result["validation_count"],
        ),
        message="验证成功",
    )


@router.post("/{experience_id}/deprecate", response_model=ApiResponse[ExperienceDeprecateResponse])
async def deprecate_experience(
    request: ExperienceDeprecateRequest,
    experience=Depends(get_experience_or_404),
    service=Depends(get_experience_service),
):
    """
    废弃经验

    当经验被证伪或已过时时调用，保留历史记录但降低检索权重。
    """
    success, message, result = await run_sync(
        service.deprecate_experience,
        experience_id=experience.id,
        reason=request.reason,
    )

    if not success or result is None:
        raise HTTPException(status_code=400, detail=message)

    return ApiResponse(
        data=ExperienceDeprecateResponse(
            experience_id=result["experience_id"],
            status=result["status"],
        ),
        message="废弃成功",
    )


@router.post("/{experience_id}/link", response_model=ApiResponse[ExperienceLinkResponse])
async def link_experience(
    request: ExperienceLinkRequest,
    experience=Depends(get_experience_or_404),
    service=Depends(get_experience_service),
):
    """
    关联经验与其他实体

    建立经验与因子、策略、笔记、研报的关联关系。
    """
    success, message, result = await run_sync(
        service.link_experience,
        experience_id=experience.id,
        entity_type=request.entity_type.value,
        entity_id=request.entity_id,
        relation=request.relation,
    )

    if not success or result is None:
        raise HTTPException(status_code=400, detail=message)

    return ApiResponse(
        data=ExperienceLinkResponse(
            link_id=result["link_id"],
            experience_id=result["experience_id"],
            entity_type=result["entity_type"],
            entity_id=result["entity_id"],
        ),
        message="关联成功",
    )


@router.get("/{experience_id}/links", response_model=ApiResponse[List[ExperienceLinkSchema]])
async def get_experience_links(
    experience=Depends(get_experience_or_404),
    service=Depends(get_experience_service),
):
    """获取经验的所有关联"""
    links = await run_sync(service.get_experience_links, experience.id)
    items = [ExperienceLinkSchema(**model_to_dict(link)) for link in links]
    return ApiResponse(data=items)
