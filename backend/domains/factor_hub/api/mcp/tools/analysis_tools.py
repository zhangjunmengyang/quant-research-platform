"""
因子分析相关的 MCP 工具

提供因子分析能力的 MCP 工具封装。
"""

import json
import logging
from datetime import datetime
from typing import Any

from domains.mcp_core.base.tool import ExecutionMode

from .base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class GetFactorICTool(BaseTool):
    """获取因子IC - 快速获取因子IC统计"""

    category = "analysis"

    @property
    def name(self) -> str:
        return "get_factor_ic"

    @property
    def description(self) -> str:
        return "快速获取因子的IC统计信息，包括IC均值、ICIR、RankIC等"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "因子文件名（如 Momentum_5d，不含 .py 后缀）",
                },
            },
            "required": ["filename"],
        }

    async def execute(self, filename: str) -> ToolResult:
        try:
            filename = self.normalize_filename(filename)
            # 从因子知识库获取因子信息
            factor = self.factor_service.get_factor(filename)
            if not factor:
                return ToolResult.fail(f"因子不存在: {filename}")

            result = {"filename": filename}

            # 检查是否有已存储的回测指标
            if hasattr(factor, 'backtest_ic') and factor.backtest_ic:
                result["ic_mean"] = factor.backtest_ic
            if hasattr(factor, 'backtest_ir') and factor.backtest_ir:
                result["icir"] = factor.backtest_ir

            # 如果没有存储的数据，提示需要运行分析
            if "ic_mean" not in result:
                result["note"] = "因子尚未进行IC分析，请使用因子分组分析工具获取IC数据"

            return ToolResult.ok(result)

        except Exception as e:
            logger.exception("获取因子IC失败")
            return ToolResult.fail(str(e))


class CompareFactorsTool(BaseTool):
    """因子对比工具 - 多因子对比分析"""

    category = "analysis"

    @property
    def name(self) -> str:
        return "compare_factors"

    @property
    def description(self) -> str:
        return "对比多个因子的分析指标，包括IC、收益、稳定性等维度"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filenames": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "因子文件名列表（不含 .py 后缀）",
                },
            },
            "required": ["filenames"],
        }

    async def execute(self, filenames: list[str]) -> ToolResult:
        try:
            if len(filenames) < 2:
                return ToolResult.fail("至少需要2个因子进行对比")

            # 规范化所有文件名
            filenames = [self.normalize_filename(f) for f in filenames]

            comparisons = []
            for filename in filenames:
                factor = self.factor_service.get_factor(filename)
                if factor:
                    comparisons.append({
                        "filename": filename,
                        "style": factor.style,
                        "llm_score": factor.llm_score,
                        "verification_status": factor.verification_status,
                    })

            if len(comparisons) < 2:
                return ToolResult.fail("有效因子不足2个")

            return ToolResult.ok({
                "factors": comparisons,
                "note": "完整的IC/收益对比需要运行因子分析服务",
            })

        except Exception as e:
            logger.exception("因子对比失败")
            return ToolResult.fail(str(e))


# ============= 多因子分析工具 =============


