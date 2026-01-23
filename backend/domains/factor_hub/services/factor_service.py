"""
因子业务服务层

提供因子管理的业务逻辑，包括查询、更新、验证等操作。
"""

from typing import List, Optional, Dict, Any, Tuple

from ..core.store import get_factor_store, FactorStore
from ..core.models import Factor


class FactorService:
    """
    因子业务服务

    封装存储层操作，提供业务逻辑处理。
    """

    def __init__(self, store: Optional[FactorStore] = None):
        """
        初始化服务

        Args:
            store: 因子存储实例，默认使用单例
        """
        self.store = store or get_factor_store()

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
    ) -> Tuple[List[Factor], int]:
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
        if verify_filter == "已验证":
            filter_condition['verified'] = True
        elif verify_filter == "未验证":
            filter_condition['verified'] = False

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
        filter_condition: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
    ) -> List[Factor]:
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
        filter_condition: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        include_excluded: bool = False,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Tuple[List[Factor], int]:
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

    def get_factor(self, filename: str) -> Optional[Factor]:
        """获取单个因子"""
        return self.store.get(filename)

    def get_factor_with_excluded(self, filename: str) -> Optional[Factor]:
        """获取单个因子（包含已排除的）"""
        return self.store.get(filename, include_excluded=True)

    def update_factor(self, filename: str, **fields) -> bool:
        """更新因子"""
        return self.store.update(filename, **fields)

    def delete_factor(self, filename: str) -> bool:
        """删除因子（同时删除数据库记录和代码文件）"""
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

        return True

    def verify_factor(self, filename: str, note: str = "") -> bool:
        """验证因子"""
        return self.store.verify(filename, note)

    def unverify_factor(self, filename: str) -> bool:
        """取消验证"""
        return self.store.unverify(filename)

    def batch_verify(self, filenames: List[str], note: str = "") -> int:
        """批量验证"""
        success = 0
        for filename in filenames:
            if self.store.verify(filename, note):
                success += 1
        return success

    def batch_unverify(self, filenames: List[str]) -> int:
        """批量取消验证"""
        success = 0
        for filename in filenames:
            if self.store.unverify(filename):
                success += 1
        return success

    def batch_delete(self, filenames: List[str]) -> int:
        """批量删除"""
        success = 0
        for filename in filenames:
            if self.store.delete(filename):
                success += 1
        return success

    def get_styles(self) -> List[str]:
        """获取所有风格"""
        return self.store.get_styles()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.store.get_stats()

    def export_markdown(self, output_path: Optional[str] = None) -> str:
        """导出 Markdown"""
        return self.store.export_to_markdown(output_path)

    def exclude_factor(self, filename: str, reason: str = "") -> bool:
        """排除因子"""
        return self.store.exclude_factor(filename, reason)

    def unexclude_factor(self, filename: str) -> bool:
        """取消排除因子"""
        return self.store.unexclude_factor(filename)

    def get_excluded_factors(self) -> Dict[str, str]:
        """获取所有排除的因子"""
        return self.store.get_excluded_factors()

    def create_factor(
        self,
        filename: str,
        code_content: str,
        style: str = "",
        formula: str = "",
        description: str = "",
    ) -> Tuple[bool, str]:
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
        from pathlib import Path
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
    ) -> Tuple[bool, str]:
        """
        更新因子代码

        同时更新数据库和文件系统中的代码。

        Args:
            filename: 因子文件名
            code_content: 新的代码内容

        Returns:
            (是否成功, 消息)
        """
        from pathlib import Path
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

    def ingest_factor_from_code(
        self,
        code_content: str,
        auto_name: bool = True,
    ) -> Tuple[bool, str, Optional[str]]:
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


# 单例
_service: Optional[FactorService] = None


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
