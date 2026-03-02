"""
Unit tests for configuration module.

Tests cover:
- Settings class
- get_settings function
- reload_settings function
"""

import pytest
from pydantic import ValidationError

from gpt_bitcoin.config import get_settings, reload_settings
from gpt_bitcoin.config.settings import Settings


class TestSettingsClass:
    """Test Settings class."""

    def test_settings_with_required_fields(self, monkeypatch):
        """Settings should initialize with required fields."""
        settings = Settings(
            upbit_access_key="test_access",
            upbit_secret_key="test_secret",
            zhipuai_api_key="test_zhipu",
        )

        assert settings.upbit_access_key == "test_access"
        assert settings.upbit_secret_key == "test_secret"
        assert settings.zhipuai_api_key == "test_zhipu"

    def test_settings_default_values(self, monkeypatch):
        """Settings should have default values."""
        settings = Settings(
            upbit_access_key="test",
            upbit_secret_key="test",
            zhipuai_api_key="test",
        )

        assert settings.trading_percentage == 100.0
        assert settings.log_level == "INFO"
        assert settings.log_format == "console"
        assert settings.glm_text_model == "glm-5"
        assert settings.glm_vision_model == "glm-4.6v"
        assert settings.schedule_times == ["00:01", "08:01", "16:01"]
        assert settings.db_path == "trading_decisions.sqlite"

    def test_trading_percentage_validation(self, monkeypatch):
        """Trading percentage should be between 0 and 100."""
        # Valid values
        for pct in [0, 50, 100]:
            settings = Settings(
                upbit_access_key="test",
                upbit_secret_key="test",
                zhipuai_api_key="test",
                trading_percentage=pct,
            )
            assert settings.trading_percentage == pct

        # Invalid - below 0
        with pytest.raises(ValidationError):
            Settings(
                upbit_access_key="test",
                upbit_secret_key="test",
                zhipuai_api_key="test",
                trading_percentage=-1,
            )

        # Invalid - above 100
        with pytest.raises(ValidationError):
            Settings(
                upbit_access_key="test",
                upbit_secret_key="test",
                zhipuai_api_key="test",
                trading_percentage=101,
            )

    def test_log_level_validation(self, monkeypatch):
        """Log level should be valid."""
        # Valid levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "debug", "info"]:
            settings = Settings(
                upbit_access_key="test",
                upbit_secret_key="test",
                zhipuai_api_key="test",
                log_level=level,
            )
            assert settings.log_level == level

        # Invalid level
        with pytest.raises(ValidationError):
            Settings(
                upbit_access_key="test",
                upbit_secret_key="test",
                zhipuai_api_key="test",
                log_level="INVALID",
            )


class TestSettingsManagement:
    """Test settings management functions."""

    def test_get_settings_returns_settings(self, monkeypatch):
        """get_settings should return a Settings instance."""
        monkeypatch.setenv("UPBIT_ACCESS_KEY", "test_access")
        monkeypatch.setenv("UPBIT_SECRET_KEY", "test_secret")
        monkeypatch.setenv("ZHIPUAI_API_KEY", "test_zhipu")

        reload_settings()
        settings = get_settings()

        # Check type using the actual class from config.settings
        assert type(settings).__name__ == "Settings"
        assert hasattr(settings, "upbit_access_key")

    def test_get_settings_caches_instance(self, monkeypatch):
        """get_settings should cache the instance."""
        monkeypatch.setenv("UPBIT_ACCESS_KEY", "test_access")
        monkeypatch.setenv("UPBIT_SECRET_KEY", "test_secret")
        monkeypatch.setenv("ZHIPUAI_API_KEY", "test_zhipu")

        reload_settings()
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_reload_settings_creates_new_instance(self, monkeypatch):
        """reload_settings should create new instance."""
        monkeypatch.setenv("UPBIT_ACCESS_KEY", "test_access")
        monkeypatch.setenv("UPBIT_SECRET_KEY", "test_secret")
        monkeypatch.setenv("ZHIPUAI_API_KEY", "test_zhipu")

        reload_settings()
        settings1 = get_settings()

        reload_settings()
        settings2 = get_settings()

        # Different instances after reload
        assert settings1 is not settings2