class GetFactorCorrelationTool(BaseTool):
    """获取因子相关性 - 计算多因子相关性矩阵 (placeholder)"""

    category = "analysis"
    execution_mode = ExecutionMode.COMPUTE
    execution_timeout = 120.0

    @property
    def name(self) -> str:
        return "get_factor_correlation"

    @property
    def description(self) -> str:
        return """[Placeholder] 计算多个因子之间的相关性矩阵，识别高相关因子对。
用于检测因子冗余和多重共线性问题。
注意: 此工具尚未完全实现，当前仅返回服务就绪状态。"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "factor_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "因子名称列表(至少2个，不含 .py 后缀)",
                },
                "correlation_threshold": {
                    "type": "number",
                    "description": "高相关性阈值，默认0.7",
                    "default": 0.7,
                },
            },
            "required": ["factor_names"],
        }

    async def execute(
        self,
        factor_names: list[str],
        correlation_threshold: float = 0.7,
    ) -> ToolResult:
        try:
            if len(factor_names) < 2:
                return ToolResult.fail("至少需要2个因子进行相关性分析")

            # 规范化所有因子名
            factor_names = [self.normalize_filename(f) for f in factor_names]

            # Placeholder: 返回服务就绪状态
            return ToolResult.ok({
                "status": "placeholder",
                "message": "此工具尚未完全实现，需要提供包含因子值的DataFrame进行分析",
                "factors": factor_names,
                "threshold": correlation_threshold,
            })

        except Exception as e:
            logger.exception("获取因子相关性失败")
            return ToolResult.fail(str(e))


class MultiFactorAnalyzeTool(BaseTool):
    """多因子完整分析工具 - 一站式多因子分析 (placeholder)"""

    category = "analysis"
    execution_mode = ExecutionMode.COMPUTE
    execution_timeout = 180.0

    @property
    def name(self) -> str:
        return "multi_factor_analyze"

    @property
    def description(self) -> str:
        return """[Placeholder] 执行完整的多因子分析，包括相关性、正交化、合成、冗余检测和增量贡献分析。
注意: 此工具尚未完全实现，当前仅返回服务就绪状态。"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "factor_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "因子名称列表(至少2个，不含 .py 后缀)",
                },
                "synthesis_method": {
                    "type": "string",
                    "description": "因子合成方法",
                    "enum": [
                        "equal_weight",
                        "ic_weight",
                        "icir_weight",
                        "max_ic",
                        "min_corr",
                    ],
                    "default": "ic_weight",
                },
            },
            "required": ["factor_names"],
        }

    async def execute(
        self,
        factor_names: list[str],
        synthesis_method: str = "ic_weight",
    ) -> ToolResult:
        try:
            if len(factor_names) < 2:
                return ToolResult.fail("至少需要2个因子进行多因子分析")

            # 规范化所有因子名
            factor_names = [self.normalize_filename(f) for f in factor_names]

            # Placeholder: 返回服务就绪状态
            return ToolResult.ok({
                "status": "placeholder",
                "message": "此工具尚未完全实现，需要提供包含因子值和收益率的DataFrame进行分析",
                "factors": factor_names,
                "synthesis_method": synthesis_method,
            })

        except Exception as e:
            logger.exception("多因子分析失败")
            return ToolResult.fail(str(e))


# ============= 因子分组分析工具 =============


class AnalyzeFactorGroupsTool(BaseTool):
    """因子分组分析工具 - 分析因子在不同分位组的收益表现"""

    category = "analysis"
    execution_mode = ExecutionMode.COMPUTE  # CPU 密集型计算
    execution_timeout = 120.0

    @property
    def name(self) -> str:
        return "analyze_factor_groups"

    @property
    def description(self) -> str:
        return """分析因子在不同分位组的收益表现。
支持分位数分箱和等宽分箱两种方法，生成分组净值曲线和柱状图。"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "factor_dict": {
                    "type": "object",
                    "description": "因子字典 {因子名: [参数列表]}",
                },
                "data_type": {
                    "type": "string",
                    "description": "数据类型: spot, swap, all",
                    "enum": ["spot", "swap", "all"],
                    "default": "swap",
                },
                "bins": {
                    "type": "integer",
                    "description": "分组数量，默认5组",
                    "default": 5,
                },
                "method": {
                    "type": "string",
                    "description": "分箱方法: pct(分位数) 或 val(等宽)",
                    "enum": ["pct", "val"],
                    "default": "pct",
                },
            },
            "required": ["factor_dict"],
        }

    async def execute(
        self,
        factor_dict: dict[str, list[Any]],
        data_type: str = "swap",
        bins: int = 5,
        method: str = "pct",
    ) -> ToolResult:
        try:
            # 规范化 factor_dict 中的因子名
            normalized_factor_dict = {
                self.normalize_filename(k): v for k, v in factor_dict.items()
            }

            from ....services import get_factor_group_analysis_service

            service = get_factor_group_analysis_service()
            # 使用异步方法避免阻塞事件循环
            results = await service.analyze_multiple_factors_async(
                factor_dict=normalized_factor_dict,
                data_type=data_type,
                bins=bins,
                method=method,
            )

            return ToolResult.ok({
                "results": [
                    {
                        "factor_name": r.factor_name,
                        "bins": r.bins,
                        "method": r.method,
                        "data_type": r.data_type,
                        "html_path": r.html_path,
                        "error": r.error,
                    }
                    for r in results
                ],
            })

        except Exception as e:
            logger.exception("因子分组分析失败")
            return ToolResult.fail(str(e))


# ============= 因子参数分析工具 =============


class RunFactorParamAnalysisTool(BaseTool):
    """因子参数分析工具 - 复用 run_backtest 结构，支持变量占位符的参数遍历"""

    category = "analysis"
    execution_mode = ExecutionMode.COMPUTE  # CPU 密集型
    execution_timeout = 600.0  # 参数遍历可能需要较长时间

    @property
    def name(self) -> str:
        return "run_factor_param_analysis"

    @property
    def description(self) -> str:
        return """因子参数敏感性分析工具。

