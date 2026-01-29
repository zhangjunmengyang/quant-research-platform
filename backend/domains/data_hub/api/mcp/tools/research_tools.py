"""
研究分析工具

提供多周期收益率计算、回撤统计、顶底识别和分阶段统计等研究分析能力。
"""

from typing import Any

import pandas as pd
from domains.mcp_core.base.tool import ExecutionMode

from .base import BaseTool, ToolResult


class CalculateReturnsTool(BaseTool):
    """多周期收益率计算工具"""

    execution_mode = ExecutionMode.COMPUTE
    execution_timeout = 60.0

    @property
    def name(self) -> str:
        return "calculate_returns"

    @property
    def description(self) -> str:
        return """计算指定币种在某时间点的多周期收益率。

可用参数:
- symbol: 币种名称 (必填)，如 BTC-USDT
- timestamp: 时间点 (必填)，格式 YYYY-MM-DD HH:MM:SS
- shift_hours: 周期列表，正数表示过去收益，负数表示未来收益，默认 [24, 48, 168, -24, -48]
- data_type: 数据类型，swap 或 spot，默认 swap

返回该时间点相对于各周期的收益率。正数周期表示从过去到当前的收益率，负数周期表示从当前到未来的收益率。"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "币种名称，如 BTC-USDT"
                },
                "timestamp": {
                    "type": "string",
                    "description": "时间点，格式 YYYY-MM-DD HH:MM:SS"
                },
                "shift_hours": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "周期列表，正数=过去收益，负数=未来收益",
                    "default": [24, 48, 168, -24, -48]
                },
                "data_type": {
                    "type": "string",
                    "description": "数据类型：swap 或 spot",
                    "enum": ["swap", "spot"],
                    "default": "swap"
                }
            },
            "required": ["symbol", "timestamp"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            symbol = params["symbol"]
            timestamp = params["timestamp"]
            shift_hours = params.get("shift_hours", [24, 48, 168, -24, -48])
            data_type = params.get("data_type", "swap")

            # 获取 K 线数据
            df = await self.data_loader.get_kline_async(
                symbol=symbol,
                data_type=data_type
            )

            if df.empty:
                return ToolResult(
                    success=False,
                    error=f"无数据: {symbol}"
                )

            # 确保时间列格式正确并重置索引
            df = df.copy()
            df = df.reset_index(drop=True)
            df["candle_begin_time"] = pd.to_datetime(df["candle_begin_time"])
            target_time = pd.to_datetime(timestamp)

            # 找到目标时间点的位置索引
            time_matches = df[df["candle_begin_time"] == target_time]
            if time_matches.empty:
                return ToolResult(
                    success=False,
                    error=f"未找到时间点: {timestamp}"
                )

            idx = time_matches.index[0]
            current_close = float(df.iloc[idx]["close"])

            # 计算各周期收益率
            returns = {}
            for shift in shift_hours:
                target_idx = idx - shift
                if target_idx < 0 or target_idx >= len(df):
                    returns[shift] = None
                    continue

                target_close = float(df.iloc[target_idx]["close"])
                if shift > 0:
                    # 过去收益率: 当前价格 / 过去价格 - 1
                    returns[shift] = round((current_close / target_close) - 1, 6)
                else:
                    # 未来收益率: 未来价格 / 当前价格 - 1
                    returns[shift] = round((target_close / current_close) - 1, 6)

            return ToolResult(
                success=True,
                data={
                    "symbol": symbol,
                    "timestamp": timestamp,
                    "current_close": current_close,
                    "returns": returns
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CalculateDrawdownTool(BaseTool):
    """回撤统计工具"""

    execution_mode = ExecutionMode.COMPUTE
    execution_timeout = 60.0

    @property
    def name(self) -> str:
        return "calculate_drawdown"

    @property
    def description(self) -> str:
        return """计算指定币种在指定时间范围内的回撤统计。

可用参数:
- symbol: 币种名称 (必填)，如 BTC-USDT
- start_date: 开始日期 (必填)，格式 YYYY-MM-DD
- end_date: 结束日期 (必填)，格式 YYYY-MM-DD
- data_type: 数据类型，swap 或 spot，默认 swap

