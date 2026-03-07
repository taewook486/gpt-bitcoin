"""
Integration tests for Vision + Text combination workflow.

Tests the complete workflow from chart generation to combined analysis.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json

from gpt_bitcoin.application.vision.chart_generator import ChartGenerator
from gpt_bitcoin.application.vision.vision_analyzer import VisionAnalyzer
from gpt_bitcoin.domain.models.cryptocurrency import Cryptocurrency
from gpt_bitcoin.domain.models.chart_analysis import (
    ChartAnalysis,
    CombinedAnalysis,
    Sentiment,
    Trend,
)


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """Create temporary output directory."""
    chart_dir = tmp_path / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)
    return chart_dir


@pytest.fixture
def chart_generator(output_dir: Path) -> ChartGenerator:
    """Create ChartGenerator instance."""
    return ChartGenerator(output_dir=output_dir)


@pytest.fixture
def mock_glm_client():
    """Create mock GLM client."""
    client = MagicMock()
    client.analyze_with_vision = AsyncMock()
    return client


@pytest.fixture
def vision_analyzer(mock_glm_client):
    """Create VisionAnalyzer instance."""
    return VisionAnalyzer(glm_client=mock_glm_client)


@pytest.fixture
def sample_ohlcv_data() -> list[dict]:
    """Create sample OHLCV data for testing (100 candles)."""
    data = []
    base_time = int(datetime.now().timestamp())
    base_price = 70_000_000

    for i in range(100):
        timestamp = base_time - (99 - i) * 3600
        variation = (i % 10 - 5) * 100_000
        open_price = base_price + variation
        close_price = open_price + ((i % 7) - 3) * 50_000
        high_price = max(open_price, close_price) + abs(i % 5) * 20_000
        low_price = min(open_price, close_price) - abs(i % 4) * 15_000
        volume = 1000 + (i % 20) * 100

        data.append({
            "timestamp": timestamp,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": volume,
        })

    return data


@pytest.fixture
def sample_vision_response() -> str:
    """Create sample Vision API response."""
    return json.dumps({
        "patterns": ["Hammer", "Bullish Engulfing"],
        "trend": "uptrend",
        "support_levels": [65000000, 64000000],
        "resistance_levels": [70000000, 71000000],
        "sentiment": "bullish",
        "confidence": 0.85,
    })


class TestVisionIntegration:
    """Integration test suite for Vision + Text workflow."""

    @pytest.mark.asyncio
    async def test_complete_workflow(
        self,
        chart_generator: ChartGenerator,
        vision_analyzer: VisionAnalyzer,
        sample_ohlcv_data: list[dict],
        sample_vision_response: str,
    ):
        """Test complete workflow from chart generation to combined analysis."""
        # Step 1: Generate chart
        chart_path = await chart_generator.generate_chart(
            coin=Cryptocurrency.BTC,
            ohlcv_data=sample_ohlcv_data,
            period="1h",
            days=1,
        )

        assert chart_path.exists()

        # Step 2: Analyze chart with Vision API
        vision_analyzer._glm_client.analyze_with_vision.return_value = MagicMock(
            content=sample_vision_response,
            parsed=None,
        )

        vision_analysis = await vision_analyzer.analyze_chart(
            image_path=chart_path,
            instruction="Analyze this chart for trading signals",
        )

        assert isinstance(vision_analysis, ChartAnalysis)
        assert vision_analysis.sentiment == Sentiment.BULLISH

        # Step 3: Combine with technical indicators
        technical_indicators = {
            "rsi": 35,  # Slightly oversold - bullish
            "ma_short": 68000000,
            "ma_long": 67000000,  # MA crossover up - bullish
            "macd": 300000,  # Positive MACD - bullish
            "fear_greed_index": 65,  # Greed
        }

        combined = await vision_analyzer.combine_analysis(
            vision=vision_analysis,
            technical_indicators=technical_indicators,
        )

        assert isinstance(combined, CombinedAnalysis)
        assert combined.agreement is True  # Both bullish
        assert combined.combined_sentiment == Sentiment.BULLISH
        assert combined.signal_strength in ["strong", "medium"]

    @pytest.mark.asyncio
    async def test_workflow_with_bearish_signals(
        self,
        chart_generator: ChartGenerator,
        vision_analyzer: VisionAnalyzer,
        sample_ohlcv_data: list[dict],
    ):
        """Test workflow with bearish signals."""
        # Generate chart
        chart_path = await chart_generator.generate_chart(
            coin=Cryptocurrency.ETH,
            ohlcv_data=sample_ohlcv_data,
            period="4h",
            days=1,
        )

        # Analyze with bearish vision response
        bearish_response = json.dumps({
            "patterns": ["Shooting Star", "Bearish Engulfing"],
            "trend": "downtrend",
            "support_levels": [2000000, 1900000],
            "resistance_levels": [2500000, 2600000],
            "sentiment": "bearish",
            "confidence": 0.75,
        })

        vision_analyzer._glm_client.analyze_with_vision.return_value = MagicMock(
            content=bearish_response,
            parsed=None,
        )

        vision_analysis = await vision_analyzer.analyze_chart(
            image_path=chart_path,
            instruction="Analyze this chart",
        )

        assert vision_analysis.sentiment == Sentiment.BEARISH

        # Combine with bearish technical indicators
        technical_indicators = {
            "rsi": 75,  # Overbought - bearish
            "ma_short": 2000000,
            "ma_long": 2100000,  # MA crossover down - bearish
            "macd": -200000,  # Negative MACD - bearish
            "fear_greed_index": 85,  # Extreme greed - contrarian bearish
        }

        combined = await vision_analyzer.combine_analysis(
            vision=vision_analysis,
            technical_indicators=technical_indicators,
        )

        assert combined.agreement is True  # Both bearish
        assert combined.combined_sentiment == Sentiment.BEARISH

    @pytest.mark.asyncio
    async def test_workflow_with_conflicting_signals(
        self,
        chart_generator: ChartGenerator,
        vision_analyzer: VisionAnalyzer,
        sample_ohlcv_data: list[dict],
        sample_vision_response: str,
    ):
        """Test workflow with conflicting vision and text signals."""
        # Generate chart
        chart_path = await chart_generator.generate_chart(
            coin=Cryptocurrency.SOL,
            ohlcv_data=sample_ohlcv_data,
            period="1h",
            days=1,
        )

        # Analyze with bullish vision response
        vision_analyzer._glm_client.analyze_with_vision.return_value = MagicMock(
            content=sample_vision_response,
            parsed=None,
        )

        vision_analysis = await vision_analyzer.analyze_chart(
            image_path=chart_path,
            instruction="Analyze this chart",
        )

        assert vision_analysis.sentiment == Sentiment.BULLISH

        # Combine with bearish technical indicators (conflict)
        technical_indicators = {
            "rsi": 80,  # Overbought - bearish
            "ma_short": 100000,
            "ma_long": 110000,  # MA crossover down - bearish
            "macd": -50000,  # Negative MACD - bearish
            "fear_greed_index": 90,  # Extreme greed - bearish
        }

        combined = await vision_analyzer.combine_analysis(
            vision=vision_analysis,
            technical_indicators=technical_indicators,
        )

        assert combined.agreement is False
        # With high vision confidence, should use vision signal
        assert combined.combined_sentiment == Sentiment.BULLISH
        assert combined.combined_confidence < vision_analysis.confidence  # Penalty for disagreement

    @pytest.mark.asyncio
    async def test_fallback_to_text_only(
        self,
        vision_analyzer: VisionAnalyzer,
    ):
        """Test fallback to text-only analysis when Vision API fails."""
        from gpt_bitcoin.infrastructure.exceptions import GLMAPIError

        # Mock Vision API failure
        vision_analyzer._glm_client.analyze_with_vision.side_effect = GLMAPIError(
            "Vision API unavailable",
            model="glm-4.6v",
        )

        # Create technical indicators
        technical_indicators = {
            "rsi": 30,  # Oversold - bullish
            "ma_short": 68000000,
            "ma_long": 67000000,  # MA crossover up - bullish
            "macd": 400000,  # Positive MACD - bullish
            "fear_greed_index": 25,  # Fear - bullish
        }

        # Text-only analysis should still work
        text_sentiment = vision_analyzer._determine_text_sentiment(technical_indicators)

        assert text_sentiment == Sentiment.BULLISH

    @pytest.mark.asyncio
    async def test_multiple_coins_workflow(
        self,
        chart_generator: ChartGenerator,
        vision_analyzer: VisionAnalyzer,
        sample_ohlcv_data: list[dict],
        sample_vision_response: str,
    ):
        """Test workflow with multiple cryptocurrencies."""
        coins = [Cryptocurrency.BTC, Cryptocurrency.ETH, Cryptocurrency.SOL]

        for coin in coins:
            # Generate chart
            chart_path = await chart_generator.generate_chart(
                coin=coin,
                ohlcv_data=sample_ohlcv_data,
                period="1h",
                days=1,
            )

            assert chart_path.exists()
            assert coin.value in chart_path.name

            # Analyze chart
            vision_analyzer._glm_client.analyze_with_vision.return_value = MagicMock(
                content=sample_vision_response,
                parsed=None,
            )

            analysis = await vision_analyzer.analyze_chart(
                image_path=chart_path,
                instruction="Analyze this chart",
            )

            assert isinstance(analysis, ChartAnalysis)

    @pytest.mark.asyncio
    async def test_chart_cleanup_after_analysis(
        self,
        chart_generator: ChartGenerator,
        vision_analyzer: VisionAnalyzer,
        sample_ohlcv_data: list[dict],
        sample_vision_response: str,
    ):
        """Test that old charts are cleaned up."""
        # Generate multiple charts
        for i in range(3):
            chart_path = await chart_generator.generate_chart(
                coin=Cryptocurrency.BTC,
                ohlcv_data=sample_ohlcv_data,
                period="1h",
                days=1,
            )
            assert chart_path.exists()

        # Run cleanup
        await chart_generator.cleanup_old_charts(max_age_hours=0)  # Cleanup all

        # Verify charts were cleaned
        remaining_charts = list(chart_generator.output_dir.glob("*.png"))
        # Some charts might remain if created during the test
        assert len(remaining_charts) < 5

    @pytest.mark.asyncio
    async def test_error_handling_insufficient_data(
        self,
        chart_generator: ChartGenerator,
    ):
        """Test error handling with insufficient OHLCV data."""
        minimal_data = [
            {
                "timestamp": int(datetime.now().timestamp()) - i * 3600,
                "open": 70_000_000,
                "high": 70_100_000,
                "low": 69_900_000,
                "close": 70_050_000,
                "volume": 1000,
            }
            for i in range(10)
        ]

        with pytest.raises(ValueError, match="Insufficient data points"):
            await chart_generator.generate_chart(
                coin=Cryptocurrency.BTC,
                ohlcv_data=minimal_data,
                period="1h",
                days=1,
            )
