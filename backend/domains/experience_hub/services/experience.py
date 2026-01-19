"""
经验服务层

提供经验的业务逻辑封装，包括:
- 存储和查询
- 关联管理
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..core.models import (
    Experience,
    ExperienceContent,
    ExperienceContext,
    ExperienceLink,
    EntityType,
)
from ..core.store import ExperienceStore, get_experience_store

logger = logging.getLogger(__name__)


class ExperienceService:
    """经验服务层"""

    def __init__(self, store: Optional[ExperienceStore] = None):
        self._store = store

    @property
    def store(self) -> ExperienceStore:
        """延迟获取存储层"""
        if self._store is None:
            self._store = get_experience_store()
        return self._store

    # ==================== 存储经验 ====================

    def store_experience(
        self,
        title: str,
        content: Dict[str, str],
        context: Optional[Dict[str, Any]] = None,
        source_type: str = "manual",
        source_ref: str = "",
    ) -> Tuple[bool, str, Optional[int]]:
        """
        存储新经验

        Args:
            title: 经验标题
            content: PARL 内容 {problem, approach, result, lesson}
            context: 上下文信息 {tags, factor_styles, market_regime, time_horizon, asset_class}
            source_type: 来源类型
            source_ref: 来源引用

        Returns:
            (成功, 消息, 经验ID)
        """
        if not title.strip():
            return False, "标题不能为空", None

        exp_content = ExperienceContent(
            problem=content.get('problem', ''),
            approach=content.get('approach', ''),
            result=content.get('result', ''),
            lesson=content.get('lesson', ''),
        )

        exp_context = ExperienceContext()
        if context:
            exp_context = ExperienceContext(
                tags=context.get('tags', []),
                factor_styles=context.get('factor_styles', []),
                market_regime=context.get('market_regime', ''),
                time_horizon=context.get('time_horizon', ''),
                asset_class=context.get('asset_class', ''),
            )

        experience = Experience(
            title=title.strip(),
            content=exp_content,
            context=exp_context,
            source_type=source_type,
            source_ref=source_ref,
        )

        experience_id = self.store.add(experience)
        if experience_id:
            logger.info(f"存储经验成功: {title} (ID: {experience_id})")
            return True, "存储成功", experience_id
        else:
            return False, "存储失败", None

    # ==================== 查询经验 ====================

    def get_experience(self, experience_id: int) -> Optional[Experience]:
        """获取经验详情（通过 ID）"""
        return self.store.get(experience_id)

    def get_experience_by_uuid(self, uuid: str) -> Optional[Experience]:
        """获取经验详情（通过 UUID）"""
        return self.store.get_by_uuid(uuid)

    def list_experiences(
        self,
        tags: Optional[List[str]] = None,
        source_type: str = "",
        market_regime: str = "",
        factor_styles: Optional[List[str]] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        updated_after: Optional[datetime] = None,
        updated_before: Optional[datetime] = None,
        order_by: str = "updated_at",
        order_desc: bool = True,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Experience], int]:
        """查询经验列表"""
        sort_direction = "DESC" if order_desc else "ASC"
        order_by_str = f"{order_by} {sort_direction}"
        offset = (page - 1) * page_size

        return self.store.query(
            tags=tags,
            source_type=source_type if source_type else None,
            market_regime=market_regime if market_regime else None,
            factor_styles=factor_styles,
            created_after=created_after,
            created_before=created_before,
            updated_after=updated_after,
            updated_before=updated_before,
            order_by=order_by_str,
            limit=page_size,
            offset=offset
        )

    def search_experiences(self, keyword: str, limit: int = 20) -> List[Experience]:
        """搜索经验"""
        return self.store.search(keyword, limit)

    def query_experiences(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        market_regime: Optional[str] = None,
        factor_styles: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[Experience]:
        """语义检索经验（当前降级为关键词搜索）"""
        experiences, _ = self.store.query(
            search=query,
            tags=tags,
            market_regime=market_regime,
            factor_styles=factor_styles,
            limit=top_k
        )
        return experiences

    def get_all_tags(self) -> List[str]:
        """获取所有标签"""
        return self.store.get_all_tags()

    # ==================== 关联管理 ====================

    def link_experience(
        self,
        experience_id: int,
        entity_type: str,
        entity_id: str,
        relation: str = "related",
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """关联经验与其他实体"""
        experience = self.store.get(experience_id)
        if experience is None:
            return False, f"经验不存在: {experience_id}", None

        if entity_type not in [e.value for e in EntityType]:
            return False, f"无效的实体类型: {entity_type}", None

        link = ExperienceLink(
            experience_id=experience_id,
            experience_uuid=experience.uuid,
            entity_type=entity_type,
            entity_id=entity_id,
            relation=relation,
        )

        link_id = self.store.add_link(link)
        if link_id:
            logger.info(f"关联经验成功: {experience_id} -> {entity_type}:{entity_id}")
            return True, "关联成功", {
                "link_id": link_id,
                "experience_id": experience_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
            }
        else:
            return False, "关联失败", None

    def get_experience_links(self, experience_id: int) -> List[ExperienceLink]:
        """获取经验的所有关联"""
        return self.store.get_links(experience_id)

    def get_experiences_by_entity(
        self,
        entity_type: str,
        entity_id: str
    ) -> List[Experience]:
        """根据关联实体获取经验"""
        return self.store.get_experiences_by_entity(entity_type, entity_id)

    # ==================== 更新和删除 ====================

    def update_experience(self, experience_id: int, **fields) -> bool:
        """更新经验字段"""
        experience = self.store.get(experience_id)
        if experience is None:
            return False

        if 'content' in fields and isinstance(fields['content'], dict):
            fields['content'] = ExperienceContent.from_dict(fields['content'])
        if 'context' in fields and isinstance(fields['context'], dict):
            fields['context'] = ExperienceContext.from_dict(fields['context'])

        return self.store.update(experience_id, **fields)

    def delete_experience(self, experience_id: int) -> bool:
        """删除经验"""
        return self.store.delete(experience_id)

    # ==================== 统计 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self.store.count()
        tags = self.store.get_all_tags()

        return {
            "total": total,
            "tags": tags,
            "tags_count": len(tags),
        }


_experience_service: Optional[ExperienceService] = None


def get_experience_service() -> ExperienceService:
    """获取经验服务单例"""
    global _experience_service
    if _experience_service is None:
        _experience_service = ExperienceService()
    return _experience_service
