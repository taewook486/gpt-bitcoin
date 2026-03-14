"""
Unit tests for UserPreferences and CoinPreference data models.

Tests cover:
- CoinPreference creation and validation
- UserPreferences creation and validation
- Portfolio allocation validation
- Helper functions
"""

import pytest

from gpt_bitcoin.domain.models.cryptocurrency import Cryptocurrency, TradingStrategy
from gpt_bitcoin.domain.models.user_preferences import (
    CoinPreference,
    CoinPreferenceModel,
    UserPreferences,
    UserPreferencesModel,
    create_default_preferences,
)


class TestCoinPreference:
    """Test CoinPreference dataclass."""

    def test_basic_creation(self) -> None:
        """CoinPreference should create with required fields."""
        pref = CoinPreference(
            coin=Cryptocurrency.BTC,
            enabled=True,
            percentage=20.0,
            strategy=TradingStrategy.BALANCED,
        )

        assert pref.coin == Cryptocurrency.BTC
        assert pref.enabled is True
        assert pref.percentage == 20.0
        assert pref.strategy == TradingStrategy.BALANCED

    def test_default_values(self) -> None:
        """CoinPreference should have default values."""
        pref = CoinPreference(coin=Cryptocurrency.ETH)

        assert pref.coin == Cryptocurrency.ETH
        assert pref.enabled is True  # Default
        assert pref.percentage == 20.0  # Default
        assert pref.strategy == TradingStrategy.BALANCED  # Default

    def test_percentage_validation_valid(self) -> None:
        """Percentage validation should accept valid values."""
        # Test boundary values
        for pct in [0.0, 50.0, 100.0]:
            pref = CoinPreference(
                coin=Cryptocurrency.BTC,
                percentage=pct,
            )
            assert pref.percentage == pct

    def test_percentage_validation_invalid_low(self) -> None:
        """Percentage validation should reject values below 0."""
        with pytest.raises(ValueError, match="between 0 and 100"):
            CoinPreference(
                coin=Cryptocurrency.BTC,
                percentage=-1.0,
            )

    def test_percentage_validation_invalid_high(self) -> None:
        """Percentage validation should reject values above 100."""
        with pytest.raises(ValueError, match="between 0 and 100"):
            CoinPreference(
                coin=Cryptocurrency.BTC,
                percentage=101.0,
            )

    def test_disabled_coin(self) -> None:
        """CoinPreference can be disabled."""
        pref = CoinPreference(
            coin=Cryptocurrency.XRP,
            enabled=False,
            percentage=0.0,
        )

        assert pref.enabled is False
        assert pref.percentage == 0.0


class TestCoinPreferenceModel:
    """Test CoinPreference Pydantic model."""

    def test_model_creation(self) -> None:
        """CoinPreferenceModel should create from CoinPreference."""
        pref = CoinPreference(
            coin=Cryptocurrency.SOL,
            enabled=True,
            percentage=30.0,
            strategy=TradingStrategy.AGGRESSIVE,
        )
        model = CoinPreferenceModel.model_validate(vars(pref))

        assert model.coin == Cryptocurrency.SOL
        assert model.enabled is True
        assert model.percentage == 30.0

    def test_model_serialization(self) -> None:
        """CoinPreferenceModel should serialize to dict."""
        pref = CoinPreference(
            coin=Cryptocurrency.ADA,
            enabled=True,
            percentage=15.0,
        )
        model = CoinPreferenceModel.model_validate(vars(pref))
        data = model.model_dump()

        assert data["coin"] == Cryptocurrency.ADA
        assert data["enabled"] is True
        assert data["percentage"] == 15.0


