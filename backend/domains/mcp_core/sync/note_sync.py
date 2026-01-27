"""
笔记同步服务

将笔记在数据库和 Markdown 文件之间同步。
使用 Markdown + YAML Front Matter 格式存储。
"""

import logging
import re
import uuid as uuid_lib
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseSyncService

logger = logging.getLogger(__name__)


class NoteSyncService(BaseSyncService):
    """
    笔记同步服务

    文件结构：
        private-data/notes/{note_type}/{uuid}.md

    Markdown 格式：
        ---
        uuid: "550e8400-e29b-41d4-a716-446655440000"
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

    注意：使用 UUID 作为文件名，保证文件名稳定（标题变更不影响文件名）
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
                # 确保笔记有 UUID，如果没有则生成并更新数据库
                if not note.uuid:
                    note.uuid = str(uuid_lib.uuid4())
                    try:
                        self.store.update(note.id, uuid=note.uuid)
                        logger.info(f"generated_uuid_for_note: {note.id} -> {note.uuid}")
                    except Exception as e:
                        logger.warning(f"failed_to_persist_uuid: {note.id}, {e}")

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

                # 清理旧格式文件
                self._cleanup_old_files(note)

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
        """获取笔记的文件路径（基于 UUID）"""
        note_type = getattr(note, 'note_type', 'general')
        type_dir = self.TYPE_DIRS.get(note_type, 'general')

        # 使用 UUID 作为文件名，保证稳定性
        note_uuid = getattr(note, 'uuid', None)
        if not note_uuid:
            # 向后兼容：如果没有 UUID，使用旧格式
            note_id = note.id or 0
            slug = self._title_to_slug(note.title)
            filename = f"{note_id:04d}_{slug}.md"
        else:
            filename = f"{note_uuid}.md"

        return self.notes_dir / type_dir / filename

    def _title_to_slug(self, title: str) -> str:
        """将标题转换为 URL 友好的 slug（用于向后兼容）"""
        if not title:
            return "untitled"

        # 移除特殊字符，保留中文、字母、数字
        slug = re.sub(r'[^\w\u4e00-\u9fff]+', '_', title)
        slug = slug.strip('_')

        # 限制长度
        if len(slug) > 50:
            slug = slug[:50].rstrip('_')

        return slug or "untitled"

    def _cleanup_old_files(self, note: Any) -> None:
        """清理旧格式的文件（迁移期间使用）"""
        if not note.uuid:
            return

        note_type = getattr(note, 'note_type', 'general')
        type_dir = self.TYPE_DIRS.get(note_type, 'general')
        dir_path = self.notes_dir / type_dir

        if not dir_path.exists():
            return

        # 查找并删除旧格式文件 ({id}_{slug}.md)
        note_id = note.id or 0
        old_pattern = f"{note_id:04d}_*.md"
        for old_file in dir_path.glob(old_pattern):
            # 不是 UUID 格式的文件名才删除
            if old_file.stem != note.uuid:
                try:
                    old_file.unlink()
                    logger.info(f"cleaned_old_note_file: {old_file}")
                except Exception as e:
                    logger.warning(f"failed_to_clean_old_file: {old_file}, {e}")

    def _note_to_markdown(self, note: Any) -> tuple[Dict[str, Any], str]:
        """将笔记对象转换为 Markdown 格式"""
        metadata = {
            'uuid': note.uuid,  # UUID 放在最前面，作为主要标识
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

        优先使用 UUID 匹配，其次使用 ID 匹配。

        Returns:
            "created", "updated", "unchanged", 或 "errors"
        """
        metadata, content = self.read_markdown_with_frontmatter(filepath)

        if not metadata:
            return "errors"

        note_uuid = metadata.get('uuid')
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

        # 优先使用 UUID 匹配，其次使用 ID 匹配
        existing = None
        if note_uuid:
            existing = self.store.get_by_uuid(note_uuid)
        if not existing and note_id:
            existing = self.store.get(note_id)

        if existing:
            # 更新现有记录
            file_mtime = self.get_file_mtime(filepath)
            db_mtime = self.get_db_mtime(existing)

            if self.should_update_db(file_mtime, db_mtime):
                self.store.update(existing.id, **note_data)
                return "updated"
            else:
                return "unchanged"

        # 创建新笔记
        from domains.note_hub.core.models import Note

        # 确保有 UUID
        if not note_uuid:
            note_uuid = str(uuid_lib.uuid4())

        note_data['uuid'] = note_uuid
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

    def export_single(self, note_id: int) -> bool:
        """
        导出单个笔记

        Args:
            note_id: 笔记 ID

        Returns:
            是否成功
        """
        if self.store is None:
            return False

        try:
            note = self.store.get(note_id)
            if note is None:
                return False

            # 确保笔记有 UUID
            if not note.uuid:
                note.uuid = str(uuid_lib.uuid4())
                try:
                    self.store.update(note.id, uuid=note.uuid)
                except Exception as e:
                    logger.warning(f"failed_to_persist_uuid: {note.id}, {e}")

            # 确保目录存在
            note_type = getattr(note, 'note_type', 'general')
            type_dir = self.TYPE_DIRS.get(note_type, 'general')
            self.ensure_dir(self.notes_dir / type_dir)

            filepath = self._get_note_filepath(note)
            metadata, content = self._note_to_markdown(note)
            self.write_markdown_with_frontmatter_atomic(filepath, metadata, content)

            # 清理旧格式文件
            self._cleanup_old_files(note)

            return True

        except Exception as e:
            logger.error(f"note_export_single_error: {note_id}, {e}")
            return False

    def import_single(self, note_id: int) -> bool:
        """
        导入单个笔记（通过 ID）

        Args:
            note_id: 笔记 ID

        Returns:
            是否成功
        """
        if self.store is None:
            return False

        try:
            note = self.store.get(note_id)
            if note is None or not note.uuid:
                return False

            # 查找对应的文件
            note_type = getattr(note, 'note_type', 'general')
            type_dir = self.TYPE_DIRS.get(note_type, 'general')
            filepath = self.notes_dir / type_dir / f"{note.uuid}.md"

            if not filepath.exists():
                return False

            result = self._import_note_file(filepath)
            return result in ("created", "updated", "unchanged")

        except Exception as e:
            logger.error(f"note_import_single_error: {note_id}, {e}")
            return False

    def sync_deletions(self, archive_orphans: bool = True) -> Dict[str, int]:
        """
        同步删除操作

        检测孤儿文件（文件存在但数据库无记录）和孤儿记录（数据库有记录但文件不存在），
        根据策略进行处理。

        Args:
            archive_orphans: 是否归档孤儿文件（而不是删除）

        Returns:
            {"orphan_files_archived": N, "orphan_records_archived": M}
        """
        stats = {"orphan_files_archived": 0, "orphan_records_archived": 0}

        if self.store is None:
            return stats

        # 1. 获取数据库中所有笔记的 UUID 集合
        try:
            db_notes = self.store.get_all(limit=100000)
        except Exception as e:
            logger.error(f"sync_deletions_db_error: {e}")
            return stats

        db_uuids = {n.uuid for n in db_notes if getattr(n, 'uuid', None)}

        # 2. 获取文件系统中所有笔记文件的 UUID 集合
        file_uuids = set()
        file_map = {}  # uuid -> filepath

        for type_dir in self.TYPE_DIRS.values():
            dir_path = self.notes_dir / type_dir
            if dir_path.exists():
                for md_file in dir_path.glob("*.md"):
                    metadata, _ = self.read_markdown_with_frontmatter(md_file)
                    if metadata and metadata.get('uuid'):
                        file_uuid = metadata['uuid']
                        file_uuids.add(file_uuid)
                        file_map[file_uuid] = md_file

        # 3. 处理孤儿文件（文件存在但数据库无记录）
        orphan_file_uuids = file_uuids - db_uuids
        archive_dir = self.notes_dir / "_archived"

        for uuid in orphan_file_uuids:
            filepath = file_map[uuid]
            try:
                if archive_orphans:
                    self.ensure_dir(archive_dir)
                    archive_path = archive_dir / filepath.name
                    filepath.rename(archive_path)
                    logger.info(f"archived_orphan_file: {filepath} -> {archive_path}")
                else:
                    filepath.unlink()
                    logger.info(f"deleted_orphan_file: {filepath}")
                stats["orphan_files_archived"] += 1
            except Exception as e:
                logger.warning(f"failed_to_handle_orphan_file: {filepath}, {e}")

        # 4. 处理孤儿记录（数据库有记录但文件不存在）
        orphan_record_uuids = db_uuids - file_uuids
        for note in db_notes:
            note_uuid = getattr(note, 'uuid', None)
            if note_uuid and note_uuid in orphan_record_uuids:
                try:
                    # 标记为已归档而不是删除
                    self.store.archive(note.id)
                    logger.info(f"archived_orphan_record: {note.id} ({note_uuid})")
                    stats["orphan_records_archived"] += 1
                except Exception as e:
                    logger.warning(f"failed_to_archive_orphan_record: {note.id}, {e}")

        logger.info(f"sync_deletions_completed: {stats}")
        return stats
