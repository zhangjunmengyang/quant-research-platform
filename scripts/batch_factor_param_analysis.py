#!/usr/bin/env python3
"""
批量因子参数分析脚本

根据因子风格(style)自动选择不同的回测配置，遍历所有有标签的因子进行参数分析。

风格与回测配置对应关系:
- 流动性: 多头策略，12H周期，多offset，过滤涨幅
- 动量/反转: 4种回测(排序true/false x 多空平衡/纯多)
- 波动率: true/false双向，无过滤
- 趋势: 后置过滤，信号触发

使用方式:
    # 回测所有有风格标签的因子
    python scripts/batch_factor_param_analysis.py

    # 仅回测指定风格
    python scripts/batch_factor_param_analysis.py --style 流动性

    # 仅回测指定因子
    python scripts/batch_factor_param_analysis.py --factor ILLQStd

    # 预览模式（不实际运行）
    python scripts/batch_factor_param_analysis.py --dry-run

    # 指定参数网格
    python scripts/batch_factor_param_analysis.py --params 72,144,216,288

    # 使用更多并行进程
    python scripts/batch_factor_param_analysis.py --jobs 16
"""
import os
import sys
from pathlib import Path

# ==================== 环境变量预处理 ====================
# 必须在任何 backend 模块导入之前设置，因为 config 在导入时读取环境变量

def _preparse_jobs() -> int | None:
    """预解析 --jobs 参数，在 argparse 之前执行"""
    for i, arg in enumerate(sys.argv):
        if arg in ("--jobs", "-j") and i + 1 < len(sys.argv):
            try:
                return int(sys.argv[i + 1])
            except ValueError:
                return None
        if arg.startswith("--jobs="):
            try:
                return int(arg.split("=", 1)[1])
            except ValueError:
                return None
    return None


# 预解析并设置环境变量
_jobs = _preparse_jobs()
if _jobs is not None:
    os.environ["BACKTEST_JOB_NUM"] = str(_jobs)

# 现在才能安全导入其他模块
PROJECT_ROOT = Path(__file__).parent.parent
_root_path = str(PROJECT_ROOT)
_backend_path = str(PROJECT_ROOT / "backend")
_domains_path = str(PROJECT_ROOT / "backend" / "domains")

# 设置 sys.path（主进程）
# 注意顺序：domains > backend > root（优先级从高到低）
sys.path.insert(0, _root_path)
sys.path.insert(0, _backend_path)
sys.path.insert(0, _domains_path)

# 设置 PYTHONPATH 环境变量（子进程继承）
# 这使 engine/core/path_kit.py 中的 `from strategy_hub.services...` 能在子进程中工作
_existing_pythonpath = os.environ.get("PYTHONPATH", "")
_new_paths = f"{_domains_path}:{_backend_path}:{_root_path}"
if _existing_pythonpath:
    os.environ["PYTHONPATH"] = f"{_new_paths}:{_existing_pythonpath}"
else:
    os.environ["PYTHONPATH"] = _new_paths

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# 如果 .env 设置了 BACKTEST_JOB_NUM 但命令行指定了 --jobs，命令行优先
if _jobs is not None:
    os.environ["BACKTEST_JOB_NUM"] = str(_jobs)

import argparse
import asyncio
import itertools
import json
import logging
from dataclasses import dataclass
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== 回测配置模板 ====================


@dataclass
class BacktestConfig:
    """回测配置"""
    name: str  # 配置名称
    strategy_list: list[dict]  # 策略配置
    param_grid: list[int]  # 参数网格
    description: str = ""  # 配置描述


# ==================== 参数网格定义 ====================
# 不同风格/配置使用不同的参数遍历范围

PARAM_GRID_LIQUIDITY = list(range(100, 2400, 100))  # 流动性: [100, 200, ..., 2300]
PARAM_GRID_LONG_SHORT = list(range(8, 128, 8))  # 多1空1: [8, 16, 24, ..., 120]
PARAM_GRID_MOMENTUM_LONG = list(range(200, 4800, 200))  # 动量纯多: [200, 400, ..., 4600]
PARAM_GRID_DEFAULT = list(range(100, 2400, 100))  # 默认: [100, 200, ..., 2300]


