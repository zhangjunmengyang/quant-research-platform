#!/usr/bin/env python3
"""
因子参数分析 CLI

对因子进行参数敏感性分析，遍历不同参数值运行回测，找出最优参数。

核心设计:
- 复用 run_backtest 的 strategy_list 结构
- 通过 param_grid 定义变量（以 $ 开头）及其取值范围
- 在 strategy_list 中使用 $variable 占位符，支持同一变量多处使用（联动）
- 自动根据 param_grid 维度选择图表类型: 1维=柱状图, 2维=热力图

使用方式:
    # 单参数遍历（柱状图）
    python scripts/factor_param_analysis.py --name "ILLQStd参数分析" \\
        --strategy '[{"factor_list": [["ILLQStd", true, "$window", 1]], "hold_period": "4H", "market": "swap_swap", "long_select_coin_num": 0.1}]' \\
        --param-grid '{"$window": [48, 96, 144, 192, 240]}'

    # 双参数遍历（热力图）
    python scripts/factor_param_analysis.py --name "ILLQStd参数与持仓周期" \\
        --strategy '[{"factor_list": [["ILLQStd", true, "$window", 1]], "hold_period": "$hold", "market": "swap_swap", "long_select_coin_num": 0.1}]' \\
        --param-grid '{"$window": [48, 96, 144], "$hold": ["1H", "4H", "24H"]}'

    # 选币因子和过滤因子使用相同参数（联动）
    python scripts/factor_param_analysis.py --name "ILLQStd联动分析" \\
        --strategy '[{"factor_list": [["ILLQStd", true, "$window", 1]], "filter_list": [["QuoteVolumeMean", "$window", "pct:<0.2", false]], "hold_period": "4H", "market": "swap_swap", "long_select_coin_num": 0.1}]' \\
        --param-grid '{"$window": [48, 96, 144, 192]}'
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


async def run_param_analysis(
    name: str,
    strategy_list: list[dict],
    param_grid: dict[str, list],
    start_date: str | None = None,
    end_date: str | None = None,
    leverage: float = 1.0,
    indicator: str = "annual_return",
    output_format: str = "table",
):
    """执行因子参数分析"""
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    mcp_url = "http://localhost:6789/mcp"

    # 计算组合数
    import itertools
    grid_keys = list(param_grid.keys())
    grid_values = [param_grid[k] for k in grid_keys]
    total_combos = len(list(itertools.product(*grid_values)))

    try:
        async with streamablehttp_client(
            mcp_url,
            timeout=1800,  # 参数遍历可能需要较长时间
            sse_read_timeout=1800
        ) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                arguments = {
                    "name": name,
                    "strategy_list": strategy_list,
                    "param_grid": param_grid,
                    "indicator": indicator,
                    "leverage": leverage,
                }

                if start_date:
                    arguments["start_date"] = start_date
                if end_date:
                    arguments["end_date"] = end_date

                print(f"参数分析任务: {name}")
                print(f"参数网格: {json.dumps(param_grid, ensure_ascii=False)}")
                print(f"总组合数: {total_combos}")
                print(f"图表类型: {'柱状图' if len(grid_keys) == 1 else '热力图'}")
                print(f"评价指标: {indicator}")
                if start_date or end_date:
                    print(f"日期范围: {start_date or '默认'} ~ {end_date or '默认'}")
                print("\n正在运行回测，请耐心等待...\n")

                result = await session.call_tool(
                    "run_factor_param_analysis",
                    arguments=arguments
                )

                # 解析结果
                for content in result.content:
                    if hasattr(content, "text"):
                        data = json.loads(content.text)
                        output_result(data, output_format, indicator)
                        return data

    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


def output_result(data: dict, output_format: str, indicator: str):
    """输出分析结果"""
    if output_format == "json":
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    # 检查是否成功
    if "error" in data:
        print(f"分析失败: {data['error']}")
        return

    # table 格式
    print("=" * 70)
    print(f"分析任务: {data.get('name', 'N/A')}")
    print(f"图表类型: {data.get('chart_type', 'N/A')}")
    print(f"参数维度: {data.get('grid_keys', [])}")
    print(f"总组合数: {data.get('total_combinations', 0)}")
    print(f"有效结果数: {data.get('valid_results', 0)}")
    if data.get('factor_updated'):
        print(f"已更新因子: {data.get('factor_updated')}")
    print("=" * 70)

    best = data.get("best_result", {})
    if best:
        print("\n最优参数组合:")
        grid_keys = data.get("grid_keys", [])
        for key in grid_keys:
            print(f"  {key}: {best.get(key, 'N/A')}")
        print()
        print(f"  年化收益:   {best.get('annual_return', 0):.2%}")
        print(f"  最大回撤:   {best.get('max_drawdown', 0):.2%}")
        print(f"  夏普比率:   {best.get('sharpe_ratio', 0):.2f}")
        print(f"  胜率:       {best.get('win_rate', 0):.2%}")
        print(f"  累计收益:   {best.get('cumulative_return', 0):.2%}")

    # 显示所有结果
    all_results = data.get("all_results", [])
    if all_results:
        print("\n所有参数对比:")
        print("-" * 90)

        grid_keys = data.get("grid_keys", [])

        # 动态生成表头
        header_parts = [f"{k:>15}" for k in grid_keys]
        header_parts.extend([f"{'年化收益':>12}", f"{'夏普比率':>10}", f"{'最大回撤':>12}", f"{'胜率':>10}"])
        print(" | ".join(header_parts))
        print("-" * 90)

        # 按指标排序
        sorted_results = sorted(
            all_results,
            key=lambda x: x.get(indicator, 0) or 0,
            reverse=True
        )

        for r in sorted_results:
            row_parts = [f"{r.get(k, 'N/A'):>15}" for k in grid_keys]
            row_parts.extend([
                f"{r.get('annual_return', 0):>12.2%}",
                f"{r.get('sharpe_ratio', 0):>10.2f}",
                f"{r.get('max_drawdown', 0):>12.2%}",
                f"{r.get('win_rate', 0):>10.2%}",
            ])
            print(" | ".join(row_parts))

    print(f"\n{data.get('message', '')}")


def build_strategy_from_simple_params(
    filename: str,
    direction: bool = True,
    hold_period: str = "4H",
    market: str = "swap_swap",
    long_select_coin_num: float = 0.1,
    short_select_coin_num: float = 0,
    long_cap_weight: float = 1,
    short_cap_weight: float = 0,
    filter_list: list | None = None,
    filter_list_post: list | None = None,
) -> list[dict]:
    """从简单参数构建 strategy_list（使用 $window 变量占位符）"""
    strategy = {
        "factor_list": [[filename, direction, "$window", 1]],  # 使用 $window 占位符
        "hold_period": hold_period,
        "market": market,
        "long_select_coin_num": long_select_coin_num,
        "short_select_coin_num": short_select_coin_num,
        "long_cap_weight": long_cap_weight,
        "short_cap_weight": short_cap_weight,
    }

    if filter_list:
        strategy["filter_list"] = filter_list
    if filter_list_post:
        strategy["filter_list_post"] = filter_list_post

    return [strategy]


def main():
    parser = argparse.ArgumentParser(
        description="因子参数分析 CLI - 复用 run_backtest 结构的参数敏感性分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:

  # ========== 完整模式（推荐） ==========
  # 单参数遍历（柱状图）- 使用 $window 变量
  python scripts/factor_param_analysis.py --name "ILLQStd参数分析" \\
      --strategy '[{"factor_list": [["ILLQStd", true, "$window", 1]], "hold_period": "4H", "market": "swap_swap", "long_select_coin_num": 0.1}]' \\
      --param-grid '{"$window": [48, 96, 144, 192, 240]}'

  # 双参数遍历（热力图）- 使用 $window 和 $hold 变量
  python scripts/factor_param_analysis.py --name "ILLQStd参数与持仓周期" \\
      --strategy '[{"factor_list": [["ILLQStd", true, "$window", 1]], "hold_period": "$hold", "market": "swap_swap", "long_select_coin_num": 0.1}]' \\
      --param-grid '{"$window": [48, 96, 144], "$hold": ["1H", "4H", "24H"]}'

  # 选币因子和过滤因子联动（同一 $window 变量用于两处）
  python scripts/factor_param_analysis.py --name "ILLQStd联动分析" \\
      --strategy '[{"factor_list": [["ILLQStd", true, "$window", 1]], "filter_list": [["QuoteVolumeMean", "$window", "pct:<0.2", false]], "hold_period": "4H", "market": "swap_swap", "long_select_coin_num": 0.1}]' \\
      --param-grid '{"$window": [48, 96, 144, 192]}'

  # ========== 简化模式 ==========
  # 使用简化参数（自动构建 strategy_list，使用 $window 变量）
  python scripts/factor_param_analysis.py --name "QuoteVolumeMean分析" \\
      --factor QuoteVolumeMean \\
      --params 72,144,216,288 \\
      --hold-period 24H --market spot_swap

  # 带过滤因子的简化模式（过滤因子使用固定参数，选币因子使用 $window）
  python scripts/factor_param_analysis.py --name "LowPrice分析" \\
      --factor LowPrice \\
      --params 48,96,144 \\
      --filter '[["QuoteVolumeMean", 24, "pct:<0.2", false]]'

  # ========== 输出格式 ==========
  # JSON 输出
  python scripts/factor_param_analysis.py --name "分析" \\
      --strategy '[...]' --param-grid '{...}' --format json

param_grid 变量占位符:
  - 变量名必须以 $ 开头，如 "$window", "$hold"
  - 同一变量可在 strategy_list 中多处使用，遍历时自动替换所有位置
  - 最多支持 2 个变量（1 个=柱状图，2 个=热力图）

常用变量示例:
  - "$window"  因子计算窗口参数
  - "$hold"    持仓周期 ("1H", "4H", "24H")
  - "$market"  市场类型

market 类型:
  - swap_swap  永续合约双向（默认）
  - spot_spot  现货双向
  - spot_swap  现货多头 + 永续空头
  - mix_spot   混合现货
  - mix_swap   混合永续

hold_period: 1H, 4H, 24H

indicator 评价指标:
  - annual_return   年化收益（默认）
  - sharpe_ratio    夏普比率
  - max_drawdown    最大回撤
  - win_rate        胜率
"""
    )

    # ========== 完整模式参数 ==========
    parser.add_argument("--name", "-n", required=True,
                        help="分析任务名称")
    parser.add_argument("--strategy", dest="strategy_json",
                        help="策略配置 JSON（strategy_list 格式）")
    parser.add_argument("--param-grid", dest="param_grid_json",
                        help="参数网格 JSON，如 '{\"factor_list[0][2]\": [48, 96, 144]}'")

    # ========== 简化模式参数 ==========
    parser.add_argument("--factor", "-f",
                        help="因子文件名（简化模式）")
    parser.add_argument("--params", "-p",
                        help="参数值列表，逗号分隔（简化模式）")
    parser.add_argument("--direction", "-d", type=lambda x: x.lower() == "true",
                        default=True,
                        help="因子方向 (True=小做多, False=大做多, 默认: True)")

    # ========== 公共策略参数 ==========
    parser.add_argument("--hold-period", "-hp", default="4H",
                        choices=["1H", "4H", "24H"],
                        help="持仓周期 (默认: 4H)")
    parser.add_argument("--market", "-m", default="swap_swap",
                        choices=["swap_swap", "spot_spot", "spot_swap", "mix_spot", "mix_swap"],
                        help="市场类型 (默认: swap_swap)")
    parser.add_argument("--long", "-l", type=float, default=0.1,
                        help="多头选币数量/比例 (默认: 0.1)")
    parser.add_argument("--short", "-s", type=float, default=0,
                        help="空头选币数量/比例 (默认: 0, 不做空)")
    parser.add_argument("--long-cap", type=float, default=1,
                        help="多头仓位权重 (默认: 1)")
    parser.add_argument("--short-cap", type=float, default=0,
                        help="空头仓位权重 (默认: 0)")

    # ========== 过滤因子参数 ==========
    parser.add_argument("--filter", dest="filter_list",
                        help="前置过滤因子列表 (JSON 格式)")
    parser.add_argument("--filter-post", dest="filter_list_post",
                        help="后置过滤因子列表 (JSON 格式)")

    # ========== 回测参数 ==========
    parser.add_argument("--start", help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end", help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--leverage", type=float, default=1.0,
                        help="杠杆倍数 (默认: 1)")
    parser.add_argument("--indicator", "-i", default="annual_return",
                        choices=["annual_return", "sharpe_ratio", "max_drawdown", "win_rate"],
                        help="评价指标 (默认: annual_return)")

    # ========== 输出格式 ==========
    parser.add_argument("--format", default="table",
                        choices=["table", "json"],
                        help="输出格式 (默认: table)")

    args = parser.parse_args()

    # 确定使用哪种模式
    if args.strategy_json and args.param_grid_json:
        # 完整模式
        try:
            strategy_list = json.loads(args.strategy_json)
        except json.JSONDecodeError as e:
            print(f"错误: strategy JSON 解析失败: {e}", file=sys.stderr)
            sys.exit(1)

        try:
            param_grid = json.loads(args.param_grid_json)
        except json.JSONDecodeError as e:
            print(f"错误: param_grid JSON 解析失败: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.factor and args.params:
        # 简化模式 - 自动构建 strategy_list 和 param_grid
        params = [int(p.strip()) for p in args.params.split(",")]
        if len(params) < 2:
            print("错误: 至少需要 2 个参数值进行分析", file=sys.stderr)
            sys.exit(1)

        # 解析过滤因子
        filter_list = None
        filter_list_post = None
        if args.filter_list:
            try:
                filter_list = json.loads(args.filter_list)
            except json.JSONDecodeError as e:
                print(f"错误: filter_list JSON 解析失败: {e}", file=sys.stderr)
                sys.exit(1)
        if args.filter_list_post:
            try:
                filter_list_post = json.loads(args.filter_list_post)
            except json.JSONDecodeError as e:
                print(f"错误: filter_list_post JSON 解析失败: {e}", file=sys.stderr)
                sys.exit(1)

        # 构建 strategy_list（使用 $window 占位符）
        strategy_list = build_strategy_from_simple_params(
            filename=args.factor,
            direction=args.direction,
            hold_period=args.hold_period,
            market=args.market,
            long_select_coin_num=args.long,
            short_select_coin_num=args.short,
            long_cap_weight=args.long_cap,
            short_cap_weight=args.short_cap,
            filter_list=filter_list,
            filter_list_post=filter_list_post,
        )

        # 构建 param_grid（使用 $window 变量）
        param_grid = {"$window": params}

    else:
        print("错误: 请使用完整模式 (--strategy + --param-grid) 或简化模式 (--factor + --params)",
              file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # 验证 param_grid
    if not param_grid:
        print("错误: param_grid 不能为空", file=sys.stderr)
        sys.exit(1)

    if len(param_grid) > 2:
        print(f"错误: param_grid 最多支持2个维度，当前有 {len(param_grid)} 个",
              file=sys.stderr)
        sys.exit(1)

    for key, values in param_grid.items():
        # 验证变量名必须以 $ 开头
        if not key.startswith("$"):
            print(f"错误: param_grid 的键必须以 $ 开头: '{key}'，应为 '${key}'",
                  file=sys.stderr)
            sys.exit(1)
        if not values or len(values) < 2:
            print(f"错误: param_grid['{key}'] 至少需要2个值", file=sys.stderr)
            sys.exit(1)

    # 执行分析
    asyncio.run(run_param_analysis(
        name=args.name,
        strategy_list=strategy_list,
        param_grid=param_grid,
        start_date=args.start,
        end_date=args.end,
        leverage=args.leverage,
        indicator=args.indicator,
        output_format=args.format,
    ))


if __name__ == "__main__":
    main()
