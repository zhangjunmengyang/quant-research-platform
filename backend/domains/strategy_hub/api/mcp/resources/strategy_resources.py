"""
策略资源定义

提供 MCP Resources，用于向 LLM 提供只读数据上下文。
基于 mcp_core.BaseResourceProvider 实现。
"""

from typing import Any, Dict, List, Optional
import logging
import json

from domains.mcp_core import (
    BaseResourceProvider,
    ResourceDefinition,
    ResourceContent,
)

from domains.strategy_hub.services import get_strategy_store

logger = logging.getLogger(__name__)


class StrategyResourceProvider(BaseResourceProvider):
    """
    策略资源提供者

    管理所有可用的 MCP 资源，支持动态资源发现和模板资源。
    继承 mcp_core.BaseResourceProvider。
    """

    def __init__(self):
        super().__init__()
        self._register_strategy_resources()

    @property
    def store(self):
        """延迟获取 StrategyStore"""
        return get_strategy_store()

    def _register_strategy_resources(self):
        """注册策略相关的资源"""
        # 统计信息资源
        self.register_static(
            uri="strategy://stats",
            name="策略统计",
            description="策略库的整体统计信息",
            handler=self._read_stats,
        )

        # 策略列表资源
        self.register_static(
            uri="strategy://list",
            name="策略列表",
            description="所有策略的列表",
            handler=self._read_list,
        )

        # 动态资源模板 - 策略详情
        self.register_dynamic(
            pattern="strategy://strategy/{strategy_id}",
            name="策略详情",
            description="获取指定策略的详细信息，将 {strategy_id} 替换为实际策略ID",
            handler=self._read_strategy,
        )

    async def _read_stats(self) -> ResourceContent:
        """读取统计信息"""
        stats = self.store.get_stats()

        return ResourceContent(
            uri="strategy://stats",
            mime_type="application/json",
            text=json.dumps(stats, ensure_ascii=False, indent=2),
        )

    async def _read_list(self) -> ResourceContent:
        """读取策略列表"""
        strategies, _ = self.store.list_all(limit=100)

        data = {
            "count": len(strategies),
            "strategies": [
                {
                    "id": s.id,
                    "name": s.name,
                    "annual_return": s.annual_return,
                    "max_drawdown": s.max_drawdown,
                    "sharpe_ratio": s.sharpe_ratio,
                    "task_status": s.task_status,
                    "verified": s.verified,
                }
                for s in strategies
            ],
        }

        return ResourceContent(
            uri="strategy://list",
            mime_type="application/json",
            text=json.dumps(data, ensure_ascii=False, indent=2),
        )

    async def _read_strategy(self, strategy_id: str) -> Optional[ResourceContent]:
        """读取策略详情"""
        try:
            strategy = self.store.get(strategy_id)

            if strategy is None:
                return None

            return ResourceContent(
                uri=f"strategy://strategy/{strategy_id}",
                mime_type="application/json",
                text=json.dumps(strategy.to_dict(), ensure_ascii=False, indent=2),
            )

        except Exception as e:
            logger.error(f"读取策略失败: {e}")
            return None
