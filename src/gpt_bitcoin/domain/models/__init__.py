"""
Domain models package containing core business entities and value objects.

This package provides:
- Cryptocurrency and TradingStrategy enums
- UserPreferences and CoinPreference data models
"""

from gpt_bitcoin.domain.models.cryptocurrency import (
    Cryptocurrency,
    TradingStrategy,
)
from gpt_bitcoin.domain.models.user_preferences import (
    CoinPreference,
    CoinPreferenceModel,
    UserPreferences,
    UserPreferencesModel,
    create_default_preferences,
)

__all__ = [
    "Cryptocurrency",
    "TradingStrategy",
    "CoinPreference",
    "CoinPreferenceModel",
    "UserPreferences",
    "UserPreferencesModel",
    "create_default_preferences",
]
