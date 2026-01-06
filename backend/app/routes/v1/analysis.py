"""
分析 API 路由

提供参数搜索、参数分析、因子分析、策略对比等分析功能的 API 端点。

NOTE: 所有同步服务调用都使用 run_sync 包装，避免阻塞 event loop。
"""

import logging
from typing import List

import pandas as pd
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.core.exceptions import handle_service_error
from app.core.async_utils import run_sync
from app.schemas.common import ApiResponse
from app.schemas.analysis import (
    ParamSearchRequest,
    ParamSearchResponse,
    ParamAnalysisRequest,
    ParamAnalysisResponse,
    FactorGroupAnalysisRequest,
    FactorGroupAnalysisResponse,
    BacktestComparisonRequest,
    BacktestComparisonResponse,
    FactorComparisonRequest,
    FactorComparisonResponse,
    StrategyComparisonRequest,
    CoinSimilarityResponse,
    EquityCorrelationResponse,
)
from domains.strategy_hub.services import (
    get_param_search_service,
    get_param_analysis_service,
    get_backtest_comparison_service,
    get_coin_similarity_service,
    get_equity_correlation_service,
)
from domains.factor_hub.services import get_factor_group_analysis_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Analysis"])


# ============= 参数搜索 =============

@router.post("/param-search", response_model=ApiResponse[ParamSearchResponse])
@handle_service_error("Param search")
async def run_param_search(
    request: ParamSearchRequest,
    background_tasks: BackgroundTasks
) -> ApiResponse[ParamSearchResponse]:
    """
    运行参数搜索

    启动参数遍历搜索任务，找到最优参数组合。
    """
    service = get_param_search_service()
    result = await run_sync(
        service.run_search,
        name=request.name,
        batch_params=request.batch_params,
        strategy_template=request.strategy_template,
        max_workers=request.max_workers
    )
    return ApiResponse(
        success=True,
        data=ParamSearchResponse(
            name=result.name,
            total_combinations=result.total_combinations,
            status=result.status,
            output_path=result.output_path,
            error=result.error
        )
    )


# ============= 参数分析 =============

@router.post("/param-analysis", response_model=ApiResponse[ParamAnalysisResponse])
@handle_service_error("Param analysis")
async def analyze_params(request: ParamAnalysisRequest) -> ApiResponse[ParamAnalysisResponse]:
    """
    参数分析

    分析参数遍历结果，生成热力图或平原图。
    """
    service = get_param_analysis_service()
    result = await run_sync(
        service.analyze,
        trav_name=request.trav_name,
        batch_params=request.batch_params,
        param_x=request.param_x,
        param_y=request.param_y,
        limit_dict=request.limit_dict,
        indicator=request.indicator
    )
    return ApiResponse(
        success=True,
        data=ParamAnalysisResponse(
            name=result.name,
            analysis_type=result.analysis_type,
            indicator=result.indicator,
            html_path=result.html_path,
            error=result.error
        )
    )


# ============= 因子分组分析 =============

from app.schemas.analysis import GroupCurvePoint, GroupBarData

@router.post("/factor-group", response_model=ApiResponse[List[FactorGroupAnalysisResponse]])
@handle_service_error("Factor group analysis")
async def analyze_factor_groups(
    request: FactorGroupAnalysisRequest
) -> ApiResponse[List[FactorGroupAnalysisResponse]]:
    """
    因子分组分析

    分析因子在不同分位组的收益表现，返回可直接用于前端渲染的数据。
    """
    service = get_factor_group_analysis_service()
    results = await run_sync(
        service.analyze_multiple_factors,
        factor_dict=request.factor_dict,
        data_type=request.data_type,
        bins=request.bins,
        method=request.method,
        filter_configs=request.filter_list
    )

    response_list = []
    for r in results:
        # 转换曲线数据为前端可用格式
        curve_data = []
        if r.group_curve is not None and not r.group_curve.empty:
            for date, row in r.group_curve.iterrows():
                curve_data.append(GroupCurvePoint(
                    date=date.strftime('%Y-%m-%d'),
                    values={col: float(row[col]) if not pd.isna(row[col]) else 0 for col in r.group_curve.columns}
                ))

        # 转换柱状图数据
        bar_data = []
        if r.bar_data is not None and not r.bar_data.empty:
            is_spot_only = r.data_type == 'spot'
            display_labels = r.labels.copy()
            if not is_spot_only:
                display_labels.append('long_short_nav')

            factor_labels = ['Min Value'] + [''] * (r.bins - 2) + ['Max Value']
            if not is_spot_only:
                factor_labels.append('')

            for i, (_, row) in enumerate(r.bar_data.iterrows()):
                group_name = row['groups']
                if group_name in display_labels:
                    label = factor_labels[i] if i < len(factor_labels) else ''
                    bar_data.append(GroupBarData(
                        group=group_name,
                        nav=float(row['asset']) if not pd.isna(row['asset']) else 0,
                        label=label
                    ))

        response_list.append(FactorGroupAnalysisResponse(
            factor_name=r.factor_name,
            bins=r.bins,
            method=r.method,
            data_type=r.data_type,
            labels=r.labels,
            curve_data=curve_data,
            bar_data=bar_data,
            error=r.error
        ))

    return ApiResponse(success=True, data=response_list)


