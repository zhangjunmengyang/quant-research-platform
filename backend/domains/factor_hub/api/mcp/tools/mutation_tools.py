"""
修改类工具

提供因子 CRUD 写操作：create_factor, update_factor, delete_factor
"""

from typing import Any, Dict

from .base import BaseTool, ToolResult


# 可更新字段的 schema 定义（复用）
FACTOR_FIELDS_SCHEMA = {
    # 代码
    "code_content": {
        "type": "string",
        "description": "因子代码内容（必须包含 signal_multi_params 函数）"
    },
    # 基础信息
    "factor_type": {
        "type": "string",
        "enum": ["time_series", "cross_section"],
        "description": "因子类型（time_series=时序, cross_section=截面）"
    },
    "style": {
        "type": "string",
        "description": "风格分类"
    },
    "formula": {
        "type": "string",
        "description": "核心公式"
    },
    "input_data": {
        "type": "string",
        "description": "输入数据"
    },
    "value_range": {
        "type": "string",
        "description": "值域"
    },
    "description": {
        "type": "string",
        "description": "刻画特征"
    },
    "analysis": {
        "type": "string",
        "description": "因子分析"
    },
    # 评分指标
    "llm_score": {
        "type": "number",
        "description": "LLM评分（0-5）",
        "minimum": 0,
        "maximum": 5
    },
    "code_complexity": {
        "type": "number",
        "description": "代码复杂度评分"
    },
    # 绩效指标
    "ic": {
        "type": "number",
        "description": "IC值"
    },
    "rank_ic": {
        "type": "number",
        "description": "RankIC值"
    },
    "backtest_sharpe": {
        "type": "number",
        "description": "回测夏普比率"
    },
    "backtest_ic": {
        "type": "number",
        "description": "回测IC均值"
    },
    "backtest_ir": {
        "type": "number",
        "description": "回测信息比率（ICIR）"
    },
    "turnover": {
        "type": "number",
        "description": "换手率"
    },
    "decay": {
        "type": "integer",
        "description": "IC半衰期（周期数）"
    },
    "last_backtest_date": {
        "type": "string",
        "description": "最后回测日期（YYYY-MM-DD格式）"
    },
    # 分类标签
    "market_regime": {
        "type": "string",
        "description": "适用市场状态（牛市/熊市/震荡）"
    },
    "best_holding_period": {
        "type": "integer",
        "description": "最佳持仓周期（小时）"
    },
    "tags": {
        "type": "string",
        "description": "标签（英文逗号分隔）"
    },
    # 验证状态
    "verified": {
        "type": "integer",
        "enum": [0, 1],
        "description": "是否已验证（0=未验证, 1=已验证）"
    },
    "verify_note": {
        "type": "string",
        "description": "验证备注"
    },
    # 排除状态
    "excluded": {
        "type": "integer",
        "enum": [0, 1],
        "description": "是否排除（0=正常, 1=已排除）"
    },
    "exclude_reason": {
        "type": "string",
        "description": "排除原因"
    }
}


class CreateFactorTool(BaseTool):
    """创建新因子"""

    @property
    def name(self) -> str:
        return "create_factor"

    @property
    def description(self) -> str:
        return """创建新因子并入库。

将因子代码保存到文件系统和数据库。

代码要求：
- 必须包含 signal_multi_params 函数
- 建议在代码开头添加 # name: FactorName 注释

如果没有指定 filename，会自动从代码注释中提取因子名，或使用时间戳生成。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        properties = {
            "filename": {
                "type": "string",
                "description": "因子文件名（可选，不含扩展名，未指定时从代码注释提取或自动生成）"
            },
            **FACTOR_FIELDS_SCHEMA
        }
        return {
            "type": "object",
            "properties": properties,
            "required": ["code_content"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            code_content = params.pop("code_content")
            filename = params.pop("filename", "")
            if filename:
                filename = self.normalize_filename(filename)

            # 收集所有额外字段
            extra_fields = {k: v for k, v in params.items() if v is not None}

            # 如果没有提供 filename，自动从代码提取
            if not filename:
                success, message, factor_name = self.factor_service.ingest_factor_from_code(
                    code_content=code_content,
                    auto_name=True,
                )
                if success and extra_fields:
                    self.factor_service.update_factor(factor_name, **extra_fields)
            else:
                # 使用提供的 filename 创建
                style = extra_fields.pop("style", "")
                formula = extra_fields.pop("formula", "")
                description = extra_fields.pop("description", "")

                success, message = self.factor_service.create_factor(
                    filename=filename,
                    code_content=code_content,
                    style=style,
                    formula=formula,
                    description=description,
                )
                factor_name = filename

                # 设置其他额外字段
                if success and extra_fields:
                    self.factor_service.update_factor(factor_name, **extra_fields)

            if success:
                return ToolResult(
                    success=True,
                    data={"filename": factor_name}
                )
            else:
                return ToolResult(success=False, error=message)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class UpdateFactorTool(BaseTool):
    """更新因子"""

    @property
    def name(self) -> str:
        return "update_factor"

    @property
    def description(self) -> str:
        return """更新因子的任意字段，包括代码和元数据。

