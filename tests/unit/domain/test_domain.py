"""
Unit tests for domain layer models.

Tests cover:
- Cryptocurrency enum
- TradingStrategy enum
- RiskTolerance enum
- TradingDecision model validation

These tests follow TDD approach to achieve 85%+ coverage.
"""

import pytest
from pydantic import ValidationError

from gpt_bitcoin.domain import (
    Cryptocurrency,
    TradingStrategy,
    RiskTolerance,
    TradingDecision,
)


class TestCryptocurrency:
    """Test Cryptocurrency enum."""

    def test_btc_value(self):
        """BTC should have KRW-BTC value."""
        assert Cryptocurrency.BTC.value == "KRW-BTC"

    def test_eth_value(self):
        """ETH should have KRW-ETH value."""
        assert Cryptocurrency.ETH.value == "KRW-ETH"

    def test_sol_value(self):
        """SOL should have KRW-SOL value."""
        assert Cryptocurrency.SOL.value == "KRW-SOL"

    def test_xrp_value(self):
        """XRP should have KRW-XRP value."""
        assert Cryptocurrency.XRP.value == "KRW-XRP"

    def test_ada_value(self):
        """ADA should have KRW-ADA value."""
        assert Cryptocurrency.ADA.value == "KRW-ADA"

    def test_doge_value(self):
        """DOGE should have KRW-DOGE value."""
        assert Cryptocurrency.DOGE.value == "KRW-DOGE"

    def test_avax_value(self):
        """AVAX should have KRW-AVAX value."""
        assert Cryptocurrency.AVAX.value == "KRW-AVAX"

    def test_dot_value(self):
        """DOT should have KRW-DOT value."""
        assert Cryptocurrency.DOT.value == "KRW-DOT"

    def test_all_coins_count(self):
        """Should have 8 supported coins."""
        assert len(Cryptocurrency) == 8

    def test_is_string_enum(self):
        """Cryptocurrency should be a string enum."""
        assert isinstance(Cryptocurrency.BTC, str)
        assert Cryptocurrency.BTC == "KRW-BTC"


class TestTradingStrategy:
    """Test TradingStrategy enum."""

    def test_conservative_value(self):
        """Conservative strategy should have correct value."""
        assert TradingStrategy.conservative.value == "conservative"

    def test_balanced_value(self):
        """Balanced strategy should have correct value."""
        assert TradingStrategy.balanced.value == "balanced"

    def test_aggressive_value(self):
        """Aggressive strategy should have correct value."""
        assert TradingStrategy.aggressive.value == "aggressive"

    def test_custom_value(self):
        """Custom strategy should have correct value."""
        assert TradingStrategy.custom.value == "custom"

    def test_all_strategies_count(self):
        """Should have 4 strategy types."""
        assert len(TradingStrategy) == 4


class TestRiskTolerance:
    """Test RiskTolerance enum."""

    def test_conservative_value(self):
        """Conservative risk tolerance should have correct value."""
        assert RiskTolerance.conservative.value == "conservative"

    def test_balanced_value(self):
        """Balanced risk tolerance should have correct value."""
        assert RiskTolerance.balanced.value == "balanced"

    def test_aggressive_value(self):
        """Aggressive risk tolerance should have correct value."""
        assert RiskTolerance.aggressive.value == "aggressive"

    def test_all_risk_levels_count(self):
        """Should have 3 risk levels."""
        assert len(RiskTolerance) == 3


class TestTradingDecision:
    """Test TradingDecision model."""

    def test_valid_buy_decision(self):
        """Should accept valid buy decision."""
        decision = TradingDecision(
            decision="buy",
            percentage=50.0,
            reason="Market looking bullish",
        )
        assert decision.decision == "buy"
        assert decision.percentage == 50.0
        assert decision.reason == "Market looking bullish"

    def test_valid_sell_decision(self):
        """Should accept valid sell decision."""
        decision = TradingDecision(
            decision="sell",
            percentage=100.0,
            reason="Taking profit",
        )
        assert decision.decision == "sell"
        assert decision.percentage == 100.0

    def test_valid_hold_decision(self):
        """Should accept valid hold decision."""
        decision = TradingDecision(
            decision="hold",
            percentage=0.0,
            reason="Waiting for signal",
        )
        assert decision.decision == "hold"
        assert decision.percentage == 0.0

    def test_percentage_bounds_lower(self):
        """Percentage must be >= 0."""
        with pytest.raises(ValidationError):
            TradingDecision(
                decision="buy",
                percentage=-10.0,
            )

    def test_percentage_bounds_upper(self):
        """Percentage must be <= 100."""
        with pytest.raises(ValidationError):
            TradingDecision(
                decision="buy",
                percentage=150.0,
            )

    def test_default_values(self):
        """Should have sensible defaults for optional fields."""
        decision = TradingDecision(decision="hold", percentage=0.0)
        assert decision.percentage == 0.0
        assert decision.reason == ""
        assert decision.timestamp is None
        assert decision.roi is None
        assert decision.btc_balance == 0.0
        assert decision.krw_balance == 0_000_000.0
        assert decision.btc_avg_buy_price == 0_000_000.0
        assert decision.btc_krw_price == 0_500_000_000.0

    def test_with_all_fields(self):
        """Should accept all optional fields."""
        decision = TradingDecision(
            decision="sell",
            percentage=75.0,
            reason="Taking profit at target",
            timestamp="2024-01-15T08:01:00",
            roi=15.5,
            btc_balance=0.05,
            krw_balance=500000.0,
            btc_avg_buy_price=50000000.0,
            btc_krw_price=55000000.0,
        )
        assert decision.timestamp == "2024-01-15T08:01:00"
        assert decision.roi == 15.5
        assert decision.btc_balance == 0.05
        assert decision.krw_balance == 500000.0
        assert decision.btc_avg_buy_price == 50000000.0
        assert decision.btc_krw_price == 55000000.0

    def test_invalid_decision_value(self):
        """Should reject invalid decision values."""
        with pytest.raises(ValidationError):
            TradingDecision(
                decision="invalid",  # Not buy, sell, or hold
                percentage=50.0,
            )

    def test_zero_percentage_allowed(self):
        """Zero percentage should be allowed (for hold)."""
        decision = TradingDecision(decision="hold", percentage=0)
        assert decision.percentage == 0

    def test_hundred_percentage_allowed(self):
        """100% percentage should be allowed (for full sell)."""
        decision = TradingDecision(decision="sell", percentage=100)
        assert decision.percentage == 100

    def test_decimal_percentage_allowed(self):
        """Decimal percentages should be allowed."""
        decision = TradingDecision(decision="buy", percentage=33.33)
        assert decision.percentage == 33.33

    def test_model_serialization(self):
        """Should serialize to dict correctly."""
        decision = TradingDecision(
            decision="buy",
            percentage=50.0,
            reason="Test",
        )
        data = decision.model_dump()
        assert data["decision"] == "buy"
        assert data["percentage"] == 50.0
        assert data["reason"] == "Test"

    def test_model_json_serialization(self):
        """Should serialize to JSON correctly."""
        decision = TradingDecision(
            decision="buy",
            percentage=50.0,
            reason="Test",
        )
        json_str = decision.model_dump_json()
        assert '"decision":"buy"' in json_str
        assert '"percentage":50.0' in json_str
