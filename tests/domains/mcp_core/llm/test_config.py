"""mcp_core.llm.config 单元测试。"""

import importlib.util
from pathlib import Path


CONFIG_PATH = (
    Path(__file__).resolve().parents[4]
    / "backend"
    / "domains"
    / "mcp_core"
    / "llm"
    / "config.py"
)


def load_llm_settings_class():
    """直接加载 config.py，避免触发 domains.mcp_core 包级副作用。"""
    spec = importlib.util.spec_from_file_location("test_llm_config_module", CONFIG_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.LLMSettings


def test_resolve_config_reads_model_specific_env_overrides(tmp_path, monkeypatch):
    """模型级 endpoint/key 应通过环境变量覆盖。"""
    LLMSettings = load_llm_settings_class()
    yaml_path = tmp_path / "llm_models.yaml"
    yaml_path.write_text(
        """
default:
  model: relay
  timeout: 120

llm_configs:
  relay:
    provider: openai
    model: gpt-5.4
    temperature: 0.3
    max_tokens: 16384
    api_url_env: TEST_RELAY_API_URL
    api_key_env: TEST_RELAY_API_KEY
    http_transport: curl_cffi
    extra_body:
      reasoning:
        effort: high
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setenv("TEST_RELAY_API_URL", "https://relay.example.com/v1")
    monkeypatch.setenv("TEST_RELAY_API_KEY", "secret-key")

    settings = LLMSettings.from_yaml(yaml_path)
    resolved = settings.resolve_config("relay")

    assert resolved["api_url"] == "https://relay.example.com/v1"
    assert resolved["api_key"] == "secret-key"
    assert resolved["http_transport"] == "curl_cffi"
    assert resolved["extra_body"] == {"reasoning": {"effort": "high"}}


def test_resolve_config_keeps_global_credentials_when_model_env_missing(tmp_path, monkeypatch):
    """未配置模型级密钥时，客户端应继续走全局环境变量。"""
    LLMSettings = load_llm_settings_class()
    yaml_path = tmp_path / "llm_models.yaml"
    yaml_path.write_text(
        """
default:
  model: gpt
  timeout: 120

llm_configs:
  gpt:
    provider: openai
    model: gpt-5.2
    temperature: 0.6
    max_tokens: 8192
    api_url_env: MISSING_MODEL_URL
    api_key_env: MISSING_MODEL_KEY
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setenv("LLM_API_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("LLM_API_KEY", "global-key")
    monkeypatch.delenv("MISSING_MODEL_URL", raising=False)
    monkeypatch.delenv("MISSING_MODEL_KEY", raising=False)

    settings = LLMSettings.from_yaml(yaml_path)
    resolved = settings.resolve_config("gpt")

    assert settings.api_url == "https://api.openai.com/v1"
    assert settings.api_key == "global-key"
    assert resolved["api_url"] is None
    assert resolved["api_key"] is None
    assert resolved["http_transport"] == "default"