可更新的字段包括：
- 代码: code_content（同时更新文件系统和数据库）
- 基础信息: factor_type, style, formula, input_data, value_range, description, analysis
- 评分指标: llm_score, code_complexity
- 绩效指标: ic, rank_ic, backtest_sharpe, backtest_ic, backtest_ir, turnover, decay, last_backtest_date
- 分类标签: market_regime, best_holding_period, tags
- 验证状态: verified, verify_note
- 排除状态: excluded, exclude_reason

注意：不能更新 filename、uuid、code_path、created_at 等系统字段。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        properties = {
            "filename": {
                "type": "string",
                "description": "因子文件名（如 Momentum_5d，不含 .py 后缀）"
            },
            **FACTOR_FIELDS_SCHEMA
        }
        return {
            "type": "object",
            "properties": properties,
            "required": ["filename"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            filename = self.normalize_filename(params.pop("filename"))

            # 验证因子存在
            factor = self.factor_service.get_factor(filename)
            if factor is None:
                return ToolResult(
                    success=False,
                    error=f"因子不存在: {filename}"
                )

            # 过滤掉 None 值
            update_fields = {k: v for k, v in params.items() if v is not None}

            if not update_fields:
                return ToolResult(
                    success=False,
                    error="没有提供要更新的字段"
                )

            # 如果包含 code_content，需要同时更新文件系统
            code_content = update_fields.pop("code_content", None)
            if code_content is not None:
                success, message = self.factor_service.update_factor_code(
                    filename=filename,
                    code_content=code_content,
                )
                if not success:
                    return ToolResult(success=False, error=message)

            # 更新其他字段
            if update_fields:
                success = self.factor_service.update_factor(filename, **update_fields)
                if not success:
                    return ToolResult(success=False, error="更新失败")

            # 计算总更新字段数
            total_fields = list(update_fields.keys())
            if code_content is not None:
                total_fields.append("code_content")

            return ToolResult(
                success=True,
                data={
                    "filename": filename,
                    "updated_fields": total_fields,
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class DeleteFactorTool(BaseTool):
    """删除因子"""

    @property
    def name(self) -> str:
        return "delete_factor"

    @property
    def description(self) -> str:
        return """删除因子。

从数据库中删除因子记录。文件系统中的代码文件保留（可手动删除）。

如果只是想标记因子为无效而非删除，建议使用 update_factor 设置 excluded=1。"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "因子文件名（如 Momentum_5d，不含 .py 后缀）"
                }
            },
            "required": ["filename"]
        }

    async def execute(self, **params) -> ToolResult:
        try:
            filename = self.normalize_filename(params["filename"])

            # 验证因子存在
            factor = self.factor_service.get_factor(filename)
            if factor is None:
                return ToolResult(
                    success=False,
                    error=f"因子不存在: {filename}"
                )

            success = self.factor_service.delete_factor(filename)

            if success:
                return ToolResult(
                    success=True,
                    data={"filename": filename}
                )
            else:
                return ToolResult(success=False, error="删除失败")

        except Exception as e:
            return ToolResult(success=False, error=str(e))
