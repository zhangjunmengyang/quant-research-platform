"""
Strategy Hub - 策略知识库模块

包含策略管理服务，核心回测引擎已迁移到 engine 模块。

主要组件:
- StrategyStore: 策略存储服务
- BacktestRunner: 回测执行器
- MCP Server: Model Context Protocol 服务

回测引擎核心代码在 domains/engine/core/ 中。
策略服务在 services/ 子目录中，提供策略存储和回测任务管理。
"""

import sys
from pathlib import Path

# 向后兼容: core 子目录仍然存在，但应使用 engine 模块
# 保留 sys.path 修改以支持旧代码的渐进式迁移
_engine_path = Path(__file__).parent
if str(_engine_path) not in sys.path:
    sys.path.insert(0, str(_engine_path))

# 导出服务层
from .services import (
    Strategy,
    TaskStatus,
    TaskInfo,
    StrategyStore,
    get_strategy_store,
    BacktestRunner,
    isolated_cache,
)

__version__ = "2.0.0"

__all__ = [
    # 数据模型
    'Strategy',
    'TaskStatus',
    'TaskInfo',
    # 存储服务
    'StrategyStore',
    'get_strategy_store',
    # 回测服务
    'BacktestRunner',
    'isolated_cache',
]
