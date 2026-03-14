"""
Unit tests for trading strategy selection.

Tests cover:
- Strategy types and parameters
- StrategyManager
- Instruction file loading

These tests follow TDD approach to achieve 85%+ coverage.
"""

from pathlib import Path

from gpt_bitcoin.domain import (
    RiskTolerance,
    StrategyConfig,
    StrategyManager,
    TradingStrategy,
)


class TestTradingStrategy:
    """Test TradingStrategy enum."""

    def test_trading_strategy_is_enum(self):
        """TradingStrategy should be an enum."""
        from enum import Enum

        assert issubclass(TradingStrategy, Enum)

    def test_strategy_types(self):
        """TradingStrategy should have expected types."""
        assert hasattr(TradingStrategy, "conservative")
        assert hasattr(TradingStrategy, "balanced")
        assert hasattr(TradingStrategy, "aggressive")
        assert hasattr(TradingStrategy, "custom")

    def test_strategy_values(self):
        """TradingStrategy values should be strings."""
        assert TradingStrategy.conservative.value == "conservative"
        assert TradingStrategy.balanced.value == "balanced"
        assert TradingStrategy.aggressive.value == "aggressive"


class TestRiskTolerance:
    """Test RiskTolerance enum."""

    def test_risk_tolerance_is_enum(self):
        """RiskTolerance should be an enum."""
        from enum import Enum

        assert issubclass(RiskTolerance, Enum)

    def test_risk_tolerance_types(self):
        """RiskTolerance should have expected types."""
        assert hasattr(RiskTolerance, "conservative")
        assert hasattr(RiskTolerance, "balanced")
        assert hasattr(RiskTolerance, "aggressive")


class TestStrategyConfig:
    """Test StrategyConfig model."""

    def test_default_config(self):
        """StrategyConfig should have sensible defaults."""
        config = StrategyConfig()
        assert config.max_buy_percentage > 0
        assert config.max_sell_percentage > 0
        assert 0 <= config.rsi_oversold <= 100
        assert 0 <= config.rsi_overbought <= 100

    def test_conservative_config(self):
        """StrategyConfig.conservative should return conservative settings."""
        config = StrategyConfig.conservative()

        assert config.max_buy_percentage <= 30  # Conservative buy limit
        assert config.max_sell_percentage <= 50  # Conservative sell limit
        assert config.rsi_oversold < 30  # More oversold for conservative

    def test_aggressive_config(self):
        """StrategyConfig.aggressive should return aggressive settings."""
        config = StrategyConfig.aggressive()

        assert config.max_buy_percentage >= 40  # Higher buy limit
        assert config.max_sell_percentage == 100  # Full sell allowed
        assert config.rsi_overbought >= 70  # Higher threshold

    def test_balanced_config(self):
        """StrategyConfig.balanced should return balanced settings."""
        config = StrategyConfig.balanced()

        # Should be between conservative and aggressive
        assert 20 <= config.max_buy_percentage <= 50
        assert 50 <= config.max_sell_percentage <= 100


class TestStrategyManager:
    """Test StrategyManager class."""

    def test_initialization_default(self):
        """StrategyManager should initialize with default strategy."""
        manager = StrategyManager()
        assert manager.current_strategy is not None

    def test_initialization_with_strategy(self):
        """StrategyManager should accept initial strategy."""
        manager = StrategyManager(strategy=TradingStrategy.aggressive)
        assert manager.current_strategy == TradingStrategy.aggressive

    def test_set_strategy(self):
        """StrategyManager should allow changing strategy."""
        manager = StrategyManager()
        manager.set_strategy(TradingStrategy.conservative)

        assert manager.current_strategy == TradingStrategy.conservative

    def test_get_config(self):
        """StrategyManager should return config for current strategy."""
        manager = StrategyManager(strategy=TradingStrategy.conservative)
        config = manager.get_config()

        assert isinstance(config, StrategyConfig)
        assert config.max_buy_percentage <= 30

    def test_get_config_for_strategy(self):
        """StrategyManager should return config for specific strategy."""
        manager = StrategyManager()
        config = manager.get_config_for_strategy(TradingStrategy.aggressive)

        assert config.max_buy_percentage >= 40

    def test_get_instruction_file(self):
        """StrategyManager should return instruction file path."""
        manager = StrategyManager()
        path = manager.get_instruction_file()

        assert path is not None
        assert isinstance(path, Path | str)

    def test_get_system_prompt(self):
        """StrategyManager should return system prompt for AI."""
        manager = StrategyManager()
        prompt = manager.get_system_prompt()

        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_strategy_from_risk_tolerance(self):
        """StrategyManager should map risk tolerance to strategy."""
        manager = StrategyManager()

        conservative = manager.strategy_from_risk_tolerance(RiskTolerance.conservative)
        aggressive = manager.strategy_from_risk_tolerance(RiskTolerance.aggressive)

        assert conservative == TradingStrategy.conservative
        assert aggressive == TradingStrategy.aggressive