def get_liquidity_configs(factor_name: str) -> list[BacktestConfig]:
    """
    流动性因子回测配置

    特点:
    - 多头策略，12H周期
    - 多 offset (0-11)
    - 过滤涨幅前80%
    - true/false 双向测试
    - 参数范围: [100, 200, ..., 2300]
    """
    configs = []

    for is_sort_asc in [True, False]:
        direction_name = "小做多" if is_sort_asc else "大做多"

        configs.append(BacktestConfig(
            name=f"{factor_name}_{direction_name}_流动性多头",
            description=f"流动性多头策略，12H周期，排序方向={is_sort_asc}",
            param_grid=PARAM_GRID_LIQUIDITY,
            strategy_list=[{
                "strategy": f"流动性多头_{direction_name}",
                "offset_list": list(range(12)),  # [0, 1, 2, ..., 11]
                "hold_period": "12H",
                "market": "swap_swap",
                "cap_weight": 2,
                "long_cap_weight": 1,
                "short_cap_weight": 0,
                "long_select_coin_num": 0.2,
                "short_select_coin_num": 0,
                "factor_list": [(factor_name, is_sort_asc, "$window", 1)],
                "filter_list": [("PctChangeMulti", "$window", "pct:<0.8", False)],
                "filter_list_post": [],
                "use_custom_func": False,
            }],
        ))

    return configs


def get_momentum_reversal_configs(factor_name: str) -> list[BacktestConfig]:
    """
    动量和反转因子回测配置

    特点:
    - 4种配置组合: 排序方向(true/false) x 策略类型(多空平衡/纯多)
    - 多空平衡: 1H周期，多1空1，参数范围 [8, 16, ..., 120]
    - 纯多: 1H周期，多0.1空0，参数范围 [200, 400, ..., 4600]
    """
    configs = []

    # 排序方向: True=因子值小的做多, False=因子值大的做多
    for is_sort_asc in [True, False]:
        direction_name = "小做多" if is_sort_asc else "大做多"

        # 配置1: 多空平衡 - 使用短窗口参数
        configs.append(BacktestConfig(
            name=f"{factor_name}_{direction_name}_多空平衡",
            description=f"多空平衡策略，1H周期，排序方向={is_sort_asc}",
            param_grid=PARAM_GRID_LONG_SHORT,
            strategy_list=[{
                "strategy": f"Strategy_{direction_name}_多空",
                "offset_list": [0],
                "hold_period": "1H",
                "market": "swap_swap",
                "cap_weight": 1,
                "long_cap_weight": 1,
                "short_cap_weight": 1,
                "long_select_coin_num": 1,
                "short_select_coin_num": 1,
                "factor_list": [(factor_name, is_sort_asc, "$window", 1)],
                "filter_list": [("QuoteVolumeMean", 24, "rank:<30", False)],
                "use_custom_func": False,
            }],
        ))

        # 配置2: 纯多头 - 使用长窗口参数
        configs.append(BacktestConfig(
            name=f"{factor_name}_{direction_name}_纯多头",
            description=f"纯多头策略，1H周期，排序方向={is_sort_asc}",
            param_grid=PARAM_GRID_MOMENTUM_LONG,
            strategy_list=[{
                "strategy": f"Strategy_{direction_name}_纯多",
                "offset_list": [0],
                "hold_period": "1H",
                "is_use_spot": False,
                "cap_weight": 1,
                "long_cap_weight": 1,
                "short_cap_weight": 0,
                "long_select_coin_num": 0.1,
                "short_select_coin_num": 0,
                "factor_list": [(factor_name, is_sort_asc, "$window", 1)],
                "filter_list": [
                    ("QuoteVolumeEMA", 1440, "pct:<0.2", False),
                    ("ILLQMean", 24, "pct:<=0.2", False),
                ],
                "filter_list_post": [],
                "use_custom_func": False,
            }],
        ))

    return configs


def get_volatility_configs(factor_name: str) -> list[BacktestConfig]:
    """
    波动率因子回测配置

    特点:
    - 无过滤
    - true/false 双向测试
    - 参数范围: [100, 200, ..., 2300]
    """
    configs = []

    for is_sort_asc in [True, False]:
        direction_name = "小做多" if is_sort_asc else "大做多"

        configs.append(BacktestConfig(
            name=f"{factor_name}_{direction_name}_波动率",
            description=f"波动率策略，无过滤，排序方向={is_sort_asc}",
            param_grid=PARAM_GRID_DEFAULT,
            strategy_list=[{
                "strategy": f"Strategy_波动率_{direction_name}",
                "offset_list": [0],
                "hold_period": "4H",
                "market": "swap_swap",
                "cap_weight": 1,
                "long_cap_weight": 1,
                "short_cap_weight": 1,
                "long_select_coin_num": 0.1,
                "short_select_coin_num": 0.1,
                "factor_list": [(factor_name, is_sort_asc, "$window", 1)],
                "filter_list": [],
                "filter_list_post": [],
                "use_custom_func": False,
            }],
        ))

    return configs


