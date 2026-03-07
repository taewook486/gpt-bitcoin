"""
Unit tests for TradingMode enum and testnet configuration.

Tests cover:
- TradingMode enum values
- TestnetConfig model validation
- MockBalance dataclass behavior
- Mode switching behavior

@MX:NOTE: Testnet 환경 설정 테스트 - TDD RED Phase
"""

from __future__ import annotations

import pytest

from gpt_bitcoin.domain.testnet_config import MockBalance, TestnetConfig
from gpt_bitcoin.domain.trading_mode import TradingMode


# =============================================================================
# TradingMode Enum Tests
# =============================================================================


class TestTradingMode:
    """Tests for TradingMode enum."""

    def test_trading_mode_production_value(self):
        """Test PRODUCTION mode has correct value."""
        assert TradingMode.PRODUCTION == "production"

    def test_trading_mode_testnet_value(self):
        """Test TESTNET mode has correct value."""
        assert TradingMode.TESTNET == "testnet"

    def test_trading_mode_values_are_strings(self):
        """Test all TradingMode values are strings."""
        assert isinstance(TradingMode.PRODUCTION.value, str)
        assert isinstance(TradingMode.TESTNET.value, str)


# =============================================================================
# TestnetConfig Tests
# =============================================================================


class TestTestnetConfig:
    """Tests for TestnetConfig model."""

    def test_default_initial_balance(self):
        """Test default initial KRW balance is 10,000,000."""
        config = TestnetConfig()
        assert config.initial_krw_balance == 10_000_000.0

    def test_default_fee_rate(self):
        """Test default simulated fee rate is 0.05%."""
        config = TestnetConfig()
        assert config.simulated_fee_rate == 0.0005

    def test_default_db_path(self):
        """Test default database path is testnet_trades.db."""
        config = TestnetConfig()
        assert config.db_path == "testnet_trades.db"

    def test_custom_initial_balance(self):
        """Test custom initial balance can be set."""
        config = TestnetConfig(initial_krw_balance=5_000_000.0)
        assert config.initial_krw_balance == 5_000_000.0

    def test_custom_fee_rate(self):
        """Test custom fee rate can be set."""
        config = TestnetConfig(simulated_fee_rate=0.001)
        assert config.simulated_fee_rate == 0.001

    def test_custom_db_path(self):
        """Test custom database path can be set."""
        config = TestnetConfig(db_path="custom_testnet.db")
        assert config.db_path == "custom_testnet.db"

    def test_config_validation_rejects_negative_balance(self):
        """Test config validation rejects negative initial balance."""
        with pytest.raises(ValueError):
            TestnetConfig(initial_krw_balance=-1000.0)

    def test_config_validation_rejects_negative_fee(self):
        """Test config validation rejects negative fee rate."""
        with pytest.raises(ValueError):
            TestnetConfig(simulated_fee_rate=-0.001)


# =============================================================================
# MockBalance Tests
# =============================================================================


class TestMockBalance:
    """Tests for MockBalance dataclass."""

    def test_default_krw_balance(self):
        """Test default KRW balance is 10,000,000."""
        balance = MockBalance()
        assert balance.krw_balance == 10_000_000.0

    def test_default_coin_balances_is_empty_dict(self):
        """Test default coin balances is empty dict."""
        balance = MockBalance()
        assert balance.coin_balances == {}

    def test_default_avg_buy_prices_is_empty_dict(self):
        """Test default avg buy prices is empty dict."""
        balance = MockBalance()
        assert balance.avg_buy_prices == {}

    def test_custom_krw_balance(self):
        """Test custom KRW balance can be set."""
        balance = MockBalance(krw_balance=5_000_000.0)
        assert balance.krw_balance == 5_000_000.0

    def test_custom_coin_balances(self):
        """Test custom coin balances can be set."""
        balance = MockBalance(coin_balances={"BTC": 0.5, "ETH": 10.0})
        assert balance.coin_balances == {"BTC": 0.5, "ETH": 10.0}

    def test_custom_avg_buy_prices(self):
        """Test custom avg buy prices can be set."""
        balance = MockBalance(avg_buy_prices={"BTC": 50_000_000.0})
        assert balance.avg_buy_prices == {"BTC": 50_000_000.0}
