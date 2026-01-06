"""
笔记服务层

提供笔记的业务逻辑封装。
"""

import logging
from typing import Optional, List, Tuple, Dict, Any

from ..core.models import Note
from ..core.store import NoteStore, get_note_store

logger = logging.getLogger(__name__)


class NoteService:
    """
    笔记服务层

    封装笔记相关的业务逻辑，代理存储层操作。
    """

    def __init__(self, store: Optional[NoteStore] = None):
        """
        初始化服务

        Args:
            store: 笔记存储层实例
        """
        self._store = store

    @property
    def store(self) -> NoteStore:
        """延迟获取存储层"""
        if self._store is None:
            self._store = get_note_store()
        return self._store

    # ==================== CRUD ====================

    def get_note(self, note_id: int) -> Optional[Note]:
        """获取笔记详情"""
        return self.store.get(note_id)

    def create_note(
        self,
        title: str,
        content: str,
        tags: str = "",
        source: str = "",
        source_ref: str = ""
    ) -> Tuple[bool, str, Optional[int]]:
        """
        创建笔记

        Returns:
            (成功, 消息, 笔记ID)
        """
        if not title.strip():
            return False, "标题不能为空", None

        note = Note(
            title=title.strip(),
            content=content,
            tags=tags,
            source=source,
            source_ref=source_ref,
        )

        note_id = self.store.add(note)
        if note_id:
            logger.info(f"创建笔记成功: {title} (ID: {note_id})")
            return True, f"创建成功", note_id
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
        tags: Optional[List[str]] = None,
        source: str = "",
        order_by: str = "updated_at",
        order_desc: bool = True,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Note], int]:
        """
        查询笔记列表

        Returns:
            (笔记列表, 总数)
        """
        sort_direction = "DESC" if order_desc else "ASC"
        order_by_str = f"{order_by} {sort_direction}"

        offset = (page - 1) * page_size

        return self.store.query(
            search=search if search else None,
            tags=tags,
            source=source if source else None,
            order_by=order_by_str,
            limit=page_size,
            offset=offset
        )

    def search_notes(self, keyword: str, limit: int = 20) -> List[Note]:
        """搜索笔记"""
        return self.store.search(keyword, limit)

    def get_notes_by_source(self, source: str, source_ref: str) -> List[Note]:
        """根据来源获取笔记"""
        return self.store.get_by_source(source, source_ref)

    def get_tags(self) -> List[str]:
        """获取所有标签"""
        return self.store.get_tags()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self.store.count()
        tags = self.store.get_tags()

        return {
            "total": total,
            "tags_count": len(tags),
            "tags": tags,
        }


# 单例实例
_note_service: Optional[NoteService] = None


def get_note_service() -> NoteService:
    """获取笔记服务单例"""
    global _note_service
    if _note_service is None:
        _note_service = NoteService()
    return _note_service
