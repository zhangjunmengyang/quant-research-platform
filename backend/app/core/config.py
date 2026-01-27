"""Application configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # 忽略 .env 中的额外变量
    )

    # Project info
    PROJECT_NAME: str = "Quant Platform API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    # Paths (relative to project root)
    # NOTE: 因子路径请使用 domains.mcp_core.paths.get_factors_dir()
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent.parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    FACTORS_DIR: Path = PROJECT_ROOT / "private" / "factors"
    CONFIG_DIR: Path = PROJECT_ROOT / "config"

    # MCP settings
    MCP_FACTOR_HUB_PORT: int = 6789
    MCP_DATA_HUB_PORT: int = 6790
    MCP_STRATEGY_HUB_PORT: int = 6791


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
