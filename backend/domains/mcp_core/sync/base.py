"""
同步服务基类

定义数据同步的通用接口和工具方法。
"""

import json
import logging
import os
import shutil
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

# Python 3.10 兼容性
UTC = timezone.utc
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class BaseSyncService(ABC):
    """
    数据同步服务基类

    提供文件系统与数据库之间的双向同步能力。
    子类需要实现具体的导入/导出逻辑。
    """

    def __init__(self, data_dir: Path, store: Any = None):
        """
        初始化同步服务

        Args:
            data_dir: 数据目录路径
            store: 数据存储实例
        """
        self.data_dir = data_dir
        self.store = store

    @abstractmethod
    def export_all(self, overwrite: bool = False) -> dict[str, int]:
        """
        导出所有数据到文件

        Args:
            overwrite: 是否覆盖已存在的文件

        Returns:
            统计信息 {"exported": N, "skipped": M, "errors": K}
        """
        pass

    @abstractmethod
    def import_all(self) -> dict[str, int]:
        """
        从文件导入所有数据

        Returns:
            统计信息 {"created": N, "updated": M, "unchanged": K, "errors": L}
        """
        pass

    def sync(self, direction: str = "file_to_db") -> dict[str, int]:
        """
        同步数据

        Args:
            direction: 同步方向
                - "file_to_db": 文件 -> 数据库
                - "db_to_file": 数据库 -> 文件
                - "bidirectional": 双向同步（基于时间戳）

        Returns:
            统计信息
        """
        if direction == "file_to_db":
            return self.import_all()
        elif direction == "db_to_file":
            return self.export_all(overwrite=True)
        elif direction == "bidirectional":
            # 双向同步：先导入再导出（文件优先）
            import_stats = self.import_all()
            export_stats = self.export_all(overwrite=False)
            return {
                "imported": import_stats,
                "exported": export_stats,
            }
        else:
            raise ValueError(f"Unknown sync direction: {direction}")

    # ===== 工具方法 =====

    def ensure_dir(self, path: Path) -> None:
        """确保目录存在"""
        path.mkdir(parents=True, exist_ok=True)

    def get_file_mtime(self, filepath: Path) -> datetime | None:
        """获取文件修改时间（UTC）"""
        if not filepath.exists():
            return None
        # 转换为 UTC 时区，确保时间比较一致性
        ts = filepath.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=UTC)

    def get_db_mtime(self, entity: Any) -> datetime | None:
        """获取数据库记录更新时间（UTC）"""
        if hasattr(entity, 'updated_at'):
            mtime = entity.updated_at
            if isinstance(mtime, datetime):
                # 如果没有时区信息，假设是本地时间，转换为 UTC
                if mtime.tzinfo is None:
                    # 数据库存储的时间通常是本地时间
                    return mtime.replace(tzinfo=UTC)
                return mtime.astimezone(UTC)
            if isinstance(mtime, str):
                try:
                    dt = datetime.fromisoformat(mtime.replace('Z', '+00:00'))
                    return dt.astimezone(UTC)
                except (ValueError, AttributeError):
                    pass
        return None

    def should_update_db(self, file_mtime: datetime | None, db_mtime: datetime | None) -> bool:
        """
        判断是否应该更新数据库

        文件更新时间 > 数据库更新时间 时，更新数据库
        添加 1 秒容差，避免时间精度问题导致的误判
        """
        if file_mtime is None:
            return False
        if db_mtime is None:
            return True
        # 添加 1 秒容差
        return file_mtime > db_mtime + timedelta(seconds=1)

    def should_update_file(self, file_mtime: datetime | None, db_mtime: datetime | None) -> bool:
        """
        判断是否应该更新文件

        数据库更新时间 > 文件更新时间 时，更新文件
        添加 1 秒容差，避免时间精度问题导致的误判
        """
        if db_mtime is None:
            return False
        if file_mtime is None:
            return True
        # 添加 1 秒容差
        return db_mtime > file_mtime + timedelta(seconds=1)

    # ===== YAML 工具 =====

    def read_yaml(self, filepath: Path) -> dict[str, Any]:
        """读取 YAML 文件"""
        with open(filepath, encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def write_yaml(self, filepath: Path, data: dict[str, Any]) -> None:
        """写入 YAML 文件"""
        self.ensure_dir(filepath.parent)
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

    # ===== JSON 工具 =====

    def read_json(self, filepath: Path) -> Any:
        """读取 JSON 文件"""
        with open(filepath, encoding='utf-8') as f:
            return json.load(f)

    def write_json(self, filepath: Path, data: Any) -> None:
        """写入 JSON 文件"""
        self.ensure_dir(filepath.parent)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ===== Markdown 工具 =====

    def read_markdown_with_frontmatter(self, filepath: Path) -> tuple[dict[str, Any], str]:
        """
        读取带 YAML Front Matter 的 Markdown 文件

        Returns:
            (metadata, content) 元组
        """
        with open(filepath, encoding='utf-8') as f:
            text = f.read()

        if not text.startswith('---'):
            return {}, text

        # 查找第二个 ---
        end_idx = text.find('---', 3)
        if end_idx == -1:
            return {}, text

        frontmatter = text[3:end_idx].strip()
        content = text[end_idx + 3:].strip()

        try:
            metadata = yaml.safe_load(frontmatter) or {}
        except yaml.YAMLError:
            metadata = {}

        return metadata, content

    def write_markdown_with_frontmatter(
        self,
        filepath: Path,
        metadata: dict[str, Any],
        content: str
    ) -> None:
        """
        写入带 YAML Front Matter 的 Markdown 文件
        """
        self.ensure_dir(filepath.parent)

        frontmatter = yaml.dump(
            metadata,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('---\n')
            f.write(frontmatter)
            f.write('---\n\n')
            f.write(content)

    # ===== 时间戳工具 =====

    def datetime_to_iso(self, dt: datetime | None) -> str | None:
        """datetime 转 ISO 格式字符串"""
        if dt is None:
            return None
        return dt.isoformat()

    def iso_to_datetime(self, iso_str: str | None) -> datetime | None:
        """ISO 格式字符串转 datetime"""
        if not iso_str:
            return None
        try:
            return datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None

    # ===== JSON 字段处理 =====

    def parse_json_field(self, value: str | None) -> Any:
        """解析 JSON 字段"""
        if not value:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    def serialize_json_field(self, value: Any) -> str | None:
        """序列化为 JSON 字段"""
        if value is None:
            return None
        if isinstance(value, str):
            # 已经是字符串，检查是否是有效 JSON
            try:
                json.loads(value)
                return value
            except json.JSONDecodeError:
                return json.dumps(value, ensure_ascii=False)
        return json.dumps(value, ensure_ascii=False)

    # ===== 原子写入工具 =====

    def write_yaml_atomic(self, filepath: Path, data: dict[str, Any]) -> None:
        """
        原子写入 YAML 文件

        使用临时文件 + 原子重命名，确保写入过程中断不会损坏文件。
        """
        self.ensure_dir(filepath.parent)

        # 写入临时文件
        fd, tmp_path = tempfile.mkstemp(
            suffix='.yaml',
            prefix='.tmp_',
            dir=filepath.parent
        )
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                yaml.dump(
                    data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
            # 原子重命名
            shutil.move(tmp_path, filepath)
        except Exception:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def write_markdown_with_frontmatter_atomic(
        self,
        filepath: Path,
        metadata: dict[str, Any],
        content: str
    ) -> None:
        """
        原子写入 Markdown 文件

        使用临时文件 + 原子重命名，确保写入过程中断不会损坏文件。
        """
        self.ensure_dir(filepath.parent)

        fd, tmp_path = tempfile.mkstemp(
            suffix='.md',
            prefix='.tmp_',
            dir=filepath.parent
        )
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write('---\n')
                yaml.dump(
                    metadata,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
                f.write('---\n\n')
                f.write(content)
            shutil.move(tmp_path, filepath)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def write_json_atomic(self, filepath: Path, data: Any) -> None:
        """
        原子写入 JSON 文件

        使用临时文件 + 原子重命名，确保写入过程中断不会损坏文件。
        """
        self.ensure_dir(filepath.parent)

        fd, tmp_path = tempfile.mkstemp(
            suffix='.json',
            prefix='.tmp_',
            dir=filepath.parent
        )
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            shutil.move(tmp_path, filepath)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
