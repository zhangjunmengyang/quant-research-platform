"""Factor Pipeline API routes.

Provides REST API endpoints for factor data cleaning pipeline operations:
- discover: Find new factors not yet in database
- ingest: Import discovered factors with field filling
- fill: Fill specific fields using LLM
- review: Review and validate factors using LLM
- status: Get pipeline statistics

NOTE: 所有同步服务调用都使用 run_sync 包装，避免阻塞 event loop。
"""

import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from app.schemas.common import ApiResponse
from app.core.deps import get_factor_store, get_field_filler
from app.core.async_utils import run_sync
from domains.mcp_core.server.sse import get_task_manager, TaskStatus

router = APIRouter()


# ==================== Schemas ====================


class PipelineStatus(BaseModel):
    """Pipeline status statistics."""

    total: int = Field(description="Total factors in database")
    scored: int = Field(description="Factors with LLM score")
    unscored: int = Field(description="Factors without LLM score")
    verified: int = Field(description="Verified factors")
    pending: int = Field(description="Pending factors to ingest")
    score_distribution: Dict[str, int] = Field(default_factory=dict)
    style_distribution: Dict[str, int] = Field(default_factory=dict)
    field_coverage: Dict[str, Dict[str, int]] = Field(default_factory=dict)


class DiscoverResult(BaseModel):
    """Result of discover operation."""

    cataloged: List[str] = Field(description="Already in database")
    pending: List[str] = Field(description="New factors to ingest")
    excluded: List[str] = Field(description="Excluded factors")
    missing_files: List[str] = Field(description="In database but file missing")
    pending_time_series: List[str] = Field(default_factory=list, description="Pending time series factors")
    pending_cross_section: List[str] = Field(default_factory=list, description="Pending cross section factors")


class FillableField(str, Enum):
    """Fields that can be filled by LLM."""

    style = "style"
    tags = "tags"
    formula = "formula"
    input_data = "input_data"
    value_range = "value_range"
    description = "description"
    analysis = "analysis"
    llm_score = "llm_score"


class FillMode(str, Enum):
    """Fill mode for field filling."""

    incremental = "incremental"  # Only fill empty values
    full = "full"  # Refill all values


class FillRequest(BaseModel):
    """Request to fill fields.

    统一的填充接口：
    - factors: 指定因子列表（调用方负责筛选）
    - fields: 要填充的字段列表
    - mode: incremental 只填空值，full 全量覆盖
    - preview: 预览模式，生成内容但不保存到数据库（用于编辑面板）
    - concurrency: 并发数（同时进行的 LLM 请求数）
    - delay: 每个请求之间的间隔时间
    """

    factors: Optional[List[str]] = Field(
        default=None,
        description="Factor filenames to fill. None means all factors."
    )
    fields: List[FillableField] = Field(description="Fields to fill")
    mode: FillMode = Field(default=FillMode.incremental)
    concurrency: int = Field(default=1, ge=1, le=10, description="Number of concurrent LLM calls")
    delay: float = Field(default=15.0, ge=0, le=120, description="Delay between each request in seconds")
    dry_run: bool = Field(default=False, description="Count only, no LLM calls")
    preview: bool = Field(default=False, description="Generate but don't save to database")


class FillProgress(BaseModel):
    """Progress of fill operation."""

    field: str
    total: int
    processed: int
    success: int
    failed: int
    status: str  # pending, running, completed, failed


class IngestRequest(BaseModel):
    """Request to ingest factors."""

    factors: Optional[List[str]] = Field(
        default=None, description="Specific factors to ingest, or None for all pending"
    )
    fill_fields: bool = Field(
        default=True, description="Whether to fill fields after ingest"
    )
    dry_run: bool = Field(default=False)


class IngestResult(BaseModel):
    """Result of ingest operation."""

    total: int
    ingested: int
    skipped: int
    failed: int
    factors: List[str]


