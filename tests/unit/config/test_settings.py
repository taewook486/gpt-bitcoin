"""
Unit tests for configuration settings.

Tests cover:
- Settings validation
- Field validators
- Default values
"""

import pytest
from pydantic import ValidationError

from gpt_bitcoin.config.settings import Settings


class TestSettings:
    """Test Settings class."""

    def test_required_fields_from_env(self, monkeypatch):
        """Settings should load required fields from environment."""
        # Set required env vars
        monkeypatch.setenv("UPBIT_ACCESS_KEY", "env_access")
        monkeypatch.setenv("UPBIT_SECRET_KEY", "env_secret")
        monkeypatch.setenv("ZHIPUAI_API_KEY", "env_zhipu")

        settings = Settings()

        assert settings.upbit_access_key == "env_access"
        assert settings.upbit_secret_key == "env_secret"
        assert settings.zhipuai_api_key == "env_zhipu"

    def test_with_required_fields(self, monkeypatch):
        """Settings should initialize with required fields."""
        settings = Settings(
            upbit_access_key="test_access",
            upbit_secret_key="test_secret",
            zhipuai_api_key="test_zhipu",
        )

        assert settings.upbit_access_key == "test_access"
        assert settings.upbit_secret_key == "test_secret"
        assert settings.zhipuai_api_key == "test_zhipu"

    def test_default_values(self, monkeypatch):
        """Settings should have sensible defaults."""
        settings = Settings(
            upbit_access_key="test",
            upbit_secret_key="test",
            zhipuai_api_key="test",
        )

        assert settings.app_name == "GPT Bitcoin Auto-Trading System"
        assert settings.app_version == "4.0.0"
        assert settings.debug is False
        assert settings.trading_percentage == 100.0
        assert settings.min_order_value == 5000.0
        assert settings.log_level == "INFO"
        assert settings.log_format == "console"
        assert settings.glm_text_model == "glm-5"
        assert settings.glm_vision_model == "glm-4.6v"
        assert settings.news_query == "btc"
        assert settings.news_limit == 10
        assert settings.db_path == "trading_decisions.sqlite"
        assert settings.max_retries == 5
        assert settings.retry_delay_seconds == 5

    def test_trading_percentage_validation(self, monkeypatch):
        """Trading percentage should be between 0 and 100."""
        # Valid values
        settings = Settings(
            upbit_access_key="test",
            upbit_secret_key="test",
            zhipuai_api_key="test",
            trading_percentage=50.0,
        )
        assert settings.trading_percentage == 50.0

        # Invalid - below 0
        with pytest.raises(ValidationError):
            Settings(
                upbit_access_key="test",
                upbit_secret_key="test",
                zhipuai_api_key="test",
                trading_percentage=-10.0,
            )

        # Invalid - above 100
        with pytest.raises(ValidationError):
            Settings(
                upbit_access_key="test",
                upbit_secret_key="test",
                zhipuai_api_key="test",
                trading_percentage=150.0,
            )

    def test_min_order_value_validation(self, monkeypatch):
        """Min order value should be >= 0."""
        # Valid value
        settings = Settings(
            upbit_access_key="test",
            upbit_secret_key="test",
            zhipuai_api_key="test",
            min_order_value=10000.0,
        )
        assert settings.min_order_value == 10000.0

        # Invalid - below 0
        with pytest.raises(ValidationError):
            Settings(
                upbit_access_key="test",
                upbit_secret_key="test",
                zhipuai_api_key="test",
                min_order_value=-100.0,
            )

    def test_log_level_validator(self, monkeypatch):
        """Log level should be valid."""
        # Valid levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            settings = Settings(
                upbit_access_key="test",
                upbit_secret_key="test",
                zhipuai_api_key="test",
                log_level=level,
            )
            assert settings.log_level == level

        # Case insensitive
        settings = Settings(
            upbit_access_key="test",
            upbit_secret_key="test",
            zhipuai_api_key="test",
            log_level="debug",
        )
        assert settings.log_level == "debug"

        # Invalid level
        with pytest.raises(ValidationError, match="log_level must be one of"):
            Settings(
                upbit_access_key="test",
                upbit_secret_key="test",
                zhipuai_api_key="test",
                log_level="INVALID",
            )

    def test_news_limit_validation(self, monkeypatch):
        """News limit should be >= 1."""
        # Valid value
        settings = Settings(
            upbit_access_key="test",
            upbit_secret_key="test",
            zhipuai_api_key="test",
            news_limit=20,
        )
        assert settings.news_limit == 20

        # Invalid - below 1
        with pytest.raises(ValidationError):
            Settings(
                upbit_access_key="test",
                upbit_secret_key="test",
                zhipuai_api_key="test",
                news_limit=0,
            )

    def test_max_retries_validation(self, monkeypatch):
        """Max retries should be >= 1."""
        # Valid value
        settings = Settings(
            upbit_access_key="test",
            upbit_secret_key="test",
            zhipuai_api_key="test",
            max_retries=10,
        )
        assert settings.max_retries == 10

        # Invalid - below 1
        with pytest.raises(ValidationError):
            Settings(
                upbit_access_key="test",
                upbit_secret_key="test",
                zhipuai_api_key="test",
                max_retries=0,
            )

    def test_retry_delay_validation(self, monkeypatch):
        """Retry delay should be >= 1."""
        # Valid value
        settings = Settings(
            upbit_access_key="test",
            upbit_secret_key="test",
            zhipuai_api_key="test",
            retry_delay_seconds=10,
        )
        assert settings.retry_delay_seconds == 10

        # Invalid - below 1
        with pytest.raises(ValidationError):
            Settings(
                upbit_access_key="test",
                upbit_secret_key="test",
                zhipuai_api_key="test",
                retry_delay_seconds=0,
            )

    def test_schedule_times_default(self, monkeypatch):
        """Schedule times should have default values."""
        settings = Settings(
            upbit_access_key="test",
            upbit_secret_key="test",
            zhipuai_api_key="test",
        )

        assert settings.schedule_times == ["00:01", "08:01", "16:01"]

    def test_serpapi_can_be_set(self, monkeypatch):
        """SerpApi key can be set explicitly."""
        settings_with_serpapi = Settings(
            upbit_access_key="test",
            upbit_secret_key="test",
            zhipuai_api_key="test",
            serpapi_api_key="custom_serpapi",
        )

        assert settings_with_serpapi.serpapi_api_key == "custom_serpapi"


