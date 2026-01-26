"""
经验同步服务

将经验在数据库和 YAML 文件之间同步。
经验使用 PARL 框架（Problem-Approach-Result-Lesson）存储。
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseSyncService

logger = logging.getLogger(__name__)


class ExperienceSyncService(BaseSyncService):
    """
    经验同步服务

    文件结构：
        private-data/experiences/
            all/{uuid}.yaml              # 经验主体
            links.yaml                   # 关联关系

    YAML 格式：
        id: 1
        uuid: "550e8400-..."
        title: 标题

        content:
            problem: 问题
            approach: 方法
            result: 结果
            lesson: 教训

        context:
            tags: [tag1, tag2]
            factor_styles: [动量, 反转]
            market_regime: 震荡
            time_horizon: 中期
            asset_class: 全市场

        source_type: research
        source_ref: "session_001"
        created_at: "2024-01-15T10:00:00"
        updated_at: "2024-01-15T10:30:00"
    """

    def __init__(self, data_dir: Path, store: Any = None):
        """
        初始化经验同步服务

        Args:
            data_dir: 私有数据目录 (private-data/)
            store: ExperienceStore 实例
        """
        super().__init__(data_dir, store)
        self.experiences_dir = data_dir / "experiences" / "all"
        self.links_file = data_dir / "experiences" / "links.yaml"

    def export_all(self, overwrite: bool = False) -> Dict[str, int]:
        """
        导出所有经验

        Args:
            overwrite: 是否覆盖已存在的文件

        Returns:
            {"exported": N, "skipped": M, "errors": K}
        """
        stats = {"exported": 0, "skipped": 0, "errors": 0}

        if self.store is None:
            logger.warning("experience_sync_export_skipped: store is None")
            return stats

        try:
            # 获取所有经验（使用较大的 limit 获取全部）
            experiences = self.store.get_all(limit=10000)
        except Exception as e:
            logger.error(f"experience_sync_export_error: {e}")
            stats["errors"] = 1
            return stats

        self.ensure_dir(self.experiences_dir)

        # 导出经验
        for exp in experiences:
            try:
                filepath = self.experiences_dir / f"{exp.uuid}.yaml"

                # 检查是否需要更新
                if filepath.exists() and not overwrite:
                    file_mtime = self.get_file_mtime(filepath)
                    db_mtime = self.get_db_mtime(exp)
                    if not self.should_update_file(file_mtime, db_mtime):
                        stats["skipped"] += 1
                        continue

                # 转换为 YAML
                data = self._experience_to_yaml(exp)
                self.write_yaml(filepath, data)
                stats["exported"] += 1

            except Exception as e:
                logger.error(f"experience_export_error: {exp.uuid}, {e}")
                stats["errors"] += 1

        # 导出关联关系
        try:
            self._export_links()
        except Exception as e:
            logger.error(f"experience_links_export_error: {e}")

        logger.info(f"experiences_exported: {stats}")
        return stats

    def import_all(self) -> Dict[str, int]:
        """
        从文件导入经验

        Returns:
            {"created": N, "updated": M, "unchanged": K, "errors": L}
        """
        stats = {"created": 0, "updated": 0, "unchanged": 0, "errors": 0}

        if self.store is None:
            logger.warning("experience_sync_import_skipped: store is None")
            return stats

        if not self.experiences_dir.exists():
            logger.info("experience_sync_import_skipped: experiences_dir not exists")
            return stats

        for yaml_file in self.experiences_dir.glob("*.yaml"):
            try:
                result = self._import_experience_file(yaml_file)
                stats[result] += 1
            except Exception as e:
                logger.error(f"experience_import_error: {yaml_file}, {e}")
                stats["errors"] += 1

        # 导入关联关系
        try:
            self._import_links()
        except Exception as e:
            logger.error(f"experience_links_import_error: {e}")

        logger.info(f"experiences_imported: {stats}")
        return stats

    def _experience_to_yaml(self, exp: Any) -> Dict[str, Any]:
        """将经验对象转换为 YAML 数据"""
        data = {
            'id': exp.id,
            'uuid': exp.uuid,
            'title': exp.title,
        }

        # PARL 内容
        if hasattr(exp, 'content') and exp.content:
            if hasattr(exp.content, 'to_dict'):
                data['content'] = exp.content.to_dict()
            elif isinstance(exp.content, dict):
                data['content'] = exp.content
            else:
                # 尝试解析 JSON
                content = self.parse_json_field(str(exp.content))
                if content:
                    data['content'] = content

        # 上下文
        if hasattr(exp, 'context') and exp.context:
            if hasattr(exp.context, 'to_dict'):
                data['context'] = exp.context.to_dict()
            elif isinstance(exp.context, dict):
                data['context'] = exp.context
            else:
                context = self.parse_json_field(str(exp.context))
                if context:
                    data['context'] = context

        # 来源
        data['source_type'] = getattr(exp, 'source_type', 'manual')
        data['source_ref'] = getattr(exp, 'source_ref', '')

        # 时间戳
        data['created_at'] = self.datetime_to_iso(getattr(exp, 'created_at', None))
        data['updated_at'] = self.datetime_to_iso(getattr(exp, 'updated_at', None))

        # 移除 None 值
        data = {k: v for k, v in data.items() if v is not None}

        return data

    def _import_experience_file(self, filepath: Path) -> str:
        """
        导入单个经验文件

        Returns:
            "created", "updated", "unchanged", 或 "errors"
        """
        data = self.read_yaml(filepath)
        if not data:
            return "errors"

        exp_uuid = data.get('uuid') or filepath.stem
        exp_id = data.get('id')

        # 查找现有记录
        existing = None
        if exp_uuid:
            existing = self.store.get_by_uuid(exp_uuid)
        if not existing and exp_id:
            existing = self.store.get(exp_id)

        # 准备经验数据
        exp_data = {
            'uuid': exp_uuid,
            'title': data.get('title', ''),
            'source_type': data.get('source_type', 'manual'),
            'source_ref': data.get('source_ref', ''),
        }

        # 处理 content
        content = data.get('content', {})
        if isinstance(content, dict):
            from domains.experience_hub.core.models import ExperienceContent
            exp_data['content'] = ExperienceContent.from_dict(content)

        # 处理 context
        context = data.get('context', {})
        if isinstance(context, dict):
            from domains.experience_hub.core.models import ExperienceContext
            exp_data['context'] = ExperienceContext.from_dict(context)

        if existing:
            file_mtime = self.get_file_mtime(filepath)
            db_mtime = self.get_db_mtime(existing)

            if self.should_update_db(file_mtime, db_mtime):
                self.store.update(existing.id, **exp_data)
                return "updated"
            else:
                return "unchanged"

        # 创建新经验
        from domains.experience_hub.core.models import Experience
        experience = Experience.from_dict(exp_data)
        self.store.add(experience)
        return "created"

    def _export_links(self) -> None:
        """导出关联关系"""
        if self.store is None:
            return

        try:
            links = self.store.get_all_links()
            if not links:
                return

            links_data = {
                'links': [link.to_dict() for link in links]
            }
            self.write_yaml(self.links_file, links_data)
        except AttributeError:
            # store 可能没有 get_all_links 方法
            pass

    def _import_links(self) -> None:
        """导入关联关系"""
        if self.store is None or not self.links_file.exists():
            return

        try:
            data = self.read_yaml(self.links_file)
            links = data.get('links', [])

            for link_data in links:
                from domains.experience_hub.core.models import ExperienceLink
                link = ExperienceLink.from_dict(link_data)
                self.store.add_link(link)
        except AttributeError:
            # store 可能没有 add_link 方法
            pass

    def get_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        status = {
            "db_count": 0,
            "file_count": 0,
            "links_count": 0,
        }

        if self.store is None:
            return status

        try:
            experiences = self.store.get_all(limit=10000)
            status["db_count"] = len(experiences)
        except Exception:
            return status

        if self.experiences_dir.exists():
            status["file_count"] = len(list(self.experiences_dir.glob("*.yaml")))

        if self.links_file.exists():
            try:
                data = self.read_yaml(self.links_file)
                status["links_count"] = len(data.get('links', []))
            except Exception:
                pass

        return status
