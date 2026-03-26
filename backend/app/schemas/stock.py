"""Stock Hub schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class StockStatusResponse(BaseModel):
    """Stock Hub 配置状态。"""

    available: bool = Field(description="核心依赖是否可用")
    factor_lib_exists: bool = Field(False, description="因子库目录是否存在")
    section_factor_lib_exists: bool = Field(False, description="截面因子库是否存在")


class StockFactorSummary(BaseModel):
    """因子摘要信息。"""

    name: str = Field(description="因子名称")
    category: str = Field("", description="分类: H财务/技术/截面")
    description: str = Field("", description="因子描述")
    has_add_factor: bool = Field(False, description="是否有 add_factor 方法")


class StockFactorDetail(BaseModel):
    """因子详情。"""

    name: str
    category: str = ""
    description: str = ""
    has_add_factor: bool = False
    source_code: str = Field("", description="Python 源码")
    fin_cols: list[str] = Field(default_factory=list, description="财务列")
    ov_cols: list[str] = Field(default_factory=list, description="行情列")
    example_select: str = Field("", description="选股示例")
    example_filter: str = Field("", description="过滤示例")


class BacktestSourceInfo(BaseModel):
    """可用回测数据源信息。"""

    name: str = Field(description="回测名称")
    factor_count: int = Field(0, description="因子数量")
    modified_time: str = Field("", description="最后修改时间")


class AvailableBacktestsResponse(BaseModel):
    """可用回测数据源列表。"""

    backtests: list[BacktestSourceInfo] = Field(default_factory=list)
    total: int = 0


class CachedFactorInfo(BaseModel):
    """缓存因子信息。"""

    name: str
    display_name: str = ""
    file_size: int = 0


class EnhancedAnalysisRequest(BaseModel):
    """增强单因子分析请求。"""

    factor_name: str = Field(description="因子名称")
    period_offset_list: list[str] = Field(
        default_factory=lambda: ["5_0"], description="分析周期列表"
    )
    rebalance_time: str = Field("0955", description="换仓时间")
    bins: int = Field(10, ge=2, le=20, description="分组数")
    backtest_name: Optional[str] = Field(None, description="回测数据源名称")


class AnalysisResultResponse(BaseModel):
    """分析结果。"""

    factor_name: str
    score: float = 0.0
    ic_mean: float = 0.0
    ic_std: float = 0.0
    icir: float = 0.0
    abs_icir: float = 0.0
    ic_ratio: str = ""
    start_date: str = ""
    end_date: str = ""
    period_offset_list: list[str] = Field(default_factory=list)
    rebalance_time: str = ""
    group_values: dict[str, float] = Field(default_factory=dict)
    style_exposure: dict[str, float] = Field(default_factory=dict)
    html_path: str = ""
    elapsed_seconds: float = 0.0


class DualAnalysisRequest(BaseModel):
    """双因子分析请求。"""

    main_factor: str = Field(description="主因子名称")
    sub_factor: str = Field(description="次因子名称")
    period_offset_list: list[str] = Field(
        default_factory=lambda: ["5_0"], description="分析周期列表"
    )
    rebalance_time: str = Field("0955", description="换仓时间")
    bins: int = Field(5, ge=2, le=20, description="分组数")
    backtest_name: Optional[str] = Field(None, description="回测数据源名称")


class DualAnalysisResultResponse(BaseModel):
    """双因子分析结果。"""

    main_factor: str
    sub_factor: str
    heatmaps: dict = Field(default_factory=dict, description="热力图数据")
    style_exposure: dict = Field(default_factory=dict, description="风格暴露对比")
    elapsed_seconds: float = 0.0


class BatchAnalysisRequest(BaseModel):
    """批量因子分析请求。"""

    period_offset_list: list[str] = Field(
        default_factory=lambda: ["5_0"]
    )
    rebalance_time: str = Field("0955")
    bins: int = Field(10, ge=2, le=20)
    max_workers: int = Field(3, ge=1, le=10)
    skip_existing: bool = Field(True)
    backtest_name: Optional[str] = None
