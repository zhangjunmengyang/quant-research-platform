"""
数据查询工具

提供币种列表、K线数据等查询能力。
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import BaseTool, ToolResult
from domains.mcp_core.base.tool import ExecutionMode


class ListSymbolsTool(BaseTool):
    """获取币种列表工具"""

    @property
    def name(self) -> str:
        return "list_symbols"

    @property
    def description(self) -> str:
        return """获取可用的交易币种列表。

可用参数：
- data_type: 数据类型，swap（合约）或 spot（现货），默认 swap

返回币种列表，如：BTC-USDT, ETH-USDT 等。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data_type": {
                    "type": "string",
                    "description": "数据类型：swap（合约）或 spot（现货）",
                    "enum": ["swap", "spot"],
                    "default": "swap"
                }
            }
        }

    async def execute(self, **params) -> ToolResult:
        try:
            data_type = params.get("data_type", "swap")
            # 使用异步方法避免阻塞事件循环
            symbols = await self.data_loader.get_symbols_async(data_type)

            return ToolResult(
                success=True,
                data={
                    "data_type": data_type,
                    "symbols": symbols,
                    "count": len(symbols),
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetSymbolInfoTool(BaseTool):
    """获取币种信息工具"""

    @property
    def name(self) -> str:
        return "get_symbol_info"

    @property
    def description(self) -> str:
        return """获取指定币种的详细信息。

返回内容包括：
- 币种名称
- 数据时间范围
- 数据条数
- 最新价格等"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "币种名称，如 BTC-USDT"
                }
            },
            "required": ["symbol"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            symbol = params["symbol"]
            # 使用异步方法避免阻塞事件循环
            info = await self.data_loader.get_symbol_info_async(symbol)

            if info is None:
                return ToolResult(
                    success=False,
                    error=f"币种不存在: {symbol}"
                )

            return ToolResult(
                success=True,
                data={
                    "symbol": info.symbol,
                    "has_spot": info.has_spot,
                    "has_swap": info.has_swap,
                    "first_candle_time": str(info.first_candle_time) if info.first_candle_time else None,
                    "last_candle_time": str(info.last_candle_time) if info.last_candle_time else None,
                    "kline_count": info.kline_count,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetCoinMetadataTool(BaseTool):
    """获取币种元数据工具"""

    execution_mode = ExecutionMode.COMPUTE  # 需要遍历所有币种
    execution_timeout = 60.0

    @property
    def name(self) -> str:
        return "get_coin_metadata"

    @property
    def description(self) -> str:
        return """获取币种的元数据信息。

可用参数:
- symbols: 币种列表（可选），不传或空列表则返回所有币种
- data_type: 数据类型，swap（合约）或 spot（现货），默认 swap

返回每个币种的:
- symbol: 币种名称
- first_trade_time: 首次交易时间
- age_days: 上线天数
- last_close: 最新收盘价"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "币种列表，如 ['BTC-USDT', 'ETH-USDT']，不传则返回所有币种"
                },
                "data_type": {
                    "type": "string",
                    "description": "数据类型: swap（合约）或 spot（现货）",
                    "enum": ["swap", "spot"],
                    "default": "swap"
                }
            }
        }

    async def execute(self, **params) -> ToolResult:
        try:
            symbols = params.get("symbols", [])
            data_type = params.get("data_type", "swap")

            # 获取所有币种列表
            all_symbols = await self.data_loader.get_symbols_async(data_type)

            # 如果指定了 symbols，过滤
            if symbols:
                # 只保留存在的币种
                all_symbols = [s for s in all_symbols if s in symbols]

            # 获取每个币种的元数据
            coins = []
            for symbol in all_symbols:
                df = await self.data_loader.get_kline_async(symbol, data_type)
                if not df.empty:
                    first_time = df['candle_begin_time'].iloc[0]
                    last_close = df['close'].iloc[-1]
                    age_days = (datetime.now() - first_time).days

                    coins.append({
                        "symbol": symbol,
                        "first_trade_time": str(first_time),
                        "age_days": age_days,
                        "last_close": float(last_close),
                    })

            return ToolResult(
                success=True,
                data={
                    "coins": coins,
                    "total": len(coins),
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
