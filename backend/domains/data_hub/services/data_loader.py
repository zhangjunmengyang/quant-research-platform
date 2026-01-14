"""
数据加载服务

代理到 engine 服务层，确保与回测引擎使用完全相同的数据加载逻辑。

异步支持:
- 提供 async 版本的数据加载方法，避免阻塞事件循环
"""

from typing import Dict, List, Optional, Tuple, Set

import pandas as pd

from ..core.models import DataConfig, SymbolInfo
from domains.core.exceptions import DataNotFoundError, ConfigError

# 使用 engine 服务
from domains.engine.services import (
    DataLoaderService as EngineDataLoader,
    get_data_loader as get_engine_data_loader,
)


class DataLoader:
    """
    数据加载服务

    代理到 engine.services.DataLoaderService，确保一致性。
    """

    def __init__(self, config: Optional[DataConfig] = None):
        """
        初始化数据加载器

        Args:
            config: 数据配置，默认从配置文件加载
        """
        self.config = config
        self._engine_loader = get_engine_data_loader()

    def load_spot_data(self, reload: bool = False) -> Dict[str, pd.DataFrame]:
        """
        加载现货数据

        Args:
            reload: 是否强制重新加载

        Returns:
            {symbol: DataFrame} 字典
        """
        try:
            return self._engine_loader.load_spot_data(reload)
        except FileNotFoundError as e:
            raise DataNotFoundError(str(e))

    def load_swap_data(self, reload: bool = False) -> Dict[str, pd.DataFrame]:
        """
        加载合约数据

        Args:
            reload: 是否强制重新加载

        Returns:
            {symbol: DataFrame} 字典
        """
        try:
            return self._engine_loader.load_swap_data(reload)
        except FileNotFoundError as e:
            raise DataNotFoundError(str(e))

    def load_all(self, reload: bool = False) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
        """
        加载全部数据

        Args:
            reload: 是否强制重新加载

        Returns:
            (spot_data, swap_data) 元组
        """
        spot_data = self.load_spot_data(reload)
        swap_data = self.load_swap_data(reload)
        return spot_data, swap_data

    def get_symbols(self, data_type: str = 'all') -> List[str]:
        """
        获取可用币种列表

        Args:
            data_type: 数据类型 ('spot', 'swap', 'all')

        Returns:
            币种列表
        """
        return self._engine_loader.get_symbols(data_type)

    def get_symbol_info(self, symbol: str) -> SymbolInfo:
        """
        获取币种信息

        Args:
            symbol: 交易对名称

        Returns:
            SymbolInfo 实例
        """
        try:
            engine_info = self._engine_loader.get_symbol_info(symbol)
            return SymbolInfo(
                symbol=engine_info.symbol,
                has_spot=engine_info.has_spot,
                has_swap=engine_info.has_swap,
                first_candle_time=engine_info.first_candle_time,
                last_candle_time=engine_info.last_candle_time,
                kline_count=engine_info.kline_count,
            )
        except KeyError as e:
            raise DataNotFoundError(str(e))

    def get_kline(
        self,
        symbol: str,
        data_type: str = 'swap',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取单个币种 K 线数据

        Args:
            symbol: 交易对名称
            data_type: 数据类型 ('spot' 或 'swap')
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            K 线 DataFrame
        """
        try:
            return self._engine_loader.get_kline(symbol, data_type, start_date, end_date)
        except KeyError as e:
            raise DataNotFoundError(str(e))

    def get_merged_kline(
        self,
        symbols: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取合并的 K 线数据

        Args:
            symbols: 币种列表，默认全部
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            合并的 DataFrame
        """
        swap_data = self.load_swap_data()

        if symbols is None:
            symbols = list(swap_data.keys())

        dfs = []
        for symbol in symbols:
            if symbol in swap_data:
                df = swap_data[symbol].copy()
                df['symbol'] = symbol

                # 时间过滤
                if start_date:
                    df = df[df['candle_begin_time'] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df['candle_begin_time'] <= pd.to_datetime(end_date)]

                if not df.empty:
                    dfs.append(df)

        if not dfs:
            return pd.DataFrame()

        return pd.concat(dfs, ignore_index=True)

    def clear_cache(self):
        """清除数据缓存"""
        self._engine_loader.clear_cache()

    def get_stats(self) -> Dict:
        """
        获取数据统计信息

        Returns:
            包含统计信息的字典
        """
        return self._engine_loader.get_stats()

    # ============================================
    # 异步方法 - 代理到 engine 的异步方法
    # ============================================

    async def load_spot_data_async(self, reload: bool = False) -> Dict[str, pd.DataFrame]:
        """异步加载现货数据"""
        try:
            return await self._engine_loader.load_spot_data_async(reload)
        except FileNotFoundError as e:
            raise DataNotFoundError(str(e))

    async def load_swap_data_async(self, reload: bool = False) -> Dict[str, pd.DataFrame]:
        """异步加载合约数据"""
        try:
            return await self._engine_loader.load_swap_data_async(reload)
        except FileNotFoundError as e:
            raise DataNotFoundError(str(e))

    async def load_all_async(self, reload: bool = False) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
        """异步加载全部数据"""
        return await self._engine_loader.load_all_async(reload)

    async def get_kline_async(
        self,
        symbol: str,
        data_type: str = 'swap',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """异步获取单个币种 K 线数据"""
        try:
            return await self._engine_loader.get_kline_async(symbol, data_type, start_date, end_date)
        except KeyError as e:
            raise DataNotFoundError(str(e))

    async def get_symbols_async(self, data_type: str = 'all') -> List[str]:
        """异步获取可用币种列表"""
        return await self._engine_loader.get_symbols_async(data_type)

    async def get_stats_async(self) -> Dict:
        """异步获取数据统计信息"""
        return await self._engine_loader.get_stats_async()

    async def get_symbol_info_async(self, symbol: str) -> SymbolInfo:
        """异步获取币种信息"""
        try:
            engine_info = await self._engine_loader.get_symbol_info_async(symbol)
            return SymbolInfo(
                symbol=engine_info.symbol,
                has_spot=engine_info.has_spot,
                has_swap=engine_info.has_swap,
                first_candle_time=engine_info.first_candle_time,
                last_candle_time=engine_info.last_candle_time,
                kline_count=engine_info.kline_count,
            )
        except KeyError as e:
            raise DataNotFoundError(str(e))