def get_trend_configs(factor_name: str) -> list[BacktestConfig]:
    """
    趋势因子回测配置

    特点:
    - 后置过滤，用于0/1信号触发
    - 多头后置过滤: factor > 0 做多
    - 空头后置过滤: factor > 0 做空
    - 参数范围: [100, 200, ..., 2300]
    """
    configs = []

    # 多头后置过滤: 因子值 > 0 时做多
    configs.append(BacktestConfig(
        name=f"{factor_name}_趋势多头",
        description="趋势多头策略，后置过滤factor>0",
        param_grid=PARAM_GRID_DEFAULT,
        strategy_list=[{
            "strategy": f"Strategy_趋势_多头",
            "offset_list": [0],
            "hold_period": "4H",
            "market": "swap_swap",
            "cap_weight": 1,
            "long_cap_weight": 1,
            "short_cap_weight": 0,
            "long_select_coin_num": 0.2,
            "short_select_coin_num": 0,
            "factor_list": [("QuoteVolumeMean", False, 24, 1)],  # 使用成交量排序
            "filter_list": [("QuoteVolumeMean", 24, "pct:<0.3", False)],
            "filter_list_post": [(factor_name, "$window", "val:>0", True)],  # 后置过滤
            "use_custom_func": False,
        }],
    ))

    # 空头后置过滤: 因子值 > 0 时做空
    configs.append(BacktestConfig(
        name=f"{factor_name}_趋势空头",
        description="趋势空头策略，后置过滤factor>0做空",
        param_grid=PARAM_GRID_DEFAULT,
        strategy_list=[{
            "strategy": f"Strategy_趋势_空头",
            "offset_list": [0],
            "hold_period": "4H",
            "market": "swap_swap",
            "cap_weight": 1,
            "long_cap_weight": 0,
            "short_cap_weight": 1,
            "long_select_coin_num": 0,
            "short_select_coin_num": 0.2,
            "factor_list": [("QuoteVolumeMean", True, 24, 1)],  # 使用成交量排序
            "filter_list": [("QuoteVolumeMean", 24, "pct:<0.3", False)],
            "filter_list_post": [(factor_name, "$window", "val:>0", True)],  # 后置过滤
            "use_custom_func": False,
        }],
    ))

    return configs


def get_default_configs(factor_name: str) -> list[BacktestConfig]:
    """
    默认回测配置（用于成长、情绪等其他风格）

    特点:
    - true/false 双向测试
    - 标准多头策略
    - 参数范围: [100, 200, ..., 2300]
    """
    configs = []

    for is_sort_asc in [True, False]:
        direction_name = "小做多" if is_sort_asc else "大做多"

        configs.append(BacktestConfig(
            name=f"{factor_name}_{direction_name}_默认",
            description=f"默认策略，4H周期，排序方向={is_sort_asc}",
            param_grid=PARAM_GRID_DEFAULT,
            strategy_list=[{
                "strategy": f"Strategy_默认_{direction_name}",
                "offset_list": [0],
                "hold_period": "4H",
                "market": "swap_swap",
                "cap_weight": 1,
                "long_cap_weight": 1,
                "short_cap_weight": 0,
                "long_select_coin_num": 0.1,
                "short_select_coin_num": 0,
                "factor_list": [(factor_name, is_sort_asc, "$window", 1)],
                "filter_list": [("QuoteVolumeMean", 24, "pct:<0.3", False)],
                "filter_list_post": [],
                "use_custom_func": False,
            }],
        ))

    return configs


# 风格关键词到配置函数的映射（使用包含匹配）
STYLE_CONFIG_MAP = {
    "流动性": get_liquidity_configs,
    "动量": get_momentum_reversal_configs,
    "反转": get_momentum_reversal_configs,
    "波动率": get_volatility_configs,
    "波动": get_volatility_configs,
    "趋势": get_trend_configs,
    "成长": get_default_configs,
    "情绪": get_default_configs,
}

