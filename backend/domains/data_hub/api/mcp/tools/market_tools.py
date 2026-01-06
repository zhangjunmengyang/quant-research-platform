"""
市场分析 MCP 工具

提供市场概览、板块表现等工具。
"""

from typing import Any, Dict
import logging
import pandas as pd

from domains.mcp_core import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class GetMarketOverviewTool(BaseTool):
    """获取市场概览工具"""

    category = "market"

    @property
    def name(self) -> str:
        return "get_market_overview"

    @property
    def description(self) -> str:
        return "获取加密货币市场整体概览，包括总市值、BTC主导率、涨跌分布等"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "trade_type": {
                    "type": "string",
                    "description": "交易类型: swap(合约) / spot(现货)",
                    "enum": ["swap", "spot"],
                    "default": "swap",
                },
                "period": {
                    "type": "string",
                    "description": "统计周期: 1h / 4h / 1d / 7d",
                    "enum": ["1h", "4h", "1d", "7d"],
                    "default": "1d",
                },
            },
        }

    async def execute(
        self,
        trade_type: str = "swap",
        period: str = "1d",
    ) -> ToolResult:
        try:
            from domains.data_hub.services import DataLoader

            loader = DataLoader()

            # 使用异步方法加载数据，避免阻塞事件循环
            if trade_type == "swap":
                data_dict = await loader.load_swap_data_async()
            else:
                data_dict = await loader.load_spot_data_async()

            if not data_dict:
                return ToolResult.fail("无法加载数据")

            # 合并为单个 DataFrame
            dfs = []
            for symbol, symbol_df in data_dict.items():
                if symbol_df is not None and not symbol_df.empty:
                    df_copy = symbol_df.copy()
                    df_copy["symbol"] = symbol
                    dfs.append(df_copy)

            if not dfs:
                return ToolResult.fail("无可用数据")

            df = pd.concat(dfs, ignore_index=True)

            # 计算周期时间
            now = df["candle_begin_time"].max()
            period_hours = {"1h": 1, "4h": 4, "1d": 24, "7d": 168}.get(period, 24)
            start_time = now - pd.Timedelta(hours=period_hours)

            # 过滤数据
            period_df = df[df["candle_begin_time"] >= start_time]

            # 计算各币种收益率
            symbols = period_df["symbol"].unique()
            returns = {}

            for symbol in symbols:
                symbol_df = period_df[period_df["symbol"] == symbol].sort_values("candle_begin_time")
                if len(symbol_df) >= 2:
                    first_close = symbol_df["close"].iloc[0]
                    last_close = symbol_df["close"].iloc[-1]
                    if first_close > 0:
                        returns[symbol] = (last_close - first_close) / first_close

            if not returns:
                return ToolResult.fail("无法计算收益率")

            returns_series = pd.Series(returns)

            # 统计
            total_symbols = len(returns_series)
            up_count = (returns_series > 0).sum()
            down_count = (returns_series < 0).sum()
            flat_count = total_symbols - up_count - down_count

            # 找出最佳和最差表现
            top_performers = returns_series.nlargest(5).to_dict()
            bottom_performers = returns_series.nsmallest(5).to_dict()

            # 计算BTC主导率（如果有BTC数据）
            btc_dominance = None
            btc_return = returns.get("BTC-USDT") or returns.get("BTCUSDT")

            overview = {
                "period": period,
                "trade_type": trade_type,
                "timestamp": now.isoformat() if hasattr(now, "isoformat") else str(now),
                "total_symbols": total_symbols,
                "up_count": int(up_count),
                "down_count": int(down_count),
                "flat_count": int(flat_count),
                "up_ratio": round(up_count / total_symbols, 4) if total_symbols > 0 else 0,
                "avg_return": round(returns_series.mean(), 4),
                "median_return": round(returns_series.median(), 4),
                "max_return": round(returns_series.max(), 4),
                "min_return": round(returns_series.min(), 4),
                "std_return": round(returns_series.std(), 4),
                "btc_return": round(btc_return, 4) if btc_return else None,
                "top_performers": {k: round(v, 4) for k, v in top_performers.items()},
                "bottom_performers": {k: round(v, 4) for k, v in bottom_performers.items()},
            }

            return ToolResult.ok(overview)
        except ImportError as e:
            return ToolResult.fail(f"模块导入失败: {e}")
        except Exception as e:
            logger.exception("获取市场概览失败")
            return ToolResult.fail(str(e))


