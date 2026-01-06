"""Data API routes.

NOTE: 所有同步服务调用都使用 run_sync 包装，避免阻塞 event loop。
"""

import math
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.schemas.common import ApiResponse
from app.core.deps import get_data_loader, get_factor_calculator
from app.core.async_utils import run_sync

router = APIRouter()


def _safe_float(val, default: Optional[float] = None) -> Optional[float]:
    """安全获取浮点值，处理 NaN 和无效值"""
    if val is None or (hasattr(val, '__iter__') and not isinstance(val, str)):
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError):
        return default


def _safe_int(val) -> Optional[int]:
    """安全获取整数值，处理 NaN 和无效值"""
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else int(f)
    except (ValueError, TypeError):
        return None


class SymbolInfo(BaseModel):
    """Symbol information."""

    symbol: str
    has_spot: bool = True
    has_swap: bool = True
    first_candle_time: Optional[str] = None
    last_candle_time: Optional[str] = None
    kline_count: Optional[int] = None


class SymbolListItem(BaseModel):
    """Symbol list item with availability flags.

    通过 has_spot 和 has_swap 可以区分:
    - 只有现货: has_spot=True, has_swap=False
    - 只有合约: has_spot=False, has_swap=True
    - 两者都有: has_spot=True, has_swap=True
    """

    symbol: str
    base_currency: str
    quote_currency: str = "USDT"
    is_active: bool = True
    has_spot: bool = False  # 是否有现货数据
    has_swap: bool = False  # 是否有合约数据
    # 以下字段为主要数据类型的统计（优先使用 swap）
    first_candle_time: Optional[str] = None
    last_candle_time: Optional[str] = None
    kline_count: Optional[int] = None


class KlineDataItem(BaseModel):
    """Single K-line data item with all available fields."""

    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float  # 成交量（基础货币）
    quote_volume: Optional[float] = None  # 成交额（计价货币）
    trade_num: Optional[int] = None  # 成交笔数
    taker_buy_base_asset_volume: Optional[float] = None  # 主动买入成交量
    taker_buy_quote_asset_volume: Optional[float] = None  # 主动买入成交额
    funding_fee: Optional[float] = None  # 资金费率（仅合约）
    avg_price_1m: Optional[float] = None  # 1分钟均价
    avg_price_5m: Optional[float] = None  # 5分钟均价


class DataTypeStats(BaseModel):
    """Statistics for a specific data type (spot/swap)."""

    total_symbols: int = 0
    active_symbols: int = 0
    total_records: int = 0
    data_start_date: Optional[str] = None
    data_end_date: Optional[str] = None


class DataOverview(BaseModel):
    """Data overview statistics."""

    total_symbols: int  # 所有币种总数（去重）
    spot: DataTypeStats  # 现货数据统计
    swap: DataTypeStats  # 合约数据统计
    last_updated: Optional[str] = None
    available_factors: List[str] = []


class FactorCalculateRequest(BaseModel):
    """Factor calculation request."""

    factor_name: str
    symbol: str
    params: List[int] = [5, 10, 20]  # 因子参数（整数）
    data_type: str = "swap"  # spot 或 swap
    start_date: Optional[str] = None  # 起始日期 (YYYY-MM-DD)
    end_date: Optional[str] = None  # 结束日期 (YYYY-MM-DD)
    limit: int = 1000  # 返回数据点数量限制


class FactorValueItem(BaseModel):
    """单个因子值数据点"""
    time: str
    value: Optional[float] = None


class FactorParamResult(BaseModel):
    """单个参数的因子计算结果"""
    param: float
    data: List[FactorValueItem]
    stats: Dict[str, Optional[float]]


class FactorCalculateResult(BaseModel):
    """Factor calculation result."""

    factor_name: str
    symbol: str
    data_type: str
    results: List[FactorParamResult]