复用 run_backtest 的 strategy_list 结构，通过变量占位符机制支持参数遍历。
自动根据 param_grid 维度选择图表类型:
- 1维: 柱状图（参数平原图）
- 2维: 热力图

**变量占位符机制**:
- 在 param_grid 中定义变量（以 $ 开头）及其取值范围
- 在 strategy_list 中使用变量占位符，同一变量可在多处使用（保证联动）
- 遍历时自动替换所有占位符

示例1 - 单变量遍历（选币因子和过滤因子使用相同参数）:
  param_grid: {"$window": [72, 144, 216, 288]}
  strategy_list: [{
    "factor_list": [["ILLQStd", true, "$window", 1]],
    "filter_list": [["QuoteVolumeMean", "$window", "pct:<0.2", true]],
    ...
  }]
  // filter_list 说明: 保留成交量最低的20%（true=升序，值小排名高）

示例2 - 双变量遍历（热力图）:
  param_grid: {"$window": [48, 96, 144], "$hold": ["1H", "4H", "24H"]}
  strategy_list: [{
    "factor_list": [["ILLQStd", true, "$window", 1]],
    "hold_period": "$hold",
    ...
  }]

示例3 - 多因子联动（多个因子使用相同窗口）:
  param_grid: {"$window": [48, 96, 144]}
  strategy_list: [{
    "factor_list": [
      ["Factor1", true, "$window", 1],
      ["Factor2", false, "$window", 1]
    ],
    ...
  }]

