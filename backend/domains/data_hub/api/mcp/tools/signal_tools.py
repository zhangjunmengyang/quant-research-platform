"""
信号分析工具

提供信号检测、市场筛选、信号表现分析等能力。
"""

from typing import Any

import numpy as np
import pandas as pd
from domains.mcp_core.base.tool import ExecutionMode

from .base import BaseTool, ToolResult


class DetectSymbolEventsTool(BaseTool):
    """单币种信号检测工具"""

    execution_mode = ExecutionMode.COMPUTE
    execution_timeout = 60.0

    @property
    def name(self) -> str:
        return "detect_symbol_events"

    @property
    def description(self) -> str:
        return """检测单个币种在指定条件下的信号事件。

可用参数:
- symbol: 币种名称 (必填), 如 BTC-USDT
- factor_name: 因子名称 (必填), 如 Bias, RSI
- param: 因子参数 (必填), 如 20
- operator: 比较操作符 (必填), 支持 ">", "<", ">=", "<=", "==", "cross_up", "cross_down"
- threshold: 阈值 (必填), 如 -0.15
- start_date: 开始日期, 格式 YYYY-MM-DD
- end_date: 结束日期, 格式 YYYY-MM-DD
- data_type: 数据类型, swap 或 spot, 默认 swap

返回满足条件的信号事件列表，包含时间、因子值和收盘价。"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "币种名称，如 BTC-USDT"
                },
                "factor_name": {
                    "type": "string",
                    "description": "因子名称，如 Bias, RSI"
                },
                "param": {
                    "type": "integer",
                    "description": "因子参数，如 20"
                },
                "operator": {
                    "type": "string",
                    "description": "比较操作符",
                    "enum": [">", "<", ">=", "<=", "==", "cross_up", "cross_down"]
                },
                "threshold": {
                    "type": "number",
                    "description": "阈值，如 -0.15"
                },
                "start_date": {
                    "type": "string",
                    "description": "开始日期，格式 YYYY-MM-DD"
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式 YYYY-MM-DD"
                },
                "data_type": {
                    "type": "string",
                    "description": "数据类型：swap 或 spot",
                    "enum": ["swap", "spot"],
                    "default": "swap"
                }
            },
            "required": ["symbol", "factor_name", "param", "operator", "threshold"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            symbol = params["symbol"]
            factor_name = params["factor_name"]
            param = params["param"]
            operator = params["operator"]
            threshold = params["threshold"]
            start_date = params.get("start_date")
            end_date = params.get("end_date")
            data_type = params.get("data_type", "swap")

            # 获取 K 线数据
            df = await self.data_loader.get_kline_async(
                symbol=symbol,
                data_type=data_type,
                start_date=start_date,
                end_date=end_date
            )

            if df.empty:
                return ToolResult(success=False, error=f"无数据: {symbol}")

            # 计算因子
            factor_config = {factor_name: [param]}
            df = self.factor_calculator.add_factors_to_df(df, factor_config)
            factor_col = f"{factor_name}_{param}"

            if factor_col not in df.columns:
                return ToolResult(success=False, error=f"无法计算因子: {factor_col}")

            # 根据操作符筛选
            if operator == ">":
                mask = df[factor_col] > threshold
            elif operator == "<":
                mask = df[factor_col] < threshold
            elif operator == ">=":
                mask = df[factor_col] >= threshold
            elif operator == "<=":
                mask = df[factor_col] <= threshold
            elif operator == "==":
                mask = df[factor_col] == threshold
            elif operator == "cross_up":
                prev = df[factor_col].shift(1)
                mask = (prev < threshold) & (df[factor_col] >= threshold)
            elif operator == "cross_down":
                prev = df[factor_col].shift(1)
                mask = (prev > threshold) & (df[factor_col] <= threshold)
            else:
                return ToolResult(success=False, error=f"不支持的操作符: {operator}")

            # 获取符合条件的事件
            events_df = df[mask][['candle_begin_time', factor_col, 'close']].copy()
            events = []
            for _, row in events_df.iterrows():
                factor_value = row[factor_col]
                events.append({
                    "time": str(row['candle_begin_time']),
                    "factor_value": float(factor_value) if factor_value == factor_value else None,
                    "close": float(row['close'])
                })

            # 构建条件描述
            condition = f"{factor_col} {operator} {threshold}"

            # 获取数据时间范围
            period_start = str(df['candle_begin_time'].min())
            period_end = str(df['candle_begin_time'].max())

            return ToolResult(
                success=True,
                data={
                    "symbol": symbol,
                    "condition": condition,
                    "period": {
                        "start": period_start,
                        "end": period_end
                    },
                    "events_count": len(events),
                    "events": events
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ScreenMarketTool(BaseTool):
    """全市场截面筛选工具"""

    execution_mode = ExecutionMode.COMPUTE
    execution_timeout = 60.0

    @property
    def name(self) -> str:
        return "screen_market"

    @property
    def description(self) -> str:
        return """全市场截面筛选，找出满足条件的币种。

