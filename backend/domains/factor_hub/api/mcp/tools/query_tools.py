"""
查询类工具

提供因子查询、统计等只读操作。
"""

import re
from typing import Any, Dict

from .base import BaseTool, ToolResult


class ListFactorsTool(BaseTool):
    """获取因子列表工具"""

    @property
    def name(self) -> str:
        return "list_factors"

    @property
    def description(self) -> str:
        return """获取因子列表，支持多种筛选条件和分页。

可用筛选条件:
- search: 按文件名搜索
- style: 按风格筛选(如"动量"、"反转"、"波动性"等)
- score_min/score_max: 按评分范围筛选
- verified: 是否已验证(true/false)

返回因子名称列表和总数。如需因子详情，请使用 get_factor 工具。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "search": {
                    "type": "string",
                    "description": "按文件名搜索关键词"
                },
                "style": {
                    "type": "string",
                    "description": "按风格筛选，如：动量、反转、波动性、量价、趋势"
                },
                "score_min": {
                    "type": "number",
                    "description": "最低评分"
                },
                "score_max": {
                    "type": "number",
                    "description": "最高评分"
                },
                "verified": {
                    "type": "boolean",
                    "description": "是否已验证"
                },
                "page": {
                    "type": "integer",
                    "description": "页码（从1开始）",
                    "default": 1,
                    "minimum": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "每页数量",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100
                },
                "order_by": {
                    "type": "string",
                    "description": "排序字段",
                    "enum": ["filename", "llm_score", "created_at", "style"],
                    "default": "filename"
                },
                "order_desc": {
                    "type": "boolean",
                    "description": "是否降序",
                    "default": False
                }
            }
        }

    async def execute(self, **params) -> ToolResult:
        try:
            # 转换参数
            search = params.get("search", "")
            style = params.get("style")
            score_min = params.get("score_min")
            score_max = params.get("score_max")
            verified = params.get("verified")
            page = params.get("page", 1)
            page_size = params.get("page_size", 20)
            order_by = params.get("order_by", "filename")
            order_desc = params.get("order_desc", False)

            # 构建筛选条件
            style_filter = style if style else "全部"

            # 评分筛选转换
            score_filter = "全部"
            if score_min is not None or score_max is not None:
                if score_min is not None and score_min >= 4.5:
                    score_filter = "4.5+"
                elif score_min is not None and score_min >= 4.0:
                    score_filter = "4.0-4.5"
                elif score_min is not None and score_min >= 3.0:
                    score_filter = "3.0-4.0"
                elif score_max is not None and score_max < 3.0:
                    score_filter = "< 3.0"

            # 验证状态
            verify_filter = "全部"
            if verified is True:
                verify_filter = "已验证"
            elif verified is False:
                verify_filter = "未验证"

            # 调用服务
            factors, total = self.factor_service.list_factors(
                search=search,
                style_filter=style_filter,
                score_filter=score_filter,
                verify_filter=verify_filter,
                order_by=order_by,
                order_desc=order_desc,
                page=page,
                page_size=page_size,
            )

            # 只返回因子名列表
            factor_names = [f.filename for f in factors]

            return ToolResult(
                success=True,
                data={
                    "factors": factor_names,
                    "total": total,
                    "pages": (total + page_size - 1) // page_size,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetFactorTool(BaseTool):
    """获取单个因子详情"""

    @property
    def name(self) -> str:
        return "get_factor"

    @property
    def description(self) -> str:
        return """获取单个因子的完整详情，包括代码内容。

