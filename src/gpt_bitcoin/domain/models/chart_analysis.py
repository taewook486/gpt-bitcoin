"""
Chart analysis domain model for GLM-4.6V Vision API.

This module provides structured output schema for vision-based chart analysis,
including pattern recognition, trend analysis, and sentiment assessment.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ChartPattern(str, Enum):
    """
    Recognized chart patterns from vision analysis.

    @MX:NOTE Common candlestick patterns for technical analysis.
    """

    # Bullish patterns
    HAMMER = "Hammer"
    INVERTED_HAMMER = "Inverted Hammer"
    BULLISH_ENGULFING = "Bullish Engulfing"
    PIERCING_LINE = "Piercing Line"
    MORNING_STAR = "Morning Star"
    THREE_WHITE_SOLDIERS = "Three White Soldiers"

    # Bearish patterns
    HANGING_MAN = "Hanging Man"
    SHOOTING_STAR = "Shooting Star"
    BEARISH_ENGULFING = "Bearish Engulfing"
    DARK_CLOUD_COVER = "Dark Cloud Cover"
    EVENING_STAR = "Evening Star"
    THREE_BLACK_CROWS = "Three Black Crows"

    # Neutral/continuation patterns
    DOJI = "Doji"
    SPINNING_TOP = "Spinning Top"
    MARUBOZU = "Marubozu"

    # Chart patterns
    DOUBLE_TOP = "Double Top"
    DOUBLE_BOTTOM = "Double Bottom"
    HEAD_AND_SHOULDERS = "Head and Shoulders"
    INVERSE_HEAD_AND_SHOULDERS = "Inverse Head and Shoulders"
    TRIANGLE = "Triangle"
    FLAG = "Flag"
    WEDGE = "Wedge"

    UNKNOWN = "Unknown"


class Trend(str, Enum):
    """
    Market trend direction.

    @MX:NOTE Primary trend classifications for market direction.
    """

    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    SIDEWAYS = "sideways"


class Sentiment(str, Enum):
    """
    Market sentiment assessment.

    @MX:NOTE Overall market sentiment derived from chart patterns.
    """

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class ChartAnalysis:
    """
    Structured output schema for GLM-4.6V Vision API analysis.

    This model captures the vision-based analysis of cryptocurrency charts,
    including pattern recognition, trend identification, and sentiment analysis.

    Attributes:
        patterns: List of recognized chart patterns
        trend: Overall market trend direction
        support_levels: Identified support price levels
        resistance_levels: Identified resistance price levels
        sentiment: Overall market sentiment
        confidence: Confidence score (0.0-1.0)
        raw_response: Full Vision API response for debugging

    @MX:ANCHOR Vision analysis output contract - used by VisionAnalyzer
    """

    patterns: list[str] = field(default_factory=list)
    trend: Trend = field(default=Trend.SIDEWAYS)
    support_levels: list[float] = field(default_factory=list)
    resistance_levels: list[float] = field(default_factory=list)
    sentiment: Sentiment = field(default=Sentiment.NEUTRAL)
    confidence: float = field(default=0.5, metadata={"ge": 0.0, "le": 1.0})
    raw_response: str = field(default="")
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate confidence range after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation of chart analysis

        @MX:NOTE Used for logging and API responses.
        """
        return {
            "patterns": self.patterns,
            "trend": self.trend.value,
            "support_levels": self.support_levels,
            "resistance_levels": self.resistance_levels,
            "sentiment": self.sentiment.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_vision_response(cls, response: str) -> "ChartAnalysis":
        """
        Parse Vision API response into structured ChartAnalysis.

        Args:
            response: Raw JSON response from GLM-4.6V Vision API

        Returns:
            ChartAnalysis instance with parsed data

        Raises:
            ValueError: If response cannot be parsed

        @MX:NOTE Vision API returns structured JSON with pattern analysis.
        """
        import json

        try:
            data = json.loads(response)

            # Parse patterns
            patterns = []
            if "patterns" in data:
                patterns = [
                    p.get("name", "Unknown") if isinstance(p, dict) else str(p)
                    for p in data["patterns"]
                ]

            # Parse trend
            trend_str = data.get("trend", "sideways").lower()
            try:
                trend = Trend(trend_str)
            except ValueError:
                trend = Trend.SIDEWAYS

            # Parse support and resistance levels
            support_levels = [float(s) for s in data.get("support_levels", [])]
            resistance_levels = [float(r) for r in data.get("resistance_levels", [])]

            # Parse sentiment
            sentiment_str = data.get("sentiment", "neutral").lower()
            try:
                sentiment = Sentiment(sentiment_str)
            except ValueError:
                sentiment = Sentiment.NEUTRAL

            # Parse confidence
            confidence = float(data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))

            return cls(
                patterns=patterns,
                trend=trend,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
                sentiment=sentiment,
                confidence=confidence,
                raw_response=response,
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise ValueError(f"Failed to parse vision response: {e}") from e


@dataclass
class CombinedAnalysis:
    """
    Combined Vision + Text analysis for enhanced decision making.

    This model merges vision-based chart pattern recognition with
    text-based technical indicator analysis for more robust signals.

    Attributes:
        vision: Vision-based chart analysis
        technical_indicators: Text-based technical analysis
        combined_sentiment: Merged sentiment from both sources
        combined_confidence: Weighted confidence score
        signal_strength: Strong/medium/weak based on agreement
        agreement: Whether vision and text signals agree

    @MX:ANCHOR Combined analysis output - used by trading strategy
    """

    vision: ChartAnalysis
    technical_indicators: dict[str, Any] = field(default_factory=dict)
    combined_sentiment: Sentiment = field(default=Sentiment.NEUTRAL)
    combined_confidence: float = field(default=0.5, metadata={"ge": 0.0, "le": 1.0})
    signal_strength: str = field(default="weak")
    agreement: bool = field(default=False)
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate confidence range after initialization."""
        if not 0.0 <= self.combined_confidence <= 1.0:
            raise ValueError(
                f"Combined confidence must be between 0.0 and 1.0, got {self.combined_confidence}"
            )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation of combined analysis

        @MX:NOTE Used for logging and API responses.
        """
        return {
            "vision": self.vision.to_dict(),
            "technical_indicators": self.technical_indicators,
            "combined_sentiment": self.combined_sentiment.value,
            "combined_confidence": self.combined_confidence,
            "signal_strength": self.signal_strength,
            "agreement": self.agreement,
            "timestamp": self.timestamp.isoformat(),
        }


__all__ = [
    "ChartAnalysis",
    "ChartPattern",
    "CombinedAnalysis",
    "Sentiment",
    "Trend",
]