可用参数:
- factor_name: 因子名称 (必填), 如 Bias, RSI
- param: 因子参数 (必填), 如 20
- operator: 比较操作符 (必填), 支持 ">", "<", ">=", "<=", "=="
- threshold: 阈值 (必填), 如 -0.15
- timestamp: 指定时间点, 格式 YYYY-MM-DD HH:MM:SS, 不指定则使用最新数据
- data_type: 数据类型, swap 或 spot, 默认 swap
- limit: 返回数量限制, 默认 50, 最大 200

返回满足条件的币种列表，按因子值排序。"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "factor_name": {
                    "type": "string",
                    "description": "因子名称，如 Bias, RSI"
                },
                "param": {
                    "type": "integer",
                    "description": "因子参数，如 20"
                },
                "operator": {
                    "type": "string",
                    "description": "比较操作符",
                    "enum": [">", "<", ">=", "<=", "=="]
                },
                "threshold": {
                    "type": "number",
                    "description": "阈值，如 -0.15"
                },
                "timestamp": {
                    "type": "string",
                    "description": "指定时间点，格式 YYYY-MM-DD HH:MM:SS"
                },
                "data_type": {
                    "type": "string",
                    "description": "数据类型：swap 或 spot",
                    "enum": ["swap", "spot"],
                    "default": "swap"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回数量限制",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 200
                }
            },
            "required": ["factor_name", "param", "operator", "threshold"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            factor_name = params["factor_name"]
            param = params["param"]
            operator = params["operator"]
            threshold = params["threshold"]
            timestamp = params.get("timestamp")
            data_type = params.get("data_type", "swap")
            limit = params.get("limit", 50)

            # 获取截面数据
            factors = {factor_name: [param]}
            if timestamp:
                df = self.data_slicer.get_cross_section(
                    timestamp=timestamp,
                    factors=factors,
                    data_type=data_type
                )
            else:
                df = self.data_slicer.get_latest_data(
                    factors=factors,
                    data_type=data_type
                )

            if df.empty:
                return ToolResult(success=False, error="无法获取截面数据")

            factor_col = f"{factor_name}_{param}"
            if factor_col not in df.columns:
                return ToolResult(success=False, error=f"无法计算因子: {factor_col}")

            total_symbols = len(df)

            # 根据操作符筛选
            if operator == ">":
                mask = df[factor_col] > threshold
            elif operator == "<":
                mask = df[factor_col] < threshold
            elif operator == ">=":
                mask = df[factor_col] >= threshold
            elif operator == "<=":
                mask = df[factor_col] <= threshold
            elif operator == "==":
                mask = df[factor_col] == threshold
            else:
                return ToolResult(success=False, error=f"不支持的操作符: {operator}")

            # 筛选并排序
            filtered_df = df[mask].copy()
            ascending = operator in ["<", "<="]
            filtered_df = filtered_df.sort_values(factor_col, ascending=ascending).head(limit)

            # 构建结果
            matched = []
            for _, row in filtered_df.iterrows():
                factor_value = row[factor_col]
                matched.append({
                    "symbol": row.get("symbol", ""),
                    "factor_value": float(factor_value) if factor_value == factor_value else None,
                    "close": float(row.get("close", 0)) if "close" in row else None
                })

            condition = f"{factor_col} {operator} {threshold}"
            actual_timestamp = timestamp or "latest"

            return ToolResult(
                success=True,
                data={
                    "condition": condition,
                    "timestamp": actual_timestamp,
                    "matched_count": len(matched),
                    "total_symbols": total_symbols,
                    "matched": matched
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class SimulateHoldingStrategyTool(BaseTool):
    """持仓策略模拟工具"""

    execution_mode = ExecutionMode.COMPUTE
    execution_timeout = 300.0  # P2 工具，较长超时

    @property
    def name(self) -> str:
        return "simulate_holding_strategy"

    @property
    def description(self) -> str:
        return """模拟持仓策略表现，支持止损止盈。

可用参数:
- symbol: 币种名称 (必填), 如 BTC-USDT
- entry_signals: 入场信号时间列表 (必填)
- holding_hours: 默认持仓时间（小时）, 默认 24
- stop_loss: 止损比例, 如 -0.05 表示 -5%
- take_profit: 止盈比例, 如 0.1 表示 10%
- data_type: 数据类型, swap 或 spot, 默认 swap

返回每笔交易详情和汇总统计。"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "币种名称，如 BTC-USDT"
                },
                "entry_signals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "入场信号时间列表"
                },
                "holding_hours": {
                    "type": "integer",
                    "description": "默认持仓时间（小时）",
                    "default": 24
                },
                "stop_loss": {
                    "type": "number",
                    "description": "止损比例，如 -0.05"
                },
                "take_profit": {
                    "type": "number",
                    "description": "止盈比例，如 0.1"
                },
                "data_type": {
                    "type": "string",
                    "description": "数据类型：swap 或 spot",
                    "enum": ["swap", "spot"],
                    "default": "swap"
                }
            },
            "required": ["symbol", "entry_signals"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            symbol = params["symbol"]
            entry_signals = params["entry_signals"]
            holding_hours = params.get("holding_hours", 24)
            stop_loss = params.get("stop_loss")
            take_profit = params.get("take_profit")
            data_type = params.get("data_type", "swap")

            if not entry_signals:
                return ToolResult(success=False, error="入场信号列表为空")

            # 获取 K 线数据
            df = await self.data_loader.get_kline_async(
                symbol=symbol,
                data_type=data_type
            )

            if df.empty:
                return ToolResult(success=False, error=f"无数据: {symbol}")

            # 确保时间列为 datetime 类型
            df['candle_begin_time'] = pd.to_datetime(df['candle_begin_time'])
            df = df.reset_index(drop=True)

            # 模拟每笔交易
            trades = []
            for entry_time_str in entry_signals:
                entry_time = pd.to_datetime(entry_time_str)
                idx_list = df[df['candle_begin_time'] == entry_time].index.tolist()

                if not idx_list:
                    continue

                entry_idx = idx_list[0]
                entry_price = df.loc[entry_idx, 'close']

                # 在持仓期间检查止损止盈
                exit_idx = None
                exit_reason = "holding_period"

                for h in range(1, holding_hours + 1):
                    check_idx = entry_idx + h
                    if check_idx >= len(df):
                        break

                    current_price = df.loc[check_idx, 'close']
                    current_return = (current_price / entry_price) - 1

                    # 检查止损
                    if stop_loss is not None and current_return <= stop_loss:
                        exit_idx = check_idx
                        exit_reason = "stop_loss"
                        break

                    # 检查止盈
                    if take_profit is not None and current_return >= take_profit:
                        exit_idx = check_idx
                        exit_reason = "take_profit"
                        break

                # 如果未触发止损止盈，使用默认持仓期
                if exit_idx is None:
                    exit_idx = entry_idx + holding_hours
                    if exit_idx >= len(df):
                        continue  # 数据不足，跳过此交易

                exit_price = df.loc[exit_idx, 'close']
                exit_time = df.loc[exit_idx, 'candle_begin_time']
                trade_return = (exit_price / entry_price) - 1

                trades.append({
                    "entry_time": str(entry_time),
                    "entry_price": float(entry_price),
                    "exit_time": str(exit_time),
                    "exit_price": float(exit_price),
                    "return": float(trade_return),
                    "exit_reason": exit_reason
                })

            # 计算汇总统计
            if not trades:
                return ToolResult(
                    success=True,
                    data={
                        "symbol": symbol,
                        "trades": [],
                        "summary": {
                            "total_trades": 0,
                            "win_rate": None,
                            "avg_return": None,
                            "max_return": None,
                            "max_loss": None,
                            "total_return": None
                        }
                    }
                )

            returns = [t["return"] for t in trades]
            returns_arr = np.array(returns)

            summary = {
                "total_trades": len(trades),
                "win_rate": float(np.sum(returns_arr > 0) / len(returns_arr)),
                "avg_return": float(np.mean(returns_arr)),
                "max_return": float(np.max(returns_arr)),
                "max_loss": float(np.min(returns_arr)),
                "total_return": float(np.sum(returns_arr))
            }

            return ToolResult(
                success=True,
                data={
                    "symbol": symbol,
                    "trades": trades,
                    "summary": summary
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