@router.get("/symbols", response_model=ApiResponse[List[SymbolListItem]])
async def list_symbols(loader=Depends(get_data_loader)):
    """获取可用币种列表（去重，包含现货/合约可用性标记）

    返回的列表可通过 has_spot/has_swap 字段进行过滤:
    - 全市场并集: 返回全部
    - 仅现货: filter(has_spot=True)
    - 仅合约: filter(has_swap=True)
    - 只有现货没有合约: filter(has_spot=True, has_swap=False)
    - 只有合约没有现货: filter(has_spot=False, has_swap=True)
    - 既有现货又有合约: filter(has_spot=True, has_swap=True)
    """
    try:
        # 加载现货和合约数据
        spot_data = await run_sync(loader.load_spot_data)
        swap_data = await run_sync(loader.load_swap_data)

        # 收集所有唯一币种名称
        all_symbols = set(spot_data.keys()) | set(swap_data.keys())

        symbols = []
        for name in sorted(all_symbols):
            base_currency = name.replace("-USDT", "").replace("USDT", "")

            # 检查可用性
            has_spot = name in spot_data
            has_swap = name in swap_data

            # 优先使用合约数据的时间范围（通常数据更全）
            df = swap_data.get(name) if has_swap else spot_data.get(name)

            first_time = None
            last_time = None
            kline_count = 0

            if df is not None and not df.empty and 'candle_begin_time' in df.columns:
                first_time = str(df['candle_begin_time'].min())[:19]
                last_time = str(df['candle_begin_time'].max())[:19]
                kline_count = len(df)

            symbols.append(SymbolListItem(
                symbol=name,
                base_currency=base_currency,
                quote_currency="USDT",
                is_active=True,
                has_spot=has_spot,
                has_swap=has_swap,
                first_candle_time=first_time,
                last_candle_time=last_time,
                kline_count=kline_count,
            ))

        return ApiResponse(data=symbols)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview", response_model=ApiResponse[DataOverview])
