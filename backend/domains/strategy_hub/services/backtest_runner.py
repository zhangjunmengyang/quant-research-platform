"""
回测执行器

封装回测引擎调用，提供任务隔离和生命周期管理。

并发配置:
- 默认 worker 数量根据 CPU 核心数动态计算
- 回测任务是 CPU 密集型，设置为核心数的一半（1-8 之间）
"""

import os
import sys
import uuid
import json
import logging
import threading
import re
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from .models import Strategy, TaskStatus, TaskInfo
from .strategy_store import StrategyStore, get_strategy_store
from .cache_isolation import isolated_cache, cleanup_task_cache
from .task_store import BacktestTaskStore, get_task_store
from domains.mcp_core.paths import get_project_root, get_backend_dir, get_data_dir

logger = logging.getLogger(__name__)


def _get_default_workers() -> int:
    """
    根据 CPU 核心数动态计算默认 worker 数量

    回测任务是 CPU 密集型，设置为 CPU 核心数的一半（至少1，最多8）
    避免过多任务竞争 CPU 资源导致整体变慢
    """
    cpu_count = os.cpu_count() or 2
    workers = max(1, min(cpu_count // 2, 8))
    return workers


DEFAULT_MAX_WORKERS = _get_default_workers()


def _setup_backtest_engine_paths():
    """
    设置回测引擎需要的 Python 路径。

    engine/core 是回测引擎核心，需要特定的路径设置:
    1. 项目根目录 - 用于 `from config import ...`
    2. backend 目录 - 用于 `from domains.engine.core...`
    """
    project_root = get_project_root()
    backend_path = get_backend_dir()

    paths_to_add = [str(project_root), str(backend_path)]
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)


@dataclass
class BacktestRequest:
    """回测请求

    完整暴露 config/backtest_config.py 的全部可配置项。
    """
    name: str  # 策略/回测名称
    strategy_list: List[Dict[str, Any]]  # 策略配置列表（兼容回测引擎格式）

    # 时间配置
    start_date: Optional[str] = None  # 回测开始日期
    end_date: Optional[str] = None  # 回测结束日期

    # 账户配置
    account_type: str = "统一账户"  # '统一账户' 或 '普通账户'
    initial_usdt: float = 10000  # 初始资金
    leverage: float = 1.0  # 杠杆倍数
    margin_rate: float = 0.05  # 维持保证金率

    # 手续费配置
    swap_c_rate: float = 0.0006  # 合约手续费率(含滑点)
    spot_c_rate: float = 0.001  # 现货手续费率(含滑点)

    # 最小下单量
    swap_min_order_limit: float = 5  # 合约最小下单量(USDT)
    spot_min_order_limit: float = 10  # 现货最小下单量(USDT)

    # 价格计算
    avg_price_col: str = "avg_price_1m"  # 均价计算列: avg_price_1m / avg_price_5m

    # 币种过滤
    min_kline_num: int = 0  # 最少上市K线数
    black_list: List[str] = field(default_factory=list)  # 黑名单
    white_list: List[str] = field(default_factory=list)  # 白名单

    # 元数据（不影响回测）
    trade_type: str = "swap"  # 交易类型标记: swap / spot
    description: Optional[str] = None  # 描述
    tags: Optional[List[str]] = None  # 标签

    # 任务执行记录关联（用于任务管理系统）
    execution_id: Optional[str] = None  # 关联的执行记录ID

    def get_factor_list(self) -> List[str]:
        """从策略配置中提取因子列表"""
        factors = []
        for stg in self.strategy_list:
            if "factor_list" in stg:
                for factor in stg["factor_list"]:
                    if isinstance(factor, (list, tuple)):
                        factors.append(factor[0])  # 因子名称
                    else:
                        factors.append(str(factor))
        return list(set(factors))

    def get_factor_params(self) -> Dict[str, Any]:
        """从策略配置中提取因子参数"""
        params = {}
        for stg in self.strategy_list:
            if "factor_list" in stg:
                for factor in stg["factor_list"]:
                    if isinstance(factor, (list, tuple)) and len(factor) >= 3:
                        params[factor[0]] = factor[2]  # 因子名称 -> 参数
        return params

    def get_select_coin_num(self) -> int:
        """获取选币数量"""
        if self.strategy_list:
            stg = self.strategy_list[0]
            return stg.get("long_select_coin_num", 5)
        return 5


class BacktestRunner:
    """
    回测执行器

    封装回测引擎调用，提供任务隔离和生命周期管理。
    支持异步执行和任务状态跟踪。
    """

    def __init__(
        self,
        store: Optional[StrategyStore] = None,
        task_store: Optional[BacktestTaskStore] = None,
        max_workers: Optional[int] = None,
    ):
        """
        初始化回测执行器

        Args:
            store: 策略存储实例
            task_store: 任务存储实例（用于更新执行记录）
            max_workers: 最大并行任务数，默认根据 CPU 核心数动态计算
        """
        self.store = store or get_strategy_store()
        self.task_store = task_store or get_task_store()

        # 使用动态计算的默认值
        if max_workers is None:
            max_workers = DEFAULT_MAX_WORKERS
        self.tasks_dir = get_data_dir() / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._running_tasks: Dict[str, TaskInfo] = {}
        self._futures: Dict[str, Future] = {}
        self._lock = threading.Lock()
        # 任务ID到执行记录ID的映射
        self._execution_mapping: Dict[str, str] = {}
        self._max_workers = max_workers

        cpu_count = os.cpu_count() or 2
        logger.info(
            f"BacktestRunner 初始化: CPU 核心数={cpu_count}, "
            f"最大并行数={max_workers}"
        )

        # 启动时清理孤儿任务（后端重启导致的中断任务）
        self._cleanup_orphan_tasks()

    def _cleanup_orphan_tasks(self):
        """
        清理孤儿任务

        后端重启后，数据库中可能存在处于 running/pending 状态的任务，
        但实际上这些任务已经不在内存中运行了。需要将它们标记为失败或删除。
        """
        try:
            # 查询所有处于运行中或待处理状态的任务
            orphan_statuses = ['running', 'pending']
            strategies, _ = self.store.list_all(
                filters={'task_status': orphan_statuses},
                page=1,
                page_size=1000,
            )

            if not strategies:
                return

            logger.info(f"发现 {len(strategies)} 个孤儿任务，开始清理...")

            for strategy in strategies:
                task_id = strategy.id
                # 删除孤儿任务（回测未完成的不入库）
                self.store.delete(task_id)
                logger.info(f"已删除孤儿任务: {task_id} ({strategy.name})")

                # 清理任务缓存目录
                cleanup_task_cache(task_id, self.tasks_dir)

            logger.info(f"孤儿任务清理完成，共清理 {len(strategies)} 个")

        except Exception as e:
            logger.warning(f"清理孤儿任务失败: {e}")

    def submit(self, request: BacktestRequest) -> str:
        """
        提交回测任务

        Args:
            request: 回测请求

        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        now = datetime.now()

        # 创建任务信息
        task_info = TaskInfo(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=now,
        )

        # 从请求中提取因子信息
        factor_list = request.get_factor_list()
        factor_params = request.get_factor_params()
        select_coin_num = request.get_select_coin_num()

        # 从策略配置中提取多空配置和排序方向
        long_select_coin_num = 5.0
        short_select_coin_num = 0.0
        long_cap_weight = 1.0
        short_cap_weight = 0.0
        hold_period = "1H"
        offset = 0
        market = "swap_swap"
        sort_directions = {}

        if request.strategy_list:
            stg = request.strategy_list[0]
            long_select_coin_num = stg.get("long_select_coin_num", 5.0)
            short_select_coin_num = stg.get("short_select_coin_num", 0.0)
            if isinstance(short_select_coin_num, str):
                short_select_coin_num = long_select_coin_num  # 'long_nums' 情况
            long_cap_weight = stg.get("long_cap_weight", 1.0)
            short_cap_weight = stg.get("short_cap_weight", 0.0)
            hold_period = stg.get("hold_period", "1H")
            offset = stg.get("offset", 0)
            market = stg.get("market", "swap_swap")

            # 提取排序方向
            factor_list_items = stg.get("factor_list", [])
            for factor_item in factor_list_items:
                if isinstance(factor_item, dict):
                    name = factor_item.get("name", "")
                    is_sort_asc = factor_item.get("is_sort_asc", True)
                    if name:
                        sort_directions[name] = is_sort_asc

        # 创建策略记录
        strategy = Strategy(
            id=task_id,
            name=request.name,
            description=request.description,
            start_date=request.start_date or "",
            end_date=request.end_date or "",
            leverage=request.leverage,
            select_coin_num=select_coin_num,
            trade_type=request.trade_type,
            # 多空配置
            long_select_coin_num=long_select_coin_num,
            short_select_coin_num=short_select_coin_num,
            long_cap_weight=long_cap_weight,
            short_cap_weight=short_cap_weight,
            # 持仓配置
            hold_period=hold_period,
            offset=offset,
            market=market,
            # 账户配置
            account_type=request.account_type,
            initial_usdt=request.initial_usdt,
            margin_rate=request.margin_rate,
            # 手续费配置
            swap_c_rate=request.swap_c_rate,
            spot_c_rate=request.spot_c_rate,
            # 最小下单量
            swap_min_order_limit=request.swap_min_order_limit,
            spot_min_order_limit=request.spot_min_order_limit,
            # 价格计算
            avg_price_col=request.avg_price_col,
            # 币种过滤
            min_kline_num=request.min_kline_num,
            # 任务信息
            task_id=task_id,
            task_status="pending",
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
        )
        strategy.set_factor_list(factor_list)
        strategy.set_factor_params(factor_params)
        strategy.set_strategy_config(request.strategy_list)
        strategy.set_sort_directions(sort_directions)
        if request.tags:
            strategy.set_tags(request.tags)
        if request.black_list:
            strategy.set_black_list(request.black_list)
        if request.white_list:
            strategy.set_white_list(request.white_list)

        # 保存到数据库
        self.store.create(strategy)

        # 创建任务目录
        task_dir = self.tasks_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # 保存任务配置（完整的策略配置）
        config_path = task_dir / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({
                "task_id": task_id,
                "name": request.name,
                "strategy_list": request.strategy_list,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "leverage": request.leverage,
                "trade_type": request.trade_type,
                "account_type": request.account_type,
                "initial_usdt": request.initial_usdt,
                "black_list": request.black_list,
                "white_list": request.white_list,
                "min_kline_num": request.min_kline_num,
            }, f, ensure_ascii=False, indent=2)

        # 提交异步执行
        future = self._executor.submit(
            self._run_backtest,
            task_id,
            request,
        )

        # 注册任务（在锁内同时注册 task_info 和 future，避免竞态条件）
        with self._lock:
            self._running_tasks[task_id] = task_info
            self._futures[task_id] = future
            # 记录执行记录ID映射（如果有）
            if request.execution_id:
                self._execution_mapping[task_id] = request.execution_id

        logger.info(f"提交回测任务: {task_id} - {request.name}, execution_id: {request.execution_id}")
        return task_id

    async def run_and_wait(self, request: BacktestRequest) -> Optional[Strategy]:
        """
        提交回测任务并等待完成

        同步模式：提交任务后阻塞等待结果，适用于 MCP 工具调用。

        Args:
            request: 回测请求

        Returns:
            完成的策略对象，失败时返回 None

        Raises:
            Exception: 回测执行失败时抛出异常
        """
        import asyncio

        task_id = self.submit(request)
        future = self._futures.get(task_id)

        if future is None:
            raise RuntimeError(f"任务提交失败: {task_id}")

        # 在事件循环中非阻塞等待线程池任务完成
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, future.result)
        except Exception as e:
            # 获取任务状态以获取详细错误信息
            task_info = self.get_status(task_id)
            error_msg = task_info.error_message if task_info else str(e)
            raise RuntimeError(f"回测执行失败: {error_msg}") from e

        # 获取结果
        strategy = self.get_result(task_id)
        if strategy is None:
            raise RuntimeError(f"回测完成但无法获取结果: {task_id}")

        return strategy

    def get_status(self, task_id: str) -> Optional[TaskInfo]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务信息
        """
        with self._lock:
            if task_id in self._running_tasks:
                return self._running_tasks[task_id]

        # 从数据库查询
        strategy = self.store.get(task_id)
        if strategy:
            return TaskInfo(
                task_id=task_id,
                status=TaskStatus(strategy.task_status),
                created_at=datetime.fromisoformat(strategy.created_at),
                error_message=strategy.error_message,
            )
        return None

    def get_result(self, task_id: str) -> Optional[Strategy]:
        """
        获取任务结果

        Args:
            task_id: 任务ID

        Returns:
            策略对象
        """
        return self.store.get(task_id)

    def cancel(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            是否取消成功
        """
        cancelled = False

        with self._lock:
            if task_id in self._futures:
                future = self._futures[task_id]
                if future.cancel():
                    self._update_task_status(task_id, TaskStatus.CANCELLED)
                    logger.info(f"取消任务: {task_id}")
                    cancelled = True

        # 如果任务不在内存中（后端重启的情况），直接清理数据库记录
        if not cancelled:
            strategy = self.store.get(task_id)
            if strategy and strategy.task_status in ('running', 'pending'):
                # 删除孤儿任务
                self.store.delete(task_id)
                cleanup_task_cache(task_id, self.tasks_dir)
                logger.info(f"取消孤儿任务: {task_id}")
                cancelled = True

        return cancelled

    def cleanup(self, task_id: str) -> bool:
        """
        清理任务资源

        Args:
            task_id: 任务ID

        Returns:
            是否清理成功
        """
        with self._lock:
            self._running_tasks.pop(task_id, None)
            self._futures.pop(task_id, None)

        return cleanup_task_cache(task_id, self.tasks_dir)

    def list_running_tasks(self) -> List[TaskInfo]:
        """列出正在运行的任务"""
        with self._lock:
            return list(self._running_tasks.values())

    def _run_backtest(self, task_id: str, request: BacktestRequest):
        """
        执行回测

        Args:
            task_id: 任务ID
            request: 回测请求
        """
        self._update_task_status(task_id, TaskStatus.RUNNING)

        try:
            # 使用隔离的缓存目录执行回测
            with isolated_cache(task_id, self.tasks_dir, cleanup_on_exit=False):
                result = self._execute_backtest(task_id, request)

            # 解析结果并更新策略
            self._parse_and_save_result(task_id, result)
            self._update_task_status(task_id, TaskStatus.COMPLETED)
            logger.info(f"回测完成: {task_id}")

        except Exception as e:
            logger.exception(f"回测失败: {task_id}")
            self._update_task_error(task_id, str(e))

        finally:
            # 清理运行状态
            with self._lock:
                self._running_tasks.pop(task_id, None)
                self._futures.pop(task_id, None)
                self._execution_mapping.pop(task_id, None)

    def _execute_backtest(
        self,
        task_id: str,
        request: BacktestRequest,
    ) -> Dict[str, Any]:
        """
        执行实际的回测

        Args:
            task_id: 任务ID
            request: 回测请求

        Returns:
            回测结果字典
        """
        try:
            # 设置回测引擎需要的 Python 路径
            _setup_backtest_engine_paths()

            # 动态导入回测引擎（使用 engine 模块）
            from domains.engine.core.model.backtest_config import BacktestConfig
            from domains.engine.core.backtest import run_backtest

            logger.info(f"任务 {task_id}: 开始构建回测配置")

            # 构建回测配置 - 完整暴露 config/backtest_config.py 的配置能力
            conf = BacktestConfig(
                name=request.name,
                # 时间配置
                start_date=request.start_date or '2024-01-01',
                end_date=request.end_date or '2024-12-31',
                # 账户配置
                account_type=request.account_type,
                initial_usdt=request.initial_usdt,
                leverage=request.leverage,
                margin_rate=request.margin_rate,
                # 手续费
                swap_c_rate=request.swap_c_rate,
                spot_c_rate=request.spot_c_rate,
                # 最小下单量
                swap_min_order_limit=request.swap_min_order_limit,
                spot_min_order_limit=request.spot_min_order_limit,
                # 价格计算
                avg_price_col=request.avg_price_col,
                # 币种过滤
                min_kline_num=request.min_kline_num,
                black_list=request.black_list,
                white_list=request.white_list,
            )

            # 转换策略配置格式 (MCP 格式 -> 引擎格式)
            engine_strategy_list = self._convert_strategy_list(request.strategy_list)

            # 加载策略配置
            conf.load_strategy_config(engine_strategy_list)
            # iter_round = 0 表示单次回测，结果存到 backtest_path (回测结果)
            # iter_round != 0 表示参数遍历，结果存到 backtest_iter_path (遍历结果)
            # 这里是单次回测，保持默认值 0

            logger.info(f"任务 {task_id}: 配置构建完成，开始执行回测")

            # 执行回测
            run_backtest(conf)

            logger.info(f"任务 {task_id}: 回测执行完成，开始解析结果")

            # 解析回测结果
            return self._parse_backtest_result(conf)

        except ImportError as e:
            logger.warning(f"任务 {task_id}: 回测引擎导入失败 ({e})，使用模拟模式")
            return self._execute_mock_backtest(task_id, request)
        except Exception as e:
            logger.error(f"任务 {task_id}: 回测执行失败: {e}")
            raise

    def _execute_mock_backtest(
        self,
        task_id: str,
        request: BacktestRequest,
    ) -> Dict[str, Any]:
        """
        模拟回测（用于开发测试）

        Args:
            task_id: 任务ID
            request: 回测请求

        Returns:
            模拟的回测结果
        """
        import random
        import time

        logger.warning(f"任务 {task_id}: 使用模拟回测模式")

        # 模拟回测耗时
        time.sleep(2)

        # 生成模拟结果
        cumulative = 1.0 + random.uniform(-0.3, 0.5)
        annual = (cumulative ** (365 / 180)) - 1  # 假设180天回测
        max_dd = random.uniform(-0.3, -0.05)

        return {
            "cumulative_return": round(cumulative, 4),
            "annual_return": round(annual, 4),
            "max_drawdown": round(max_dd, 4),
            "max_drawdown_start": "2024-03-01",
            "max_drawdown_end": "2024-03-15",
            "sharpe_ratio": round(annual / abs(max_dd), 2) if max_dd != 0 else 0,
            "recovery_rate": round(random.uniform(0.1, 0.3), 4),
            "recovery_time": "30",
            "win_periods": random.randint(50, 100),
            "loss_periods": random.randint(30, 80),
            "win_rate": round(random.uniform(0.45, 0.65), 4),
            "avg_return_per_period": round(random.uniform(0.001, 0.01), 6),
            "profit_loss_ratio": round(random.uniform(0.8, 2.0), 2),
            "max_single_profit": round(random.uniform(0.05, 0.15), 4),
            "max_single_loss": round(random.uniform(-0.1, -0.02), 4),
            "max_consecutive_wins": random.randint(3, 10),
            "max_consecutive_losses": random.randint(2, 8),
            "return_std": round(random.uniform(0.01, 0.05), 4),
        }

    def _parse_backtest_result(self, conf) -> Dict[str, Any]:
        """
        解析回测引擎返回的结果

        Args:
            conf: BacktestConfig 对象（包含 report）

        Returns:
            标准化的结果字典
        """
        result = {}

        # 从 conf.report 获取策略评价指标
        if conf.report is not None and not conf.report.empty:
            report = conf.report.iloc[0] if len(conf.report) > 0 else conf.report

            # 解析百分数字符串
            def parse_pct(val):
                if isinstance(val, str) and val.endswith('%'):
                    return float(val.rstrip('%')) / 100
                return float(val) if val else 0.0

            # 核心指标
            result["cumulative_return"] = parse_pct(report.get("累积净值", 1.0))
            result["annual_return"] = parse_pct(report.get("年化收益", 0))
            result["max_drawdown"] = parse_pct(report.get("最大回撤", 0))
            result["max_drawdown_start"] = str(report.get("最大回撤开始时间", ""))
            result["max_drawdown_end"] = str(report.get("最大回撤结束时间", ""))
            result["sharpe_ratio"] = float(report.get("年化收益/回撤比", 0) or 0)

            # 交易统计
            result["win_periods"] = int(report.get("盈利周期数", 0) or 0)
            result["loss_periods"] = int(report.get("亏损周期数", 0) or 0)
            result["win_rate"] = parse_pct(report.get("胜率", 0))
            result["avg_return_per_period"] = parse_pct(report.get("每周期平均收益", 0))
            result["profit_loss_ratio"] = float(report.get("盈亏收益比", 0) or 0)
            result["max_single_profit"] = parse_pct(report.get("单周期最大盈利", 0))
            result["max_single_loss"] = parse_pct(report.get("单周期大亏损", 0))
            result["max_consecutive_wins"] = int(report.get("最大连续盈利周期数", 0) or 0)
            result["max_consecutive_losses"] = int(report.get("最大连续亏损周期数", 0) or 0)
            result["return_std"] = parse_pct(report.get("收益率标准差", 0))

            # 解析修复涨幅/时间
            recovery_str = str(report.get("修复涨幅（均/最大）", ""))
            if "/" in recovery_str:
                parts = recovery_str.split("/")
                result["recovery_rate"] = parse_pct(parts[0].strip())
            recovery_time_str = str(report.get("修复时间（均/最大）", ""))
            if "/" in recovery_time_str:
                parts = recovery_time_str.split("/")
                result["recovery_time"] = parts[0].strip()

        # 读取资金曲线文件
        try:
            result_folder = conf.get_result_folder()
            equity_file = result_folder / "资金曲线.csv"
            if equity_file.exists():
                import pandas as pd
                equity_df = pd.read_csv(equity_file, encoding='utf-8-sig')
                # 存储简化的资金曲线数据（每日数据点）
                if len(equity_df) > 0:
                    # 对于大数据量，采样保存
                    if len(equity_df) > 1000:
                        sample_df = equity_df.iloc[::len(equity_df)//1000]
                    else:
                        sample_df = equity_df
                    result["equity_curve"] = sample_df[["candle_begin_time", "多空资金曲线"]].to_dict("records")
        except Exception as e:
            logger.warning(f"读取资金曲线失败: {e}")

        # 读取周期收益
        try:
            result_folder = conf.get_result_folder()
            for period, filename in [
                ("year_return", "年度账户收益.csv"),
                ("quarter_return", "季度账户收益.csv"),
                ("month_return", "月度账户收益.csv"),
            ]:
                filepath = result_folder / filename
                if filepath.exists():
                    import pandas as pd
                    df = pd.read_csv(filepath, encoding='utf-8-sig')
                    result[period] = df.to_dict("records")
        except Exception as e:
            logger.warning(f"读取周期收益失败: {e}")

        return result

    def _parse_and_save_result(self, task_id: str, result: Dict[str, Any]):
        """
        解析回测结果并保存

        Args:
            task_id: 任务ID
            result: 回测结果
        """
        strategy = self.store.get(task_id)
        if not strategy:
            logger.error(f"策略不存在: {task_id}")
            return

        # 更新绩效指标
        strategy.cumulative_return = result.get("cumulative_return", 0.0)
        strategy.annual_return = result.get("annual_return", 0.0)
        strategy.max_drawdown = result.get("max_drawdown", 0.0)
        strategy.max_drawdown_start = result.get("max_drawdown_start")
        strategy.max_drawdown_end = result.get("max_drawdown_end")
        strategy.sharpe_ratio = result.get("sharpe_ratio", 0.0)
        strategy.recovery_rate = result.get("recovery_rate", 0.0)
        strategy.recovery_time = result.get("recovery_time")

        # 交易统计
        strategy.win_periods = result.get("win_periods", 0)
        strategy.loss_periods = result.get("loss_periods", 0)
        strategy.win_rate = result.get("win_rate", 0.0)
        strategy.avg_return_per_period = result.get("avg_return_per_period", 0.0)
        strategy.profit_loss_ratio = result.get("profit_loss_ratio", 0.0)
        strategy.max_single_profit = result.get("max_single_profit", 0.0)
        strategy.max_single_loss = result.get("max_single_loss", 0.0)
        strategy.max_consecutive_wins = result.get("max_consecutive_wins", 0)
        strategy.max_consecutive_losses = result.get("max_consecutive_losses", 0)
        strategy.return_std = result.get("return_std", 0.0)

        # 周期收益
        if "year_return" in result:
            strategy.year_return = json.dumps(result["year_return"], ensure_ascii=False)
        if "quarter_return" in result:
            strategy.quarter_return = json.dumps(result["quarter_return"], ensure_ascii=False)
        if "month_return" in result:
            strategy.month_return = json.dumps(result["month_return"], ensure_ascii=False)
        if "equity_curve" in result:
            strategy.equity_curve = json.dumps(result["equity_curve"], ensure_ascii=False)

        self.store.update(strategy)

        # 同步更新执行记录（如果有关联）
        execution_id = self._execution_mapping.get(task_id)
        if execution_id:
            self._update_execution_result(execution_id, result)

    def _update_execution_result(self, execution_id: str, result: Dict[str, Any]):
        """更新执行记录的回测结果"""
        try:
            execution = self.task_store.get_execution(execution_id)
            if not execution:
                logger.warning(f"执行记录不存在: {execution_id}")
                return

            # 更新绩效指标
            execution.cumulative_return = result.get("cumulative_return", 0.0)
            execution.annual_return = result.get("annual_return", 0.0)
            execution.max_drawdown = result.get("max_drawdown", 0.0)
            execution.max_drawdown_start = result.get("max_drawdown_start")
            execution.max_drawdown_end = result.get("max_drawdown_end")
            execution.sharpe_ratio = result.get("sharpe_ratio", 0.0)
            execution.recovery_rate = result.get("recovery_rate", 0.0)
            execution.recovery_time = result.get("recovery_time")

            # 交易统计
            execution.win_periods = result.get("win_periods", 0)
            execution.loss_periods = result.get("loss_periods", 0)
            execution.win_rate = result.get("win_rate", 0.0)
            execution.avg_return_per_period = result.get("avg_return_per_period", 0.0)
            execution.profit_loss_ratio = result.get("profit_loss_ratio", 0.0)
            execution.max_single_profit = result.get("max_single_profit", 0.0)
            execution.max_single_loss = result.get("max_single_loss", 0.0)
            execution.max_consecutive_wins = result.get("max_consecutive_wins", 0)
            execution.max_consecutive_losses = result.get("max_consecutive_losses", 0)
            execution.return_std = result.get("return_std", 0.0)

            # 周期收益
            if "year_return" in result:
                execution.year_return = json.dumps(result["year_return"], ensure_ascii=False)
            if "quarter_return" in result:
                execution.quarter_return = json.dumps(result["quarter_return"], ensure_ascii=False)
            if "month_return" in result:
                execution.month_return = json.dumps(result["month_return"], ensure_ascii=False)
            if "equity_curve" in result:
                execution.equity_curve = json.dumps(result["equity_curve"], ensure_ascii=False)

            self.task_store.update_execution(execution)
            logger.debug(f"更新执行记录结果: {execution_id}")
        except Exception as e:
            logger.error(f"更新执行记录结果失败: {execution_id}, {e}")

    def _update_task_status(self, task_id: str, status: TaskStatus):
        """更新任务状态"""
        now = datetime.now()
        execution_id = None

        with self._lock:
            if task_id in self._running_tasks:
                self._running_tasks[task_id].status = status
                if status == TaskStatus.RUNNING:
                    self._running_tasks[task_id].started_at = now
                elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    self._running_tasks[task_id].completed_at = now
            execution_id = self._execution_mapping.get(task_id)

        # 更新策略数据库
        strategy = self.store.get(task_id)
        if strategy:
            strategy.task_status = status.value
            self.store.update(strategy)

        # 更新执行记录（如果有关联）
        if execution_id:
            self._update_execution_status(execution_id, status, now)

    def _update_execution_status(
        self,
        execution_id: str,
        status: TaskStatus,
        timestamp: datetime,
        error_message: Optional[str] = None,
    ):
        """更新执行记录状态"""
        try:
            execution = self.task_store.get_execution(execution_id)
            if not execution:
                logger.warning(f"执行记录不存在: {execution_id}")
                return

            execution.status = status.value
            if status == TaskStatus.RUNNING:
                execution.started_at = timestamp.isoformat()
            elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                execution.completed_at = timestamp.isoformat()

            if error_message:
                execution.error_message = error_message

            self.task_store.update_execution(execution)
            logger.debug(f"更新执行记录状态: {execution_id} -> {status.value}")
        except Exception as e:
            logger.error(f"更新执行记录失败: {execution_id}, {e}")

    def _update_task_error(self, task_id: str, error: str):
        """更新任务错误"""
        execution_id = None
        with self._lock:
            if task_id in self._running_tasks:
                self._running_tasks[task_id].error_message = error
            execution_id = self._execution_mapping.get(task_id)

        self._update_task_status(task_id, TaskStatus.FAILED)

        # 更新执行记录的错误信息
        if execution_id:
            try:
                execution = self.task_store.get_execution(execution_id)
                if execution:
                    execution.error_message = error
                    self.task_store.update_execution(execution)
            except Exception as e:
                logger.error(f"更新执行记录错误信息失败: {e}")

        # 回测失败时删除策略记录，不入库
        strategy = self.store.get(task_id)
        if strategy:
            self.store.delete(task_id)
            logger.info(f"回测失败，已删除策略记录: {task_id}")

    def _convert_strategy_list(
        self,
        strategy_list: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        转换策略配置格式 (MCP 格式 -> 引擎格式)

        MCP 格式 (用户友好):
            {
                "factor_list": [["Bias", true, {"n": 24}]],
                "long_select_coin_num": 0.1,
                "short_select_coin_num": 0,
                "hold_period": "1H",
                "market": "swap_swap"
            }

        引擎格式 (BacktestConfig.load_strategy_config 期望):
            {
                "strategy": "dynamic_strategy",  # 策略名称（引擎会尝试加载，找不到则使用 DummyStrategy）
                "cap_weight": 1,  # 策略权重（必需）
                "factor_list": [["Bias", true, {"n": 24}, 1]],  # 因子配置（4 元素: 名称, 排序, 参数, 权重）
                "long_select_coin_num": 0.1,
                "hold_period": "1H",
                "market": "swap_swap",
                ...
            }

        Args:
            strategy_list: MCP 格式的策略配置列表

        Returns:
            引擎格式的策略配置列表
        """
        engine_list = []
        for idx, stg in enumerate(strategy_list):
            engine_stg = {
                # 必需字段
                "strategy": stg.get("strategy", f"dynamic_strategy_{idx}"),
                "cap_weight": stg.get("cap_weight", 1.0),
            }

            # 复制其他字段（排除 strategy, cap_weight, factor_list）
            for k, v in stg.items():
                if k not in ("strategy", "cap_weight", "factor_list"):
                    engine_stg[k] = v

            # 转换 factor_list 格式
            # MCP: [name, is_sort_asc, param] (3 元素)
            # 引擎: [name, is_sort_asc, param, weight] (4 元素)
            # 注意: param 需要转换为引擎期望的格式
            if "factor_list" in stg:
                converted_factors = []
                for factor in stg["factor_list"]:
                    if len(factor) >= 3:
                        name = factor[0]
                        is_sort_asc = factor[1]
                        param = factor[2]
                        weight = factor[3] if len(factor) >= 4 else 1

                        # 转换参数格式
                        # 引擎因子期望的参数格式因因子而异:
                        # - 简单因子（如 Bias）: 直接传整数值，如 24
                        # - 复杂因子: 可能需要字典或元组
                        #
                        # MCP 用户友好格式: {"n": 24} 或 {"n": 24, "m": 5}
                        # 转换规则:
                        # - 单参数字典 {"n": 24} -> 24 (提取值)
                        # - 多参数字典 {"n": 24, "m": 5} -> (24, 5) (按键排序后提取值为元组)
                        if isinstance(param, dict):
                            if len(param) == 1:
                                # 单参数: 直接提取值
                                param = list(param.values())[0]
                            else:
                                # 多参数: 按键排序后提取值为元组
                                param = tuple(v for k, v in sorted(param.items()))

                        converted_factors.append([name, is_sort_asc, param, weight])
                    else:
                        # 格式不正确，跳过
                        logger.warning(f"跳过格式不正确的因子配置: {factor}")
                        continue
                engine_stg["factor_list"] = converted_factors

            engine_list.append(engine_stg)
        return engine_list

    def shutdown(self, wait: bool = True):
        """关闭执行器"""
        self._executor.shutdown(wait=wait)
        logger.info("BacktestRunner 已关闭")


# 单例实例
_backtest_runner: Optional[BacktestRunner] = None


def get_backtest_runner() -> BacktestRunner:
    """获取回测执行器单例"""
    global _backtest_runner
    if _backtest_runner is None:
        _backtest_runner = BacktestRunner()
    return _backtest_runner