# 支持的风格关键词列表
SUPPORTED_STYLES = list(STYLE_CONFIG_MAP.keys())


def match_style(style: str) -> str | None:
    """
    宽松匹配风格关键词

    Args:
        style: 因子的风格字符串

    Returns:
        匹配到的风格关键词，未匹配返回 None
    """
    if not style:
        return None

    style_lower = style.lower()

    # 按优先级匹配（更具体的优先）
    for keyword in SUPPORTED_STYLES:
        if keyword in style or keyword.lower() in style_lower:
            return keyword

    return None



# ==================== 核心逻辑 ====================


def _substitute_variables(obj: Any, variables: dict[str, Any]) -> Any:
    """递归替换对象中的变量占位符（返回新对象）"""
    if isinstance(obj, str):
        return variables.get(obj, obj)
    elif isinstance(obj, dict):
        return {key: _substitute_variables(value, variables) for key, value in obj.items()}
    elif isinstance(obj, tuple):
        return tuple(_substitute_variables(item, variables) for item in obj)
    elif isinstance(obj, list):
        return [_substitute_variables(item, variables) for item in obj]
    else:
        return obj


async def run_param_analysis_async(
    name: str,
    strategy_list: list[dict],
    param_grid: dict[str, list],
    indicator: str = "annual_return",
) -> dict[str, Any]:
    """
    使用 BacktestRunner 进行参数分析（与 MCP 工具相同方式）

    结果存入数据库，并更新因子的 param_analysis 字段
    """
    from domains.strategy_hub.services.backtest_runner import (
        BacktestRequest,
        get_backtest_runner,
    )
    from domains.factor_hub.services import get_factor_service

    try:
        # 验证 param_grid
        if not param_grid:
            return {"error": "param_grid 不能为空"}

        grid_keys = list(param_grid.keys())

        # 验证变量名格式
        for key in grid_keys:
            if not key.startswith("$"):
                return {"error": f"param_grid 的键必须以 $ 开头: '{key}'"}

        # 验证每个维度至少有2个值
        for key, values in param_grid.items():
            if not values or len(values) < 2:
                return {"error": f"param_grid['{key}'] 至少需要2个值"}

        # 计算笛卡尔积
        grid_values = [param_grid[k] for k in grid_keys]
        combinations = list(itertools.product(*grid_values))
        total_combinations = len(combinations)

        logger.info(f"生成 {total_combinations} 个参数组合")

        runner = get_backtest_runner()
        results = []

        # 遍历所有参数组合
        for i, combo in enumerate(combinations, 1):
            combo_dict = dict(zip(grid_keys, combo))

            try:
                # 替换变量占位符
                injected_strategy_list = _substitute_variables(strategy_list, combo_dict)

                # 构建回测名称
                combo_name = "_".join(f"{k.lstrip('$')}_{v}" for k, v in combo_dict.items())
                request = BacktestRequest(
                    name=f"{name}_{combo_name}",
                    strategy_list=injected_strategy_list,
                )

                logger.info(f"[{i}/{total_combinations}] 回测: {combo_dict}")
                strategy = await runner.run_and_wait(request)

                result_entry = {
                    **combo_dict,
                    "annual_return": strategy.annual_return,
                    "max_drawdown": strategy.max_drawdown,
                    "sharpe_ratio": strategy.sharpe_ratio,
                    "win_rate": strategy.win_rate,
                    "cumulative_return": strategy.cumulative_return,
                }
                results.append(result_entry)

                logger.info(f"  -> {indicator}={result_entry.get(indicator, 0):.4f}")

            except Exception as e:
                logger.warning(f"组合 {combo_dict} 回测失败: {e}")
                results.append({**combo_dict, "error": str(e)})

        # 计算最优参数
        valid_results = [r for r in results if "error" not in r]
        if not valid_results:
            return {"error": "所有参数组合回测均失败"}

        best_result = max(valid_results, key=lambda x: x.get(indicator, 0) or 0)

        # 生成 ECharts 图表配置
        grid_dim = len(grid_keys)
        if grid_dim == 1:
            chart_type = "bar"
            chart = _generate_bar_chart(results, grid_keys[0], param_grid[grid_keys[0]], indicator)
        else:
            chart_type = "heatmap"
            chart = _generate_heatmap_chart(
                results, grid_keys[0], param_grid[grid_keys[0]],
                grid_keys[1], param_grid[grid_keys[1]], indicator
            )

        # 构建分析结果
        from datetime import datetime
        param_analysis = {
            "updated_at": datetime.now().isoformat(),
            "chart_type": chart_type,
            "config": {
                "strategy_list": strategy_list,
                "param_grid": param_grid,
            },
            "grid_keys": grid_keys,
            "results": valid_results,
            "best_result": best_result,
            "indicator": indicator,
            "chart": chart,
        }

        # 返回分析结果（不在这里更新因子，由调用方统一更新）
        return {
            "name": name,
            "chart_type": chart_type,
            "grid_keys": grid_keys,
            "total_combinations": total_combinations,
            "valid_results": len(valid_results),
            "best_result": best_result,
            "param_analysis": param_analysis,  # 返回完整分析数据
        }

    except Exception as e:
        logger.exception(f"参数分析失败: {name}")
        return {"error": str(e)}


