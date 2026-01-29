"""
笔记服务层

提供笔记的业务逻辑封装。

Note Hub 定位为"研究草稿/临时记录"层，支持：
- 研究流程：观察 -> 假设 -> 检验
- 归档管理
- 提炼为经验（需要 experience_hub 支持）
- 知识边关联：通过 Graph Hub (Neo4j) 管理实体间关系
"""

import logging
from typing import Any

from domains.graph_hub.core import (
    GraphEdge,
    GraphStore,
    NodeType,
    RelationType,
    get_graph_store,
)

from ..core.models import Note, NoteType
from ..core.store import NoteStore, get_note_store

logger = logging.getLogger(__name__)


class NoteService:
    """
    笔记服务层

    封装笔记相关的业务逻辑，代理存储层操作。
    """

    def __init__(
        self,
        store: NoteStore | None = None,
        graph_store: GraphStore | None = None,
    ):
        """
        初始化服务

        Args:
            store: 笔记存储层实例
            graph_store: 图存储层实例 (Neo4j)
        """
        self._store = store
        self._graph_store = graph_store

    @property
    def store(self) -> NoteStore:
        """延迟获取存储层"""
        if self._store is None:
            self._store = get_note_store()
        return self._store

    @property
    def graph_store(self) -> GraphStore:
        """延迟获取图存储层"""
        if self._graph_store is None:
            self._graph_store = get_graph_store()
        return self._graph_store

    # ==================== CRUD ====================

    def get_note(self, note_id: int) -> Note | None:
        """获取笔记详情"""
        return self.store.get(note_id)

    def create_note(
        self,
        title: str,
        content: str,
        tags: str = "",
        note_type: str = NoteType.OBSERVATION.value,
    ) -> tuple[bool, str, int | None]:
        """
        创建笔记

        Args:
            title: 标题
            content: 内容
            tags: 标签（逗号分隔）
            note_type: 笔记类型

        Returns:
            (成功, 消息, 笔记ID)

        Note:
            创建笔记后，可使用 link_note() 建立与其他实体的关联。
            例如检验关联假设：link_note(note_id, "note", str(hypothesis_id), "relates", subtype="validates")
        """
        if not title.strip():
            return False, "标题不能为空", None

        note = Note(
            title=title.strip(),
            content=content,
            tags=tags,
            note_type=note_type,
        )

        note_id = self.store.add(note)
        if note_id:
            logger.info(f"创建笔记成功: {title} (ID: {note_id}, 类型: {note_type})")
            return True, "创建成功", note_id
        else:
            return False, "创建失败", None

    def update_note(self, note_id: int, **fields) -> bool:
        """更新笔记字段"""
        # 验证笔记存在
        note = self.store.get(note_id)
        if note is None:
            return False

        return self.store.update(note_id, **fields)

    def delete_note(self, note_id: int) -> bool:
        """删除笔记"""
        return self.store.delete(note_id)

    # ==================== 查询 ====================

    def list_notes(
        self,
        search: str = "",
        tags: list[str] | None = None,
        note_type: str = "",
        is_archived: bool | None = None,
        order_by: str = "updated_at",
        order_desc: bool = True,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[Note], int]:
        """
        查询笔记列表

        Args:
            search: 搜索关键词
            tags: 标签筛选
            note_type: 笔记类型筛选
            is_archived: 归档状态筛选
            order_by: 排序字段
            order_desc: 是否降序
            page: 页码
            page_size: 每页数量

        Returns:
            (笔记列表, 总数)
        """
        sort_direction = "DESC" if order_desc else "ASC"
        order_by_str = f"{order_by} {sort_direction}"

        offset = (page - 1) * page_size

        return self.store.query(
            search=search if search else None,
            tags=tags,
            note_type=note_type if note_type else None,
            is_archived=is_archived,
            order_by=order_by_str,
            limit=page_size,
            offset=offset
        )

    def search_notes(self, keyword: str, limit: int = 20) -> list[Note]:
        """搜索笔记"""
        return self.store.search(keyword, limit)

    def get_tags(self, include_archived: bool = False) -> list[str]:
        """获取所有标签

        Args:
            include_archived: 是否包含已归档笔记的标签，默认 False
        """
        return self.store.get_tags(include_archived=include_archived)

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        extended_stats = self.store.get_stats_extended()
        tags = self.store.get_tags()

        return {
            **extended_stats,
            "tags_count": len(tags),
            "tags": tags,
        }

    # ==================== 研究记录 ====================

    def record_observation(
        self,
        title: str,
        content: str,
        tags: str = "",
    ) -> tuple[bool, str, int | None]:
        """
        记录观察

        观察是对数据或现象的客观记录，是研究的起点。

        Args:
            title: 观察标题
            content: 观察内容
            tags: 标签

        Returns:
            (成功, 消息, 笔记ID)
        """
        return self.create_note(
            title=title,
            content=content,
            tags=tags,
            note_type=NoteType.OBSERVATION.value,
        )

    def record_hypothesis(
        self,
        title: str,
        content: str,
        tags: str = "",
    ) -> tuple[bool, str, int | None]:
        """
        记录假设

        假设是基于观察提出的待验证假说。

        Args:
            title: 假设标题
            content: 假设内容
            tags: 标签

        Returns:
            (成功, 消息, 笔记ID)
        """
        return self.create_note(
            title=title,
            content=content,
            tags=tags,
            note_type=NoteType.HYPOTHESIS.value,
        )

    def record_verification(
        self,
        title: str,
        content: str,
        tags: str = "",
        hypothesis_id: int | None = None,
    ) -> tuple[bool, str, int | None]:
        """
        记录检验

        检验是对假设的验证过程和结论。

        Args:
            title: 检验标题
            content: 检验内容
            tags: 标签
            hypothesis_id: 关联的假设笔记 ID（可选，通过 Graph Hub 关联）

        Returns:
            (成功, 消息, 笔记ID)
        """
        success, message, note_id = self.create_note(
            title=title,
            content=content,
            tags=tags,
            note_type=NoteType.VERIFICATION.value,
        )

        # 如果创建成功且指定了假设 ID，通过 Graph Hub 建立关联
        if success and note_id and hypothesis_id:
            self.link_note(
                note_id=note_id,
                target_type="note",
                target_id=str(hypothesis_id),
                relation="relates",
                subtype="validates",
            )

        return success, message, note_id

    # ==================== 类型查询 ====================

    def get_notes_by_type(
        self,
        note_type: str,
        limit: int = 50,
        include_archived: bool = False
    ) -> list[Note]:
        """
        按类型获取笔记

        Args:
            note_type: 笔记类型
            limit: 限制数量
            include_archived: 是否包含已归档的笔记

        Returns:
            笔记列表
        """
        return self.store.get_by_type(note_type, limit, include_archived)

    def get_verifications_for_hypothesis(
        self,
        hypothesis_id: int,
        include_archived: bool = False
    ) -> list[Note]:
        """
        获取假设的所有验证笔记

        通过 Graph Hub (Neo4j) 查找关联到指定假设的验证笔记。

        Args:
            hypothesis_id: 假设笔记 ID
            include_archived: 是否包含已归档的笔记

        Returns:
            验证笔记列表
        """
        # 通过 Graph Hub 查找 validates 关系
        edges = self.graph_store.get_edges_to_entity(
            entity_type=NodeType.NOTE,
            entity_id=str(hypothesis_id),
        )

        # 筛选 validates 子类型的笔记关联
        note_ids = [
            int(edge.source_id)
            for edge in edges
            if edge.source_type == NodeType.NOTE
            and edge.relation == RelationType.RELATES
            and edge.subtype == "validates"
        ]

        # 获取笔记详情
        notes = []
        for nid in note_ids:
            note = self.store.get(nid)
            if note and (include_archived or not note.is_archived):
                notes.append(note)

        return sorted(notes, key=lambda n: n.created_at or n.id)

    # ==================== 归档管理 ====================

    def archive_note(self, note_id: int) -> tuple[bool, str]:
        """
        归档笔记

        Args:
            note_id: 笔记 ID

        Returns:
            (成功, 消息)
        """
        note = self.store.get(note_id)
        if note is None:
            return False, f"笔记不存在: {note_id}"

        if note.is_archived:
            return False, "笔记已归档"

        success = self.store.archive(note_id)
        if success:
            logger.info(f"归档笔记: {note.title} (ID: {note_id})")
            return True, "归档成功"
        else:
            return False, "归档失败"

    def unarchive_note(self, note_id: int) -> tuple[bool, str]:
        """
        取消归档笔记

        Args:
            note_id: 笔记 ID

        Returns:
            (成功, 消息)
        """
        note = self.store.get(note_id)
        if note is None:
            return False, f"笔记不存在: {note_id}"

        if not note.is_archived:
            return False, "笔记未归档"

        success = self.store.unarchive(note_id)
        if success:
            logger.info(f"取消归档笔记: {note.title} (ID: {note_id})")
            return True, "取消归档成功"
        else:
            return False, "取消归档失败"

    # ==================== 提炼为经验 ====================

    def promote_to_experience(
        self,
        note_id: int,
        experience_id: int
    ) -> tuple[bool, str]:
        """
        标记笔记已提炼为经验

        注意：此方法仅标记笔记的提炼状态，实际创建经验需要调用 experience_hub。

        Args:
            note_id: 笔记 ID
            experience_id: 经验 ID

        Returns:
            (成功, 消息)
        """
        note = self.store.get(note_id)
        if note is None:
            return False, f"笔记不存在: {note_id}"

        if note.is_promoted:
            return False, f"笔记已提炼为经验: {note.promoted_to_experience_id}"

        success = self.store.set_promoted(note_id, experience_id)
        if success:
            logger.info(f"标记笔记已提炼为经验: {note.title} -> Experience {experience_id}")
            return True, "标记成功"
        else:
            return False, "标记失败"

    # ==================== 知识边关联 ====================

    def link_note(
        self,
        note_id: int,
        target_type: str,
        target_id: str,
        relation: str = "relates",
        subtype: str = "",
        is_bidirectional: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, str, int | None]:
        """
        创建笔记与其他实体的关联

        Args:
            note_id: 笔记 ID
            target_type: 目标实体类型（data/factor/strategy/note/research/experience）
            target_id: 目标实体 ID
            relation: 关系类型（derives/relates）
            subtype: 关系子类型（based/uses/refs/validates 等）
            is_bidirectional: 是否双向关联
            metadata: 扩展元数据

        Returns:
            (成功, 消息, 边ID) - 注意: Neo4j 不返回边ID，成功时返回 None
        """
        # 验证笔记存在
        note = self.store.get(note_id)
        if note is None:
            return False, f"笔记不存在: {note_id}", None

        # 验证实体类型
        try:
            target_node_type = NodeType(target_type)
        except ValueError:
            return False, f"无效的实体类型: {target_type}", None

        # 验证关系类型
        try:
            relation_type = RelationType(relation)
        except ValueError:
            return False, f"无效的关系类型: {relation}", None

        # 创建图边
        edge = GraphEdge(
            source_type=NodeType.NOTE,
            source_id=str(note_id),
            target_type=target_node_type,
            target_id=target_id,
            relation=relation_type,
            subtype=subtype,
            is_bidirectional=is_bidirectional,
            metadata=metadata or {},
        )

        success = self.graph_store.create_edge(edge)
        if success:
            logger.info(f"创建笔记关联: note:{note_id} -[{relation}]-> {target_type}:{target_id}")
            return True, "关联成功", None
        else:
            return False, "关联失败（可能已存在）", None

    def get_note_edges(
        self,
        note_id: int,
        include_bidirectional: bool = True,
    ) -> list[dict[str, Any]]:
        """
        获取笔记的所有关联

        Args:
            note_id: 笔记 ID
            include_bidirectional: 是否包含双向关联

        Returns:
            关联列表
        """
        edges = self.graph_store.get_edges_by_entity(
            entity_type=NodeType.NOTE,
            entity_id=str(note_id),
            include_bidirectional=include_bidirectional,
        )
        return [edge.to_dict() for edge in edges]

    def get_edges_to_note(self, note_id: int) -> list[dict[str, Any]]:
        """
        获取指向笔记的所有关联

        Args:
            note_id: 笔记 ID

        Returns:
            关联列表
        """
        edges = self.graph_store.get_edges_to_entity(
            entity_type=NodeType.NOTE,
            entity_id=str(note_id),
        )
        return [edge.to_dict() for edge in edges]

    def trace_note_lineage(
        self,
        note_id: int,
        direction: str = "backward",
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:
        """
        追溯笔记的知识链路

        Args:
            note_id: 笔记 ID
            direction: 追溯方向
                - "backward": 向上追溯源头（笔记引用了什么）
                - "forward": 向下追溯应用（笔记被什么引用）
            max_depth: 最大追溯深度

        Returns:
            链路列表，每项包含 depth 和 node 信息
        """
        result = self.graph_store.trace_lineage(
            entity_type=NodeType.NOTE,
            entity_id=str(note_id),
            direction=direction,
            max_depth=max_depth,
        )
        return [node.to_dict() for node in result.nodes]

    def delete_note_edge(
        self,
        note_id: int,
        target_type: str,
        target_id: str,
        relation: str,
    ) -> tuple[bool, str]:
        """
        删除笔记关联

        Args:
            note_id: 笔记 ID (源节点)
            target_type: 目标实体类型
            target_id: 目标实体 ID
            relation: 关系类型

        Returns:
            (成功, 消息)
        """
        # 验证实体类型
        try:
            target_node_type = NodeType(target_type)
        except ValueError:
            return False, f"无效的实体类型: {target_type}"

        # 验证关系类型
        try:
            relation_type = RelationType(relation)
        except ValueError:
            return False, f"无效的关系类型: {relation}"

        success = self.graph_store.delete_edge(
            source_type=NodeType.NOTE,
            source_id=str(note_id),
            target_type=target_node_type,
            target_id=target_id,
            relation=relation_type,
        )
        if success:
            logger.info(f"删除笔记关联: note:{note_id} -[{relation}]-> {target_type}:{target_id}")
            return True, "删除成功"
        else:
            return False, "删除失败"


# 单例实例
_note_service: NoteService | None = None


def get_note_service() -> NoteService:
    """获取笔记服务单例"""
    global _note_service
    if _note_service is None:
        _note_service = NoteService()
    return _note_service
