"""
Unit tests for multi-coin support.

Tests cover:
- Cryptocurrency enum
- User preferences
- Coin manager

These tests follow TDD approach to achieve 85%+ coverage.
"""

import pytest
from enum import Enum

from gpt_bitcoin.domain import (
    Cryptocurrency,
    UserPreferences,
    CoinManager,
)


class TestCryptocurrency:
    """Test Cryptocurrency enum."""

    def test_cryptocurrency_is_enum(self):
        """Cryptocurrency should be an enum."""
        assert issubclass(Cryptocurrency, Enum)

    def test_supported_coins(self):
        """Cryptocurrency should include supported coins."""
        assert hasattr(Cryptocurrency, "BTC")
        assert hasattr(Cryptocurrency, "ETH")
        assert hasattr(Cryptocurrency, "SOL")
        assert hasattr(Cryptocurrency, "XRP")
        assert hasattr(Cryptocurrency, "ADA")
        assert hasattr(Cryptocurrency, "DOGE")
        assert hasattr(Cryptocurrency, "AVAX")
        assert hasattr(Cryptocurrency, "DOT")

    def test_cryptocurrency_values_are_upbit_tickers(self):
        """Cryptocurrency values should be Upbit ticker format."""
        assert Cryptocurrency.BTC.value == "KRW-BTC"
        assert Cryptocurrency.ETH.value == "KRW-ETH"
        assert Cryptocurrency.SOL.value == "KRW-SOL"

    def test_cryptocurrency_from_string(self):
        """Cryptocurrency should be creatable from string."""
        btc = Cryptocurrency("KRW-BTC")
        assert btc == Cryptocurrency.BTC


class TestUserPreferences:
    """Test UserPreferences model."""

    def test_default_selected_coin(self):
        """UserPreferences should default to BTC."""
        prefs = UserPreferences()
        assert prefs.selected_coin == Cryptocurrency.BTC

    def test_custom_selected_coin(self):
        """UserPreferences should accept custom coin."""
        prefs = UserPreferences(selected_coin=Cryptocurrency.ETH)
        assert prefs.selected_coin == Cryptocurrency.ETH

    def test_risk_tolerance_default(self):
        """UserPreferences should default to balanced risk tolerance."""
        prefs = UserPreferences()
        assert prefs.risk_tolerance == "balanced"

    def test_risk_tolerance_values(self):
        """UserPreferences should accept valid risk tolerance values."""
        conservative = UserPreferences(risk_tolerance="conservative")
        aggressive = UserPreferences(risk_tolerance="aggressive")

        assert conservative.risk_tolerance == "conservative"
        assert aggressive.risk_tolerance == "aggressive"

    def test_selected_coin_can_be_changed(self):
        """UserPreferences selected_coin should be mutable."""
        prefs = UserPreferences()
        prefs.selected_coin = Cryptocurrency.SOL

        assert prefs.selected_coin == Cryptocurrency.SOL


class TestCoinManager:
    """Test CoinManager class."""

    def test_coin_manager_initialization(self):
        """CoinManager should initialize with default preferences."""
        manager = CoinManager()
        assert manager.preferences is not None

    def test_coin_manager_with_custom_preferences(self):
        """CoinManager should accept custom preferences."""
        prefs = UserPreferences(selected_coin=Cryptocurrency.ETH)
        manager = CoinManager(preferences=prefs)

        assert manager.preferences.selected_coin == Cryptocurrency.ETH

    def test_get_current_coin(self):
        """CoinManager should return current selected coin."""
        manager = CoinManager()
        coin = manager.get_current_coin()

        assert coin == Cryptocurrency.BTC

    def test_set_coin(self):
        """CoinManager should allow changing coin."""
        manager = CoinManager()
        manager.set_coin(Cryptocurrency.SOL)

        assert manager.get_current_coin() == Cryptocurrency.SOL

    def test_get_ticker(self):
        """CoinManager should return Upbit ticker for current coin."""
        manager = CoinManager()
        ticker = manager.get_ticker()

        assert ticker == "KRW-BTC"

    def test_get_ticker_for_coin(self):
        """CoinManager should return ticker for specific coin."""
        manager = CoinManager()
        ticker = manager.get_ticker_for_coin(Cryptocurrency.ETH)

        assert ticker == "KRW-ETH"

    def test_get_supported_coins(self):
        """CoinManager should return list of supported coins."""
        manager = CoinManager()
        coins = manager.get_supported_coins()

        assert Cryptocurrency.BTC in coins
        assert Cryptocurrency.ETH in coins
        assert len(coins) >= 8  # At least 8 coins per SPEC

    def test_is_coin_supported(self):
        """CoinManager should check if coin is supported."""
        manager = CoinManager()

        assert manager.is_coin_supported(Cryptocurrency.BTC) is True
        assert manager.is_coin_supported(Cryptocurrency.ETH) is True

    def test_coin_info(self):
        """CoinManager should return coin information."""
        manager = CoinManager()
        info = manager.get_coin_info(Cryptocurrency.BTC)

        assert info is not None
        assert "name" in info
        assert "ticker" in info
