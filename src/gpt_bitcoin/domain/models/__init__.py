"""
Domain models package containing core business entities and value objects.

This package provides:
- Cryptocurrency and TradingStrategy enums
- UserPreferences and CoinPreference data models
- ChartAnalysis and CombinedAnalysis for Vision API
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
from gpt_bitcoin.domain.models.chart_analysis import (
    ChartAnalysis,
    ChartPattern,
    CombinedAnalysis,
    Sentiment,
    Trend,
)

__all__ = [
    "Cryptocurrency",
    "TradingStrategy",
    "CoinPreference",
    "CoinPreferenceModel",
    "UserPreferences",
    "UserPreferencesModel",
    "create_default_preferences",
    "ChartAnalysis",
    "ChartPattern",
    "CombinedAnalysis",
    "Sentiment",
    "Trend",
]
