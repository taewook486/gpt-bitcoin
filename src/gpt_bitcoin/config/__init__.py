"""
Configuration management using pydantic-settings.

This module provides centralized configuration with environment variable support
and validation.
"""

from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        extra="ignore",
    )

    # API Keys
    upbit_access_key: str = Field(..., description="Upbit API access key")
    upbit_secret_key: str = Field(..., description="Upbit API secret key")
    zhipuai_api_key: str = Field(..., description="ZhipuAI API key for GLM models")
    serpapi_api_key: str = Field(default="", description="SerpApi key for news data")

    # Trading Configuration
    trading_percentage: float = Field(
        default=100.0,
        ge=0,
        le=100,
        description="Percentage of balance to trade (0-100)",
    )
    min_order_value_krw: float = Field(
        default=5000.0,
        gt=0,
        description="Minimum order value in KRW",
    )

    # Logging Configuration
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

    # Scheduling Configuration
    schedule_times: list[str] = Field(
        default=["00:01", "08:01", "16:01"],
        description="Times to run scheduled trading (HH:MM format)",
    )

    # Database Configuration
    db_path: str = Field(
        default="trading_decisions.sqlite",
        description="Path to SQLite database file",
    )

    @field_validator("trading_percentage")
    @classmethod
    def validate_trading_percentage(cls, v: float) -> float:
        if not 0 <= v <= 100:
            raise ValueError("trading_percentage must be between 0 and 100")
        return v

    @field_validator("min_order_value_krw")
    @classmethod
    def validate_min_order_value(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("min_order_value_krw must be positive")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR"}
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v


# Global settings instance
# In production, this would be managed via dependency injection
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
