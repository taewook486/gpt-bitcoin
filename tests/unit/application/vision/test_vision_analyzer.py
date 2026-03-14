"""
Unit tests for VisionAnalyzer.

Tests GLM-4.6V Vision API integration and analysis combination.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from gpt_bitcoin.application.vision.vision_analyzer import VisionAnalyzer
from gpt_bitcoin.domain.models.chart_analysis import (
    ChartAnalysis,
    CombinedAnalysis,
    Sentiment,
    Trend,
)
from gpt_bitcoin.infrastructure.exceptions import GLMAPIError


@pytest.fixture
def mock_glm_client():
    """Create mock GLM client."""
    client = MagicMock()
    client.analyze_with_vision = AsyncMock()
    return client


@pytest.fixture
def vision_analyzer(mock_glm_client):
    """Create VisionAnalyzer instance with mock client."""
    return VisionAnalyzer(glm_client=mock_glm_client)


@pytest.fixture
def sample_chart_image(tmp_path: Path) -> Path:
    """Create sample chart image for testing."""
    # Create a minimal PNG image (1x1 pixel)
    image_path = tmp_path / "test_chart.png"
    # Minimal PNG file bytes
    image_path.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9c\xf8\x0f\x00\x00\x01"
        b"\x00\x05\xfe\x02\xfd\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return image_path


@pytest.fixture
def sample_vision_response() -> str:
    """Create sample Vision API response."""
    return json.dumps(
        {
            "patterns": ["Hammer", "Bullish Engulfing"],
            "trend": "uptrend",
            "support_levels": [65000000, 64000000],
            "resistance_levels": [70000000, 71000000],
            "sentiment": "bullish",
            "confidence": 0.85,
        }
    )


@pytest.fixture
def sample_technical_indicators() -> dict:
    """Create sample technical indicators."""
    return {
        "rsi": 45.5,
        "ma_short": 68000000,
        "ma_long": 67000000,
        "macd": {"macd": 500000, "signal": 400000, "histogram": 100000},
        "fear_greed_index": 60,
    }


class TestVisionAnalyzer:
    """Test suite for VisionAnalyzer."""

    @pytest.mark.asyncio
    async def test_analyze_chart_success(
        self,
        vision_analyzer: VisionAnalyzer,
        sample_chart_image: Path,
        sample_vision_response: str,
    ):
        """Test successful chart analysis."""
        # Mock GLM client response
        vision_analyzer._glm_client.analyze_with_vision.return_value = MagicMock(
            content=sample_vision_response,
            parsed=None,
        )

        analysis = await vision_analyzer.analyze_chart(
            image_path=sample_chart_image,
            coin_name="BTC",
        )

        assert isinstance(analysis, ChartAnalysis)
        assert len(analysis.patterns) == 2
        assert "Hammer" in analysis.patterns
        assert analysis.trend == Trend.UPTREND
        assert analysis.sentiment == Sentiment.BULLISH
        assert analysis.confidence == 0.85

    @pytest.mark.asyncio
    async def test_analyze_chart_api_failure(
        self,
        vision_analyzer: VisionAnalyzer,
        sample_chart_image: Path,
    ):
        """Test chart analysis with API failure."""
        vision_analyzer._glm_client.analyze_with_vision.side_effect = GLMAPIError(
            "API failed",
            model="glm-4.6v",
        )

        with pytest.raises(GLMAPIError):
            await vision_analyzer.analyze_chart(
                image_path=sample_chart_image,
                coin_name="BTC",
            )

    @pytest.mark.asyncio
    async def test_analyze_chart_invalid_json(
        self,
        vision_analyzer: VisionAnalyzer,
        sample_chart_image: Path,
    ):
        """Test chart analysis with invalid JSON response."""
        vision_analyzer._glm_client.analyze_with_vision.return_value = MagicMock(
            content="Invalid JSON",
            parsed=None,
        )

        with pytest.raises(GLMAPIError, match="Failed to parse"):
            await vision_analyzer.analyze_chart(
                image_path=sample_chart_image,
                coin_name="BTC",
            )

    @pytest.mark.asyncio
    async def test_combine_analysis_agreement(
        self,
        vision_analyzer: VisionAnalyzer,
        sample_technical_indicators: dict,
    ):
        """Test combined analysis when vision and text agree."""
        vision = ChartAnalysis(
            patterns=["Hammer"],
            trend=Trend.UPTREND,
            support_levels=[65000000],
            resistance_levels=[70000000],
            sentiment=Sentiment.BULLISH,
            confidence=0.8,
        )

        # Add bullish technical indicators
        sample_technical_indicators["rsi"] = 30  # Oversold - bullish
        sample_technical_indicators["ma_short"] = 68000000
        sample_technical_indicators["ma_long"] = 67000000  # MA crossover - bullish
        sample_technical_indicators["macd"] = {
            "macd": 500000,
            "signal": 400000,
            "histogram": 100000,
        }  # Positive MACD - bullish
        sample_technical_indicators["fear_greed_index"] = 75  # Greed - contrarian bullish

        combined = await vision_analyzer.combine_analysis(
            vision=vision,
            technical_indicators=sample_technical_indicators,
        )

        assert isinstance(combined, CombinedAnalysis)
        assert combined.agreement is True  # Both bullish
        assert combined.combined_sentiment == Sentiment.BULLISH
        assert combined.combined_confidence >= 0.8  # Agreement bonus
        assert combined.signal_strength == "strong"

    @pytest.mark.asyncio
    async def test_combine_analysis_disagreement(
        self,
        vision_analyzer: VisionAnalyzer,
        sample_technical_indicators: dict,
    ):
        """Test combined analysis when vision and text disagree."""
        vision = ChartAnalysis(
            patterns=["Shooting Star"],
            trend=Trend.DOWNTREND,
            support_levels=[65000000],
            resistance_levels=[70000000],
            sentiment=Sentiment.BEARISH,
            confidence=0.6,
        )

        # Add bullish technical indicators (disagree with vision)
        sample_technical_indicators["rsi"] = 30
        sample_technical_indicators["ma_short"] = 68000000
        sample_technical_indicators["ma_long"] = 67000000
        sample_technical_indicators["macd"] = {
            "macd": 500000,
            "signal": 400000,
            "histogram": 100000,
        }
        sample_technical_indicators["fear_greed_index"] = 75

        combined = await vision_analyzer.combine_analysis(
            vision=vision,
            technical_indicators=sample_technical_indicators,
        )

        assert combined.agreement is False
        # Should use vision signal since confidence >= 0.7
        assert combined.combined_confidence < 0.6  # Disagreement penalty
        assert combined.signal_strength in ["medium", "weak"]

    @pytest.mark.asyncio
    async def test_combine_analysis_pattern_bonus(
        self,
        vision_analyzer: VisionAnalyzer,
        sample_technical_indicators: dict,
    ):
        """Test combined analysis with pattern detection bonus."""
        vision = ChartAnalysis(
            patterns=["Hammer", "Bullish Engulfing", "Morning Star"],  # 3 patterns
            trend=Trend.UPTREND,
            support_levels=[65000000],
            resistance_levels=[70000000],
            sentiment=Sentiment.BULLISH,
            confidence=0.7,
        )

        sample_technical_indicators["rsi"] = 30
        sample_technical_indicators["ma_short"] = 68000000
        sample_technical_indicators["ma_long"] = 67000000
        sample_technical_indicators["macd"] = {
            "macd": 500000,
            "signal": 400000,
            "histogram": 100000,
        }
        sample_technical_indicators["fear_greed_index"] = 75

        combined = await vision_analyzer.combine_analysis(
            vision=vision,
            technical_indicators=sample_technical_indicators,
        )

        # Pattern bonus should increase confidence
        assert combined.combined_confidence >= 0.8

    def test_determine_text_sentiment_bullish(
        self,
        vision_analyzer: VisionAnalyzer,
    ):
        """Test text sentiment determination for bullish signals."""
        sentiment = vision_analyzer._determine_text_sentiment(
            rsi=30,  # Oversold
            ma_short=68000000,
            ma_long=67000000,  # Crossover up
            macd={"macd": 500000, "signal": 400000, "histogram": 100000},  # Positive
            fear_greed=20,  # Fear - contrarian bullish
        )
        assert sentiment == Sentiment.BULLISH

    def test_determine_text_sentiment_bearish(
        self,
        vision_analyzer: VisionAnalyzer,
    ):
        """Test text sentiment determination for bearish signals."""
        sentiment = vision_analyzer._determine_text_sentiment(
            rsi=75,  # Overbought
            ma_short=65000000,
            ma_long=67000000,  # Crossover down
            macd={"macd": -500000, "signal": -400000, "histogram": -100000},  # Negative
            fear_greed=85,  # Extreme greed - contrarian bearish
        )
        assert sentiment == Sentiment.BEARISH

    def test_determine_text_sentiment_neutral(
        self,
        vision_analyzer: VisionAnalyzer,
    ):
        """Test text sentiment determination for neutral signals."""
        # To get NEUTRAL, need equal bullish and bearish signals
        # - RSI < 30: bullish (+1)
        # - MA short <= long: bearish (+1)
        # - MACD <= signal: bearish (+1)
        # - Fear/greed < 25: bullish (+1)
        # Total: bullish=2, bearish=2 -> NEUTRAL
        sentiment = vision_analyzer._determine_text_sentiment(
            rsi=25,  # Oversold - bullish
            ma_short=66000000,
            ma_long=67000000,  # Death cross tendency - bearish
            macd={"macd": -100000, "signal": 0, "histogram": -100000},  # Below signal - bearish
            fear_greed=20,  # Fear - contrarian bullish
        )
        assert sentiment == Sentiment.NEUTRAL

    def test_check_agreement(
        self,
        vision_analyzer: VisionAnalyzer,
    ):
        """Test signal agreement detection."""
        assert vision_analyzer._check_agreement(Sentiment.BULLISH, Sentiment.BULLISH) is True
        assert vision_analyzer._check_agreement(Sentiment.BEARISH, Sentiment.BEARISH) is True
        assert vision_analyzer._check_agreement(Sentiment.NEUTRAL, Sentiment.NEUTRAL) is True
        assert vision_analyzer._check_agreement(Sentiment.BULLISH, Sentiment.BEARISH) is False
        assert vision_analyzer._check_agreement(Sentiment.BULLISH, Sentiment.NEUTRAL) is False

    def test_combine_sentiments(
        self,
        vision_analyzer: VisionAnalyzer,
    ):
        """Test sentiment combination logic."""
        # Agreement case
        result = vision_analyzer._combine_sentiments(
            Sentiment.BULLISH, Sentiment.BULLISH, 0.8, True
        )
        assert result == Sentiment.BULLISH
        # Disagreement with high vision confidence
        result = vision_analyzer._combine_sentiments(
            Sentiment.BULLISH, Sentiment.BEARISH, 0.8, False
        )
        assert result == Sentiment.BULLISH
        # Disagreement with low vision confidence
        result = vision_analyzer._combine_sentiments(
            Sentiment.BULLISH, Sentiment.BEARISH, 0.5, False
        )
        assert result == Sentiment.BEARISH

    def test_calculate_combined_confidence(
        self,
        vision_analyzer: VisionAnalyzer,
    ):
        """Test combined confidence calculation."""
        # Agreement bonus
        confidence = vision_analyzer._calculate_combined_confidence(
            vision_confidence=0.7,
            agreement=True,
            pattern_count=1,
        )
        assert confidence >= 0.85  # 0.7 + 0.15 bonus
        # Disagreement penalty
        confidence = vision_analyzer._calculate_combined_confidence(
            vision_confidence=0.7,
            agreement=False,
            pattern_count=1,
        )
        assert confidence <= 0.6  # 0.7 - 0.1 penalty
        # Pattern bonus
        confidence = vision_analyzer._calculate_combined_confidence(
            vision_confidence=0.7,
            agreement=True,
            pattern_count=3,
        )
        assert confidence >= 0.95  # Agreement + pattern bonuses

    def test_determine_signal_strength(
        self,
        vision_analyzer: VisionAnalyzer,
    ):
        """Test signal strength determination."""
        assert vision_analyzer._determine_signal_strength(0.85, True) == "strong"
        assert vision_analyzer._determine_signal_strength(0.8, False) == "medium"
        assert vision_analyzer._determine_signal_strength(0.6, True) == "medium"
        assert vision_analyzer._determine_signal_strength(0.5, False) == "weak"
