"""回测配置模型"""
from typing import Optional, List, Tuple
from pydantic import BaseModel, Field


class FactorConfig(BaseModel):
    """单个因子配置"""
    name: str                         # 因子名称
    ascending: bool = True            # 是否升序排列（True=选小的）
    param: str = ""                   # 因子参数
    weight: float = 1.0               # 因子权重


class FilterConfig(BaseModel):
    """单个过滤条件"""
    name: str                         # 因子名称
    param: Optional[str] = None       # 因子参数
    condition: str                    # 过滤条件，如 "val:>0,<=100"
    keep: bool = True                 # True=保留满足条件的


class StrategyConfig(BaseModel):
    """单个策略配置"""
    name: str = "默认策略"
    hold_period: str = "W"            # W=周, M=月, W2=双周
    offset_list: List[int] = [0]      # 偏移量列表
    select_num: int = 3               # 选股数量
    cap_weight: float = 1.0           # 市值权重
    rebalance_time: str = "open"      # open/close
    factor_list: List[FactorConfig] = []
    filter_list: List[FilterConfig] = []


class BacktestRequest(BaseModel):
    """回测请求模型"""
    backtest_name: str = "AI框架回测"
    start_date: str = "2024-01-01"
    end_date: Optional[str] = None
    strategies: List[StrategyConfig] = Field(default_factory=lambda: [StrategyConfig()])
    performance_mode: str = "ECO"     # ECO/BAL/MAX
    stay_real: bool = True
    excluded_boards: List[str] = Field(default_factory=lambda: ["bj"])
    days_listed: int = 250
    total_cap_usage: float = 1.0
    initial_cash: float = 1_0000_0000
    c_rate: float = 1.2 / 10000
    t_rate: float = 1 / 1000
    stock_timing_order_price: int = 5


class BacktestResult(BaseModel):
    """回测结果模型"""
    status: str                       # ok / error
    message: str = ""
    result_path: Optional[str] = None # 结果文件夹路径
    log_output: str = ""              # 回测日志输出
    summary: Optional[dict] = None    # 回测摘要数据
