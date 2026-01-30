"""
筛选表达式解析器

解析符号表达式如 "annual_return > 10" 为结构化条件。
"""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class FilterCondition:
    """解析后的筛选条件"""

    field: str
    operator: str
    value: Any


class FilterParser:
    """
    筛选表达式解析器

    支持的表达式格式: <field> <operator> <value>
    支持的运算符: >, <, >=, <=, =, !=

    安全特性:
    - 字段白名单验证
    - 运算符白名单
    - 值类型转换
    """

    ALLOWED_OPERATORS = {">", "<", ">=", "<=", "=", "!="}

    # 表达式正则: field operator value
    # 运算符匹配顺序很重要: 先匹配 >= <= != 再匹配 > < =
    EXPRESSION_PATTERN = re.compile(r"^(\w+)\s*(>=|<=|!=|>|<|=)\s*(.+)$")

    def __init__(
        self,
        allowed_fields: set[str],
        numeric_fields: set[str] | None = None,
    ):
        """
        初始化解析器

        Args:
            allowed_fields: 允许筛选的字段白名单
            numeric_fields: 数值类型字段集合（用于值类型转换）
        """
        self.allowed_fields = allowed_fields
        self.numeric_fields = numeric_fields or set()

    def parse(self, expression: str) -> FilterCondition | None:
        """
        解析单个表达式

        Args:
            expression: 如 "annual_return > 10"

        Returns:
            FilterCondition 或 None (无效表达式)
        """
        expression = expression.strip()
        match = self.EXPRESSION_PATTERN.match(expression)

        if not match:
            return None

        field, operator, value_str = match.groups()

        # 字段白名单验证 (防 SQL 注入)
        if field not in self.allowed_fields:
            return None

        # 运算符白名单验证
        if operator not in self.ALLOWED_OPERATORS:
            return None

        # 值转换
        value = self._parse_value(field, value_str.strip())

        return FilterCondition(field=field, operator=operator, value=value)

    def parse_many(self, expressions: list[str]) -> list[FilterCondition]:
        """
        解析多个表达式，忽略无效项

        Args:
            expressions: 表达式列表

        Returns:
            有效的 FilterCondition 列表
        """
        conditions = []
        for expr in expressions:
            cond = self.parse(expr)
            if cond:
                conditions.append(cond)
        return conditions

    def _parse_value(self, field: str, value_str: str) -> Any:
        """
        值类型转换

        Args:
            field: 字段名
            value_str: 值字符串

        Returns:
            转换后的值
        """
        # 布尔值
        if value_str.lower() in ("true", "false"):
            return value_str.lower() == "true"

        # 数值字段
        if field in self.numeric_fields:
            try:
                if "." in value_str:
                    return float(value_str)
                return int(value_str)
            except ValueError:
                return value_str

        # 尝试数值转换
        try:
            if "." in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            return value_str