async def get_overview(
    loader=Depends(get_data_loader),
    calculator=Depends(get_factor_calculator),
):
    """获取数据概览"""
    try:
        from datetime import datetime

        # 获取数据统计信息
        stats = await run_sync(loader.get_stats)
        factors = await run_sync(calculator.list_factors)

        return ApiResponse(
            data=DataOverview(
                total_symbols=stats['total_symbols'],
                spot=DataTypeStats(**stats['spot']),
                swap=DataTypeStats(**stats['swap']),
                last_updated=datetime.now().isoformat(),
                available_factors=factors,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kline/{symbol}", response_model=ApiResponse[List[KlineDataItem]])
async def get_kline(
    symbol: str,
    data_type: str = Query("swap", description="数据类型: spot 或 swap"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(5000, ge=1, le=10000),
    loader=Depends(get_data_loader),
):
    """获取币种K线数据"""
    try:
        df = await run_sync(loader.get_kline, symbol, data_type=data_type, start_date=start_date, end_date=end_date)
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"币种数据不存在: {symbol}")

        # 当有日期筛选时，返回筛选范围内的所有数据（最多 limit 条）
        # 当没有日期筛选时，返回最新的 limit 条数据
        if start_date or end_date:
            df = df.head(limit)
        else:
            df = df.tail(limit)

        # 过滤无效数据行（open/close 为 0 表示无数据）
        df = df[(df['open'] != 0) | (df['close'] != 0)]

        if df.empty:
            return ApiResponse(data=[])

        # 使用向量化操作转换数据（比 iterrows 快 100x）
        # 替换 NaN/Inf 为 None
        df = df.replace([float('inf'), float('-inf')], None)

        # 构建时间字符串
        time_series = df['candle_begin_time'].apply(
            lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x)
        )

        # 使用 to_dict('records') 进行批量转换
        kline_items = []
        records = df.to_dict('records')
        time_list = time_series.tolist()

        for i, row in enumerate(records):
            kline_items.append(KlineDataItem(
                time=time_list[i],
                open=_safe_float(row.get('open'), 0.0),
                high=_safe_float(row.get('high'), 0.0),
                low=_safe_float(row.get('low'), 0.0),
                close=_safe_float(row.get('close'), 0.0),
                volume=_safe_float(row.get('volume'), 0.0),
                quote_volume=_safe_float(row.get('quote_volume')),
                trade_num=_safe_int(row.get('trade_num')),
                taker_buy_base_asset_volume=_safe_float(row.get('taker_buy_base_asset_volume')),
                taker_buy_quote_asset_volume=_safe_float(row.get('taker_buy_quote_asset_volume')),
                funding_fee=_safe_float(row.get('funding_fee')),
                avg_price_1m=_safe_float(row.get('avg_price_1m')),
                avg_price_5m=_safe_float(row.get('avg_price_5m')),
            ))

        return ApiResponse(data=kline_items)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbol/{symbol}", response_model=ApiResponse[SymbolInfo])
async def get_symbol_info(symbol: str, loader=Depends(get_data_loader)):
    """获取币种详细信息"""
    try:
        info = await run_sync(loader.get_symbol_info, symbol)
        if not info:
            raise HTTPException(status_code=404, detail=f"币种不存在: {symbol}")

        return ApiResponse(
            data=SymbolInfo(
                symbol=info.symbol,
                has_spot=info.has_spot,
                has_swap=info.has_swap,
                first_candle_time=str(info.first_candle_time)
                if info.first_candle_time
                else None,
                last_candle_time=str(info.last_candle_time)
                if info.last_candle_time
                else None,
                kline_count=info.kline_count,
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/factors", response_model=ApiResponse[List[str]])
async def list_available_factors(calculator=Depends(get_factor_calculator)):
    """获取可用因子列表"""
    try:
        factors = await run_sync(calculator.list_factors)
        return ApiResponse(data=factors)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate-factor", response_model=ApiResponse[FactorCalculateResult])
async def calculate_factor(
    request: FactorCalculateRequest,
    loader=Depends(get_data_loader),
    calculator=Depends(get_factor_calculator),
):
    """计算因子"""
    try:
        # Get kline data with optional date range
        df = await run_sync(
            loader.get_kline,
            request.symbol,
            data_type=request.data_type,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        if df is None or df.empty:
            raise HTTPException(
                status_code=404, detail=f"币种数据不存在: {request.symbol}"
            )

        # Calculate factor
        result = await run_sync(calculator.calculate, request.factor_name, df, request.params)
        if result is None:
            raise HTTPException(
                status_code=400, detail=f"因子计算失败: {request.factor_name}"
            )

        # 获取时间序列
        time_col = df['candle_begin_time'] if 'candle_begin_time' in df.columns else df.index

        # Convert result to response format with time series
        param_results = []
        for param, series in result.items():
            # 取最后 limit 条数据
            series_tail = series.tail(request.limit)
            time_tail = time_col.tail(request.limit)

            # 构建时序数据
            data_points = []
            for t, v in zip(time_tail, series_tail):
                time_str = t.isoformat() if hasattr(t, 'isoformat') else str(t)
                value = _safe_float(v)
                data_points.append(FactorValueItem(time=time_str, value=value))

            # 计算统计量
            valid_values = series.dropna()
            stats = {
                'count': len(valid_values),
                'mean': _safe_float(valid_values.mean()) if len(valid_values) > 0 else None,
                'std': _safe_float(valid_values.std()) if len(valid_values) > 0 else None,
                'min': _safe_float(valid_values.min()) if len(valid_values) > 0 else None,
                'max': _safe_float(valid_values.max()) if len(valid_values) > 0 else None,
                'latest': _safe_float(valid_values.iloc[-1]) if len(valid_values) > 0 else None,
            }

            param_results.append(FactorParamResult(
                param=float(param),
                data=data_points,
                stats=stats,
            ))

        return ApiResponse(
            data=FactorCalculateResult(
                factor_name=request.factor_name,
                symbol=request.symbol,
                data_type=request.data_type,
                results=param_results,
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