class TestGetSettingsAndReload:
    """Test get_settings and reload_settings functions - covers lines 129-131, 141-142."""

    def setup_method(self):
        """Reset settings before each test."""
        from gpt_bitcoin.config.settings import reload_settings

        reload_settings()

    def teardown_method(self):
        """Clean up after each test."""
        from gpt_bitcoin.config.settings import reload_settings

        reload_settings()

    def test_get_settings_returns_singleton(self, monkeypatch):
        """get_settings should return the same instance."""
        from gpt_bitcoin.config.settings import get_settings

        monkeypatch.setenv("UPBIT_ACCESS_KEY", "test_access")
        monkeypatch.setenv("UPBIT_SECRET_KEY", "test_secret")
        monkeypatch.setenv("ZHIPUAI_API_KEY", "test_zhipu")

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_reload_settings_creates_new_instance(self, monkeypatch):
        """reload_settings should create a new Settings instance."""
        from gpt_bitcoin.config.settings import get_settings, reload_settings

        monkeypatch.setenv("UPBIT_ACCESS_KEY", "test_access")
        monkeypatch.setenv("UPBIT_SECRET_KEY", "test_secret")
        monkeypatch.setenv("ZHIPUAI_API_KEY", "test_zhipu")

        settings1 = get_settings()

        reload_settings()
        settings2 = get_settings()

        # Should be different instances after reload
        assert settings1 is not settings2

    def test_reload_settings_loads_from_env(self, monkeypatch):
        """reload_settings should reload from environment."""
        from gpt_bitcoin.config import settings as settings_module
        from gpt_bitcoin.config.settings import get_settings

        # Clear any cached settings first and set module-level variable
        settings_module._settings = None

        monkeypatch.setenv("UPBIT_ACCESS_KEY", "first_access")
        monkeypatch.setenv("UPBIT_SECRET_KEY", "first_secret")
        monkeypatch.setenv("ZHIPUAI_API_KEY", "first_zhipu")

        settings1 = get_settings()
        assert settings1.upbit_access_key == "first_access"

        # Change environment
        monkeypatch.setenv("UPBIT_ACCESS_KEY", "second_access")

        # Clear cache and reload
        settings_module._settings = None
        settings2 = get_settings()

        assert settings2.upbit_access_key == "second_access"