**完整调用示例**:
{
  "name": "ILLQStd_window_analysis",
  "param_grid": {"$window": [72, 144, 216, 288]},
  "strategy_list": [{
    "factor_list": [["ILLQStd", true, "$window", 1]],
    "filter_list": [["PctChange", "$window", "pct:<0.8", false]],
    "long_select_coin_num": 0.1,
    "short_select_coin_num": 0,
    "long_cap_weight": 1,
    "short_cap_weight": 0,
    "hold_period": "4H",
    "market": "swap_swap"
  }],
  "indicator": "annual_return"
}
// filter_list: 保留涨幅排名前80%（false=降序，涨幅大排名高，pct:<0.8保留前80%）"""

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "分析任务名称",
                },
                "strategy_list": {
                    "type": "array",
                    "description": "策略配置列表（与 run_backtest 相同结构）。支持使用 $变量名 作为占位符，在 param_grid 中定义变量取值。",
                    "items": {
                        "type": "object",
                        "properties": {
                            "factor_list": {
                                "type": "array",
                                "description": (
                                    "因子列表，每个因子为 [名称, 排序方向, 参数, 权重]。"
                                    "排序方向: True=因子值小的做多/大的做空, False=反之。"
                                    "参数: 计算窗口(小时)，可使用变量如 \"$window\"。权重: 固定为 1。"
                                    "示例: [[\"Momentum\", true, \"$window\", 1]]"
                                ),
                            },
                            "filter_list": {
                                "type": "array",
                                "description": (
                                    "前置过滤因子列表，每个过滤因子为 [名称, 参数, 过滤条件, 排序方向]。"
                                    "参数: 计算窗口(小时)，可使用变量如 \"$window\"。"
                                    "过滤条件: \"pct:<0.2\"(百分位<20%), \"rank:<10\"(排名<10), \"val:>100\"(原值>100)。"
                                    "排序方向: true=升序(值小排名高), false=降序(值大排名高)。对val无效，对pct/rank有效。"
                                    "示例: [[\"QuoteVolumeMean\", \"$window\", \"pct:<0.2\", true]] 保留成交量最低的20%"
                                ),
                            },
                            "filter_list_post": {
                                "type": "array",
                                "description": (
                                    "后置过滤因子列表（在选币后应用），格式同 filter_list。"
                                    "参数位置可使用变量如 \"$window\"。"
                                ),
                            },
                            "long_select_coin_num": {
                                "type": "number",
                                "description": "多头选币数量。[0,1): 比例(如 0.1=10%); >=1: 绝对数量",
                                "default": 0.1,
                            },
                            "short_select_coin_num": {
                                "type": "number",
                                "description": "空头选币数量(0=不做空)。[0,1): 比例; >=1: 绝对数量",
                                "default": 0,
                            },
                            "long_cap_weight": {
                                "type": "number",
                                "description": "多头仓位权重。实际占比=long/(long+short)。纯多头: long=1,short=0",
                                "default": 1,
                            },
                            "short_cap_weight": {
                                "type": "number",
                                "description": "空头仓位权重。多空平衡: long=1,short=1; 纯空头: long=0,short=1",
                                "default": 0,
                            },
                            "hold_period": {
                                "type": "string",
                                "description": "持仓周期，如 \"1H\", \"4H\", \"24H\"。可使用变量如 \"$hold\"",
                                "default": "4H",
                            },
                            "market": {
                                "type": "string",
                                "description": (
                                    "币池与交易类型: "
                                    "spot_spot(现货币池+现货交易), "
                                    "swap_swap(合约币池+合约交易), "
                                    "spot_swap(现货币池+优先合约), "
                                    "mix_spot(合并币池+优先现货), "
                                    "mix_swap(合并币池+优先合约)"
                                ),
                                "default": "swap_swap",
                            },
                        },
                    },
                },
                "param_grid": {
                    "type": "object",
                    "description": (
                        "参数变量网格。键为变量名（以$开头），值为取值列表。"
                        "示例: {\"$window\": [72, 144, 216], \"$hold\": [\"1H\", \"4H\"]}。"
                        "1个变量=柱状图，2个变量=热力图，最多2个变量。"
                    ),
                },
                "start_date": {
                    "type": "string",
                    "description": "回测开始日期 (YYYY-MM-DD)，不传则使用数据最早日期",
                },
                "end_date": {
                    "type": "string",
                    "description": "回测结束日期 (YYYY-MM-DD)，不传则使用数据最新日期",
                },
                "leverage": {
                    "type": "number",
                    "description": "杠杆倍数，仅合约交易有效",
                    "default": 1,
                },
                "indicator": {
                    "type": "string",
                    "description": "评价指标: annual_return(年化收益), sharpe_ratio(夏普比率), max_drawdown(最大回撤), win_rate(胜率)",
                    "enum": ["annual_return", "sharpe_ratio", "max_drawdown", "win_rate"],
                    "default": "annual_return",
                },
            },
            "required": ["name", "strategy_list", "param_grid"],
        }

    async def execute(
        self,
        name: str,
        strategy_list: list[dict[str, Any]],
        param_grid: dict[str, list[Any]],
        start_date: str | None = None,
        end_date: str | None = None,
        leverage: float = 1.0,
        indicator: str = "annual_return",
    ) -> ToolResult:
        try:
            import copy
            import itertools

            from domains.strategy_hub.services.backtest_runner import (
                BacktestRequest,
                get_backtest_runner,
            )

            # 验证 param_grid
            if not param_grid:
                return ToolResult.fail("param_grid 不能为空")

            grid_keys = list(param_grid.keys())
            grid_dim = len(grid_keys)

            # 验证变量名格式（必须以 $ 开头）
            for key in grid_keys:
                if not key.startswith("$"):
                    return ToolResult.fail(
                        f"param_grid 的键必须以 $ 开头: '{key}'，"
                        f"应为 '${key}'"
                    )

            if grid_dim > 2:
                return ToolResult.fail(
                    f"param_grid 最多支持2个维度，当前有 {grid_dim} 个: {grid_keys}"
                )

            # 验证每个维度至少有2个值
            for key, values in param_grid.items():
                if not values or len(values) < 2:
                    return ToolResult.fail(
                        f"param_grid['{key}'] 至少需要2个值，当前: {values}"
                    )

            # 计算笛卡尔积
            grid_values = [param_grid[k] for k in grid_keys]
            combinations = list(itertools.product(*grid_values))
            total_combinations = len(combinations)

            if total_combinations > 100:
                return ToolResult.fail(
                    f"参数组合数 {total_combinations} 过多(最大100)，请减少参数范围"
                )

            logger.info(
                f"参数分析: {name}, {grid_dim}维, 共 {total_combinations} 种组合"
            )

            runner = get_backtest_runner()
            results = []
            first_strategy = None

            # 遍历所有参数组合
            for combo in combinations:
                combo_dict = dict(zip(grid_keys, combo))

                try:
                    # 深拷贝 strategy_list 并替换变量占位符
                    injected_strategy_list = copy.deepcopy(strategy_list)
                    self._substitute_variables(injected_strategy_list, combo_dict)

                    # 构建回测名称（去掉变量的 $ 前缀）
                    combo_name = "_".join(
                        f"{k.lstrip('$')}_{v}" for k, v in combo_dict.items()
                    )
                    request = BacktestRequest(
                        name=f"{name}_{combo_name}",
                        strategy_list=injected_strategy_list,
                        start_date=start_date,
                        end_date=end_date,
                        leverage=leverage,
                    )

                    strategy = await runner.run_and_wait(request)

                    if first_strategy is None:
                        first_strategy = strategy

                    result_entry = {
                        **combo_dict,
                        "annual_return": strategy.annual_return,
                        "max_drawdown": strategy.max_drawdown,
                        "sharpe_ratio": strategy.sharpe_ratio,
                        "win_rate": strategy.win_rate,
                        "cumulative_return": strategy.cumulative_return,
                    }
                    results.append(result_entry)

                    logger.info(
                        f"组合 {combo_dict} -> {indicator}="
                        f"{result_entry.get(indicator, 0):.4f}"
                    )

                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    logger.warning(f"组合 {combo_dict} 回测失败: {e}\n{error_detail}")
                    results.append({
                        **combo_dict,
                        "error": str(e),
                    })

            # 计算最优参数
            valid_results = [r for r in results if "error" not in r]
            if not valid_results:
                return ToolResult.fail("所有参数组合回测均失败")

            best_result = max(
                valid_results, key=lambda x: x.get(indicator, 0) or 0
            )

            # 获取实际日期范围
            actual_start_date = start_date
            actual_end_date = end_date
            if first_strategy:
                if not actual_start_date and first_strategy.start_date:
                    actual_start_date = first_strategy.start_date
                if not actual_end_date and first_strategy.end_date:
                    actual_end_date = first_strategy.end_date

            # 根据维度生成图表
            if grid_dim == 1:
                chart_type = "bar"
                chart = self._generate_bar_chart(
                    results, grid_keys[0], param_grid[grid_keys[0]], indicator
                )
            else:
                chart_type = "heatmap"
                chart = self._generate_heatmap_chart(
                    results,
                    grid_keys[0], param_grid[grid_keys[0]],
                    grid_keys[1], param_grid[grid_keys[1]],
                    indicator,
                )

            # 构建分析结果
            param_analysis = {
                "updated_at": datetime.now().isoformat(),
                "chart_type": chart_type,
                "config": {
                    "strategy_list": strategy_list,
                    "param_grid": param_grid,
                    "start_date": actual_start_date,
                    "end_date": actual_end_date,
                    "leverage": leverage,
                },
                "grid_keys": grid_keys,
                "results": results,
                "best_result": best_result,
                "indicator": indicator,
                "chart": chart,
            }

            # 尝试提取因子名并更新元数据
            factor_filename = self._extract_factor_filename(strategy_list)
            if factor_filename:
                factor_filename = self.normalize_filename(factor_filename)
                factor = self.factor_service.get_factor(factor_filename)
                if factor:
                    self.factor_service.update_factor(
                        factor_filename,
                        param_analysis=json.dumps(param_analysis, ensure_ascii=False),
                    )
                    logger.info(f"已更新因子 {factor_filename} 的参数分析数据")

            return ToolResult.ok({
                "name": name,
                "chart_type": chart_type,
                "grid_keys": grid_keys,
                "total_combinations": total_combinations,
                "valid_results": len(valid_results),
                "best_result": best_result,
                "all_results": valid_results,
                "factor_updated": factor_filename,
                "message": f"参数分析完成，最优组合: {best_result}",
            })

        except Exception as e:
            logger.exception("因子参数分析失败")
            return ToolResult.fail(str(e))

    def _substitute_variables(
        self,
        obj: Any,
        variables: dict[str, Any],
    ) -> None:
        """递归替换对象中的变量占位符

        变量占位符格式: $varname (如 $window, $hold)
        在 strategy_list 的任意位置匹配并替换

        Args:
            obj: 要处理的对象（会被原地修改）
            variables: 变量字典，如 {"$window": 72, "$hold": "4H"}
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str) and value in variables:
                    # 字符串值完全匹配变量名
                    obj[key] = variables[value]
                elif isinstance(value, (dict, list)):
                    # 递归处理嵌套结构
                    self._substitute_variables(value, variables)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, str) and item in variables:
                    # 列表元素完全匹配变量名
                    obj[i] = variables[item]
                elif isinstance(item, (dict, list)):
                    # 递归处理嵌套结构
                    self._substitute_variables(item, variables)

    def _extract_factor_filename(
        self, strategy_list: list[dict[str, Any]]
    ) -> str | None:
        """从 strategy_list 中提取第一个因子的文件名"""
        if not strategy_list:
            return None

        first_strategy = strategy_list[0]
        factor_list = first_strategy.get("factor_list", [])

        if factor_list and len(factor_list) > 0:
            first_factor = factor_list[0]
            if isinstance(first_factor, (list, tuple)) and len(first_factor) > 0:
                return str(first_factor[0])

        return None

    def _generate_bar_chart(
        self,
        results: list[dict[str, Any]],
        x_key: str,
        x_values: list[Any],
        indicator: str,
    ) -> dict[str, Any]:
        """生成 ECharts 柱状图（参数平原图）配置"""
        # 构建值映射
        value_map = {}
        for r in results:
            if "error" not in r:
                x = r.get(x_key)
                value_map[x] = r.get(indicator, 0) or 0

        # 准备数据
        x_data = [str(v) for v in x_values]
        y_data = []
        colors = []

        best_value = None
        best_idx = None

        for i, x in enumerate(x_values):
            val = value_map.get(x)
            if val is not None:
                display_val = (
                    round(val * 100, 2)
                    if indicator != "sharpe_ratio"
                    else round(val, 2)
                )
                y_data.append(display_val)
                colors.append("#5470c6")

                if best_value is None or val > best_value:
                    best_value = val
                    best_idx = i
            else:
                y_data.append(None)
                colors.append("#ccc")

        # 标记最优参数
        if best_idx is not None:
            colors[best_idx] = "#91cc75"

        # 生成 x 轴标签（去掉 $ 前缀）
        x_label = x_key.lstrip("$")

        return {
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "shadow"},
            },
            "xAxis": {
                "type": "category",
                "data": x_data,
                "name": x_label,
                "nameLocation": "middle",
                "nameGap": 25,
            },
            "yAxis": {
                "type": "value",
                "axisLabel": {
                    "formatter": (
                        "{value}%" if indicator != "sharpe_ratio" else "{value}"
                    ),
                },
            },
            "series": [
                {
                    "type": "bar",
                    "data": [
                        {"value": v, "itemStyle": {"color": c}}
                        for v, c in zip(y_data, colors)
                    ],
                    "label": {
                        "show": True,
                        "position": "top",
                        "formatter": (
                            "{c}" + ("%" if indicator != "sharpe_ratio" else "")
                        ),
                        "fontSize": 11,
                    },
                    "barMaxWidth": 60,
                }
            ],
            "grid": {
                "left": "8%",
                "right": "8%",
                "top": "8%",
                "bottom": "18%",
                "containLabel": True,
            },
        }

    def _generate_heatmap_chart(
        self,
        results: list[dict[str, Any]],
        x_key: str,
        x_values: list[Any],
        y_key: str,
        y_values: list[Any],
        indicator: str,
    ) -> dict[str, Any]:
        """生成 ECharts 热力图配置"""
        # 构建值映射
        value_map = {}
        for r in results:
            if "error" not in r:
                x = r.get(x_key)
                y = r.get(y_key)
                value_map[(x, y)] = r.get(indicator, 0) or 0

        # 转换为 ECharts heatmap 数据格式
        x_data = [str(v) for v in x_values]
        y_data = [str(v) for v in y_values]
        heatmap_data = []

        for xi, x in enumerate(x_values):
            for yi, y in enumerate(y_values):
                val = value_map.get((x, y))
                if val is not None:
                    display_val = (
                        round(val * 100, 2)
                        if indicator != "sharpe_ratio"
                        else round(val, 2)
                    )
                    heatmap_data.append([xi, yi, display_val])

        # 计算数值范围
        all_values = [d[2] for d in heatmap_data]
        min_val = min(all_values) if all_values else 0
        max_val = max(all_values) if all_values else 1

        # 生成轴标签（去掉 $ 前缀）
        x_label = x_key.lstrip("$")
        y_label = y_key.lstrip("$")

        return {
            "tooltip": {
                "position": "top",
            },
            "xAxis": {
                "type": "category",
                "data": x_data,
                "name": x_label,
                "nameLocation": "middle",
                "nameGap": 25,
                "splitArea": {"show": True},
            },
            "yAxis": {
                "type": "category",
                "data": y_data,
                "name": y_label,
                "splitArea": {"show": True},
            },
            "visualMap": {
                "min": min_val,
                "max": max_val,
                "calculable": True,
                "orient": "horizontal",
                "left": "center",
                "bottom": "5%",
                "inRange": {
                    "color": [
                        "#313695", "#4575b4", "#74add1", "#abd9e9",
                        "#e0f3f8", "#ffffbf", "#fee090", "#fdae61",
                        "#f46d43", "#d73027", "#a50026",
                    ],
                },
            },
            "series": [
                {
                    "type": "heatmap",
                    "data": heatmap_data,
                    "label": {
                        "show": True,
                        "fontSize": 10,
                        "formatter": (
                            "{@[2]}" + ("%" if indicator != "sharpe_ratio" else "")
                        ),
                    },
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowColor": "rgba(0, 0, 0, 0.5)",
                        },
                    },
                }
            ],
            "grid": {
                "left": "10%",
                "right": "10%",
                "top": "5%",
                "bottom": "20%",
                "containLabel": True,
            },
        }


