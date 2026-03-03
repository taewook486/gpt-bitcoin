"""
Cryptocurrency and trading strategy enums for multi-coin support.

This module provides enum types for supported cryptocurrencies and trading strategies,
along with properties for display names and ticker symbols.
"""

from enum import Enum
from typing import Final


class Cryptocurrency(str, Enum):
    """
    Supported cryptocurrencies for trading.

    Each cryptocurrency has an associated Upbit ticker and Korean display name.

    Attributes:
        BTC: Bitcoin
        ETH: Ethereum
        SOL: Solana
        XRP: Ripple
        ADA: Cardano
    """

    BTC = "BTC"
    ETH = "ETH"
    SOL = "SOL"
    XRP = "XRP"
    ADA = "ADA"

    @property
    def upbit_ticker(self) -> str:
        """
        Get Upbit ticker symbol.

        Returns:
            Upbit ticker in format "{COIN}-KRW" (e.g., "BTC-KRW")

        @MX:NOTE This property provides the Upbit API-compatible ticker format.
        """
        return f"{self.value}-KRW"

    @property
    def display_name(self) -> str:
        """
        Get display name in Korean.

        Returns:
            Korean display name for the cryptocurrency

        @MX:NOTE Korean display names are used in UI presentation layer.
        """
        names: Final[dict[str, str]] = {
            "BTC": "비트코인",
            "ETH": "이더리움",
            "SOL": "솔라나",
            "XRP": "리플",
            "ADA": "에이다",
        }
        return names[self.value]


class TradingStrategy(str, Enum):
    """
    Available trading strategies.

    Each strategy has an associated instruction file and Korean display name.

    Attributes:
        CONSERVATIVE: Low risk, steady growth strategy (new)
        BALANCED: v1-based balanced strategy
        AGGRESSIVE: v2-based aggressive strategy with fear/greed index
        VISION_AGGRESSIVE: v3-based vision + ROI strategy
    """

    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    VISION_AGGRESSIVE = "vision_aggressive"

    @property
    def instruction_file(self) -> str:
        """
        Get instruction file path for this strategy.

        Returns:
            Relative path to the instruction file

        @MX:NOTE Instruction files are stored in instructions/current/ directory.
        """
        return f"instructions/current/{self.value}.md"

    @property
    def display_name(self) -> str:
        """
        Get display name in Korean.

        Returns:
            Korean display name for the strategy

        @MX:NOTE Korean display names are used in UI strategy selection dropdowns.
        """
        names: Final[dict[str, str]] = {
            "conservative": "보수적",
            "balanced": "균형적",
            "aggressive": "공격적",
            "vision_aggressive": "비전 공격적",
        }
        return names[self.value]


__all__ = ["Cryptocurrency", "TradingStrategy"]