def _extract_factor_filename(strategy_list: list[dict]) -> str | None:
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
    results: list[dict],
    x_key: str,
    x_values: list,
    indicator: str,
) -> dict:
    """生成 ECharts 柱状图配置"""
    value_map = {r.get(x_key): r.get(indicator, 0) or 0 for r in results if "error" not in r}

    x_data = [str(v) for v in x_values]
    y_data = []
    colors = []
    best_value, best_idx = None, None

    for i, x in enumerate(x_values):
        val = value_map.get(x)
        if val is not None:
            display_val = round(val * 100, 2) if indicator != "sharpe_ratio" else round(val, 2)
            y_data.append(display_val)
            colors.append("#5470c6")
            if best_value is None or val > best_value:
                best_value, best_idx = val, i
        else:
            y_data.append(None)
            colors.append("#ccc")

    if best_idx is not None:
        colors[best_idx] = "#91cc75"

    return {
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "xAxis": {"type": "category", "data": x_data, "name": x_key.lstrip("$")},
        "yAxis": {"type": "value", "axisLabel": {"formatter": "{value}%" if indicator != "sharpe_ratio" else "{value}"}},
        "series": [{"type": "bar", "data": [{"value": v, "itemStyle": {"color": c}} for v, c in zip(y_data, colors)]}],
    }


def _generate_heatmap_chart(
    results: list[dict],
    x_key: str,
    x_values: list,
    y_key: str,
    y_values: list,
    indicator: str,
) -> dict:
    """生成 ECharts 热力图配置"""
    value_map = {(r.get(x_key), r.get(y_key)): r.get(indicator, 0) or 0 for r in results if "error" not in r}

    x_data = [str(v) for v in x_values]
    y_data = [str(v) for v in y_values]
    heatmap_data = []

    for xi, x in enumerate(x_values):
        for yi, y in enumerate(y_values):
            val = value_map.get((x, y))
            if val is not None:
                display_val = round(val * 100, 2) if indicator != "sharpe_ratio" else round(val, 2)
                heatmap_data.append([xi, yi, display_val])

    all_values = [d[2] for d in heatmap_data]
    min_val = min(all_values) if all_values else 0
    max_val = max(all_values) if all_values else 1

    return {
        "tooltip": {"position": "top"},
        "xAxis": {"type": "category", "data": x_data, "name": x_key.lstrip("$")},
        "yAxis": {"type": "category", "data": y_data, "name": y_key.lstrip("$")},
        "visualMap": {"min": min_val, "max": max_val, "calculable": True, "orient": "horizontal", "left": "center", "bottom": "5%"},
        "series": [{"type": "heatmap", "data": heatmap_data, "label": {"show": True}}],
    }


def get_factors_by_style(style_filter: str | None = None) -> list[tuple[str, str]]:
    """
    获取有风格标签的因子列表

    Args:
        style_filter: 风格筛选关键词，None 表示获取所有有风格的因子

    Returns:
        [(filename, matched_style), ...]
    """
    try:
        from domains.factor_hub.services import get_factor_service

        service = get_factor_service()
        factors, _ = service.query_factors(
            filter_condition={"style": "not_empty"},
            order_by="filename",
        )
    except Exception as e:
        logger.error(f"获取因子列表失败: {e}")
        return []

    # 预处理 style_filter
    filter_keywords = []
    if style_filter:
        filter_keywords = [style_filter, style_filter.lower()]
        # 同时匹配配置表中的关键词（如 "波动" 同时匹配 "波动率"）
        matched_filter = match_style(style_filter)
        if matched_filter and matched_filter != style_filter:
            filter_keywords.append(matched_filter)

    result = []
    for factor in factors:
        if not factor.style:
            continue

        # 宽松匹配风格
        matched_style = match_style(factor.style)
        if not matched_style:
            logger.debug(f"因子 {factor.filename} 的风格 '{factor.style}' 未匹配到支持的类型")
            continue

        # 应用风格筛选
        if filter_keywords:
            style_lower = factor.style.lower()
            if not any(kw in factor.style or kw in style_lower for kw in filter_keywords):
                continue

        result.append((factor.filename, matched_style))

    return result


