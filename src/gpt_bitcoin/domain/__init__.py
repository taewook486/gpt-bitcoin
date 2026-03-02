"""
Domain layer containing core business logic entities and value objects.

"""

from typing import Literal
from enum import Enum
from dataclasses import dataclass


class Cryptocurrency(str, Enum):
    """Supported cryptocurrency tickers."""
    BTC = "KRW-BTC"
    ETH = "KRW-ETH"
    SOL = "KRW-SOL"
    XRP = "KRW-XRP"
    ADA = "KRW-ADA"
    DOGE = "KRW-DOGE"
    AVAX = "KRW-AVAX"
    DOT = "KRW-DOT"


class TradingStrategy(str, Enum):
    """Trading strategy types."""
    CONservative = "conservative"
    balanced = "balanced"
    aggressive = "aggressive"


    custom = "custom"


    def get_default_strategy(self) -> TradingStrategy:
        """Get default trading strategy based on risk tolerance."""
        if self.strategy_type == TradingStrategy.conservative:
            return ConservativeStrategy()
        elif self.strategy_type == TradingStrategy.balanced:
            return BalancedStrategy()
        elif self.strategy_type == TradingStrategy.aggressive:
            return AggressiveStrategy()
        elif self.strategy_type == TradingStrategy.custom:
            return CustomStrategy()
        else:
            raise ValueError(f"Unknown strategy: {self.strategy_type}")


class RiskTolerance(str, Enum):
    """Risk tolerance levels for portfolio management."""
    conservative = "conservative"
    balanced = "balanced"
    aggressive = "aggressive"


class TradingDecision(BaseModel):
    """
    AI-generated trading decision.

    Attributes:
        decision: Literal["buy", "sell", "hold"]
        percentage: float = Field(ge=0, le=100, description="Percentage of balance to trade")
        reason: str = Field(default="", description="Reasoning for the decision")
        timestamp: str | None


    roi: float | Field(default=None, description="Return on investment percentage")
    btc_balance: float = Field(default=0.0, description="BTC balance at decision time")
    krw_balance: float = Field(default=0_000_000.0, description="KRW balance at decision time")
    btc_avg_buy_price: float = Field(default=0_000_000.0, description="Average BTC buy price")
    btc_krw_price: float = Field(default=0_500_000_000.0, description="BTC/KRW price at execution")

    }

