from typing import Optional, Literal

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
    app_version: str = Field(default="0.7.1", description="Application version")

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
    
    # Advanced features
    ci_multiplier: float = Field(
        default=2.0,
        description="Multiplier for resource limits when running in CI environment."
    )
    retry_count: int = Field(
        default=0,
        description="Number of retries for failed/violation tests. 0 means disabled."
    )
    stall_timeout: Optional[float] = Field(
        default=None,
        description="Timeout in seconds for low request/cpu activity to detect deadlocks."
    )
    stall_cpu_threshold: float = Field(
        default=1.0,
        description="CPU percentage threshold below which is considered 'stalled' if exceeded stall_timeout."
    )
    
    # Session-level timeout
    session_timeout: Optional[float] = Field(
        default=None,
        description="Global timeout in seconds for the entire test run session. If exceeded, pytest-vigil will terminate the test run."
    )
    session_timeout_grace_period: float = Field(
        default=5.0,
        description="Grace period in seconds after session timeout before forcefully killing the test run."
    )

    # Force-exit escalation
    force_exit_delay: Optional[float] = Field(
        default=None,
        description=(
            "If set, start an escalation timer when a soft interrupt is sent. "
            "If the test does not respond within this many seconds — for example "
            "because it is stuck in a GIL-holding C extension — call os._exit(124) "
            "to force-terminate the process. Disabled by default (None)."
        ),
    )
    
    # Reporting
    console_report_verbosity: Literal["none", "short", "full"] = Field(
        default="short",
        description="Control terminal report display: 'none' (no report), 'short' (summary stats), 'full' (all tests)."
    )
    json_report_filename: str = Field(
        default="vigil_report.json",
        description="Default JSON report filename when report saving is enabled."
    )
    json_report: bool = Field(
        default=False,
        description="Enable JSON report saving by default."
    )
    artifacts_dir: str = Field(
        default=".pytest_vigil",
        description="Default directory where plugin-generated artifacts are stored."
    )


def get_settings() -> Settings:
    """Retrieve application settings."""
    return Settings()