async def process_factor(
    factor_name: str,
    style: str,
    dry_run: bool = False,
    param_grid_override: list[int] | None = None,
    indicator: str = "annual_return",
) -> dict[str, Any]:
    """
    处理单个因子的参数分析

    Args:
        factor_name: 因子名称
        style: 因子风格
        dry_run: 是否仅预览
        param_grid_override: 覆盖参数网格（如果提供，则忽略配置内置的参数网格）
        indicator: 评价指标

    Returns:
        处理结果
    """
    from domains.factor_hub.services import get_factor_service

    # 使用传入的已匹配风格获取配置函数
    config_func = STYLE_CONFIG_MAP.get(style)
    if not config_func:
        # 尝试重新匹配
        matched = match_style(style)
        if matched:
            config_func = STYLE_CONFIG_MAP.get(matched)

    if not config_func:
        return {
            "factor": factor_name,
            "style": style,
            "error": f"不支持的风格: {style}",
            "configs_run": 0,
        }

    configs = config_func(factor_name)
    results = []
    all_param_analyses = []  # 收集所有配置的分析结果

    for config in configs:
        # 使用覆盖参数或配置内置参数
        param_grid = param_grid_override if param_grid_override else config.param_grid

        if dry_run:
            logger.info(f"[预览] {config.name}: {config.description}, 参数数量={len(param_grid)}")
            results.append({
                "config_name": config.name,
                "description": config.description,
                "param_count": len(param_grid),
                "status": "dry_run",
            })
            continue

        logger.info(f"运行参数分析: {config.name}")
        logger.info(f"  描述: {config.description}")
        logger.info(f"  参数网格: {len(param_grid)} 个值 [{param_grid[0]}...{param_grid[-1]}]")

        result = await run_param_analysis_async(
            name=config.name,
            strategy_list=config.strategy_list,
            param_grid={"$window": param_grid},
            indicator=indicator,
        )

        if "error" in result:
            logger.error(f"  失败: {result['error']}")
            results.append({
                "config_name": config.name,
                "status": "failed",
                "error": result["error"],
            })
        else:
            best = result.get("best_result", {})
            logger.info(f"  完成: 最优 {indicator}={best.get(indicator, 0):.4f}")
            results.append({
                "config_name": config.name,
                "status": "success",
                "best_result": best,
                "valid_results": result.get("valid_results", 0),
            })

            # 收集分析结果，添加配置名称标识
            param_analysis = result.get("param_analysis")
            if param_analysis:
                param_analysis["config_name"] = config.name
                param_analysis["description"] = config.description
                all_param_analyses.append(param_analysis)

    # 所有配置完成后，将分析结果数组保存到因子
    if all_param_analyses and not dry_run:
        try:
            factor_service = get_factor_service()
            # 将数组转为 JSON 字符串保存
            factor_service.update_factor(factor_name, param_analysis=json.dumps(all_param_analyses, ensure_ascii=False))
            logger.info(f"因子 {factor_name} 的 param_analysis 已更新 ({len(all_param_analyses)} 个配置)")
        except Exception as e:
            logger.error(f"更新因子 {factor_name} 失败: {e}")

    return {
        "factor": factor_name,
        "style": style,
        "configs_run": len(configs),
        "results": results,
        "param_analyses_saved": len(all_param_analyses),
    }


