"""
Tests for TestnetConfig module (SPEC-TRADING-005).

This test module covers:
- TestnetConfig validation
- MockBalance management
- TradingMode enum

@MX:NOTE: Test-first approach - RED phase before implementation.
"""

from __future__ import annotations

import pytest

from gpt_bitcoin.domain.testnet_config import TestnetConfig, MockBalance
from gpt_bitcoin.domain.trading_mode import TradingMode


class TestTestnetConfigEdgeCases:
    """Additional edge case tests for TestnetConfig."""

    def test_config_with_zero_balance(self) -> None:
        """Test config with zero initial balance (edge case)."""
        config = TestnetConfig(initial_krw_balance=0.0)
        assert config.initial_krw_balance == 0.0

    def test_config_with_zero_fee_rate(self) -> None:
        """Test config with zero fee rate (edge case)."""
        config = TestnetConfig(simulated_fee_rate=0.0)
        assert config.simulated_fee_rate == 0.0

    def test_config_model_dump(self) -> None:
        """Test config serialization."""
        config = TestnetConfig(
            initial_krw_balance=5_000_000.0,
            simulated_fee_rate=0.001,
            db_path="custom.db",
        )
        data = config.model_dump()

        assert data["initial_krw_balance"] == 5_000_000.0
        assert data["simulated_fee_rate"] == 0.001
        assert data["db_path"] == "custom.db"

    def test_config_model_dump_roundtrip(self) -> None:
        """Test config serialization roundtrip."""
        original = TestnetConfig(
            initial_krw_balance=15_000_000.0,
            simulated_fee_rate=0.0003,
        )
        data = original.model_dump()
        restored = TestnetConfig(**data)

        assert restored.initial_krw_balance == original.initial_krw_balance
        assert restored.simulated_fee_rate == original.simulated_fee_rate


class TestMockBalanceEdgeCases:
    """Additional edge case tests for MockBalance."""

    def test_balance_with_zero_krw(self) -> None:
        """Test balance with zero KRW."""
        balance = MockBalance(krw_balance=0.0)
        assert balance.krw_balance == 0.0

    def test_balance_with_multiple_coins(self) -> None:
        """Test balance with multiple coin types."""
        balance = MockBalance(
            krw_balance=10_000_000.0,
            coin_balances={
                "BTC": 0.001,
                "ETH": 0.01,
                "SOL": 1.0,
            },
            avg_buy_prices={
                "BTC": 50_000_000.0,
                "ETH": 3_000_000.0,
                "SOL": 150_000.0,
            },
        )

        assert len(balance.coin_balances) == 3
        assert balance.coin_balances["BTC"] == 0.001
        assert balance.avg_buy_prices["BTC"] == 50_000_000.0


class TestTradingModeEdgeCases:
    """Additional edge case tests for TradingMode."""

    def test_trading_mode_comparison(self) -> None:
        """Test TradingMode enum comparison."""
        assert TradingMode.PRODUCTION == TradingMode.PRODUCTION
        assert TradingMode.PRODUCTION != TradingMode.TESTNET

    def test_trading_mode_iteration(self) -> None:
        """Test iterating over TradingMode values."""
        modes = list(TradingMode)
        assert len(modes) == 2
        assert TradingMode.PRODUCTION in modes
        assert TradingMode.TESTNET in modes

    def test_trading_mode_string_conversion(self) -> None:
        """Test converting string to TradingMode."""
        assert TradingMode("production") == TradingMode.PRODUCTION
        assert TradingMode("testnet") == TradingMode.TESTNET
