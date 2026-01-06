"""
任务管理 API Schema

定义回测任务单和执行记录的请求/响应模型。
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# =============================================================================
# 任务单 (BacktestTask) Schema
# =============================================================================


class TaskConfigBase(BaseModel):
    """任务配置基础模型 - 与 BacktestRequest 保持一致"""

    name: str = Field(..., description="回测名称")
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")
    account_type: str = Field(default="统一账户", description="账户类型")
    initial_usdt: float = Field(default=10000, description="初始资金")
    leverage: float = Field(default=1.0, description="杠杆倍数")
    margin_rate: float = Field(default=0.05, description="维持保证金率")
    swap_c_rate: float = Field(default=0.0006, description="合约手续费率")
    spot_c_rate: float = Field(default=0.001, description="现货手续费率")
    swap_min_order_limit: float = Field(default=5, description="合约最小下单量")
    spot_min_order_limit: float = Field(default=10, description="现货最小下单量")
    avg_price_col: str = Field(default="avg_price_1m", description="均价计算列")
    min_kline_num: int = Field(default=0, description="最少上市K线数")
    black_list: List[str] = Field(default_factory=list, description="黑名单")
    white_list: List[str] = Field(default_factory=list, description="白名单")
    strategy_list: List[Dict[str, Any]] = Field(
        default_factory=list, description="策略配置列表"
    )
    re_timing: Optional[Dict[str, Any]] = Field(None, description="再择时配置")


class CreateTaskRequest(BaseModel):
    """创建任务单请求"""

    name: str = Field(..., description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    config: TaskConfigBase = Field(..., description="回测配置")
    tags: Optional[List[str]] = Field(None, description="标签")
    notes: Optional[str] = Field(None, description="备注")


class UpdateTaskRequest(BaseModel):
    """更新任务单请求"""

    name: Optional[str] = Field(None, description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    config: Optional[TaskConfigBase] = Field(None, description="回测配置")
    tags: Optional[List[str]] = Field(None, description="标签")
    notes: Optional[str] = Field(None, description="备注")


class DuplicateTaskRequest(BaseModel):
    """复制任务单请求"""

    new_name: str = Field(..., description="新任务名称")


class TaskResponse(BaseModel):
    """任务单响应"""

    id: str
    name: str
    description: Optional[str] = None
    config: str  # JSON 字符串
    created_at: str
    updated_at: str
    tags: Optional[str] = None  # JSON 字符串
    notes: Optional[str] = None
    execution_count: int = 0
    last_execution_at: Optional[str] = None


class TaskListResponse(BaseModel):
    """任务列表响应"""

    items: List[TaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# 执行记录 (TaskExecution) Schema
# =============================================================================


class ExecuteTaskRequest(BaseModel):
    """执行任务请求"""

    config_override: Optional[Dict[str, Any]] = Field(
        None, description="配置覆盖（可选）"
    )


class ExecutionResponse(BaseModel):
    """执行记录响应"""

    id: str
    task_id: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: float = 0.0
    message: Optional[str] = None

    # 因子信息
    factor_list: Optional[str] = None
    factor_params: Optional[str] = None

    # 配置快照
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    leverage: Optional[float] = None
    account_type: Optional[str] = None
    initial_usdt: Optional[float] = None
    hold_period: Optional[str] = None
    long_select_coin_num: Optional[float] = None
    short_select_coin_num: Optional[float] = None

    # 绩效指标
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

    # 周期收益
    year_return: Optional[str] = None
    quarter_return: Optional[str] = None
    month_return: Optional[str] = None

    # 资金曲线
    equity_curve: Optional[str] = None

    # 错误信息
    error_message: Optional[str] = None

    # 策略库关联
    strategy_id: Optional[str] = None


class ExecutionListResponse(BaseModel):
    """执行记录列表响应"""

    items: List[ExecutionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ExecutionSubmitResponse(BaseModel):
    """执行提交响应"""

    execution_id: str
    status: str
    message: str


class TaskStatsResponse(BaseModel):
    """任务统计响应"""

    total: int
    completed: int
    failed: int
    running: int
    pending: int
    avg_annual_return: Optional[float] = None
    avg_sharpe_ratio: Optional[float] = None
    best_annual_return: Optional[float] = None
    worst_annual_return: Optional[float] = None


class ExportToStrategyRequest(BaseModel):
    """导出到策略库请求"""

    strategy_name: str = Field(..., description="策略名称")
    description: Optional[str] = Field(None, description="策略描述")


class ExportToStrategyResponse(BaseModel):
    """导出到策略库响应"""

    strategy_id: str
    message: str
