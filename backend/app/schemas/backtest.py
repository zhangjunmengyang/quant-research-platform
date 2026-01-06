"""
回测 API 数据模型

完整暴露 strategy_hub/core 回测引擎的配置能力。
"""

from typing import Optional, List, Dict, Any, Literal, Union
from pydantic import BaseModel, Field


# =============================================================================
# 因子配置模型
# =============================================================================


class FactorItem(BaseModel):
    """单个选币因子配置"""

    name: str = Field(..., description="因子名称，需与 factors 目录中的因子文件名一致")
    is_sort_asc: bool = Field(True, description="排序方向，True=升序(选小的)，False=降序(选大的)")
    param: Union[int, float, List[Any]] = Field(0, description="因子参数")
    weight: float = Field(1.0, description="因子权重，多因子时用于加权排序")


class FilterItem(BaseModel):
    """单个过滤因子配置"""

    name: str = Field(..., description="过滤因子名称")
    param: Union[int, float, List[Any]] = Field(0, description="因子参数")
    method: Optional[str] = Field(
        None,
        description="过滤方式，格式为 'how:range'，如 'rank:<=10', 'pct:<0.1', 'val:>0'",
    )
    is_sort_asc: bool = Field(True, description="排序方向")


# =============================================================================
# 策略配置模型
# =============================================================================


class StrategyItem(BaseModel):
    """单个子策略配置

    对应回测引擎 strategy_list 中的一个策略项。
    """

    strategy: str = Field(..., description="策略名称/标识，用于从 StrategyHub 加载策略文件")

    # 持仓周期
    hold_period: str = Field("1H", description="持仓周期，如 1H, 6H, 1D, 7D")

    # 偏移配置
    offset: int = Field(0, description="策略偏移量")
    offset_list: Optional[List[int]] = Field(None, description="多偏移列表，如 [0, 1, 2]")

    # 选币市场范围
    market: str = Field(
        "swap_swap",
        description="选币范围_优先下单: swap_swap(合约选合约下), spot_spot, spot_swap, mix_spot, mix_swap",
    )

    # 多头配置
    long_select_coin_num: Union[int, float] = Field(
        0.1, description="多头选币数量，整数=固定数量，小数=百分比"
    )
    long_cap_weight: float = Field(1.0, description="多头资金权重")

    # 空头配置
    short_select_coin_num: Union[int, float, str] = Field(
        "long_nums", description="空头选币数量，'long_nums'=与多头相同"
    )
    short_cap_weight: float = Field(1.0, description="空头资金权重")

    # 策略整体权重
    cap_weight: float = Field(1.0, description="策略在组合中的资金权重")

    # 选币因子
    factor_list: List[FactorItem] = Field(
        default_factory=list, description="选币因子列表（多空共用）"
    )
    long_factor_list: Optional[List[FactorItem]] = Field(
        None, description="多头专用选币因子（多空分离时使用）"
    )
    short_factor_list: Optional[List[FactorItem]] = Field(
        None, description="空头专用选币因子（多空分离时使用）"
    )

    # 前置过滤因子
    filter_list: List[FilterItem] = Field(
        default_factory=list, description="前置过滤因子列表（多空共用）"
    )
    long_filter_list: Optional[List[FilterItem]] = Field(
        None, description="多头专用前置过滤因子"
    )
    short_filter_list: Optional[List[FilterItem]] = Field(
        None, description="空头专用前置过滤因子"
    )

    # 后置过滤因子
    filter_list_post: List[FilterItem] = Field(
        default_factory=list, description="后置过滤因子列表"
    )

    # 是否使用策略文件中的自定义函数
    use_custom_func: bool = Field(True, description="是否使用策略文件中的自定义计算函数")


# =============================================================================
# 回测请求模型
# =============================================================================


class BacktestRequest(BaseModel):
    """完整的回测请求配置

    对应 config/backtest_config.py 的全部可配置项。
    """

    # 回测名称
    name: str = Field(..., description="回测名称，用于标识和存储结果")

    # 时间配置
    start_date: str = Field(..., description="回测开始日期，格式 YYYY-MM-DD")
    end_date: str = Field(..., description="回测结束日期，格式 YYYY-MM-DD")

    # 账户配置
    account_type: Literal["统一账户", "普通账户"] = Field(
        "统一账户", description="账户类型"
    )
    initial_usdt: float = Field(10000.0, description="初始资金(USDT)")
    leverage: float = Field(1.0, description="杠杆倍数", ge=0.1, le=10.0)
    margin_rate: float = Field(0.05, description="维持保证金率", ge=0.01, le=0.5)

    # 手续费配置
    swap_c_rate: float = Field(0.0006, description="合约手续费率(含滑点)")
    spot_c_rate: float = Field(0.001, description="现货手续费率(含滑点)")

    # 最小下单量
    swap_min_order_limit: float = Field(5.0, description="合约最小下单量(USDT)")
    spot_min_order_limit: float = Field(10.0, description="现货最小下单量(USDT)")

    # 价格计算
    avg_price_col: Literal["avg_price_1m", "avg_price_5m"] = Field(
        "avg_price_1m", description="均价计算列"
    )

    # 币种过滤
    min_kline_num: int = Field(0, description="最少上市K线数，不满足的币种会被剔除")
    black_list: List[str] = Field(
        default_factory=list, description="黑名单币种，如 ['LUNA-USDT']"
    )
    white_list: List[str] = Field(
        default_factory=list, description="白名单币种，非空时只交易白名单中的币"
    )

    # 策略列表
    strategy_list: List[StrategyItem] = Field(
        ..., description="策略配置列表，至少包含一个策略"
    )

    # 再择时配置（可选）
    re_timing: Optional[Dict[str, Any]] = Field(None, description="再择时配置")


