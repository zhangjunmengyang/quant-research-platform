"""
数据资源定义

提供 MCP Resources，用于向 LLM 提供只读数据上下文。
基于 mcp_core.BaseResourceProvider 实现。
"""

import json
import logging

from domains.mcp_core import (
    BaseResourceProvider,
    ResourceContent,
)

logger = logging.getLogger(__name__)


class DataResourceProvider(BaseResourceProvider):
    """
    数据资源提供者

    管理所有可用的 MCP 资源，支持动态资源发现和模板资源。
    继承 mcp_core.BaseResourceProvider。
    """

    def __init__(self, data_loader=None, factor_calculator=None):
        super().__init__()
        self._data_loader = data_loader
        self._factor_calculator = factor_calculator
        self._register_data_resources()

    @property
    def data_loader(self):
        """延迟获取 DataLoader"""
        if self._data_loader is None:
            from domains.data_hub import DataLoader
            self._data_loader = DataLoader()
        return self._data_loader

    @property
    def factor_calculator(self):
        """延迟获取 FactorCalculator"""
        if self._factor_calculator is None:
            from domains.data_hub import FactorCalculator
            self._factor_calculator = FactorCalculator()
        return self._factor_calculator

    def _register_data_resources(self):
        """注册数据相关的资源"""
        # 币种列表资源
        self.register_static(
            uri="data://symbols",
            name="币种列表",
            description="所有可用交易币种的列表",
            handler=self._read_symbols,
        )

        # 因子列表资源
        self.register_static(
            uri="data://factors",
            name="可用因子",
            description="所有可用于计算的因子列表",
            handler=self._read_factors,
        )

        # 数据概览
        self.register_static(
            uri="data://overview",
            name="数据概览",
            description="数据模块的整体统计信息",
            handler=self._read_overview,
        )

        # 配置信息
        self.register_static(
            uri="data://config",
            name="数据配置",
            description="当前数据模块的配置信息",
            handler=self._read_config,
        )

        # 动态资源模板
        self.register_dynamic(
            pattern="data://kline/{symbol}",
            name="K线数据",
            description="获取指定币种的最新 K 线数据，将 {symbol} 替换为实际币种名",
            handler=self._read_kline,
        )

        self.register_dynamic(
            pattern="data://symbol/{symbol}/info",
            name="币种信息",
            description="获取指定币种的详细信息",
            handler=self._read_symbol_info,
        )

    async def _read_symbols(self) -> ResourceContent:
        """读取币种列表"""
        swap_symbols = self.data_loader.get_symbols("swap")
        spot_symbols = self.data_loader.get_symbols("spot")

        data = {
            "swap": {
                "count": len(swap_symbols),
                "symbols": swap_symbols,
            },
            "spot": {
                "count": len(spot_symbols),
                "symbols": spot_symbols,
            },
        }

        return ResourceContent(
            uri="data://symbols",
            mime_type="application/json",
            text=json.dumps(data, ensure_ascii=False, indent=2),
        )

    async def _read_factors(self) -> ResourceContent:
        """读取因子列表"""
        factors = self.factor_calculator.list_factors()

        data = {
            "count": len(factors),
            "factors": factors,
        }

        return ResourceContent(
            uri="data://factors",
            mime_type="application/json",
            text=json.dumps(data, ensure_ascii=False, indent=2),
        )

    async def _read_overview(self) -> ResourceContent:
        """读取数据概览"""
        swap_symbols = self.data_loader.get_symbols("swap")
        spot_symbols = self.data_loader.get_symbols("spot")
        factors = self.factor_calculator.list_factors()

        data = {
            "swap_symbols_count": len(swap_symbols),
            "spot_symbols_count": len(spot_symbols),
            "available_factors_count": len(factors),
            "data_type": "1H K-line",
            "description": "币圈交易数据模块，提供 K 线数据查询和因子计算能力",
        }

        return ResourceContent(
            uri="data://overview",
            mime_type="application/json",
            text=json.dumps(data, ensure_ascii=False, indent=2),
        )

    async def _read_config(self) -> ResourceContent:
        """读取配置信息"""
        from domains.mcp_core import get_config
        config = get_config()

        data = config.to_dict()

        return ResourceContent(
            uri="data://config",
            mime_type="application/json",
            text=json.dumps(data, ensure_ascii=False, indent=2),
        )

    async def _read_kline(self, symbol: str) -> ResourceContent | None:
        """读取 K 线数据"""
        try:
            df = self.data_loader.get_kline(symbol=symbol, data_type="swap")

            if df.empty:
                return None

            # 只返回最近 50 条
            df = df.tail(50)

            records = []
            for _, row in df.iterrows():
                records.append({
                    "candle_begin_time": str(row.get("candle_begin_time", "")),
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "close": float(row.get("close", 0)),
                    "volume": float(row.get("volume", 0)),
                })

            data = {
                "symbol": symbol,
                "count": len(records),
                "klines": records,
            }

            return ResourceContent(
                uri=f"data://kline/{symbol}",
                mime_type="application/json",
                text=json.dumps(data, ensure_ascii=False, indent=2),
            )

        except Exception as e:
            logger.error(f"读取 K 线数据失败: {e}")
            return None

    async def _read_symbol_info(self, symbol: str) -> ResourceContent | None:
        """读取币种信息"""
        try:
            info = self.data_loader.get_symbol_info(symbol)

            if info is None:
                return None

            data = {
                "symbol": info.symbol,
                "has_spot": info.has_spot,
                "has_swap": info.has_swap,
                "first_candle_time": str(info.first_candle_time) if info.first_candle_time else None,
                "last_candle_time": str(info.last_candle_time) if info.last_candle_time else None,
                "kline_count": info.kline_count,
            }

            return ResourceContent(
                uri=f"data://symbol/{symbol}/info",
                mime_type="application/json",
                text=json.dumps(data, ensure_ascii=False, indent=2),
            )

        except Exception as e:
            logger.error(f"读取币种信息失败: {e}")
            return None
