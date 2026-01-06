"""
资金曲线相关性服务

计算多策略资金曲线涨跌幅之间的相关性。
"""

import logging
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from ..utils.plot_functions import draw_params_heatmap_plotly, merge_html_flexible
from ..utils.data_functions import curve_difference_all_pairs

logger = logging.getLogger(__name__)


@dataclass
class EquityCorrelationResult:
    """资金曲线相关性分析结果"""
    strategies: List[str] = field(default_factory=list)
    correlation_matrix: Optional[pd.DataFrame] = None
    html_path: Optional[str] = None
    error: Optional[str] = None


class EquityCorrelationService:
    """
    资金曲线相关性服务

    计算多策略资金曲线涨跌幅之间的相关性。
    """

    def __init__(self, data_path: Optional[Path] = None):
        """
        初始化服务

        Args:
            data_path: 数据根路径
        """
        self.data_path = data_path or Path("data")
        self.output_path = self.data_path / "analysis_results" / "equity_correlation"
        self.output_path.mkdir(parents=True, exist_ok=True)

    def analyze(self, strategy_list: List[str]) -> EquityCorrelationResult:
        """
        分析多策略资金曲线相关性

        Args:
            strategy_list: 策略名称列表

        Returns:
            分析结果
        """
        result = EquityCorrelationResult(strategies=strategy_list)

        try:
            logger.info(f"Starting equity correlation analysis for {len(strategy_list)} strategies")

            # 获取所有策略的资金曲线
            curve_return = curve_difference_all_pairs(self.data_path, strategy_list)

            # 检查策略对数据有效性
            strategy_pairs = list(combinations(strategy_list, 2))
            for strat1, strat2 in strategy_pairs:
                pair_df = curve_return[[strat1, strat2]].copy()
                pair_df = pair_df.dropna()
                if pair_df.empty:
                    logger.warning(f"{strat1} and {strat2} have no overlapping backtest period")

            # 计算相关性矩阵
            curve_corr = curve_return.corr()
            curve_corr = curve_corr.round(4)
            curve_corr.replace(np.nan, '', inplace=True)

            result.correlation_matrix = curve_corr

            # 绘制热力图
            fig = draw_params_heatmap_plotly(
                curve_corr, 'Multi-Strategy Equity Curve Correlation'
            )

            html_name = 'equity_curve_correlation.html'
            html_path = self.output_path / html_name
            merge_html_flexible([fig], html_path, show=False)

            result.html_path = str(html_path)
            logger.info("Equity correlation analysis completed")

        except Exception as e:
            logger.error(f"Equity correlation analysis failed: {e}")
            result.error = str(e)

        return result


# 单例模式
_equity_correlation_service: Optional[EquityCorrelationService] = None


def get_equity_correlation_service() -> EquityCorrelationService:
    """获取资金曲线相关性服务单例"""
    global _equity_correlation_service
    if _equity_correlation_service is None:
        _equity_correlation_service = EquityCorrelationService()
    return _equity_correlation_service


def reset_equity_correlation_service() -> None:
    """重置服务单例"""
    global _equity_correlation_service
    _equity_correlation_service = None
