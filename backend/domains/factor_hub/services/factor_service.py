"""
因子业务服务层

提供因子管理的业务逻辑，包括查询、更新、验证等操作。
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

from ..core.models import Factor
from ..core.store import FactorStore, get_factor_store

logger = logging.getLogger(__name__)


class FactorService:
    """
    因子业务服务

    封装存储层操作，提供业务逻辑处理。
    """

    def __init__(
        self,
        store: FactorStore | None = None,
        graph_store: GraphStore | None = None,
    ):
        """
        初始化服务

        Args:
            store: 因子存储实例，默认使用单例
            graph_store: 图存储层实例（Neo4j）
        """
        self.store = store or get_factor_store()
        self._graph_store = graph_store

    @property
    def graph_store(self) -> GraphStore:
        """延迟获取图存储层"""
        if self._graph_store is None:
            self._graph_store = get_graph_store()
        return self._graph_store

    def list_factors(
        self,
        search: str = "",
        style_filter: str = "全部",
        score_filter: str = "全部",
        verify_filter: str = "全部",
        order_by: str = "filename",
        order_desc: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Factor], int]:
        """
        获取因子列表

        Args:
            search: 搜索关键词
            style_filter: 风格筛选
            score_filter: 评分筛选
            verify_filter: 验证状态筛选
            order_by: 排序字段
            order_desc: 是否降序
            page: 页码
            page_size: 每页数量

        Returns:
            (因子列表, 总数)
        """
        filter_condition = {}

        # 搜索条件
        if search:
            filter_condition['filename'] = f'contains:{search}'

        # 风格筛选
        if style_filter and style_filter != "全部":
            filter_condition['style'] = f'contains:{style_filter}'

        # 评分筛选
        if score_filter == "4.5+":
            filter_condition['llm_score'] = '>=4.5'
        elif score_filter == "< 3.0":
            filter_condition['llm_score'] = '<3.0'
        elif score_filter == "未评分":
            filter_condition['llm_score'] = 'empty'

        # 验证状态筛选
        from ..core.models import VerificationStatus
        if verify_filter == "通过":
            filter_condition['verification_status'] = VerificationStatus.PASSED
        elif verify_filter == "未验证":
            filter_condition['verification_status'] = VerificationStatus.UNVERIFIED
        elif verify_filter == "废弃":
            filter_condition['verification_status'] = VerificationStatus.FAILED

        # 排序
        order = f"{order_by} DESC" if order_desc else order_by

        # 查询
        all_factors = self.store.query(filter_condition, order_by=order)

        # 额外的范围筛选
        if score_filter == "4.0-4.5":
            all_factors = [f for f in all_factors if f.llm_score and 4.0 <= f.llm_score < 4.5]
        elif score_filter == "3.0-4.0":
            all_factors = [f for f in all_factors if f.llm_score and 3.0 <= f.llm_score < 4.0]

        total = len(all_factors)

        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        factors = all_factors[start:end]

        return factors, total

    def query(
        self,
        filter_condition: dict[str, Any] | None = None,
        order_by: str | None = None,
    ) -> list[Factor]:
        """
        查询因子列表（底层查询接口）

        直接代理到存储层的 query 方法，供 REST API 使用。
        对于更高级的筛选逻辑，请使用 list_factors 方法。

        Args:
            filter_condition: 过滤条件字典
            order_by: 排序字段，如 "created_at DESC"

        Returns:
            因子列表
        """
        return self.store.query(filter_condition, order_by=order_by)

    def query_factors(
        self,
        filter_condition: dict[str, Any] | None = None,
        order_by: str | None = None,
        include_excluded: bool = False,
        page: int | None = None,
        page_size: int | None = None,
    ) -> tuple[list[Factor], int]:
        """
        查询因子列表（支持分页和排除状态）

        Args:
            filter_condition: 过滤条件字典
            order_by: 排序字段，如 "created_at DESC"
            include_excluded: 是否包含已排除的因子
            page: 页码（从1开始），None 表示不分页
            page_size: 每页数量

        Returns:
            (因子列表, 总数)
        """
        all_factors = self.store.query(
            filter_condition,
            order_by=order_by,
            include_excluded=include_excluded,
        )
        total = len(all_factors)

        # 分页
        if page is not None and page_size is not None:
            start = (page - 1) * page_size
            end = start + page_size
            factors = all_factors[start:end]
        else:
            factors = all_factors

        return factors, total

    def get_factor(self, filename: str) -> Factor | None:
        """获取单个因子"""
        return self.store.get(filename)

    def get_factor_with_excluded(self, filename: str) -> Factor | None:
        """获取单个因子（包含已排除的）"""
        return self.store.get(filename, include_excluded=True)

    def update_factor(self, filename: str, **fields) -> bool:
        """更新因子"""
        return self.store.update(filename, **fields)

    def delete_factor(self, filename: str) -> bool:
        """删除因子（同时删除数据库记录、代码文件和元数据文件）"""
        import os
        from pathlib import Path

        # 先获取因子信息，以便知道文件路径
        factor = self.store.get(filename, include_excluded=True)
        if not factor:
            return False

        # 删除数据库记录
        if not self.store.delete(filename):
            return False

        # 删除代码文件
        if factor.code_path:
            code_path = Path(factor.code_path)
            if code_path.exists():
                try:
                    code_path.unlink()
                except Exception:
                    # 文件删除失败不影响整体结果，数据库记录已删除
                    pass

        # 删除元数据文件
        private_dir = Path(os.environ.get('PRIVATE_DATA_DIR', 'private'))
        metadata_path = private_dir / "metadata" / f"{filename}.yaml"
        if metadata_path.exists():
            try:
                metadata_path.unlink()
            except Exception:
                pass

        return True

    def set_verification_status(self, filename: str, status: int, note: str = "") -> bool:
        """设置因子验证状态"""
        return self.store.set_verification_status(filename, status, note)

    def mark_factor_as_passed(self, filename: str, note: str = "") -> bool:
        """标记因子为验证通过"""
        return self.store.mark_as_passed(filename, note)

    def mark_factor_as_failed(self, filename: str, note: str = "") -> bool:
        """标记因子为废弃（失败研究）"""
        return self.store.mark_as_failed(filename, note)

    def reset_factor_verification(self, filename: str) -> bool:
        """重置因子验证状态为未验证"""
        return self.store.reset_verification(filename)

    def batch_mark_as_passed(self, filenames: list[str], note: str = "") -> int:
        """批量标记为验证通过"""
        success = 0
        for filename in filenames:
            if self.store.mark_as_passed(filename, note):
                success += 1
        return success

    def batch_mark_as_failed(self, filenames: list[str], note: str = "") -> int:
        """批量标记为废弃"""
        success = 0
        for filename in filenames:
            if self.store.mark_as_failed(filename, note):
                success += 1
        return success

    def batch_reset_verification(self, filenames: list[str]) -> int:
        """批量重置验证状态"""
        success = 0
        for filename in filenames:
            if self.store.reset_verification(filename):
                success += 1
        return success

    def batch_delete(self, filenames: list[str]) -> int:
        """批量删除（同时删除数据库记录、代码文件和元数据文件）"""
        success = 0
        for filename in filenames:
            if self.delete_factor(filename):
                success += 1
        return success

    def get_styles(self) -> list[str]:
        """获取所有风格"""
        return self.store.get_styles()

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return self.store.get_stats()

    def export_markdown(self, output_path: str | None = None) -> str:
        """导出 Markdown"""
        return self.store.export_to_markdown(output_path)

    def exclude_factor(self, filename: str, reason: str = "") -> bool:
        """排除因子"""
        return self.store.exclude_factor(filename, reason)

    def unexclude_factor(self, filename: str) -> bool:
        """取消排除因子"""
        return self.store.unexclude_factor(filename)

    def get_excluded_factors(self) -> dict[str, str]:
        """获取所有排除的因子"""
        return self.store.get_excluded_factors()

    def create_factor(
        self,
        filename: str,
        code_content: str,
        style: str = "",
        formula: str = "",
        description: str = "",
    ) -> tuple[bool, str]:
        """
        创建新因子

        将因子代码同时保存到文件系统和数据库。

        Args:
            filename: 因子文件名（不含扩展名）
            code_content: 因子代码内容
            style: 风格分类
            formula: 核心公式
            description: 刻画特征

        Returns:
            (是否成功, 消息)
        """
        import re

        from ..core.config import get_config_loader

        # 验证文件名
        filename = filename.strip()
        if not filename:
            return False, "文件名不能为空"

        # 确保文件名符合 Python 标识符规范
        safe_filename = re.sub(r'[^\w]', '_', filename)
        if safe_filename[0].isdigit():
            safe_filename = f"factor_{safe_filename}"

        # 检查是否已存在
        existing = self.store.get(safe_filename)
        if existing:
            return False, f"因子 {safe_filename} 已存在"

        # 保存到文件系统
        config = get_config_loader()
        factors_dir = config.factors_dir
        factors_dir.mkdir(parents=True, exist_ok=True)

        code_path = factors_dir / f"{safe_filename}.py"
        if code_path.exists():
            return False, f"因子文件 {safe_filename}.py 已存在"

        try:
            code_path.write_text(code_content, encoding='utf-8')
        except Exception as e:
            return False, f"保存因子文件失败: {e}"

        # 创建因子记录
        factor = Factor(
            filename=safe_filename,
            code_content=code_content,
            code_path=str(code_path),
            style=style,
            formula=formula,
            description=description,
        )

        success = self.store.add(factor)
        if success:
            return True, f"因子 {safe_filename} 创建成功"
        else:
            # 如果数据库添加失败，删除已创建的文件
            if code_path.exists():
                code_path.unlink()
            return False, "因子添加到数据库失败"

    def update_factor_code(
        self,
        filename: str,
        code_content: str,
    ) -> tuple[bool, str]:
        """
        更新因子代码

        同时更新数据库和文件系统中的代码。

        Args:
            filename: 因子文件名
            code_content: 新的代码内容

        Returns:
            (是否成功, 消息)
        """
        from ..core.config import get_config_loader

        # 验证因子存在
        factor = self.store.get(filename)
        if factor is None:
            return False, f"因子 {filename} 不存在"

        # 更新文件系统
        config = get_config_loader()
        code_path = config.factors_dir / f"{filename}.py"

        try:
            code_path.write_text(code_content, encoding='utf-8')
        except Exception as e:
            return False, f"更新因子文件失败: {e}"

        # 更新数据库
        success = self.store.update(
            filename,
            code_content=code_content,
            code_path=str(code_path),
        )

        if success:
            return True, f"因子 {filename} 代码已更新"
        else:
            return False, "更新数据库失败"

    def check_consistency(self) -> dict[str, Any]:
        """
        检测因子一致性

        对比文件系统、数据库、元数据YAML三者的一致性。

        Returns:
            {
                "is_consistent": bool,
                "summary": {
                    "code_files": int,      # 代码文件数量
                    "db_records": int,      # 数据库记录数量
                    "metadata_files": int,  # 元数据文件数量
                },
                "orphan_db_records": [...],      # 数据库中存在但代码文件不存在
                "orphan_metadata": [...],        # 元数据存在但代码文件不存在
                "missing_metadata": [...],       # 代码文件存在但元数据不存在
                "missing_db_records": [...],     # 代码文件存在但数据库记录不存在
            }
        """
        import os
        from pathlib import Path

        from ..core.config import get_config_loader

        config = get_config_loader()
        factors_dir = config.factors_dir
        private_dir = Path(os.environ.get('PRIVATE_DATA_DIR', 'private'))
        metadata_dir = private_dir / "metadata"

        # 1. 获取代码文件列表
        code_files = set()
        if factors_dir.exists():
            for f in factors_dir.glob("*.py"):
                if f.name != "__init__.py":
                    code_files.add(f.stem)

        # 2. 获取数据库记录列表
        all_factors = self.store.query(include_excluded=True)
        db_records = {f.filename for f in all_factors}

        # 3. 获取元数据文件列表
        metadata_files = set()
        if metadata_dir.exists():
            for f in metadata_dir.glob("*.yaml"):
                metadata_files.add(f.stem)

        # 4. 计算差异
        orphan_db_records = sorted(db_records - code_files)
        orphan_metadata = sorted(metadata_files - code_files)
        missing_metadata = sorted(code_files - metadata_files)
        missing_db_records = sorted(code_files - db_records)

        is_consistent = (
            len(orphan_db_records) == 0 and
            len(orphan_metadata) == 0 and
            len(missing_db_records) == 0
        )

        return {
            "is_consistent": is_consistent,
            "summary": {
                "code_files": len(code_files),
                "db_records": len(db_records),
                "metadata_files": len(metadata_files),
            },
            "orphan_db_records": orphan_db_records,
            "orphan_metadata": orphan_metadata,
            "missing_metadata": missing_metadata,
            "missing_db_records": missing_db_records,
        }

    def cleanup_orphans(self, dry_run: bool = True) -> dict[str, Any]:
        """
        清理孤立数据

        删除代码文件不存在但数据库/元数据仍存在的记录。

        Args:
            dry_run: 是否仅预览（不实际删除）

        Returns:
            {
                "dry_run": bool,
                "deleted_db_records": [...],
                "deleted_metadata": [...],
                "errors": [...],
            }
        """
        import os
        from pathlib import Path

        consistency = self.check_consistency()
        private_dir = Path(os.environ.get('PRIVATE_DATA_DIR', 'private'))
        metadata_dir = private_dir / "metadata"

        deleted_db_records = []
        deleted_metadata = []
        errors = []

        # 删除孤立的数据库记录
        for filename in consistency["orphan_db_records"]:
            if dry_run:
                deleted_db_records.append(filename)
            else:
                try:
                    if self.store.delete(filename):
                        deleted_db_records.append(filename)
                    else:
                        errors.append(f"删除数据库记录失败: {filename}")
                except Exception as e:
                    errors.append(f"删除数据库记录异常: {filename} - {e}")

        # 删除孤立的元数据文件
        for filename in consistency["orphan_metadata"]:
            metadata_path = metadata_dir / f"{filename}.yaml"
            if dry_run:
                deleted_metadata.append(filename)
            else:
                try:
                    if metadata_path.exists():
                        metadata_path.unlink()
                        deleted_metadata.append(filename)
                except Exception as e:
                    errors.append(f"删除元数据文件异常: {filename} - {e}")

        return {
            "dry_run": dry_run,
            "deleted_db_records": deleted_db_records,
            "deleted_metadata": deleted_metadata,
            "errors": errors,
        }

    def sync_missing(self) -> dict[str, Any]:
        """
        同步缺失的数据

        为存在代码文件但缺少数据库记录的因子创建记录。

        Returns:
            {
                "created_db_records": [...],
                "exported_metadata": [...],
                "errors": [...],
            }
        """
        consistency = self.check_consistency()

        created_db_records = []
        exported_metadata = []
        errors = []

        # 为缺失的数据库记录创建因子
        for filename in consistency["missing_db_records"]:
            try:
                # 触发代码同步会自动创建记录
                result = self.store.sync_code_from_files()
                if result.get("created", 0) > 0:
                    created_db_records.append(filename)
                break  # sync_code_from_files 会处理所有缺失的
            except Exception as e:
                errors.append(f"同步因子代码失败: {filename} - {e}")

        # 导出缺失的元数据
        if consistency["missing_metadata"]:
            try:
                from domains.mcp_core.sync import get_sync_manager
                manager = get_sync_manager()
                result = manager.export("factors")
                exported_metadata = consistency["missing_metadata"]
            except Exception as e:
                errors.append(f"导出元数据失败: {e}")

        return {
            "created_db_records": created_db_records,
            "exported_metadata": exported_metadata,
            "errors": errors,
        }

    def ingest_factor_from_code(
        self,
        code_content: str,
        auto_name: bool = True,
    ) -> tuple[bool, str, str | None]:
        """
        从代码内容入库因子

        解析代码中的因子名，自动创建因子记录。
        支持 Agent 生成代码后自动入库的场景。

        Args:
            code_content: 因子代码内容（包含 signal_multi_params 函数）
            auto_name: 是否自动从代码中提取名称

        Returns:
            (是否成功, 消息, 因子名)
        """
        import re
        from datetime import datetime

        # 验证代码包含必需的函数
        if "def signal_multi_params" not in code_content:
            return False, "代码必须包含 signal_multi_params 函数", None

        # 从代码中提取因子名
        factor_name = None
        if auto_name:
            lines = code_content.split('\n')
            for line in lines[:10]:  # 检查前10行
                line = line.strip()
                if line.startswith('# name:'):
                    factor_name = line.replace('# name:', '').strip()
                    break
                elif line.startswith('#') and 'name' in line.lower():
                    match = re.search(r'name[:\s]+([a-zA-Z_][a-zA-Z0-9_]*)', line, re.IGNORECASE)
                    if match:
                        factor_name = match.group(1)
                        break

        # 如果没有找到因子名，使用时间戳
        if not factor_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            factor_name = f"factor_{timestamp}"

        # 调用创建方法
        success, message = self.create_factor(
            filename=factor_name,
            code_content=code_content,
        )

        return success, message, factor_name if success else None


    # ==================== 知识边关联 (Neo4j) ====================

    def link_factor(
        self,
        factor_name: str,
        target_type: str,
        target_id: str,
        relation: str = "related",
        is_bidirectional: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        """
        创建因子与其他实体的关联

        Args:
            factor_name: 因子名称
            target_type: 目标实体类型（data/factor/strategy/note/research/experience）
            target_id: 目标实体 ID
            relation: 关系类型（derives/relates），可配合 subtype 细化语义
            is_bidirectional: 是否双向关联
            metadata: 扩展元数据

        Returns:
            (成功, 消息)
        """
        # 验证因子存在
        factor = self.store.get(factor_name)
        if factor is None:
            return False, f"因子不存在: {factor_name}"

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

        # 创建图边
        edge = GraphEdge(
            source_type=NodeType.FACTOR,
            source_id=factor_name,
            target_type=target_node_type,
            target_id=target_id,
            relation=relation_type,
            is_bidirectional=is_bidirectional,
            metadata=metadata or {},
        )

        success = self.graph_store.create_edge(edge)
        if success:
            logger.info(f"创建因子关联: factor:{factor_name} -[{relation}]-> {target_type}:{target_id}")
            return True, "关联成功"
        else:
            return False, "关联失败"

    def get_factor_edges(
        self,
        factor_name: str,
        include_bidirectional: bool = True,
    ) -> list[dict[str, Any]]:
        """
        获取因子的所有关联

        Args:
            factor_name: 因子名称
            include_bidirectional: 是否包含双向关联

        Returns:
            关联列表
        """
        edges = self.graph_store.get_edges_by_entity(
            entity_type=NodeType.FACTOR,
            entity_id=factor_name,
            include_bidirectional=include_bidirectional,
        )
        return [edge.to_dict() for edge in edges]

    def get_edges_to_factor(self, factor_name: str) -> list[dict[str, Any]]:
        """
        获取指向因子的所有关联

        Args:
            factor_name: 因子名称

        Returns:
            关联列表
        """
        edges = self.graph_store.get_edges_to_entity(
            entity_type=NodeType.FACTOR,
            entity_id=factor_name,
        )
        return [edge.to_dict() for edge in edges]

    def trace_factor_lineage(
        self,
        factor_name: str,
        direction: str = "backward",
        max_depth: int = 5,
    ) -> dict[str, Any]:
        """
        追溯因子的知识链路

        Args:
            factor_name: 因子名称
            direction: 追溯方向
                - "backward": 向上追溯源头（因子基于什么）
                - "forward": 向下追溯应用（因子被什么使用/改进）
            max_depth: 最大追溯深度

        Returns:
            链路追溯结果，包含 start_type, start_id, direction, max_depth, count, nodes
        """
        result = self.graph_store.trace_lineage(
            entity_type=NodeType.FACTOR,
            entity_id=factor_name,
            direction=direction,
            max_depth=max_depth,
        )
        return result.to_dict()

    def delete_factor_edge(
        self,
        target_type: str,
        target_id: str,
        relation: str,
        factor_name: str,
    ) -> tuple[bool, str]:
        """
        删除因子关联

        Args:
            target_type: 目标实体类型
            target_id: 目标实体 ID
            relation: 关系类型
            factor_name: 因子名称（作为源）

        Returns:
            (成功, 消息)
        """
        try:
            target_node_type = NodeType(target_type)
            relation_type = RelationType(relation)
        except ValueError as e:
            return False, f"无效的参数: {e}"

        success = self.graph_store.delete_edge(
            source_type=NodeType.FACTOR,
            source_id=factor_name,
            target_type=target_node_type,
            target_id=target_id,
            relation=relation_type,
        )
        if success:
            logger.info(f"删除因子关联: factor:{factor_name} -[{relation}]-> {target_type}:{target_id}")
            return True, "删除成功"
        else:
            return False, "删除失败"


# 单例
_service: FactorService | None = None


def get_factor_service() -> FactorService:
    """获取服务单例"""
    global _service
    if _service is None:
        _service = FactorService()
    return _service


def reset_factor_service():
    """重置单例（用于测试）"""
    global _service
    _service = None
