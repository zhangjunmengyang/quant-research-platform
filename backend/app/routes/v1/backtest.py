"""
回测 API 路由

完整暴露 strategy_hub/core 回测引擎的配置能力。

NOTE: 所有同步服务调用都使用 run_sync 包装，避免阻塞 event loop。
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException

from app.schemas.common import ApiResponse
from app.core.async_utils import run_sync
from app.schemas.backtest import (
    BacktestRequest,
    SimpleBacktestRequest,
    BacktestStatus,
    BacktestResult,
    BacktestMetrics,
    BacktestTemplate,
    BacktestConfigResponse,
    StrategyItem,
    FactorItem,
    BatchBacktestRequest,
    BatchBacktestStatus,
)
from app.core.deps import get_backtest_runner

router = APIRouter()


def _convert_request_to_engine_format(request: BacktestRequest) -> list:
    """将 API 请求转换为回测引擎期望的格式"""
    strategy_list = []

    for stg in request.strategy_list:
        # 构建因子列表: (factor_name, is_sort_asc, param, weight)
        factor_list = [
            (f.name, f.is_sort_asc, f.param, f.weight) for f in stg.factor_list
        ]

        # 多空分离因子
        long_factor_list = None
        short_factor_list = None
        if stg.long_factor_list:
            long_factor_list = [
                (f.name, f.is_sort_asc, f.param, f.weight) for f in stg.long_factor_list
            ]
        if stg.short_factor_list:
            short_factor_list = [
                (f.name, f.is_sort_asc, f.param, f.weight)
                for f in stg.short_factor_list
            ]

        # 构建过滤因子列表
        def build_filter_list(filters):
            result = []
            for f in filters:
                if f.method:
                    result.append((f.name, f.param, f.method, f.is_sort_asc))
                else:
                    result.append((f.name, f.param))
            return result

        filter_list = build_filter_list(stg.filter_list)
        long_filter_list = (
            build_filter_list(stg.long_filter_list) if stg.long_filter_list else None
        )
        short_filter_list = (
            build_filter_list(stg.short_filter_list) if stg.short_filter_list else None
        )
        filter_list_post = build_filter_list(stg.filter_list_post)

        stg_dict = {
            "strategy": stg.strategy,
            "hold_period": stg.hold_period,
            "offset": stg.offset,
            "market": stg.market,
            "long_select_coin_num": stg.long_select_coin_num,
            "short_select_coin_num": stg.short_select_coin_num,
            "long_cap_weight": stg.long_cap_weight,
            "short_cap_weight": stg.short_cap_weight,
            "cap_weight": stg.cap_weight,
            "factor_list": factor_list,
            "filter_list": filter_list,
            "filter_list_post": filter_list_post,
            "use_custom_func": stg.use_custom_func,
        }

        # 添加可选的偏移列表
        if stg.offset_list:
            stg_dict["offset_list"] = stg.offset_list

        # 添加多空分离因子
        if long_factor_list:
            stg_dict["long_factor_list"] = long_factor_list
        if short_factor_list:
            stg_dict["short_factor_list"] = short_factor_list
        if long_filter_list:
            stg_dict["long_filter_list"] = long_filter_list
        if short_filter_list:
            stg_dict["short_filter_list"] = short_filter_list

        strategy_list.append(stg_dict)

    return strategy_list


def _submit_single_backtest(request: BacktestRequest, runner) -> str:
    """提交单个回测任务，返回 task_id"""
    from domains.strategy_hub.services.backtest_runner import (
        BacktestRequest as RunnerRequest,
    )

    # 转换策略列表为引擎格式
    strategy_list = _convert_request_to_engine_format(request)

    runner_request = RunnerRequest(
        name=request.name,
        strategy_list=strategy_list,
        start_date=request.start_date,
        end_date=request.end_date,
        # 账户配置
        account_type=request.account_type,
        initial_usdt=request.initial_usdt,
        leverage=request.leverage,
        margin_rate=request.margin_rate,
        # 手续费
        swap_c_rate=request.swap_c_rate,
        spot_c_rate=request.spot_c_rate,
        # 最小下单量
        swap_min_order_limit=request.swap_min_order_limit,
        spot_min_order_limit=request.spot_min_order_limit,
        # 其他配置
        avg_price_col=request.avg_price_col,
        min_kline_num=request.min_kline_num,
        black_list=request.black_list,
        white_list=request.white_list,
    )

    return runner.submit(runner_request)


@router.post("/submit/batch", response_model=ApiResponse[BatchBacktestStatus])
async def submit_batch_backtest(
    request: BatchBacktestRequest,
    runner=Depends(get_backtest_runner),
):
    """批量提交回测任务

    支持一次提交多个回测任务，后端并行执行。
    单个回测是批量的特例（tasks 只包含一个元素）。
    """
    try:
        tasks_status = []
        for task_request in request.tasks:
            task_id = await run_sync(_submit_single_backtest, task_request, runner)
            tasks_status.append(
                BacktestStatus(
                    task_id=task_id,
                    status="pending",
                    progress=0.0,
                    message="回测任务已提交",
                )
            )

        return ApiResponse(
            data=BatchBacktestStatus(
                total=len(request.tasks),
                submitted=len(tasks_status),
                tasks=tasks_status,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit", response_model=ApiResponse[BacktestStatus])
async def submit_backtest(
    request: BacktestRequest,
    runner=Depends(get_backtest_runner),
):
    """提交完整回测任务

    接受完整的回测配置，支持多策略、多因子、多空分离等高级功能。
    这是批量提交的简化版本（单个任务）。
    """
    try:
        task_id = await run_sync(_submit_single_backtest, request, runner)

        return ApiResponse(
            data=BacktestStatus(
                task_id=task_id,
                status="pending",
                progress=0.0,
                message="回测任务已提交",
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit/simple", response_model=ApiResponse[BacktestStatus])
async def submit_simple_backtest(
    request: SimpleBacktestRequest,
    runner=Depends(get_backtest_runner),
):
    """提交简化版回测任务

    用于快速测试单因子/单策略，自动转换为完整格式。
    """
    try:
        # 转换为完整请求
        full_request = request.to_full_request()

        from domains.strategy_hub.services.backtest_runner import (
            BacktestRequest as RunnerRequest,
        )

        strategy_list = _convert_request_to_engine_format(full_request)

        runner_request = RunnerRequest(
            name=full_request.name,
            strategy_list=strategy_list,
            start_date=full_request.start_date,
            end_date=full_request.end_date,
            leverage=full_request.leverage,
            initial_usdt=full_request.initial_usdt,
        )

        task_id = await run_sync(runner.submit, runner_request)

        return ApiResponse(
            data=BacktestStatus(
                task_id=task_id,
                status="pending",
                progress=0.0,
                message="回测任务已提交",
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _get_task_status(task_id: str, runner) -> BacktestStatus:
    """获取单个任务状态"""
    status = runner.get_status(task_id)
    if not status:
        return BacktestStatus(
            task_id=task_id,
            status="failed",
            progress=0.0,
            message=f"任务不存在: {task_id}",
        )

    return BacktestStatus(
        task_id=task_id,
        status=status.status.value
        if hasattr(status.status, "value")
        else status.status,
        progress=status.progress,
        message=status.error_message,
        started_at=str(status.started_at) if status.started_at else None,
        completed_at=str(status.completed_at) if status.completed_at else None,
    )


@router.post("/status/batch", response_model=ApiResponse[BatchBacktestStatus])
async def get_batch_backtest_status(
    task_ids: List[str],
    runner=Depends(get_backtest_runner),
):
    """批量获取回测任务状态"""
    try:
        tasks_status = []
        for task_id in task_ids:
            status = await run_sync(_get_task_status, task_id, runner)
            tasks_status.append(status)

        return ApiResponse(
            data=BatchBacktestStatus(
                total=len(task_ids),
                submitted=len(tasks_status),
                tasks=tasks_status,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}/status", response_model=ApiResponse[BacktestStatus])
async def get_backtest_status(task_id: str, runner=Depends(get_backtest_runner)):
    """获取回测任务状态"""
    try:
        status = await run_sync(runner.get_status, task_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

        return ApiResponse(
            data=BacktestStatus(
                task_id=task_id,
                status=status.status.value
                if hasattr(status.status, "value")
                else status.status,
                progress=status.progress,
                message=status.error_message,
                started_at=str(status.started_at) if status.started_at else None,
                completed_at=str(status.completed_at) if status.completed_at else None,
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}/result", response_model=ApiResponse[BacktestResult])
async def get_backtest_result(task_id: str, runner=Depends(get_backtest_runner)):
    """获取回测结果"""
    import json

    try:
        strategy = await run_sync(runner.get_result, task_id)
        if not strategy:
            raise HTTPException(status_code=404, detail=f"任务不存在或未完成: {task_id}")

        # 构建指标
        metrics = BacktestMetrics(
            cumulative_return=strategy.cumulative_return,
            annual_return=strategy.annual_return,
            max_drawdown=strategy.max_drawdown,
            max_drawdown_start=strategy.max_drawdown_start,
            max_drawdown_end=strategy.max_drawdown_end,
            sharpe_ratio=strategy.sharpe_ratio,
            recovery_rate=strategy.recovery_rate,
            recovery_time=strategy.recovery_time,
            win_periods=strategy.win_periods,
            loss_periods=strategy.loss_periods,
            win_rate=strategy.win_rate,
            avg_return_per_period=strategy.avg_return_per_period,
            profit_loss_ratio=strategy.profit_loss_ratio,
            max_single_profit=strategy.max_single_profit,
            max_single_loss=strategy.max_single_loss,
            max_consecutive_wins=strategy.max_consecutive_wins,
            max_consecutive_losses=strategy.max_consecutive_losses,
            return_std=strategy.return_std,
        )

        # 解析资金曲线
        equity_curve = None
        if strategy.equity_curve:
            try:
                equity_curve = json.loads(strategy.equity_curve)
            except json.JSONDecodeError:
                pass

        return ApiResponse(
            data=BacktestResult(
                task_id=task_id,
                strategy_id=strategy.id,
                status=strategy.task_status,
                metrics=metrics,
                equity_curve=equity_curve,
                trades=None,
                error=strategy.error_message,
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}", response_model=ApiResponse[None])
async def cancel_backtest(task_id: str, runner=Depends(get_backtest_runner)):
    """取消回测任务"""
    try:
        success = await run_sync(runner.cancel, task_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"任务不存在或无法取消: {task_id}")

        return ApiResponse(message="任务已取消")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config", response_model=ApiResponse[BacktestConfigResponse])
async def get_backtest_config():
    """获取当前回测配置

    返回 config/backtest_config.py 中的默认配置和可用因子列表。
    """
    try:
        import config
        from pathlib import Path

        # 获取可用因子列表 - 从 factors 目录读取
        project_root = Path(__file__).parent.parent.parent.parent.parent
        factors_dir = project_root / "factors"

        available_factors = []
        if factors_dir.exists():
            for f in factors_dir.iterdir():
                if f.is_file() and f.suffix == ".py" and not f.name.startswith("_"):
                    factor_name = f.stem
                    available_factors.append(factor_name)
            available_factors.sort()

        return ApiResponse(
            data=BacktestConfigResponse(
                pre_data_path=config.pre_data_path,
                data_source_dict=config.data_source_dict,
                start_date=config.start_date,
                end_date=config.end_date,
                account_type=config.account_type,
                initial_usdt=config.initial_usdt,
                leverage=config.leverage,
                margin_rate=config.margin_rate,
                swap_c_rate=config.swap_c_rate,
                spot_c_rate=config.spot_c_rate,
                swap_min_order_limit=config.swap_min_order_limit,
                spot_min_order_limit=config.spot_min_order_limit,
                avg_price_col=config.avg_price_col,
                min_kline_num=config.min_kline_num,
                black_list=config.black_list,
                white_list=config.white_list,
                stable_symbol=config.stable_symbol,
                available_factors=available_factors,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates", response_model=ApiResponse[List[BacktestTemplate]])
async def list_templates():
    """获取回测模板列表

    模板用于快速验证某类风格因子的有效性。
    模板不填充具体的选币因子，由用户自行添加要验证的因子。
    """
    templates = [
        BacktestTemplate(
            name="流动性因子验证",
            description="多空各10%选币，1H持仓，混合市场选合约。适用于流动性相关因子的快速验证。",
            strategy_list=[
                StrategyItem(
                    strategy="Liquidity",
                    hold_period="1H",
                    market="mix_swap",
                    long_select_coin_num=0.1,  # 10%
                    short_select_coin_num=0.1,  # 10%
                    long_cap_weight=1.0,
                    short_cap_weight=1.0,
                    factor_list=[],  # 不预设因子，由用户添加
                )
            ],
            default_config={
                "leverage": 1.0,
                "initial_usdt": 10000,
            },
        ),
    ]

    return ApiResponse(data=templates)
