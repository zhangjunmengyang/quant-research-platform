"""A股回测执行服务"""
import json
import logging
import os
import subprocess
import uuid
import time
from typing import Optional, Dict
from pathlib import Path

from domains.stock_hub.config import (
    STOCK_FRAMEWORK_PATH,
    FUEL_PYTHON_PATH,
    DATA_CENTER_PATH,
    CACHE_DIR,
    BACKTEST_TIMEOUT,
)
from domains.stock_hub.models.backtest_config_model import (
    BacktestRequest,
    BacktestResult,
)

logger = logging.getLogger(__name__)

# 临时配置文件目录
TMP_DIR = CACHE_DIR / "tmp"
TMP_DIR.mkdir(exist_ok=True)

# 回测任务记录
_tasks: Dict[str, dict] = {}


class StockBacktestService:
    """回测执行服务 - 通过子进程调用Fuel Python运行选股回测"""

    def __init__(self):
        self.script_path = Path(__file__).parent.parent / "scripts" / "run_backtest.py"

    def submit_backtest(self, request: BacktestRequest) -> str:
        """提交回测任务，返回task_id"""
        from domains.stock_hub.config import is_stock_framework_available

        task_id = str(uuid.uuid4())[:8]

        if not is_stock_framework_available():
            _tasks[task_id] = {
                "status": "error",
                "config_path": "",
                "request": request.model_dump(),
                "submitted_at": time.time(),
                "result": BacktestResult(
                    status="error",
                    message="Stock framework not configured. Set STOCK_FRAMEWORK_PATH and FUEL_PYTHON_PATH environment variables.",
                ).model_dump(),
            }
            return task_id

        # 生成JSON配置文件
        config_data = self._build_config(request)
        config_path = TMP_DIR / f"backtest_{task_id}.json"
        config_path.write_text(
            json.dumps(config_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 记录任务
        _tasks[task_id] = {
            "status": "running",
            "config_path": str(config_path),
            "request": request.model_dump(),
            "submitted_at": time.time(),
            "result": None,
        }

        # 同步执行（后续可改为异步）
        try:
            result = self._run_subprocess(config_path)
            _tasks[task_id]["status"] = result.status
            _tasks[task_id]["result"] = result.model_dump()
        finally:
            # 清理临时配置文件
            try:
                config_path.unlink()
            except Exception:
                pass

        return task_id

    def get_task(self, task_id: str) -> Optional[dict]:
        """查询回测任务状态"""
        return _tasks.get(task_id)

    def list_tasks(self) -> list:
        """列出所有回测任务（含名称和结果路径）"""
        return [
            {
                "task_id": tid,
                "status": t["status"],
                "submitted_at": t["submitted_at"],
                "backtest_name": t["request"].get("backtest_name", tid),
                "result": t["result"],
            }
            for tid, t in _tasks.items()
        ]

    def _build_config(self, request: BacktestRequest) -> dict:
        """构建传递给子进程的JSON配置"""
        strategies = []
        for s in request.strategies:
            strategies.append({
                "name": s.name,
                "hold_period": s.hold_period,
                "offset_list": s.offset_list,
                "select_num": s.select_num,
                "cap_weight": s.cap_weight,
                "rebalance_time": s.rebalance_time,
                "factor_list": [f.model_dump() for f in s.factor_list],
                "filter_list": [fl.model_dump() for fl in s.filter_list],
            })

        return {
            "stock_framework_path": str(STOCK_FRAMEWORK_PATH),
            "data_center_path": str(DATA_CENTER_PATH),
            "backtest_name": request.backtest_name,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "performance_mode": request.performance_mode,
            "stay_real": request.stay_real,
            "strategies": strategies,
            "excluded_boards": request.excluded_boards,
            "days_listed": request.days_listed,
            "total_cap_usage": request.total_cap_usage,
            "initial_cash": request.initial_cash,
            "c_rate": request.c_rate,
            "t_rate": request.t_rate,
            "stock_timing_order_price": request.stock_timing_order_price,
        }

    def _run_subprocess(self, config_path: Path) -> BacktestResult:
        """执行子进程回测"""
        cmd = [
            str(FUEL_PYTHON_PATH),
            "-X", "utf8",
            str(self.script_path),
            "--config", str(config_path),
        ]

        env = {
            **os.environ,
            "PYTHONIOENCODING": "utf-8",
        }

        logger.info(f"启动回测子进程: {' '.join(cmd)}")
        start_time = time.time()

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                cwd=str(STOCK_FRAMEWORK_PATH),
                timeout=BACKTEST_TIMEOUT,
            )

            duration = time.time() - start_time
            logger.info(f"回测子进程完成, 耗时 {duration:.1f}s, 退出码 {proc.returncode}")

            # 解析输出中的JSON结果
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""

            result_json = None
            for line in stdout.split("\n"):
                if line.startswith("__RESULT_JSON__:"):
                    try:
                        result_json = json.loads(line[len("__RESULT_JSON__:"):])
                    except json.JSONDecodeError:
                        pass

            if result_json:
                return BacktestResult(
                    status=result_json.get("status", "error"),
                    message=result_json.get("message", ""),
                    result_path=result_json.get("result_path"),
                    log_output=stdout[-5000:],  # 最后5000字符
                )
            else:
                # 没有找到结果标记
                error_msg = stderr[-2000:] if stderr else "未找到回测结果输出"
                return BacktestResult(
                    status="error",
                    message=error_msg,
                    log_output=stdout[-5000:],
                )

        except subprocess.TimeoutExpired:
            return BacktestResult(
                status="error",
                message=f"回测超时（{BACKTEST_TIMEOUT}秒）",
            )
        except Exception as e:
            return BacktestResult(
                status="error",
                message=f"子进程执行失败: {e}",
            )


# 单例
_service: Optional[StockBacktestService] = None


def get_stock_backtest_service() -> StockBacktestService:
    """获取服务单例"""
    global _service
    if _service is None:
        _service = StockBacktestService()
    return _service
