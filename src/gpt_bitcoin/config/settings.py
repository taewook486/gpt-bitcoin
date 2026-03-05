"""
Configuration management using pydantic-settings.

This module provides centralized configuration with environment variable support
and validation.
"""


from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from gpt_bitcoin.domain.security import SecuritySettingsModel


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings are validated and type-safe using Pydantic.
    Environment variables are automatically loaded and validated.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown env vars
    )

    # Application
    app_name: str = Field(default="GPT Bitcoin Auto-Trading System")
    app_version: str = Field(default="4.0.0")
    debug: bool = Field(default=False)

    # API Keys
    upbit_access_key: str = Field(..., description="Upbit access key")
    upbit_secret_key: str = Field(..., description="Upbit secret key")
    zhipuai_api_key: str = Field(..., description="ZhipuAI API key")
    serpapi_api_key: str = Field(default="", description="SerpApi API key (optional)")

    # Trading settings
    testnet_mode: bool = Field(
        default=False,
        description="Enable testnet mode (uses MockUpbitClient instead of real API)",
    )
    trading_percentage: float = Field(
        default=100.0,
        ge=0,
        le=100,
        description="Percentage of balance to trade (0-100)",
    )
    min_order_value: float = Field(
        default=5000.0,
        ge=0,
        description="Minimum order value in KRW",
    )

    # Logging settings
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    log_format: str = Field(
        default="console",
        description="Log output format (console, json)",
    )

    # GLM Model Configuration
    glm_text_model: str = Field(
        default="glm-5",
        description="GLM model for text analysis",
    )
    glm_vision_model: str = Field(
        default="glm-4.6v",
        description="GLM model for vision analysis",
    )

    # News settings
    news_query: str = Field(
        default="btc",
        description="Search query for news",
    )
    news_limit: int = Field(
        default=10,
        ge=1,
        description="Number of news articles to fetch",
    )

    # Database settings
    db_path: str = Field(
        default="trading_decisions.sqlite",
        description="Path to SQLite database",
    )

    # Scheduling
    schedule_times: list[str] = Field(
        default=["00:01", "08:01", "16:01"],
        description="Times to run scheduled trading (HH:MM)",
    )

    # Retry settings
    max_retries: int = Field(
        default=5,
        ge=1,
        description="Maximum retry attempts for API calls",
    )
    retry_delay_seconds: int = Field(
        default=5,
        ge=1,
        description="Delay between retry attempts",
    )

    # Security settings (2FA, trading limits)
    security: SecuritySettingsModel = Field(
        default_factory=SecuritySettingsModel,
        description="Security settings for 2FA and trading limits",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR"}
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """
    Get application settings.

    Returns a cached Settings instance.
    Creates a new instance on first call.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> None:
    """
    Reload settings from environment.

    Useful for testing or when environment changes.
    """
    global _settings
    _settings = None
    get_settings()