class ReviewRequest(BaseModel):
    """Request to review factors."""

    factors: Optional[List[str]] = Field(
        default=None, description="Specific factors to review"
    )
    fields: List[str] = Field(
        default=["style", "formula"], description="Fields to review"
    )
    filter_verified: Optional[bool] = Field(default=None)
    filter_score_min: Optional[float] = Field(default=None)
    filter_score_max: Optional[float] = Field(default=None)
    concurrency: int = Field(default=1, ge=1, le=10, description="Number of concurrent LLM calls")
    delay: float = Field(default=15.0, ge=0, le=120, description="Delay between each LLM call in seconds")
    dry_run: bool = Field(default=False)


class ReviewResult(BaseModel):
    """Result of review operation."""

    total: int
    reviewed: int
    revised: int
    details: List[Dict[str, Any]] = Field(default_factory=list)


class ModelConfig(BaseModel):
    """Model configuration for a prompt."""

    name: str = Field(default="", description="Model key from llm_configs (e.g. claude/gpt/gemini)")
    temperature: float = Field(default=0.3, ge=0, le=2, description="Temperature (0-2)")
    max_tokens: int = Field(default=500, ge=1, le=65536, description="Max output tokens")


class PromptConfig(BaseModel):
    """Single field prompt configuration."""

    field: str = Field(description="Field name")
    description: str = Field(description="Field description")
    system: str = Field(description="System prompt template")
    user: str = Field(description="User prompt template")
    output_format: str = Field(default="text", description="Output format: text, number, json")
    max_length: int = Field(default=500, description="Max output length (deprecated, use model.max_tokens)")
    model: ModelConfig = Field(default_factory=ModelConfig, description="Model configuration")


class ModelConfigUpdate(BaseModel):
    """Request to update model configuration."""

    name: Optional[str] = Field(default=None, description="Model key from llm_configs")
    temperature: Optional[float] = Field(default=None, ge=0, le=2, description="Temperature")
    max_tokens: Optional[int] = Field(default=None, ge=1, le=65536, description="Max tokens")


class PromptConfigUpdate(BaseModel):
    """Request to update a prompt configuration."""

    system: Optional[str] = Field(default=None, description="New system prompt")
    user: Optional[str] = Field(default=None, description="New user prompt")
    description: Optional[str] = Field(default=None, description="New description")
    output_format: Optional[str] = Field(default=None, description="New output format")
    max_length: Optional[int] = Field(default=None, description="New max length (deprecated)")
    model: Optional[ModelConfigUpdate] = Field(default=None, description="Model configuration")


# ==================== Task State ====================

# Simple in-memory task tracking with TTL and max size to prevent memory leaks
# For production, use Redis/DB instead
from collections import OrderedDict
import time

_MAX_TASK_STATES = 1000  # 最多保存 1000 个任务状态
_TASK_STATE_TTL = 3600  # 任务状态保留 1 小时

# 使用 OrderedDict 以便按插入顺序删除旧条目
_task_state: OrderedDict[str, Dict[str, Any]] = OrderedDict()


def _cleanup_old_states():
    """清理过期的任务状态"""
    current_time = time.time()
    # 清理过期条目
    expired_keys = [
        k for k, v in _task_state.items()
        if current_time - v.get('_created_at', 0) > _TASK_STATE_TTL
    ]
    for k in expired_keys:
        _task_state.pop(k, None)

    # 如果仍然超过最大数量，删除最旧的条目
    while len(_task_state) > _MAX_TASK_STATES:
        _task_state.popitem(last=False)


def get_task_state(task_id: str) -> Optional[Dict[str, Any]]:
    state = _task_state.get(task_id)
    if state:
        # 检查是否过期
        if time.time() - state.get('_created_at', 0) > _TASK_STATE_TTL:
            _task_state.pop(task_id, None)
            return None
    return state


def set_task_state(task_id: str, state: Dict[str, Any]):
    # 添加创建时间戳
    state['_created_at'] = time.time()
    _task_state[task_id] = state
    # 每次设置时清理旧状态
    _cleanup_old_states()