通过文件名获取因子的所有信息，包括：
- 基本信息：文件名、UUID、风格
- 元数据：核心公式、输入数据、值域、刻画特征、因子分析
- 评分信息：LLM评分、IC、RankIC
- 状态：验证状态
- 代码：完整的因子代码"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "因子文件名（如 Momentum_5d，不含 .py 后缀）"
                },
                "include_code": {
                    "type": "boolean",
                    "description": "是否包含代码内容",
                    "default": True
                }
            },
            "required": ["filename"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            filename = self.normalize_filename(params["filename"])
            include_code = params.get("include_code", True)

            factor = self.factor_service.get_factor(filename)

            if factor is None:
                return ToolResult(
                    success=False,
                    error=f"因子不存在: {filename}"
                )

            # 使用 to_dict() 获取完整字段
            data = factor.to_dict()

            # 转换日期时间字段为字符串
            if data.get("created_at"):
                data["created_at"] = str(data["created_at"])
            if data.get("updated_at"):
                data["updated_at"] = str(data["updated_at"])

            # 确保 verified 和 excluded 为布尔值
            data["verified"] = bool(data.get("verified"))
            data["excluded"] = bool(data.get("excluded"))

            # 根据参数决定是否包含代码
            if not include_code:
                data.pop("code_content", None)
                data.pop("code_path", None)

            return ToolResult(success=True, data=data)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetStatsTool(BaseTool):
    """获取因子库统计信息"""

    @property
    def name(self) -> str:
        return "get_stats"

    @property
    def description(self) -> str:
        return """获取因子库的统计信息。

返回内容包括：
- 总因子数、已评分数、已验证数
- 评分分布（各分段的因子数量）
- 风格分布
- IC/RankIC 统计
- 字段完整度"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    async def execute(self, **params) -> ToolResult:
        try:
            stats = self.factor_service.get_stats()

            return ToolResult(
                success=True,
                data={
                    "total": stats.get("total", 0),
                    "scored": stats.get("scored", 0),
                    "unscored": stats.get("unscored", 0),
                    "verified": stats.get("verified", 0),
                    "score_distribution": stats.get("score_distribution", {}),
                    "style_distribution": stats.get("style_distribution", {}),
                    "score_stats": stats.get("score_stats", {}),
                    "ic_stats": stats.get("ic_stats", {}),
                    "rank_ic_stats": stats.get("rank_ic_stats", {}),
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class GetStylesTool(BaseTool):
    """获取所有因子风格列表"""

    @property
    def name(self) -> str:
        return "get_styles"

    @property
    def description(self) -> str:
        return """获取因子库中所有可用的风格分类。

返回风格列表，如：动量、反转、波动性、量价、趋势等。
可用于筛选因子时选择风格。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    async def execute(self, **params) -> ToolResult:
        try:
            styles = self.factor_service.get_styles()

            return ToolResult(
                success=True,
                data={"styles": styles}
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class SearchByCodeTool(BaseTool):
    """按代码内容搜索因子"""

    @property
    def name(self) -> str:
        return "search_by_code"

    @property
    def description(self) -> str:
        return """在因子代码中搜索特定模式或关键词。

支持正则表达式搜索，可用于：
- 查找使用特定指标的因子（如 rolling、ewm）
- 查找使用特定字段的因子（如 volume、close）
- 查找特定计算模式"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "搜索模式（支持正则表达式）"
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "是否区分大小写",
                    "default": False
                },
                "limit": {
                    "type": "integer",
                    "description": "最大返回数量",
                    "default": 50,
                    "maximum": 100
                }
            },
            "required": ["pattern"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            pattern = params["pattern"]
            case_sensitive = params.get("case_sensitive", False)
            limit = params.get("limit", 50)

            # 编译正则表达式
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return ToolResult(
                    success=False,
                    error=f"无效的正则表达式: {e}"
                )

            # 获取所有因子
            factors, _ = self.factor_service.list_factors(
                page=1,
                page_size=10000
            )

            # 搜索匹配的因子
            matches = []
            for factor in factors:
                code = factor.code_content or ""
                if regex.search(code):
                    # 提取匹配的上下文
                    match = regex.search(code)
                    start = max(0, match.start() - 50)
                    end = min(len(code), match.end() + 50)
                    context = code[start:end]

                    matches.append({
                        "filename": factor.filename,
                        "style": factor.style,
                        "llm_score": factor.llm_score,
                        "match_context": f"...{context}...",
                    })

                    if len(matches) >= limit:
                        break

            return ToolResult(
                success=True,
                data={
                    "pattern": pattern,
                    "matches": matches,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
