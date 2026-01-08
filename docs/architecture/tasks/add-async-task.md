# 任务: 添加异步任务

## 概述

异步任务用于处理 CPU 密集型或长时间运行的计算任务。本项目使用 BacktestRunner 等专用执行器管理任务，而非外部任务队列。

## 执行模式

| 模式 | 适用场景 | 示例 |
|------|---------|------|
| FAST | I/O 密集型，轻量查询（< 100ms） | list_factors, get_kline |
| COMPUTE | CPU 密集型任务 | run_backtest, analyze_factor |

## 实现示例

### 1. 定义 COMPUTE 模式工具

```python
# backend/domains/strategy_hub/api/mcp/tools/strategy_tools.py
from domains.mcp_core.base.tool import BaseTool, ToolResult, ExecutionMode
import uuid

class RunBacktestTool(BaseTool):
    category = "mutation"
    execution_mode = ExecutionMode.COMPUTE  # CPU 密集型任务
    execution_timeout = 3600.0  # 最长 1 小时

    async def execute(self, **params) -> ToolResult:
        from domains.strategy_hub.services import get_backtest_runner

        task_id = str(uuid.uuid4())
        runner = get_backtest_runner()

        # 提交任务到 BacktestRunner（内置 ThreadPoolExecutor）
        runner.submit(task_id, params)

        return ToolResult.ok({
            "task_id": task_id,
            "status": "pending",
            "message": "任务已提交，请通过 task_id 查询状态"
        })
```

### 2. 任务执行器

BacktestRunner 使用 ThreadPoolExecutor 管理任务:

```python
# backend/domains/strategy_hub/services/backtest_service.py
from concurrent.futures import ThreadPoolExecutor

class BacktestRunner:
    def __init__(self, max_workers: int = 1):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: Dict[str, TaskStatus] = {}

    def submit(self, task_id: str, params: dict):
        self._tasks[task_id] = TaskStatus(status="pending")
        future = self._executor.submit(self._run_backtest, task_id, params)
        future.add_done_callback(lambda f: self._on_complete(task_id, f))
```

### 3. 任务状态查询

客户端通过 REST API 或 WebSocket 查询任务状态:

- REST: `GET /api/v1/backtest/tasks/{task_id}`
- WebSocket: `ws://localhost:8000/api/v1/ws/backtest/{task_id}`

状态流转: `pending -> running -> completed/failed`

## 任务状态追踪

使用 Redis 存储任务状态（可选）:

```python
# backend/domains/mcp_core/queue/task_queue.py
class TaskQueue:
    async def submit(self, task_type: str, params: dict) -> str:
        task_id = str(uuid.uuid4())
        # 存储任务元数据到 Redis
        await self._redis.set(f"task:{task_id}:meta", json.dumps({...}))
        return task_id

    async def get_result(self, task_id: str) -> TaskResult:
        # 从 Redis 读取任务状态
        ...
```

## 资源管理

回测任务的 CPU 并行度由 `JOB_NUM` 环境变量控制:

```bash
# .env
JOB_NUM=4  # 回测引擎内部 ProcessPoolExecutor workers
```

建议配置:
- 单任务场景: JOB_NUM = CPU 核心数
- 多任务场景: 根据并发任务数分配