class TestUserPreferences:
    """Test UserPreferences dataclass."""

    def test_basic_creation(self) -> None:
        """UserPreferences should create with required fields."""
        prefs = UserPreferences(
            default_strategy=TradingStrategy.BALANCED,
            coins=[
                CoinPreference(coin=Cryptocurrency.BTC, percentage=50.0),
                CoinPreference(coin=Cryptocurrency.ETH, percentage=50.0),
            ],
            auto_trade=True,
            daily_trading_limit_krw=100000.0,
        )

        assert prefs.default_strategy == TradingStrategy.BALANCED
        assert len(prefs.coins) == 2
        assert prefs.auto_trade is True
        assert prefs.daily_trading_limit_krw == 100000.0

    def test_default_values(self) -> None:
        """UserPreferences should have default values."""
        prefs = UserPreferences(coins=[])

        assert prefs.default_strategy == TradingStrategy.BALANCED
        assert prefs.coins == []
        assert prefs.auto_trade is True
        assert prefs.daily_trading_limit_krw == 100000.0

    def test_portfolio_allocation_valid(self) -> None:
        """Portfolio allocation should sum to 100% for enabled coins."""
        prefs = UserPreferences(
            coins=[
                CoinPreference(coin=Cryptocurrency.BTC, enabled=True, percentage=40.0),
                CoinPreference(coin=Cryptocurrency.ETH, enabled=True, percentage=40.0),
                CoinPreference(coin=Cryptocurrency.SOL, enabled=True, percentage=20.0),
            ],
        )

        # Should not raise - allocation is 100%
        enabled = [c for c in prefs.coins if c.enabled]
        total = sum(c.percentage for c in enabled)
        assert total == 100.0

    def test_portfolio_allocation_invalid(self) -> None:
        """Portfolio allocation should reject non-100% sums."""
        with pytest.raises(ValueError, match="must sum to 100%"):
            UserPreferences(
                coins=[
                    CoinPreference(coin=Cryptocurrency.BTC, enabled=True, percentage=50.0),
                    CoinPreference(coin=Cryptocurrency.ETH, enabled=True, percentage=30.0),
                ],
            )

    def test_portfolio_allocation_disabled_coins(self) -> None:
        """Disabled coins should not count towards allocation."""
        prefs = UserPreferences(
            coins=[
                CoinPreference(coin=Cryptocurrency.BTC, enabled=True, percentage=50.0),
                CoinPreference(coin=Cryptocurrency.ETH, enabled=False, percentage=30.0),
                CoinPreference(coin=Cryptocurrency.SOL, enabled=True, percentage=50.0),
            ],
        )

        # Should be valid - only enabled coins count (50 + 50 = 100)
        enabled = [c for c in prefs.coins if c.enabled]
        total = sum(c.percentage for c in enabled)
        assert total == 100.0

    def test_portfolio_allocation_no_enabled_coins(self) -> None:
        """No enabled coins should be valid."""
        prefs = UserPreferences(
            coins=[
                CoinPreference(coin=Cryptocurrency.BTC, enabled=False, percentage=0.0),
                CoinPreference(coin=Cryptocurrency.ETH, enabled=False, percentage=0.0),
            ],
        )

        # Should be valid - no enabled coins
        enabled = [c for c in prefs.coins if c.enabled]
        assert len(enabled) == 0

    def test_get_coin_preference_existing(self) -> None:
        """get_coin_preference should return preference for existing coin."""
        btc_pref = CoinPreference(
            coin=Cryptocurrency.BTC,
            percentage=100.0,
        )
        prefs = UserPreferences(coins=[btc_pref])

        result = prefs.get_coin_preference(Cryptocurrency.BTC)
        assert result is not None
        assert result.coin == Cryptocurrency.BTC
        assert result.percentage == 100.0

    def test_get_coin_preference_missing(self) -> None:
        """get_coin_preference should return None for missing coin."""
        prefs = UserPreferences(coins=[CoinPreference(coin=Cryptocurrency.BTC, percentage=100.0)])

        result = prefs.get_coin_preference(Cryptocurrency.ETH)
        assert result is None

    def test_get_enabled_coins(self) -> None:
        """get_enabled_coins should return only enabled coins."""
        prefs = UserPreferences(
            coins=[
                CoinPreference(coin=Cryptocurrency.BTC, enabled=True, percentage=50.0),
                CoinPreference(coin=Cryptocurrency.ETH, enabled=False, percentage=0.0),
                CoinPreference(coin=Cryptocurrency.SOL, enabled=True, percentage=50.0),
            ],
        )

        enabled = prefs.get_enabled_coins()
        assert len(enabled) == 2
        assert Cryptocurrency.BTC in enabled
        assert Cryptocurrency.SOL in enabled
        assert Cryptocurrency.ETH not in enabled