# ============= 回测实盘对比 =============

@router.post("/backtest-comparison", response_model=ApiResponse[BacktestComparisonResponse])
@handle_service_error("Backtest comparison")
async def compare_backtest_live(
    request: BacktestComparisonRequest
) -> ApiResponse[BacktestComparisonResponse]:
    """
    回测实盘对比

    对比回测和实盘的资金曲线、选币结果。
    """
    service = get_backtest_comparison_service()
    result = await run_sync(
        service.compare,
        backtest_name=request.backtest_name,
        start_time=request.start_time,
        end_time=request.end_time
    )
    return ApiResponse(
        success=True,
        data=BacktestComparisonResponse(
            backtest_name=result.backtest_name,
            start_time=result.start_time,
            end_time=result.end_time,
            coin_selection_similarity=result.coin_selection_similarity,
            html_path=result.html_path,
            error=result.error
        )
    )


@router.post("/factor-comparison", response_model=ApiResponse[FactorComparisonResponse])
@handle_service_error("Factor comparison")
async def compare_factor_values(
    request: FactorComparisonRequest
) -> ApiResponse[FactorComparisonResponse]:
    """
    因子值对比

    对比单个币种在回测和实盘中的因子值。
    """
    service = get_backtest_comparison_service()
    result = await run_sync(
        service.compare_factor_values,
        backtest_name=request.backtest_name,
        coin=request.coin,
        factor_names=request.factor_names
    )
    return ApiResponse(
        success=True,
        data=FactorComparisonResponse(
            backtest_name=result.backtest_name,
            coin=result.coin,
            factors=result.factors,
            html_path=result.html_path,
            error=result.error
        )
    )


# ============= 策略对比 =============

@router.post("/coin-similarity", response_model=ApiResponse[CoinSimilarityResponse])
@handle_service_error("Coin similarity analysis")
async def analyze_coin_similarity(
    request: StrategyComparisonRequest
) -> ApiResponse[CoinSimilarityResponse]:
    """
    选币相似度分析

    计算多策略之间的选币重合度。
    """
    if request.comparison_type != 'coin_similarity':
        return ApiResponse(success=False, error="Invalid comparison_type for this endpoint")

    service = get_coin_similarity_service()
    result = await run_sync(service.analyze, request.strategy_list)
    return ApiResponse(
        success=True,
        data=CoinSimilarityResponse(
            strategies=result.strategies,
            html_path=result.html_path,
            error=result.error
        )
    )


@router.post("/equity-correlation", response_model=ApiResponse[EquityCorrelationResponse])
@handle_service_error("Equity correlation analysis")
async def analyze_equity_correlation(
    request: StrategyComparisonRequest
) -> ApiResponse[EquityCorrelationResponse]:
    """
    资金曲线相关性分析

    计算多策略资金曲线涨跌幅之间的相关性。
    """
    if request.comparison_type != 'equity_correlation':
        return ApiResponse(success=False, error="Invalid comparison_type for this endpoint")

    service = get_equity_correlation_service()
    result = await run_sync(service.analyze, request.strategy_list)
    return ApiResponse(
        success=True,
        data=EquityCorrelationResponse(
            strategies=result.strategies,
            html_path=result.html_path,
            error=result.error
        )
    )


# ============= 报告获取 =============

@router.get("/reports/{report_path:path}")
async def get_report(report_path: str):
    """
    获取分析报告

    返回生成的 HTML 分析报告文件。
    """
    from domains.factor_hub.core.config import get_config_loader

    # 使用配置获取数据目录的绝对路径
    config_loader = get_config_loader()
    base_path = config_loader.data_dir / "analysis_results"
    full_path = base_path / report_path

    logger.info(f"Looking for report at: {full_path}")

    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Report not found: {full_path}")

    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    # 安全检查：确保路径在允许的目录内
    try:
        full_path.resolve().relative_to(base_path.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(
        path=full_path,
        media_type="text/html",
        filename=full_path.name
    )
