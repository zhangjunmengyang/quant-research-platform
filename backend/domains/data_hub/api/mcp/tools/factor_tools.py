"""
因子计算工具

提供因子列表、因子计算、因子排名等能力。
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import BaseTool, ToolResult
from domains.mcp_core.base.tool import ExecutionMode


class ListFactorsTool(BaseTool):
    """获取可用因子列表"""

    @property
    def name(self) -> str:
        return "list_available_factors"

    @property
    def description(self) -> str:
        return """获取可用于计算的因子列表。

返回所有可用因子的名称列表，如：Bias, RSI, MACD 等。
这些因子可以用于 calculate_factor 和 get_factor_ranking 工具。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    async def execute(self, **params) -> ToolResult:
        try:
            factors = self.factor_calculator.list_factors()

            return ToolResult(
                success=True,
                data={
                    "factors": factors,
                    "count": len(factors),
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class CalculateFactorTool(BaseTool):
    """计算因子值"""

    execution_mode = ExecutionMode.COMPUTE  # CPU 密集型计算
    execution_timeout = 60.0

    @property
    def name(self) -> str:
        return "calculate_factor"

    @property
    def description(self) -> str:
        return """计算指定币种的因子值。

支持两种模式:
1. 单因子模式: 使用 factor_name + params
2. 多因子模式: 使用 factors 数组批量计算

可用参数:
- symbol: 币种名称 (必填)
- factor_name: 因子名称，如 Bias, RSI, MACD (单因子模式)
- params: 因子参数列表，如 [5, 10, 20] (单因子模式)
- factors: 多因子配置数组 (多因子模式，与 factor_name 二选一)
- data_type: 数据类型，swap 或 spot，默认 swap
- start_date: 开始日期
- end_date: 结束日期
- limit: 返回条数限制

返回计算后的因子值序列。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "币种名称，如 BTC-USDT"
                },
                "factor_name": {
                    "type": "string",
                    "description": "因子名称，如 Bias, RSI, MACD (单因子模式)"
                },
                "params": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "因子参数列表，如 [5, 10, 20] (单因子模式)",
                    "default": [20]
                },
                "factors": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "param": {"type": "integer"}
                        },
                        "required": ["name", "param"]
                    },
                    "description": "多因子批量计算，与 factor_name 二选一"
                },
                "data_type": {
                    "type": "string",
                    "description": "数据类型: swap 或 spot",
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
            factors_list = params.get("factors")
            factor_name = params.get("factor_name")
            factor_params = params.get("params", [20])
            data_type = params.get("data_type", "swap")
            start_date = params.get("start_date")
            end_date = params.get("end_date")
            limit = params.get("limit", 100)

            # 检查参数有效性
            if not factors_list and not factor_name:
                return ToolResult(
                    success=False,
                    error="必须提供 factor_name 或 factors 参数"
                )

            # 使用异步方法获取 K 线数据，避免阻塞事件循环
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

            # 构建因子配置
            if factors_list:
                # 多因子模式
                factor_config = {}
                for f in factors_list:
                    name = f['name']
                    param = f['param']
                    if name not in factor_config:
                        factor_config[name] = []
                    factor_config[name].append(param)
            else:
                # 单因子模式
                factor_config = {factor_name: factor_params}

            # 一次性计算所有因子
            df = self.factor_calculator.add_factors_to_df(df, factor_config)

            # 限制返回条数
            df = df.tail(limit)

            # 构建返回数据
            records = []

            # 确定因子列名
            if factors_list:
                factor_columns = [f"{f['name']}_{f['param']}" for f in factors_list]
            else:
                factor_columns = [f"{factor_name}_{p}" for p in factor_params]

            for _, row in df.iterrows():
                record = {
                    "candle_begin_time": str(row.get("candle_begin_time", "")),
                    "close": float(row.get("close", 0)),
                }
                for col in factor_columns:
                    if col in row:
                        val = row[col]
                        record[col] = float(val) if val == val else None  # 处理 NaN

                records.append(record)

            # 构建返回结果
            result_data = {
                "symbol": symbol,
                "count": len(records),
                "data": records,
            }

            if factors_list:
                result_data["factors"] = factors_list
            else:
                result_data["factor_name"] = factor_name
                result_data["params"] = factor_params

            return ToolResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetSymbolRankAtTool(BaseTool):
    """获取单币种在指定时刻的因子排名"""

    execution_mode = ExecutionMode.COMPUTE
    execution_timeout = 60.0

    @property
    def name(self) -> str:
        return "get_symbol_rank_at"

    @property
    def description(self) -> str:
        return """获取单个币种在指定时刻的因子排名。

可用参数:
- symbol: 币种名称 (必填)
- factor_name: 因子名称 (必填)
- param: 因子参数 (必填)
- timestamp: 指定时间点 (必填)，格式 YYYY-MM-DD HH:MM:SS
- ascending: 是否升序排列，默认 True
- data_type: 数据类型，swap 或 spot，默认 swap

返回该币种在所有币种中的排名位置和百分位。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
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
                "timestamp": {
                    "type": "string",
                    "description": "指定时间点，格式 YYYY-MM-DD HH:MM:SS"
                },
                "ascending": {
                    "type": "boolean",
                    "description": "是否升序排列 (因子值从小到大)",
                    "default": True
                },
                "data_type": {
                    "type": "string",
                    "description": "数据类型: swap 或 spot",
                    "enum": ["swap", "spot"],
                    "default": "swap"
                }
            },
            "required": ["symbol", "factor_name", "param", "timestamp"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            symbol = params["symbol"]
            factor_name = params["factor_name"]
            param = params["param"]
            timestamp = params["timestamp"]
            ascending = params.get("ascending", True)
            data_type = params.get("data_type", "swap")

            # 获取截面数据
            df = self.data_slicer.get_cross_section(
                timestamp=timestamp,
                factors={factor_name: [param]},
                data_type=data_type
            )

            if df.empty:
                return ToolResult(
                    success=False,
                    error=f"时间点 {timestamp} 无截面数据"
                )

            factor_col = f"{factor_name}_{param}"

            if factor_col not in df.columns:
                return ToolResult(
                    success=False,
                    error=f"因子 {factor_col} 计算失败"
                )

            # 排序并计算排名
            df = df.sort_values(factor_col, ascending=ascending)
            df['rank'] = range(1, len(df) + 1)

            # 查找目标币种
            symbol_rows = df[df['symbol'] == symbol]

            if symbol_rows.empty:
                return ToolResult(
                    success=False,
                    error=f"币种 {symbol} 在时间点 {timestamp} 无数据"
                )

            row = symbol_rows.iloc[0]
            rank = int(row['rank'])
            total = len(df)
            percentile = (total - rank + 1) / total * 100

            factor_value = row[factor_col]
            factor_value = float(factor_value) if factor_value == factor_value else None

            return ToolResult(
                success=True,
                data={
                    "symbol": symbol,
                    "factor_name": factor_name,
                    "param": param,
                    "timestamp": timestamp,
                    "rank": rank,
                    "percentile": round(percentile, 2),
                    "total_symbols": total,
                    "factor_value": factor_value,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetFactorRankingTool(BaseTool):
    """获取因子排名"""

    execution_mode = ExecutionMode.COMPUTE  # CPU 密集型计算
    execution_timeout = 60.0

    @property
    def name(self) -> str:
        return "get_factor_ranking"

    @property
    def description(self) -> str:
        return """获取所有币种在指定因子上的排名。

可用参数：
- factor_name: 因子名称（必填）
- param: 因子参数（必填），如 20
- data_type: 数据类型，swap 或 spot，默认 swap
- timestamp: 指定时间点，格式 YYYY-MM-DD HH:MM:SS，不指定则使用最新数据
- ascending: 是否升序排列，默认 True
- top_n: 返回前 N 名，默认 30

返回币种排名列表。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
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
                "data_type": {
                    "type": "string",
                    "description": "数据类型：swap 或 spot",
                    "enum": ["swap", "spot"],
                    "default": "swap"
                },
                "timestamp": {
                    "type": "string",
                    "description": "指定时间点，格式 YYYY-MM-DD HH:MM:SS"
                },
                "ascending": {
                    "type": "boolean",
                    "description": "是否升序排列（因子值从小到大）",
                    "default": True
                },
                "top_n": {
                    "type": "integer",
                    "description": "返回前 N 名",
                    "default": 30,
                    "minimum": 1,
                    "maximum": 200
                }
            },
            "required": ["factor_name", "param"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            factor_name = params["factor_name"]
            param = params["param"]
            data_type = params.get("data_type", "swap")
            timestamp = params.get("timestamp")
            ascending = params.get("ascending", True)
            top_n = params.get("top_n", 30)

            ranking_df = self.data_slicer.get_factor_ranking(
                factor_name=factor_name,
                param=param,
                timestamp=timestamp,
                ascending=ascending,
                top_n=top_n,
                data_type=data_type
            )

            if ranking_df.empty:
                return ToolResult(
                    success=False,
                    error="无法获取排名数据"
                )

            # 转换为列表
            factor_col = f"{factor_name}_{param}"
            records = []
            for _, row in ranking_df.iterrows():
                record = {
                    "rank": int(row.get("rank", 0)),
                    "symbol": row.get("symbol", ""),
                    "factor_value": float(row[factor_col]) if factor_col in row and row[factor_col] == row[factor_col] else None,
                    "close": float(row.get("close", 0)) if "close" in row else None,
                }
                records.append(record)

            return ToolResult(
                success=True,
                data={
                    "factor_name": factor_name,
                    "param": param,
                    "timestamp": timestamp or "latest",
                    "ascending": ascending,
                    "count": len(records),
                    "ranking": records,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


