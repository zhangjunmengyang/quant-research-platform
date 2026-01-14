"""
配置加载器 - 加载 llm_models.yaml 和 prompts/*.yaml

支持从 config/ 目录加载配置文件。
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from domains.mcp_core.paths import get_project_root, get_config_dir, get_factors_dir, get_data_dir


# 加载项目根目录的 .env 文件
load_dotenv(get_project_root() / '.env')


class ConfigLoader:
    """
    配置加载器

    负责加载用户变量和 Prompt 配置文件。
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置加载器

        Args:
            config_dir: 配置文件目录，默认为项目根目录下的 config/
        """
        if config_dir is None:
            config_dir = get_config_dir()
        self.config_dir = Path(config_dir)
        self.prompts_dir = self.config_dir / "prompts"
        self.llm_models_path = self.config_dir / "llm_models.yaml"

        # 数据目录
        self.data_dir = get_data_dir()

        # 缓存
        self._llm_models: Optional[Dict[str, Any]] = None
        self._prompts: Dict[str, Dict[str, Any]] = {}

    def load_llm_models(self, reload: bool = False) -> Dict[str, Any]:
        """
        加载 LLM 模型配置

        Args:
            reload: 是否强制重新加载

        Returns:
            LLM 模型配置字典
        """
        if self._llm_models is not None and not reload:
            return self._llm_models

        if not self.llm_models_path.exists():
            self._llm_models = {}
            return self._llm_models

        with open(self.llm_models_path, 'r', encoding='utf-8') as f:
            self._llm_models = yaml.safe_load(f) or {}

        return self._llm_models

    # 兼容旧接口
    def load_user_vars(self, reload: bool = False) -> Dict[str, Any]:
        """兼容旧接口，返回 LLM 模型配置"""
        return self.load_llm_models(reload)

    def load_prompt(self, task_name: str, reload: bool = False) -> Dict[str, Any]:
        """
        加载指定任务的 Prompt 配置

        Args:
            task_name: 任务名称 (如 "score", "review")
            reload: 是否强制重新加载

        Returns:
            Prompt 配置字典
        """
        if task_name in self._prompts and not reload:
            return self._prompts[task_name]

        prompt_path = self.prompts_dir / f"{task_name}.yaml"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt 配置文件不存在: {prompt_path}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_config = yaml.safe_load(f) or {}

        self._prompts[task_name] = prompt_config
        return prompt_config

    def load_field_prompt(self, field_name: str, reload: bool = False) -> Dict[str, Any]:
        """
        加载字段填充的 Prompt 配置

        Args:
            field_name: 字段名称 (如 "style", "analysis")
            reload: 是否强制重新加载

        Returns:
            Prompt 配置字典
        """
        cache_key = f"fields/{field_name}"
        if cache_key in self._prompts and not reload:
            return self._prompts[cache_key]

        prompt_path = self.prompts_dir / "fields" / f"{field_name}.yaml"
        if not prompt_path.exists():
            raise FileNotFoundError(f"字段 Prompt 配置文件不存在: {prompt_path}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_config = yaml.safe_load(f) or {}

        self._prompts[cache_key] = prompt_config
        return prompt_config

    def load_all_prompts(self, reload: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        加载所有 Prompt 配置

        Args:
            reload: 是否强制重新加载

        Returns:
            {task_name: prompt_config} 字典
        """
        if not self.prompts_dir.exists():
            return {}

        for prompt_file in self.prompts_dir.glob("*.yaml"):
            task_name = prompt_file.stem
            if task_name not in self._prompts or reload:
                self.load_prompt(task_name, reload=reload)

        return self._prompts

    def get_api_config(self, task_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取 API 配置

        Args:
            task_name: 任务名称（如 review, generate_analysis），用于加载任务特定的模型配置

        Returns:
            API 配置字典，包含 model, max_tokens, temperature, url, key 等

        优先级：
            1. 任务 prompt yaml 的 model 配置
            2. llm_models.yaml 中对应模型的配置
            3. llm_models.yaml 的 default 配置
        """
        llm_models = self.load_llm_models()
        default_config = llm_models.get('default', {})
        llm_configs = llm_models.get('llm_configs', {})

        # 默认模型
        default_model_name = default_config.get('model', 'gpt')
        default_model_config = llm_configs.get(default_model_name, {})

        # 基础配置
        base_config = {
            'model': default_model_config.get('model', 'gpt-4'),
            'max_tokens': default_model_config.get('max_tokens', 8192),
            'temperature': default_model_config.get('temperature', 0.6),
            'timeout': default_config.get('timeout', 120),
            'concurrency': default_config.get('concurrency', 3),
            'url': os.environ.get('LLM_API_URL', 'https://api.openai.com/v1/chat/completions'),
            'key': os.environ.get('LLM_API_KEY', ''),
        }

        # 如果指定了任务名称，尝试加载任务特定配置
        if task_name:
            task_config = self.load_prompt(task_name)
            if task_config:
                model_config = task_config.get('model', {})
                if model_config:
                    # 如果任务指定了模型 key，获取该模型的配置
                    task_model_name = model_config.get('name', '')
                    if task_model_name and task_model_name in llm_configs:
                        task_model_config = llm_configs[task_model_name]
                        base_config['model'] = task_model_config.get('model', base_config['model'])
                        base_config['max_tokens'] = task_model_config.get('max_tokens', base_config['max_tokens'])
                        base_config['temperature'] = task_model_config.get('temperature', base_config['temperature'])

                    # 任务配置中的 temperature/max_tokens 最高优先级
                    if model_config.get('temperature') is not None:
                        base_config['temperature'] = model_config['temperature']
                    if model_config.get('max_tokens') is not None:
                        base_config['max_tokens'] = model_config['max_tokens']

        return base_config

    @property
    def project_root(self) -> Path:
        """获取项目根目录"""
        return get_project_root()

    @property
    def factors_dir(self) -> Path:
        """获取因子代码目录"""
        return get_factors_dir()


# 单例实例
_config_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """获取配置加载器单例"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def reset_config_loader():
    """重置配置加载器单例（用于测试）"""
    global _config_loader
    _config_loader = None
