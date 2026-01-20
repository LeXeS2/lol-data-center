"""Configuration management using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Riot API
    riot_api_key: str = Field(
        default="RGAPI-test-key-not-set",
        description="Riot Games API Key",
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://lol_user:lol_password@localhost:5432/lol_data_center",
        description="PostgreSQL connection string",
    )

    # Discord
    discord_webhook_url: str = Field(
        default="https://discord.com/api/webhooks/not-configured",
        description="Discord webhook URL for notifications",
    )

    # Polling
    polling_interval_seconds: int = Field(
        default=300,
        ge=60,
        description="Interval between polling cycles in seconds",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    # Region
    default_region: str = Field(
        default="europe",
        description="Default routing region for Riot API",
    )

    # Rate Limiting
    rate_limit_requests: int = Field(
        default=100,
        description="Maximum requests per rate limit window",
    )
    rate_limit_window_seconds: int = Field(
        default=120,
        description="Rate limit window in seconds",
    )

    # Paths
    invalid_responses_dir: Path = Field(
        default=Path("data/invalid_responses"),
        description="Directory to store invalid API responses",
    )
    achievements_config_path: Path = Field(
        default=Path("achievements.yaml"),
        description="Path to achievements configuration file",
    )

    @field_validator("invalid_responses_dir", mode="after")
    @classmethod
    def ensure_dir_exists(cls, v: Path) -> Path:
        """Ensure the invalid responses directory exists."""
        v.mkdir(parents=True, exist_ok=True)
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
