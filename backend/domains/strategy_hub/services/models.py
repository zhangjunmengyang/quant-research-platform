"""
策略数据模型

定义 Strategy 数据类和相关枚举。
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    """回测任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BacktestTask:
    """回测任务单

    存储回测配置模板，可被多次执行。
    每次执行产生一条 TaskExecution 记录。
    """

    # 基本信息
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str | None = None

    # 完整回测配置 (JSON 字符串)
    config: str = "{}"  # JSON: BacktestRequest 格式

    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # 标签和备注
    tags: str | None = None  # JSON: List[str]
    notes: str | None = None

    # 统计信息
    execution_count: int = 0  # 执行次数
    last_execution_at: str | None = None  # 最后执行时间

    def get_config(self) -> dict[str, Any]:
        """获取配置"""
        try:
            return json.loads(self.config) if self.config else {}
        except json.JSONDecodeError:
            return {}

    def set_config(self, config: dict[str, Any]) -> None:
        """设置配置"""
        self.config = json.dumps(config, ensure_ascii=False)

    def get_tags(self) -> list[str]:
        """获取标签列表"""
        try:
            return json.loads(self.tags) if self.tags else []
        except json.JSONDecodeError:
            return []

    def set_tags(self, tags: list[str]) -> None:
        """设置标签列表"""
        self.tags = json.dumps(tags, ensure_ascii=False)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "config": self.config,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
            "notes": self.notes,
            "execution_count": self.execution_count,
            "last_execution_at": self.last_execution_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BacktestTask":
        """从字典创建实例"""
        task = cls()
        fields = [
            "id", "name", "description", "config",
            "created_at", "updated_at", "tags", "notes",
            "execution_count", "last_execution_at",
        ]
        for field_name in fields:
            if field_name in data and data[field_name] is not None:
                setattr(task, field_name, data[field_name])
        return task


