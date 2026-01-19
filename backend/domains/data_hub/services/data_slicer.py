"""
数据切片服务

提供灵活的数据查询和切片能力。
"""

from typing import Dict, List, Optional, Any

import pandas as pd

from .data_loader import DataLoader
from .factor_calculator import FactorCalculator
from ..core.models import DataConfig
from domains.core.exceptions import DataNotFoundError


class DataSlicer:
    """
    数据切片服务

    提供灵活的数据查询和切片能力。
    整合 DataLoader 和 FactorCalculator 的能力。
    """

    def __init__(
        self,
        loader: Optional[DataLoader] = None,
        calculator: Optional[FactorCalculator] = None,
    ):
        """
        初始化数据切片器

        Args:
            loader: 数据加载器实例
            calculator: 因子计算器实例
        """
        self.loader = loader or DataLoader()
        self.calculator = calculator or FactorCalculator()

    def slice_by_time(
        self,
        start: str,
        end: str,
        symbols: Optional[List[str]] = None,
        data_type: str = 'swap',
    ) -> pd.DataFrame:
        """
        按时间切片数据

        Args:
            start: 开始时间
            end: 结束时间
            symbols: 币种列表，默认全部
            data_type: 数据类型 ('spot' 或 'swap')

        Returns:
            切片后的 DataFrame
        """
        if symbols is None:
            symbols = self.loader.get_symbols(data_type)

        dfs = []
        for symbol in symbols:
            try:
                df = self.loader.get_kline(symbol, data_type, start, end)
                df['symbol'] = symbol
                dfs.append(df)
            except DataNotFoundError:
                continue

        if not dfs:
            return pd.DataFrame()

        return pd.concat(dfs, ignore_index=True)

    def slice_by_symbol(
        self,
        symbols: List[str],
        start: Optional[str] = None,
        end: Optional[str] = None,
        with_factors: Optional[Dict[str, List[Any]]] = None,
        data_type: str = 'swap',
    ) -> pd.DataFrame:
        """
        按币种切片数据

        Args:
            symbols: 币种列表
            start: 开始时间
            end: 结束时间
            with_factors: 要计算的因子 {factor_name: [params]}
            data_type: 数据类型

        Returns:
            切片后的 DataFrame（可能包含因子列）
        """
        dfs = []
        for symbol in symbols:
            try:
                df = self.loader.get_kline(symbol, data_type, start, end)
                df['symbol'] = symbol

                # 计算因子
                if with_factors:
                    df = self.calculator.add_factors_to_df(df, with_factors)

                dfs.append(df)
            except DataNotFoundError:
                continue

        if not dfs:
            return pd.DataFrame()

        return pd.concat(dfs, ignore_index=True)

    def get_cross_section(
        self,
        timestamp: str,
        symbols: Optional[List[str]] = None,
        factors: Optional[Dict[str, List[Any]]] = None,
        data_type: str = 'swap',
        lookback_hours: int = 500,
    ) -> pd.DataFrame:
        """
        获取截面数据

        获取某个时间点的所有币种数据快照。

        Args:
            timestamp: 时间戳
            symbols: 币种列表，默认全部
            factors: 要计算的因子 {factor_name: [params]}
            data_type: 数据类型
            lookback_hours: 因子计算所需的回看小时数

        Returns:
            截面 DataFrame
        """
        target_time = pd.to_datetime(timestamp)

        # 计算时间范围（因子计算需要历史数据）
        start_time = target_time - pd.Timedelta(hours=lookback_hours)

        if symbols is None:
            symbols = self.loader.get_symbols(data_type)

        rows = []
        for symbol in symbols:
            try:
                df = self.loader.get_kline(
                    symbol, data_type,
                    start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    target_time.strftime('%Y-%m-%d %H:%M:%S'),
                )

                if df.empty:
                    continue

                # 计算因子（如果需要）
                if factors:
                    df = self.calculator.add_factors_to_df(df, factors)

                # 获取目标时间点的数据
                target_row = df[df['candle_begin_time'] == target_time]
                if not target_row.empty:
                    row_data = target_row.iloc[0].to_dict()
                    row_data['symbol'] = symbol
                    rows.append(row_data)

            except DataNotFoundError:
                continue

        if not rows:
            return pd.DataFrame()

        return pd.DataFrame(rows)

    def get_latest_data(
        self,
        symbols: Optional[List[str]] = None,
        factors: Optional[Dict[str, List[Any]]] = None,
        data_type: str = 'swap',
        lookback_hours: int = 500,
    ) -> pd.DataFrame:
        """
        获取最新数据

        获取所有币种的最新 K 线数据。

        Args:
            symbols: 币种列表，默认全部
            factors: 要计算的因子
            data_type: 数据类型
            lookback_hours: 因子计算所需的回看小时数

        Returns:
            最新数据 DataFrame
        """
        if symbols is None:
            symbols = self.loader.get_symbols(data_type)

        rows = []
        for symbol in symbols:
            try:
                df = self.loader.get_kline(symbol, data_type)

                if df.empty:
                    continue

                # 只保留最近的数据用于因子计算
                df = df.tail(lookback_hours)

                # 计算因子
                if factors:
                    df = self.calculator.add_factors_to_df(df, factors)

                # 获取最新一行
                row_data = df.iloc[-1].to_dict()
                row_data['symbol'] = symbol
                rows.append(row_data)

            except DataNotFoundError:
                continue

        if not rows:
            return pd.DataFrame()

        return pd.DataFrame(rows)

    def get_factor_ranking(
        self,
        factor_name: str,
        param: Any,
        timestamp: Optional[str] = None,
        symbols: Optional[List[str]] = None,
        ascending: bool = True,
        top_n: Optional[int] = None,
        data_type: str = 'swap',
    ) -> pd.DataFrame:
        """
        获取因子排名

        按因子值对币种进行排名。

        Args:
            factor_name: 因子名称
            param: 因子参数
            timestamp: 时间戳，默认最新
            symbols: 币种列表
            ascending: 是否升序
            top_n: 返回前 N 个
            data_type: 数据类型

        Returns:
            排名 DataFrame
        """
        factors = {factor_name: [param]}

        if timestamp:
            df = self.get_cross_section(timestamp, symbols, factors, data_type)
        else:
            df = self.get_latest_data(symbols, factors, data_type)

        if df.empty:
            return df

        col_name = f"{factor_name}_{param}"
        if col_name not in df.columns:
            return pd.DataFrame()

        # 排序
        df = df.sort_values(col_name, ascending=ascending)

        # 添加排名列
        df['rank'] = range(1, len(df) + 1)

        # 限制数量
        if top_n:
            df = df.head(top_n)

        return df[['symbol', col_name, 'rank', 'close', 'volume']]