返回最大回撤、回撤起止时间、持续时长、当前回撤等统计信息。"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "币种名称，如 BTC-USDT"
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
            "required": ["symbol", "start_date", "end_date"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            symbol = params["symbol"]
            start_date = params["start_date"]
            end_date = params["end_date"]
            data_type = params.get("data_type", "swap")

            # 获取 K 线数据
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

            df = df.copy()
            df["candle_begin_time"] = pd.to_datetime(df["candle_begin_time"])

            # 计算累计最大值和回撤
            df["running_max"] = df["close"].cummax()
            df["drawdown"] = (df["close"] - df["running_max"]) / df["running_max"]

            # 找到最大回撤点
            max_dd_idx = df["drawdown"].idxmin()
            max_drawdown = float(df.loc[max_dd_idx, "drawdown"])
            trough_time = df.loc[max_dd_idx, "candle_begin_time"]
            trough_price = float(df.loc[max_dd_idx, "close"])

            # 找到最大回撤对应的峰值点（在最大回撤点之前）
            df_before_trough = df.loc[:max_dd_idx]
            peak_idx = df_before_trough["close"].idxmax()
            peak_time = df.loc[peak_idx, "candle_begin_time"]
            peak_price = float(df.loc[peak_idx, "close"])

            # 计算回撤持续时间（小时）
            duration_hours = int((trough_time - peak_time).total_seconds() / 3600)

            # 当前回撤
            current_drawdown = float(df["drawdown"].iloc[-1])

            return ToolResult(
                success=True,
                data={
                    "symbol": symbol,
                    "period": {
                        "start": start_date,
                        "end": end_date
                    },
                    "max_drawdown": round(max_drawdown, 6),
                    "max_drawdown_start": str(peak_time),
                    "max_drawdown_end": str(trough_time),
                    "max_drawdown_duration_hours": duration_hours,
                    "current_drawdown": round(current_drawdown, 6),
                    "peak_price": peak_price,
                    "peak_time": str(peak_time),
                    "trough_price": trough_price,
                    "trough_time": str(trough_time)
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class FindPeaksTroughsTool(BaseTool):
    """顶底识别工具"""

    execution_mode = ExecutionMode.COMPUTE
    execution_timeout = 60.0

    @property
    def name(self) -> str:
        return "find_peaks_troughs"

    @property
    def description(self) -> str:
        return """识别指定币种在指定时间范围内的顶部和底部。

可用参数:
- symbol: 币种名称 (必填)，如 BTC-USDT
- start_date: 开始日期 (必填)，格式 YYYY-MM-DD
- end_date: 结束日期 (必填)，格式 YYYY-MM-DD
- window: 局部极值窗口小时数，默认 24
- min_change: 最小涨跌幅阈值，默认 0.05 (5%)
- data_type: 数据类型，swap 或 spot，默认 swap

返回识别出的顶部和底部列表，包含时间、价格和相对涨跌幅。"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "币种名称，如 BTC-USDT"
                },
                "start_date": {
                    "type": "string",
                    "description": "开始日期，格式 YYYY-MM-DD"
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式 YYYY-MM-DD"
                },
                "window": {
                    "type": "integer",
                    "description": "局部极值窗口小时数",
                    "default": 24,
                    "minimum": 1
                },
                "min_change": {
                    "type": "number",
                    "description": "最小涨跌幅阈值",
                    "default": 0.05,
                    "minimum": 0
                },
                "data_type": {
                    "type": "string",
                    "description": "数据类型：swap 或 spot",
                    "enum": ["swap", "spot"],
                    "default": "swap"
                }
            },
            "required": ["symbol", "start_date", "end_date"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            symbol = params["symbol"]
            start_date = params["start_date"]
            end_date = params["end_date"]
            window = params.get("window", 24)
            min_change = params.get("min_change", 0.05)
            data_type = params.get("data_type", "swap")

            # 获取 K 线数据
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

            df = df.copy()
            df = df.reset_index(drop=True)
            df["candle_begin_time"] = pd.to_datetime(df["candle_begin_time"])

            # 使用滚动窗口找局部极值
            half_window = window // 2
            peaks = []
            troughs = []

            for i in range(half_window, len(df) - half_window):
                window_start = i - half_window
                window_end = i + half_window + 1
                window_data = df.iloc[window_start:window_end]

                current_close = df.iloc[i]["close"]
                current_time = df.iloc[i]["candle_begin_time"]

                # 判断是否为局部最大值（顶）
                if current_close == window_data["close"].max():
                    peaks.append({
                        "idx": i,
                        "time": current_time,
                        "price": float(current_close)
                    })

                # 判断是否为局部最小值（底）
                if current_close == window_data["close"].min():
                    troughs.append({
                        "idx": i,
                        "time": current_time,
                        "price": float(current_close)
                    })

            # 过滤小于 min_change 的波动并计算涨跌幅
            filtered_peaks = []
            filtered_troughs = []

            # 处理顶部
            for peak in peaks:
                # 找到之前最近的底部
                prev_troughs = [t for t in troughs if t["idx"] < peak["idx"]]
                if prev_troughs:
                    prev_trough = prev_troughs[-1]
                    rise = (peak["price"] / prev_trough["price"]) - 1
                    if rise >= min_change:
                        filtered_peaks.append({
                            "time": str(peak["time"]),
                            "price": peak["price"],
                            "prev_trough_price": prev_trough["price"],
                            "rise": round(rise, 6)
                        })

            # 处理底部
            for trough in troughs:
                # 找到之前最近的顶部
                prev_peaks = [p for p in peaks if p["idx"] < trough["idx"]]
                if prev_peaks:
                    prev_peak = prev_peaks[-1]
                    drop = (trough["price"] / prev_peak["price"]) - 1
                    if drop <= -min_change:
                        filtered_troughs.append({
                            "time": str(trough["time"]),
                            "price": trough["price"],
                            "prev_peak_price": prev_peak["price"],
                            "drop": round(drop, 6)
                        })

            return ToolResult(
                success=True,
                data={
                    "symbol": symbol,
                    "peaks": filtered_peaks,
                    "troughs": filtered_troughs,
                    "peak_count": len(filtered_peaks),
                    "trough_count": len(filtered_troughs)
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CalculateStageStatsTool(BaseTool):
    """分阶段统计工具"""

    execution_mode = ExecutionMode.COMPUTE
    execution_timeout = 60.0

    @property
    def name(self) -> str:
        return "calculate_stage_stats"

    @property
    def description(self) -> str:
        return """计算指定币种在多个阶段的统计数据。

可用参数:
- symbol: 币种名称 (必填)，如 BTC-USDT
- stages: 阶段列表 (必填)，每个阶段包含 name, start, end
- data_type: 数据类型，swap 或 spot，默认 swap

返回每个阶段的收益率、最大回撤、波动率、平均成交量等统计信息。"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "币种名称，如 BTC-USDT"
                },
                "stages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "阶段名称"},
                            "start": {"type": "string", "description": "开始日期，格式 YYYY-MM-DD"},
                            "end": {"type": "string", "description": "结束日期，格式 YYYY-MM-DD"}
                        },
                        "required": ["name", "start", "end"]
                    },
                    "description": "阶段列表"
                },
                "data_type": {
                    "type": "string",
                    "description": "数据类型：swap 或 spot",
                    "enum": ["swap", "spot"],
                    "default": "swap"
                }
            },
            "required": ["symbol", "stages"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            symbol = params["symbol"]
            stages = params["stages"]
            data_type = params.get("data_type", "swap")

            # 获取完整 K 线数据
            df = await self.data_loader.get_kline_async(
                symbol=symbol,
                data_type=data_type
            )

            if df.empty:
                return ToolResult(
                    success=False,
                    error=f"无数据: {symbol}"
                )

            df = df.copy()
            df["candle_begin_time"] = pd.to_datetime(df["candle_begin_time"])

            stage_results = []
            for stage in stages:
                stage_name = stage["name"]
                start_date = pd.to_datetime(stage["start"])
                end_date = pd.to_datetime(stage["end"]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

                # 筛选阶段数据
                stage_df = df[(df["candle_begin_time"] >= start_date) & (df["candle_begin_time"] <= end_date)]

                if stage_df.empty:
                    stage_results.append({
                        "name": stage_name,
                        "start": stage["start"],
                        "end": stage["end"],
                        "error": "无数据"
                    })
                    continue

                # 计算收益率
                first_close = float(stage_df.iloc[0]["close"])
                last_close = float(stage_df.iloc[-1]["close"])
                stage_return = (last_close / first_close) - 1

                # 计算最大回撤
                stage_df = stage_df.copy()
                stage_df["running_max"] = stage_df["close"].cummax()
                stage_df["drawdown"] = (stage_df["close"] - stage_df["running_max"]) / stage_df["running_max"]
                max_drawdown = float(stage_df["drawdown"].min())

                # 计算波动率（小时收益率的标准差）
                stage_df["returns"] = stage_df["close"].pct_change()
                volatility = float(stage_df["returns"].std())

                # 计算平均成交量
                volume_avg = float(stage_df["volume"].mean()) if "volume" in stage_df.columns else None

                # K 线数量
                kline_count = len(stage_df)

                stage_results.append({
                    "name": stage_name,
                    "start": stage["start"],
                    "end": stage["end"],
                    "return": round(stage_return, 6),
                    "max_drawdown": round(max_drawdown, 6),
                    "volatility": round(volatility, 6) if volatility == volatility else None,
                    "volume_avg": round(volume_avg, 2) if volume_avg is not None else None,
                    "kline_count": kline_count
                })

            return ToolResult(
                success=True,
                data={
                    "symbol": symbol,
                    "stages": stage_results
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