@dataclass
class TaskExecution:
    """任务执行记录

    记录每次执行的状态和结果。
    每个执行记录关联到一个 BacktestTask。
    """

    # 执行ID
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""  # 关联的任务单ID

    # 执行状态
    status: str = "pending"  # pending/running/completed/failed/cancelled

    # 执行时间
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: str | None = None
    completed_at: str | None = None

    # 执行进度
    progress: float = 0.0
    message: str | None = None

    # 因子信息（从config中提取，便于展示）
    factor_list: str = "[]"  # JSON: List[str]
    factor_params: str = "{}"  # JSON: Dict

    # 回测配置快照（便于查询）
    start_date: str = ""
    end_date: str = ""
    leverage: float = 1.0
    account_type: str = "统一账户"
    initial_usdt: float = 10000
    hold_period: str = "1H"

    # 多空配置
    long_select_coin_num: float = 5
    short_select_coin_num: float = 0

    # 核心绩效指标
    cumulative_return: float = 0.0
    annual_return: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_start: str | None = None
    max_drawdown_end: str | None = None
    sharpe_ratio: float = 0.0
    recovery_rate: float = 0.0
    recovery_time: str | None = None

    # 交易统计
    win_periods: int = 0
    loss_periods: int = 0
    win_rate: float = 0.0
    avg_return_per_period: float = 0.0
    profit_loss_ratio: float = 0.0
    max_single_profit: float = 0.0
    max_single_loss: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    return_std: float = 0.0

    # 周期收益 (JSON 存储)
    year_return: str | None = None
    quarter_return: str | None = None
    month_return: str | None = None

    # 资金曲线数据 (JSON 存储)
    equity_curve: str | None = None

    # 错误信息
    error_message: str | None = None

    # 策略库关联（导出后的ID）
    strategy_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "progress": self.progress,
            "message": self.message,
            "factor_list": self.factor_list,
            "factor_params": self.factor_params,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "leverage": self.leverage,
            "account_type": self.account_type,
            "initial_usdt": self.initial_usdt,
            "hold_period": self.hold_period,
            "long_select_coin_num": self.long_select_coin_num,
            "short_select_coin_num": self.short_select_coin_num,
            "cumulative_return": self.cumulative_return,
            "annual_return": self.annual_return,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_start": self.max_drawdown_start,
            "max_drawdown_end": self.max_drawdown_end,
            "sharpe_ratio": self.sharpe_ratio,
            "recovery_rate": self.recovery_rate,
            "recovery_time": self.recovery_time,
            "win_periods": self.win_periods,
            "loss_periods": self.loss_periods,
            "win_rate": self.win_rate,
            "avg_return_per_period": self.avg_return_per_period,
            "profit_loss_ratio": self.profit_loss_ratio,
            "max_single_profit": self.max_single_profit,
            "max_single_loss": self.max_single_loss,
            "max_consecutive_wins": self.max_consecutive_wins,
            "max_consecutive_losses": self.max_consecutive_losses,
            "return_std": self.return_std,
            "year_return": self.year_return,
            "quarter_return": self.quarter_return,
            "month_return": self.month_return,
            "equity_curve": self.equity_curve,
            "error_message": self.error_message,
            "strategy_id": self.strategy_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskExecution":
        """从字典创建实例"""
        execution = cls()
        for field_name in [
            "id", "task_id", "status", "created_at", "started_at", "completed_at",
            "progress", "message", "factor_list", "factor_params",
            "start_date", "end_date", "leverage", "account_type", "initial_usdt",
            "hold_period", "long_select_coin_num", "short_select_coin_num",
            "cumulative_return", "annual_return", "max_drawdown",
            "max_drawdown_start", "max_drawdown_end", "sharpe_ratio",
            "recovery_rate", "recovery_time",
            "win_periods", "loss_periods", "win_rate",
            "avg_return_per_period", "profit_loss_ratio",
            "max_single_profit", "max_single_loss",
            "max_consecutive_wins", "max_consecutive_losses", "return_std",
            "year_return", "quarter_return", "month_return", "equity_curve",
            "error_message", "strategy_id",
        ]:
            if field_name in data and data[field_name] is not None:
                setattr(execution, field_name, data[field_name])
        return execution


@dataclass
class TaskInfo:
    """回测任务信息"""
    task_id: str
    status: TaskStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    progress: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "progress": self.progress,
        }


