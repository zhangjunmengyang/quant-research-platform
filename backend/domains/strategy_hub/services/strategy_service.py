"""
策略业务服务层

提供策略管理的业务逻辑，包括查询、更新、验证等操作。
与 REST API 和 MCP 统一使用此服务层，遵循分层架构规范。
"""

from typing import List, Optional, Dict, Any, Tuple

from .strategy_store import StrategyStore, get_strategy_store
from .models import Strategy


class StrategyService:
    """
    策略业务服务

    封装存储层操作，提供业务逻辑处理。
    """

    def __init__(self, store: Optional[StrategyStore] = None):
        """
        初始化服务

        Args:
            store: 策略存储实例，默认使用单例
        """
        self.store = store or get_strategy_store()

    def list_strategies(
        self,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = "created_at",
        order_desc: bool = True,
        page: int = 1,
        page_size: int = 50,
        limit: Optional[int] = None,
    ) -> Tuple[List[Strategy], int]:
        """
        获取策略列表

        Args:
            filters: 过滤条件 (verified, task_status 等)
            order_by: 排序字段
            order_desc: 是否降序
            page: 页码
            page_size: 每页数量
            limit: 总数量限制（用于 MCP）

        Returns:
            (策略列表, 总数)
        """
        return self.store.list_all(
            filters=filters,
            order_by=order_by,
            order_desc=order_desc,
            page=page,
            page_size=page_size,
            limit=limit,
        )

    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """获取单个策略"""
        return self.store.get(strategy_id)

    def create_strategy(self, strategy: Strategy) -> Strategy:
        """创建策略"""
        return self.store.create(strategy)

    def create_strategy_from_dict(self, **kwargs) -> Strategy:
        """从字典创建策略"""
        strategy = Strategy.from_dict(kwargs)
        return self.store.create(strategy)

    def update_strategy(self, strategy: Strategy) -> Strategy:
        """更新策略"""
        return self.store.update(strategy)

    def update_strategy_fields(self, strategy_id: str, **fields) -> bool:
        """更新策略指定字段"""
        strategy = self.store.get(strategy_id)
        if not strategy:
            return False

        for key, value in fields.items():
            if hasattr(strategy, key):
                setattr(strategy, key, value)

        self.store.update(strategy)
        return True

    def delete_strategy(self, strategy_id: str) -> bool:
        """删除策略"""
        return self.store.delete(strategy_id)

    def search_strategies(self, query: str) -> List[Strategy]:
        """搜索策略"""
        return self.store.search(query)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.store.get_stats()

    def batch_delete(self, strategy_ids: List[str]) -> int:
        """批量删除"""
        success = 0
        for sid in strategy_ids:
            if self.store.delete(sid):
                success += 1
        return success


# 单例
_service: Optional[StrategyService] = None


def get_strategy_service() -> StrategyService:
    """获取服务单例"""
    global _service
    if _service is None:
        _service = StrategyService()
    return _service


def reset_strategy_service():
    """重置单例（用于测试）"""
    global _service
    _service = None
