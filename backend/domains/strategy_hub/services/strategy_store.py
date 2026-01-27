"""
策略存储层

基于 PostgreSQL 的策略持久化存储。
继承 mcp_core.BaseStore，复用连接管理和通用 CRUD。
"""

import logging
import math
from typing import Any, Dict, List, Optional, Set
from datetime import datetime

from domains.mcp_core.base import (
    BaseStore,
    get_store_instance,
    reset_store_instance,
)

from .models import Strategy

logger = logging.getLogger(__name__)


class StrategyStore(BaseStore[Strategy]):
    """
    策略存储层

    继承 BaseStore，提供策略的 CRUD 操作和高级查询功能。
    """

    # BaseStore 配置
    table_name = "strategies"

    allowed_columns: Set[str] = {
        # 基础信息
        'id', 'name', 'description',
        # 因子配置
        'factor_list', 'factor_params', 'strategy_config', 'sort_directions',
        # 回测配置
        'start_date', 'end_date', 'leverage', 'select_coin_num', 'trade_type',
        # 多空配置
        'long_select_coin_num', 'short_select_coin_num',
        'long_cap_weight', 'short_cap_weight',
        # 持仓配置
        'hold_period', 'offset', 'market',
        # 账户配置
        'account_type', 'initial_usdt', 'margin_rate',
        # 手续费配置
        'swap_c_rate', 'spot_c_rate',
        # 最小下单量
        'swap_min_order_limit', 'spot_min_order_limit',
        # 价格计算
        'avg_price_col',
        # 币种过滤
        'min_kline_num', 'black_list', 'white_list',
        # 核心绩效指标
        'cumulative_return', 'annual_return', 'max_drawdown',
        'max_drawdown_start', 'max_drawdown_end', 'sharpe_ratio',
        'recovery_rate', 'recovery_time',
        # 交易统计
        'win_periods', 'loss_periods', 'win_rate',
        'avg_return_per_period', 'profit_loss_ratio',
        'max_single_profit', 'max_single_loss',
        'max_consecutive_wins', 'max_consecutive_losses', 'return_std',
        # 周期收益
        'year_return', 'quarter_return', 'month_return', 'equity_curve',
        # 元数据
        'created_at', 'updated_at', 'verified', 'tags', 'notes',
        # 任务信息
        'task_id', 'task_status', 'error_message',
    }

    numeric_fields: Set[str] = {
        'leverage', 'select_coin_num',
        'long_select_coin_num', 'short_select_coin_num',
        'long_cap_weight', 'short_cap_weight',
        'initial_usdt', 'margin_rate',
        'swap_c_rate', 'spot_c_rate',
        'swap_min_order_limit', 'spot_min_order_limit',
        'min_kline_num',
        'cumulative_return', 'annual_return', 'max_drawdown',
        'sharpe_ratio', 'recovery_rate',
        'win_periods', 'loss_periods', 'win_rate',
        'avg_return_per_period', 'profit_loss_ratio',
        'max_single_profit', 'max_single_loss',
        'max_consecutive_wins', 'max_consecutive_losses', 'return_std',
    }

    # 允许排序的字段白名单
    ALLOWED_ORDER_FIELDS = {
        "created_at", "updated_at", "name", "annual_return", "max_drawdown",
        "sharpe_ratio", "win_rate", "cumulative_return", "leverage",
    }

    def __init__(self, database_url: Optional[str] = None):
        """
        初始化存储层

        Args:
            database_url: PostgreSQL 连接 URL
        """
        super().__init__(database_url)
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with self._cursor() as cursor:
            # 先检查表是否存在，避免 PostgreSQL 的 CREATE TABLE IF NOT EXISTS 竞态条件
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'strategies'
                )
            """)
            table_exists = cursor.fetchone()['exists']

            if table_exists:
                logger.debug("strategies 表已存在，跳过创建")
                return

            cursor.execute("""
                CREATE TABLE strategies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,

                    -- 因子配置
                    factor_list TEXT DEFAULT '[]',
                    factor_params TEXT DEFAULT '{}',
                    strategy_config TEXT,
                    sort_directions TEXT,

                    -- 回测配置
                    start_date TEXT,
                    end_date TEXT,
                    leverage FLOAT DEFAULT 1.0,
                    select_coin_num FLOAT DEFAULT 5,
                    trade_type TEXT DEFAULT 'swap',

                    -- 多空配置
                    long_select_coin_num FLOAT DEFAULT 5,
                    short_select_coin_num FLOAT DEFAULT 0,
                    long_cap_weight FLOAT DEFAULT 1.0,
                    short_cap_weight FLOAT DEFAULT 0.0,

                    -- 持仓配置
                    hold_period TEXT DEFAULT '1H',
                    "offset" INTEGER DEFAULT 0,
                    market TEXT DEFAULT 'swap_swap',

                    -- 账户配置
                    account_type TEXT DEFAULT '统一账户',
                    initial_usdt FLOAT DEFAULT 10000,
                    margin_rate FLOAT DEFAULT 0.05,

                    -- 手续费配置
                    swap_c_rate FLOAT DEFAULT 0.0006,
                    spot_c_rate FLOAT DEFAULT 0.001,

                    -- 最小下单量
                    swap_min_order_limit FLOAT DEFAULT 5,
                    spot_min_order_limit FLOAT DEFAULT 10,

                    -- 价格计算
                    avg_price_col TEXT DEFAULT 'avg_price_1m',

                    -- 币种过滤
                    min_kline_num INTEGER DEFAULT 0,
                    black_list TEXT,
                    white_list TEXT,

                    -- 核心绩效指标
                    cumulative_return FLOAT DEFAULT 0.0,
                    annual_return FLOAT DEFAULT 0.0,
                    max_drawdown FLOAT DEFAULT 0.0,
                    max_drawdown_start TEXT,
                    max_drawdown_end TEXT,
                    sharpe_ratio FLOAT DEFAULT 0.0,
                    recovery_rate FLOAT DEFAULT 0.0,
                    recovery_time TEXT,

                    -- 交易统计
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

                    -- 周期收益
                    year_return TEXT,
                    quarter_return TEXT,
                    month_return TEXT,
                    equity_curve TEXT,

                    -- 元数据
                    created_at TEXT,
                    updated_at TEXT,
                    verified BOOLEAN DEFAULT FALSE,
                    tags TEXT,
                    notes TEXT,

                    -- 任务信息
                    task_id TEXT,
                    task_status TEXT DEFAULT 'pending',
                    error_message TEXT
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategies_name ON strategies(name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategies_verified ON strategies(verified)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategies_task_status ON strategies(task_status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategies_annual_return ON strategies(annual_return)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_strategies_sharpe_ratio ON strategies(sharpe_ratio)")

            logger.info("策略数据库初始化完成")

    def _row_to_entity(self, row: Dict[str, Any]) -> Strategy:
        """将数据库行转换为 Strategy 对象（BaseStore 抽象方法实现）"""
        return self._row_to_strategy(row)

    def _row_to_strategy(self, row: Dict[str, Any]) -> Strategy:
        """将数据库行转换为 Strategy 对象"""
        def get_col(name, default=None):
            return row.get(name) if row.get(name) is not None else default

        def safe_float(val, default=0.0):
            """将可能为 None/nan/inf 的值转换为安全的 float"""
            if val is None:
                return default
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return default
            return f

        return Strategy(
            id=row["id"],
            name=row["name"],
            description=row.get("description"),
            # 因子配置
            factor_list=row.get("factor_list") or "[]",
            factor_params=row.get("factor_params") or "{}",
            strategy_config=get_col("strategy_config"),
            sort_directions=get_col("sort_directions"),
            # 回测配置
            start_date=row.get("start_date") or "",
            end_date=row.get("end_date") or "",
            leverage=row.get("leverage") or 1.0,
            select_coin_num=row.get("select_coin_num") or 5,
            trade_type=row.get("trade_type") or "swap",
            # 多空配置
            long_select_coin_num=get_col("long_select_coin_num", 5),
            short_select_coin_num=get_col("short_select_coin_num", 0),
            long_cap_weight=get_col("long_cap_weight", 1.0),
            short_cap_weight=get_col("short_cap_weight", 0.0),
            # 持仓配置
            hold_period=get_col("hold_period", "1H"),
            offset=get_col("offset", 0),
            market=get_col("market", "swap_swap"),
            # 账户配置
            account_type=get_col("account_type", "统一账户"),
            initial_usdt=get_col("initial_usdt", 10000),
            margin_rate=get_col("margin_rate", 0.05),
            # 手续费配置
            swap_c_rate=get_col("swap_c_rate", 0.0006),
            spot_c_rate=get_col("spot_c_rate", 0.001),
            # 最小下单量
            swap_min_order_limit=get_col("swap_min_order_limit", 5),
            spot_min_order_limit=get_col("spot_min_order_limit", 10),
            # 价格计算
            avg_price_col=get_col("avg_price_col", "avg_price_1m"),
            # 币种过滤
            min_kline_num=get_col("min_kline_num", 0),
            black_list=get_col("black_list"),
            white_list=get_col("white_list"),
            # 绩效指标
            cumulative_return=safe_float(row.get("cumulative_return")),
            annual_return=safe_float(row.get("annual_return")),
            max_drawdown=safe_float(row.get("max_drawdown")),
            max_drawdown_start=row.get("max_drawdown_start"),
            max_drawdown_end=row.get("max_drawdown_end"),
            sharpe_ratio=safe_float(row.get("sharpe_ratio")),
            recovery_rate=safe_float(row.get("recovery_rate")),
            recovery_time=row.get("recovery_time"),
            win_periods=row.get("win_periods") or 0,
            loss_periods=row.get("loss_periods") or 0,
            win_rate=safe_float(row.get("win_rate")),
            avg_return_per_period=safe_float(row.get("avg_return_per_period")),
            profit_loss_ratio=safe_float(row.get("profit_loss_ratio")),
            max_single_profit=safe_float(row.get("max_single_profit")),
            max_single_loss=safe_float(row.get("max_single_loss")),
            max_consecutive_wins=row.get("max_consecutive_wins") or 0,
            max_consecutive_losses=row.get("max_consecutive_losses") or 0,
            return_std=safe_float(row.get("return_std")),
            year_return=row.get("year_return"),
            quarter_return=row.get("quarter_return"),
            month_return=row.get("month_return"),
            equity_curve=row.get("equity_curve"),
            created_at=row.get("created_at") or datetime.now().isoformat(),
            updated_at=row.get("updated_at") or datetime.now().isoformat(),
            verified=bool(row.get("verified")),
            tags=row.get("tags"),
            notes=row.get("notes"),
            task_id=row.get("task_id") or "",
            task_status=row.get("task_status") or "pending",
            error_message=row.get("error_message"),
        )

    # ===== CRUD 操作 =====

    def add(self, strategy: Strategy) -> Strategy:
        """添加策略（统一接口命名）"""
        strategy.updated_at = datetime.now().isoformat()

        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO strategies (
                    id, name, description,
                    factor_list, factor_params, strategy_config, sort_directions,
                    start_date, end_date, leverage, select_coin_num, trade_type,
                    long_select_coin_num, short_select_coin_num,
                    long_cap_weight, short_cap_weight,
                    hold_period, "offset", market,
                    account_type, initial_usdt, margin_rate,
                    swap_c_rate, spot_c_rate,
                    swap_min_order_limit, spot_min_order_limit,
                    avg_price_col, min_kline_num, black_list, white_list,
                    cumulative_return, annual_return, max_drawdown,
                    max_drawdown_start, max_drawdown_end, sharpe_ratio,
                    recovery_rate, recovery_time,
                    win_periods, loss_periods, win_rate,
                    avg_return_per_period, profit_loss_ratio,
                    max_single_profit, max_single_loss,
                    max_consecutive_wins, max_consecutive_losses, return_std,
                    year_return, quarter_return, month_return, equity_curve,
                    created_at, updated_at, verified, tags, notes,
                    task_id, task_status, error_message
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                strategy.id, strategy.name, strategy.description,
                strategy.factor_list, strategy.factor_params,
                strategy.strategy_config, strategy.sort_directions,
                strategy.start_date, strategy.end_date, strategy.leverage,
                strategy.select_coin_num, strategy.trade_type,
                strategy.long_select_coin_num, strategy.short_select_coin_num,
                strategy.long_cap_weight, strategy.short_cap_weight,
                strategy.hold_period, strategy.offset, strategy.market,
                strategy.account_type, strategy.initial_usdt, strategy.margin_rate,
                strategy.swap_c_rate, strategy.spot_c_rate,
                strategy.swap_min_order_limit, strategy.spot_min_order_limit,
                strategy.avg_price_col, strategy.min_kline_num,
                strategy.black_list, strategy.white_list,
                strategy.cumulative_return, strategy.annual_return, strategy.max_drawdown,
                strategy.max_drawdown_start, strategy.max_drawdown_end, strategy.sharpe_ratio,
                strategy.recovery_rate, strategy.recovery_time,
                strategy.win_periods, strategy.loss_periods, strategy.win_rate,
                strategy.avg_return_per_period, strategy.profit_loss_ratio,
                strategy.max_single_profit, strategy.max_single_loss,
                strategy.max_consecutive_wins, strategy.max_consecutive_losses, strategy.return_std,
                strategy.year_return, strategy.quarter_return, strategy.month_return, strategy.equity_curve,
                strategy.created_at, strategy.updated_at,
                strategy.verified,
                strategy.tags, strategy.notes,
                strategy.task_id, strategy.task_status, strategy.error_message,
            ))
            logger.info(f"创建策略: {strategy.id} - {strategy.name}")

        # 触发实时同步
        self._trigger_sync(strategy.id)

        return strategy

    # 向后兼容别名
    create = add

    def get(self, strategy_id: str) -> Optional[Strategy]:
        """获取策略"""
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM strategies WHERE id = %s", (strategy_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_strategy(dict(row))
            return None

    def get_by_name(self, name: str) -> Optional[Strategy]:
        """按名称获取策略"""
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM strategies WHERE name = %s", (name,))
            row = cursor.fetchone()
            if row:
                return self._row_to_strategy(dict(row))
            return None

    def update(self, strategy: Strategy) -> Strategy:
        """更新策略"""
        strategy.updated_at = datetime.now().isoformat()

        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE strategies SET
                    name = %s, description = %s,
                    factor_list = %s, factor_params = %s,
                    strategy_config = %s, sort_directions = %s,
                    start_date = %s, end_date = %s, leverage = %s,
                    select_coin_num = %s, trade_type = %s,
                    long_select_coin_num = %s, short_select_coin_num = %s,
                    long_cap_weight = %s, short_cap_weight = %s,
                    hold_period = %s, "offset" = %s, market = %s,
                    account_type = %s, initial_usdt = %s, margin_rate = %s,
                    swap_c_rate = %s, spot_c_rate = %s,
                    swap_min_order_limit = %s, spot_min_order_limit = %s,
                    avg_price_col = %s, min_kline_num = %s,
                    black_list = %s, white_list = %s,
                    cumulative_return = %s, annual_return = %s, max_drawdown = %s,
                    max_drawdown_start = %s, max_drawdown_end = %s, sharpe_ratio = %s,
                    recovery_rate = %s, recovery_time = %s,
                    win_periods = %s, loss_periods = %s, win_rate = %s,
                    avg_return_per_period = %s, profit_loss_ratio = %s,
                    max_single_profit = %s, max_single_loss = %s,
                    max_consecutive_wins = %s, max_consecutive_losses = %s, return_std = %s,
                    year_return = %s, quarter_return = %s, month_return = %s, equity_curve = %s,
                    updated_at = %s, verified = %s, tags = %s, notes = %s,
                    task_id = %s, task_status = %s, error_message = %s
                WHERE id = %s
            """, (
                strategy.name, strategy.description,
                strategy.factor_list, strategy.factor_params,
                strategy.strategy_config, strategy.sort_directions,
                strategy.start_date, strategy.end_date, strategy.leverage,
                strategy.select_coin_num, strategy.trade_type,
                strategy.long_select_coin_num, strategy.short_select_coin_num,
                strategy.long_cap_weight, strategy.short_cap_weight,
                strategy.hold_period, strategy.offset, strategy.market,
                strategy.account_type, strategy.initial_usdt, strategy.margin_rate,
                strategy.swap_c_rate, strategy.spot_c_rate,
                strategy.swap_min_order_limit, strategy.spot_min_order_limit,
                strategy.avg_price_col, strategy.min_kline_num,
                strategy.black_list, strategy.white_list,
                strategy.cumulative_return, strategy.annual_return, strategy.max_drawdown,
                strategy.max_drawdown_start, strategy.max_drawdown_end, strategy.sharpe_ratio,
                strategy.recovery_rate, strategy.recovery_time,
                strategy.win_periods, strategy.loss_periods, strategy.win_rate,
                strategy.avg_return_per_period, strategy.profit_loss_ratio,
                strategy.max_single_profit, strategy.max_single_loss,
                strategy.max_consecutive_wins, strategy.max_consecutive_losses, strategy.return_std,
                strategy.year_return, strategy.quarter_return, strategy.month_return, strategy.equity_curve,
                strategy.updated_at,
                strategy.verified,
                strategy.tags, strategy.notes,
                strategy.task_id, strategy.task_status, strategy.error_message,
                strategy.id,
            ))
            logger.debug(f"更新策略: {strategy.id}")

        # 触发实时同步
        self._trigger_sync(strategy.id)

        return strategy

    def _trigger_sync(self, strategy_id: str) -> None:
        """触发策略同步到文件（不阻塞主流程）"""
        try:
            from domains.mcp_core.sync.trigger import get_sync_trigger
            get_sync_trigger().sync_strategy(strategy_id)
        except Exception as e:
            # 同步失败只记录日志，不影响主业务
            logger.debug(f"strategy_sync_trigger_skipped: {strategy_id}, {e}")

    def delete(self, strategy_id: str) -> bool:
        """删除策略"""
        with self._cursor() as cursor:
            cursor.execute("DELETE FROM strategies WHERE id = %s", (strategy_id,))
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"删除策略: {strategy_id}")
            return deleted

    # ===== 查询操作 =====

    def list_all(
        self,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = "created_at",
        order_desc: bool = True,
        limit: Optional[int] = None,
        offset: int = 0,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> tuple[List[Strategy], int]:
        """
        列出所有策略

        Args:
            filters: 过滤条件 {"verified": True, "trade_type": "swap"}
            order_by: 排序字段
            order_desc: 是否降序
            limit: 限制数量
            offset: 偏移量
            page: 页码（从1开始），与 page_size 一起使用
            page_size: 每页数量

        Returns:
            (策略列表, 总数)
        """
        # 验证 order_by 字段，防止 SQL 注入
        if order_by not in self.ALLOWED_ORDER_FIELDS:
            order_by = "created_at"

        if page is not None and page_size is not None:
            limit = page_size
            offset = (page - 1) * page_size

        query = "SELECT * FROM strategies"
        count_query = "SELECT COUNT(*) FROM strategies"
        params = []

        # 构建 WHERE 子句
        if filters:
            conditions = []
            for key, value in filters.items():
                if value is None:
                    conditions.append(f"{key} IS NULL")
                elif isinstance(value, bool):
                    # verified 是 integer 类型 (0/1)，需要转换
                    conditions.append(f"{key} = %s")
                    params.append(1 if value else 0)
                else:
                    conditions.append(f"{key} = %s")
                    params.append(value)
            if conditions:
                where_clause = " WHERE " + " AND ".join(conditions)
                query += where_clause
                count_query += where_clause

        with self._cursor() as cursor:
            # 获取总数
            cursor.execute(count_query, params)
            total = cursor.fetchone()['count']

            # ORDER BY (order_by 已验证，安全拼接)
            order_dir = "DESC" if order_desc else "ASC"
            query += f" ORDER BY {order_by} {order_dir}"

            # LIMIT & OFFSET
            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"

            cursor.execute(query, params)
            strategies = [self._row_to_strategy(dict(row)) for row in cursor.fetchall()]

            return strategies, total

    def search(self, query: str) -> List[Strategy]:
        """搜索策略（按名称和描述）"""
        search_pattern = f"%{query}%"
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM strategies
                WHERE name ILIKE %s OR description ILIKE %s OR factor_list ILIKE %s
                ORDER BY created_at DESC
            """, (search_pattern, search_pattern, search_pattern))
            return [self._row_to_strategy(dict(row)) for row in cursor.fetchall()]

    def get_by_factor(self, factor_name: str) -> List[Strategy]:
        """获取使用指定因子的策略"""
        search_pattern = f'%"{factor_name}"%'
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM strategies
                WHERE factor_list ILIKE %s
                ORDER BY created_at DESC
            """, (search_pattern,))
            return [self._row_to_strategy(dict(row)) for row in cursor.fetchall()]

    def get_verified(self) -> List[Strategy]:
        """获取已验证的策略"""
        strategies, _ = self.list_all(filters={"verified": True})
        return strategies

    # ===== 统计操作 =====

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM strategies")
            total = cursor.fetchone()['count']

            # verified 是 BOOLEAN 类型
            cursor.execute("SELECT COUNT(*) as count FROM strategies WHERE verified = TRUE")
            verified = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM strategies WHERE task_status = 'completed'")
            completed = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM strategies WHERE task_status = 'failed'")
            failed = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM strategies WHERE task_status = 'running'")
            running = cursor.fetchone()['count']

            cursor.execute("""
                SELECT
                    AVG(annual_return) as avg_annual_return,
                    AVG(max_drawdown) as avg_max_drawdown,
                    AVG(sharpe_ratio) as avg_sharpe_ratio,
                    AVG(win_rate) as avg_win_rate
                FROM strategies WHERE task_status = 'completed'
            """)
            row = cursor.fetchone()

            def safe_float(val, default=0.0):
                """将可能为 None/nan/inf 的值转换为安全的 float"""
                if val is None:
                    return default
                f = float(val)
                if math.isnan(f) or math.isinf(f):
                    return default
                return f

            return {
                "total": total,
                "verified": verified,
                "completed": completed,
                "failed": failed,
                "running": running,
                "avg_annual_return": safe_float(row['avg_annual_return']),
                "avg_max_drawdown": safe_float(row['avg_max_drawdown']),
                "avg_sharpe_ratio": safe_float(row['avg_sharpe_ratio']),
                "avg_win_rate": safe_float(row['avg_win_rate']),
            }

    def get_top_performers(
        self,
        metric: str = "annual_return",
        n: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Strategy]:
        """
        获取绩效最佳的策略

        Args:
            metric: 排序指标 (annual_return, sharpe_ratio, win_rate, etc.)
            n: 返回数量
            filters: 过滤条件
        """
        strategies, _ = self.list_all(
            filters=filters,
            order_by=metric,
            order_desc=True,
            limit=n,
        )
        return strategies

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """计数"""
        query = "SELECT COUNT(*) as count FROM strategies"
        params = []

        if filters:
            conditions = []
            for key, value in filters.items():
                if value is None:
                    conditions.append(f"{key} IS NULL")
                elif isinstance(value, bool):
                    conditions.append(f"{key} = %s")
                    params.append(value)
                else:
                    conditions.append(f"{key} = %s")
                    params.append(value)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        with self._cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()['count']


def get_strategy_store() -> StrategyStore:
    """获取策略存储单例"""
    return get_store_instance(StrategyStore)


def reset_strategy_store():
    """重置策略存储单例（用于测试）"""
    reset_store_instance("StrategyStore")
