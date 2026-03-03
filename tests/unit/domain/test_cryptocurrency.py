"""
Unit tests for Cryptocurrency and TradingStrategy enums.

Tests cover:
- Enum values and properties
- Upbit ticker generation
- Korean display names
- Instruction file paths
"""

import pytest

from gpt_bitcoin.domain.models.cryptocurrency import Cryptocurrency, TradingStrategy


class TestCryptocurrencyEnum:
    """Test Cryptocurrency enum values and properties."""

    def test_enum_values(self) -> None:
        """Cryptocurrency enum should have correct values."""
        assert Cryptocurrency.BTC.value == "BTC"
        assert Cryptocurrency.ETH.value == "ETH"
        assert Cryptocurrency.SOL.value == "SOL"
        assert Cryptocurrency.XRP.value == "XRP"
        assert Cryptocurrency.ADA.value == "ADA"

    def test_enum_count(self) -> None:
        """Should have exactly 5 cryptocurrencies."""
        assert len(Cryptocurrency) == 5

    def test_upbit_ticker_btc(self) -> None:
        """BTC upbit ticker should be BTC-KRW."""
        assert Cryptocurrency.BTC.upbit_ticker == "BTC-KRW"

    def test_upbit_ticker_eth(self) -> None:
        """ETH upbit ticker should be ETH-KRW."""
        assert Cryptocurrency.ETH.upbit_ticker == "ETH-KRW"

    def test_upbit_ticker_sol(self) -> None:
        """SOL upbit ticker should be SOL-KRW."""
        assert Cryptocurrency.SOL.upbit_ticker == "SOL-KRW"

    def test_upbit_ticker_xrp(self) -> None:
        """XRP upbit ticker should be XRP-KRW."""
        assert Cryptocurrency.XRP.upbit_ticker == "XRP-KRW"

    def test_upbit_ticker_ada(self) -> None:
        """ADA upbit ticker should be ADA-KRW."""
        assert Cryptocurrency.ADA.upbit_ticker == "ADA-KRW"

    def test_display_name_btc(self) -> None:
        """BTC display name should be Korean."""
        assert Cryptocurrency.BTC.display_name == "비트코인"

    def test_display_name_eth(self) -> None:
        """ETH display name should be Korean."""
        assert Cryptocurrency.ETH.display_name == "이더리움"

    def test_display_name_sol(self) -> None:
        """SOL display name should be Korean."""
        assert Cryptocurrency.SOL.display_name == "솔라나"

    def test_display_name_xrp(self) -> None:
        """XRP display name should be Korean."""
        assert Cryptocurrency.XRP.display_name == "리플"

    def test_display_name_ada(self) -> None:
        """ADA display name should be Korean."""
        assert Cryptocurrency.ADA.display_name == "에이다"

    def test_string_conversion(self) -> None:
        """Enum should convert to string properly."""
        assert str(Cryptocurrency.BTC) == "Cryptocurrency.BTC"
        assert f"{Cryptocurrency.ETH.value}" == "ETH"

    def test_enum_comparison(self) -> None:
        """Enum should support equality comparison."""
        assert Cryptocurrency.BTC == Cryptocurrency.BTC
        assert Cryptocurrency.BTC != Cryptocurrency.ETH

    def test_enum_from_string(self) -> None:
        """Should create enum from string value."""
        assert Cryptocurrency("BTC") == Cryptocurrency.BTC
        assert Cryptocurrency("ETH") == Cryptocurrency.ETH


class TestTradingStrategyEnum:
    """Test TradingStrategy enum values and properties."""

    def test_enum_values(self) -> None:
        """TradingStrategy enum should have correct values."""
        assert TradingStrategy.CONSERVATIVE.value == "conservative"
        assert TradingStrategy.BALANCED.value == "balanced"
        assert TradingStrategy.AGGRESSIVE.value == "aggressive"
        assert TradingStrategy.VISION_AGGRESSIVE.value == "vision_aggressive"

    def test_enum_count(self) -> None:
        """Should have exactly 4 strategies."""
        assert len(TradingStrategy) == 4

    def test_instruction_file_conservative(self) -> None:
        """Conservative instruction file path."""
        assert TradingStrategy.CONSERVATIVE.instruction_file == "instructions/current/conservative.md"

    def test_instruction_file_balanced(self) -> None:
        """Balanced instruction file path."""
        assert TradingStrategy.BALANCED.instruction_file == "instructions/current/balanced.md"

    def test_instruction_file_aggressive(self) -> None:
        """Aggressive instruction file path."""
        assert TradingStrategy.AGGRESSIVE.instruction_file == "instructions/current/aggressive.md"

    def test_instruction_file_vision_aggressive(self) -> None:
        """Vision aggressive instruction file path."""
        expected = "instructions/current/vision_aggressive.md"
        assert TradingStrategy.VISION_AGGRESSIVE.instruction_file == expected

    def test_display_name_conservative(self) -> None:
        """Conservative display name should be Korean."""
        assert TradingStrategy.CONSERVATIVE.display_name == "보수적"

    def test_display_name_balanced(self) -> None:
        """Balanced display name should be Korean."""
        assert TradingStrategy.BALANCED.display_name == "균형적"

    def test_display_name_aggressive(self) -> None:
        """Aggressive display name should be Korean."""
        assert TradingStrategy.AGGRESSIVE.display_name == "공격적"

    def test_display_name_vision_aggressive(self) -> None:
        """Vision aggressive display name should be Korean."""
        assert TradingStrategy.VISION_AGGRESSIVE.display_name == "비전 공격적"

    def test_string_conversion(self) -> None:
        """Enum should convert to string properly."""
        assert str(TradingStrategy.BALANCED) == "TradingStrategy.BALANCED"
        assert f"{TradingStrategy.AGGRESSIVE.value}" == "aggressive"

    def test_enum_comparison(self) -> None:
        """Enum should support equality comparison."""
        assert TradingStrategy.BALANCED == TradingStrategy.BALANCED
        assert TradingStrategy.CONSERVATIVE != TradingStrategy.AGGRESSIVE

    def test_enum_from_string(self) -> None:
        """Should create enum from string value."""
        assert TradingStrategy("conservative") == TradingStrategy.CONSERVATIVE
        assert TradingStrategy("balanced") == TradingStrategy.BALANCED