async def batch_process(
    factors: list[tuple[str, str]],
    dry_run: bool = False,
    param_grid_override: list[int] | None = None,
    indicator: str = "annual_return",
) -> list[dict[str, Any]]:
    """
    批量处理因子参数分析

    Args:
        factors: 因子列表 [(filename, style), ...]
        dry_run: 是否仅预览
        param_grid_override: 覆盖参数网格
        indicator: 评价指标

    Returns:
        处理结果列表
    """
    results = []

    for i, (factor_name, style) in enumerate(factors, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"[{i}/{len(factors)}] 处理因子: {factor_name} (风格: {style})")
        logger.info(f"{'='*60}")

        result = await process_factor(
            factor_name=factor_name,
            style=style,
            dry_run=dry_run,
            param_grid_override=param_grid_override,
            indicator=indicator,
        )
        results.append(result)

    return results


def print_summary(results: list[dict[str, Any]]):
    """打印处理摘要"""
    print("\n" + "=" * 60)
    print("处理摘要")
    print("=" * 60)

    total_factors = len(results)
    total_configs = sum(r.get("configs_run", 0) for r in results)
    success_configs = sum(
        len([c for c in r.get("results", []) if c.get("status") == "success"])
        for r in results
    )
    failed_configs = sum(
        len([c for c in r.get("results", []) if c.get("status") == "failed"])
        for r in results
    )

    print(f"处理因子数: {total_factors}")
    print(f"运行配置数: {total_configs}")
    print(f"成功: {success_configs}")
    print(f"失败: {failed_configs}")

    # 按风格统计
    style_stats = {}
    for r in results:
        style = r.get("style", "未知")
        if style not in style_stats:
            style_stats[style] = {"count": 0, "success": 0, "failed": 0}
        style_stats[style]["count"] += 1
        for c in r.get("results", []):
            if c.get("status") == "success":
                style_stats[style]["success"] += 1
            elif c.get("status") == "failed":
                style_stats[style]["failed"] += 1

    print("\n按风格统计:")
    for style, stats in style_stats.items():
        print(f"  {style}: {stats['count']} 因子, 成功 {stats['success']}, 失败 {stats['failed']}")

    # 显示失败详情
    failures = []
    for r in results:
        for c in r.get("results", []):
            if c.get("status") == "failed":
                failures.append({
                    "factor": r["factor"],
                    "config": c["config_name"],
                    "error": c.get("error", "未知错误"),
                })

    if failures:
        print("\n失败详情:")
        for f in failures:
            print(f"  - {f['factor']} / {f['config']}: {f['error']}")


