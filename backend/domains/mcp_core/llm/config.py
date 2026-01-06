"""
LLM 配置管理

从 config/llm_models.yaml 加载配置，支持:
- 默认模型配置
- 多模型定义
- 运行时参数覆盖

配置文件路径通过函数参数传入，不硬编码业务路径。
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelConfig(BaseModel):
    """单个模型配置"""

    provider: str = "openai"
    model: str = "gpt-4"
    temperature: float = 0.6
    max_tokens: int = 8192


class LLMSettings(BaseSettings):
    """
    LLM 配置 (pydantic-settings)

    环境变量:
    - LLM_API_URL: API 端点
    - LLM_API_KEY: API 密钥
    """

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        extra="ignore",
    )

    # 环境变量配置
    api_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias="LLM_API_URL",
    )
    api_key: str = Field(
        default="",
        validation_alias="LLM_API_KEY",
    )

    # 运行时配置 (从 yaml 加载)
    default_model: str = "gpt"
    timeout: int = 120
    models: Dict[str, ModelConfig] = Field(default_factory=dict)

    @classmethod
    def from_yaml(cls, yaml_path: Optional[Path] = None) -> "LLMSettings":
        """
        从 yaml 文件加载配置

        Args:
            yaml_path: YAML 配置文件路径，None 则使用默认路径
        """
        if yaml_path is None:
            # 默认路径: 项目根目录/config/llm_models.yaml
            current = Path(__file__).resolve()
            # backend/domains/mcp_core/llm/config.py -> 项目根目录
            project_root = current.parent.parent.parent.parent.parent
            yaml_path = project_root / "config" / "llm_models.yaml"

        if not yaml_path.exists():
            return cls()

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        default = data.get("default", {})
        llm_configs = data.get("llm_configs", {})

        models = {name: ModelConfig(**config) for name, config in llm_configs.items()}

        return cls(
            default_model=default.get("model", "gpt"),
            timeout=default.get("timeout", 120),
            models=models,
        )

    def get_model_config(self, model_key: Optional[str] = None) -> ModelConfig:
        """
        获取模型配置

        Args:
            model_key: 模型 key (如 "claude", "gpt")，None 则使用默认

        Returns:
            ModelConfig 实例
        """
        key = model_key or self.default_model
        return self.models.get(key, ModelConfig())

    def resolve_config(
        self,
        model_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        解析最终配置 (支持覆盖)

        优先级: 参数传入 > 模型配置 > 默认值

        Args:
            model_key: 模型 key
            temperature: 温度参数覆盖
            max_tokens: max_tokens 覆盖

        Returns:
            最终配置字典，包含 model, temperature, max_tokens
        """
        base = self.get_model_config(model_key)
        return {
            "model": base.model,
            "temperature": temperature if temperature is not None else base.temperature,
            "max_tokens": max_tokens if max_tokens is not None else base.max_tokens,
        }


# 全局配置实例
_llm_settings: Optional[LLMSettings] = None


def get_llm_settings(yaml_path: Optional[Path] = None) -> LLMSettings:
    """
    获取 LLM 配置单例

    首次调用时从 yaml 加载配置，后续调用返回缓存的实例。
    """
    global _llm_settings
    if _llm_settings is None:
        _llm_settings = LLMSettings.from_yaml(yaml_path)
    return _llm_settings


def reload_llm_settings(yaml_path: Optional[Path] = None) -> LLMSettings:
    """
    重新加载配置

    清除缓存并重新加载。
    """
    global _llm_settings
    _llm_settings = LLMSettings.from_yaml(yaml_path)
    return _llm_settings