class TestUserPreferencesModel:
    """Test UserPreferences Pydantic model."""

    def test_model_creation(self) -> None:
        """UserPreferencesModel should create from UserPreferences."""
        prefs = UserPreferences(
            default_strategy=TradingStrategy.AGGRESSIVE,
            coins=[
                CoinPreference(coin=Cryptocurrency.BTC, percentage=60.0),
                CoinPreference(coin=Cryptocurrency.ETH, percentage=40.0),
            ],
            auto_trade=False,
            daily_trading_limit_krw=200000.0,
        )
        # Convert to dict with nested coin preferences as dicts
        prefs_dict = {
            "default_strategy": prefs.default_strategy,
            "coins": [vars(c) for c in prefs.coins],
            "auto_trade": prefs.auto_trade,
            "daily_trading_limit_krw": prefs.daily_trading_limit_krw,
        }
        model = UserPreferencesModel.model_validate(prefs_dict)

        assert model.default_strategy == TradingStrategy.AGGRESSIVE
        assert len(model.coins) == 2
        assert model.auto_trade is False
        assert model.daily_trading_limit_krw == 200000.0

    def test_model_serialization(self) -> None:
        """UserPreferencesModel should serialize to dict."""
        prefs = UserPreferences(
            coins=[
                CoinPreference(coin=Cryptocurrency.BTC, percentage=100.0),
            ],
        )
        prefs_dict = {
            "default_strategy": prefs.default_strategy,
            "coins": [vars(c) for c in prefs.coins],
            "auto_trade": prefs.auto_trade,
            "daily_trading_limit_krw": prefs.daily_trading_limit_krw,
        }
        model = UserPreferencesModel.model_validate(prefs_dict)
        data = model.model_dump()

        assert data["default_strategy"] == TradingStrategy.BALANCED
        assert data["auto_trade"] is True
        assert len(data["coins"]) == 1


class TestCreateDefaultPreferences:
    """Test create_default_preferences helper function."""

    def test_default_preferences_creation(self) -> None:
        """create_default_preferences should create valid preferences."""
        prefs = create_default_preferences()

        assert prefs.default_strategy == TradingStrategy.BALANCED
        assert len(prefs.coins) == 5
        assert prefs.auto_trade is True
        assert prefs.daily_trading_limit_krw == 100000.0

    def test_default_preferences_equal_allocation(self) -> None:
        """Default preferences should have equal 20% allocation per coin."""
        prefs = create_default_preferences()

        for coin_pref in prefs.coins:
            assert coin_pref.percentage == 20.0
            assert coin_pref.enabled is True
            assert coin_pref.strategy == TradingStrategy.BALANCED

    def test_default_preferences_all_coins_included(self) -> None:
        """Default preferences should include all 5 coins."""
        prefs = create_default_preferences()
        coin_types = {pref.coin for pref in prefs.coins}

        assert coin_types == {
            Cryptocurrency.BTC,
            Cryptocurrency.ETH,
            Cryptocurrency.SOL,
            Cryptocurrency.XRP,
            Cryptocurrency.ADA,
        }

    def test_default_preferences_valid_allocation(self) -> None:
        """Default preferences should have valid 100% allocation."""
        prefs = create_default_preferences()

        # Should not raise - allocation is 100%
        total = sum(c.percentage for c in prefs.coins if c.enabled)
        assert total == 100.0
