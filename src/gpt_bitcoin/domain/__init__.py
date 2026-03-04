"""
Domain layer containing core business logic entities and value objects.

"""

from typing import Literal
from enum import Enum

from pydantic import BaseModel, Field


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
    conservative = "conservative"
    balanced = "balanced"
    aggressive = "aggressive"
    custom = "custom"


class RiskTolerance(str, Enum):
    """Risk tolerance levels for portfolio management."""
    conservative = "conservative"
    balanced = "balanced"
    aggressive = "aggressive"


class TradingDecision(BaseModel):
    """
    AI-generated trading decision.

    Attributes:
        decision: Trading action - buy, sell, or hold
        percentage: Percentage of balance to trade
        reason: Reasoning for the decision
        timestamp: ISO timestamp of the decision
        roi: Return on investment percentage
        btc_balance: BTC balance at decision time
        krw_balance: KRW balance at decision time
        btc_avg_buy_price: Average BTC buy price
        btc_krw_price: BTC/KRW price at execution
    """

    decision: Literal["buy", "sell", "hold"]
    percentage: float = Field(ge=0, le=100, description="Percentage of balance to trade")
    reason: str = Field(default="", description="Reasoning for the decision")
    timestamp: str | None = None
    roi: float | None = Field(default=None, description="Return on investment percentage")
    btc_balance: float = Field(default=0.0, description="BTC balance at decision time")
    krw_balance: float = Field(default=0_000_000.0, description="KRW balance at decision time")
    btc_avg_buy_price: float = Field(default=0_000_000.0, description="Average BTC buy price")
    btc_krw_price: float = Field(default=0_500_000_000.0, description="BTC/KRW price at execution")
