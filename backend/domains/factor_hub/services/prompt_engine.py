"""
Prompt 模板引擎 - 变量注入和渲染

支持模板变量替换和条件渲染。
"""

import json
import re
from typing import Any

from ..core.config import ConfigLoader, get_config_loader


class PromptEngine:
    """
    Prompt 模板引擎

    支持:
    - {variable} - 简单变量替换
    - {% if condition %}...{% endif %} - 条件渲染
    """

    def __init__(self, config_loader: ConfigLoader | None = None):
        """
        初始化 Prompt 引擎

        Args:
            config_loader: 配置加载器实例
        """
        self.config = config_loader or get_config_loader()
        self._user_vars: dict[str, Any] | None = None

    @property
    def user_vars(self) -> dict[str, Any]:
        """获取用户变量"""
        if self._user_vars is None:
            self._user_vars = self.config.load_user_vars()
        return self._user_vars

    def reload_user_vars(self):
        """重新加载用户变量"""
        self._user_vars = self.config.load_user_vars(reload=True)

    def render(
        self,
        task_name: str,
        input_vars: dict[str, Any] | None = None,
        extra_vars: dict[str, Any] | None = None
    ) -> dict[str, str]:
        """
        渲染 Prompt 模板

        Args:
            task_name: 任务名称 (如 "score", "review")
            input_vars: 运行时输入变量 (如 filename, code)
            extra_vars: 额外变量 (覆盖其他变量)

        Returns:
            {"system": str, "user": str} 渲染后的 Prompt
        """
        prompt_config = self.config.load_prompt(task_name)
        input_vars = input_vars or {}
        extra_vars = extra_vars or {}

        # 合并变量：user_vars < input_vars < extra_vars
        all_vars = {**self.user_vars, **input_vars, **extra_vars}

        system_template = prompt_config.get('system', '')
        system = self._render_template(system_template, all_vars)

        user_template = prompt_config.get('user', '')
        user = self._render_template(user_template, all_vars)

        return {
            'system': system,
            'user': user,
            'task': task_name,
            'output_format': prompt_config.get('output', {}).get('format', 'text'),
        }

    def render_field(
        self,
        field_name: str,
        input_vars: dict[str, Any] | None = None,
        extra_vars: dict[str, Any] | None = None
    ) -> dict[str, str]:
        """
        渲染字段填充的 Prompt

        Args:
            field_name: 字段名称
            input_vars: 运行时输入变量
            extra_vars: 额外变量

        Returns:
            渲染后的 Prompt
        """
        prompt_config = self.config.load_field_prompt(field_name)
        input_vars = input_vars or {}
        extra_vars = extra_vars or {}

        all_vars = {**self.user_vars, **input_vars, **extra_vars}

        system_template = prompt_config.get('system', '')
        system = self._render_template(system_template, all_vars)

        user_template = prompt_config.get('user', '')
        user = self._render_template(user_template, all_vars)

        return {
            'system': system,
            'user': user,
            'field': field_name,
            'output_format': prompt_config.get('output', {}).get('format', 'text'),
        }

    def _render_template(self, template: str, variables: dict[str, Any]) -> str:
        """渲染模板字符串"""
        if not template:
            return ''

        result = template
        result = self._process_conditionals(result, variables)
        result = self._substitute_variables(result, variables)
        return result

    def _process_conditionals(self, template: str, variables: dict[str, Any]) -> str:
        """处理条件渲染块"""
        pattern = r'\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*endif\s*%\}'

        def replace_conditional(match):
            condition_var = match.group(1)
            content = match.group(2)
            value = variables.get(condition_var)
            return content if value else ''

        return re.sub(pattern, replace_conditional, template, flags=re.DOTALL)

    def _substitute_variables(self, template: str, variables: dict[str, Any]) -> str:
        """替换变量占位符"""
        pattern = r'\{(\w+)\}'

        def replace_var(match):
            var_name = match.group(1)
            value = variables.get(var_name)
            if value is not None:
                if isinstance(value, (list, dict)):
                    return json.dumps(value, ensure_ascii=False, indent=2)
                return str(value)
            return match.group(0)

        return re.sub(pattern, replace_var, template)

    def validate_prompt(self, task_name: str) -> list[str]:
        """验证 Prompt 配置，返回错误列表"""
        errors = []

        try:
            prompt_config = self.config.load_prompt(task_name)
        except FileNotFoundError as e:
            return [str(e)]

        required_vars = prompt_config.get('required_vars', [])
        for var in required_vars:
            if var not in self.user_vars:
                errors.append(f"缺少必需的用户变量: {var}")

        output_config = prompt_config.get('output', {})
        output_format = output_config.get('format')
        if output_format and output_format not in ['json', 'text', 'markdown']:
            errors.append(f"不支持的输出格式: {output_format}")

        return errors

    def get_input_vars(self, task_name: str) -> list[str]:
        """获取任务所需的输入变量列表"""
        prompt_config = self.config.load_prompt(task_name)
        return prompt_config.get('input_vars', [])

    def get_output_schema(self, task_name: str) -> dict[str, Any]:
        """获取任务的输出 schema"""
        prompt_config = self.config.load_prompt(task_name)
        return prompt_config.get('output', {}).get('schema', {})


# 单例
_prompt_engine: PromptEngine | None = None


def get_prompt_engine() -> PromptEngine:
    """获取 Prompt 引擎单例"""
    global _prompt_engine
    if _prompt_engine is None:
        _prompt_engine = PromptEngine()
    return _prompt_engine


def reset_prompt_engine():
    """重置单例（用于测试）"""
    global _prompt_engine
    _prompt_engine = None
