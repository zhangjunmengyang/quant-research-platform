"""
回测实盘对比服务

对比回测和实盘的资金曲线、选币结果。
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd

from ..utils.plot_functions import (
    draw_equity_curve_plotly,
    draw_coins_difference,
    draw_coins_table,
    merge_html_flexible,
)
from ..utils.data_functions import (
    process_equity_data,
    process_coin_selection_data,
    process_backtest_trading_factors,
)

logger = logging.getLogger(__name__)


@dataclass
class BacktestComparisonResult:
    """回测实盘对比结果"""
    backtest_name: str
    start_time: str
    end_time: str
    equity_similarity: Optional[float] = None
    coin_selection_similarity: Optional[float] = None
    html_path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class FactorComparisonResult:
    """因子值对比结果"""
    backtest_name: str
    coin: str
    factors: List[str] = field(default_factory=list)
    html_path: Optional[str] = None
    error: Optional[str] = None


class BacktestComparisonService:
    """
    回测实盘对比服务

    对比回测和实盘的资金曲线、选币结果、因子值。
    """

    def __init__(self, data_path: Optional[Path] = None):
        """
        初始化服务

        Args:
            data_path: 数据根路径
        """
        self.data_path = data_path or Path("data")
        self.backtest_path = self.data_path / "backtest_results"
        self.output_path = self.data_path / "analysis_results" / "backtest_comparison"
        self.output_path.mkdir(parents=True, exist_ok=True)

    def compare(
        self,
        backtest_name: str,
        start_time: str,
        end_time: str
    ) -> BacktestComparisonResult:
        """
        执行回测实盘对比

        Args:
            backtest_name: 回测策略名称
            start_time: 对比开始时间
            end_time: 对比结束时间

        Returns:
            对比结果
        """
        result = BacktestComparisonResult(
            backtest_name=backtest_name,
            start_time=start_time,
            end_time=end_time
        )

        try:
            fig_list = []

            # 1. 资金曲线对比
            equity_data = process_equity_data(
                self.data_path, backtest_name, start_time, end_time
            )

            left_axis = {
                'Backtest NAV': 'backtest_nav',
                'Live NAV': 'live_nav',
                'Comparison NAV': 'comparison_nav'
            }
            fig = draw_equity_curve_plotly(
                equity_data, left_axis, date_col='time',
                title='Backtest vs Live Equity Curve'
            )
            fig_list.append(fig)

            # 2. 选币结果对比
            coin_selection_data = process_coin_selection_data(
                self.data_path, backtest_name, start_time, end_time
            )

            left_axis = {
                f'Backtest {backtest_name} Count': f'backtest_{backtest_name}_count',
                f'Live {backtest_name} Count': f'live_{backtest_name}_count',
                'Overlap Count': 'overlap_count',
            }

            similarity_mean = coin_selection_data['similarity'].mean().round(2)
            result.coin_selection_similarity = float(similarity_mean)

            right_axis = {
                f'Similarity (Mean: {similarity_mean})': 'similarity',
            }

            fig = draw_coins_difference(
                coin_selection_data, left_axis,
                date_col='candle_begin_time',
                right_axis=right_axis,
                title='Backtest vs Live Coin Selection'
            )
            fig_list.append(fig)

            # 3. 选币明细表
            table_data = coin_selection_data[
                ['candle_begin_time', 'backtest_only', 'live_only']
            ].copy()
            table_data['candle_begin_time'] = table_data['candle_begin_time'].map(
                lambda x: x.strftime('%Y-%m-%d %H:00:00')
            )
            table_data['backtest_only'] = table_data['backtest_only'].apply(
                lambda x: ', '.join(sorted(x)) if isinstance(x, set) else x
            )
            table_data['live_only'] = table_data['live_only'].apply(
                lambda x: ', '.join(sorted(x)) if isinstance(x, set) else x
            )
            table_data.replace('', np.nan, inplace=True)
            table_data = table_data.dropna(subset=['backtest_only', 'live_only'], how='all')
            table_data.replace(np.nan, '', inplace=True)

            fig = draw_coins_table(
                table_data, table_data.columns, title='Coin Selection Details'
            )
            fig_list.append(fig)

            # 生成报告
            output_dir = self.output_path / backtest_name
            output_dir.mkdir(parents=True, exist_ok=True)
            html_name = f'{backtest_name}_comparison.html'
            html_path = output_dir / html_name

            merge_html_flexible(
                fig_list, html_path,
                title=f'{backtest_name} Backtest vs Live Comparison',
                show=False
            )

            result.html_path = str(html_path)
            logger.info(f"Backtest comparison completed: {backtest_name}")

        except Exception as e:
            logger.error(f"Backtest comparison failed: {e}")
            result.error = str(e)

        return result

    def compare_factor_values(
        self,
        backtest_name: str,
        coin: str,
        factor_names: Optional[List[str]] = None
    ) -> FactorComparisonResult:
        """
        对比单个币种的因子值

        Args:
            backtest_name: 回测策略名称
            coin: 币种名称
            factor_names: 因子名称列表（为空则自动检测）

        Returns:
            对比结果
        """
        result = FactorComparisonResult(
            backtest_name=backtest_name,
            coin=coin
        )

        try:
            # 标准化币种名称
            coin = coin.strip().upper()
            if not coin.endswith('USDT'):
                coin += 'USDT'
            coin = coin.replace('-', '')

            # 自动检测因子列表
            if factor_names is None:
                cache_path = self.data_path / 'cache'
                factor_names = [
                    f[7:-4] for f in cache_path.glob('factor_*.pkl')
                ]

            result.factors = factor_names

            # 获取因子对比数据
            from ..utils.data_functions import process_backtest_trading_factors
            factors_data = process_backtest_trading_factors(
                self.data_path, factor_names, backtest_name, coin
            )

            if isinstance(factors_data, bool) and not factors_data:
                result.error = f"Coin {coin} not found in data"
                return result

            # 绘图
            from ..utils.plot_functions import draw_line_plotly
            col_right_axis = [
                col for col in factors_data.columns
                if col not in ['live_close(left)', 'backtest_close(left)']
            ]
            fig = draw_line_plotly(
                x=factors_data.index,
                y1=factors_data[['live_close(left)', 'backtest_close(left)']],
                y2=factors_data[col_right_axis],
                if_log=True,
                title=f'Backtest vs Live {coin} Factor Values'
            )

            # 输出
            output_dir = self.output_path / "factor_comparison"
            output_dir.mkdir(parents=True, exist_ok=True)
            html_name = f'{backtest_name}_{coin}_factor_comparison.html'
            html_path = output_dir / html_name

            merge_html_flexible([fig], html_path, title='', show=False)

            result.html_path = str(html_path)
            logger.info(f"Factor comparison completed: {backtest_name} - {coin}")

        except Exception as e:
            logger.error(f"Factor comparison failed: {e}")
            result.error = str(e)

        return result


# 单例模式
_backtest_comparison_service: Optional[BacktestComparisonService] = None


def get_backtest_comparison_service() -> BacktestComparisonService:
    """获取回测对比服务单例"""
    global _backtest_comparison_service
    if _backtest_comparison_service is None:
        _backtest_comparison_service = BacktestComparisonService()
    return _backtest_comparison_service


def reset_backtest_comparison_service() -> None:
    """重置服务单例"""
    global _backtest_comparison_service
    _backtest_comparison_service = None
