"""
经验服务层

提供经验的业务逻辑封装，包括:
- 存储和查询
- 语义检索
- 验证和废弃
- 提炼和关联
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..core.config import get_experience_hub_settings
from ..core.models import (
    Experience,
    ExperienceContent,
    ExperienceContext,
    ExperienceLink,
    ExperienceLevel,
    ExperienceStatus,
    SourceType,
    EntityType,
)
from ..core.store import ExperienceStore, get_experience_store

logger = logging.getLogger(__name__)


class ExperienceService:
    """
    经验服务层

    封装经验相关的业务逻辑，代理存储层操作。
    """

    def __init__(self, store: Optional[ExperienceStore] = None):
        """
        初始化服务

        Args:
            store: 经验存储层实例
        """
        self._store = store
        self._settings = get_experience_hub_settings()

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
        experience_level: str,
        category: str,
        content: Dict[str, str],
        context: Optional[Dict[str, Any]] = None,
        source_type: str = "manual",
        source_ref: str = "",
        confidence: Optional[float] = None,
    ) -> Tuple[bool, str, Optional[int]]:
        """
        存储新经验

        Args:
            title: 经验标题
            experience_level: 经验层级（strategic/tactical/operational）
            category: 分类
            content: PARL 内容 {problem, approach, result, lesson}
            context: 上下文信息 {market_regime, factor_styles, time_horizon, asset_class, tags}
            source_type: 来源类型
            source_ref: 来源引用
            confidence: 初始置信度

        Returns:
            (成功, 消息, 经验ID)
        """
        if not title.strip():
            return False, "标题不能为空", None

        # 验证层级
        if experience_level not in [e.value for e in ExperienceLevel]:
            return False, f"无效的经验层级: {experience_level}", None

        # 构建经验对象
        exp_content = ExperienceContent(
            problem=content.get('problem', ''),
            approach=content.get('approach', ''),
            result=content.get('result', ''),
            lesson=content.get('lesson', ''),
        )

        exp_context = ExperienceContext()
        if context:
            exp_context = ExperienceContext(
                market_regime=context.get('market_regime', ''),
                factor_styles=context.get('factor_styles', []),
                time_horizon=context.get('time_horizon', ''),
                asset_class=context.get('asset_class', ''),
                tags=context.get('tags', []),
            )

        experience = Experience(
            title=title.strip(),
            experience_level=experience_level,
            category=category,
            content=exp_content,
            context=exp_context,
            source_type=source_type,
            source_ref=source_ref,
            confidence=confidence if confidence is not None else self._settings.default_confidence,
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
        experience_level: str = "",
        category: str = "",
        status: str = "",
        source_type: str = "",
        market_regime: str = "",
        factor_styles: Optional[List[str]] = None,
        min_confidence: float = 0.0,
        include_deprecated: bool = False,
        order_by: str = "updated_at",
        order_desc: bool = True,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Experience], int]:
        """
        查询经验列表

        Returns:
            (经验列表, 总数)
        """
        sort_direction = "DESC" if order_desc else "ASC"
        order_by_str = f"{order_by} {sort_direction}"

        offset = (page - 1) * page_size

        return self.store.query(
            experience_level=experience_level if experience_level else None,
            category=category if category else None,
            status=status if status else None,
            source_type=source_type if source_type else None,
            market_regime=market_regime if market_regime else None,
            factor_styles=factor_styles,
            min_confidence=min_confidence,
            include_deprecated=include_deprecated,
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
        experience_level: Optional[str] = None,
        category: Optional[str] = None,
        market_regime: Optional[str] = None,
        factor_styles: Optional[List[str]] = None,
        min_confidence: float = 0.0,
        include_deprecated: bool = False,
        top_k: int = 5,
    ) -> List[Experience]:
        """
        语义检索经验

        优先使用向量检索，如果向量检索不可用则降级为关键词搜索。

        Args:
            query: 自然语言查询
            experience_level: 过滤层级
            category: 过滤分类
            market_regime: 过滤市场环境
            factor_styles: 过滤因子风格
            min_confidence: 最低置信度
            include_deprecated: 是否包含已废弃经验
            top_k: 返回数量

        Returns:
            匹配的经验列表，按相关性排序
        """
        # TODO: 实现向量检索
        # 当前降级为关键词搜索
        experiences, _ = self.store.query(
            search=query,
            experience_level=experience_level,
            category=category,
            market_regime=market_regime,
            factor_styles=factor_styles,
            min_confidence=min_confidence,
            include_deprecated=include_deprecated,
            limit=top_k
        )
        return experiences

    # ==================== 验证和废弃 ====================

    def validate_experience(
        self,
        experience_id: int,
        validation_note: Optional[str] = None,
        confidence_delta: Optional[float] = None,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        验证/增强经验

        当后续研究证实了某条经验时调用，会：
        1. 增加 validation_count
        2. 更新 last_validated
        3. 提升 confidence（不超过 1.0）
        4. 如果是 draft 状态，更新为 validated

        Args:
            experience_id: 经验 ID
            validation_note: 验证说明（可选，用于记录）
            confidence_delta: 置信度增量

        Returns:
            (成功, 消息, {experience_id, new_confidence, validation_count})
        """
        experience = self.store.get(experience_id)
        if experience is None:
            return False, f"经验不存在: {experience_id}", None

        if experience.is_deprecated:
            return False, "已废弃的经验无法验证", None

        delta = confidence_delta if confidence_delta is not None else self._settings.confidence_delta_on_validate
        updated = self.store.validate(experience_id, delta)

        if updated:
            logger.info(f"验证经验成功: {experience_id}, 置信度: {updated.confidence}")
            return True, "验证成功", {
                "experience_id": experience_id,
                "new_confidence": updated.confidence,
                "validation_count": updated.validation_count,
            }
        else:
            return False, "验证失败", None

    def deprecate_experience(
        self,
        experience_id: int,
        reason: str,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        废弃经验

        当经验被证伪或已过时时调用，会：
        1. 将 status 更新为 deprecated
        2. 记录废弃原因
        3. 保留历史记录但降低检索权重

        Args:
            experience_id: 经验 ID
            reason: 废弃原因

        Returns:
            (成功, 消息, {experience_id, status})
        """
        if not reason.strip():
            return False, "废弃原因不能为空", None

        experience = self.store.get(experience_id)
        if experience is None:
            return False, f"经验不存在: {experience_id}", None

        if experience.is_deprecated:
            return False, "经验已经是废弃状态", None

        updated = self.store.deprecate(experience_id, reason)

        if updated:
            logger.info(f"废弃经验成功: {experience_id}, 原因: {reason}")
            return True, "废弃成功", {
                "experience_id": experience_id,
                "status": ExperienceStatus.DEPRECATED.value,
            }
        else:
            return False, "废弃失败", None

    # ==================== 提炼经验 ====================

    def curate_experience(
        self,
        source_experience_ids: List[int],
        target_level: str,
        title: str,
        content: Dict[str, str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[int]]:
        """
        从低层经验提炼高层经验

        例如：
        - 从多个 operational 经验总结为一个 tactical 结论
        - 从多个 tactical 结论抽象为一个 strategic 原则

        Args:
            source_experience_ids: 源经验 ID 列表
            target_level: 目标层级（必须高于源经验）
            title: 新经验标题
            content: PARL 内容
            context: 上下文

        Returns:
            (成功, 消息, 新经验ID)
        """
        if len(source_experience_ids) < 2:
            return False, "至少需要两个源经验", None

        # 验证源经验存在
        source_experiences = []
        for exp_id in source_experience_ids:
            exp = self.store.get(exp_id)
            if exp is None:
                return False, f"源经验不存在: {exp_id}", None
            source_experiences.append(exp)

        # 验证层级关系
        for exp in source_experiences:
            if not self._settings.can_curate_to_level(exp.experience_level, target_level):
                return False, f"无法从 {exp.experience_level} 提炼到 {target_level}", None

        # 确定分类（根据目标层级选择合适的分类）
        category = self._determine_category_for_level(target_level)

        # 创建新经验
        success, message, new_id = self.store_experience(
            title=title,
            experience_level=target_level,
            category=category,
            content=content,
            context=context,
            source_type=SourceType.CURATED.value,
            source_ref=",".join(str(id) for id in source_experience_ids),
            confidence=0.6,  # 提炼的经验初始置信度稍高
        )

        if not success or new_id is None:
            return False, message, None

        # 记录提炼来源
        for source_id in source_experience_ids:
            self._record_curation_source(new_id, source_id)

        # 关联源经验
        new_exp = self.store.get(new_id)
        if new_exp:
            for source_id in source_experience_ids:
                link = ExperienceLink(
                    experience_id=new_id,
                    experience_uuid=new_exp.uuid,
                    entity_type=EntityType.EXPERIENCE.value,
                    entity_id=str(source_id),
                    relation="curated_from",
                )
                self.store.add_link(link)

        logger.info(f"提炼经验成功: {title} (ID: {new_id}), 来源: {source_experience_ids}")
        return True, "提炼成功", new_id

    def _determine_category_for_level(self, level: str) -> str:
        """根据层级确定默认分类"""
        if level == ExperienceLevel.STRATEGIC.value:
            return "market_regime_principle"
        elif level == ExperienceLevel.TACTICAL.value:
            return "factor_performance"
        else:
            return "research_observation"

    def _record_curation_source(self, curated_id: int, source_id: int):
        """记录提炼来源关系"""
        try:
            with self.store._cursor() as cursor:
                cursor.execute('''
                    INSERT INTO experience_curation_sources (curated_experience_id, source_experience_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                ''', (curated_id, source_id))
        except Exception as e:
            logger.warning(f"记录提炼来源失败: {e}")

    # ==================== 关联管理 ====================

    def link_experience(
        self,
        experience_id: int,
        entity_type: str,
        entity_id: str,
        relation: str = "related",
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        关联经验与其他实体

        建立经验与因子、策略、笔记、研报的关联关系。

        Args:
            experience_id: 经验 ID
            entity_type: 实体类型（factor/strategy/note/research）
            entity_id: 实体 ID
            relation: 关系类型（related/derived_from/applied_to）

        Returns:
            (成功, 消息, {link_id, experience_id, entity_type, entity_id})
        """
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

        # 处理嵌套对象
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
        by_status = self.store.count_by_status()
        by_level = self.store.count_by_level()
        categories = self.store.get_categories()

        return {
            "total": total,
            "by_status": by_status,
            "by_level": by_level,
            "categories": categories,
            "categories_count": len(categories),
        }


# 单例实例
_experience_service: Optional[ExperienceService] = None


def get_experience_service() -> ExperienceService:
    """获取经验服务单例"""
    global _experience_service
    if _experience_service is None:
        _experience_service = ExperienceService()
    return _experience_service
