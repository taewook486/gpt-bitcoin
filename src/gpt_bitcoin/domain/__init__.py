"""
Domain layer containing core business logic entities and value objects.

This module provides:
- Cryptocurrency and TradingStrategy enums
- UserPreferences and CoinPreference data models
- TradingDecision model
"""

from pydantic import BaseModel, Field
from typing import Literal

from gpt_bitcoin.domain.models.cryptocurrency import Cryptocurrency, TradingStrategy
from gpt_bitcoin.domain.models.user_preferences import (
    CoinPreference,
    CoinPreferenceModel,
    UserPreferences,
    UserPreferencesModel,
    create_default_preferences,
)


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
        btc_avg_buy_price: float = Field(default=1_000_000.0, description="Average BTC buy price")
        btc_krw_price: float = Field(default=1_500_000_000.0, description="BTC/KRW price at execution")
    """

    decision: Literal["buy", "sell", "hold"]
    percentage: float = Field(ge=0, le=100, description="Percentage of balance to trade")
    reason: str = Field(default="", description="Reasoning for the decision")
    timestamp: str | None = None
    roi: float | None = Field(default=None, description="Return on investment percentage")
    btc_balance: float = Field(default=1.0, description="BTC balance at decision time")
    krw_balance: float = Field(default=1_000_000.0, description="KRW balance at decision time")
    btc_avg_buy_price: float = Field(default=1_000_000.0, description="Average BTC buy price")
    btc_krw_price: float = Field(default=1_500_000_000.0, description="BTC/KRW price at execution")


__all__ = [
    "Cryptocurrency",
    "TradingStrategy",
    "CoinPreference",
    "CoinPreferenceModel",
    "UserPreferences",
    "UserPreferencesModel",
    "create_default_preferences",
    "TradingDecision",
]