def main():
    parser = argparse.ArgumentParser(
        description="批量因子参数分析 - 根据风格自动选择回测配置，生成参数平原图",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
风格与回测配置（含内置参数范围）:
  流动性: 多头策略，12H周期，参数 [100, 200, ..., 2300]
  动量/反转:
    - 多空平衡: 参数 [8, 16, ..., 120]
    - 纯多头: 参数 [200, 400, ..., 4600]
  波动率/趋势/默认: 参数 [100, 200, ..., 2300]

示例:
  # 回测所有有风格标签的因子（使用内置参数范围）
  python scripts/batch_factor_param_analysis.py

  # 仅回测流动性因子
  python scripts/batch_factor_param_analysis.py --style 流动性

  # 仅回测指定因子
  python scripts/batch_factor_param_analysis.py --factor ILLQStd

  # 预览模式
  python scripts/batch_factor_param_analysis.py --dry-run

  # 覆盖参数网格（所有配置使用相同参数）
  python scripts/batch_factor_param_analysis.py --params 72,144,216,288

并行配置:
  使用 --jobs 参数设置回测引擎的并行进程数 (默认: 2)
    python scripts/batch_factor_param_analysis.py --jobs 16

结果输出:
  结果保存到 backend/domains/engine/data/traversal_results/{配置名}/最优参数.xlsx
"""
    )

    parser.add_argument(
        "--style", "-s",
        help=f"仅回测包含指定风格关键词的因子 (支持: {', '.join(SUPPORTED_STYLES)})",
    )
    parser.add_argument(
        "--factor", "-f",
        help="仅回测指定因子（需要该因子有风格标签）",
    )
    parser.add_argument(
        "--params", "-p",
        default=None,
        help="覆盖参数网格，逗号分隔 (不指定则使用各风格内置范围)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际运行回测",
    )
    parser.add_argument(
        "--indicator", "-i",
        default="annual_return",
        choices=["annual_return", "sharpe_ratio", "max_drawdown", "win_rate"],
        help="评价指标 (默认: annual_return)",
    )
    parser.add_argument(
        "--output", "-o",
        help="输出结果到 JSON 文件",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="跳过确认提示，直接执行",
    )
    parser.add_argument(
        "--jobs", "-j",
        type=int,
        default=None,
        help="回测引擎并行进程数 (默认: 2，已在脚本启动时预解析并设置)",
    )

    args = parser.parse_args()

    # 解析参数网格覆盖（可选）
    param_grid_override = None
    if args.params:
        try:
            param_grid_override = [int(p.strip()) for p in args.params.split(",")]
            if len(param_grid_override) < 2:
                print("错误: 参数网格至少需要2个值", file=sys.stderr)
                sys.exit(1)
        except ValueError as e:
            print(f"错误: 无效的参数网格: {e}", file=sys.stderr)
            sys.exit(1)

    # 获取因子列表
    if args.factor:
        # 指定单个因子
        from domains.factor_hub.services import get_factor_service
        service = get_factor_service()
        factor = service.get_factor(args.factor)
        if not factor:
            print(f"错误: 因子不存在: {args.factor}", file=sys.stderr)
            sys.exit(1)
        if not factor.style:
            print(f"错误: 因子 {args.factor} 没有风格标签", file=sys.stderr)
            sys.exit(1)

        # 宽松匹配风格
        matched_style = match_style(factor.style)
        if not matched_style:
            print(f"错误: 因子 {args.factor} 的风格 '{factor.style}' 不支持自动回测", file=sys.stderr)
            print(f"支持的风格关键词: {', '.join(SUPPORTED_STYLES)}", file=sys.stderr)
            sys.exit(1)

        factors = [(args.factor, matched_style)]
    else:
        # 获取所有有风格标签的因子
        factors = get_factors_by_style(args.style)

    if not factors:
        print("没有找到符合条件的因子", file=sys.stderr)
        if args.style:
            print(f"提示: 没有风格为 '{args.style}' 的因子", file=sys.stderr)
        else:
            print("提示: 没有设置风格标签的因子，或风格不在支持列表中", file=sys.stderr)
            print(f"支持的风格: {', '.join(SUPPORTED_STYLES)}", file=sys.stderr)
        sys.exit(1)

    # 显示任务概览
    current_job_num = os.environ.get("BACKTEST_JOB_NUM", "2")

    print("=" * 60)
    print("批量因子参数分析 (使用 BacktestRunner，结果存入数据库)")
    print("=" * 60)
    print(f"因子数量: {len(factors)}")
    if param_grid_override:
        print(f"参数网格: {param_grid_override} (覆盖)")
    else:
        print("参数网格: 各风格内置范围")
    print(f"并行进程: {current_job_num} (BACKTEST_JOB_NUM)")
    print(f"评价指标: {args.indicator}")
    print(f"预览模式: {'是' if args.dry_run else '否'}")
    print()

    # 按风格分组显示
    by_style = {}
    for fname, style in factors:
        if style not in by_style:
            by_style[style] = []
        by_style[style].append(fname)

    print("待处理因子:")
    for style, names in by_style.items():
        configs = STYLE_CONFIG_MAP[style]("test")
        print(f"  {style} ({len(names)} 因子, 每个 {len(configs)} 配置):")
        # 显示参数范围信息
        if not param_grid_override:
            param_ranges = set(str(c.param_grid[0]) + "-" + str(c.param_grid[-1]) for c in configs)
            print(f"    参数范围: {', '.join(param_ranges)}")
        for name in names[:5]:
            print(f"    - {name}")
        if len(names) > 5:
            print(f"    - ... 还有 {len(names) - 5} 个")

    print()

    # 确认执行
    if not args.dry_run:
        total_configs = sum(
            len(names) * len(STYLE_CONFIG_MAP[style]("test"))
            for style, names in by_style.items()
        )
        print(f"预计运行 {total_configs} 个回测配置。")
        print("这可能需要较长时间。")
        print()
        if not args.yes:
            try:
                confirm = input("确认执行? (y/N): ").strip().lower()
                if confirm != "y":
                    print("已取消")
                    sys.exit(0)
            except (KeyboardInterrupt, EOFError):
                print("\n已取消")
                sys.exit(0)

    # 执行批量处理（异步）
    results = asyncio.run(batch_process(
        factors=factors,
        dry_run=args.dry_run,
        param_grid_override=param_grid_override,
        indicator=args.indicator,
    ))

    # 打印摘要
    print_summary(results)

    # 输出到文件
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {args.output}")


if __name__ == "__main__":
    main()
