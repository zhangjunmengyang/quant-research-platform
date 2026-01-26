"""
笔记同步服务

将笔记在数据库和 Markdown 文件之间同步。
使用 Markdown + YAML Front Matter 格式存储。
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseSyncService

logger = logging.getLogger(__name__)


class NoteSyncService(BaseSyncService):
    """
    笔记同步服务

    文件结构：
        private-data/notes/{note_type}/{id}_{slug}.md

    Markdown 格式：
        ---
        id: 123
        title: 标题
        note_type: observation
        tags: tag1,tag2
        source: factor
        source_ref: Momentum_5d
        research_session_id: "session_001"
        is_archived: false
        promoted_to_experience_id: null
        created_at: "2024-01-15T10:00:00"
        updated_at: "2024-01-15T10:30:00"
        ---

        笔记内容...
    """

    # 笔记类型到目录的映射
    TYPE_DIRS = {
        'observation': 'observations',
        'hypothesis': 'hypotheses',
        'finding': 'findings',
        'trail': 'trails',
        'general': 'general',
    }

    def __init__(self, data_dir: Path, store: Any = None):
        """
        初始化笔记同步服务

        Args:
            data_dir: 私有数据目录 (private-data/)
            store: NoteStore 实例
        """
        super().__init__(data_dir, store)
        self.notes_dir = data_dir / "notes"

    def export_all(self, overwrite: bool = False) -> Dict[str, int]:
        """
        导出所有笔记到 Markdown 文件

        Args:
            overwrite: 是否覆盖已存在的文件

        Returns:
            {"exported": N, "skipped": M, "errors": K}
        """
        stats = {"exported": 0, "skipped": 0, "errors": 0}

        if self.store is None:
            logger.warning("note_sync_export_skipped: store is None")
            return stats

        try:
            notes = self.store.get_all(limit=10000)
        except Exception as e:
            logger.error(f"note_sync_export_error: {e}")
            stats["errors"] = 1
            return stats

        # 确保所有类型目录存在
        for type_dir in self.TYPE_DIRS.values():
            self.ensure_dir(self.notes_dir / type_dir)

        for note in notes:
            try:
                filepath = self._get_note_filepath(note)

                # 检查是否需要更新
                if filepath.exists() and not overwrite:
                    file_mtime = self.get_file_mtime(filepath)
                    db_mtime = self.get_db_mtime(note)
                    if not self.should_update_file(file_mtime, db_mtime):
                        stats["skipped"] += 1
                        continue

                # 转换为 Markdown
                metadata, content = self._note_to_markdown(note)
                self.write_markdown_with_frontmatter(filepath, metadata, content)
                stats["exported"] += 1

            except Exception as e:
                logger.error(f"note_export_error: {note.id}, {e}")
                stats["errors"] += 1

        logger.info(f"notes_exported: {stats}")
        return stats

    def import_all(self) -> Dict[str, int]:
        """
        从 Markdown 文件导入笔记

        Returns:
            {"created": N, "updated": M, "unchanged": K, "errors": L}
        """
        stats = {"created": 0, "updated": 0, "unchanged": 0, "errors": 0}

        if self.store is None:
            logger.warning("note_sync_import_skipped: store is None")
            return stats

        if not self.notes_dir.exists():
            logger.info("note_sync_import_skipped: notes_dir not exists")
            return stats

        # 遍历所有类型目录
        for type_dir in self.TYPE_DIRS.values():
            dir_path = self.notes_dir / type_dir
            if not dir_path.exists():
                continue

            for md_file in dir_path.glob("*.md"):
                try:
                    result = self._import_note_file(md_file)
                    stats[result] += 1
                except Exception as e:
                    logger.error(f"note_import_error: {md_file}, {e}")
                    stats["errors"] += 1

        logger.info(f"notes_imported: {stats}")
        return stats

    def _get_note_filepath(self, note: Any) -> Path:
        """获取笔记的文件路径"""
        note_type = getattr(note, 'note_type', 'general')
        type_dir = self.TYPE_DIRS.get(note_type, 'general')

        # 生成文件名：{id}_{slug}.md
        note_id = note.id or 0
        slug = self._title_to_slug(note.title)
        filename = f"{note_id:04d}_{slug}.md"

        return self.notes_dir / type_dir / filename

    def _title_to_slug(self, title: str) -> str:
        """将标题转换为 URL 友好的 slug"""
        if not title:
            return "untitled"

        # 移除特殊字符，保留中文、字母、数字
        slug = re.sub(r'[^\w\u4e00-\u9fff]+', '_', title)
        slug = slug.strip('_')

        # 限制长度
        if len(slug) > 50:
            slug = slug[:50].rstrip('_')

        return slug or "untitled"

    def _note_to_markdown(self, note: Any) -> tuple[Dict[str, Any], str]:
        """将笔记对象转换为 Markdown 格式"""
        metadata = {
            'id': note.id,
            'title': note.title,
            'note_type': note.note_type,
            'tags': note.tags,
            'source': note.source,
            'source_ref': note.source_ref,
            'research_session_id': note.research_session_id,
            'is_archived': note.is_archived,
            'promoted_to_experience_id': note.promoted_to_experience_id,
            'created_at': self.datetime_to_iso(note.created_at),
            'updated_at': self.datetime_to_iso(note.updated_at),
        }

        # 移除 None 值
        metadata = {k: v for k, v in metadata.items() if v is not None}

        content = note.content or ""

        return metadata, content

    def _import_note_file(self, filepath: Path) -> str:
        """
        导入单个笔记文件

        Returns:
            "created", "updated", "unchanged", 或 "errors"
        """
        metadata, content = self.read_markdown_with_frontmatter(filepath)

        if not metadata:
            return "errors"

        note_id = metadata.get('id')

        # 准备笔记数据
        note_data = {
            'title': metadata.get('title', ''),
            'content': content,
            'tags': metadata.get('tags', ''),
            'source': metadata.get('source', ''),
            'source_ref': metadata.get('source_ref', ''),
            'note_type': metadata.get('note_type', 'general'),
            'research_session_id': metadata.get('research_session_id'),
            'is_archived': metadata.get('is_archived', False),
            'promoted_to_experience_id': metadata.get('promoted_to_experience_id'),
        }

        if note_id:
            # 尝试更新现有笔记
            existing = self.store.get(note_id)
            if existing:
                file_mtime = self.get_file_mtime(filepath)
                db_mtime = self.get_db_mtime(existing)

                if self.should_update_db(file_mtime, db_mtime):
                    self.store.update(note_id, **note_data)
                    return "updated"
                else:
                    return "unchanged"

        # 创建新笔记
        from domains.note_hub.core.models import Note
        note = Note.from_dict(note_data)
        self.store.add(note)
        return "created"

    def get_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        status = {
            "db_count": 0,
            "file_count": 0,
            "by_type": {},
        }

        if self.store is None:
            return status

        try:
            notes = self.store.get_all(limit=10000)
            status["db_count"] = len(notes)
        except Exception:
            return status

        if self.notes_dir.exists():
            for type_name, type_dir in self.TYPE_DIRS.items():
                dir_path = self.notes_dir / type_dir
                if dir_path.exists():
                    count = len(list(dir_path.glob("*.md")))
                    status["by_type"][type_name] = count
                    status["file_count"] += count

        return status
