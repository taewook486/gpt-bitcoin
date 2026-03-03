"""
User preferences for multi-coin trading configuration.

This module provides data models for managing user preferences including:
- Coin preferences with allocation percentages
- Default trading strategy
- Trading limits
"""

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from gpt_bitcoin.domain.models.cryptocurrency import Cryptocurrency, TradingStrategy


@dataclass
class CoinPreference:
    """
    User preference for a specific coin.

    Attributes:
        coin: The cryptocurrency
        enabled: Whether trading is enabled for this coin
        percentage: Portfolio allocation percentage (0-100)
        strategy: Trading strategy to use for this coin

    @MX:NOTE Percentage validation ensures portfolio allocation sums to 100% total
    """

    coin: Cryptocurrency
    enabled: bool = True
    percentage: float = field(default=20.0)
    strategy: TradingStrategy = field(default_factory=lambda: TradingStrategy.BALANCED)

    def __post_init__(self) -> None:
        """Validate percentage is within bounds after initialization."""
        if not 0.0 <= self.percentage <= 100.0:
            raise ValueError(
                f"Percentage must be between 0 and 100, got {self.percentage}"
            )


class CoinPreferenceModel(BaseModel):
    """
    Pydantic model for coin preference validation.

    Used for API serialization and deserialization.
    """

    coin: Cryptocurrency
    enabled: bool = True
    percentage: float = Field(default=20.0, ge=0.0, le=100.0)
    strategy: TradingStrategy = TradingStrategy.BALANCED


@dataclass
class UserPreferences:
    """
    User trading preferences.

    Attributes:
        default_strategy: Default strategy for coins without specific strategy
        coins: List of coin preferences
        auto_trade: Whether auto-trading is enabled
        daily_trading_limit_krw: Maximum daily trading amount in KRW

    @MX:NOTE Portfolio allocation must sum to 100% for enabled coins
    """

    default_strategy: TradingStrategy = field(default_factory=lambda: TradingStrategy.BALANCED)
    coins: list[CoinPreference] = field(default_factory=list)
    auto_trade: bool = True
    daily_trading_limit_krw: float = 100000.0

    def __post_init__(self) -> None:
        """Validate portfolio allocation after initialization."""
        self._validate_allocation()

    def _validate_allocation(self) -> None:
        """
        Validate that enabled coin percentages sum to 100%.

        Raises:
            ValueError: If allocation doesn't sum to 100% for enabled coins
        """
        enabled_coins = [c for c in self.coins if c.enabled]
        if not enabled_coins:
            return  # No enabled coins is valid

        total = sum(c.percentage for c in enabled_coins)
        if abs(total - 100.0) > 0.01:  # Allow small floating point errors
            raise ValueError(
                f"Portfolio allocation must sum to 100%, got {total:.2f}%"
            )

    def get_coin_preference(
        self, coin: Cryptocurrency
    ) -> CoinPreference | None:
        """
        Get preference for a specific coin.

        Args:
            coin: The cryptocurrency to get preference for

        Returns:
            CoinPreference if found, None otherwise
        """
        for pref in self.coins:
            if pref.coin == coin:
                return pref
        return None

    def get_enabled_coins(self) -> list[Cryptocurrency]:
        """
        Get list of enabled coins.

        Returns:
            List of enabled cryptocurrencies
        """
        return [c.coin for c in self.coins if c.enabled]


class UserPreferencesModel(BaseModel):
    """
    Pydantic model for user preferences validation.

    Used for API serialization and deserialization.
    """

    default_strategy: TradingStrategy = TradingStrategy.BALANCED
    coins: list[CoinPreferenceModel] = []
    auto_trade: bool = True
    daily_trading_limit_krw: float = Field(default=100000.0, ge=0.0)

    @model_validator(mode="after")
    def validate_allocation(self) -> "UserPreferencesModel":
        """Validate that portfolio allocation sums to 100%."""
        enabled_coins = [c for c in self.coins if c.enabled]
        if not enabled_coins:
            return self

        total = sum(c.percentage for c in enabled_coins)
        if abs(total - 100.0) > 0.01:
            raise ValueError(
                f"Portfolio allocation must sum to 100%, got {total:.2f}%"
            )

        return self

    def get_coin_preference(
        self, coin: Cryptocurrency
    ) -> CoinPreferenceModel | None:
        """Get preference for a specific coin."""
        for pref in self.coins:
            if pref.coin == coin:
                return pref
        return None

    def get_enabled_coins(self) -> list[Cryptocurrency]:
        """Get list of enabled coins."""
        return [c.coin for c in self.coins if c.enabled]


def create_default_preferences() -> UserPreferences:
    """
    Create default user preferences with equal allocation.

    Returns:
        UserPreferences with all coins enabled and equal 20% allocation
    """
    coins = [
        CoinPreference(
            coin=coin,
            enabled=True,
            percentage=20.0,
            strategy=TradingStrategy.BALANCED,
        )
        for coin in Cryptocurrency
    ]
    return UserPreferences(
        default_strategy=TradingStrategy.BALANCED,
        coins=coins,
        auto_trade=True,
        daily_trading_limit_krw=100000.0,
    )


__all__ = [
    "CoinPreference",
    "CoinPreferenceModel",
    "UserPreferences",
    "UserPreferencesModel",
    "create_default_preferences",
]
