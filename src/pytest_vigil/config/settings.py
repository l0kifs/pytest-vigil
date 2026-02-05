from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Configuration settings for pytest-vigil.
    
    Values can be overridden by environment variables with PYTEST_VIGIL__ prefix.
    e.g. PYTEST_VIGIL__TIMEOUT=5.0
    """
    model_config = SettingsConfigDict(
        env_prefix="PYTEST_VIGIL__",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = Field(default="pytest-vigil", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")

    # Default global limits (if not specified via CLI or Marker)
    timeout: Optional[float] = Field(
        default=None,
        description="Default timeout in seconds for tests. Can be overridden by CLI or marker."
    )
    memory_limit_mb: Optional[float] = Field(
        default=None,
        description="Default memory limit in megabytes for tests. Can be overridden by CLI or marker."
    )
    cpu_limit_percent: Optional[float] = Field(
        default=None,
        description="Default CPU limit as a percentage for tests. Can be overridden by CLI or marker."
    )
    
    # Internal monitoring configuration
    monitor_interval: float = Field(
        default=0.1,
        description="Interval in seconds for internal monitoring checks."
    )
    strict_mode: bool = Field(
        default=True,
        description="Whether to enforce strict mode for monitoring."
    )


def get_settings() -> Settings:
    """Retrieve application settings."""
    return Settings()
