"""
任务管理 API 路由

提供回测任务单和执行记录的 CRUD 操作。

NOTE: 所有同步服务调用都使用 run_sync 包装，避免阻塞 event loop。
"""

import json
import math
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query

from app.schemas.common import ApiResponse
from app.schemas.task import (
    CreateTaskRequest,
    UpdateTaskRequest,
    DuplicateTaskRequest,
    TaskResponse,
    TaskListResponse,
    ExecuteTaskRequest,
    ExecutionResponse,
    ExecutionListResponse,
    ExecutionSubmitResponse,
    TaskStatsResponse,
    ExportToStrategyRequest,
    ExportToStrategyResponse,
)
from domains.strategy_hub.services.models import BacktestTask, TaskExecution
from domains.strategy_hub.services.task_store import get_task_store, BacktestTaskStore
from app.core.deps import get_backtest_runner
from app.core.async_utils import run_sync

router = APIRouter()


def get_store() -> BacktestTaskStore:
    """获取任务存储实例"""
    return get_task_store()


# =============================================================================
# 任务单 (BacktestTask) API
# =============================================================================


@router.post("", response_model=ApiResponse[TaskResponse])
async def create_task(
    request: CreateTaskRequest,
    store: BacktestTaskStore = Depends(get_store),
):
    """创建新任务单"""
    try:
        task = BacktestTask(
            name=request.name,
            description=request.description,
        )
        task.set_config(request.config.model_dump())
        if request.tags:
            task.set_tags(request.tags)
        if request.notes:
            task.notes = request.notes

        task = await run_sync(store.create_task, task)
        return ApiResponse(data=TaskResponse(**task.to_dict()))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=ApiResponse[TaskListResponse])
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    order_by: str = Query("created_at"),
    order_desc: bool = Query(True),
    store: BacktestTaskStore = Depends(get_store),
):
    """列出所有任务单"""
    try:
        tasks, total = await run_sync(
            store.list_tasks,
            page=page,
            page_size=page_size,
            search=search,
            order_by=order_by,
            order_desc=order_desc,
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return ApiResponse(
            data=TaskListResponse(
                items=[TaskResponse(**t.to_dict()) for t in tasks],
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}", response_model=ApiResponse[TaskResponse])
async def get_task(
    task_id: str,
    store: BacktestTaskStore = Depends(get_store),
):
    """获取任务单详情"""
    task = await run_sync(store.get_task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return ApiResponse(data=TaskResponse(**task.to_dict()))


@router.put("/{task_id}", response_model=ApiResponse[TaskResponse])
async def update_task(
    task_id: str,
    request: UpdateTaskRequest,
    store: BacktestTaskStore = Depends(get_store),
):
    """更新任务单"""
    task = await run_sync(store.get_task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    if request.name is not None:
        task.name = request.name
    if request.description is not None:
        task.description = request.description
    if request.config is not None:
        task.set_config(request.config.model_dump())
    if request.tags is not None:
        task.set_tags(request.tags)
    if request.notes is not None:
        task.notes = request.notes

    task = await run_sync(store.update_task, task)
    return ApiResponse(data=TaskResponse(**task.to_dict()))


@router.delete("/{task_id}", response_model=ApiResponse[None])
async def delete_task(
    task_id: str,
    store: BacktestTaskStore = Depends(get_store),
):
    """删除任务单（级联删除执行记录）"""
    success = await run_sync(store.delete_task, task_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return ApiResponse(data=None, message="删除成功")


@router.post("/{task_id}/duplicate", response_model=ApiResponse[TaskResponse])
async def duplicate_task(
    task_id: str,
    request: DuplicateTaskRequest,
    store: BacktestTaskStore = Depends(get_store),
):
    """复制任务单"""
    original = await run_sync(store.get_task, task_id)
    if not original:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    # 创建副本
    new_task = BacktestTask(
        name=request.new_name,
        description=original.description,
        config=original.config,
        tags=original.tags,
        notes=original.notes,
    )
    new_task = await run_sync(store.create_task, new_task)
    return ApiResponse(data=TaskResponse(**new_task.to_dict()))


# =============================================================================
# 任务执行 API
# =============================================================================


@router.post("/{task_id}/execute", response_model=ApiResponse[ExecutionSubmitResponse])
async def execute_task(
    task_id: str,
    request: ExecuteTaskRequest = None,
    store: BacktestTaskStore = Depends(get_store),
    runner=Depends(get_backtest_runner),
):
    """执行任务单"""
    task = await run_sync(store.get_task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    try:
        # 获取配置
        config = task.get_config()
        if request and request.config_override:
            config.update(request.config_override)

        # 创建执行记录
        execution = TaskExecution(
            task_id=task_id,
            status="pending",
            message="任务已提交",
        )

        # 从配置中提取因子信息
        strategy_list = config.get("strategy_list", [])
        if strategy_list:
            # 提取所有因子名称和参数
            factor_names = []
            factor_params = {}
            for stg in strategy_list:
                for factor in stg.get("factor_list", []):
                    name = factor.get("name", "")
                    if name and name not in factor_names:
                        factor_names.append(name)
                        factor_params[name] = factor.get("param", 0)

            execution.factor_list = json.dumps(factor_names, ensure_ascii=False)
            execution.factor_params = json.dumps(factor_params, ensure_ascii=False)

            # 从第一个策略获取配置快照
            first_stg = strategy_list[0]
            execution.hold_period = first_stg.get("hold_period", "1H")
            execution.long_select_coin_num = first_stg.get("long_select_coin_num", 5)
            execution.short_select_coin_num = first_stg.get("short_select_coin_num", 0)

        execution.start_date = config.get("start_date", "")
        execution.end_date = config.get("end_date", "")
        execution.leverage = config.get("leverage", 1.0)
        execution.account_type = config.get("account_type", "统一账户")
        execution.initial_usdt = config.get("initial_usdt", 10000)

        # 保存执行记录
        execution = await run_sync(store.create_execution, execution)

        # 增加任务执行次数
        await run_sync(store.increment_execution_count, task_id)

        # 提交回测任务
        from domains.strategy_hub.services.backtest_runner import (
            BacktestRequest as RunnerRequest,
        )
        from app.routes.v1.backtest import _convert_request_to_engine_format
        from app.schemas.backtest import BacktestRequest

        # 转换配置为 BacktestRequest
        backtest_request = BacktestRequest(**config)
        strategy_list_engine = _convert_request_to_engine_format(backtest_request)

        runner_request = RunnerRequest(
            name=config.get("name", task.name),
            strategy_list=strategy_list_engine,
            start_date=config.get("start_date", ""),
            end_date=config.get("end_date", ""),
            account_type=config.get("account_type", "统一账户"),
            initial_usdt=config.get("initial_usdt", 10000),
            leverage=config.get("leverage", 1.0),
            margin_rate=config.get("margin_rate", 0.05),
            swap_c_rate=config.get("swap_c_rate", 0.0006),
            spot_c_rate=config.get("spot_c_rate", 0.001),
            swap_min_order_limit=config.get("swap_min_order_limit", 5),
            spot_min_order_limit=config.get("spot_min_order_limit", 10),
            avg_price_col=config.get("avg_price_col", "avg_price_1m"),
            min_kline_num=config.get("min_kline_num", 0),
            black_list=config.get("black_list", []),
            white_list=config.get("white_list", []),
            execution_id=execution.id,  # 关联执行记录
        )

        runner_task_id = runner.submit(runner_request)

        return ApiResponse(
            data=ExecutionSubmitResponse(
                execution_id=execution.id,
                status="pending",
                message=f"任务已提交，runner_task_id: {runner_task_id}",
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}/executions", response_model=ApiResponse[ExecutionListResponse])
async def list_executions(
    task_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    store: BacktestTaskStore = Depends(get_store),
):
    """获取任务的所有执行记录"""
    # 检查任务是否存在
    task = await run_sync(store.get_task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    executions, total = await run_sync(
        store.list_executions,
        task_id=task_id,
        page=page,
        page_size=page_size,
        status=status,
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return ApiResponse(
        data=ExecutionListResponse(
            items=[ExecutionResponse(**e.to_dict()) for e in executions],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.get("/{task_id}/stats", response_model=ApiResponse[TaskStatsResponse])
async def get_task_stats(
    task_id: str,
    store: BacktestTaskStore = Depends(get_store),
):
    """获取任务的统计信息"""
    task = await run_sync(store.get_task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    stats = await run_sync(store.get_task_stats, task_id)
    return ApiResponse(data=TaskStatsResponse(**stats))


# =============================================================================
# 执行记录 API
# =============================================================================


@router.get("/executions/{execution_id}", response_model=ApiResponse[ExecutionResponse])
async def get_execution(
    execution_id: str,
    store: BacktestTaskStore = Depends(get_store),
):
    """获取执行记录详情"""
    execution = await run_sync(store.get_execution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail=f"执行记录不存在: {execution_id}")
    return ApiResponse(data=ExecutionResponse(**execution.to_dict()))


@router.delete(
    "/executions/{execution_id}", response_model=ApiResponse[None]
)
async def delete_execution(
    execution_id: str,
    store: BacktestTaskStore = Depends(get_store),
):
    """删除执行记录"""
    success = await run_sync(store.delete_execution, execution_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"执行记录不存在: {execution_id}")
    return ApiResponse(data=None, message="删除成功")


@router.post(
    "/executions/{execution_id}/export",
    response_model=ApiResponse[ExportToStrategyResponse],
)
async def export_to_strategy(
    execution_id: str,
    request: ExportToStrategyRequest,
    store: BacktestTaskStore = Depends(get_store),
):
    """导出执行结果到策略库"""
    execution = await run_sync(store.get_execution, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail=f"执行记录不存在: {execution_id}")

    if execution.status != "completed":
        raise HTTPException(status_code=400, detail="只能导出已完成的执行记录")

    try:
        from domains.strategy_hub.services import get_strategy_service
        from domains.strategy_hub.services.models import Strategy

        # 创建策略
        strategy = Strategy(
            name=request.strategy_name,
            description=request.description,
            factor_list=execution.factor_list,
            factor_params=execution.factor_params,
            start_date=execution.start_date,
            end_date=execution.end_date,
            leverage=execution.leverage,
            account_type=execution.account_type,
            initial_usdt=execution.initial_usdt,
            hold_period=execution.hold_period,
            long_select_coin_num=execution.long_select_coin_num,
            short_select_coin_num=execution.short_select_coin_num,
            cumulative_return=execution.cumulative_return,
            annual_return=execution.annual_return,
            max_drawdown=execution.max_drawdown,
            max_drawdown_start=execution.max_drawdown_start,
            max_drawdown_end=execution.max_drawdown_end,
            sharpe_ratio=execution.sharpe_ratio,
            recovery_rate=execution.recovery_rate,
            recovery_time=execution.recovery_time,
            win_periods=execution.win_periods,
            loss_periods=execution.loss_periods,
            win_rate=execution.win_rate,
            avg_return_per_period=execution.avg_return_per_period,
            profit_loss_ratio=execution.profit_loss_ratio,
            max_single_profit=execution.max_single_profit,
            max_single_loss=execution.max_single_loss,
            max_consecutive_wins=execution.max_consecutive_wins,
            max_consecutive_losses=execution.max_consecutive_losses,
            return_std=execution.return_std,
            year_return=execution.year_return,
            quarter_return=execution.quarter_return,
            month_return=execution.month_return,
            equity_curve=execution.equity_curve,
            task_status="completed",
        )

        service = get_strategy_service()
        strategy = await run_sync(service.create, strategy)

        # 更新执行记录的策略关联
        execution.strategy_id = strategy.id
        await run_sync(store.update_execution, execution)

        return ApiResponse(
            data=ExportToStrategyResponse(
                strategy_id=strategy.id,
                message="导出成功",
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
