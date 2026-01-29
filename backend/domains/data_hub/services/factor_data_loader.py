"""
因子数据加载服务

为 factor_hub 分析工具提供统一的因子数据加载接口。
加载因子值 + 收益率数据，供因子分析使用。
"""

import asyncio
import logging
from typing import Any

import pandas as pd
from domains.core.exceptions import DataNotFoundError, FactorNotFoundError

from .data_loader import DataLoader
from .factor_calculator import FactorCalculator

logger = logging.getLogger(__name__)


class FactorDataLoader:
    """
    因子数据加载器

    为因子分析提供统一的数据加载接口，整合 K 线数据、因子计算和收益率计算。
    """

    # 预设的收益率周期（小时）
    RETURN_PERIODS = [1, 4, 8, 24, 48]

    def __init__(
        self,
        data_loader: DataLoader | None = None,
        factor_calculator: FactorCalculator | None = None,
    ):
        """
        初始化因子数据加载器

        Args:
            data_loader: 数据加载器实例
            factor_calculator: 因子计算器实例
        """
        self._data_loader = data_loader
        self._factor_calculator = factor_calculator

    @property
    def data_loader(self) -> DataLoader:
        """延迟获取 DataLoader"""
        if self._data_loader is None:
            self._data_loader = DataLoader()
        return self._data_loader

    @property
    def factor_calculator(self) -> FactorCalculator:
        """延迟获取 FactorCalculator"""
        if self._factor_calculator is None:
            self._factor_calculator = FactorCalculator()
        return self._factor_calculator

    def load_factor_data(
        self,
        factor_name: str,
        param: Any | None = None,
        symbols: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        data_type: str = "swap",
        return_periods: list[int] | None = None,
    ) -> pd.DataFrame:
        """
        加载因子数据（同步版本）

        加载指定因子的值以及对应的未来收益率，供因子分析使用。

        Args:
            factor_name: 因子名称
            param: 因子参数，默认为 20
            symbols: 币种列表，默认全部
            start_date: 开始日期
            end_date: 结束日期
            data_type: 数据类型 ('swap' 或 'spot')
            return_periods: 收益率周期列表（小时），默认 [1, 4, 8, 24, 48]

        Returns:
            DataFrame，包含列:
            - candle_begin_time: 时间
            - symbol: 交易对
            - close: 收盘价
            - {factor_name}_{param}: 因子值
            - return_1h, return_4h, ...: 未来收益率
        """
        if param is None:
            param = 20

        if return_periods is None:
            return_periods = self.RETURN_PERIODS

        # 获取币种列表
        if symbols is None:
            symbols = self.data_loader.get_symbols(data_type)

        factor_col = f"{factor_name}_{param}"
        all_dfs = []

        for symbol in symbols:
            try:
                # 加载 K 线数据
                df = self.data_loader.get_kline(symbol, data_type, start_date, end_date)

                if df.empty or len(df) < 50:
                    continue

                # 计算因子
                factor_config = {factor_name: [param]}
                df = self.factor_calculator.add_factors_to_df(df, factor_config)

                if factor_col not in df.columns:
                    continue

                # 计算未来收益率
                for period in return_periods:
                    df[f"return_{period}h"] = df["close"].shift(-period) / df["close"] - 1

                # 添加 symbol 列
                df["symbol"] = symbol

                # 选择需要的列
                cols = ["candle_begin_time", "symbol", "close", factor_col]
                cols += [f"return_{p}h" for p in return_periods]
                df = df[cols].copy()

                all_dfs.append(df)

            except (DataNotFoundError, FactorNotFoundError) as e:
                logger.debug(f"跳过 {symbol}: {e}")
                continue
            except Exception as e:
                logger.warning(f"处理 {symbol} 时出错: {e}")
                continue

        if not all_dfs:
            raise DataNotFoundError(f"无法加载因子数据: {factor_name}")

        result = pd.concat(all_dfs, ignore_index=True)

        # 删除包含 NaN 的行（因子计算初期和收益率计算末期会有 NaN）
        result = result.dropna()

        return result

    async def load_factor_data_async(
        self,
        factor_name: str,
        param: Any | None = None,
        symbols: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        data_type: str = "swap",
        return_periods: list[int] | None = None,
    ) -> pd.DataFrame:
        """
        加载因子数据（异步版本）

        通过 asyncio.to_thread 将同步方法包装为异步，避免阻塞事件循环。
        """
        return await asyncio.to_thread(
            self.load_factor_data,
            factor_name=factor_name,
            param=param,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            data_type=data_type,
            return_periods=return_periods,
        )

    def load_multiple_factors(
        self,
        factor_params: dict[str, list[Any]],
        symbols: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        data_type: str = "swap",
        return_periods: list[int] | None = None,
    ) -> pd.DataFrame:
        """
        加载多个因子数据（同步版本）

        用于多因子分析、相关性分析等场景。

        Args:
            factor_params: {factor_name: [params]} 字典
            symbols: 币种列表，默认全部
            start_date: 开始日期
            end_date: 结束日期
            data_type: 数据类型
            return_periods: 收益率周期列表

        Returns:
            DataFrame，包含所有因子列和收益率列
        """
        if return_periods is None:
            return_periods = self.RETURN_PERIODS

        # 获取币种列表
        if symbols is None:
            symbols = self.data_loader.get_symbols(data_type)

        # 构建因子列名列表
        factor_cols = []
        for factor_name, params in factor_params.items():
            for param in params:
                factor_cols.append(f"{factor_name}_{param}")

        all_dfs = []

        for symbol in symbols:
            try:
                # 加载 K 线数据
                df = self.data_loader.get_kline(symbol, data_type, start_date, end_date)

                if df.empty or len(df) < 50:
                    continue

                # 一次性计算所有因子
                df = self.factor_calculator.add_factors_to_df(df, factor_params)

                # 检查是否有因子列被成功计算
                available_cols = [col for col in factor_cols if col in df.columns]
                if not available_cols:
                    continue

                # 计算未来收益率
                for period in return_periods:
                    df[f"return_{period}h"] = df["close"].shift(-period) / df["close"] - 1

                # 添加 symbol 列
                df["symbol"] = symbol

                # 选择需要的列
                cols = ["candle_begin_time", "symbol", "close"]
                cols += available_cols
                cols += [f"return_{p}h" for p in return_periods]
                df = df[cols].copy()

                all_dfs.append(df)

            except (DataNotFoundError, FactorNotFoundError) as e:
                logger.debug(f"跳过 {symbol}: {e}")
                continue
            except Exception as e:
                logger.warning(f"处理 {symbol} 时出错: {e}")
                continue

        if not all_dfs:
            raise DataNotFoundError("无法加载多因子数据")

        result = pd.concat(all_dfs, ignore_index=True)

        # 删除所有因子列都为 NaN 的行
        factor_cols_available = [col for col in factor_cols if col in result.columns]
        if factor_cols_available:
            result = result.dropna(subset=factor_cols_available, how="all")

        return result

    async def load_multiple_factors_async(
        self,
        factor_params: dict[str, list[Any]],
        symbols: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        data_type: str = "swap",
        return_periods: list[int] | None = None,
    ) -> pd.DataFrame:
        """
        加载多个因子数据（异步版本）
        """
        return await asyncio.to_thread(
            self.load_multiple_factors,
            factor_params=factor_params,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            data_type=data_type,
            return_periods=return_periods,
        )

    def load_factor_cross_section(
        self,
        factor_name: str,
        param: Any | None = None,
        timestamp: str | None = None,
        symbols: list[str] | None = None,
        data_type: str = "swap",
        lookback_hours: int = 500,
    ) -> pd.DataFrame:
        """
        加载因子截面数据（同步版本）

        获取某个时间点所有币种的因子值。

        Args:
            factor_name: 因子名称
            param: 因子参数
            timestamp: 时间点，默认最新
            symbols: 币种列表
            data_type: 数据类型
            lookback_hours: 因子计算所需的回看小时数

        Returns:
            DataFrame，每行一个币种，包含因子值
        """
        if param is None:
            param = 20

        # 获取币种列表
        if symbols is None:
            symbols = self.data_loader.get_symbols(data_type)

        factor_col = f"{factor_name}_{param}"
        rows = []

        for symbol in symbols:
            try:
                # 加载 K 线数据
                df = self.data_loader.get_kline(symbol, data_type)

                if df.empty:
                    continue

                # 只保留最近的数据用于因子计算
                df = df.tail(lookback_hours)

                # 计算因子
                factor_config = {factor_name: [param]}
                df = self.factor_calculator.add_factors_to_df(df, factor_config)

                if factor_col not in df.columns:
                    continue

                # 获取目标时间点或最新数据
                if timestamp:
                    target_time = pd.to_datetime(timestamp)
                    target_row = df[df["candle_begin_time"] == target_time]
                    if target_row.empty:
                        continue
                    row = target_row.iloc[0]
                else:
                    row = df.iloc[-1]

                factor_value = row[factor_col]
                if pd.isna(factor_value):
                    continue

                rows.append({
                    "symbol": symbol,
                    "candle_begin_time": row["candle_begin_time"],
                    "close": row["close"],
                    factor_col: factor_value,
                })

            except Exception as e:
                logger.debug(f"跳过 {symbol}: {e}")
                continue

        if not rows:
            raise DataNotFoundError(f"无法加载因子截面数据: {factor_name}")

        return pd.DataFrame(rows)

    async def load_factor_cross_section_async(
        self,
        factor_name: str,
        param: Any | None = None,
        timestamp: str | None = None,
        symbols: list[str] | None = None,
        data_type: str = "swap",
        lookback_hours: int = 500,
    ) -> pd.DataFrame:
        """
        加载因子截面数据（异步版本）
        """
        return await asyncio.to_thread(
            self.load_factor_cross_section,
            factor_name=factor_name,
            param=param,
            timestamp=timestamp,
            symbols=symbols,
            data_type=data_type,
            lookback_hours=lookback_hours,
        )


# 单例实例
_factor_data_loader: FactorDataLoader | None = None


def get_factor_data_loader() -> FactorDataLoader:
    """获取因子数据加载器单例"""
    global _factor_data_loader
    if _factor_data_loader is None:
        _factor_data_loader = FactorDataLoader()
    return _factor_data_loader


def reset_factor_data_loader():
    """重置因子数据加载器单例（用于测试）"""
    global _factor_data_loader
    _factor_data_loader = None
