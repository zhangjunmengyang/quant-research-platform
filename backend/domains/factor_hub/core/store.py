"""
因子存储层 - PostgreSQL 数据源

提供因子的持久化存储和查询功能。
继承 mcp_core.BaseStore，复用连接管理和通用 CRUD。
"""

import uuid as uuid_lib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import psycopg2

from domains.mcp_core.base.store import (
    BaseStore,
    get_database_url,
    get_store_instance,
    reset_store_instance,
)
from domains.mcp_core.database.query_builder import QueryBuilder

from .models import Factor, FactorType
from .config import get_config_loader

logger = logging.getLogger(__name__)


class FactorStore(BaseStore[Factor]):
    """
    因子存储层 - PostgreSQL 数据源

    继承 BaseStore，提供因子的 CRUD 操作、查询、统计等功能。
    """

    # BaseStore 配置
    table_name = "factors"

    allowed_columns = {
        'filename', 'factor_type', 'uuid', 'style', 'formula', 'input_data',
        'value_range', 'description', 'analysis', 'code_path', 'code_content',
        'llm_score', 'ic', 'rank_ic', 'verified', 'verify_note',
        'created_at', 'updated_at', 'backtest_sharpe', 'backtest_ic',
        'backtest_ir', 'turnover', 'decay', 'market_regime',
        'best_holding_period', 'tags', 'code_complexity',
        'last_backtest_date', 'excluded', 'exclude_reason', 'param_analysis'
    }

    numeric_fields = {
        'llm_score', 'ic', 'rank_ic', 'backtest_sharpe',
        'backtest_ic', 'backtest_ir', 'turnover', 'decay',
        'code_complexity', 'best_holding_period'
    }

    # 向后兼容别名
    ALLOWED_COLUMNS = allowed_columns
    ALLOWED_ORDER_COLUMNS = allowed_columns
    NUMERIC_FIELDS = tuple(numeric_fields)

    # 列名映射（用于导出）
    COLUMN_MAPPING = {
        '文件名': 'filename',
        '因子风格': 'style',
        '核心公式': 'formula',
        '输入数据': 'input_data',
        '值域': 'value_range',
        '刻画特征': 'description',
        '因子分析': 'analysis',
        '代码': 'code_path',
        '大模型评分': 'llm_score',
        '已验证': 'verified',
        '验证备注': 'verify_note',
    }

    REVERSE_MAPPING = {v: k for k, v in COLUMN_MAPPING.items()}

    def _row_to_entity(self, row: Dict[str, Any]) -> Factor:
        """将数据库行转换为 Factor 对象"""
        return self._row_to_factor(row)

    def _row_to_factor(self, row: Dict[str, Any]) -> Factor:
        """将数据库行转换为 Factor 对象"""
        # 处理 PostgreSQL 的布尔值 -> int（Factor 模型中定义为 int）
        if 'verified' in row:
            row['verified'] = 1 if row['verified'] else 0
        if 'excluded' in row:
            row['excluded'] = 1 if row['excluded'] else 0

        # 移除 Factor 模型中不存在的字段
        valid_fields = {k: v for k, v in row.items() if k in Factor.__dataclass_fields__}
        return Factor(**valid_fields)

    def _create_query_builder(self) -> QueryBuilder:
        """创建查询构建器"""
        return QueryBuilder(
            table=self.table_name,
            allowed_columns=self.allowed_columns,
            numeric_fields=self.numeric_fields
        )

    # ==================== 基本 CRUD ====================

    def get(self, filename: str, include_excluded: bool = False) -> Optional[Factor]:
        """获取单个因子"""
        with self._cursor() as cursor:
            if include_excluded:
                cursor.execute(
                    'SELECT * FROM factors WHERE filename = %s',
                    (filename,)
                )
            else:
                cursor.execute(
                    'SELECT * FROM factors WHERE filename = %s AND excluded = FALSE',
                    (filename,)
                )
            row = cursor.fetchone()
            if row:
                return self._row_to_factor(dict(row))
        return None

    def get_all(self, include_excluded: bool = False) -> List[Factor]:
        """获取所有因子"""
        with self._cursor() as cursor:
            if include_excluded:
                cursor.execute('SELECT * FROM factors ORDER BY filename')
            else:
                cursor.execute(
                    'SELECT * FROM factors WHERE excluded = FALSE ORDER BY filename'
                )
            return [self._row_to_factor(dict(row)) for row in cursor.fetchall()]

    def add(self, factor: Factor) -> bool:
        """添加因子"""
        if not factor.uuid:
            factor.uuid = str(uuid_lib.uuid4())
        factor.created_at = datetime.now()
        factor.updated_at = datetime.now()

        try:
            with self._cursor() as cursor:
                cursor.execute('''
                    INSERT INTO factors (
                        filename, factor_type, uuid, style, formula, input_data, value_range,
                        description, analysis, code_path, code_content, llm_score,
                        ic, rank_ic, verified, verify_note, created_at, updated_at,
                        backtest_sharpe, backtest_ic, backtest_ir, turnover, decay,
                        market_regime, best_holding_period, tags, code_complexity,
                        last_backtest_date, excluded, exclude_reason, param_analysis
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                ''', (
                    factor.filename, factor.factor_type, factor.uuid, factor.style,
                    factor.formula, factor.input_data, factor.value_range, factor.description,
                    factor.analysis, factor.code_path, factor.code_content,
                    factor.llm_score, factor.ic, factor.rank_ic, bool(factor.verified),
                    factor.verify_note, factor.created_at, factor.updated_at,
                    factor.backtest_sharpe, factor.backtest_ic, factor.backtest_ir,
                    factor.turnover, factor.decay, factor.market_regime,
                    factor.best_holding_period, factor.tags, factor.code_complexity,
                    factor.last_backtest_date, bool(factor.excluded), factor.exclude_reason,
                    factor.param_analysis
                ))
            return True
        except psycopg2.IntegrityError:
            return False

    def update(self, filename: str, **fields) -> bool:
        """更新因子字段"""
        if not fields:
            return False

        # 安全验证字段名，防止 SQL 注入
        safe_fields = {k: v for k, v in fields.items() if k in self.allowed_columns}
        if not safe_fields:
            logger.warning(f"No valid fields to update: {list(fields.keys())}")
            return False

        safe_fields['updated_at'] = datetime.now()

        # 处理布尔字段
        if 'verified' in safe_fields:
            safe_fields['verified'] = bool(safe_fields['verified'])
        if 'excluded' in safe_fields:
            safe_fields['excluded'] = bool(safe_fields['excluded'])

        set_clause = ', '.join(f'{k} = %s' for k in safe_fields.keys())
        values = list(safe_fields.values()) + [filename]

        with self._cursor() as cursor:
            cursor.execute(
                f'UPDATE factors SET {set_clause} WHERE filename = %s',
                values
            )
            return cursor.rowcount > 0

    def delete(self, filename: str) -> bool:
        """删除因子"""
        with self._cursor() as cursor:
            cursor.execute('DELETE FROM factors WHERE filename = %s', (filename,))
            return cursor.rowcount > 0

    # ==================== 批量操作 ====================

    def batch_add(self, factors: List[Factor]) -> Tuple[int, int]:
        """批量添加因子，返回 (成功数, 失败数)"""
        success, failed = 0, 0
        for factor in factors:
            if self.add(factor):
                success += 1
            else:
                failed += 1
        return success, failed

    # ==================== 查询操作 ====================

    def query(
        self,
        filter_condition: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        include_excluded: bool = False
    ) -> List[Factor]:
        """
        条件查询因子

        Args:
            filter_condition: 筛选条件，支持特殊语法:
                - ">=value", "<=value", ">value", "<value": 比较
                - "empty": 空值
                - "not_empty": 非空
                - "contains:keyword": 包含关键词
            order_by: 排序字段 (如 "llm_score DESC")
            limit: 限制数量
            offset: 偏移量
            include_excluded: 是否包含已排除的因子
        """
        builder = self._create_query_builder()

        # 默认排除已排除的因子
        if not include_excluded:
            builder.where_raw('excluded = FALSE')

        # 添加筛选条件
        if filter_condition:
            for field, value in filter_condition.items():
                builder.where(field, value)

        # 排序
        if order_by:
            builder.order_by(order_by)

        # 分页
        if limit is not None:
            builder.limit(limit)
        if offset is not None:
            builder.offset(offset)

        sql, params = builder.build()

        with self._cursor() as cursor:
            cursor.execute(sql, params)
            return [self._row_to_factor(dict(row)) for row in cursor.fetchall()]

    def get_unscored(self) -> List[Factor]:
        """获取未评分的因子"""
        return self.query({'llm_score': 'empty'})

    def get_verified(self) -> List[Factor]:
        """获取已验证的因子"""
        return self.query({'verified': True})

    def get_low_score(self, threshold: float = 2.0) -> List[Factor]:
        """获取低分因子"""
        return self.query({'llm_score': f'<{threshold}'})

    def count(self, filter_condition: Optional[Dict[str, Any]] = None) -> int:
        """统计因子数量"""
        return len(self.query(filter_condition))

    def get_styles(self) -> List[str]:
        """获取所有因子风格（去重）"""
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT style FROM factors WHERE style != '' AND excluded = FALSE ORDER BY style"
            )
            styles = set()
            for row in cursor.fetchall():
                for s in row['style'].split(','):
                    s = s.strip()
                    if s:
                        styles.add(s)
            return sorted(styles)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        优化版本：使用单次 SQL 查询获取所有基础统计，减少数据库往返
        """
        with self._cursor() as cursor:
            # 单次查询获取所有基础统计
            cursor.execute('''
                SELECT
                    COUNT(*) FILTER (WHERE excluded = FALSE) as total,
                    COUNT(*) FILTER (WHERE excluded = FALSE AND llm_score IS NOT NULL) as scored,
                    COUNT(*) FILTER (WHERE excluded = FALSE AND verified = TRUE) as verified,
                    COUNT(*) FILTER (WHERE excluded = TRUE) as excluded_count,
                    AVG(llm_score) FILTER (WHERE excluded = FALSE AND llm_score IS NOT NULL) as avg_score,
                    MIN(llm_score) FILTER (WHERE excluded = FALSE AND llm_score IS NOT NULL) as min_score,
                    MAX(llm_score) FILTER (WHERE excluded = FALSE AND llm_score IS NOT NULL) as max_score
                FROM factors
            ''')
            stats_row = cursor.fetchone()

            total = stats_row['total'] or 0
            scored = stats_row['scored'] or 0
            verified = stats_row['verified'] or 0
            excluded_count = stats_row['excluded_count'] or 0

            score_stats = {}
            if stats_row['avg_score'] is not None:
                score_stats = {
                    'avg': round(float(stats_row['avg_score']), 2),
                    'min': float(stats_row['min_score']),
                    'max': float(stats_row['max_score'])
                }

            # 评分分布 - 单次查询
            cursor.execute('''
                SELECT
                    CASE
                        WHEN llm_score >= 4.5 THEN '4.5-5'
                        WHEN llm_score >= 4.0 THEN '4-4.5'
                        WHEN llm_score >= 3.5 THEN '3.5-4'
                        WHEN llm_score >= 3.0 THEN '3-3.5'
                        WHEN llm_score >= 2.5 THEN '2.5-3'
                        WHEN llm_score >= 2.0 THEN '2-2.5'
                        WHEN llm_score >= 1.5 THEN '1.5-2'
                        WHEN llm_score >= 1.0 THEN '1-1.5'
                        WHEN llm_score >= 0.5 THEN '0.5-1'
                        WHEN llm_score >= 0 THEN '0-0.5'
                        ELSE '未评分'
                    END as score_range,
                    COUNT(*) as count
                FROM factors WHERE excluded = FALSE GROUP BY score_range
            ''')
            score_dist = {row['score_range']: row['count'] for row in cursor.fetchall()}

            # 风格分布 - 只获取 style 字段，避免全表扫描
            cursor.execute(
                "SELECT style FROM factors WHERE excluded = FALSE AND style != ''"
            )
            style_dist = {}
            for row in cursor.fetchall():
                for style in row['style'].split(','):
                    style = style.strip()
                    if style:
                        style_dist[style] = style_dist.get(style, 0) + 1

            # 入库时间分布（按月）- 使用 SQL 聚合
            cursor.execute('''
                SELECT TO_CHAR(created_at, 'YYYY-MM') as month, COUNT(*) as count
                FROM factors
                WHERE created_at IS NOT NULL AND excluded = FALSE
                GROUP BY TO_CHAR(created_at, 'YYYY-MM')
                ORDER BY month
            ''')
            time_dist = {row['month']: row['count'] for row in cursor.fetchall()}

            # IC/RankIC 统计 - 合并为单次查询
            cursor.execute('''
                SELECT
                    AVG(ic) as avg_ic, MIN(ic) as min_ic, MAX(ic) as max_ic, COUNT(ic) as count_ic,
                    AVG(rank_ic) as avg_rank_ic, MIN(rank_ic) as min_rank_ic,
                    MAX(rank_ic) as max_rank_ic, COUNT(rank_ic) as count_rank_ic
                FROM factors WHERE excluded = FALSE
            ''')
            ic_row = cursor.fetchone()

            ic_stats = {}
            if ic_row['avg_ic'] is not None:
                ic_stats = {
                    'avg': round(float(ic_row['avg_ic']), 4),
                    'min': round(float(ic_row['min_ic']), 4),
                    'max': round(float(ic_row['max_ic']), 4),
                    'count': ic_row['count_ic']
                }

            rank_ic_stats = {}
            if ic_row['avg_rank_ic'] is not None:
                rank_ic_stats = {
                    'avg': round(float(ic_row['avg_rank_ic']), 4),
                    'min': round(float(ic_row['min_rank_ic']), 4),
                    'max': round(float(ic_row['max_rank_ic']), 4),
                    'count': ic_row['count_rank_ic']
                }

        return {
            'total': total,
            'scored': scored,
            'unscored': total - scored,
            'verified': verified,
            'excluded': excluded_count,
            'score_distribution': score_dist,
            'style_distribution': style_dist,
            'score_stats': score_stats,
            'time_distribution': time_dist,
            'ic_stats': ic_stats,
            'rank_ic_stats': rank_ic_stats,
        }

    # ==================== 状态管理 ====================

    def verify(self, filename: str, note: str = "") -> bool:
        """标记因子为已验证"""
        return self.update(filename, verified=True, verify_note=note)

    def unverify(self, filename: str) -> bool:
        """取消因子验证状态"""
        return self.update(filename, verified=False, verify_note="")

    # ==================== 排除因子管理 ====================

    def get_excluded_factors(self) -> Dict[str, str]:
        """获取所有排除的因子，返回 {filename: reason}"""
        excluded = {}
        with self._cursor() as cursor:
            cursor.execute(
                'SELECT filename, exclude_reason FROM factors WHERE excluded = TRUE'
            )
            for row in cursor.fetchall():
                excluded[row['filename']] = row['exclude_reason'] or ""
        return excluded

    def exclude_factor(self, filename: str, reason: str = "") -> bool:
        """排除因子（标记为已排除，不删除数据）"""
        return self.update(filename, excluded=True, exclude_reason=reason)

    def unexclude_factor(self, filename: str) -> bool:
        """取消排除因子"""
        return self.update(filename, excluded=False, exclude_reason="")

    # ==================== 代码同步 ====================

    def sync_code_from_files(self) -> Dict[str, int]:
        """从 factors/ 目录同步代码到数据库"""
        config = get_config_loader()
        stats = {"updated": 0, "created": 0, "unchanged": 0}
        excluded = self.get_excluded_factors()

        # 同步时序因子（factors/ 目录）
        factors_dir = config.factors_dir
        if factors_dir.exists():
            self._sync_directory(
                directory=factors_dir,
                factor_type=FactorType.TIME_SERIES,
                excluded=excluded,
                stats=stats
            )

        # 同步截面因子（sections/ 目录）
        sections_dir = config.project_root / "sections"
        if sections_dir.exists():
            self._sync_directory(
                directory=sections_dir,
                factor_type=FactorType.CROSS_SECTION,
                excluded=excluded,
                stats=stats
            )

        return stats

    def _sync_directory(
        self,
        directory: Path,
        factor_type: str,
        excluded: Dict[str, str],
        stats: Dict[str, int]
    ):
        """同步单个目录的因子文件"""
        for py_file in directory.glob("*.py"):
            filename = py_file.stem

            if filename in excluded:
                continue

            try:
                code_content = py_file.read_text(encoding='utf-8')
            except Exception:
                continue

            existing = self.get(filename)

            if existing is None:
                factor = Factor(
                    filename=filename,
                    factor_type=factor_type,
                    code_content=code_content,
                    code_path=str(py_file),
                )
                if self.add(factor):
                    stats["created"] += 1
            else:
                needs_update = False
                update_fields = {}

                if existing.code_content != code_content:
                    update_fields["code_content"] = code_content
                    update_fields["code_path"] = str(py_file)
                    needs_update = True

                if existing.factor_type != factor_type:
                    update_fields["factor_type"] = factor_type
                    needs_update = True

                if needs_update:
                    self.update(filename, **update_fields)
                    stats["updated"] += 1
                else:
                    stats["unchanged"] += 1

    def get_time_series_factors(self) -> List[Factor]:
        """获取所有时序因子"""
        return self.query({'factor_type': FactorType.TIME_SERIES})

    def get_cross_section_factors(self) -> List[Factor]:
        """获取所有截面因子"""
        return self.query({'factor_type': FactorType.CROSS_SECTION})

    # ==================== 导出功能 ====================

    def export_to_markdown(self, output_path: Optional[str] = None) -> str:
        """导出为 Markdown 表格"""
        factors = self.get_all()

        lines = [
            "# 因子目录",
            "",
            "| 文件名 | 因子风格 | 核心公式 | 输入数据 | 值域 | 刻画特征 | 因子分析 | 代码 | 大模型评分 | 已验证 | 验证备注 |",
            "|--------|----------|----------|----------|------|----------|----------|------|------------|--------|----------|",
        ]

        for f in factors:
            def escape(s):
                if not s:
                    return ''
                return str(s).replace('|', '\\|').replace('\n', ' ')

            score = f'{f.llm_score:.1f}' if f.llm_score is not None else ''
            verified = 'v' if f.verified else ''

            line = f"| {escape(f.filename)} | {escape(f.style)} | {escape(f.formula)} | {escape(f.input_data)} | {escape(f.value_range)} | {escape(f.description)} | {escape(f.analysis)} | {escape(f.code_path)} | {score} | {verified} | {escape(f.verify_note)} |"
            lines.append(line)

        content = '\n'.join(lines) + '\n'

        if output_path:
            Path(output_path).write_text(content, encoding='utf-8')

        return content


# ==================== 单例管理 ====================

def get_factor_store(database_url: Optional[str] = None) -> FactorStore:
    """获取因子存储层单例"""
    return get_store_instance(FactorStore, "FactorStore", database_url=database_url)


def reset_factor_store():
    """重置存储层单例（用于测试）"""
    reset_store_instance("FactorStore")