# ==================== Endpoints ====================


@router.get("/status", response_model=ApiResponse[PipelineStatus])
async def get_pipeline_status(store=Depends(get_factor_store)):
    """Get pipeline status and statistics."""
    try:
        stats = await run_sync(store.get_stats)

        # Calculate field coverage
        all_factors = await run_sync(store.get_all)
        field_coverage = {}
        fields_to_check = [
            "style",
            "tags",
            "formula",
            "input_data",
            "value_range",
            "description",
            "analysis",
            "llm_score",
        ]

        for field in fields_to_check:
            filled = sum(
                1 for f in all_factors if getattr(f, field, None) not in [None, "", 0]
            )
            field_coverage[field] = {"filled": filled, "empty": len(all_factors) - filled}

        # Get pending count from discover
        from domains.factor_hub.tasks.diff_catalog import discover_factors

        discover_result = await run_sync(discover_factors)
        pending_count = len(discover_result.pending)

        return ApiResponse(
            data=PipelineStatus(
                total=stats.get("total", 0),
                scored=stats.get("scored", 0),
                unscored=stats.get("unscored", 0),
                verified=stats.get("verified", 0),
                pending=pending_count,
                score_distribution=stats.get("score_distribution", {}),
                style_distribution=stats.get("style_distribution", {}),
                field_coverage=field_coverage,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discover", response_model=ApiResponse[DiscoverResult])
async def discover_factors_endpoint(store=Depends(get_factor_store)):
    """Discover new factors not yet in database."""
    try:
        from domains.factor_hub.tasks.diff_catalog import discover_factors

        result = await run_sync(discover_factors)

        return ApiResponse(
            data=DiscoverResult(
                cataloged=list(result.cataloged),
                pending=list(result.pending),
                excluded=list(result.excluded),
                missing_files=list(result.missing_files),
                pending_time_series=list(result.pending_time_series),
                pending_cross_section=list(result.pending_cross_section),
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest", response_model=ApiResponse[IngestResult])
async def ingest_factors(
    request: IngestRequest,
    store=Depends(get_factor_store),
):
    """Ingest new factors into database."""
    try:
        from domains.factor_hub.tasks.diff_catalog import discover_factors
        from domains.factor_hub.core.models import Factor, FactorType

        # Get factors to ingest with type info
        discover_result = await run_sync(discover_factors)

        if request.factors:
            factors_to_ingest = request.factors
        else:
            factors_to_ingest = list(discover_result.pending)

        # Build type mapping from discover result
        time_series_set = discover_result.pending_time_series
        cross_section_set = discover_result.pending_cross_section

        if request.dry_run:
            return ApiResponse(
                data=IngestResult(
                    total=len(factors_to_ingest),
                    ingested=0,
                    skipped=0,
                    failed=0,
                    factors=factors_to_ingest,
                ),
                message="Dry run - no changes made",
            )

        ingested = []
        skipped = []
        failed = []

        # Get factor directories
        base_path = Path(__file__).parent.parent.parent.parent.parent
        factors_dir = base_path / "factors"
        sections_dir = base_path / "sections"

        for filename in factors_to_ingest:
            try:
                # Check if already exists
                existing = await run_sync(store.get, filename)
                if existing:
                    skipped.append(filename)
                    continue

                # Determine factor type and find the code file
                if filename in time_series_set:
                    factor_type = FactorType.TIME_SERIES
                    code_path = factors_dir / f"{filename}.py"
                elif filename in cross_section_set:
                    factor_type = FactorType.CROSS_SECTION
                    code_path = sections_dir / f"{filename}.py"
                else:
                    # Fallback: check both directories
                    code_path = factors_dir / f"{filename}.py"
                    if code_path.exists():
                        factor_type = FactorType.TIME_SERIES
                    else:
                        code_path = sections_dir / f"{filename}.py"
                        if code_path.exists():
                            factor_type = FactorType.CROSS_SECTION
                        else:
                            failed.append(filename)
                            continue

                if not code_path.exists():
                    failed.append(filename)
                    continue

                # Create factor record with type
                factor = Factor(
                    filename=filename,
                    code_path=str(code_path),
                    factor_type=factor_type,
                )

                # Save to database
                success = await run_sync(store.add, factor)
                if success:
                    ingested.append(filename)
                else:
                    failed.append(filename)

            except Exception:
                failed.append(filename)

        # Note: fill_fields is not implemented here, user should call /fill after ingest

        return ApiResponse(
            data=IngestResult(
                total=len(factors_to_ingest),
                ingested=len(ingested),
                skipped=len(skipped),
                failed=len(failed),
                factors=ingested,
            ),
            message=f"Ingested {len(ingested)} factors",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fields", response_model=ApiResponse[List[str]])
async def get_fillable_fields(filler=Depends(get_field_filler)):
    """Get list of fields that can be filled by LLM."""
    try:
        fields = await run_sync(filler.get_fillable_fields)
        return ApiResponse(data=fields)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fill", response_model=ApiResponse[Dict[str, Any]])
async def fill_fields(
    request: FillRequest,
    store=Depends(get_factor_store),
    filler=Depends(get_field_filler),
):
    """Fill specified fields using LLM.

    统一填充接口：
    - 传入 factors 列表时，只填充指定因子
    - 不传 factors 时，填充所有因子
    - 非 dry_run/preview 模式下，返回 task_id，通过 SSE 订阅进度
    """
    import traceback
    try:
        # 获取因子：指定列表或全部
        # 注意：空列表 [] 也是 falsy，所以要用 is not None 判断
        if request.factors is not None:
            # 按文件名列表获取
            all_factors = await run_sync(store.get_all)
            factors = [f for f in all_factors if f.filename in request.factors]
            # 保持请求顺序
            factor_order = {name: i for i, name in enumerate(request.factors)}
            factors.sort(key=lambda f: factor_order.get(f.filename, 999))
        else:
            factors = await run_sync(store.get_all)

        if not factors:
            return ApiResponse(
                data={"total_factors": 0, "fields": [], "message": "No factors found"},
                message="No factors to fill",
            )

        fields_to_fill = [f.value for f in request.fields]

        if request.dry_run:
            # Count how many would be filled
            counts = {}
            for field in fields_to_fill:
                if request.mode == FillMode.incremental:
                    empty_count = sum(
                        1
                        for f in factors
                        if getattr(f, field, None) in [None, "", 0]
                    )
                    counts[field] = empty_count
                else:
                    counts[field] = len(factors)

            return ApiResponse(
                data={
                    "dry_run": True,
                    "total_factors": len(factors),
                    "factors": [f.filename for f in factors],
                    "fields": fields_to_fill,
                    "to_fill": counts,
                },
                message="Dry run - no changes made",
            )

        # preview 模式：同步执行，返回生成的值
        if request.preview:
            result = await filler.fill_fields_async(
                factors=factors,
                fields=fields_to_fill,
                mode=request.mode.value,
                concurrency=request.concurrency,
                delay=request.delay,
                save_to_store=False,
            )

            # 转换结果为可序列化格式
            serialized_result = {}
            generated_values: Dict[str, Dict[str, str]] = {}

            for field, field_result in result.items():
                serialized_result[field] = {
                    "field": field_result.field,
                    "success_count": field_result.success_count,
                    "fail_count": field_result.fail_count,
                    "results": [
                        {
                            "filename": r.filename,
                            "field": r.field,
                            "old_value": r.old_value,
                            "new_value": r.new_value,
                            "success": r.success,
                            "error": r.error,
                        }
                        for r in field_result.results
                    ],
                }
                for r in field_result.results:
                    if r.success and r.new_value:
                        if r.filename not in generated_values:
                            generated_values[r.filename] = {}
                        generated_values[r.filename][r.field] = r.new_value

            return ApiResponse(
                data={
                    "total_factors": len(factors),
                    "factors": [f.filename for f in factors],
                    "fields": fields_to_fill,
                    "result": serialized_result,
                    "preview": True,
                    "generated": generated_values,
                },
                message="Preview completed",
            )

        # 非 preview 模式：异步执行，返回 task_id
        manager = get_task_manager()
        task_id = manager.create_task()

        # 计算待填充数量
        to_fill_counts = {}
        for field in fields_to_fill:
            if request.mode == FillMode.incremental:
                empty_count = sum(
                    1 for f in factors if getattr(f, field, None) in [None, "", 0]
                )
                to_fill_counts[field] = empty_count
            else:
                to_fill_counts[field] = len(factors)

        total_to_fill = sum(to_fill_counts.values())

        # 后台执行填充任务
        asyncio.create_task(_execute_fill_task(
            task_id=task_id,
            factors=factors,
            fields=fields_to_fill,
            mode=request.mode.value,
            concurrency=request.concurrency,
            delay=request.delay,
            filler=filler,
            total_to_fill=total_to_fill,
        ))

        return ApiResponse(
            data={
                "task_id": task_id,
                "status": "pending",
                "total_factors": len(factors),
                "fields": fields_to_fill,
                "to_fill": to_fill_counts,
            },
            message="Fill task submitted",
        )

    except Exception as e:
        print(f"Fill API error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


async def _execute_fill_task(
    task_id: str,
    factors: List,
    fields: List[str],
    mode: str,
    concurrency: int,
    delay: float,
    filler,
    total_to_fill: int,
):
    """后台执行填充任务，推送实时进度"""
    manager = get_task_manager()

    try:
        # 标记任务开始
        manager.start_task(task_id)
        await manager.update_progress(
            task_id,
            status=TaskStatus.RUNNING,
            progress=0,
            message="开始填充...",
            total_steps=total_to_fill,
            current_step_num=0,
        )

        # 执行填充（带进度回调）
        result = await filler.fill_fields_async(
            factors=factors,
            fields=fields,
            mode=mode,
            concurrency=concurrency,
            delay=delay,
            save_to_store=True,
            task_id=task_id,  # 传递 task_id 用于进度推送
        )

        # 汇总结果
        total_success = sum(r.success_count for r in result.values())
        total_fail = sum(r.fail_count for r in result.values())

        # 标记任务完成
        await manager.complete_task(
            task_id,
            data={
                "type": "completed",
                "success_count": total_success,
                "fail_count": total_fail,
                "fields": fields,
            },
        )

    except Exception as e:
        await manager.fail_task(task_id, str(e))


@router.get("/fill/active")
async def get_active_fill_task():
    """获取当前活跃的填充任务（running 或 pending 状态）"""
    manager = get_task_manager()
    tasks = manager.list_tasks()

    # 找到最近的 running 或 pending 任务
    for task in sorted(tasks, key=lambda t: t.created_at, reverse=True):
        if task.status in (TaskStatus.RUNNING, TaskStatus.PENDING):
            return ApiResponse(data=task.to_dict())

    return ApiResponse(data=None, message="No active fill task")


@router.get("/fill/{task_id}/progress")
async def fill_progress(task_id: str):
    """SSE 端点：订阅填充任务进度"""
    manager = get_task_manager()

    async def event_generator():
        async for event in manager.subscribe(task_id):
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/review", response_model=ApiResponse[ReviewResult])
async def review_factors(
    request: ReviewRequest,
    store=Depends(get_factor_store),
):
    """Review factors using LLM for quality validation."""
    try:
        from domains.factor_hub.tasks.review import run_review

        # Build filter condition
        filter_condition = {}
        if request.filter_verified is not None:
            filter_condition["verified"] = 1 if request.filter_verified else 0

        # 支持范围过滤：同时指定 min 和 max 时使用列表形式
        score_filters = []
        if request.filter_score_min is not None:
            score_filters.append(f">={request.filter_score_min}")
        if request.filter_score_max is not None:
            score_filters.append(f"<={request.filter_score_max}")
        if score_filters:
            filter_condition["llm_score"] = score_filters if len(score_filters) > 1 else score_filters[0]

        if request.dry_run:
            factors = await run_sync(
                store.query,
                filter_condition=filter_condition if filter_condition else None
            )
            if request.factors:
                factors = [f for f in factors if f.filename in request.factors]

            return ApiResponse(
                data=ReviewResult(
                    total=len(factors),
                    reviewed=0,
                    revised=0,
                    details=[],
                ),
                message=f"Dry run - would review {len(factors)} factors",
            )

        # Run review (run_review 内部有 LLM 调用，使用 run_sync 包装)
        summary = await run_sync(
            run_review,
            filter_condition=filter_condition if filter_condition else None,
            review_fields=request.fields,
            concurrency=request.concurrency,
            delay=request.delay,
            dry_run=request.dry_run,
            apply_revisions=True,
        )

        # 使用 ReviewSummary 结果
        return ApiResponse(
            data=ReviewResult(
                total=summary.success_count + summary.fail_count,
                reviewed=summary.success_count,
                revised=summary.revision_count,
                details=[],
            ),
            message="Review completed",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Variables Endpoint ====================


class PromptVariable(BaseModel):
    """A variable available for use in prompts."""

    name: str = Field(description="Variable name")
    desc: str = Field(description="Variable description")
    type: str = Field(default="str", description="Variable type (str, float, int, etc.)")


def _get_factor_variables() -> List[PromptVariable]:
    """Get all available variables from Factor model.

    返回 Factor 模型的所有字段，这些字段可用于 Prompt 模板中。
    每次 LLM 请求只处理单个因子，所以变量都是单因子字段。
    """
    # Factor 模型字段及其描述
    # 与 backend/domains/factor_hub/core/models.py 中的 Factor 类保持同步
    variables = [
        # 基础信息
        PromptVariable(name="filename", desc="因子文件名", type="str"),
        PromptVariable(name="factor_type", desc="因子类型 (time_series/cross_section)", type="str"),
        PromptVariable(name="uuid", desc="因子唯一标识符", type="str"),
        PromptVariable(name="code", desc="因子代码内容 (从 code_content 读取)", type="str"),
        PromptVariable(name="code_path", desc="代码文件路径", type="str"),
        # LLM 生成字段
        PromptVariable(name="style", desc="因子风格分类", type="str"),
        PromptVariable(name="formula", desc="核心公式", type="str"),
        PromptVariable(name="input_data", desc="输入数据字段", type="str"),
        PromptVariable(name="value_range", desc="值域范围", type="str"),
        PromptVariable(name="description", desc="因子描述", type="str"),
        PromptVariable(name="analysis", desc="因子详细分析", type="str"),
        PromptVariable(name="tags", desc="因子标签 (逗号分隔)", type="str"),
        PromptVariable(name="llm_score", desc="LLM评分 (0-5)", type="float"),
        # 回测指标
        PromptVariable(name="ic", desc="IC值", type="float"),
        PromptVariable(name="rank_ic", desc="RankIC值", type="float"),
        PromptVariable(name="backtest_sharpe", desc="回测夏普比率", type="float"),
        PromptVariable(name="backtest_ic", desc="回测IC均值", type="float"),
        PromptVariable(name="backtest_ir", desc="回测IR", type="float"),
        PromptVariable(name="turnover", desc="换手率", type="float"),
        PromptVariable(name="decay", desc="IC半衰期 (周期数)", type="int"),
        # 验证状态
        PromptVariable(name="verified", desc="是否已验证 (0/1)", type="int"),
        PromptVariable(name="verify_note", desc="验证备注", type="str"),
        # 分类标签
        PromptVariable(name="market_regime", desc="适用市场环境 (牛市/熊市/震荡)", type="str"),
        PromptVariable(name="best_holding_period", desc="最佳持仓周期 (小时)", type="int"),
        # 代码质量
        PromptVariable(name="code_complexity", desc="代码复杂度评分", type="float"),
        PromptVariable(name="last_backtest_date", desc="最后回测日期", type="str"),
        # 排除状态
        PromptVariable(name="excluded", desc="是否被排除 (0/1)", type="int"),
        PromptVariable(name="exclude_reason", desc="排除原因", type="str"),
        # 时间戳
        PromptVariable(name="created_at", desc="创建时间", type="datetime"),
        PromptVariable(name="updated_at", desc="更新时间", type="datetime"),
    ]
    return variables


@router.get("/variables", response_model=ApiResponse[List[PromptVariable]])
async def get_prompt_variables():
    """Get all available variables for prompt templates.

    返回可用于 Prompt 模板的所有变量列表。
    这些变量与 Factor 模型字段对应，每次 LLM 请求处理单个因子。
    """
    try:
        variables = _get_factor_variables()
        return ApiResponse(data=variables)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== LLM Models Endpoint ====================


class LLMModelInfo(BaseModel):
    """Information about an available LLM model."""

    key: str = Field(description="Model key for reference in prompts")
    provider: str = Field(default="openai", description="API provider type")
    model: str = Field(description="Actual model identifier")
    temperature: float = Field(description="Default temperature")
    max_tokens: int = Field(description="Default max tokens")


class LLMModelsResponse(BaseModel):
    """Response containing available LLM models."""

    models: List[LLMModelInfo] = Field(description="List of available models")
    default: str = Field(description="Default model key")


def _load_llm_models() -> Dict[str, Any]:
    """Load llm_models.yaml configuration."""
    import yaml
    config_dir = Path(__file__).parent.parent.parent.parent.parent / "config"
    llm_models_path = config_dir / "llm_models.yaml"
    if not llm_models_path.exists():
        return {}
    with open(llm_models_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


@router.get("/models", response_model=ApiResponse[LLMModelsResponse])
async def get_available_models():
    """Get available LLM models for prompt configuration.

    返回 llm_models.yaml 中配置的 llm_configs 模型列表。
    第一个模型为默认模型。
    """
    try:
        llm_models = _load_llm_models()
        llm_configs = llm_models.get('llm_configs', {})

        models = []
        for key, config in llm_configs.items():
            if isinstance(config, dict):
                models.append(LLMModelInfo(
                    key=key,
                    provider=config.get('provider', 'openai'),
                    model=config.get('model', key),
                    temperature=config.get('temperature', 0.6),
                    max_tokens=config.get('max_tokens', 8192),
                ))

        # 第一个模型为默认模型
        default_model = models[0].key if models else ''

        return ApiResponse(data=LLMModelsResponse(
            models=models,
            default=default_model,
        ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Prompt Config Endpoints ====================


def _get_prompts_dir() -> Path:
    """Get the prompts directory path."""
    return Path(__file__).parent.parent.parent.parent.parent / "config" / "prompts" / "fields"


def _load_prompt_yaml(field: str) -> Optional[Dict[str, Any]]:
    """Load a single prompt YAML file."""
    import yaml
    prompts_dir = _get_prompts_dir()
    yaml_path = prompts_dir / f"{field}.yaml"
    if not yaml_path.exists():
        return None
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def _save_prompt_yaml(field: str, config: Dict[str, Any]) -> bool:
    """Save a prompt configuration to YAML file.

    使用 literal block scalar (|) 保存多行字符串，保持可读性。
    """
    import yaml

    # 自定义 Dumper，对多行字符串使用 literal block style (|)
    class LiteralBlockDumper(yaml.SafeDumper):
        pass

    def str_representer(dumper, data):
        # 如果字符串包含换行符，使用 literal block style
        if '\n' in data:
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)

    LiteralBlockDumper.add_representer(str, str_representer)

    prompts_dir = _get_prompts_dir()
    yaml_path = prompts_dir / f"{field}.yaml"
    if not yaml_path.exists():
        return False
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, Dumper=LiteralBlockDumper, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return True


def _parse_model_config(config: Dict[str, Any]) -> ModelConfig:
    """Parse model configuration from YAML config."""
    model_data = config.get('model', {})
    if not isinstance(model_data, dict):
        model_data = {}
    return ModelConfig(
        name=model_data.get('name', ''),
        temperature=model_data.get('temperature', 0.3),
        max_tokens=model_data.get('max_tokens', 500),
    )


def _config_to_prompt_config(config: Dict[str, Any], field_name: str) -> PromptConfig:
    """Convert YAML config dict to PromptConfig model."""
    return PromptConfig(
        field=config.get('field', field_name),
        description=config.get('description', ''),
        system=config.get('system', ''),
        user=config.get('user', ''),
        output_format=config.get('output', {}).get('format', 'text') if isinstance(config.get('output'), dict) else 'text',
        max_length=config.get('output', {}).get('max_length', 500) if isinstance(config.get('output'), dict) else 500,
        model=_parse_model_config(config),
    )


@router.get("/prompts", response_model=ApiResponse[List[PromptConfig]])
async def get_all_prompts():
    """Get all prompt configurations."""
    try:
        prompts_dir = _get_prompts_dir()
        if not prompts_dir.exists():
            return ApiResponse(data=[], message="Prompts directory not found")

        configs = []
        for yaml_file in sorted(prompts_dir.glob("*.yaml")):
            config = _load_prompt_yaml(yaml_file.stem)
            if config:
                configs.append(_config_to_prompt_config(config, yaml_file.stem))

        return ApiResponse(data=configs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts/{field}", response_model=ApiResponse[PromptConfig])
async def get_prompt(field: str):
    """Get a single prompt configuration by field name."""
    try:
        config = _load_prompt_yaml(field)
        if not config:
            raise HTTPException(status_code=404, detail=f"Prompt config for field '{field}' not found")

        return ApiResponse(data=_config_to_prompt_config(config, field))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/prompts/{field}", response_model=ApiResponse[PromptConfig])
async def update_prompt(field: str, update: PromptConfigUpdate):
    """Update a prompt configuration.

    Only provided fields will be updated, others remain unchanged.
    """
    try:
        config = _load_prompt_yaml(field)
        if not config:
            raise HTTPException(status_code=404, detail=f"Prompt config for field '{field}' not found")

        # Update only provided fields
        if update.system is not None:
            config['system'] = update.system
        if update.user is not None:
            config['user'] = update.user
        if update.description is not None:
            config['description'] = update.description

        # Handle output sub-object
        if update.output_format is not None or update.max_length is not None:
            if 'output' not in config or not isinstance(config['output'], dict):
                config['output'] = {}
            if update.output_format is not None:
                config['output']['format'] = update.output_format
            if update.max_length is not None:
                config['output']['max_length'] = update.max_length

        # Handle model sub-object
        if update.model is not None:
            if 'model' not in config or not isinstance(config['model'], dict):
                config['model'] = {}
            if update.model.name is not None:
                config['model']['name'] = update.model.name
            if update.model.temperature is not None:
                config['model']['temperature'] = update.model.temperature
            if update.model.max_tokens is not None:
                config['model']['max_tokens'] = update.model.max_tokens

        # Save back to YAML
        if not _save_prompt_yaml(field, config):
            raise HTTPException(status_code=500, detail="Failed to save prompt config")

        # Reload field_filler to pick up changes
        from domains.factor_hub.services.field_filler import _field_filler
        if _field_filler is not None:
            _field_filler._load_field_configs()

        return ApiResponse(
            data=_config_to_prompt_config(config, field),
            message=f"Prompt config for '{field}' updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
