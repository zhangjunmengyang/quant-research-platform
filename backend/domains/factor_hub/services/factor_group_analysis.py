"""
因子分箱分析服务

分析因子在不同分位组的收益表现，生成分箱分析报告。

设计原则:
- 自包含: 不依赖外部预计算的缓存文件
- 按需计算: 使用 DataLoader 和 FactorCalculator 直接从原始数据计算
- 与回测引擎一致: 使用相同的因子计算逻辑确保结果一致性
- 异步友好: 提供异步方法避免阻塞事件循环
"""

import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Literal, Any
import logging

import pandas as pd
import numpy as np

from ..core.config import get_config_loader

logger = logging.getLogger(__name__)


@dataclass
class FactorGroupAnalysisResult:
    """因子分箱分析结果"""
    factor_name: str
    bins: int
    method: str
    data_type: str
    group_curve: Optional[pd.DataFrame] = None
    bar_data: Optional[pd.DataFrame] = None
    labels: List[str] = field(default_factory=list)
    html_path: Optional[str] = None
    error: Optional[str] = None


class FactorGroupAnalysisService:
    """
    因子分箱分析服务

    分析因子在不同分位组的收益表现，支持分位数分箱和等宽分箱两种方法。

    特点:
    - 自包含设计，不依赖外部预计算的缓存文件
    - 使用 DataLoader 和 FactorCalculator 直接从原始数据计算
    - 与回测引擎使用相同的因子计算逻辑
    """

    def __init__(self, data_path: Optional[Path] = None):
        """
        初始化服务

        Args:
            data_path: 数据根路径，默认使用配置中的路径
        """
        config_loader = get_config_loader()
        self.data_path = data_path or config_loader.data_dir
        self.output_path = self.data_path / "analysis_results" / "factor_analysis"
        self.output_path.mkdir(parents=True, exist_ok=True)

        # 延迟初始化数据服务
        self._data_loader = None
        self._factor_calculator = None

    @property
    def data_loader(self):
        """获取数据加载器（延迟初始化）"""
        if self._data_loader is None:
            from domains.engine.services import get_data_loader
            self._data_loader = get_data_loader()
        return self._data_loader

    @property
    def factor_calculator(self):
        """获取因子计算器（延迟初始化）"""
        if self._factor_calculator is None:
            from domains.engine.services import get_factor_calculator
            self._factor_calculator = get_factor_calculator()
        return self._factor_calculator

    def _load_kline_data(
        self,
        symbols: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        data_type: str = 'all'
    ) -> pd.DataFrame:
        """
        加载 K 线数据

        直接从原始数据加载，确保数据独立性和一致性。

        Args:
            symbols: 币种列表，默认全部
            start_date: 开始日期
            end_date: 结束日期
            data_type: 数据类型 ('spot', 'swap', 'all')

        Returns:
            合并的 K 线数据 DataFrame
        """
        logger.info("Loading kline data from raw source...")
        return self._build_kline_data(symbols, start_date, end_date, data_type)

    def _build_kline_data(
        self,
        symbols: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        data_type: str = 'all'
    ) -> pd.DataFrame:
        """
        从原始数据构建 K 线数据

        Args:
            symbols: 币种列表，默认全部
            start_date: 开始日期
            end_date: 结束日期
            data_type: 数据类型 ('spot', 'swap', 'all')

        Returns:
            合并的 K 线数据 DataFrame
        """
        dfs = []

        # 加载合约数据
        if data_type in ('swap', 'all'):
            swap_data = self.data_loader.load_swap_data()
            swap_symbols = symbols or list(swap_data.keys())
            for symbol in swap_symbols:
                if symbol not in swap_data:
                    continue
                df = swap_data[symbol].copy()
                df['symbol'] = symbol
                df['is_spot'] = 0
                df['symbol_swap'] = symbol
                df['symbol_spot'] = ''

                # 时间过滤
                if start_date:
                    df = df[df['candle_begin_time'] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df['candle_begin_time'] <= pd.to_datetime(end_date)]

                # 计算 next_close
                df['next_close'] = df['close'].shift(-1)

                if not df.empty:
                    dfs.append(df)

        # 加载现货数据
        if data_type in ('spot', 'all'):
            spot_data = self.data_loader.load_spot_data()
            spot_symbols = symbols or list(spot_data.keys())
            for symbol in spot_symbols:
                if symbol not in spot_data:
                    continue
                df = spot_data[symbol].copy()
                df['symbol'] = symbol
                df['is_spot'] = 1
                df['symbol_spot'] = symbol
                df['symbol_swap'] = ''

                # 时间过滤
                if start_date:
                    df = df[df['candle_begin_time'] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df['candle_begin_time'] <= pd.to_datetime(end_date)]

                # 计算 next_close
                df['next_close'] = df['close'].shift(-1)

                if not df.empty:
                    dfs.append(df)

        if not dfs:
            return pd.DataFrame()

        result = pd.concat(dfs, ignore_index=True)
        result.sort_values(by=['candle_begin_time', 'symbol', 'is_spot'], inplace=True)
        result.reset_index(drop=True, inplace=True)

        return result

    def _compute_factor_for_kline(
        self,
        factor_name: str,
        param: Any,
        kline_df: pd.DataFrame
    ) -> pd.Series:
        """
        计算因子数据

        直接计算，确保每次分析的独立性。

        Args:
            factor_name: 因子名称
            param: 因子参数
            kline_df: K 线数据

        Returns:
            因子数据 Series
        """
        logger.info(f"Computing factor {factor_name}({param})...")
        return self._compute_factor(factor_name, param, kline_df)

    def _compute_factor(
        self,
        factor_name: str,
        param: Any,
        kline_df: pd.DataFrame
    ) -> pd.Series:
        """
        按需计算因子

        使用与回测引擎相同的因子计算逻辑。

        Args:
            factor_name: 因子名称
            param: 因子参数
            kline_df: K 线数据

        Returns:
            因子值 Series
        """
        factor_col = f"factor_{factor_name}_{param}"

        # 按币种分组计算因子
        result_series_list = []

        for symbol in kline_df['symbol'].unique():
            symbol_df = kline_df[kline_df['symbol'] == symbol].copy()
            if symbol_df.empty:
                continue

            # 使用 FactorCalculator 计算因子
            symbol_df = self.factor_calculator.add_factors_to_df(
                symbol_df,
                {factor_name: [param]}
            )

            factor_col_name = f'{factor_name}_{param}'
            if factor_col_name in symbol_df.columns:
                result_series_list.append(symbol_df[factor_col_name])

        if not result_series_list:
            return pd.Series(np.nan, index=kline_df.index, name=factor_col)

        # 合并所有币种的因子值
        result = pd.concat(result_series_list)
        result.name = factor_col
        return result

    def _filter_by_data_type(
        self,
        df: pd.DataFrame,
        data_type: Literal['spot', 'swap', 'all']
    ) -> pd.DataFrame:
        """
        按数据类型过滤数据

        Args:
            df: 原始数据
            data_type: 数据类型 ('spot', 'swap', 'all')

        Returns:
            过滤后的数据
        """
        if data_type == 'spot':
            filtered = df[df['is_spot'] == 1]
        elif data_type == 'swap':
            filtered = df[(df['is_spot'] == 0) & (df['symbol_swap'] != '')]
        elif data_type == 'all':
            filtered = df
        else:
            raise ValueError(f"Invalid data_type: {data_type}")

        if filtered.empty:
            raise ValueError(f"No data available for data_type: {data_type}")

        return filtered

    def _calculate_group_returns(
        self,
        df: pd.DataFrame,
        factor_col: str,
        bins: int,
        method: str
    ) -> Tuple[List[str], pd.DataFrame]:
        """
        计算分组收益

        Args:
            df: 数据DataFrame
            factor_col: 因子列名
            bins: 分组数量
            method: 分箱方法 'pct' 或 'val'

        Returns:
            (标签列表, 分组收益DataFrame)
        """
        df = df.copy()
        df['total_coins'] = df.groupby('candle_begin_time')['symbol'].transform('size')
        valid_df = df[df['total_coins'] >= bins].copy()

        if valid_df.empty:
            raise ValueError("Not enough data for grouping")

        if method == 'pct':
            valid_df['rank'] = valid_df.groupby('candle_begin_time')[factor_col].rank(method='first')
            labels = [f'Group_{i}' for i in range(1, bins + 1)]
            valid_df['groups'] = valid_df.groupby('candle_begin_time')['rank'].transform(
                lambda x: pd.qcut(x, q=bins, labels=labels, duplicates='drop')
            )
        elif method == 'val':
            all_values = df[factor_col].dropna()
            if all_values.empty:
                raise ValueError("Factor data is empty")
            _, bins_edges = pd.cut(all_values, bins=bins, retbins=True)
            labels = []
            for i in range(len(bins_edges) - 1):
                left_edge = round(bins_edges[i], 4)
                right_edge = round(bins_edges[i + 1], 4)
                left_bracket = '[' if i == 0 else '('
                labels.append(f'Group_{i + 1}{left_bracket}{left_edge}-{right_edge}]')
            valid_df['groups'] = pd.cut(
                valid_df[factor_col],
                bins=bins_edges,
                labels=labels,
                include_lowest=True,
                duplicates='drop'
            )
        else:
            raise ValueError(f"Invalid method: {method}")

        valid_df['ret_next'] = valid_df['next_close'] / valid_df['close'] - 1
        group_returns = valid_df.groupby(['candle_begin_time', 'groups'])['ret_next'].mean().to_frame()
        group_returns.reset_index('groups', inplace=True)
        group_returns['groups'] = group_returns['groups'].astype(str)

        return labels, group_returns

    def analyze_factor(
        self,
        factor_name: str,
        param: Any,
        data_type: Literal['spot', 'swap', 'all'] = 'swap',
        bins: int = 5,
        method: Literal['pct', 'val'] = 'pct',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        symbols: Optional[List[str]] = None,
        filter_configs: Optional[List[Tuple]] = None,
        generate_html: bool = False
    ) -> FactorGroupAnalysisResult:
        """
        分析单个因子

        自包含设计: 自动从原始数据加载 K 线并计算因子，无需预计算缓存。

        Args:
            factor_name: 因子名称（不含 .py 后缀）
            param: 因子参数
            data_type: 数据类型 ('spot', 'swap', 'all')
            bins: 分组数量
            method: 分箱方法 ('pct': 分位数, 'val': 等宽)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            symbols: 指定币种列表，默认全部
            filter_configs: 过滤配置列表
            generate_html: 是否生成HTML报告

        Returns:
            分析结果
        """
        # 处理因子名称（移除可能的 .py 后缀）
        if factor_name.endswith('.py'):
            factor_name = factor_name[:-3]

        factor_col = f"factor_{factor_name}_{param}"
        result = FactorGroupAnalysisResult(
            factor_name=factor_col,
            bins=bins,
            method=method,
            data_type=data_type
        )

        try:
            # 加载 K 线数据
            logger.info(f"Loading kline data for data_type={data_type}, date range: {start_date} to {end_date}")
            kline_df = self._load_kline_data(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                data_type=data_type
            )

            if kline_df.empty:
                raise ValueError("No kline data available")

            # 计算因子数据
            factor_data = self._compute_factor_for_kline(factor_name, param, kline_df)

            # 将因子数据合并到 K 线数据
            # 需要确保索引对齐
            if len(factor_data) == len(kline_df):
                kline_df[factor_col] = factor_data.values
            else:
                # 如果长度不匹配，尝试按索引合并
                kline_df[factor_col] = factor_data.reindex(kline_df.index).values

            # 按数据类型过滤
            filtered_df = self._filter_by_data_type(kline_df, data_type)

            # 移除因子值为 NaN 的行
            filtered_df = filtered_df.dropna(subset=[factor_col])

            if filtered_df.empty:
                raise ValueError(f"No valid factor data for {factor_col}")

            # 应用过滤条件
            if filter_configs:
                # TODO: 实现过滤逻辑
                pass

            # 计算分组收益
            labels, group_returns = self._calculate_group_returns(
                filtered_df, factor_col, bins, method
            )

            # 构建分组净值曲线
            group_returns = group_returns.reset_index()
            group_returns = pd.pivot(
                group_returns,
                index='candle_begin_time',
                columns='groups',
                values='ret_next'
            )
            group_curve = (group_returns + 1).cumprod()
            group_curve = group_curve[labels]

            # 计算多空收益
            first_bin = labels[0]
            last_bin = labels[-1]
            if group_curve[first_bin].iloc[-1] > group_curve[last_bin].iloc[-1]:
                ls_ret = (group_returns[first_bin] - group_returns[last_bin]) / 2
            else:
                ls_ret = (group_returns[last_bin] - group_returns[first_bin]) / 2

            group_curve['long_short_nav'] = (ls_ret + 1).cumprod()
            group_curve = group_curve.ffill()

            # 重采样到日级别
            group_curve = group_curve.resample('D').last()

            # 准备柱状图数据
            bar_df = group_curve.iloc[-1].reset_index()
            bar_df.columns = ['groups', 'asset']

            result.group_curve = group_curve
            result.bar_data = bar_df
            result.labels = labels

            # 生成HTML报告
            if generate_html:
                try:
                    html_path = self._generate_html_report(result)
                    # 返回相对于 data/analysis_results 的路径，以便 API 可以正确找到
                    result.html_path = f"factor_analysis/{html_path.name}"
                except Exception as html_err:
                    logger.warning(f"Failed to generate HTML report: {html_err}")

            logger.info(f"Factor group analysis completed: {factor_col}")

        except Exception as e:
            logger.error(f"Factor group analysis failed: {e}")
            result.error = str(e)

        return result

    def _generate_html_report(self, result: FactorGroupAnalysisResult) -> Path:
        """
        生成HTML分析报告

        Args:
            result: 分析结果

        Returns:
            HTML文件路径
        """
        # 从 engine 导入绘图函数（已迁移到共享层）
        from domains.engine.chart_utils import (
            draw_bar_plotly,
            draw_line_plotly,
            merge_html_flexible,
        )

        fig_list = []

        # 绘制分组净值柱状图
        is_spot_only = result.data_type == 'spot'
        display_labels = result.labels.copy()
        if not is_spot_only:
            display_labels.append('long_short_nav')

        bar_df = result.bar_data[result.bar_data['groups'].isin(display_labels)]

        factor_labels = ['Min Value'] + [''] * (result.bins - 2) + ['Max Value']
        if not is_spot_only:
            factor_labels.append('')
        bar_df = bar_df.copy()
        bar_df['value_label'] = factor_labels[:len(bar_df)]

        group_fig = draw_bar_plotly(
            x=bar_df['groups'],
            y=bar_df['asset'],
            text_data=bar_df['value_label'],
            title='Group NAV'
        )
        fig_list.append(group_fig)

        # 绘制分组净值曲线
        group_cols = [col for col in result.group_curve.columns if 'Group_' in col]
        y2_data = result.group_curve[['long_short_nav']] if not is_spot_only else pd.DataFrame()
        line_fig = draw_line_plotly(
            x=result.group_curve.index,
            y1=result.group_curve[group_cols],
            y2=y2_data,
            if_log=True,
            title='Group NAV Curve'
        )
        fig_list.append(line_fig)

        # 生成HTML
        start_time = result.group_curve.index[0].strftime('%Y/%m/%d')
        end_time = result.group_curve.index[-1].strftime('%Y/%m/%d')
        html_path = self.output_path / f'{result.factor_name}_analysis.html'
        title = f'{result.factor_name} Analysis Report ({start_time} - {end_time})'

        merge_html_flexible(fig_list, html_path, title=title, show=False)

        return html_path

    def analyze_multiple_factors(
        self,
        factor_dict: Dict[str, List[Any]],
        data_type: Literal['spot', 'swap', 'all'] = 'swap',
        bins: int = 5,
        method: Literal['pct', 'val'] = 'pct',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        symbols: Optional[List[str]] = None,
        filter_configs: Optional[List[Tuple]] = None
    ) -> List[FactorGroupAnalysisResult]:
        """
        分析多个因子

        Args:
            factor_dict: 因子字典 {因子名: [参数列表]}
            data_type: 数据类型 ('spot', 'swap', 'all')
            bins: 分组数量
            method: 分箱方法
            start_date: 开始日期
            end_date: 结束日期
            symbols: 指定币种列表
            filter_configs: 过滤配置

        Returns:
            分析结果列表
        """
        results = []
        for factor_name, params in factor_dict.items():
            for param in params:
                result = self.analyze_factor(
                    factor_name=factor_name,
                    param=param,
                    data_type=data_type,
                    bins=bins,
                    method=method,
                    start_date=start_date,
                    end_date=end_date,
                    symbols=symbols,
                    filter_configs=filter_configs
                )
                results.append(result)
        return results

    # ============================================
    # 异步方法 - 避免阻塞事件循环
    # ============================================

    async def analyze_factor_async(
        self,
        factor_name: str,
        param: Any,
        data_type: Literal['spot', 'swap', 'all'] = 'swap',
        bins: int = 5,
        method: Literal['pct', 'val'] = 'pct',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        symbols: Optional[List[str]] = None,
        filter_configs: Optional[List[Tuple]] = None,
        generate_html: bool = False
    ) -> FactorGroupAnalysisResult:
        """
        异步分析单个因子

        将同步的分析操作移到线程池执行，避免阻塞事件循环。

        Args:
            factor_name: 因子名称
            param: 因子参数
            data_type: 数据类型
            bins: 分组数量
            method: 分箱方法
            start_date: 开始日期
            end_date: 结束日期
            symbols: 指定币种列表
            filter_configs: 过滤配置
            generate_html: 是否生成HTML报告

        Returns:
            分析结果
        """
        return await asyncio.to_thread(
            self.analyze_factor,
            factor_name,
            param,
            data_type,
            bins,
            method,
            start_date,
            end_date,
            symbols,
            filter_configs,
            generate_html,
        )

    async def analyze_multiple_factors_async(
        self,
        factor_dict: Dict[str, List[Any]],
        data_type: Literal['spot', 'swap', 'all'] = 'swap',
        bins: int = 5,
        method: Literal['pct', 'val'] = 'pct',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        symbols: Optional[List[str]] = None,
        filter_configs: Optional[List[Tuple]] = None
    ) -> List[FactorGroupAnalysisResult]:
        """
        异步分析多个因子

        将同步的分析操作移到线程池执行，避免阻塞事件循环。

        Args:
            factor_dict: 因子字典 {因子名: [参数列表]}
            data_type: 数据类型
            bins: 分组数量
            method: 分箱方法
            start_date: 开始日期
            end_date: 结束日期
            symbols: 指定币种列表
            filter_configs: 过滤配置

        Returns:
            分析结果列表
        """
        return await asyncio.to_thread(
            self.analyze_multiple_factors,
            factor_dict,
            data_type,
            bins,
            method,
            start_date,
            end_date,
            symbols,
            filter_configs,
        )


# 单例模式
_factor_group_analysis_service: Optional[FactorGroupAnalysisService] = None


def get_factor_group_analysis_service() -> FactorGroupAnalysisService:
    """获取因子分箱分析服务单例"""
    global _factor_group_analysis_service
    if _factor_group_analysis_service is None:
        _factor_group_analysis_service = FactorGroupAnalysisService()
    return _factor_group_analysis_service


def reset_factor_group_analysis_service() -> None:
    """重置服务单例"""
    global _factor_group_analysis_service
    _factor_group_analysis_service = None
