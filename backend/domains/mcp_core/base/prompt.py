"""
MCP Prompt 基类和提供者

提供可扩展的 Prompt 定义框架，支持:
- 预定义 Prompt 模板
- 动态参数填充
- Prompt 分类管理
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class PromptArgument:
    """Prompt 参数定义"""
    name: str
    description: str
    required: bool = True


@dataclass
class PromptDefinition:
    """MCP Prompt 定义"""
    name: str
    description: str
    arguments: List[PromptArgument] = field(default_factory=list)

    def to_mcp_format(self) -> Dict[str, Any]:
        """转换为 MCP 协议格式"""
        return {
            "name": self.name,
            "description": self.description,
            "arguments": [
                {
                    "name": arg.name,
                    "description": arg.description,
                    "required": arg.required,
                }
                for arg in self.arguments
            ],
        }


@dataclass
class PromptMessage:
    """Prompt 消息"""
    role: str  # "user" | "assistant"
    content: str

    def to_mcp_format(self) -> Dict[str, Any]:
        """转换为 MCP 协议格式"""
        return {
            "role": self.role,
            "content": {
                "type": "text",
                "text": self.content,
            },
        }


@dataclass
class PromptResult:
    """Prompt 获取结果"""
    description: Optional[str]
    messages: List[PromptMessage]

    def to_mcp_format(self) -> Dict[str, Any]:
        """转换为 MCP 协议格式"""
        result = {
            "messages": [msg.to_mcp_format() for msg in self.messages],
        }
        if self.description:
            result["description"] = self.description
        return result


class BasePromptProvider(ABC):
    """
    Prompt 提供者基类

    管理 MCP Prompt 的注册和获取。

    使用方式:
        class MyPromptProvider(BasePromptProvider):
            def __init__(self):
                super().__init__()
                self._register_prompts()

            def _register_prompts(self):
                self.register(
                    name="analyze_factor",
                    description="分析因子代码",
                    arguments=[
                        PromptArgument("code", "因子代码"),
                        PromptArgument("context", "上下文信息", required=False),
                    ],
                    handler=self._get_analyze_prompt,
                )

            async def _get_analyze_prompt(self, code: str, context: str = "") -> PromptResult:
                return PromptResult(
                    description="分析因子代码的 Prompt",
                    messages=[
                        PromptMessage("user", f"请分析以下因子代码:\\n{code}"),
                    ],
                )
    """

    def __init__(self):
        self._prompts: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        description: str,
        handler: Callable[..., Awaitable[PromptResult]],
        arguments: Optional[List[PromptArgument]] = None,
    ) -> None:
        """
        注册 Prompt

        Args:
            name: Prompt 名称
            description: Prompt 描述
            handler: Prompt 获取处理函数
            arguments: 参数定义列表
        """
        self._prompts[name] = {
            "definition": PromptDefinition(
                name=name,
                description=description,
                arguments=arguments or [],
            ),
            "handler": handler,
        }
        logger.debug(f"注册 Prompt: {name}")

    def list_prompts(self) -> List[PromptDefinition]:
        """列出所有可用 Prompt"""
        return [p["definition"] for p in self._prompts.values()]

    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[PromptResult]:
        """
        获取 Prompt

        Args:
            name: Prompt 名称
            arguments: 参数字典

        Returns:
            Prompt 结果，不存在则返回 None
        """
        if name not in self._prompts:
            logger.warning(f"未知 Prompt: {name}")
            return None

        prompt_info = self._prompts[name]
        definition = prompt_info["definition"]
        handler = prompt_info["handler"]
        arguments = arguments or {}

        # 验证必填参数
        for arg in definition.arguments:
            if arg.required and arg.name not in arguments:
                logger.error(f"Prompt {name} 缺少必填参数: {arg.name}")
                return None

        try:
            result = await handler(**arguments)
            return result
        except Exception as e:
            logger.exception(f"获取 Prompt {name} 失败")
            return None


class TemplatePromptProvider(BasePromptProvider):
    """
    基于模板的 Prompt 提供者

    支持使用字符串模板定义 Prompt。
    """

    def register_template(
        self,
        name: str,
        description: str,
        template: str,
        role: str = "user",
        arguments: Optional[List[PromptArgument]] = None,
    ) -> None:
        """
        注册模板 Prompt

        Args:
            name: Prompt 名称
            description: Prompt 描述
            template: 模板字符串，使用 {param} 占位符
            role: 消息角色
            arguments: 参数定义列表（自动从模板提取）
        """
        # 自动提取参数
        if arguments is None:
            param_names = re.findall(r'\{(\w+)\}', template)
            arguments = [PromptArgument(name=p, description=p) for p in param_names]

        async def handler(**kwargs) -> PromptResult:
            content = template.format(**kwargs)
            return PromptResult(
                description=description,
                messages=[PromptMessage(role=role, content=content)],
            )

        self.register(name, description, handler, arguments)


class EmptyPromptProvider(BasePromptProvider):
    """空 Prompt 提供者，用于不需要 Prompt 的场景"""

    def list_prompts(self) -> List[PromptDefinition]:
        return []

    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[PromptResult]:
        return None
