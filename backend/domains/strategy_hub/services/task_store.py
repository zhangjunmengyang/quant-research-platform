"""
任务存储层

提供 BacktestTask 和 TaskExecution 的 PostgreSQL 数据库操作。
"""

import logging
import math
from datetime import datetime
from typing import Any

from domains.mcp_core.base import ThreadSafeConnectionMixin

from .models import BacktestTask, TaskExecution

logger = logging.getLogger(__name__)


class BacktestTaskStore(ThreadSafeConnectionMixin):
    """
    回测任务单存储

    继承 ThreadSafeConnectionMixin 实现线程安全的连接管理。
    """

    def __init__(self, database_url: str | None = None):
        self._init_connection(database_url)
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with self._cursor() as cursor:
            # 先检查表是否存在，避免 PostgreSQL 的 CREATE TABLE IF NOT EXISTS 竞态条件
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'backtest_tasks'
                )
            """)
            tasks_exists = cursor.fetchone()['exists']

            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'task_executions'
                )
            """)
            executions_exists = cursor.fetchone()['exists']

            if tasks_exists and executions_exists:
                logger.debug("任务表已存在，跳过创建")
                return

            # 创建 backtest_tasks 表
            if not tasks_exists:
                cursor.execute("""
                    CREATE TABLE backtest_tasks (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        config TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        tags TEXT,
                        notes TEXT,
                        execution_count INTEGER DEFAULT 0,
                        last_execution_at TEXT
                    )
                """)

            # 创建 task_executions 表
            if not executions_exists:
                cursor.execute("""
                    CREATE TABLE task_executions (
                        id TEXT PRIMARY KEY,
                        task_id TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'pending',
                        created_at TEXT NOT NULL,
                        started_at TEXT,
                        completed_at TEXT,
                        progress FLOAT DEFAULT 0.0,
                        message TEXT,
                        factor_list TEXT,
                        factor_params TEXT,
                        start_date TEXT,
                        end_date TEXT,
                        leverage FLOAT DEFAULT 1.0,
                        account_type TEXT DEFAULT '统一账户',
                        initial_usdt FLOAT DEFAULT 10000,
                        hold_period TEXT DEFAULT '1H',
                        long_select_coin_num FLOAT DEFAULT 5,
                        short_select_coin_num FLOAT DEFAULT 0,
                        cumulative_return FLOAT DEFAULT 0.0,
                        annual_return FLOAT DEFAULT 0.0,
                        max_drawdown FLOAT DEFAULT 0.0,
                        max_drawdown_start TEXT,
                        max_drawdown_end TEXT,
                        sharpe_ratio FLOAT DEFAULT 0.0,
                        recovery_rate FLOAT DEFAULT 0.0,
                        recovery_time TEXT,
                        win_periods INTEGER DEFAULT 0,
                        loss_periods INTEGER DEFAULT 0,
                        win_rate FLOAT DEFAULT 0.0,
                        avg_return_per_period FLOAT DEFAULT 0.0,
                        profit_loss_ratio FLOAT DEFAULT 0.0,
                        max_single_profit FLOAT DEFAULT 0.0,
                        max_single_loss FLOAT DEFAULT 0.0,
                        max_consecutive_wins INTEGER DEFAULT 0,
                        max_consecutive_losses INTEGER DEFAULT 0,
                        return_std FLOAT DEFAULT 0.0,
                        year_return TEXT,
                        quarter_return TEXT,
                        month_return TEXT,
                        equity_curve TEXT,
                        error_message TEXT,
                        strategy_id TEXT,
                        FOREIGN KEY (task_id) REFERENCES backtest_tasks(id) ON DELETE CASCADE
                    )
                """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON backtest_tasks(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_name ON backtest_tasks(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_task_id ON task_executions(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_status ON task_executions(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_created_at ON task_executions(created_at)")

            logger.info("任务存储数据库初始化完成")

    # =========================================================================
    # BacktestTask CRUD
    # =========================================================================

    def create_task(self, task: BacktestTask) -> BacktestTask:
        """创建任务单"""
        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO backtest_tasks
                (id, name, description, config, created_at, updated_at, tags, notes, execution_count, last_execution_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    task.id,
                    task.name,
                    task.description,
                    task.config,
                    task.created_at,
                    task.updated_at,
                    task.tags,
                    task.notes,
                    task.execution_count,
                    task.last_execution_at,
                ),
            )
        return task

    def get_task(self, task_id: str) -> BacktestTask | None:
        """获取任务单"""
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM backtest_tasks WHERE id = %s", (task_id,)
            )
            row = cursor.fetchone()
            if row:
                return BacktestTask.from_dict(dict(row))
            return None

    # 允许排序的字段白名单
    ALLOWED_ORDER_FIELDS = {"created_at", "updated_at", "name", "execution_count", "last_execution_at"}

    def list_tasks(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> tuple[list[BacktestTask], int]:
        """列出任务单"""
        # 验证 order_by 字段，防止 SQL 注入
        if order_by not in self.ALLOWED_ORDER_FIELDS:
            order_by = "created_at"

        with self._cursor() as cursor:
            # 构建查询条件
            where_clause = ""
            params: list[Any] = []

            if search:
                where_clause = "WHERE name ILIKE %s OR description ILIKE %s"
                params = [f"%{search}%", f"%{search}%"]

            # 获取总数
            count_sql = f"SELECT COUNT(*) as count FROM backtest_tasks {where_clause}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()['count']

            # 分页查询 (order_by 已验证，安全拼接)
            order = "DESC" if order_desc else "ASC"
            offset = (page - 1) * page_size
            query_sql = f"""
                SELECT * FROM backtest_tasks
                {where_clause}
                ORDER BY {order_by} {order}
                LIMIT %s OFFSET %s
            """
            cursor.execute(query_sql, params + [page_size, offset])
            rows = cursor.fetchall()

            tasks = [BacktestTask.from_dict(dict(row)) for row in rows]
            return tasks, total

    def update_task(self, task: BacktestTask) -> BacktestTask:
        """更新任务单"""
        task.updated_at = datetime.now().isoformat()
        with self._cursor() as cursor:
            cursor.execute(
                """
                UPDATE backtest_tasks
                SET name = %s, description = %s, config = %s, updated_at = %s,
                    tags = %s, notes = %s, execution_count = %s, last_execution_at = %s
                WHERE id = %s
                """,
                (
                    task.name,
                    task.description,
                    task.config,
                    task.updated_at,
                    task.tags,
                    task.notes,
                    task.execution_count,
                    task.last_execution_at,
                    task.id,
                ),
            )
        return task

    def delete_task(self, task_id: str) -> bool:
        """删除任务单（级联删除执行记录）"""
        with self._cursor() as cursor:
            # 先删除关联的执行记录
            cursor.execute("DELETE FROM task_executions WHERE task_id = %s", (task_id,))
            # 再删除任务单
            cursor.execute("DELETE FROM backtest_tasks WHERE id = %s", (task_id,))
            return cursor.rowcount > 0

    def increment_execution_count(self, task_id: str) -> None:
        """增加执行次数并更新最后执行时间"""
        now = datetime.now().isoformat()
        with self._cursor() as cursor:
            cursor.execute(
                """
                UPDATE backtest_tasks
                SET execution_count = execution_count + 1,
                    last_execution_at = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                (now, now, task_id),
            )

    # =========================================================================
    # TaskExecution CRUD
    # =========================================================================

    def create_execution(self, execution: TaskExecution) -> TaskExecution:
        """创建执行记录"""
        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO task_executions
                (id, task_id, status, created_at, started_at, completed_at,
                 progress, message, factor_list, factor_params,
                 start_date, end_date, leverage, account_type, initial_usdt,
                 hold_period, long_select_coin_num, short_select_coin_num,
                 cumulative_return, annual_return, max_drawdown,
                 max_drawdown_start, max_drawdown_end, sharpe_ratio,
                 recovery_rate, recovery_time,
                 win_periods, loss_periods, win_rate,
                 avg_return_per_period, profit_loss_ratio,
                 max_single_profit, max_single_loss,
                 max_consecutive_wins, max_consecutive_losses, return_std,
                 year_return, quarter_return, month_return, equity_curve,
                 error_message, strategy_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    execution.id,
                    execution.task_id,
                    execution.status,
                    execution.created_at,
                    execution.started_at,
                    execution.completed_at,
                    execution.progress,
                    execution.message,
                    execution.factor_list,
                    execution.factor_params,
                    execution.start_date,
                    execution.end_date,
                    execution.leverage,
                    execution.account_type,
                    execution.initial_usdt,
                    execution.hold_period,
                    execution.long_select_coin_num,
                    execution.short_select_coin_num,
                    execution.cumulative_return,
                    execution.annual_return,
                    execution.max_drawdown,
                    execution.max_drawdown_start,
                    execution.max_drawdown_end,
                    execution.sharpe_ratio,
                    execution.recovery_rate,
                    execution.recovery_time,
                    execution.win_periods,
                    execution.loss_periods,
                    execution.win_rate,
                    execution.avg_return_per_period,
                    execution.profit_loss_ratio,
                    execution.max_single_profit,
                    execution.max_single_loss,
                    execution.max_consecutive_wins,
                    execution.max_consecutive_losses,
                    execution.return_std,
                    execution.year_return,
                    execution.quarter_return,
                    execution.month_return,
                    execution.equity_curve,
                    execution.error_message,
                    execution.strategy_id,
                ),
            )
        return execution

    def get_execution(self, execution_id: str) -> TaskExecution | None:
        """获取执行记录"""
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM task_executions WHERE id = %s", (execution_id,)
            )
            row = cursor.fetchone()
            if row:
                return TaskExecution.from_dict(dict(row))
            return None

    def list_executions(
        self,
        task_id: str,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[TaskExecution], int]:
        """列出任务的执行记录"""
        with self._cursor() as cursor:
            # 构建查询条件
            where_clause = "WHERE task_id = %s"
            params: list[Any] = [task_id]

            if status:
                where_clause += " AND status = %s"
                params.append(status)

            # 获取总数
            count_sql = f"SELECT COUNT(*) as count FROM task_executions {where_clause}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()['count']

            # 分页查询
            offset = (page - 1) * page_size
            query_sql = f"""
                SELECT * FROM task_executions
                {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(query_sql, params + [page_size, offset])
            rows = cursor.fetchall()

            executions = [TaskExecution.from_dict(dict(row)) for row in rows]
            return executions, total

    def update_execution(self, execution: TaskExecution) -> TaskExecution:
        """更新执行记录"""
        with self._cursor() as cursor:
            cursor.execute(
                """
                UPDATE task_executions
                SET status = %s, started_at = %s, completed_at = %s,
                    progress = %s, message = %s,
                    cumulative_return = %s, annual_return = %s, max_drawdown = %s,
                    max_drawdown_start = %s, max_drawdown_end = %s, sharpe_ratio = %s,
                    recovery_rate = %s, recovery_time = %s,
                    win_periods = %s, loss_periods = %s, win_rate = %s,
                    avg_return_per_period = %s, profit_loss_ratio = %s,
                    max_single_profit = %s, max_single_loss = %s,
                    max_consecutive_wins = %s, max_consecutive_losses = %s, return_std = %s,
                    year_return = %s, quarter_return = %s, month_return = %s, equity_curve = %s,
                    error_message = %s, strategy_id = %s
                WHERE id = %s
                """,
                (
                    execution.status,
                    execution.started_at,
                    execution.completed_at,
                    execution.progress,
                    execution.message,
                    execution.cumulative_return,
                    execution.annual_return,
                    execution.max_drawdown,
                    execution.max_drawdown_start,
                    execution.max_drawdown_end,
                    execution.sharpe_ratio,
                    execution.recovery_rate,
                    execution.recovery_time,
                    execution.win_periods,
                    execution.loss_periods,
                    execution.win_rate,
                    execution.avg_return_per_period,
                    execution.profit_loss_ratio,
                    execution.max_single_profit,
                    execution.max_single_loss,
                    execution.max_consecutive_wins,
                    execution.max_consecutive_losses,
                    execution.return_std,
                    execution.year_return,
                    execution.quarter_return,
                    execution.month_return,
                    execution.equity_curve,
                    execution.error_message,
                    execution.strategy_id,
                    execution.id,
                ),
            )
        return execution

    def delete_execution(self, execution_id: str) -> bool:
        """删除执行记录"""
        with self._cursor() as cursor:
            cursor.execute(
                "DELETE FROM task_executions WHERE id = %s", (execution_id,)
            )
            return cursor.rowcount > 0

    def get_task_stats(self, task_id: str) -> dict[str, Any]:
        """获取任务的统计信息"""
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    AVG(CASE WHEN status = 'completed' THEN annual_return ELSE NULL END) as avg_annual_return,
                    AVG(CASE WHEN status = 'completed' THEN sharpe_ratio ELSE NULL END) as avg_sharpe_ratio,
                    MAX(CASE WHEN status = 'completed' THEN annual_return ELSE NULL END) as best_annual_return,
                    MIN(CASE WHEN status = 'completed' THEN annual_return ELSE NULL END) as worst_annual_return
                FROM task_executions
                WHERE task_id = %s
                """,
                (task_id,),
            )
            row = cursor.fetchone()

            def safe_float(val):
                """将可能为 None/nan/inf 的值转换为安全的 float 或 None"""
                if val is None:
                    return None
                f = float(val)
                if math.isnan(f) or math.isinf(f):
                    return None
                return f

            return {
                "total": row["total"] or 0,
                "completed": row["completed"] or 0,
                "failed": row["failed"] or 0,
                "running": row["running"] or 0,
                "pending": row["pending"] or 0,
                "avg_annual_return": safe_float(row["avg_annual_return"]),
                "avg_sharpe_ratio": safe_float(row["avg_sharpe_ratio"]),
                "best_annual_return": safe_float(row["best_annual_return"]),
                "worst_annual_return": safe_float(row["worst_annual_return"]),
            }


# 单例实例
_task_store: BacktestTaskStore | None = None


def get_task_store() -> BacktestTaskStore:
    """获取任务存储单例"""
    global _task_store
    if _task_store is None:
        _task_store = BacktestTaskStore()
    return _task_store


def reset_task_store():
    """重置任务存储单例（用于测试）"""
    global _task_store
    if _task_store:
        _task_store.close()
    _task_store = None