@dataclass
class Strategy:
    """
    策略数据模型

    基于 strategy_evaluate() 返回的指标设计。
    """

    # 基础信息
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str | None = None

    # 因子配置 (JSON 字符串存储)
    factor_list: str = "[]"  # JSON: List[str]
    factor_params: str = "{}"  # JSON: Dict[str, Any]

    # 完整策略配置 (JSON 字符串存储)
    strategy_config: str | None = None  # JSON: 完整的 strategy_list 配置

    # 回测配置
    start_date: str = ""
    end_date: str = ""
    leverage: float = 1.0
    select_coin_num: float = 5  # 支持小数（百分比）
    trade_type: str = "swap"  # swap / spot

    # 多空配置
    long_select_coin_num: float = 5  # 多头选币数量
    short_select_coin_num: float = 0  # 空头选币数量
    long_cap_weight: float = 1.0  # 多头资金权重
    short_cap_weight: float = 0.0  # 空头资金权重

    # 持仓配置
    hold_period: str = "1H"  # 持仓周期
    offset: int = 0  # 偏移量
    market: str = "swap_swap"  # 选币市场范围

    # 排序方向 (JSON 字符串存储)
    sort_directions: str | None = None  # JSON: Dict[str, bool] 因子名 -> is_sort_asc

    # 账户配置
    account_type: str = "统一账户"  # 账户类型
    initial_usdt: float = 10000  # 初始资金
    margin_rate: float = 0.05  # 维持保证金率

    # 手续费配置
    swap_c_rate: float = 0.0006  # 合约手续费率
    spot_c_rate: float = 0.001  # 现货手续费率

    # 最小下单量
    swap_min_order_limit: float = 5  # 合约最小下单量
    spot_min_order_limit: float = 10  # 现货最小下单量

    # 价格计算
    avg_price_col: str = "avg_price_1m"  # 均价计算列

    # 币种过滤
    min_kline_num: int = 0  # 最少上市K线数
    black_list: str | None = None  # JSON: List[str]
    white_list: str | None = None  # JSON: List[str]

    # 核心绩效指标 (来自 strategy_evaluate)
    cumulative_return: float = 0.0  # 累积净值
    annual_return: float = 0.0  # 年化收益
    max_drawdown: float = 0.0  # 最大回撤
    max_drawdown_start: str | None = None  # 最大回撤开始时间
    max_drawdown_end: str | None = None  # 最大回撤结束时间
    sharpe_ratio: float = 0.0  # 年化收益/回撤比
    recovery_rate: float = 0.0  # 修复涨幅
    recovery_time: str | None = None  # 修复时间

    # 交易统计
    win_periods: int = 0  # 盈利周期数
    loss_periods: int = 0  # 亏损周期数
    win_rate: float = 0.0  # 胜率
    avg_return_per_period: float = 0.0  # 每周期平均收益
    profit_loss_ratio: float = 0.0  # 盈亏收益比
    max_single_profit: float = 0.0  # 单周期最大盈利
    max_single_loss: float = 0.0  # 单周期最大亏损
    max_consecutive_wins: int = 0  # 最大连续盈利周期数
    max_consecutive_losses: int = 0  # 最大连续亏损周期数
    return_std: float = 0.0  # 收益率标准差

    # 周期收益 (JSON 存储)
    year_return: str | None = None  # 年度收益 JSON
    quarter_return: str | None = None  # 季度收益 JSON
    month_return: str | None = None  # 月度收益 JSON

    # 资金曲线数据 (JSON 存储)
    equity_curve: str | None = None  # 资金曲线 JSON

    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    verified: bool = False
    tags: str | None = None  # JSON: List[str]
    notes: str | None = None

    # 任务信息
    task_id: str = ""
    task_status: str = "pending"  # pending/running/completed/failed
    error_message: str | None = None

    # ===== 便捷方法 =====

    def get_factor_list(self) -> list[str]:
        """获取因子列表"""
        try:
            return json.loads(self.factor_list) if self.factor_list else []
        except json.JSONDecodeError:
            return []

    def set_factor_list(self, factors: list[str]) -> None:
        """设置因子列表"""
        self.factor_list = json.dumps(factors, ensure_ascii=False)

    def get_factor_params(self) -> dict[str, Any]:
        """获取因子参数"""
        try:
            return json.loads(self.factor_params) if self.factor_params else {}
        except json.JSONDecodeError:
            return {}

    def set_factor_params(self, params: dict[str, Any]) -> None:
        """设置因子参数"""
        self.factor_params = json.dumps(params, ensure_ascii=False)

    def get_tags(self) -> list[str]:
        """获取标签列表"""
        try:
            return json.loads(self.tags) if self.tags else []
        except json.JSONDecodeError:
            return []

    def set_tags(self, tags: list[str]) -> None:
        """设置标签列表"""
        self.tags = json.dumps(tags, ensure_ascii=False)

    def get_sort_directions(self) -> dict[str, bool]:
        """获取排序方向"""
        try:
            return json.loads(self.sort_directions) if self.sort_directions else {}
        except json.JSONDecodeError:
            return {}

    def set_sort_directions(self, directions: dict[str, bool]) -> None:
        """设置排序方向"""
        self.sort_directions = json.dumps(directions, ensure_ascii=False)

    def get_strategy_config(self) -> list[dict[str, Any]]:
        """获取完整策略配置"""
        try:
            return json.loads(self.strategy_config) if self.strategy_config else []
        except json.JSONDecodeError:
            return []

    def set_strategy_config(self, config: list[dict[str, Any]]) -> None:
        """设置完整策略配置"""
        self.strategy_config = json.dumps(config, ensure_ascii=False)

    def get_black_list(self) -> list[str]:
        """获取黑名单"""
        try:
            return json.loads(self.black_list) if self.black_list else []
        except json.JSONDecodeError:
            return []

    def set_black_list(self, coins: list[str]) -> None:
        """设置黑名单"""
        self.black_list = json.dumps(coins, ensure_ascii=False)

    def get_white_list(self) -> list[str]:
        """获取白名单"""
        try:
            return json.loads(self.white_list) if self.white_list else []
        except json.JSONDecodeError:
            return []

    def set_white_list(self, coins: list[str]) -> None:
        """设置白名单"""
        self.white_list = json.dumps(coins, ensure_ascii=False)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典

        返回完整的策略数据，供内部存储和前端使用。
        """
        return {
            # 基础信息
            "id": self.id,
            "name": self.name,
            "description": self.description,
            # 因子配置
            "factor_list": self.factor_list,
            "factor_params": self.factor_params,
            "strategy_config": self.strategy_config,
            # 回测配置
            "start_date": self.start_date,
            "end_date": self.end_date,
            "leverage": self.leverage,
            "trade_type": self.trade_type,
            # 多空配置
            "long_select_coin_num": self.long_select_coin_num,
            "short_select_coin_num": self.short_select_coin_num,
            "long_cap_weight": self.long_cap_weight,
            "short_cap_weight": self.short_cap_weight,
            # 持仓配置
            "hold_period": self.hold_period,
            "offset": self.offset,
            "market": self.market,
            # 排序方向
            "sort_directions": self.sort_directions,
            # 账户配置
            "account_type": self.account_type,
            "initial_usdt": self.initial_usdt,
            "margin_rate": self.margin_rate,
            # 手续费配置
            "swap_c_rate": self.swap_c_rate,
            "spot_c_rate": self.spot_c_rate,
            # 最小下单量
            "swap_min_order_limit": self.swap_min_order_limit,
            "spot_min_order_limit": self.spot_min_order_limit,
            # 价格计算
            "avg_price_col": self.avg_price_col,
            # 币种过滤
            "min_kline_num": self.min_kline_num,
            "black_list": self.black_list,
            "white_list": self.white_list,
            # 核心绩效指标
            "cumulative_return": self.cumulative_return,
            "annual_return": self.annual_return,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_start": self.max_drawdown_start,
            "max_drawdown_end": self.max_drawdown_end,
            "sharpe_ratio": self.sharpe_ratio,
            "recovery_rate": self.recovery_rate,
            "recovery_time": self.recovery_time,
            # 交易统计
            "win_periods": self.win_periods,
            "loss_periods": self.loss_periods,
            "win_rate": self.win_rate,
            "avg_return_per_period": self.avg_return_per_period,
            "profit_loss_ratio": self.profit_loss_ratio,
            "max_single_profit": self.max_single_profit,
            "max_single_loss": self.max_single_loss,
            "max_consecutive_wins": self.max_consecutive_wins,
            "max_consecutive_losses": self.max_consecutive_losses,
            "return_std": self.return_std,
            # 周期收益
            "year_return": self.year_return,
            "quarter_return": self.quarter_return,
            "month_return": self.month_return,
            # 资金曲线
            "equity_curve": self.equity_curve,
            # 元数据
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "verified": self.verified,
            "tags": self.tags,
            "notes": self.notes,
            "task_id": self.task_id,
            "task_status": self.task_status,
            "error_message": self.error_message,
        }

    def to_result_dict(self) -> dict[str, Any]:
        """转换为结果字典

        只返回绩效结果，供 MCP 工具返回使用。
        注意: equity_curve 数据量大，需要时通过 compare_equity_curves 工具获取。
        """
        return {
            # 标识
            "id": self.id,
            "name": self.name,
            # 核心绩效
            "cumulative_return": self.cumulative_return,
            "annual_return": self.annual_return,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_start": self.max_drawdown_start,
            "max_drawdown_end": self.max_drawdown_end,
            "sharpe_ratio": self.sharpe_ratio,
            "recovery_rate": self.recovery_rate,
            "recovery_time": self.recovery_time,
            # 交易统计
            "win_periods": self.win_periods,
            "loss_periods": self.loss_periods,
            "win_rate": self.win_rate,
            "avg_return_per_period": self.avg_return_per_period,
            "profit_loss_ratio": self.profit_loss_ratio,
            "max_single_profit": self.max_single_profit,
            "max_single_loss": self.max_single_loss,
            "max_consecutive_wins": self.max_consecutive_wins,
            "max_consecutive_losses": self.max_consecutive_losses,
            "return_std": self.return_std,
            # 周期收益
            "year_return": self.year_return,
            "quarter_return": self.quarter_return,
            "month_return": self.month_return,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Strategy":
        """从字典创建实例"""
        strategy = cls()

        # 基础字段直接赋值
        simple_fields = [
            "id", "name", "description", "start_date", "end_date",
            "leverage", "select_coin_num", "trade_type",
            # 多空配置
            "long_select_coin_num", "short_select_coin_num",
            "long_cap_weight", "short_cap_weight",
            # 持仓配置
            "hold_period", "offset", "market",
            # 账户配置
            "account_type", "initial_usdt", "margin_rate",
            # 手续费配置
            "swap_c_rate", "spot_c_rate",
            # 最小下单量
            "swap_min_order_limit", "spot_min_order_limit",
            # 价格计算
            "avg_price_col",
            # 币种过滤
            "min_kline_num",
            # 绩效指标
            "cumulative_return", "annual_return", "max_drawdown",
            "max_drawdown_start", "max_drawdown_end", "sharpe_ratio",
            "recovery_rate", "recovery_time",
            "win_periods", "loss_periods", "win_rate",
            "avg_return_per_period", "profit_loss_ratio",
            "max_single_profit", "max_single_loss",
            "max_consecutive_wins", "max_consecutive_losses", "return_std",
            "year_return", "quarter_return", "month_return", "equity_curve",
            "created_at", "updated_at", "verified", "notes",
            "task_id", "task_status", "error_message",
        ]

        for field_name in simple_fields:
            if field_name in data:
                setattr(strategy, field_name, data[field_name])

        # JSON 字段特殊处理
        if "factor_list" in data:
            if isinstance(data["factor_list"], list):
                strategy.set_factor_list(data["factor_list"])
            else:
                strategy.factor_list = data["factor_list"]

        if "factor_params" in data:
            if isinstance(data["factor_params"], dict):
                strategy.set_factor_params(data["factor_params"])
            else:
                strategy.factor_params = data["factor_params"]

        if "tags" in data:
            if isinstance(data["tags"], list):
                strategy.set_tags(data["tags"])
            else:
                strategy.tags = data["tags"]

        if "sort_directions" in data:
            if isinstance(data["sort_directions"], dict):
                strategy.set_sort_directions(data["sort_directions"])
            else:
                strategy.sort_directions = data["sort_directions"]

        if "strategy_config" in data:
            if isinstance(data["strategy_config"], list):
                strategy.set_strategy_config(data["strategy_config"])
            else:
                strategy.strategy_config = data["strategy_config"]

        if "black_list" in data:
            if isinstance(data["black_list"], list):
                strategy.set_black_list(data["black_list"])
            else:
                strategy.black_list = data["black_list"]

        if "white_list" in data:
            if isinstance(data["white_list"], list):
                strategy.set_white_list(data["white_list"])
            else:
                strategy.white_list = data["white_list"]

        return strategy
