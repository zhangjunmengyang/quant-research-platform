"""
数据查询工具

提供币种列表、K线数据等查询能力。
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import BaseTool, ToolResult


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


class GetKlineTool(BaseTool):
    """获取 K 线数据工具"""

    @property
    def name(self) -> str:
        return "get_kline"

    @property
    def description(self) -> str:
        return """获取指定币种的 K 线数据。

可用参数：
- symbol: 币种名称（必填）
- data_type: 数据类型，swap 或 spot，默认 swap
- start_date: 开始日期，格式 YYYY-MM-DD
- end_date: 结束日期，格式 YYYY-MM-DD
- limit: 返回条数限制，默认 100

返回 K 线数据列表，包含 open, high, low, close, volume 等字段。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "币种名称，如 BTC-USDT"
                },
                "data_type": {
                    "type": "string",
                    "description": "数据类型：swap（合约）或 spot（现货）",
                    "enum": ["swap", "spot"],
                    "default": "swap"
                },
                "start_date": {
                    "type": "string",
                    "description": "开始日期，格式 YYYY-MM-DD"
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式 YYYY-MM-DD"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回条数限制",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 10000
                }
            },
            "required": ["symbol"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            symbol = params["symbol"]
            data_type = params.get("data_type", "swap")
            start_date = params.get("start_date")
            end_date = params.get("end_date")
            limit = params.get("limit", 100)

            # 使用异步方法避免阻塞事件循环
            df = await self.data_loader.get_kline_async(
                symbol=symbol,
                data_type=data_type,
                start_date=start_date,
                end_date=end_date
            )

            if df.empty:
                return ToolResult(
                    success=False,
                    error=f"无数据: {symbol}"
                )

            # 限制返回条数
            df = df.tail(limit)

            # 转换为列表
            records = []
            for _, row in df.iterrows():
                record = {
                    "candle_begin_time": str(row.get("candle_begin_time", "")),
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "close": float(row.get("close", 0)),
                    "volume": float(row.get("volume", 0)),
                }
                if "quote_volume" in row:
                    record["quote_volume"] = float(row["quote_volume"])
                records.append(record)

            return ToolResult(
                success=True,
                data={
                    "symbol": symbol,
                    "data_type": data_type,
                    "count": len(records),
                    "klines": records,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
