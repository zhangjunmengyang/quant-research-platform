"""Strategy-related Pydantic schemas."""

from typing import Optional, Union

from pydantic import BaseModel, Field


class Strategy(BaseModel):
    """Strategy model for API responses.

    包含完整的回测配置和指标，支持 MCP 和 REST API 查询。
    """

    # 基础信息
    id: str
    name: str
    description: Optional[str] = None

    # 因子配置 (JSON 字符串)
    factor_list: Optional[str] = None
    factor_params: Optional[str] = None
    strategy_config: Optional[str] = None  # 完整策略配置

    # 回测配置
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    leverage: float = 1.0
    select_coin_num: Union[int, float] = 5
    trade_type: str = "swap"

    # 多空配置
    long_select_coin_num: Optional[float] = None
    short_select_coin_num: Optional[float] = None
    long_cap_weight: Optional[float] = None
    short_cap_weight: Optional[float] = None

    # 持仓配置
    hold_period: Optional[str] = None
    offset: Optional[int] = None
    market: Optional[str] = None

    # 排序方向 (JSON 字符串)
    sort_directions: Optional[str] = None

    # 账户配置
    account_type: Optional[str] = None
    initial_usdt: Optional[float] = None
    margin_rate: Optional[float] = None

    # 手续费配置
    swap_c_rate: Optional[float] = None
    spot_c_rate: Optional[float] = None

    # 最小下单量
    swap_min_order_limit: Optional[float] = None
    spot_min_order_limit: Optional[float] = None

    # 价格计算
    avg_price_col: Optional[str] = None

    # 币种过滤
    min_kline_num: Optional[int] = None
    black_list: Optional[str] = None
    white_list: Optional[str] = None

    # 核心绩效指标
    cumulative_return: Optional[float] = None
    annual_return: Optional[float] = None
    max_drawdown: Optional[float] = None
    max_drawdown_start: Optional[str] = None
    max_drawdown_end: Optional[str] = None
    sharpe_ratio: Optional[float] = None
    recovery_rate: Optional[float] = None
    recovery_time: Optional[str] = None

    # 交易统计
    win_periods: Optional[int] = None
    loss_periods: Optional[int] = None
    win_rate: Optional[float] = None
    avg_return_per_period: Optional[float] = None
    profit_loss_ratio: Optional[float] = None
    max_single_profit: Optional[float] = None
    max_single_loss: Optional[float] = None
    max_consecutive_wins: Optional[int] = None
    max_consecutive_losses: Optional[int] = None
    return_std: Optional[float] = None

    # 周期收益 (JSON 字符串)
    year_return: Optional[str] = None
    quarter_return: Optional[str] = None
    month_return: Optional[str] = None

    # 资金曲线 (JSON 字符串)
    equity_curve: Optional[str] = None

    # 元数据
    verified: bool = False
    tags: Optional[str] = None
    notes: Optional[str] = None
    task_status: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class StrategyStats(BaseModel):
    """Strategy statistics."""

    total: int
    verified: int
    avg_sharpe: Optional[float] = None
    avg_return: Optional[float] = None


class StrategyCreate(BaseModel):
    """Strategy create request."""

    name: str
    description: Optional[str] = None
    factor_list: str
    factor_params: str
    start_date: str
    end_date: str
    leverage: float = 1.0
    select_coin_num: Union[int, float] = 5
    trade_type: str = "swap"


class StrategyUpdate(BaseModel):
    """Strategy update request."""

    name: Optional[str] = None
    description: Optional[str] = None
    factor_list: Optional[str] = None
    factor_params: Optional[str] = None
