"""回测服务最小测试 - 2个月短周期回测"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from domains.stock_hub.services.stock_backtest_service import StockBacktestService
from domains.stock_hub.models.backtest_config_model import (
    BacktestRequest,
    StrategyConfig,
    FactorConfig,
)


def test_config_generation():
    """测试配置生成（不执行回测）"""
    print("=" * 60)
    print("[测试1] 配置生成")
    print("=" * 60)

    service = StockBacktestService()

    request = BacktestRequest(
        backtest_name="配置生成测试",
        start_date="2024-01-01",
        end_date="2024-03-01",
        strategies=[
            StrategyConfig(
                name="测试策略",
                hold_period="W",
                offset_list=[0],
                select_num=3,
                factor_list=[
                    FactorConfig(name="市值", ascending=True),
                    FactorConfig(name="H估值_市盈率TTM", ascending=True),
                ],
            )
        ],
        performance_mode="ECO",
    )

    config = service._build_config(request)
    print(f"  配置字段: {list(config.keys())}")
    print(f"  策略数: {len(config['strategies'])}")
    print(f"  因子数: {len(config['strategies'][0]['factor_list'])}")
    print(f"  时间范围: {config['start_date']} ~ {config['end_date']}")

    assert config["start_date"] == "2024-01-01"
    assert config["end_date"] == "2024-03-01"
    assert len(config["strategies"]) == 1
    assert len(config["strategies"][0]["factor_list"]) == 2
    print("  ✓ 通过\n")


def test_backtest_execution():
    """测试实际回测执行（2个月最小测试）"""
    print("=" * 60)
    print("[测试2] 回测执行（2个月ECO模式）")
    print("=" * 60)

    service = StockBacktestService()

    request = BacktestRequest(
        backtest_name="AI框架最小测试",
        start_date="2024-01-01",
        end_date="2024-03-01",
        strategies=[
            StrategyConfig(
                name="最小测试",
                hold_period="W",
                offset_list=[0],
                select_num=3,
                factor_list=[
                    FactorConfig(name="市值", ascending=True),
                ],
            )
        ],
        performance_mode="ECO",
        stay_real=False,  # 单进程更稳定
    )

    print("  提交回测任务...")
    start = time.time()
    task_id = service.submit_backtest(request)
    duration = time.time() - start
    print(f"  回测耗时: {duration:.1f}s")

    task = service.get_task(task_id)
    assert task is not None
    result = task["result"]
    print(f"  状态: {result['status']}")
    print(f"  消息: {result['message']}")
    if result.get("result_path"):
        print(f"  结果路径: {result['result_path']}")

    assert result["status"] == "ok", f"回测失败: {result['message']}"
    print("  ✓ 通过\n")

    # 测试任务列表
    print("[测试3] 任务列表...")
    tasks = service.list_tasks()
    print(f"  共 {len(tasks)} 个任务")
    assert len(tasks) >= 1
    print("  ✓ 通过\n")

    print("=" * 60)
    print("回测服务测试全部通过!")
    print("=" * 60)


if __name__ == "__main__":
    test_config_generation()
    test_backtest_execution()