# =============================================================================
# 简化版回测请求（兼容旧API）
# =============================================================================


class SimpleBacktestRequest(BaseModel):
    """简化版回测请求

    用于快速测试单因子/单策略，自动转换为完整格式。
    """

    strategy_name: str = Field(..., description="策略名称")
    factor_list: List[str] = Field(..., description="因子名称列表")
    factor_params: Dict[str, List[float]] = Field(
        default_factory=dict, description="因子参数，key为因子名，value为参数列表"
    )
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")

    # 简化配置
    leverage: float = Field(1.0, description="杠杆")
    select_coin_num: Union[int, float] = Field(5, description="选币数量")
    trade_type: Literal["swap", "spot"] = Field("swap", description="交易类型")

    # 可选的高级配置
    hold_period: str = Field("1H", description="持仓周期")
    initial_usdt: float = Field(10000.0, description="初始资金")

    def to_full_request(self) -> BacktestRequest:
        """转换为完整回测请求"""
        # 构建因子列表
        factors = [
            FactorItem(
                name=name,
                is_sort_asc=True,
                param=self.factor_params.get(name, [0])[0]
                if self.factor_params.get(name)
                else 0,
                weight=1.0,
            )
            for name in self.factor_list
        ]

        # 构建策略
        market = "swap_swap" if self.trade_type == "swap" else "spot_spot"
        strategy = StrategyItem(
            strategy=self.strategy_name,
            hold_period=self.hold_period,
            market=market,
            long_select_coin_num=self.select_coin_num,
            short_select_coin_num=0,  # 简化版默认不做空
            factor_list=factors,
        )

        return BacktestRequest(
            name=self.strategy_name,
            start_date=self.start_date,
            end_date=self.end_date,
            leverage=self.leverage,
            initial_usdt=self.initial_usdt,
            strategy_list=[strategy],
        )


# =============================================================================
# 回测状态和结果模型
# =============================================================================


class BacktestStatus(BaseModel):
    """回测任务状态"""

    task_id: str
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    progress: float = 0.0
    message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class BatchBacktestRequest(BaseModel):
    """批量回测请求

    支持一次提交多个回测任务，后端并行执行。
    单个回测是批量的特例（tasks 只包含一个元素）。
    """

    tasks: List[BacktestRequest] = Field(
        ..., description="回测任务列表", min_length=1
    )


class BatchBacktestStatus(BaseModel):
    """批量回测状态"""

    total: int = Field(..., description="任务总数")
    submitted: int = Field(..., description="已提交数")
    tasks: List[BacktestStatus] = Field(default_factory=list, description="各任务状态")


class BacktestMetrics(BaseModel):
    """回测指标"""

    # 收益指标
    cumulative_return: Optional[float] = Field(None, description="累计收益率")
    annual_return: Optional[float] = Field(None, description="年化收益率")
    avg_return_per_period: Optional[float] = Field(None, description="每周期平均收益")

    # 风险指标
    max_drawdown: Optional[float] = Field(None, description="最大回撤")
    max_drawdown_start: Optional[str] = Field(None, description="最大回撤开始日期")
    max_drawdown_end: Optional[str] = Field(None, description="最大回撤结束日期")
    return_std: Optional[float] = Field(None, description="收益标准差")

    # 风险调整收益
    sharpe_ratio: Optional[float] = Field(None, description="夏普比率")
    recovery_rate: Optional[float] = Field(None, description="恢复率")
    recovery_time: Optional[str] = Field(None, description="恢复时间")

    # 胜率统计
    win_periods: Optional[int] = Field(None, description="盈利周期数")
    loss_periods: Optional[int] = Field(None, description="亏损周期数")
    win_rate: Optional[float] = Field(None, description="胜率")
    profit_loss_ratio: Optional[float] = Field(None, description="盈亏比")

    # 极值统计
    max_single_profit: Optional[float] = Field(None, description="单次最大盈利")
    max_single_loss: Optional[float] = Field(None, description="单次最大亏损")
    max_consecutive_wins: Optional[int] = Field(None, description="最大连续盈利次数")
    max_consecutive_losses: Optional[int] = Field(None, description="最大连续亏损次数")


class BacktestResult(BaseModel):
    """回测结果"""

    task_id: str
    strategy_id: Optional[str] = None
    status: str
    metrics: Optional[BacktestMetrics] = None
    equity_curve: Optional[List[Dict[str, Any]]] = None
    trades: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


# =============================================================================
# 回测模板和配置
# =============================================================================


class BacktestTemplate(BaseModel):
    """回测模板"""

    name: str
    description: Optional[str] = None
    strategy_list: List[StrategyItem] = Field(default_factory=list)
    default_config: Optional[Dict[str, Any]] = None


class BacktestConfigResponse(BaseModel):
    """当前回测配置响应"""

    # 数据路径
    pre_data_path: str = Field(..., description="预处理数据路径")
    data_source_dict: Dict[str, Any] = Field(
        default_factory=dict, description="额外数据源"
    )

    # 默认时间范围
    start_date: str
    end_date: str

    # 默认交易配置
    account_type: str
    initial_usdt: float
    leverage: float
    margin_rate: float
    swap_c_rate: float
    spot_c_rate: float
    swap_min_order_limit: float
    spot_min_order_limit: float
    avg_price_col: str

    # 币种过滤
    min_kline_num: int
    black_list: List[str]
    white_list: List[str]
    stable_symbol: List[str]

    # 可用因子列表
    available_factors: List[str] = Field(default_factory=list)
