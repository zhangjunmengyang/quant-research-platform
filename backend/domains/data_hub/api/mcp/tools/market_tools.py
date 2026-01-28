"""
市场分析 MCP 工具

提供市场概览、板块表现等工具。
"""

import logging
from typing import Any

import pandas as pd
from domains.mcp_core.base.tool import ExecutionMode

from .base import BaseTool, ToolResult

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
    def input_schema(self) -> dict[str, Any]:
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


class DetectKlinePatternsTool(BaseTool):
    """K线形态识别工具"""

    category = "market"
    execution_mode = ExecutionMode.COMPUTE
    execution_timeout = 60.0

    @property
    def name(self) -> str:
        return "detect_kline_patterns"

    @property
    def description(self) -> str:
        return """识别指定币种在指定时间范围内的K线形态。

支持的形态:
- doji: 十字星(实体很小)
- hammer: 锤子线(下影线长,上影线短,实体在上半部分)
- engulfing_bullish: 看涨吞没(阳包阴)
- engulfing_bearish: 看跌吞没(阴包阳)
- shooting_star: 射击之星(上影线长,下影线短,实体在下半部分)
- morning_star: 晨星(三根K线组合)
- evening_star: 暮星(三根K线组合)

返回识别到的形态列表及其出现时间。"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "币种名称,如 BTC-USDT"
                },
                "patterns": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "doji", "hammer", "engulfing_bullish",
                            "engulfing_bearish", "shooting_star",
                            "morning_star", "evening_star"
                        ]
                    },
                    "description": "要识别的形态列表"
                },
                "start_date": {
                    "type": "string",
                    "description": "开始日期,格式 YYYY-MM-DD"
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期,格式 YYYY-MM-DD"
                },
                "data_type": {
                    "type": "string",
                    "description": "数据类型: swap(合约) 或 spot(现货)",
                    "enum": ["swap", "spot"],
                    "default": "swap"
                }
            },
            "required": ["symbol", "patterns", "start_date", "end_date"]
        }

    def _detect_patterns(self, df: pd.DataFrame, patterns: list[str]) -> dict[str, list[int]]:
        """
        检测K线形态

        Args:
            df: K线数据
            patterns: 要检测的形态列表

        Returns:
            形态检测结果,key为形态名,value为检测到该形态的行索引列表
        """
        results = {p: [] for p in patterns}

        if df.empty or len(df) < 3:
            return results

        # 预计算常用指标
        body = abs(df['close'] - df['open'])
        upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
        lower_shadow = df[['open', 'close']].min(axis=1) - df['low']
        candle_range = df['high'] - df['low']

        for i in range(len(df)):
            # 避免除零错误
            if candle_range.iloc[i] == 0:
                continue

            # doji: 十字星,实体很小(小于整体范围的10%)
            if 'doji' in patterns and body.iloc[i] <= candle_range.iloc[i] * 0.1:
                results['doji'].append(i)

            # hammer: 锤子线,下影线长(至少为实体的2倍),上影线短(小于实体的0.5倍)
            if ('hammer' in patterns and body.iloc[i] > 0 and
                    lower_shadow.iloc[i] >= body.iloc[i] * 2 and
                    upper_shadow.iloc[i] <= body.iloc[i] * 0.5):
                results['hammer'].append(i)

            # shooting_star: 射击之星,上影线长,下影线短,实体在下半部分
            if ('shooting_star' in patterns and body.iloc[i] > 0 and
                    upper_shadow.iloc[i] >= body.iloc[i] * 2 and
                    lower_shadow.iloc[i] <= body.iloc[i] * 0.5):
                results['shooting_star'].append(i)

            # engulfing_bullish: 阳包阴(前一根阴线,当前阳线完全包住前一根)
            if 'engulfing_bullish' in patterns and i > 0:
                prev_bearish = df.iloc[i - 1]['close'] < df.iloc[i - 1]['open']
                curr_bullish = df.iloc[i]['close'] > df.iloc[i]['open']
                engulfs = (df.iloc[i]['open'] <= df.iloc[i - 1]['close'] and
                           df.iloc[i]['close'] >= df.iloc[i - 1]['open'])
                if prev_bearish and curr_bullish and engulfs:
                    results['engulfing_bullish'].append(i)

            # engulfing_bearish: 阴包阳(前一根阳线,当前阴线完全包住前一根)
            if 'engulfing_bearish' in patterns and i > 0:
                prev_bullish = df.iloc[i - 1]['close'] > df.iloc[i - 1]['open']
                curr_bearish = df.iloc[i]['close'] < df.iloc[i]['open']
                engulfs = (df.iloc[i]['open'] >= df.iloc[i - 1]['close'] and
                           df.iloc[i]['close'] <= df.iloc[i - 1]['open'])
                if prev_bullish and curr_bearish and engulfs:
                    results['engulfing_bearish'].append(i)

            # morning_star: 晨星(三根K线: 大阴线 + 小实体 + 大阳线)
            if 'morning_star' in patterns and i >= 2:
                # 第一根: 大阴线
                first_bearish = (df.iloc[i - 2]['close'] < df.iloc[i - 2]['open'] and
                                 body.iloc[i - 2] > candle_range.iloc[i - 2] * 0.5)
                # 第二根: 小实体
                second_small = body.iloc[i - 1] <= candle_range.iloc[i - 1] * 0.3 if candle_range.iloc[i - 1] > 0 else False
                # 第三根: 大阳线
                third_bullish = (df.iloc[i]['close'] > df.iloc[i]['open'] and
                                 body.iloc[i] > candle_range.iloc[i] * 0.5)
                # 第三根收盘价高于第一根的中点
                first_mid = (df.iloc[i - 2]['open'] + df.iloc[i - 2]['close']) / 2
                closes_above_mid = df.iloc[i]['close'] > first_mid

                if first_bearish and second_small and third_bullish and closes_above_mid:
                    results['morning_star'].append(i)

            # evening_star: 暮星(三根K线: 大阳线 + 小实体 + 大阴线)
            if 'evening_star' in patterns and i >= 2:
                # 第一根: 大阳线
                first_bullish = (df.iloc[i - 2]['close'] > df.iloc[i - 2]['open'] and
                                 body.iloc[i - 2] > candle_range.iloc[i - 2] * 0.5)
                # 第二根: 小实体
                second_small = body.iloc[i - 1] <= candle_range.iloc[i - 1] * 0.3 if candle_range.iloc[i - 1] > 0 else False
                # 第三根: 大阴线
                third_bearish = (df.iloc[i]['close'] < df.iloc[i]['open'] and
                                 body.iloc[i] > candle_range.iloc[i] * 0.5)
                # 第三根收盘价低于第一根的中点
                first_mid = (df.iloc[i - 2]['open'] + df.iloc[i - 2]['close']) / 2
                closes_below_mid = df.iloc[i]['close'] < first_mid

                if first_bullish and second_small and third_bearish and closes_below_mid:
                    results['evening_star'].append(i)

        return results

    async def execute(self, **params) -> ToolResult:
        try:
            symbol = params["symbol"]
            patterns = params["patterns"]
            start_date = params["start_date"]
            end_date = params["end_date"]
            data_type = params.get("data_type", "swap")

            # 参数验证
            if not patterns:
                return ToolResult.fail("patterns 不能为空")

            valid_patterns = {
                "doji", "hammer", "engulfing_bullish",
                "engulfing_bearish", "shooting_star",
                "morning_star", "evening_star"
            }
            invalid_patterns = set(patterns) - valid_patterns
            if invalid_patterns:
                return ToolResult.fail(f"不支持的形态: {invalid_patterns}")

            # 获取K线数据
            df = await self.data_loader.get_kline_async(
                symbol=symbol,
                data_type=data_type,
                start_date=start_date,
                end_date=end_date
            )

            if df.empty:
                return ToolResult.fail(f"无数据: {symbol}")

            # 检测形态
            pattern_indices = self._detect_patterns(df, patterns)

            # 构建返回结果
            patterns_found = {}
            pattern_counts = {}

            for pattern_name, indices in pattern_indices.items():
                pattern_counts[pattern_name] = len(indices)
                if indices:
                    patterns_found[pattern_name] = []
                    for idx in indices:
                        row = df.iloc[idx]
                        patterns_found[pattern_name].append({
                            "time": str(row.get("candle_begin_time", "")),
                            "open": float(row.get("open", 0)),
                            "close": float(row.get("close", 0)),
                            "high": float(row.get("high", 0)),
                            "low": float(row.get("low", 0)),
                        })

            return ToolResult.ok({
                "symbol": symbol,
                "patterns_found": patterns_found,
                "pattern_counts": pattern_counts,
            })

        except Exception as e:
            logger.exception("K线形态识别失败")
            return ToolResult.fail(str(e))


