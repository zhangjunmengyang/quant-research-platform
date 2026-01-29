"""
经验同步服务

将经验在数据库和 YAML 文件之间同步。
经验使用 PARL 框架（Problem-Approach-Result-Lesson）存储。
"""

import logging
import uuid as uuid_lib
from pathlib import Path
from typing import Any

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

    def export_all(self, overwrite: bool = False) -> dict[str, int]:
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
                # 确保经验有 UUID，如果没有则生成并更新数据库
                if not exp.uuid:
                    exp.uuid = str(uuid_lib.uuid4())
                    try:
                        self.store.update(exp.id, uuid=exp.uuid)
                        logger.info(f"generated_uuid_for_experience: {exp.id} -> {exp.uuid}")
                    except Exception as e:
                        logger.warning(f"failed_to_persist_uuid: {exp.id}, {e}")

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

    def import_all(self) -> dict[str, int]:
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

    def _experience_to_yaml(self, exp: Any) -> dict[str, Any]:
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
        """
        导入关联关系（幂等）

        只导入不存在的关联，避免重复插入错误。
        """
        if self.store is None or not self.links_file.exists():
            return

        try:
            data = self.read_yaml(self.links_file)
            links = data.get('links', [])

            for link_data in links:
                # 先查找对应的经验
                exp_uuid = link_data.get('experience_uuid')
                if not exp_uuid:
                    continue

                experience = self.store.get_by_uuid(exp_uuid)
                if not experience:
                    logger.debug(f"skip_link_import_no_experience: {exp_uuid}")
                    continue

                # 检查关联是否已存在
                entity_type = link_data.get('entity_type', '')
                entity_id = link_data.get('entity_id', '')
                relation = link_data.get('relation', 'related')

                if self.store.link_exists(experience.id, entity_type, entity_id, relation):
                    continue

                # 导入新关联
                from domains.experience_hub.core.models import ExperienceLink
                link = ExperienceLink.from_dict({
                    **link_data,
                    'experience_id': experience.id
                })
                self.store.add_link(link)
        except AttributeError as e:
            # store 可能没有某些方法
            logger.debug(f"experience_links_import_skipped: {e}")
        except Exception as e:
            logger.error(f"experience_links_import_error: {e}")

    def export_single(self, experience_id: int) -> bool:
        """
        导出单个经验

        Args:
            experience_id: 经验 ID

        Returns:
            是否成功
        """
        if self.store is None:
            return False

        try:
            exp = self.store.get(experience_id)
            if exp is None:
                return False

            # 确保经验有 UUID
            if not exp.uuid:
                exp.uuid = str(uuid_lib.uuid4())
                try:
                    self.store.update(exp.id, uuid=exp.uuid)
                except Exception as e:
                    logger.warning(f"failed_to_persist_uuid: {exp.id}, {e}")

            self.ensure_dir(self.experiences_dir)

            filepath = self.experiences_dir / f"{exp.uuid}.yaml"
            data = self._experience_to_yaml(exp)
            self.write_yaml_atomic(filepath, data)

            return True

        except Exception as e:
            logger.error(f"experience_export_single_error: {experience_id}, {e}")
            return False

    def import_single(self, experience_id: int) -> bool:
        """
        导入单个经验（通过 ID）

        Args:
            experience_id: 经验 ID

        Returns:
            是否成功
        """
        if self.store is None:
            return False

        try:
            exp = self.store.get(experience_id)
            if exp is None or not exp.uuid:
                return False

            filepath = self.experiences_dir / f"{exp.uuid}.yaml"
            if not filepath.exists():
                return False

            result = self._import_experience_file(filepath)
            return result in ("created", "updated", "unchanged")

        except Exception as e:
            logger.error(f"experience_import_single_error: {experience_id}, {e}")
            return False

    def get_status(self) -> dict[str, Any]:
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
